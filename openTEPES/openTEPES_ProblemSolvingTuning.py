"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 05, 2026
openTEPES.openTEPES_ProblemSolvingTuning — per-solver option presets for the initial solve and the fix-and-resolve LP pass.

Each solver family (Gurobi, CPLEX, HiGHS, GAMS) has a distinct option-setting API; ``apply_solver_options()``
centralises the dispatch so ``ProblemSolving`` does not need to know which solver it is talking to. The function
also picks the right barrier / simplex method depending on whether this is the first solve (``ncall == 1`` →
barrier ``Method=2``) or a warm-restart (``ncall > 1`` → automatic ``Method=-1``).

For GAMS, options are returned as a set of additional CLI strings rather than set on ``Solver.options``; that is
why the function returns an optional ``solver_options`` value for the caller to forward to ``Solver.solve()``.

``apply_resolve_options()`` is the lighter pass used between the initial MIP solve and the fix-and-resolve LP
pass — it just switches the solver to ``Method=-1`` / ``LPMethod=0`` for warm-restart behaviour.

Thread count defaults to half the available logical+physical cores. Numerically hard large-scale
stochastic LPs may need solver-specific barrier tuning (e.g. ``Crossover``, ``BarHomogeneous``,
``ScaleFlag``, ``NumericFocus`` for Gurobi); set those per deployment, since the right values are
case-dependent and can regress smaller cases.
"""
from __future__ import annotations

import os

import psutil


def _threads() -> int:
    """Thread count for the solver: ``--threads`` or ``OTEPES_THREADS`` when set to a positive integer, else half of the
    (logical + physical) cores, rounded down. Capping it lets cases run side by side, each taking a slice of the cores
    instead of all claiming half the machine.
    """
    env = os.environ.get("OTEPES_THREADS", "").strip()
    if env.isdigit() and int(env) > 0:
        return int(env)
    return int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False)) / 2)


def apply_solver_options(Solver, SolverName: str, FileName: str, ncall: int):
    """Apply initial-solve options to ``Solver`` based on ``SolverName``. Returns a GAMS ``solver_options`` set
    if applicable; ``None`` otherwise (for Gurobi/CPLEX/HiGHS the options are set on ``Solver.options``)."""
    if SolverName == "gurobi" or SolverName == "gurobi_direct" or SolverName == "appsi_gurobi":
        Solver.options["OutputFlag"]      = 1
        Solver.options["LogFile"]         = FileName
        Solver.options["DisplayInterval"] = 100
        Solver.options["LPWarmStart"]     = 2
        Solver.options["Method"]          = 2 if ncall == 1 else -1
        Solver.options["Crossover"]       = -1
        Solver.options["MIPGap"]          = 0.01
        Solver.options["Threads"]         = _threads()
        Solver.options["TimeLimit"]       = 36000
        Solver.options["IterationLimit"]  = 36000000
        # Solver.options["SolutionTarget"] = 1                                                 # optimal solution with or without basic solutions
        # Solver.options["MIPFocus"]      = 3
        # Solver.options["Seed"]          = 104729
        # Solver.options["RINS"]          = 100
        # Solver.options["BarConvTol"]    = 1e-10
        # Solver.options["BarQCPConvTol"] = 0.025
        return None

    if SolverName == "gurobi_persistent":
        Solver.set_gurobi_param("OutputFlag",      1)
        Solver.set_gurobi_param("LogFile",  FileName)
        Solver.set_gurobi_param("DisplayInterval", 100)
        Solver.set_gurobi_param("LPWarmStart",     2)
        Solver.set_gurobi_param("Method",          2 if ncall == 1 else -1)
        Solver.set_gurobi_param("Crossover",      -1)
        Solver.set_gurobi_param("MIPGap",       0.01)
        Solver.set_gurobi_param("Threads",     _threads())
        Solver.set_gurobi_param("TimeLimit",      36000)
        Solver.set_gurobi_param("IterationLimit", 36000000)
        return None

    if SolverName == "cplex":
        # Solver.options["LogFile"]          = FileName
        Solver.options["LPMethod"]           = 4 if ncall == 1 else 0
        Solver.options["Threads"]            = _threads()
        Solver.options["TimeLimit"]          = 72000
        # Solver.options["BarCrossAlg"]      = 0
        # Solver.options["NumericalEmphasis"] = 1
        # Solver.options["PreInd"]           = 1
        # Solver.options["RINSHeur"]         = 100
        # Solver.options["EpGap"]            = 0.01
        return None

    if SolverName == "highs":
        Solver.options["log_file"]                = FileName
        Solver.options["solver"]                  = "choose"
        Solver.options["simplex_strategy"]        = 1
        Solver.options["run_crossover"]           = "on"
        Solver.options["mip_rel_gap"]             = 0.01
        Solver.options["parallel"]                = "choose"
        # Solver.options["primal_feasibility_tolerance"] = 1e-3
        Solver.options["threads"]                 = _threads()
        Solver.options["time_limit"]              = 72000
        Solver.options["simplex_iteration_limit"] = 72000000
        return None

    if SolverName == "gams":
        return {
            'file COPT / cplex.opt / ; put COPT putclose "LPMethod 4" / "EpGap 0.01" / ; GAMS_MODEL.OptFile = 1 ; '
            "option SysOut  = off   ;",
            "option LP      = cplex ; option MIP     = cplex    ;",
            "option ResLim  = 72000 ; option IterLim = 72000000 ;",
            "option Threads = " + str(_threads()) + " ;",
        }

    return None


def apply_resolve_options(Solver, SolverName: str) -> None:
    """Switch ``Solver`` to warm-restart LP mode for the fix-and-resolve pass after the initial MIP solve."""
    if SolverName == "gurobi" or SolverName == "gurobi_direct" or SolverName == "appsi_gurobi":
        Solver.options["Method"]      = -1
    elif SolverName == "gurobi_persistent":
        Solver.set_gurobi_param("Method", -1)
    elif SolverName == "cplex":
        Solver.options["LPMethod"]    = 0
