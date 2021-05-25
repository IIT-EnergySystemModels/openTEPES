"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - May 25, 2021
"""

import time
import os
import psutil
from   pyomo.opt     import SolverFactory
from   pyomo.environ import Suffix

def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES):
    print('Problem solving                        ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% solving the problem
    Solver = SolverFactory(SolverName, solver_io="mps")                                                       # select solver
    if SolverName == 'gurobi':
        Solver.options['LogFile'       ] = _path+'/openTEPES_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = _path+'/openTEPES_'+CaseName+'.ilp'               # should be uncommented to show results of IIS
        Solver.options['Method'        ] = 2                                                 # barrier method
        Solver.options['Presolve'      ] = 2
        Solver.options['Crossover'     ] = 0
        Solver.options['BarConvTol'    ] = 1e-9
        Solver.options['MIPGap'        ] = 0.025
        Solver.options['Threads'       ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'     ] =    18000
        Solver.options['IterationLimit'] = 18000000
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat*len(mTEPES.nr) + mTEPES.pIndBinLineCommit*len(mTEPES.la) == 0:
        Solver.options['relax_integrality'] =  1
        if SolverName == 'gurobi':
            Solver.options['Crossover'    ] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT)
    SolverResults = Solver.solve(OptModel, tee=False, report_timing=True)               # tee=True displays the log of the solver
    assert str(SolverResults.solver.termination_condition) == "optimal"
    SolverResults.write()                                                              # summary of the solver results

    #%% fix values of binary variables to get dual variables and solve it again
    # investment decision values < 1e-5 are converted to 0
    pEpsilon = 1e-5
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat*len(mTEPES.nr) + mTEPES.pIndBinLineCommit*len(mTEPES.la):
        if mTEPES.pIndBinGenInvest*len(mTEPES.gc):
            for gc in mTEPES.gc:
                if  OptModel.vGenerationInvest[gc]() <= pEpsilon:
                    OptModel.vGenerationInvest[gc].fix(0)
                else:
                    OptModel.vGenerationInvest[gc].fix(OptModel.vGenerationInvest[gc]())
        if mTEPES.pIndBinNetInvest*len(mTEPES.lc):
            for lc in mTEPES.lc:
                if  OptModel.vNetworkInvest   [lc]() <= pEpsilon:
                    OptModel.vNetworkInvest   [lc].fix(0)
                else:
                    OptModel.vNetworkInvest   [lc].fix(OptModel.vNetworkInvest[lc]())
        if mTEPES.pIndBinGenOperat*len(mTEPES.nr):
            for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr:
                OptModel.vCommitment[sc,p,n,nr].fix(OptModel.vCommitment[sc,p,n,nr]())
                OptModel.vStartUp   [sc,p,n,nr].fix(OptModel.vStartUp   [sc,p,n,nr]())
                OptModel.vShutDown  [sc,p,n,nr].fix(OptModel.vShutDown  [sc,p,n,nr]())
        if mTEPES.pIndBinLineCommit*len(mTEPES.la):
            for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la:
                OptModel.vLineCommit  [sc,p,n,ni,nf,cc].fix(OptModel.vLineCommit  [sc,p,n,ni,nf,cc]())
                OptModel.vLineOnState [sc,p,n,ni,nf,cc].fix(OptModel.vLineOnState [sc,p,n,ni,nf,cc]())
                OptModel.vLineOffState[sc,p,n,ni,nf,cc].fix(OptModel.vLineOffState[sc,p,n,ni,nf,cc]())
        Solver.options['relax_integrality'] =  1                                               # introduced to show results of the dual variables
        if SolverName == 'gurobi':
            Solver.options['Crossover'    ] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        SolverResults = Solver.solve(OptModel, tee=False, report_timing=True, warmstart=True)  # tee=True displays the log of the solver
        SolverResults.write()                                                                  # summary of the solver results

    SolvingTime = time.time() - StartTime
    print('Solution time                          ... ', round(SolvingTime), 's')

    print('Total system cost [MEUR]                   ', OptModel.eTotalTCost.expr())
