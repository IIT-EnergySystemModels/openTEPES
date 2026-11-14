"""The LP method is barrier unless a persistent solver re-solves an instance it already holds.

The operation stage loop passes ncall = p*sc*st, so ncall exceeds 1 from the second period on even
when each solve starts from scratch. Read as a warm restart, it sent those periods to Gurobi's
automatic method (concurrent), whose result changes from run to run.
"""
import pytest

from openTEPES.openTEPES_ProblemSolvingTuning import apply_solver_options


class _Options:
    def __init__(self):
        self.options = {}


class _Persistent:
    def __init__(self):
        self.params = {}

    def set_gurobi_param(self, name, value):
        self.params[name] = value


@pytest.mark.parametrize("name", ["gurobi", "gurobi_direct"])
@pytest.mark.parametrize("ncall", [1, 2, 7])
def test_one_shot_gurobi_always_uses_barrier(name, ncall):
    solver = _Options()
    apply_solver_options(solver, name, "unused.log", ncall)
    assert solver.options["Method"] == 2


@pytest.mark.parametrize("ncall", [1, 2, 7])
def test_cplex_always_uses_barrier(ncall):
    solver = _Options()
    apply_solver_options(solver, "cplex", "unused.log", ncall)
    assert solver.options["LPMethod"] == 4


@pytest.mark.parametrize("ncall, method", [(1, 2), (2, -1)])
def test_appsi_gurobi_reuses_the_basis_on_a_re_solve(ncall, method):
    solver = _Options()
    apply_solver_options(solver, "appsi_gurobi", "unused.log", ncall)
    assert solver.options["Method"] == method


@pytest.mark.parametrize("ncall, method", [(1, 2), (2, -1)])
def test_gurobi_persistent_reuses_the_basis_on_a_re_solve(ncall, method):
    solver = _Persistent()
    apply_solver_options(solver, "gurobi_persistent", "unused.log", ncall)
    assert solver.params["Method"] == method


@pytest.mark.parametrize("value", [None, "", "  "])
def test_highs_uses_hipo_by_default(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("OTEPES_HIGHS_SOLVER", raising=False)
    else:
        monkeypatch.setenv("OTEPES_HIGHS_SOLVER", value)
    solver = _Options()
    apply_solver_options(solver, "highs", "unused.log", 1)
    assert solver.options["solver"] == "hipo"


def test_the_highs_method_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("OTEPES_HIGHS_SOLVER", "choose")
    solver = _Options()
    apply_solver_options(solver, "highs", "unused.log", 1)
    assert solver.options["solver"] == "choose"
