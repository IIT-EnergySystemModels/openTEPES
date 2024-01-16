"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 16, 2024
"""

import time
import os
import pandas        as pd
import pyomo.environ as pyo
import psutil
import logging
from   pyomo.opt             import SolverFactory, SolverStatus, TerminationCondition
from   pyomo.util.infeasible import log_infeasible_constraints
from   pyomo.environ         import Suffix

def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc):
    print('Problem solving                        ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% solving the problem
    Solver = SolverFactory(SolverName)                                                       # select solver
    if SolverName == 'gurobi':
        Solver.options['LogFile'       ] = _path+'/openTEPES_gurobi_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = _path+'/openTEPES_gurobi_'+CaseName+'.ilp'        # should be uncommented to show results of IIS
        Solver.options['Method'        ] = 2                                                 # barrier method
        # Solver.options['MIPFocus'      ] = 3
        # Solver.options['Presolve'      ] = 2
        # Solver.options['RINS'          ] = 100
        Solver.options['Crossover'     ] = -1
        # Solver.options['BarConvTol'    ] = 1e-9
        # Solver.options['BarQCPConvTol' ] = 0.025
        Solver.options['MIPGap'        ] = 0.01
        Solver.options['Threads'       ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'     ] =    36000
        Solver.options['IterationLimit'] = 36000000
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
            idx += 1
    if idx == 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT_EXPORT)

    if SolverName == 'gurobi':
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)
    if SolverName == 'gams'  :
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, symbolic_solver_labels=False, add_options=solver_options)

    print('Termination condition: ', SolverResults.solver.termination_condition)
    if SolverResults.solver.termination_condition == TerminationCondition.infeasible:
        log_infeasible_constraints(OptModel, log_expression=True, log_variables=True)
        logging.basicConfig(filename=_path+'/openTEPES_infeasibilities_'+CaseName+'.txt', level=logging.INFO)
    assert (SolverResults.solver.termination_condition == TerminationCondition.optimal or SolverResults.solver.termination_condition == TerminationCondition.maxTimeLimit or SolverResults.solver.termination_condition == TerminationCondition.infeasible.maxIterations), 'Problem infeasible'
    SolverResults.write()                                                              # summary of the solver results

    #%% fix values of some variables to get duals and solve it again
    # binary/continuous investment decisions are fixed to their optimal values
    # binary            operation  decisions are fixed to their optimal values
    idx = 0
    for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
        if not var.is_continuous():
            var.fixed = True  # fix the current value
            idx += 1
    if idx > 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT_EXPORT)
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    # saving the dual variables for writing in output results
    pDuals = {}
    for c in OptModel.component_objects(pyo.Constraint, active=True):
        if c.is_indexed():
            for index in c:
                pDuals[str(c.name)+str(index)] = OptModel.dual[c[index]]

    # delete dual and rc suffixes if they exist
    if idx > 0:
        OptModel.del_component(OptModel.dual)
        OptModel.del_component(OptModel.rc  )

    mTEPES.pDuals.update(pDuals)

    SolvingTime = time.time() - StartTime

    print('***** Period: '+str(p)+', Scenario: '+str(sc)+' ******')
    print    ('  Problem size                         ... ', OptModel.model().nconstraints(), 'constraints, ', OptModel.model().nvariables()-mTEPES.nFixedVariables+1, 'variables')
    print    ('  Solution time                        ... ', round(SolvingTime), 's')
    print    ('  Total system                 cost [MEUR] ', OptModel.vTotalSCost())
    print    ('  Total generation  investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost [gc      ]   * OptModel.vGenerationInvest[p,gc      ]() for gc       in mTEPES.gc))
    print    ('  Total generation  retirement cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenRetireCost [gd      ]   * OptModel.vGenerationRetire[p,gd      ]() for gd       in mTEPES.gd))
    if mTEPES.pIndHydroTopology == 1 and len(mTEPES.rn):
        print('  Total reservoir   investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pRsrInvestCost [rc      ]   * OptModel.vReservoirInvest [p,rc      ]() for rc       in mTEPES.rn))
    else:
        print('  Total reservoir   investment cost [MEUR] ', 0.0)
    print    ('  Total network     investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pNetFixedCost  [ni,nf,cc]   * OptModel.vNetworkInvest   [p,ni,nf,cc]() for ni,nf,cc in mTEPES.lc))
    if mTEPES.pIndHydrogen      == 1 and len(mTEPES.pc):
        print('  Total pipeline    investment cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pLineInvestCost[ni,nf,cc]   * OptModel.vPipelineInvest  [p,ni,nf,cc]() for ni,nf,cc in mTEPES.pc))
    else:
        print('  Total pipeline    investment cost [MEUR] ', 0.0)
    print    ('  Total generation  operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb      [p,sc    ]() * OptModel.vTotalGCost      [p,sc,n    ]() for n        in mTEPES.n ))
    print    ('  Total consumption operation  cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb      [p,sc    ]() * OptModel.vTotalCCost      [p,sc,n    ]() for n        in mTEPES.n ))
    print    ('  Total emission               cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb      [p,sc    ]() * OptModel.vTotalECost      [p,sc,n    ]() for n        in mTEPES.n ))
    print    ('  Total reliability            cost [MEUR] ', sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb      [p,sc    ]() * OptModel.vTotalRCost      [p,sc,n    ]() for n        in mTEPES.n ))
