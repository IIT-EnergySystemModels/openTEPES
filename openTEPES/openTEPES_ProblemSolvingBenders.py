"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026
openTEPES.openTEPES_ProblemSolvingBenders — classical L-shaped Benders decomposition for transmission expansion.

Master problem
--------------

* Decision variables: ``x[p, ni, nf, cc]`` for every candidate transmission line in ``mTEPES.plc`` (the
  set of ``(Period, InitialNode, FinalNode, Circuit)`` tuples whose ``FixedInvestmentCost > 0``).
* Recourse variable ``theta`` approximates the **full** system total cost ``eTotalSCost`` (operation +
  investment) as a function of master decisions. Investment cost is therefore baked into the cuts; the
  master objective is simply ``min theta``.
* Benders cuts accumulated across iterations: ``theta >= eTotalSCost(x*) + dual^T (x - x*)`` where the
  dual is the multiplier on the subproblem's fixing constraint at ``x = x*``.

Subproblem
----------

The full openTEPES model with every candidate ``vNetworkInvest`` pinned to the master's decision via an
explicit equality constraint ``vNetworkInvest[k] == benders_x[k]`` (mutable ``Param`` ``benders_x``).
The dual on this constraint is exactly ``∂(eTotalSCost) / ∂(vNetworkInvest[k])`` at the current master
solution — which is what the Benders cut needs. Pyomo's ``rc`` Suffix on ``Var.fix()`` is not reliably
populated by every solver (HiGHS in particular leaves it empty), so the explicit-constraint approach is
solver-portable.

Scope
-----

This is a deliberately minimal driver — single deterministic case, no multi-cut, no trust region, no
binary investments (subproblem must be LP for the duals to be valid). Intended as a **compatibility guard**
for the layered-architecture restructure: every future refactor must keep this Benders loop converging to
the joint-LP optimum on the bundled CI cases. The full Benders / sector decomposition driver with stochastic
support is RFC PR #9 (``solver/decomposition/``).

Validation: on the bundled ``9n`` case (one candidate line, single-stage 7-day fixture), ``lshaped()``
converges in ≤ 10 iterations to the joint-LP total cost within 1e-4 relative tolerance.
"""
from __future__ import annotations

import math
import time

import pyomo.environ as pyo
from pyomo.opt import SolverFactory


_BENDERS_PARAM_ATTR = "_benders_x_param"
_BENDERS_CONSTR_ATTR = "_benders_fix_constr"


def _attach_fixing_constraints(mTEPES, candidates: list[tuple]) -> tuple:
    """Add (or replace) the mutable Param + explicit equality constraint that pin each candidate
    ``vNetworkInvest`` to the master's current decision. Returns ``(param, constr)`` references."""
    # Remove previous attachments if present so the function is idempotent across reruns.
    for attr in (_BENDERS_CONSTR_ATTR, _BENDERS_PARAM_ATTR):
        if hasattr(mTEPES, attr):
            mTEPES.del_component(getattr(mTEPES, attr))

    candidates_set = pyo.Set(initialize=candidates, dimen=4)
    mTEPES.add_component("_benders_candidates", candidates_set)

    param = pyo.Param(candidates_set, mutable=True, initialize=0.0, within=pyo.Reals)
    mTEPES.add_component(_BENDERS_PARAM_ATTR, param)

    def _fix_rule(m, *k):
        return m.vNetworkInvest[k] == getattr(m, _BENDERS_PARAM_ATTR)[k]

    constr = pyo.Constraint(candidates_set, rule=_fix_rule)
    mTEPES.add_component(_BENDERS_CONSTR_ATTR, constr)

    if not hasattr(mTEPES, "dual"):
        mTEPES.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    return param, constr


def _detach_fixing_constraints(mTEPES) -> None:
    """Remove the Benders auxiliary Param/Constraint/Set so mTEPES is left as we found it."""
    for attr in (_BENDERS_CONSTR_ATTR, _BENDERS_PARAM_ATTR, "_benders_candidates"):
        if hasattr(mTEPES, attr):
            mTEPES.del_component(getattr(mTEPES, attr))


def lshaped(mTEPES, solver_name: str = "highs", max_iter: int = 20, tol: float = 1e-4,
            verbose: bool = False) -> dict:
    """Run classical L-shaped Benders on an already-built openTEPES model.

    Parameters
    ----------
    mTEPES : pyomo.ConcreteModel
        Fully built openTEPES model (joint-LP solve optional — the driver unfixes every candidate
        ``vNetworkInvest`` before starting and discards any prior solution).
    solver_name : str
        Pyomo solver name used for both master and subproblem. Default ``"highs"``.
    max_iter : int
        Hard cap on Benders iterations.
    tol : float
        Relative convergence tolerance: stop when ``(UB - LB) / max(|LB|, 1)`` ≤ ``tol``.
    verbose : bool
        If ``True``, print one line per iteration with LB, UB, gap, and master solution.

    Returns
    -------
    dict
        Keys: ``total_cost`` (UB at termination), ``master_decisions`` (dict keyed on
        ``(p, ni, nf, cc)``), ``num_iterations`` (iterations performed),
        ``converged`` (bool — True iff the convergence test triggered before ``max_iter``),
        ``history`` (list of per-iteration ``(it, LB, UB, gap, sub_cost)`` tuples),
        ``wall_clock_s`` (total seconds).
    """
    t0 = time.time()

    candidates = list(mTEPES.plc)
    if not candidates:
        raise ValueError(
            "openTEPES.openTEPES_ProblemSolvingBenders.lshaped requires at least one candidate transmission line "
            "(mTEPES.plc is empty — no row in oT_Data_Network has FixedInvestmentCost > 0)."
        )

    bounds: dict[tuple, tuple[float, float]] = {}
    for (p, ni, nf, cc) in candidates:
        lo = float(pyo.value(mTEPES.pNetLoInvest[ni, nf, cc]))
        up = float(pyo.value(mTEPES.pNetUpInvest[ni, nf, cc]))
        bounds[(p, ni, nf, cc)] = (lo, up)

    # Reset every candidate investment var so the joint-LP solution does not leak into the master.
    for k in candidates:
        if mTEPES.vNetworkInvest[k].fixed:
            mTEPES.vNetworkInvest[k].unfix()

    # Attach the fixing Param + equality constraint that the subproblem uses to receive master decisions.
    bd_param, bd_constr = _attach_fixing_constraints(mTEPES, candidates)

    # ----- Build the master -----

    master = pyo.ConcreteModel("benders_master")
    master.CANDIDATES = pyo.Set(initialize=candidates, dimen=4)
    master.x = pyo.Var(master.CANDIDATES, bounds=lambda m, *k: bounds[k], initialize=lambda m, *k: bounds[k][0])
    master.theta = pyo.Var(domain=pyo.Reals, initialize=0.0)
    # Initial finite lower bound on theta; once the first cut lands it becomes inactive.
    master.theta.setlb(-1.0e9)
    master.cuts = pyo.ConstraintList()
    master.obj = pyo.Objective(expr=master.theta, sense=pyo.minimize)

    solver = SolverFactory(solver_name)

    # ----- L-shaped loop -----

    UB = math.inf
    LB = -math.inf
    history: list[tuple] = []
    last_x: dict[tuple, float] = {k: 0.0 for k in candidates}

    try:
        for it in range(1, max_iter + 1):
            # ---- Solve master ----
            master_result = solver.solve(master, tee=False)
            if str(master_result.solver.termination_condition) != "optimal":
                raise RuntimeError(
                    f"Benders master infeasible / non-optimal at iter {it}: "
                    f"{master_result.solver.termination_condition}"
                )
            LB = float(pyo.value(master.obj))
            x_sol = {k: float(pyo.value(master.x[k])) for k in candidates}

            # ---- Push master decisions into the subproblem Param and solve ----
            for k in candidates:
                bd_param[k] = x_sol[k]

            sub_result = solver.solve(mTEPES, tee=False)
            if str(sub_result.solver.termination_condition) != "optimal":
                raise RuntimeError(
                    f"Benders subproblem infeasible at iter {it}: "
                    f"{sub_result.solver.termination_condition}"
                )

            sub_total_cost = float(pyo.value(mTEPES.eTotalSCost))

            # ---- Read duals on the fixing constraint (one per candidate) ----
            duals: dict[tuple, float] = {}
            for k in candidates:
                duals[k] = float(mTEPES.dual.get(bd_constr[k], 0.0))

            # ---- Update UB and check convergence ----
            if sub_total_cost < UB:
                UB = sub_total_cost
            gap = UB - LB
            history.append((it, LB, UB, gap, sub_total_cost))
            if verbose:
                print(f"  Benders iter {it}: LB={LB:.6f}, UB={UB:.6f}, gap={gap:.2e}, x={x_sol}")

            last_x = x_sol
            if abs(gap) <= tol * max(abs(LB), 1.0):
                return {
                    "total_cost":       UB,
                    "master_decisions": last_x,
                    "num_iterations":   it,
                    "converged":        True,
                    "history":          history,
                    "wall_clock_s":     time.time() - t0,
                }

            # ---- Add Benders optimality cut to master ----
            # theta >= sub_total_cost(x*) + sum_k dual[k] * (x[k] - x*[k])
            cut_expr = sub_total_cost + sum(duals[k] * (master.x[k] - x_sol[k]) for k in candidates)
            master.cuts.add(master.theta >= cut_expr)

    finally:
        _detach_fixing_constraints(mTEPES)

    return {
        "total_cost":       UB,
        "master_decisions": last_x,
        "num_iterations":   max_iter,
        "converged":        False,
        "history":          history,
        "wall_clock_s":     time.time() - t0,
    }
