"""The run status file reports what the solver said, and a solver limit is not reported as an infeasible problem.

No solver is needed: the solve call is replaced by one that returns a chosen termination condition.
"""
from types import SimpleNamespace

import pyomo.environ as pyo
import pytest
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
