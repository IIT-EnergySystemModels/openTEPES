"""A HiPO solve that returns no solution is solved again with the method HiGHS chooses.

HiGHS 1.16's HiPO sometimes stops with "NaN detected" on a small LP, and Pyomo then raises
NoFeasibleSolutionError. These tests use a stand-in solver, so no HiGHS is needed.
"""
import pytest
from pyomo.contrib.solver.common.util import NoFeasibleSolutionError
from pyomo.environ import SolverFactory

from openTEPES.openTEPES_ProblemSolving import _solve_without_duals_if_unavailable


class _Solver:
    """Fails while the method is HiPO (or always, if told to) and records the method of every solve.

    It carries Pyomo's own HiGHS options object, because that object does not return set values through .get().
    """

    def __init__(self, method, always_fail=False):
        self.options = SolverFactory("highs").options
        self.options["solver"] = method
        self.always_fail = always_fail
        self.methods = []

    def solve(self, model, **kwargs):
        method = self.options["solver"] if "solver" in self.options else None
        self.methods.append(method)
        if self.always_fail or method == "hipo":
            raise NoFeasibleSolutionError()
        return "results"


def test_a_failed_hipo_solve_is_solved_again_with_choose():
    solver = _Solver("hipo")
    assert _solve_without_duals_if_unavailable(solver, object()) == "results"
    assert solver.methods == ["hipo", "choose"]
    assert solver.options["solver"] == "hipo"


def test_an_infeasible_model_still_raises():
    solver = _Solver("hipo", always_fail=True)
    with pytest.raises(NoFeasibleSolutionError):
        _solve_without_duals_if_unavailable(solver, object())
    assert solver.methods == ["hipo", "choose"]
    assert solver.options["solver"] == "hipo"


def test_other_methods_are_not_solved_again():
    solver = _Solver("choose", always_fail=True)
    with pytest.raises(NoFeasibleSolutionError):
        _solve_without_duals_if_unavailable(solver, object())
    assert solver.methods == ["choose"]


def test_a_solver_with_no_method_option_is_not_solved_again():
    solver = _Solver("choose", always_fail=True)
    solver.options = SolverFactory("highs").options
    with pytest.raises(NoFeasibleSolutionError):
        _solve_without_duals_if_unavailable(solver, object())
    assert solver.methods == [None]
