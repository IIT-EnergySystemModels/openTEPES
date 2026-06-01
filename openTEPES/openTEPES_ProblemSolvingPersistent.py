"""
openTEPES.openTEPES_ProblemSolvingPersistent — persistent-solver lifecycle for ``appsi_gurobi`` and ``gurobi_persistent``.

The ``ncall`` counter in ``ProblemSolving`` distinguishes the first solve of a given Pyomo instance (which must
``set_instance`` once) from subsequent solves in the stage loop (which only need to update vars / params /
constraints). This module owns the bookkeeping flags ``_appsi_gurobi_initialized`` /
``_gurobi_persistent_initialized`` and the ``update_config`` toggles that control what gets pushed into the
persistent Gurobi instance between solves.

Non-persistent solvers (``gurobi``, ``gurobi_direct``, ``cplex``, ``highs``, ``gams``, ``glpk``) bypass this layer
entirely — ``setup_solver()`` just calls ``SolverFactory(SolverName)`` and clears any stale log file.
"""
from __future__ import annotations

import os

import pyomo.environ as pyo
from pyomo.opt import SolverFactory


def setup_solver(OptModel, SolverName: str, FileName: str, ncall: int, mTEPES):
    """Return the (possibly cached) solver instance for this OptModel + SolverName combination.

    For ``appsi_gurobi`` / ``gurobi_persistent`` the solver is attached to ``OptModel`` on first call and
    re-used across stage-loop iterations; for everything else a fresh ``SolverFactory`` handle is built and the
    stale log file (if any) is removed so each solve writes to a clean file.
    """
    if SolverName != "appsi_gurobi" and SolverName != "gurobi_persistent":
        Solver = SolverFactory(SolverName)
        if os.path.exists(FileName):
            os.remove(FileName)
        return Solver

    if SolverName == "appsi_gurobi":
        if not hasattr(OptModel, "_appsi_gurobi_solver"):
            OptModel._appsi_gurobi_solver = SolverFactory(SolverName)
        Solver = OptModel._appsi_gurobi_solver
        if ncall == 1 or not getattr(OptModel, "_appsi_gurobi_initialized", False):
            Solver.set_instance(OptModel)
            OptModel._appsi_gurobi_initialized = True
        else:
            if mTEPES.pIndSectorDecomposition == 0:
                Solver.update_config.check_for_new_or_removed_params      = True
                Solver.update_config.check_for_new_or_removed_vars        = True
                Solver.update_config.check_for_new_or_removed_constraints = True
                Solver.update_config.update_params                        = True
                Solver.update_config.update_vars                          = True
                Solver.update_config.update_constraints                   = True
            else:
                Solver.update_config.check_for_new_or_removed_params      = False
                Solver.update_config.check_for_new_or_removed_vars        = False
                Solver.update_config.check_for_new_or_removed_constraints = False
                Solver.update_config.update_params                        = False
                Solver.update_config.update_vars                          = True
                Solver.update_config.update_constraints                   = False
            Solver.update_config.update_named_expressions                 = False
            Solver.config.load_solution                                   = True
            Solver.config.warmstart                                       = True
            Solver.config.stream_solver                                   = True
        return Solver

    # gurobi_persistent
    if not hasattr(OptModel, "_gurobi_persistent_solver"):
        OptModel._gurobi_persistent_solver = SolverFactory(SolverName)
    Solver = OptModel._gurobi_persistent_solver
    if ncall == 1 or not getattr(OptModel, "_gurobi_persistent_initialized", False):
        Solver.set_instance(OptModel)
        OptModel._gurobi_persistent_initialized = True
    else:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            Solver.update_var(var)
    return Solver


def prepare_for_resolve(OptModel, Solver, SolverName: str) -> None:
    """Update the persistent solver's state for the fix-and-resolve LP pass.

    For ``appsi_gurobi`` only the variable values changed (no new constraints / params / vars); for
    ``gurobi_persistent`` push every var's new bound into Gurobi via ``update_var``.
    """
    if SolverName == "appsi_gurobi":
        Solver.update_config.check_for_new_or_removed_params      = False
        Solver.update_config.check_for_new_or_removed_vars        = False
        Solver.update_config.check_for_new_or_removed_constraints = False
        Solver.update_config.update_params                        = False
        Solver.update_config.update_vars                          = True
        Solver.update_config.update_constraints                   = False
    elif SolverName == "gurobi_persistent":
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            Solver.update_var(var)
