"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 20, 2021
"""

import time
import os
import psutil
from   pyomo.opt     import SolverFactory
from   pyomo.environ import Suffix, Set

def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole):
    print('Problem solving                        ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% activating all scenarios, periods, and load levels
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and mTEPES.pScenProb   [scc])
    mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp                                            )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt, nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration        )

    #%% solving the problem
    # Solver = SolverFactory(SolverName, solver_io='mps')                                      # select solver
    Solver = SolverFactory(SolverName)                                                         # select solver
    if SolverName == 'gurobi':
        Solver.options['LogFile'       ] = _path+'/openTEPES_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = _path+'/openTEPES_'+CaseName+'.ilp'               # should be uncommented to show results of IIS
        Solver.options['Method'        ] = 2                                                 # barrier method
        Solver.options['Presolve'      ] = 2
        Solver.options['Crossover'     ] = 0
        Solver.options['RINS'          ] = 100
        # Solver.options['BarConvTol'    ] = 1e-9
        # Solver.options['BarQCPConvTol' ] = 0.025
        Solver.options['MIPGap'        ] = 0.01
        Solver.options['Threads'       ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'     ] =    7200
        Solver.options['IterationLimit'] = 7200000
    if mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la) + len(mTEPES.g2g) == 0:
        if SolverName == 'gurobi' or SolverName == 'mosek':
            Solver.options['relax_integrality'] =  1  # introduced to show results of the dual variables
            Solver.options['Crossover'        ] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT)
    if pIndLogConsole == 1:
        SolverResults = Solver.solve(OptModel, tee=True , report_timing=True )               # tee=True displays the log of the solver
    else:
        SolverResults = Solver.solve(OptModel, tee=False, report_timing=False)
    assert str(SolverResults.solver.termination_condition) == 'optimal'
    SolverResults.write()                                                              # summary of the solver results

    #%% fix values of somes variables to get duals and solve it again
    # binary/continuous investment decisions are fixed to their optimal values
    # binary            operation  decisions are fixed to their optimal values
    if mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinGenRetire()*len(mTEPES.gd) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la) + len(mTEPES.g2g):
        if mTEPES.pIndBinGenInvest()*len(mTEPES.gc):
            for gc in mTEPES.gc:
                if mTEPES.pIndBinUnitInvest[gc] != 0:
                    OptModel.vGenerationInvest[gc].fix(round(OptModel.vGenerationInvest[gc]()))
                else:
                    OptModel.vGenerationInvest[gc].fix(      OptModel.vGenerationInvest[gc]())
        if mTEPES.pIndBinGenRetire()*len(mTEPES.gd):
            for gd in mTEPES.gd:
                if mTEPES.pIndBinUnitRetire[gd] != 0:
                    OptModel.vGenerationRetire[gd].fix(round(OptModel.vGenerationRetire[gd]()))
                else:
                    OptModel.vGenerationRetire[gd].fix(      OptModel.vGenerationRetire[gd]())
        if mTEPES.pIndBinNetInvest()*len(mTEPES.lc):
            for lc in mTEPES.lc:
                if mTEPES.pIndBinLineInvest[lc] != 0:
                    OptModel.vNetworkInvest   [lc].fix(round(OptModel.vNetworkInvest   [lc]()))
                else:
                    OptModel.vNetworkInvest   [lc].fix(      OptModel.vNetworkInvest   [lc]())
        if mTEPES.pIndBinGenOperat()*len(mTEPES.nr):
            for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr:
                if mTEPES.pIndBinUnitCommit[nr] != 0:
                    OptModel.vCommitment[sc,p,n,nr].fix(round(OptModel.vCommitment[sc,p,n,nr]()))
                    OptModel.vStartUp   [sc,p,n,nr].fix(round(OptModel.vStartUp   [sc,p,n,nr]()))
                    OptModel.vShutDown  [sc,p,n,nr].fix(round(OptModel.vShutDown  [sc,p,n,nr]()))
        if mTEPES.pIndBinLineCommit()*len(mTEPES.la):
            for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la:
                if mTEPES.pIndBinLineSwitch[ni,nf,cc] != 0:
                    OptModel.vLineCommit  [sc,p,n,ni,nf,cc].fix(round(OptModel.vLineCommit  [sc,p,n,ni,nf,cc]()))
                    OptModel.vLineOnState [sc,p,n,ni,nf,cc].fix(round(OptModel.vLineOnState [sc,p,n,ni,nf,cc]()))
                    OptModel.vLineOffState[sc,p,n,ni,nf,cc].fix(round(OptModel.vLineOffState[sc,p,n,ni,nf,cc]()))
        if len(mTEPES.g2g):
            for nr in mTEPES.nr:
                if sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g):
                    OptModel.vMaxCommitment[nr].fix(OptModel.vMaxCommitment[nr]())
        if SolverName == 'gurobi' or SolverName == 'mosek':
            Solver.options['relax_integrality'] =  1  # introduced to show results of the dual variables
            Solver.options['Crossover'        ] = -1
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT)
        if pIndLogConsole == 1:
            SolverResults = Solver.solve(OptModel, tee=True , report_timing=True , warmstart=True)   # tee=True displays the log of the solver
        else:
            SolverResults = Solver.solve(OptModel, tee=False, report_timing=False, warmstart=True)
        SolverResults.write()                                                                  # summary of the solver results

    SolvingTime = time.time() - StartTime
    print('Solution time                          ... ', round(SolvingTime), 's')
    print('Total system      cost [MEUR]              ', OptModel.eTotalTCost.expr())
    print('Total investment  cost [MEUR]              ', OptModel.vTotalFCost())
    print('Total generation  cost [MEUR]              ', sum(mTEPES.pScenProb[sc] * OptModel.vTotalGCost[sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n))
    print('Total consumption cost [MEUR]              ', sum(mTEPES.pScenProb[sc] * OptModel.vTotalCCost[sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n))
    print('Total emission    cost [MEUR]              ', sum(mTEPES.pScenProb[sc] * OptModel.vTotalECost[sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n))
    print('Total reliability cost [MEUR]              ', sum(mTEPES.pScenProb[sc] * OptModel.vTotalRCost[sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n))
