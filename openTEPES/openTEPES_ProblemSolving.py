"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - November 08, 2024
"""

import time
import os
import pandas        as pd
import gurobipy
import pyomo.environ as pyo
import psutil
import logging
from   pyomo.opt             import SolverFactory, SolverStatus, TerminationCondition
from   pyomo.util.infeasible import log_infeasible_constraints
from   pyomo.environ         import Suffix

def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Problem solving                        ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% solving the problem
    Solver = SolverFactory(SolverName)                                                       # select solver
    if SolverName == 'gurobi':
        FileName = _path+f'/openTEPES_gurobi_{CaseName}_{p}_{sc}_{st}.log'
        if os.path.exists(FileName):
            os.remove(FileName)
        Solver.options['LogFile'         ] = _path+f'/openTEPES_gurobi_{CaseName}_{p}_{sc}_{st}.log'
        # Solver.options['SolutionTarget'] = 1                                                 # optimal solution with or without basic solutions
        Solver.options['Method'          ] = 2                                                 # barrier method
        Solver.options['Crossover'       ] = -1
        # Solver.options['MIPFocus'      ] = 3
        # Solver.options['Presolve'      ] = 2
        # Solver.options['RINS'          ] = 100
        # Solver.options['BarConvTol'    ] = 1e-9
        # Solver.options['BarQCPConvTol' ] = 0.025
        # Solver.options['IISFile'       ] = _path+f'/openTEPES_gurobi_'+CaseName+'.ilp'        # should be uncommented to show results of IIS
        Solver.options['MIPGap'          ] = 0.01
        Solver.options['Threads'         ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['Threads'] = 1
        Solver.options['TimeLimit'       ] =    36000
        Solver.options['IterationLimit'  ] = 36000000
    if SolverName == 'cplex':
        FileName = _path+f'/openTEPES_cplex_{CaseName}_{p}_{sc}_{st}.log'
        if os.path.exists(FileName):
            os.remove(FileName)
        # Solver.options['LogFile'          ] = _path+f'/openTEPES_cplex_{CaseName}_{p}_{sc}_{st}.log'
        Solver.options['LPMethod'           ] = 4                                                 # barrier method
        # Solver.options['BarCrossAlg'      ] = 0
        # Solver.options['NumericalEmphasis'] = 1
        # Solver.options['PreInd'           ] = 1
        # Solver.options['RINSHeur'         ] = 100
        # Solver.options['EpGap'            ] = 0.01
        Solver.options['Threads'            ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'          ] =    36000
        # Solver.options['ItLim'            ] = 36000000
    if SolverName == 'appsi_highs':
        FileName = _path+f'/openTEPES_highs_{CaseName}_{p}_{sc}_{st}.log'
        if os.path.exists(FileName):
            os.remove(FileName)
        Solver.options['log_file'               ] = _path+f'/openTEPES_highs_{CaseName}_{p}_{sc}_{st}.log'
        Solver.options['log_to_console'         ] = 'true'
        Solver.options['solver'                 ] = 'simplex'
        Solver.options['run_crossover'          ] = 'off'
        Solver.options['mip_rel_gap'            ] = 0.01
        Solver.options['threads'                ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['time_limit'             ] =    36000
        Solver.options['simplex_iteration_limit'] = 36000000
    if SolverName == 'gams':
        solver_options = {
            'file COPT / cplex.opt / ; put COPT putclose "LPMethod 4" / "RINSHeur 100" / ; GAMS_MODEL.OptFile = 1 ;'
            'option SysOut  = off   ;',
            'option LP      = cplex ; option MIP     = cplex    ;',
            'option ResLim  = 36000 ; option IterLim = 36000000 ;',
            'option Threads = '+str(int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))+' ;'
        }

    idx = 0
    for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
        if not var.is_continuous():
            # print("trucutrucu")
            idx += 1
    if idx == 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT_EXPORT)

    if SolverName == 'gams':
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, symbolic_solver_labels=False, add_options=solver_options)
    else:
        print(f"Claiming gurobi p:{p},sc:{sc},st:{st}")
        SolverResults = Solver.solve(OptModel, tee=False, report_timing=True)

    print('Termination condition: ', SolverResults.solver.termination_condition)
    if SolverResults.solver.termination_condition == TerminationCondition.infeasible or SolverResults.solver.termination_condition == TerminationCondition.maxTimeLimit or SolverResults.solver.termination_condition == TerminationCondition.infeasible.maxIterations:
        log_infeasible_constraints(OptModel, log_expression=True, log_variables=True)
        logging.basicConfig(filename=_path+f'/openTEPES_infeasibilities_{CaseName}_{p}_{sc}_{st}.log', level=logging.INFO)
        raise ValueError('Problem infeasible')
    SolverResults.write()                                                              # summary of the solver results

    #%% fix values of some variables to get duals and solve it again
    # binary/continuous investment decisions are fixed to their optimal values
    # binary            operation  decisions are fixed to their optimal values
    # if NoRepetition == 1, all variables are fixed
    # if NoRepetition == 0, only the variables of the current period and scenario are fixed
    idx = 0
    if mTEPES.NoRepetition == 1:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed():
                var.fixed = True  # fix the current value
                idx += 1
    else:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed() and var.index()[0] == p and var.index()[1] == sc:
                var.fixed = True  # fix the current value
                idx += 1

    # continuous investment decisions are fixed to their optimal values
    for gc in mTEPES.gc:
        OptModel.vGenerationInvest[p,gc].fix(        OptModel.vGenerationInvest[p,gc      ]())
    for gd in mTEPES.gd:
        OptModel.vGenerationRetire[p,gd].fix(        OptModel.vGenerationRetire[p,gd      ]())
    if mTEPES.pIndHydroTopology == 1:
        for rc in mTEPES.rn:
            OptModel.vReservoirInvest[p,rc].fix(     OptModel.vReservoirInvest [p,rc      ]())
    for ni,nf,cc in mTEPES.lc:
        OptModel.vNetworkInvest[p,ni,nf,cc].fix(     OptModel.vNetworkInvest   [p,ni,nf,cc]())
    if mTEPES.pIndHydrogen == 1:
        for ni,nf,cc in mTEPES.pc:
            OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(OptModel.vH2PipeInvest    [p,ni,nf,cc]())
    if mTEPES.pIndHeat == 1:
        for ni,nf,cc in mTEPES.hc:
            OptModel.vHeatPipeInvest[p,ni,nf,cc].fix(OptModel.vHeatPipeInvest  [p,ni,nf,cc]())

    if idx > 0:
        print("FGFGFGFGFGFGFG")
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT_EXPORT)
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    import threading

    # Thread-safe lock for updating mTEPES.pDuals
    pDuals_lock = threading.Lock()
    # saving the dual variables for writing in output results
    pDuals = {}
    for con in OptModel.component_objects(pyo.Constraint, active=True):
        if con.is_indexed():
            for index in con:
                pDuals[str(con.name)+str(index)] = OptModel.dual[con[index]]

    with pDuals_lock:
        mTEPES.pDuals.update(pDuals)

    # save values of each stage
    for n in mTEPES.n:
        OptModel.vTotalGCost[p,sc,n].fix(OptModel.vTotalGCost[p,sc,n]())
        OptModel.vTotalCCost[p,sc,n].fix(OptModel.vTotalCCost[p,sc,n]())
        OptModel.vTotalECost[p,sc,n].fix(OptModel.vTotalECost[p,sc,n]())
        OptModel.vTotalRCost[p,sc,n].fix(OptModel.vTotalRCost[p,sc,n]())

    # delete dual and rc suffixes
    OptModel.del_component(OptModel.dual)
    OptModel.del_component(OptModel.rc  )

    SolvingTime = time.time() - StartTime

    #%% writing the results
    # print    ('  Problem size                         ... ', OptModel.model().nconstraints(), 'constraints, ', OptModel.model().nvariables()-mTEPES.nFixedVariables+1, 'variables')
    # print    ('  Solution time                        ... ', round(SolvingTime), 's')
    # print    ('  Total system                 cost [MEUR] ', OptModel.vTotalSCo())
    # if mTEPES.NoRepetition == 1:
    #     print("No repetition")
    #     for pp,scc in mTEPES.ps:
    #         print    (f'***** Period: {pp}, Scenario: {scc}, Stage: {st} ******')
    #         print    ('  Total generation  investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pGenInvestCost    [gc      ]   * OptModel.vGenerationInvest[pp,gc      ]() for gc       in mTEPES.gc if (pp,gc)       in mTEPES.pgc))
    #         print    ('  Total generation  retirement cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire[pp,gd      ]() for gd       in mTEPES.gd if (pp,gd)       in mTEPES.pgd))
    #         if mTEPES.pIndHydroTopology == 1 and len(mTEPES.rn):
    #             print('  Total reservoir   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest [pp,rc      ]() for rc       in mTEPES.rn if (pp,rc)       in mTEPES.prc))
    #         else:
    #             print('  Total reservoir   investment cost [MEUR] ', 0.0)
    #         print    ('  Total network     investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest   [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.lc if (pp,ni,nf,cc) in mTEPES.plc))
    #         if mTEPES.pIndHydrogen      == 1 and len(mTEPES.pc):
    #             print('  Total H2   pipe   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest    [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.pc if (pp,ni,nf,cc) in mTEPES.ppc))
    #         else:
    #             print('  Total H2   pipe   investment cost [MEUR] ', 0.0)
    #         if mTEPES.pIndHeat          == 1 and len(mTEPES.hc):
    #             print('  Total heat pipe   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest  [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.hc if (pp,ni,nf,cc) in mTEPES.phc))
    #         else:
    #             print('  Total heat pipe   investment cost [MEUR] ', 0.0)
    #         print    ('  Total generation  operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalGCost      [pp,scc,n    ]() for n        in mTEPES.n ))
    #         print    ('  Total consumption operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalCCost      [pp,scc,n    ]() for n        in mTEPES.n ))
    #         print    ('  Total emission               cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalECost      [pp,scc,n    ]() for n        in mTEPES.n ))
    #         print    ('  Total reliability            cost [MEUR] ', sum(mTEPES.pDiscountedWeight[pp] * mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRCost      [pp,scc,n    ]() for n        in mTEPES.n ))
    # else:
    #     print("Repetition")
    #     print        (f'***** Period: {p}, Scenario: {sc}, Stage: {st} ******')
    #     print        ('  Total generation  investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pGenInvestCost    [gc      ]   * OptModel.vGenerationInvest[p,gc        ]() for gc       in mTEPES.gc if (p,gc)       in mTEPES.pgc))
    #     print        ('  Total generation  retirement cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire[p,gd        ]() for gd       in mTEPES.gd if (p,gd)       in mTEPES.pgd))
    #     if mTEPES.pIndHydroTopology == 1 and len(mTEPES.rn):
    #         print    ('  Total reservoir   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest [p,rc        ]() for rc       in mTEPES.rn if (p,rc)       in mTEPES.prc))
    #     else:
    #         print    ('  Total reservoir   investment cost [MEUR] ', 0.0)
    #     print        ('  Total network     investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest   [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc))
    #     if mTEPES.pIndHydrogen      == 1 and len(mTEPES.pc):
    #         print    ('  Total H2   pipe   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest    [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc))
    #     else:
    #         print    ('  Total H2   pipe   investment cost [MEUR] ', 0.0)
    #     if mTEPES.pIndHeat          == 1 and len(mTEPES.hc):
    #         print    ('  Total heat pipe   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest  [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc))
    #     else:
    #         print    ('  Total heat pipe   investment cost [MEUR] ', 0.0)
    #     print        ('  Total generation  operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalGCost      [p,sc,n      ]() for n        in mTEPES.n ))
    #     print        ('  Total consumption operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalCCost      [p,sc,n      ]() for n        in mTEPES.n ))
    #     print        ('  Total emission               cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalECost      [p,sc,n      ]() for n        in mTEPES.n ))
    #     print        ('  Total reliability            cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p]  * mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRCost      [p,sc,n      ]() for n        in mTEPES.n ))
