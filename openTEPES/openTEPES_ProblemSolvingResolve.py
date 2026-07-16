"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 16, 2026

openTEPES.openTEPES_ProblemSolvingResolve — Mode C post-build hot-swap re-solve.

Re-solve a built model once per parameter overlay without rebuilding, so a sweep reuses the one slow build.
A swap reaches the model only for a ``mutable=True`` Param the built model reads live; ``resolve`` rejects
an overlay it cannot see. A Param is not read live when a constraint captured its value as a constant with
``pX[...]()``, or when the constraints that reference it were skipped for the case (e.g. the adequacy
reserve margin on a case with no generation candidates). A swap is also inexact for a Param with a
build-derived dependent: ``pDemandElec`` sets the immutable peak and the commitment boundary, which a swap
does not update. See ``resolve`` for the overlay format.
"""
from __future__ import annotations

from pyomo.environ import SolverFactory, Constraint, Objective
from pyomo.opt import TerminationCondition
from pyomo.core.expr import identify_mutable_parameters

try:
    from .openTEPES_ProblemSolvingDualExtraction import unfix_for_duals
except ImportError:  # direct run: no parent package
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from openTEPES_ProblemSolvingDualExtraction import unfix_for_duals


def _live_mutable_params(OptModel) -> set[str]:
    """Names of the mutable Params the active constraints and objective actually read live.

    A constraint that captures a Param with ``pX[...]()`` freezes its value at build time, so swapping the
    Param later does nothing there. Only a Param referenced without the call stays live. This returns the set
    that a swap can still reach, so resolve can reject an overlay that would silently do nothing.
    """
    live = set()
    for obj in OptModel.component_data_objects(Objective, active=True):
        for par in identify_mutable_parameters(obj.expr):
            live.add(par.parent_component().name)
    # A constraint keeps its right-hand side in lower / upper, not body: an equality sum(...) == pDemandElec
    # holds pDemandElec in the bound. Walk all three or a Param used only as a bound is missed.
    for con in OptModel.component_data_objects(Constraint, active=True):
        for expr in (con.body, con.lower, con.upper):
            if expr is not None:
                for par in identify_mutable_parameters(expr):
                    live.add(par.parent_component().name)
    return live


def overlay_scaled(OptModel, param_name: str, factor: float) -> dict:
    """Return an overlay scaling every current value of ``param_name`` by ``factor``.

    E.g. ``overlay_scaled(model, "pDemandElec", 1.10)`` for a 10 % demand uplift.
    """
    param = getattr(OptModel, param_name)
    return {param_name: {idx: val * factor for idx, val in param.extract_values().items()}}


def resolve(OptModel, SolverName: str, overlays, *, restore: bool = True, tee: bool = False):
    """Re-solve ``OptModel`` once per overlay, swapping mutable Param values in place.

    ``overlays`` is a list of dicts mapping a mutable Param name to new values (``index ->
    value``, or a scalar). Each overlay applies relative to the baseline, not cumulatively;
    ``{}`` re-solves the baseline. ``restore`` (default) restores the baseline at the end.
    ``SolverName`` must be non-persistent. Returns one dict per overlay with the termination
    condition and total system cost (None if not optimal).

    Releases the investment and commitment decisions that the solve fixed to read the duals, so each
    overlay re-optimises them. Decisions the case itself fixed stay fixed.
    """
    overlays = list(overlays)

    # Solving fixes the investment plan and the commitment to read the duals, so a model that has been solved
    # would answer a demand rise with unserved energy instead of new capacity, and report too high a cost
    # without saying anything. Release those decisions first; a model that was never solved is unaffected.
    unfix_for_duals(OptModel)

    # Reject an overlay the re-solve cannot see, so it does not swap silently and return an unchanged cost as
    # if it had worked. A Param is unseen when the name is wrong, a constraint captured its value as a
    # constant, or the constraints that use it were skipped for this case.
    touched = set()
    for ov in overlays:
        touched.update(ov.keys())
    live = _live_mutable_params(OptModel)
    inert = sorted(name for name in touched if name not in live)
    if inert:
        raise ValueError(
            f"resolve() cannot apply these overlays; the built model does not read them live: {', '.join(inert)}."
        )

    # Snapshot the baseline of every touched Param: used to reset before each overlay (so
    # overlays are independent, not cumulative) and for the optional restore at the end.
    baseline = {name: getattr(OptModel, name).extract_values() for name in touched}

    Solver = SolverFactory(SolverName)
    results = []
    for i, ov in enumerate(overlays):
        for name, values in baseline.items():
            getattr(OptModel, name).store_values(values)
        for name, values in ov.items():
            getattr(OptModel, name).store_values(values)
        SolverResults = Solver.solve(OptModel, tee=tee)
        tc = SolverResults.solver.termination_condition
        cost = OptModel.vTotalSCost() if tc == TerminationCondition.optimal else None
        results.append({"overlay": i, "status": str(tc), "total_cost_meur": cost})

    if restore:
        for name, values in baseline.items():
            getattr(OptModel, name).store_values(values)

    return results
