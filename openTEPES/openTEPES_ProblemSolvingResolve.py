"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 11, 2026

openTEPES.openTEPES_ProblemSolvingResolve — Mode C post-build hot-swap re-solve.

Re-solve an already-built model once per parameter overlay without rebuilding it, so a
sweep, sensitivity study or Monte-Carlo reuses the one slow build. Only ``mutable=True``
Params can be hot-swapped: the operational set ``pDemandElec``, ``pENSCost``,
``pLinearVarCost``, ``pEFOR``, ``pReserveMargin``, ``pRESEnergy``. See ``resolve`` for the
overlay format.
"""
from __future__ import annotations

from pyomo.environ import SolverFactory
from pyomo.opt import TerminationCondition


def overlay_scaled(OptModel, param_name: str, factor: float) -> dict:
    """Return an overlay that scales every current value of ``param_name`` by ``factor``.

    Example: ``overlay_scaled(model, "pDemandElec", 1.10)`` for a 10 % demand uplift.
    """
    param = getattr(OptModel, param_name)
    return {param_name: {idx: val * factor for idx, val in param.extract_values().items()}}


def resolve(OptModel, SolverName: str, overlays, *, restore: bool = True, tee: bool = False):
    """Re-solve ``OptModel`` once per overlay, swapping mutable Param values in place.

    ``overlays`` is a list of dicts, each mapping a mutable Param name to new values (a
    dict ``index -> value`` for an indexed Param, or a scalar). Each overlay is applied
    relative to the baseline (values at call time), not cumulatively; ``{}`` re-solves the
    baseline. With ``restore`` (default) the baseline is restored at the end. ``SolverName``
    must be a non-persistent solver. Returns one dict per overlay with the termination
    condition and total system cost (None if not optimal).
    """
    overlays = list(overlays)

    # Snapshot the baseline values of every Param any overlay touches. The snapshot serves
    # two purposes: resetting the touched Params before each overlay (so overlays are
    # independent, not cumulative) and the optional restore at the end of the sweep.
    touched = set()
    for ov in overlays:
        touched.update(ov.keys())
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
