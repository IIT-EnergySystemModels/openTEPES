"""Regression test for the heat investment formulation typo.

`openTEPES_ModelFormulation.py:135` looked up `vTotalHeatFCost` but the
variable is `vTotalFHeatCost` (defined at `openTEPES_InputData.py:1823`,
used correctly at line 52 and `OutputResults.py:1566`). The bug was
dormant because no in-tree case had a candidate heat pipe — the
`InvestmentHeatModelFormulation` call at `openTEPES.py:207-208` is
gated by `mTEPES.pIndHeat and mTEPES.hc`.

This test builds the smallest Pyomo state that exercises the heat
investment constraint and asserts the formulation completes without
an AttributeError.
"""
from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Param,
    Set,
    Var,
)

from openTEPES.openTEPES_ModelFormulation import InvestmentHeatModelFormulation


def _build_minimal_heat_invest_model() -> ConcreteModel:
    """Smallest model that triggers `InvestmentHeatModelFormulation`.

    Required attributes (mirrors what `InputData` would build for a case
    with `pIndHeat=1` and at least one candidate heat pipe):

      * `m.p`               — period set
      * `m.hc`              — candidate heat pipes (dimen=3)
      * `m.phc`             — (period, ni, nf, cc) tuples (dimen=4)
      * `m.pHeatPipeFixedCost` — Param indexed by `hc`
      * `m.vHeatPipeInvest` / `vHeatPipeInvPer` — investment decision Vars
      * `m.vTotalFHeatCost` — the variable whose name the buggy rule misspelled
    """
    m = ConcreteModel()
    m.p = Set(initialize=[2030], ordered=True)
    pipe = ("Node_A", "Node_B", "hc1")
    m.hc = Set(initialize=[pipe], dimen=3)
    m.phc = Set(initialize=[(2030,) + pipe], dimen=4)
    m.pHeatPipeFixedCost = Param(
        m.hc, initialize={pipe: 0.5}, within=NonNegativeReals
    )
    m.vHeatPipeInvest = Var(m.phc, within=NonNegativeReals)
    m.vHeatPipeInvPer = Var(m.phc, within=NonNegativeReals)
    m.vTotalFHeatCost = Var(m.p, within=NonNegativeReals)
    return m


def test_heat_investment_constraint_constructs():
    """Build a minimal heat investment model and confirm the constraint
    is constructed without an AttributeError on a misspelled Var name.

    Pre-fix behaviour: `InvestmentHeatModelFormulation` raises
        AttributeError: 'ConcreteModel' object has no attribute
        'vTotalHeatFCost'. Did you mean: 'vTotalFHeatCost'?
    Post-fix behaviour: the constraint exists and is indexed by m.p.
    """
    m = _build_minimal_heat_invest_model()

    # Same calling convention as openTEPES.py:208 — (OptModel, mTEPES, ...).
    InvestmentHeatModelFormulation(m, m, pIndLogConsole=0)

    assert hasattr(m, "eTotalFHeatCost"), (
        "eTotalFHeatCost constraint missing — investment formulation did not run"
    )
    assert isinstance(m.eTotalFHeatCost, Constraint), (
        "eTotalFHeatCost is not a Constraint object"
    )
    assert 2030 in m.eTotalFHeatCost, (
        "eTotalFHeatCost not indexed by the period set"
    )
