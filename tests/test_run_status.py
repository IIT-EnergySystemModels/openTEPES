"""The run status file reports what the solver said, and a solver limit is not reported as an infeasible problem.

No solver is needed: the solve call is replaced by one that returns a chosen termination condition.
"""
from types import SimpleNamespace

import pyomo.environ as pyo
import pytest
from pyomo.contrib.solver.common.util import NoFeasibleSolutionError
from pyomo.opt import TerminationCondition

import openTEPES.openTEPES_ProblemSolving as oPS
from openTEPES.openTEPES import RunStatus


def test_status_is_optimal_only_if_every_solve_was():
    assert RunStatus(["optimal", "optimal"]) == "optimal"
    assert RunStatus(["optimal", "feasible", "optimal"]) == "feasible"
    assert RunStatus([]) == "unknown"


def _stop_with(monkeypatch, pCondition):
    """Make ProblemSolving see a solver that ends with ``pCondition``."""
    pResults = SimpleNamespace(solver=SimpleNamespace(termination_condition=pCondition))
    monkeypatch.setattr(oPS, "setup_solver", lambda *args: None)
    monkeypatch.setattr(oPS, "apply_solver_options", lambda *args: {})
    monkeypatch.setattr(oPS, "_solve_without_duals_if_unavailable", lambda *args, **kwargs: pResults)
    monkeypatch.setattr(oPS, "fallback_if_stalled", lambda Solver, OptModel, SolverName, ncall, SolverResults, kwargs: SolverResults)


def _solve(tmp_path, mTEPES=None):
    OptModel = pyo.ConcreteModel()
    OptModel.x = pyo.Var(bounds=(0, 1))
    mTEPES = mTEPES or SimpleNamespace(pIndACPowerFlow=lambda: 0)
    (tmp_path / "case").mkdir()
    oPS.ProblemSolving(str(tmp_path), "case", "highs", OptModel, mTEPES, 0, 2030, "sc01", "st1", 1)


@pytest.mark.parametrize("pCondition, pLimit", [(TerminationCondition.maxTimeLimit, "time limit"),
                                                (TerminationCondition.maxIterations, "iteration limit")])
def test_a_solver_limit_is_not_called_infeasible(monkeypatch, tmp_path, pCondition, pLimit):
    _stop_with(monkeypatch, pCondition)
    with pytest.raises(ValueError, match=pLimit) as pError:
        _solve(tmp_path)
    assert "Problem infeasible" not in str(pError.value)
    assert not list((tmp_path / "case").glob("openTEPES_infeasibilities_*.log"))


def test_an_infeasible_problem_is_still_called_infeasible(monkeypatch, tmp_path):
    _stop_with(monkeypatch, TerminationCondition.infeasible)
    mTEPES = SimpleNamespace(pIndACPowerFlow=lambda: 0)
    with pytest.raises(ValueError, match="Problem infeasible"):
        _solve(tmp_path, mTEPES)
    assert mTEPES.pTerminationConditions == ["infeasible"]


class _HighsModel:
    """Stand-in for the highspy model Pyomo keeps on the solver, reporting the status HiGHS ended with."""

    def __init__(self, name):
        self.name = name

    def getModelStatus(self):
        return self


def _raise_on_solve(monkeypatch, pError, pHighsStatus=None):
    """Make the solve raise ``pError``, as Pyomo does when it has no solution to load."""
    pSolver = SimpleNamespace(_solver_model=_HighsModel(pHighsStatus)) if pHighsStatus else SimpleNamespace()
    monkeypatch.setattr(oPS, "setup_solver", lambda *args: pSolver)
    monkeypatch.setattr(oPS, "apply_solver_options", lambda *args: {})

    def _solve(*args, **kwargs):
        raise pError
    monkeypatch.setattr(oPS, "_solve_without_duals_if_unavailable", _solve)


@pytest.mark.parametrize("pStatus, pLimit", [("kTimeLimit", "time limit"), ("kIterationLimit", "iteration limit")])
def test_a_highs_limit_without_a_feasible_point_names_the_limit(monkeypatch, tmp_path, pStatus, pLimit):
    _raise_on_solve(monkeypatch, NoFeasibleSolutionError(), pStatus)
    with pytest.raises(ValueError, match=pLimit):
        _solve(tmp_path)
    assert not list((tmp_path / "case").glob("openTEPES_infeasibilities_*.log"))


def test_an_infeasible_problem_on_highs_logs_the_infeasible_constraints(monkeypatch, tmp_path):
    _raise_on_solve(monkeypatch, NoFeasibleSolutionError(), "kInfeasible")
    pLogged = []
    monkeypatch.setattr(oPS, "log_infeasible_constraints", lambda OptModel, **kwargs: pLogged.append(OptModel))
    with pytest.raises(ValueError, match="Problem infeasible for"):
        _solve(tmp_path)
    assert len(pLogged) == 1


def test_a_gurobi_shell_abort_is_not_called_infeasible(monkeypatch, tmp_path):
    _raise_on_solve(monkeypatch, ValueError("Cannot load a SolverResults object with bad status: aborted"))
    with pytest.raises(ValueError, match="before it found a feasible solution") as pError:
        _solve(tmp_path)
    assert "Problem infeasible" not in str(pError.value)


@pytest.mark.parametrize("pError, pHighsStatus", [(NoFeasibleSolutionError(), "kSolveError"),
                                                  (NoFeasibleSolutionError(), None),
                                                  (ValueError("some other error"), None)])
def test_any_other_error_is_raised_unchanged(monkeypatch, tmp_path, pError, pHighsStatus):
    _raise_on_solve(monkeypatch, pError, pHighsStatus)
    with pytest.raises(type(pError)) as pRaised:
        _solve(tmp_path)
    assert pRaised.value is pError
