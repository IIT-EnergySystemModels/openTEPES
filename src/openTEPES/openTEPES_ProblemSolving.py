# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.16 - September 11, 2020

import time
import psutil
from pyomo.opt import SolverFactory
from pyomo.environ import Suffix


def ProblemSolving(CaseName, SolverName, mTEPES):
    print('Problem solving             ****')

    StartTime = time.time()

    # %% solving the problem
    # select solver
    Solver = SolverFactory(SolverName)
    if SolverName == 'gurobi':
        Solver.options['LogFile'] = CaseName+'/openTEPES_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = CaseName+'/openTEPES_'+CaseName+'.ilp'              # should be uncommented to show results of IIS
        # barrier method
        Solver.options['Method'] = 2
        Solver.options['Presolve'] = 2
        Solver.options['Crossover'] = 0
        Solver.options['MIPGap'] = 0.025
        Solver.options['Threads'] = int(
            (psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'] = 7200
        Solver.options['IterationLimit'] = 7200000
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat() == 0:
        # introduced to show results of the dual variables
        Solver.options['relax_integrality'] = 1
        if SolverName == 'gurobi':
            Solver.options['Crossover'] = -1
        mTEPES.dual = Suffix(direction=Suffix.IMPORT)
    # tee=True displays the log of the solver
    SolverResults = Solver.solve(mTEPES, tee=True, report_timing=True)
    # summary of the solver results
    SolverResults.write()

    # %% fix values of binary variables to get dual variables and solve it again
    # investment decision values < 1e-5 are converted to 0
    pEpsilon = 1e-5
    if mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat():
        if mTEPES.pIndBinGenInvest*len(mTEPES.gc):
            for gc in mTEPES.gc:
                if mTEPES.vGenerationInvest[gc]() <= pEpsilon:
                    mTEPES.vGenerationInvest[gc].fix(0)
                else:
                    mTEPES.vGenerationInvest[gc].fix(
                        mTEPES.vGenerationInvest[gc]())
        if mTEPES.pIndBinNetInvest*len(mTEPES.lc):
            for lc in mTEPES.lc:
                if mTEPES.vNetworkInvest[lc]() <= pEpsilon:
                    mTEPES.vNetworkInvest[lc].fix(0)
                else:
                    mTEPES.vNetworkInvest[lc].fix(mTEPES.vNetworkInvest[lc]())
        if mTEPES.pIndBinGenOperat:
            for sc, p, n, t in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.t:
                mTEPES.vCommitment[sc, p, n, t].fix(
                    mTEPES.vCommitment[sc, p, n, t]())
                mTEPES.vStartUp[sc, p, n, t].fix(
                    mTEPES.vStartUp[sc, p, n, t]())
                mTEPES.vShutDown[sc, p, n, t].fix(
                    mTEPES.vShutDown[sc, p, n, t]())
        # introduced to show results of the dual variables
        Solver.options['relax_integrality'] = 1
        if SolverName == 'gurobi':
            Solver.options['Crossover'] = -1
        mTEPES.dual = Suffix(direction=Suffix.IMPORT)
        # tee=True displays the log of the solver
        SolverResults = Solver.solve(
            mTEPES, warmstart=True, tee=False, report_timing=True)
        # summary of the solver results
        SolverResults.write()

    SolvingTime = time.time() - StartTime
    StartTime = time.time()
    print('Solving                               ... ', round(SolvingTime), 's')

    print('Total system cost [MEUR]                  ',
          mTEPES.eTotalTCost.expr())
