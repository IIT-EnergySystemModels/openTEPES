"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 16, 2026
openTEPES.openTEPES_ProblemSolvingDualExtraction — fix-and-resolve pass that recovers shadow prices on a MIP solution.

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

``fix_for_duals`` records what it changed on the model, so ``unfix_for_duals`` can put it back. A Mode C
sweep needs that: the fixed plan is right for reading duals but wrong for re-optimising.
"""
from __future__ import annotations

import pyomo.environ as pyo
from pyomo.environ import UnitInterval

# What fix_for_duals changed, so unfix_for_duals can put it back: keyed by id() because a Pyomo variable
# builds an expression from ==, which makes it unusable as a dict key. Values are (var, prior domain) for
# the relaxed binaries and (var, prior fixed flag) for the investments.
_FIX_REGISTRY = "_pDualFixRelaxed"
_INV_REGISTRY = "_pDualFixInvest"


def _registry(OptModel, name) -> dict:
    reg = getattr(OptModel, name, None)
    if reg is None:
        reg = {}
        setattr(OptModel, name, reg)
    return reg


def fix_for_duals(OptModel, mTEPES, p, sc) -> int:
    """Fix binary/integer vars + continuous investment vars in preparation for the LP-relaxation re-solve.

    Returns the number of newly-fixed binary/integer vars. If 0, no re-solve is needed (the initial solve was
    already an LP and produced clean duals); the caller should skip the resolve pass entirely.
    """
    nUnfixedVars = 0
    relaxed = _registry(OptModel, _FIX_REGISTRY)
    if mTEPES.NoRepetition == 1:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed() and var.value is not None:
                relaxed.setdefault(id(var), (var, var.domain))
                var.fixed  = True
                var.domain = UnitInterval
                nUnfixedVars += 1
    else:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if (not var.is_continuous() and not var.is_fixed() and var.value is not None
                    and var.index()[0] == p and var.index()[1] == sc):
                relaxed.setdefault(id(var), (var, var.domain))
                var.fixed  = True
                var.domain = UnitInterval
                nUnfixedVars += 1

    # Continuous investment decisions are fixed to their optimal values regardless of NoRepetition; without
    # this the LP re-solve could revisit the investment plan, which would distort the duals on the operation
    # constraints.
    invest = _registry(OptModel, _INV_REGISTRY)

    def _fix_investment(var):
        # Record whether it was already fixed before this pass: unfix_for_duals must release only what was
        # pinned here, and leave a decision the case itself fixed alone.
        invest.setdefault(id(var), (var, var.fixed))
        var.fix(var())

    for eb in mTEPES.eb:
        if (p, eb) in mTEPES.peb:
            _fix_investment(OptModel.vGenerationInvest[p, eb])
    for gd in mTEPES.gd:
        if (p, gd) in mTEPES.pgd:
            _fix_investment(OptModel.vGenerationRetire[p, gd])
    for ni, nf, cc in mTEPES.lc:
        if (p, ni, nf, cc) in mTEPES.plc:
            _fix_investment(OptModel.vNetworkInvest[p, ni, nf, cc])
    if mTEPES.pIndHydroTopology:
        for rc in mTEPES.rn:
            if (p, rc) in mTEPES.prc:
                _fix_investment(OptModel.vReservoirInvest[p, rc])
    if mTEPES.pIndHydrogen:
        for ni, nf, cc in mTEPES.pc:
            if (p, ni, nf, cc) in mTEPES.ppc:
                _fix_investment(OptModel.vH2PipeInvest[p, ni, nf, cc])
    if mTEPES.pIndHeat:
        for ni, nf, cc in mTEPES.hc:
            if (p, ni, nf, cc) in mTEPES.phc:
                _fix_investment(OptModel.vHeatPipeInvest[p, ni, nf, cc])

    return nUnfixedVars


def unfix_for_duals(OptModel) -> int:
    """Undo ``fix_for_duals``: restore the relaxed domains and release what it fixed. Returns the count.

    Only what ``fix_for_duals`` changed is touched, so a decision the case itself fixed stays fixed. Safe to
    call on a model that was never solved, where it does nothing.
    """
    n = 0
    for var, prior_domain in _registry(OptModel, _FIX_REGISTRY).values():
        var.fixed  = False
        var.domain = prior_domain
        n += 1
    for var, was_fixed in _registry(OptModel, _INV_REGISTRY).values():
        if not was_fixed:
            var.unfix()
            n += 1
    _registry(OptModel, _FIX_REGISTRY).clear()
    _registry(OptModel, _INV_REGISTRY).clear()
    return n


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
