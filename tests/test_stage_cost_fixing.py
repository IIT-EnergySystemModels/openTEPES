from pyomo.environ import ConcreteModel, Var

from openTEPES.openTEPES_ProblemSolvingDualExtraction import (
    fix_stage_costs,
    unfix_for_duals,
    unfix_stage_costs,
)


def test_unfix_stage_costs_releases_only_variables_it_fixed():
    model = ConcreteModel()
    model.cost = Var([1, 2], initialize={1: 10, 2: 20})
    model.cost[2].fix(20)

    fix_stage_costs(model, model.cost.values())

    assert all(var.fixed for var in model.cost.values())
    assert unfix_stage_costs(model) == 1
    assert not model.cost[1].fixed
    assert model.cost[2].fixed


def test_unfix_for_duals_also_releases_stage_costs():
    model = ConcreteModel()
    model.cost = Var(initialize=10)
    fix_stage_costs(model, [model.cost])

    assert unfix_for_duals(model) == 1
    assert not model.cost.fixed
