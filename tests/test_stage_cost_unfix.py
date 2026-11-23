from pyomo.environ import ConcreteModel, Var

from openTEPES.openTEPES_ProblemSolvingDualExtraction import unfix_stage_costs


def test_unfix_stage_costs_releases_saved_costs_only():
    model = ConcreteModel()
    model.vTotalGCost = Var([0, 1])
    model.vTotalCCost = Var()
    model.vNetworkInvest = Var()
    model.vTotalGCost[0].fix(1)
    model.vTotalCCost.fix(2)
    model.vNetworkInvest.fix(3)

    assert unfix_stage_costs(model) == 2
    assert not model.vTotalGCost[0].fixed
    assert not model.vTotalCCost.fixed
    assert model.vNetworkInvest.fixed
