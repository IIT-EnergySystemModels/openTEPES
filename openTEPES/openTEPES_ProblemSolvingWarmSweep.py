"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 25, 2026
openTEPES.openTEPES_ProblemSolvingWarmSweep — opt-in two-mode persistent re-solve for Mode C sweeps (default OFF).

Motivation
----------
For a Mode C sensitivity sweep (change a parameter, re-solve, repeat) the persistent solver already avoids
re-exporting the model. On top of that, when consecutive re-solves differ by a SMALL amount, dual simplex can
warm-start from the previous basis and finish much faster than a cold barrier solve. Measured on the 9n case
(498k-row LP, Gurobi): fine 2% steps ran 3-9 s with warm dual simplex versus ~10 s persistent-barrier and
~16 s non-persistent. But the same warm simplex on LARGE steps was erratic and once took 202 s, because
simplex struggles on big degenerate changes. So warm simplex is only safe with a time cap and a barrier
fallback.

This module adds that as an OPT-IN mode, off by default so the standard solve path is unchanged. It applies to
persistent-solver RE-SOLVES of one built model: the Mode C hot-swap sweep (``openTEPES_ProblemSolvingResolve``)
and, when a case is solved with ``gurobi_persistent``, the stage-loop re-solves (ncall > 1). It does nothing
for Mode A / Mode B (each runs a different model, so nothing persists) or for non-Gurobi solvers.

  * ``enabled()``               True only when OTEPES_WARM_RESOLVE is set truthy.
  * ``apply_resolve_method()``  on a re-solve (ncall > 1) switch the persistent Gurobi solver to dual simplex
                                with a short TimeLimit, so a stall aborts quickly instead of hanging.
  * ``fallback_if_stalled()``   if that capped re-solve hit the time limit, restore barrier + the full
                                TimeLimit and solve once more, so the sweep never gets stuck.

Two flags. ``--warm-resolve`` (``OTEPES_WARM_RESOLVE``) turns the mode on and every persistent re-solve uses
BARRIER — reliable, the saving coming purely from not re-exporting the resident model (~1.5x over
non-persistent). ``--warm-resolve-simplex`` (``OTEPES_WARM_RESOLVE_SIMPLEX``, needs the base flag) additionally
uses warm dual simplex (up to ~5x on small steps, but erratic on this LP class, so time-capped with a barrier
fallback). Both mirror ``--threads`` in openTEPES_Main. Default off: the standard solve path is unchanged.
"""
from __future__ import annotations

import os

from pyomo.opt import TerminationCondition

# Full barrier TimeLimit used by the standard Gurobi presets (see openTEPES_ProblemSolvingTuning).
_FULL_TIME_LIMIT = 36000


def enabled() -> bool:
    """True when the opt-in warm dual-simplex re-solve mode is switched on via the environment flag."""
    return os.environ.get("OTEPES_WARM_RESOLVE", "").strip().lower() in ("1", "true", "yes", "on")


def simplex_enabled() -> bool:
    """True when the DEEPER warm dual-simplex opt-in is on (OTEPES_WARM_RESOLVE_SIMPLEX).

    Requires the base mode (``enabled()``) too. When off, every persistent re-solve uses BARRIER — reliable,
    the whole saving coming from not re-exporting the resident model. The dual-simplex gamble (up to ~5x on
    small RHS/bound steps, but erratic on this LP class and direction-wrong for objective/cost overlays) is
    opt-in only.
    """
    return enabled() and os.environ.get("OTEPES_WARM_RESOLVE_SIMPLEX", "").strip().lower() in ("1", "true", "yes", "on")


def cap_seconds() -> int:
    """Per-re-solve time cap (seconds) for the warm dual-simplex attempt; OTEPES_WARM_RESOLVE_CAP overrides.

    Kept short so a stalled simplex aborts and hands over to the barrier fallback quickly. Default 60 s.
    """
    env = os.environ.get("OTEPES_WARM_RESOLVE_CAP", "").strip()
    return int(env) if env.isdigit() and int(env) > 0 else 60


def _is_gurobi(SolverName: str) -> bool:
    return SolverName in ("gurobi", "gurobi_direct", "appsi_gurobi", "gurobi_persistent")


def _set_param(Solver, SolverName: str, name: str, value) -> None:
    """Set one Gurobi parameter through whichever API this solver flavour uses."""
    if SolverName == "gurobi_persistent":
        Solver.set_gurobi_param(name, value)
    else:
        Solver.options[name] = value


def apply_resolve_method(Solver, SolverName: str, ncall: int) -> bool:
    """Configure the Gurobi solver for the stage-loop re-solve, ONLY when the deeper simplex opt-in is on.

    With just ``--warm-resolve`` this is a no-op: the stage loop keeps openTEPES's own barrier/``Method=-1``
    behaviour, so barrier stays the default everywhere. Under ``OTEPES_WARM_RESOLVE_SIMPLEX`` it switches the
    re-solve to warm dual simplex:

    * ncall == 1 (baseline): force ``Crossover=1`` so the barrier solve leaves a simplex BASIS (the standard
      ``Crossover=-1`` does not guarantee one, and the later warm-starts need it).
    * ncall > 1 (re-solve): dual simplex under a short time cap, so a stall aborts quickly and hands over to
      the barrier fallback instead of hanging.

    Returns True if warm-simplex re-solve options were applied (so the caller arms the fallback); False otherwise.
    """
    if not simplex_enabled() or not _is_gurobi(SolverName):
        return False
    if ncall <= 1:
        _set_param(Solver, SolverName, "Crossover", 1)   # barrier baseline must leave a basis to warm-start from
        return False
    _set_param(Solver, SolverName, "Method", 1)          # dual simplex -> warm-starts from the retained basis
    _set_param(Solver, SolverName, "LPWarmStart", 2)     # keep and use the previous basis
    _set_param(Solver, SolverName, "TimeLimit", cap_seconds())
    return True


def fallback_if_stalled(Solver, OptModel, SolverName: str, ncall: int, SolverResults, solve_kwargs: dict):
    """If the capped warm-simplex re-solve hit the time limit, redo it with barrier and the full time budget.

    Returns the (possibly new) SolverResults. A no-op unless warm simplex is on, this was a re-solve, and the
    last result was ``maxTimeLimit``.
    """
    if not simplex_enabled() or ncall <= 1 or not _is_gurobi(SolverName):
        return SolverResults
    if SolverResults.solver.termination_condition != TerminationCondition.maxTimeLimit:
        return SolverResults
    print("warm simplex stalled; falling back to barrier ####", ncall)
    _set_param(Solver, SolverName, "Method", 2)          # barrier
    _set_param(Solver, SolverName, "Crossover", -1)
    _set_param(Solver, SolverName, "TimeLimit", _FULL_TIME_LIMIT)
    return Solver.solve(OptModel, **solve_kwargs)


def resolve_persistent(OptModel, overlays, baseline, touched, tee: bool = False):
    """Persistent + warm-simplex version of the Mode C ``resolve`` re-solve loop.

    The standard ``resolve`` builds a fresh non-persistent solver and re-exports the whole model for every
    overlay. This keeps ONE ``gurobi_persistent`` instance: it exports the model once, then for each overlay
    pushes only the changed constraints (those reading a swapped Param) and re-solves. The first overlay uses
    barrier + crossover to leave a basis; later overlays use dual simplex warm-started from it, under a time
    cap that falls back to barrier if it stalls. Returns the same list-of-dicts as ``resolve``.

    ``baseline`` / ``touched`` are the caller's snapshot of the swapped Params (see ``resolve``); overlays are
    applied relative to the baseline, not cumulatively.
    """
    from pyomo.environ import SolverFactory, Constraint, Objective
    from pyomo.core.expr import identify_mutable_parameters

    names = set(touched)
    # Constraints that read a swapped Param must be re-pushed after each swap; the persistent solver otherwise
    # keeps the stale coefficients. Find them once.
    affected = []
    for con in OptModel.component_data_objects(Constraint, active=True):
        for expr in (con.body, con.lower, con.upper):
            if expr is not None and any(p.parent_component().name in names
                                        for p in identify_mutable_parameters(expr)):
                affected.append(con)
                break
    objective = next(OptModel.component_data_objects(Objective, active=True))
    obj_touched = any(p.parent_component().name in names
                      for p in identify_mutable_parameters(objective.expr))

    # Default = BARRIER on every overlay: reliable, and the saving comes purely from not re-exporting the
    # resident model. Warm dual simplex is a DEEPER opt-in (OTEPES_WARM_RESOLVE_SIMPLEX) because on this LP
    # class it is (a) erratic — the same step can take 1 s or >200 s on pivot luck — and (b) direction-wrong
    # for objective (cost) overlays, where the basis goes dual-infeasible and dual simplex stalls. It only
    # helps for small RHS/bound overlays, and even then needs the time-cap + barrier fallback below.
    use_simplex = simplex_enabled()

    Solver = SolverFactory("gurobi_persistent")
    Solver.set_instance(OptModel)
    Solver.set_gurobi_param("OutputFlag", 1 if tee else 0)
    cap = cap_seconds()

    results = []
    for i, ov in enumerate(overlays):
        for name, values in baseline.items():
            getattr(OptModel, name).store_values(values)
        for name, values in ov.items():
            getattr(OptModel, name).store_values(values)
        for con in affected:
            Solver.remove_constraint(con)
            Solver.add_constraint(con)                   # re-reads the swapped Param
        if obj_touched:
            Solver.set_objective(objective)
        if use_simplex and i > 0:
            Solver.set_gurobi_param("Method", 1)         # dual simplex, warm from the retained basis
            Solver.set_gurobi_param("TimeLimit", cap)
        else:
            Solver.set_gurobi_param("Method", 2)         # barrier (reliable default)
            Solver.set_gurobi_param("Crossover", 1 if use_simplex else -1)  # basis only needed to seed simplex
            Solver.set_gurobi_param("TimeLimit", _FULL_TIME_LIMIT)
        SolverResults = Solver.solve()
        if use_simplex and i > 0 and SolverResults.solver.termination_condition == TerminationCondition.maxTimeLimit:
            print("warm simplex stalled on overlay", i, "; falling back to barrier")
            Solver.set_gurobi_param("Method", 2)
            Solver.set_gurobi_param("Crossover", -1)
            Solver.set_gurobi_param("TimeLimit", _FULL_TIME_LIMIT)
            SolverResults = Solver.solve()
        tc = SolverResults.solver.termination_condition
        cost = OptModel.vTotalSCost() if tc == TerminationCondition.optimal else None
        results.append({"overlay": i, "status": str(tc), "total_cost_meur": cost})
    return results
