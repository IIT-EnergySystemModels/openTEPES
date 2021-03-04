# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - February 7, 2021

import time
import os
import psutil
from   pyomo.opt     import SolverFactory
from   pyomo.environ import Suffix

def ProblemSolving(CaseName, DirName, SolverName, mTEPES):
    print('Problem solving             ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% solving the problem
    Solver = SolverFactory(SolverName)                                                       # select solver
    if SolverName == 'gurobi':
        Solver.options['LogFile'       ] = _path+'/openTEPES_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = CaseName+'/openTEPES_'+CaseName+'.ilp'              # should be uncommented to show results of IIS
        Solver.options['Method'        ] = 2                                                   # barrier method
        Solver.options['Presolve'      ] = 2
        Solver.options['Crossover'     ] = 0
        Solver.options['MIPGap'        ] = 0.025
        Solver.options['Threads'       ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'     ] =    18000
        Solver.options['IterationLimit'] = 18000000
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat() == 0:
        if SolverName == 'gurobi':
            Solver.options['relax_integrality'] =  1                                       # introduced to show results of the dual variables
            Solver.options['Crossover'        ] = -1
        mTEPES.dual = Suffix(direction=Suffix.IMPORT)
    SolverResults = Solver.solve(mTEPES, tee=True, report_timing=True)                     # tee=True displays the log of the solver
    SolverResults.write()                                                                  # summary of the solver results

    #%% fix values of binary variables to get dual variables and solve it again
    # investment decision values < 1e-5 are converted to 0
    pEpsilon = 1e-5
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat():
        if mTEPES.pIndBinGenInvest*len(mTEPES.gc):
            for gc in mTEPES.gc:
                if  mTEPES.vGenerationInvest[gc]() <= pEpsilon:
                    mTEPES.vGenerationInvest[gc].fix(0)
                else:
                    mTEPES.vGenerationInvest[gc].fix(mTEPES.vGenerationInvest[gc]())
        if mTEPES.pIndBinNetInvest*len(mTEPES.lc):
            for lc in mTEPES.lc:
                if  mTEPES.vNetworkInvest   [lc]() <= pEpsilon:
                    mTEPES.vNetworkInvest   [lc].fix(0)
                else:
                    mTEPES.vNetworkInvest   [lc].fix(mTEPES.vNetworkInvest[lc]())
        if mTEPES.pIndBinGenOperat:
            for sc,p,n,t in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.t:
                mTEPES.vCommitment[sc,p,n,t].fix(mTEPES.vCommitment[sc,p,n,t]())
                mTEPES.vStartUp   [sc,p,n,t].fix(mTEPES.vStartUp   [sc,p,n,t]())
                mTEPES.vShutDown  [sc,p,n,t].fix(mTEPES.vShutDown  [sc,p,n,t]())
        Solver.options['relax_integrality'] =  1                                             # introduced to show results of the dual variables
        if SolverName == 'gurobi':
            Solver.options['Crossover'        ] = -1
        mTEPES.dual   = Suffix(direction=Suffix.IMPORT)
        SolverResults = Solver.solve(mTEPES, warmstart=True, tee=False, report_timing=True)  # tee=True displays the log of the solver
        SolverResults.write()                                                                # summary of the solver results

    SolvingTime = time.time() - StartTime
    StartTime   = time.time()
    print('Solving                               ... ', round(SolvingTime), 's')

    print('Total system cost [MEUR]                  ', mTEPES.eTotalTCost.expr())
