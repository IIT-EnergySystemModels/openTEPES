"""
openTEPES.openTEPES_ProblemSolving — per-stage solve orchestrator.

Composes the three Layer 5.a primitives:

  * ``Persistent.setup_solver``       set up (or reuse) the solver instance; handles ``appsi_gurobi`` /
                                      ``gurobi_persistent`` ``ncall`` lifecycle.
  * ``Tuning.apply_solver_options``   set per-solver option presets (Gurobi / CPLEX / HiGHS / GAMS).
  * ``DualExtraction.fix_for_duals``  fix integers + investments after the initial solve so the LP
                                      re-solve recovers shadow prices.
  * ``DualExtraction.collect_duals``  copy active-constraint duals into ``mTEPES.pDuals`` after the resolve.

The cost-reporting block at the end (printing investment / operation / reliability components per period and
scenario) stays inline here for now; it will move to Layer 6 ``results/`` in a follow-on PR. Behaviour is
byte-identical to the pre-split ``openTEPES_ProblemSolving.py`` (verified by the full ``tests/test_run.py``
matrix).
"""
from __future__ import annotations

import logging
import os
import time

import pyomo.environ as pyo
from pyomo.environ import Suffix
from pyomo.opt import TerminationCondition
from pyomo.util.infeasible import log_infeasible_constraints

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_ProblemSolvingDualExtraction import collect_duals, fix_for_duals
    from .openTEPES_ProblemSolvingPersistent import prepare_for_resolve, setup_solver
    from .openTEPES_ProblemSolvingTuning import apply_resolve_options, apply_solver_options
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_ProblemSolvingDualExtraction import collect_duals, fix_for_duals
    from openTEPES.openTEPES_ProblemSolvingPersistent import prepare_for_resolve, setup_solver
    from openTEPES.openTEPES_ProblemSolvingTuning import apply_resolve_options, apply_solver_options


def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc, st, ncall):
    print("Problem solving                        ####", ncall)
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    FileName = f"{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}.log"

    # ---- Set up solver (persistent or one-shot) ----
    Solver = setup_solver(OptModel, SolverName, FileName, ncall, mTEPES)
    solver_options = apply_solver_options(Solver, SolverName, FileName, ncall)

    # ---- Decide whether to attach the dual Suffix before the initial solve ----
    # Only a pure-LP model can return duals from its first solve, so the Suffix is
    # attached up front only when there is no unfixed integer/binary variable. A MIP
    # gets its duals later, from the fix-and-resolve LP pass below. The variable's
    # value is deliberately NOT checked here: before the first solve every value is
    # None, so an investment MIP (whose binary variables have no starting value) would
    # otherwise look like an LP, get the Suffix, and crash when HiGHS is asked for
    # duals it does not have for a MIP. Unit-commitment MIPs hid this because their
    # binary variables are given starting values.
    nIntegerVars = 0
    for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
        if not var.is_continuous() and not var.is_fixed():
            nIntegerVars += 1
    if nIntegerVars == 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)

    # ---- Initial solve ----
    if SolverName == "gams":
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, symbolic_solver_labels=False,
                                     add_options=solver_options, logfile=FileName)
    elif SolverName == "gurobi_persistent":
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, warmstart=True,
                                     keepfiles=False, load_solutions=True, save_results=False)
    else:
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    print("Termination condition: ", SolverResults.solver.termination_condition)
    if (SolverResults.solver.termination_condition == TerminationCondition.infeasible
            or SolverResults.solver.termination_condition == TerminationCondition.maxTimeLimit
            or SolverResults.solver.termination_condition == TerminationCondition.infeasible.maxIterations):
        log_infeasible_constraints(OptModel, log_expression=True, log_variables=True)
        logging.basicConfig(filename=f"{_path}/openTEPES_infeasibilities_{CaseName}_{p}_{sc}_{st}.log",
                            level=logging.INFO)
        raise ValueError(f"### Problem infeasible for period {p}, scenario {sc}, stage {st}")

    # ---- Fix integers + investments; re-solve as LP to recover duals ----
    nUnfixedVars = fix_for_duals(OptModel, mTEPES, p, sc)

    if nUnfixedVars > 0:
        print("Problem solving with fixed investments ####", ncall)
        ncall += 1
        prepare_for_resolve(OptModel, Solver, SolverName)
        apply_resolve_options(Solver, SolverName)

        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        if SolverName == "gurobi_persistent":
            SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, warmstart=True,
                                         keepfiles=False, load_solutions=True, save_results=False)
        else:
            SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    # ---- Collect duals into mTEPES.pDuals (used by MarginalResults / EconomicResults) ----
    collect_duals(OptModel, mTEPES)

    # save values of each stage
    # for n in mTEPES.n:
    #     OptModel.vTotalGCost        [p,sc,n].fix(OptModel.vTotalGCost    [p,sc,n]())
    #     OptModel.vTotalCCost        [p,sc,n].fix(OptModel.vTotalCCost    [p,sc,n]())
    #     OptModel.vTotalECost        [p,sc,n].fix(OptModel.vTotalECost    [p,sc,n]())
    #     OptModel.vTotalRElecCost    [p,sc,n].fix(OptModel.vTotalRElecCost[p,sc,n]())
    #     if mTEPES.pIndHydrogen:
    #         OptModel.vTotalRH2Cost  [p,sc,n].fix(OptModel.vTotalRH2Cost  [p,sc,n]())
    #     if mTEPES.pIndHeat:
    #         OptModel.vTotalRHeatCost[p,sc,n].fix(OptModel.vTotalRHeatCost[p,sc,n]())

    SolvingTime = time.time() - StartTime

    # ---- Cost-summary report (stays inline; moves to Layer 6 results/ in a follow-on PR) ----
    print            ('  Total system                 cost [MEUR] ', OptModel.vTotalSCost(), ' Constraints', OptModel.model().nconstraints(), ' Variables', OptModel.model().nvariables()-mTEPES.nFixedVariables+1, ' Seconds', round(SolvingTime))
    if mTEPES.NoRepetition == 1:
        for pp,scc in mTEPES.ps:
            print    (f'***** Period: {pp}, Scenario: {scc}, Stage: {st} ******')
            print    ('  Total generation  investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenInvestCost    [eb      ]   * OptModel.vGenerationInvest    [pp,eb      ]() for eb       in mTEPES.eb if (pp,eb)       in mTEPES.peb) +
                                                                     mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenInvestCost    [bc      ]   * OptModel.vGenerationInvestHeat[pp,bc      ]() for bc       in mTEPES.bc if (pp,bc)       in mTEPES.pbc))
            print    ('  Total generation  retirement cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire    [pp,gd      ]() for gd       in mTEPES.gd if (pp,gd)       in mTEPES.pgd))
            if mTEPES.pIndHydroTopology and mTEPES.rn:
                print('  Total reservoir   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest     [pp,rc      ]() for rc       in mTEPES.rn if (pp,rc)       in mTEPES.prc))
            else:
                print('  Total reservoir   investment cost [MEUR] ', 0.0)
            print    ('  Total network     investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest       [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.lc if (pp,ni,nf,cc) in mTEPES.plc))
            if mTEPES.pIndHydrogen      and mTEPES.pc:
                print('  Total H2   pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest        [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.pc if (pp,ni,nf,cc) in mTEPES.ppc))
            else:
                print('  Total H2   pipe   investment cost [MEUR] ', 0.0)
            if mTEPES.pIndHeat          and mTEPES.hc:
                print('  Total heat pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest      [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.hc if (pp,ni,nf,cc) in mTEPES.phc))
            else:
                print('  Total heat pipe   investment cost [MEUR] ', 0.0)
            print    ('  Total generation  operation  cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalGCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total consumption operation  cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalCCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total emission               cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalECost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total network losses penalty cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalNCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total reliability electr     cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRElecCost      [pp,scc,n    ]() for n        in mTEPES.n ))
            if mTEPES.pIndHydrogen:
                print('  Total reliability hydrogen   cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRH2Cost        [pp,scc,n    ]() for n        in mTEPES.n ))
            if mTEPES.pIndHeat:
                print('  Total reliability heat       cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRHeatCost      [pp,scc,n    ]() for n        in mTEPES.n ))
    else:
        print        (f'***** Period: {p}, Scenario: {sc}, Stage: {st} ******')
        print        ('  Total generation  investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenInvestCost    [eb      ]   * OptModel.vGenerationInvest    [p,eb        ]() for eb       in mTEPES.eb if (p,eb)       in mTEPES.peb) +
                                                                     mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenInvestCost    [bc      ]   * OptModel.vGenerationInvestHeat[p,bc        ]() for bc       in mTEPES.bc if (p,bc)       in mTEPES.pbc))
        print        ('  Total generation  retirement cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire    [p,gd        ]() for gd       in mTEPES.gd if (p,gd)       in mTEPES.pgd))
        if mTEPES.pIndHydroTopology and mTEPES.rn:
            print    ('  Total reservoir   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest     [p,rc        ]() for rc       in mTEPES.rn if (p,rc)       in mTEPES.prc))
        else:
            print    ('  Total reservoir   investment cost [MEUR] ', 0.0)
        print        ('  Total network     investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest       [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc))
        if mTEPES.pIndHydrogen      and mTEPES.pc:
            print    ('  Total H2   pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest        [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc))
        else:
            print    ('  Total H2   pipe   investment cost [MEUR] ', 0.0)
        if mTEPES.pIndHeat          and mTEPES.hc:
            print    ('  Total heat pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest      [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc))
        else:
            print    ('  Total heat pipe   investment cost [MEUR] ', 0.0)
        print        ('  Total generation  operation  cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalGCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total consumption operation  cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalCCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total emission               cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalECost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total network losses penalty cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalNCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total reliability electr     cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRElecCost      [p,sc,n      ]() for n        in mTEPES.n ))
        if mTEPES.pIndHydrogen      and mTEPES.pc:
            print    ('  Total reliability H2         cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRH2Cost        [p,sc,n      ]() for n        in mTEPES.n ))
        if mTEPES.pIndHeat          and mTEPES.hc:
            print    ('  Total reliability heat       cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRHeatCost      [p,sc,n      ]() for n        in mTEPES.n ))

    # Adding SolverResults to mTEPES
    mTEPES.SolverResults = SolverResults
