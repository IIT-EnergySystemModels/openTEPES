"""
openTEPES.oT_Solver.DualExtraction — fix-and-resolve pass that recovers shadow prices on a MIP solution.

After an initial MIP solve, ``fix_for_duals()`` fixes every binary/integer variable to its optimal value and
relaxes its domain to ``UnitInterval`` so the model becomes a pure LP; ``ProblemSolving`` then re-solves it
with a ``dual`` Suffix attached, and ``collect_duals()`` walks every active constraint to copy the dual values
into ``mTEPES.pDuals`` for downstream consumption by ``MarginalResults`` / ``EconomicResults`` (LMPs, water
values, H2 marginals, …).

The fixing of continuous investment variables (lines 172-192 of the original ``ProblemSolving.py``) is
preserved exactly — those decisions are pinned even on a fully-LP case, ensuring the second solve cannot
revise the investment plan.

``NoRepetition`` controls scope: when set, every binary var across every ``(p, sc)`` is fixed; otherwise only
the current ``(p, sc)`` block is fixed (the rest stays as it was at the end of the previous stage solve).
"""
from __future__ import annotations

import pyomo.environ as pyo
from pyomo.environ import UnitInterval


def fix_for_duals(OptModel, mTEPES, p, sc) -> int:
    """Fix binary/integer vars + continuous investment vars in preparation for the LP-relaxation re-solve.

    Returns the number of newly-fixed binary/integer vars. If 0, no re-solve is needed (the initial solve was
    already an LP and produced clean duals); the caller should skip the resolve pass entirely.
    """
    nUnfixedVars = 0
    if mTEPES.NoRepetition == 1:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed() and var.value is not None:
                var.fixed  = True
                var.domain = UnitInterval
                nUnfixedVars += 1
    else:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if (not var.is_continuous() and not var.is_fixed() and var.value is not None
                    and var.index()[0] == p and var.index()[1] == sc):
                var.fixed  = True
                var.domain = UnitInterval
                nUnfixedVars += 1

    # Continuous investment decisions are fixed to their optimal values regardless of NoRepetition; without
    # this the LP re-solve could revisit the investment plan, which would distort the duals on the operation
    # constraints.
    for eb in mTEPES.eb:
        if (p, eb) in mTEPES.peb:
            OptModel.vGenerationInvest[p, eb].fix(OptModel.vGenerationInvest[p, eb]())
    for gd in mTEPES.gd:
        if (p, gd) in mTEPES.pgd:
            OptModel.vGenerationRetire[p, gd].fix(OptModel.vGenerationRetire[p, gd]())
    for ni, nf, cc in mTEPES.lc:
        if (p, ni, nf, cc) in mTEPES.plc:
            OptModel.vNetworkInvest[p, ni, nf, cc].fix(OptModel.vNetworkInvest[p, ni, nf, cc]())
    if mTEPES.pIndHydroTopology:
        for rc in mTEPES.rn:
            if (p, rc) in mTEPES.prc:
                OptModel.vReservoirInvest[p, rc].fix(OptModel.vReservoirInvest[p, rc]())
    if mTEPES.pIndHydrogen:
        for ni, nf, cc in mTEPES.pc:
            if (p, ni, nf, cc) in mTEPES.ppc:
                OptModel.vH2PipeInvest[p, ni, nf, cc].fix(OptModel.vH2PipeInvest[p, ni, nf, cc]())
    if mTEPES.pIndHeat:
        for ni, nf, cc in mTEPES.hc:
            if (p, ni, nf, cc) in mTEPES.phc:
                OptModel.vHeatPipeInvest[p, ni, nf, cc].fix(OptModel.vHeatPipeInvest[p, ni, nf, cc]())

    return nUnfixedVars


def collect_duals(OptModel, mTEPES) -> None:
    """Walk every active constraint in ``OptModel`` and copy its dual value into ``mTEPES.pDuals``.

    Keys are formatted as ``"<ConstraintName><index>"`` to match the historical contract that
    ``MarginalResults`` / ``EconomicResults`` rely on. The ``dual`` Suffix is deleted from ``OptModel`` once
    the duals have been collected so the next iteration of the stage loop starts with a clean slate.
    """
    pDuals = {}
    for con in OptModel.component_objects(pyo.Constraint, active=True):
        if con.is_indexed():
            for index in con:
                pDuals[str(con.name) + str(index)] = OptModel.dual[con[index]]
    mTEPES.pDuals.update(pDuals)
    OptModel.del_component(OptModel.dual)
