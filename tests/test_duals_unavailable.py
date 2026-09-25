"""A solve that finds an optimum but cannot return its duals continues without them.

Gurobi solves a quadratically constrained model with the barrier method and computes the duals from the KKT system
afterwards (QCPDual). When the barrier solution is not accurate enough for that it reports the optimum and no duals,
and gurobipy raises "Unable to retrieve attribute 'Pi'" when Pyomo asks for them. On a 695-busbar AC case that ended
the run with an optimal solution in hand. These tests use a stand-in solver, so none of them needs Gurobi.
"""
import pytest
from pyomo.environ import ConcreteModel, Constraint, Suffix, Var

from openTEPES.openTEPES_ProblemSolving import _solve_without_duals_if_unavailable
from openTEPES.openTEPES_ProblemSolvingDualExtraction import collect_duals


class _Solver:
    """Raises the given error on the first solve while the model carries a dual Suffix, then succeeds."""

    def __init__(self, error):
        self.error, self.calls, self.had_suffix = error, 0, []

    def solve(self, model, **kwargs):
        self.calls += 1
        self.had_suffix.append(hasattr(model, "dual"))
        if self.calls == 1 and self.error is not None:
            raise self.error
        return "results"


def _model():
    m = ConcreteModel()
    m.x = Var(bounds=(0, 1))
    m.c = Constraint(expr=m.x >= 0)
    m.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
    return m


@pytest.mark.parametrize("attribute", ["Pi", "QCPi"])
def test_an_optimum_without_duals_is_solved_again_without_asking_for_them(attribute):
    m, solver = _model(), _Solver(RuntimeError(f"Unable to retrieve attribute '{attribute}'"))
    assert _solve_without_duals_if_unavailable(solver, m, tee=False) == "results"
    assert solver.had_suffix == [True, False], "the second solve must not ask for duals"
    assert not hasattr(m, "dual")


def test_any_other_solver_error_is_raised():
    m, solver = _model(), _Solver(RuntimeError("Model too large for size-limited license"))
    with pytest.raises(RuntimeError, match="size-limited"):
        _solve_without_duals_if_unavailable(solver, m)
    assert hasattr(m, "dual"), "an error that is not about the duals leaves the model as it was"


def test_the_dual_error_is_raised_when_no_duals_were_asked_for():
    m, solver = _model(), _Solver(RuntimeError("Unable to retrieve attribute 'Pi'"))
    m.del_component(m.dual)
    with pytest.raises(RuntimeError, match="'Pi'"):
        _solve_without_duals_if_unavailable(solver, m)


def test_a_solve_that_succeeds_is_solved_once():
    m, solver = _model(), _Solver(None)
    _solve_without_duals_if_unavailable(solver, m)
    assert solver.calls == 1 and hasattr(m, "dual")


def test_no_duals_to_collect_leaves_the_prices_empty():
    class _Holder:
        pDuals = {}
    m = _model()
    m.del_component(m.dual)
    holder = _Holder()
    collect_duals(m, holder)
    assert holder.pDuals == {}
