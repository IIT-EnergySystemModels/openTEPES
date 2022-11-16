"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - November 15, 2022
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

    #%% activating all periods, scenarios, and load levels
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )

    #%% solving the problem
    Solver = SolverFactory(SolverName)                                                       # select solver
    if SolverName == 'gurobi':
        Solver.options['LogFile'       ] = _path+'/openTEPES_'+CaseName+'.log'
        # Solver.options['IISFile'     ] = _path+'/openTEPES_'+CaseName+'.ilp'               # should be uncommented to show results of IIS
        Solver.options['Method'        ] = 2                                                 # barrier method
        Solver.options['MIPFocus'      ] = 1
        Solver.options['Presolve'      ] = 2
        Solver.options['RINS'          ] = 100
        Solver.options['Crossover'     ] = -1
        # Solver.options['BarConvTol'    ] = 1e-9
        # Solver.options['BarQCPConvTol' ] = 0.025
        Solver.options['MIPGap'        ] = 0.01
        Solver.options['Threads'       ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'     ] =    36000
        Solver.options['IterationLimit'] = 36000000
    if mTEPES.pIndBinGenInvest()*len(mTEPES.gc)*sum(mTEPES.pIndBinUnitInvest[gc] for gc in mTEPES.gc) + mTEPES.pIndBinGenRetire()*len(mTEPES.gd)*sum(mTEPES.pIndBinUnitRetire[gd] for gd in mTEPES.gd) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc)*sum(mTEPES.pIndBinLineInvest[lc] for lc in mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr)*sum(mTEPES.pIndBinUnitCommit[nr] for nr in mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)*sum(mTEPES.pIndBinLineSwitch[la] for la in mTEPES.la) + len(mTEPES.g2g) == 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT)
    SolverResults = Solver.solve(OptModel, tee=True , report_timing=True)              # tee=True displays the log of the solver
    print('Termination Condition: ', SolverResults.solver.termination_condition)
    assert (str(SolverResults.solver.termination_condition) == 'optimal' or str(SolverResults.solver.termination_condition) == 'maxTimeLimit' or str(SolverResults.solver.termination_condition) == 'maxIterations')
    SolverResults.write()                                                              # summary of the solver results

    #%% fix values of some variables to get duals and solve it again
    # binary/continuous investment decisions are fixed to their optimal values
    # binary            operation  decisions are fixed to their optimal values
    if mTEPES.pIndBinGenInvest()*len(mTEPES.gc)*sum(mTEPES.pIndBinUnitInvest[gc] for gc in mTEPES.gc) + mTEPES.pIndBinGenRetire()*len(mTEPES.gd)*sum(mTEPES.pIndBinUnitRetire[gd] for gd in mTEPES.gd) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc)*sum(mTEPES.pIndBinLineInvest[lc] for lc in mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr)*sum(mTEPES.pIndBinUnitCommit[nr] for nr in mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)*sum(mTEPES.pIndBinLineSwitch[la] for la in mTEPES.la) + len(mTEPES.g2g) > 0:
        if mTEPES.pIndBinGenInvest()*len(mTEPES.gc)*sum(mTEPES.pIndBinUnitInvest[gc] for gc in mTEPES.gc):
            for p,gc in mTEPES.p*mTEPES.gc:
                if mTEPES.pIndBinUnitInvest[gc] != 0:
                    OptModel.vGenerationInvest[p,gc].fix(round(OptModel.vGenerationInvest[p,gc]()))
                else:
                    OptModel.vGenerationInvest[p,gc].fix(      OptModel.vGenerationInvest[p,gc]())
        if mTEPES.pIndBinGenRetire()*len(mTEPES.gd)*sum(mTEPES.pIndBinUnitRetire[gd] for gd in mTEPES.gd):
            for p,gd in mTEPES.p*mTEPES.gd:
                if mTEPES.pIndBinUnitRetire[gd] != 0:
                    OptModel.vGenerationRetire[p,gd].fix(round(OptModel.vGenerationRetire[p,gd]()))
                else:
                    OptModel.vGenerationRetire[p,gd].fix(      OptModel.vGenerationRetire[p,gd]())
        if mTEPES.pIndBinNetInvest()*len(mTEPES.lc)*sum(mTEPES.pIndBinLineInvest[lc] for lc in mTEPES.lc):
            for p,ni,nf,cc in mTEPES.p*mTEPES.lc:
                if mTEPES.pIndBinLineInvest[ni,nf,cc] != 0:
                    OptModel.vNetworkInvest[p,ni,nf,cc].fix(round(OptModel.vNetworkInvest[p,ni,nf,cc]()))
                else:
                    OptModel.vNetworkInvest[p,ni,nf,cc].fix(      OptModel.vNetworkInvest[p,ni,nf,cc]())
        if mTEPES.pIndBinGenOperat()*len(mTEPES.nr)*sum(mTEPES.pIndBinUnitCommit[nr] for nr in mTEPES.nr):
            for p,sc,n,nr in mTEPES.psnnr:
                if mTEPES.pIndBinUnitCommit[nr] != 0:
                    OptModel.vCommitment[p,sc,n,nr].fix(round(OptModel.vCommitment[p,sc,n,nr]()))
                    OptModel.vStartUp   [p,sc,n,nr].fix(round(OptModel.vStartUp   [p,sc,n,nr]()))
                    OptModel.vShutDown  [p,sc,n,nr].fix(round(OptModel.vShutDown  [p,sc,n,nr]()))
        if mTEPES.pIndBinLineCommit()*len(mTEPES.la)*sum(mTEPES.pIndBinLineSwitch[la] for la in mTEPES.la):
            for p,sc,n,ni,nf,cc in mTEPES.psnla:
                if mTEPES.pIndBinLineSwitch[ni,nf,cc] != 0:
                    OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(round(OptModel.vLineCommit   [p,sc,n,ni,nf,cc]()))
                    OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(round(OptModel.vLineOnState  [p,sc,n,ni,nf,cc]()))
                    OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(round(OptModel.vLineOffState [p,sc,n,ni,nf,cc]()))
                elif (ni,nf,cc) in mTEPES.lc:
                    OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(round(OptModel.vNetworkInvest[p,     ni,nf,cc]()))
        if len(mTEPES.g2g):
            for nr in mTEPES.nr:
                if sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g):
                    OptModel.vMaxCommitment[nr].fix(round(OptModel.vMaxCommitment[nr]()))
        OptModel.dual = Suffix(direction=Suffix.IMPORT)
        OptModel.rc   = Suffix(direction=Suffix.IMPORT)
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, warmstart=False)   # tee=True displays the log of the solver
        SolverResults.write()                                                                  # summary of the solver results

    SolvingTime = time.time() - StartTime
    print('Solution time                                ... ', round(SolvingTime), 's')
    print('Total system            cost [MEUR]              ', OptModel.eTotalSCost.expr())
    for p,sc in mTEPES.ps:
        print('***** Period: '+str(p)+', Scenario: '+str(sc)+' ******')
        print('      Total generation  investment cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pGenInvestCost[gc      ] * OptModel.vGenerationInvest[p,gc      ]() for gc       in mTEPES.gc))
        print('      Total generation  retirement cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pGenRetireCost[gd      ] * OptModel.vGenerationRetire[p,gd      ]() for gd       in mTEPES.gd))
        print('      Total network     investment cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pNetFixedCost [ni,nf,cc] * OptModel.vNetworkInvest   [p,ni,nf,cc]() for ni,nf,cc in mTEPES.lc))
        print('      Total generation  operation  cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb     [p,sc    ] * OptModel.vTotalGCost      [p,sc,n    ]() for n        in mTEPES.n ))
        print('      Total consumption operation  cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb     [p,sc    ] * OptModel.vTotalCCost      [p,sc,n    ]() for n        in mTEPES.n ))
        print('      Total emission               cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb     [p,sc    ] * OptModel.vTotalECost      [p,sc,n    ]() for n        in mTEPES.n ))
        print('      Total reliability            cost [MEUR]   ', sum(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb     [p,sc    ] * OptModel.vTotalRCost      [p,sc,n    ]() for n        in mTEPES.n ))
