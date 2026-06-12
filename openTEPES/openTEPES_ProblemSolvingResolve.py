"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 12, 2026

openTEPES.openTEPES_ProblemSolvingResolve — Mode C post-build hot-swap re-solve.

Re-solve an already-built openTEPES model under a sequence of parameter overlays without
rebuilding it. Building the model is the slow step on large cases (tens of seconds), so
re-using one built model across many parameter values is the cheapest way to run a
parametric sweep, a sensitivity study, or a Monte-Carlo on parameter values.

Only Params declared ``mutable=True`` can be hot-swapped. The operational sweep set
promoted for Mode C is::

    pDemandElec  pENSCost  pLinearVarCost  pEFOR  pReserveMargin  pRESEnergy

(see ``openTEPES_DataConfiguration.py``). Structural and topology Params stay immutable
because they are read in build-time Python conditionals; changing them needs a rebuild
(RFC Modes A / B).

An overlay is a dict mapping a Param name to its new values::

    {"pDemandElec": {(p, sc, n, nd): value, ...}}   # indexed Param: dict of index -> value
    {"pENSCost": 12000.0}                            # scalar Param: a single value

``overlay_scaled`` builds the common "scale the current values by a factor" overlay.

This is the single-process building block. The fork()-based parallel runner of RFC PR #7
composes it across worker processes (build once in the master, fork, resolve in each child).
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

    Parameters
    ----------
    OptModel :
        An already-built (and usually already-solved) openTEPES model.
    SolverName : str
        Any non-persistent solver name (``gurobi``, ``highs``, ``cplex``, ``glpk`` ...).
        Each call re-reads the current mutable Param values, so no explicit solver update
        is needed. Persistent backends (``appsi_gurobi`` / ``gurobi_persistent``) are not
        yet supported here and need an ``update_params`` pass; use a one-shot solver.
    overlays : list of dict
        Each dict maps a mutable Param name to new values (a dict ``index -> value`` for an
        indexed Param, or a scalar for a scalar Param). Every overlay is applied **relative
        to the baseline** (the Param values at call time), not to the previous overlay: the
        touched Params are reset to their baseline values before each overlay is stored, so
        ``[{"pDemandElec": ...}, {"pENSCost": ...}]`` solves demand-only then ENS-cost-only.
        An empty dict ``{}`` re-solves the baseline unchanged.
    restore : bool, default True
        Restore the original Param values after the sweep so the model can be reused. With
        ``restore=False`` the last overlay stays applied.
    tee : bool, default False
        Stream solver output.

    Returns
    -------
    list of dict
        One entry per overlay: ``{"overlay": i, "status": <termination condition>,
        "total_cost_meur": <float or None>}``. ``total_cost_meur`` is None when the solve
        did not reach an optimal solution.
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
