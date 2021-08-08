"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 20, 2021
"""

import time
import os
import psutil
from pyomo.opt import SolverFactory
from pyomo.environ import Suffix, Set


def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES):
    print('Problem solving                        ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # %% activating all scenarios, periods, and load levels
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n)
    mTEPES.sc = Set(
        initialize=mTEPES.scc,
        ordered=True,
        doc='scenarios',
        filter=lambda mTEPES,
        scc: scc in mTEPES.scc and mTEPES.pScenProb[scc])
    mTEPES.p = Set(
        initialize=mTEPES.pp,
        ordered=True,
        doc='periods',
        filter=lambda mTEPES,
        pp: pp)
    mTEPES.st = Set(
        initialize=mTEPES.stt,
        ordered=True,
        doc='stages',
        filter=lambda mTEPES,
        stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(
            1 for (
                stt,
                nn) in mTEPES.s2n))
    mTEPES.n = Set(
        initialize=mTEPES.nn,
        ordered=True,
        doc='load levels',
        filter=lambda mTEPES,
        nn: nn in mTEPES.pDuration)

    # %% solving the problem
    # select solver
    Solver = SolverFactory(SolverName, solver_io='mps')
    if SolverName == 'gurobi':
        Solver.options['LogFile'] = _path + '/openTEPES_' + CaseName + '.log'
        # Solver.options['IISFile'     ] = _path+'/openTEPES_'+CaseName+'.ilp'
        # # should be uncommented to show results of IIS
        # barrier method
        Solver.options['Method'] = 2
        Solver.options['Presolve'] = 2
        Solver.options['Crossover'] = 0
        Solver.options['RINS'] = 100
        # Solver.options['BarConvTol'    ] = 1e-9
        # Solver.options['BarQCPConvTol' ] = 0.025
        Solver.options['MIPGap'] = 0.01
        Solver.options['Threads'] = int(
            (psutil.cpu_count(
                logical=True) +
                psutil.cpu_count(
                logical=False)) /
            2)
        Solver.options['TimeLimit'] = 7200
        Solver.options['IterationLimit'] = 7200000
    if mTEPES.pIndBinGenInvest() * len(mTEPES.gc) + mTEPES.pIndBinNetInvest() * len(mTEPES.lc) + \
            mTEPES.pIndBinGenOperat() * len(mTEPES.nr) + mTEPES.pIndBinLineCommit() * len(mTEPES.la) == 0:
        Solver.options['relax_integrality'] = 1
        if SolverName == 'gurobi':
            Solver.options['Crossover'] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc = Suffix(direction=Suffix.IMPORT)
    # tee=True displays the log of the solver
    SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)
    assert str(SolverResults.solver.termination_condition) == 'optimal'
    # summary of the solver results
    SolverResults.write()

    # %% fix values of binary variables to get dual variables and solve it again
    # investment decision values are rounded to the nearest integer
    if mTEPES.pIndBinGenInvest() * len(mTEPES.gc) + mTEPES.pIndBinNetInvest() * len(mTEPES.lc) + \
            mTEPES.pIndBinGenOperat() * len(mTEPES.nr) + mTEPES.pIndBinLineCommit() * len(mTEPES.la):
        if mTEPES.pIndBinGenInvest() * len(mTEPES.gc):
            for gc in mTEPES.gc:
                OptModel.vGenerationInvest[gc].fix(
                    round(OptModel.vGenerationInvest[gc]()))
        if mTEPES.pIndBinNetInvest() * len(mTEPES.lc):
            for lc in mTEPES.lc:
                OptModel.vNetworkInvest[lc].fix(
                    round(OptModel.vNetworkInvest[lc]()))
        if mTEPES.pIndBinGenOperat() * len(mTEPES.nr):
            for sc, p, n, nr in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.nr:
                OptModel.vCommitment[sc, p, n, nr].fix(
                    round(OptModel.vCommitment[sc, p, n, nr]()))
                OptModel.vStartUp[sc, p, n, nr].fix(
                    round(OptModel.vStartUp[sc, p, n, nr]()))
                OptModel.vShutDown[sc, p, n, nr].fix(
                    round(OptModel.vShutDown[sc, p, n, nr]()))
        if mTEPES.pIndBinLineCommit() * len(mTEPES.la):
            for sc, p, n, ni, nf, cc in mTEPES.sc * \
                    mTEPES.p * mTEPES.n * mTEPES.la:
                if mTEPES.pLineSwitching[ni, nf, cc] == 1:
                    OptModel.vLineCommit[sc, p, n, ni, nf, cc].fix(
                        round(OptModel.vLineCommit[sc, p, n, ni, nf, cc]()))
                    OptModel.vLineOnState[sc, p, n, ni, nf, cc].fix(
                        round(OptModel.vLineOnState[sc, p, n, ni, nf, cc]()))
                    OptModel.vLineOffState[sc, p, n, ni, nf, cc].fix(
                        round(OptModel.vLineOffState[sc, p, n, ni, nf, cc]()))
        # introduced to show results of the dual variables
        Solver.options['relax_integrality'] = 1
        if SolverName == 'gurobi':
            Solver.options['Crossover'] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc = Suffix(direction=Suffix.IMPORT)
        SolverResults = Solver.solve(
            OptModel,
            tee=True,
            report_timing=True,
            warmstart=True)   # tee=True displays the log of the solver
        # summary of the solver results
        SolverResults.write()

    SolvingTime = time.time() - StartTime
    print('Solution time                          ... ', round(SolvingTime), 's')

    print(
        'Total system cost [MEUR]                   ',
        OptModel.eTotalTCost.expr())
