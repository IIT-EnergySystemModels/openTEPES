"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 02, 2026
"""

import os
import time
import psutil
import subprocess
import importlib
import pandas as pd
import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set, RangeSet, Param, Var, NonNegativeReals, Binary, UnitInterval, Reals, Constraint, Objective, minimize, Suffix
from   pyomo.opt     import SolverFactory

try:
    from . import openTEPES_ProblemSolvingStageSolve   as oSS
    from . import openTEPES_ModelFormulationInvestment as oMFI
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES import openTEPES_ProblemSolvingStageSolve   as oSS
    from openTEPES import openTEPES_ModelFormulationInvestment as oMFI


def StageDecomposition(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc, st, _path, pIndCycleFlow):
    print('Time Benders decomposition             ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    mMaster = ConcreteModel('Master problem')
    # maximum number of Benders iterations
    if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.ec) + len(mTEPES.lc) == 0:
        mMaster.itBd = RangeSet(1)
    else:
        mMaster.itBd = RangeSet(22)
    mMaster.iter = Set(doc='iterations')

    mMaster.vTotalSCost     = Var(                within=NonNegativeReals, doc='total system            cost [MEUR]')
    mMaster.vTotalICost     = Var(                within=NonNegativeReals, doc='total system investment cost [MEUR]')
    mMaster.vTotalFElecCost = Var(mTEPES.p,       within=NonNegativeReals, doc='total system fixed      cost [MEUR]')
    mMaster.vTheta          = Var(initialize=0.0, within=Reals,            doc='total system variable   cost [MEUR]')

    if mTEPES.pIndBinGenInvest() == 0:
        mMaster.vGenerationInvest = Var(mTEPES.pgc, within=UnitInterval, doc='generation investment decision exists in a year [0,1]')
    else:
        mMaster.vGenerationInvest = Var(mTEPES.pgc, within=Binary,       doc='generation investment decision exists in a year {0,1}')

    if mTEPES.pIndBinGenRetire() == 0:
        mMaster.vGenerationRetire = Var(mTEPES.pgd, within=UnitInterval, doc='generation retirement decision exists in a year [0,1]')
    else:
        mMaster.vGenerationRetire = Var(mTEPES.pgd, within=Binary,       doc='generation retirement decision exists in a year {0,1}')

    if mTEPES.pIndBinNetElecInvest() == 0:
        mMaster.vNetworkInvest    = Var(mTEPES.plc, within=UnitInterval, doc='network    investment decision exists in a year [0,1]')
    else:
        mMaster.vNetworkInvest    = Var(mTEPES.plc, within=Binary,       doc='network    investment decision exists in a year {0,1}')

    def eTotalSCost(mMaster):
        return mMaster.vTotalSCost
    mMaster.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalTCost(mMaster):
        return mMaster.vTotalSCost == mMaster.vTotalICost + mMaster.vTheta
    mMaster.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system       cost [MEUR]')

    def eBd_Cuts(mMaster, iter):
        return mMaster.vTheta - pTotalOCost_it[iter] >= (- sum(pGenerationInvestMarginalG_it[iter,p,gc      ] * (pGenerationInvest[iter,p,gc      ] - mMaster.vGenerationInvest[p,gc      ]) for p,gc       in mTEPES.pgc)
                                                         - sum(pGenerationInvestMarginalR_it[iter,p,gd      ] * (pGenerationRetire[iter,p,gd      ] - mMaster.vGenerationRetire[p,gd      ]) for p,gd       in mTEPES.pgd)
                                                         - sum(pNetworkInvestMarginalCap_it [iter,p,ni,nf,cc] * (pNetworkInvest   [iter,p,ni,nf,cc] - mMaster.vNetworkInvest   [p,ni,nf,cc]) for p,ni,nf,cc in mTEPES.plc))

    oMFI.InvestmentElecModelFormulation(mMaster, mTEPES, pIndLogConsole)

    OptModel.dual                     = Suffix(direction=Suffix.IMPORT)
    mTEPES.pTotalOCost                = Param(initialize=0.0, doc='total system operation cost                [MEUR]', mutable=True)
    mTEPES.pGenerationInvestMarginalG = Param(mTEPES.pgc,     doc='marginal of generation investment decision [MEUR]', mutable=True)
    mTEPES.pGenerationInvestMarginalR = Param(mTEPES.pgd,     doc='marginal of generation retirement decision [MEUR]', mutable=True)
    mTEPES.pGenerationInvestMarginalE = Param(mTEPES.pec,     doc='marginal of generation investment decision [MEUR]', mutable=True)
    mTEPES.pNetworkInvestMarginalCap  = Param(mTEPES.plc,     doc='marginal of network    investment decision [MEUR]', mutable=True)

    Solver = SolverFactory(SolverName)

    pTotalOCost_it = pd.Series([0.0]*len(mMaster.itBd), index=mMaster.itBd)

    if len(mTEPES.gc):
        pGenerationInvest             = pd.Series([0.0]*len(mMaster.itBd*mTEPES.pgc), index=mMaster.itBd*mTEPES.pgc)
        pGenerationInvestMarginalG_it = pd.Series([0.0]*len(mMaster.itBd*mTEPES.pgc), index=mMaster.itBd*mTEPES.pgc)
    if len(mTEPES.gd):
        pGenerationRetire             = pd.Series([0.0]*len(mMaster.itBd*mTEPES.pgd), index=mMaster.itBd*mTEPES.pgd)
        pGenerationInvestMarginalR_it = pd.Series([0.0]*len(mMaster.itBd*mTEPES.pgd), index=mMaster.itBd*mTEPES.pgd)
    if len(mTEPES.ec):
        pGenerationInvestMarginalE_it = pd.Series([0.0]*len(mMaster.itBd*mTEPES.pec), index=mMaster.itBd*mTEPES.pec)
    if len(mTEPES.lc):
        pNetworkInvest                = pd.Series([0.0]*len(mMaster.itBd*mTEPES.plc), index=mMaster.itBd*mTEPES.plc)
        pNetworkInvestMarginalCap_it  = pd.Series([0.0]*len(mMaster.itBd*mTEPES.plc), index=mMaster.itBd*mTEPES.plc)

    # # launch processes to allow parallel solution. Only needed with pyro as solver manager factory
    # if pIndSequentialSolving == 0:
    #     subprocess.Popen('pyomo_ns       -n localhost')
    #     subprocess.Popen('dispatch_srvr  -n localhost')
    #     subprocess.Popen('pyro_mip_server --traceback')
    #     subprocess.Popen('pyro_mip_server --traceback')

    # initialization
    Z_Lower = float('-inf')
    Z_Upper = float(' inf')

    # Benders algorithm
    mMaster.vTheta.fix(0)
    itBdFinal = 0
    itBdOptml = 0
    for itBd in mMaster.itBd:
        if ((abs(1-Z_Lower/Z_Upper) > mTEPES.pBdTol or itBd == 1) and Z_Lower < Z_Upper) or itBdFinal <= 9999:

            if SolverName == 'gurobi':
                Solver.options['OutputFlag'] = 0
                Solver.options['LogFile'   ] = f'{_path}/openTEPES_gurobi_Mst_{CaseName}_{p}_{sc}_{st}.log'
                Solver.options['MIPGap'    ] = 0.03
                Solver.options['Threads'   ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)

            if pIndLogConsole == 1:
                StartTime         = time.time()
                mMaster.write(f'{_path}/openTEPES_Mst_itBd{itBd}_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                WritingLPFileTime = time.time() - StartTime
                StartTime         = time.time()
                print('Input data                             ****')
                print('Writing MST LP file iteration', itBd, '       ... ', round(WritingLPFileTime), 's')

            # in normal Benders iterations
            if itBdFinal < 9999:
                # solving master problem
                SolverResultsMst = Solver.solve(mMaster)
                pTotalSCost      = mMaster.vTotalSCost()

                # storing the master solution and fixing investment decision for the subproblem
                for p,gc       in mTEPES.pgc:
                    pGenerationInvest         [itBd,p,gc      ] = mMaster.vGenerationInvest[          p,gc      ]()
                    OptModel.vGenerationInvest[     p,gc      ].fix(      pGenerationInvest[itBd,     p,gc      ])
                for p,gd       in mTEPES.pgd:
                    pGenerationRetire         [itBd,p,gd      ] = mMaster.vGenerationRetire[          p,gd      ]()
                    OptModel.vGenerationRetire[     p,gd      ].fix(      pGenerationRetire[itBd,     p,gd      ])
                for p,ni,nf,cc in mTEPES.plc:
                    pNetworkInvest            [itBd,p,ni,nf,cc] = mMaster.vNetworkInvest   [          p,ni,nf,cc]()
                    OptModel.vNetworkInvest   [     p,ni,nf,cc].fix(      pNetworkInvest   [itBd,     p,ni,nf,cc])
            else:
                # fixing investment decision for the subproblem for the final Benders iteration
                for p          in mTEPES.p:
                    OptModel.vTotalFElecCost  [     p         ].fix(      mMaster.vTotalFElecCost[p]())
                for p,gc       in mTEPES.pgc:
                    pGenerationInvest         [itBd,p,gc      ] =         pGenerationInvest[itBdOptml,p,gc      ]
                    OptModel.vGenerationInvest[     p,gc      ].fix(      pGenerationInvest[itBdOptml,p,gc      ])
                for p,gd       in mTEPES.pgd:
                    pGenerationRetire         [itBd,p,gd      ] =         pGenerationRetire[itBdOptml,p,gd      ]
                    OptModel.vGenerationRetire[     p,gd      ].fix(      pGenerationRetire[itBdOptml,p,gd      ])
                for p,ni,nf,cc in mTEPES.plc:
                    pNetworkInvest            [itBd,p,ni,nf,cc] =         pNetworkInvest   [itBdOptml,p,ni,nf,cc]
                    OptModel.vNetworkInvest   [     p,ni,nf,cc].fix(      pNetworkInvest   [itBdOptml,p,ni,nf,cc])

            # after the first iteration free vTheta
            if itBd == 1:
                mMaster.vTheta.free()

            oSS.StageSolve(OptModel, mTEPES, DirName, CaseName, SolverName, pIndLogConsole, _path, pIndCycleFlow, itBd, itBdFinal)

            pTotalOCost          = mTEPES.pTotalOCost()
            pTotalOCost_it[itBd] = pTotalOCost

            # save the iteration if the o.f. strictly improves
            if Z_Upper >= pTotalSCost - mMaster.vTheta() + pTotalOCost and itBdFinal < 9999:
                itBdOptml = itBd
                print('Iteration Optimal ', itBdOptml)

            # updating lower and upper bound
            Z_Lower =                  pTotalSCost
            if itBdFinal < 9999:
                Z_Upper = min(Z_Upper, pTotalSCost - mMaster.vTheta() + pTotalOCost)
            OptModel.vTotalSCost = Z_Upper
            print('Iteration         ', itBd, ' Lower bound [MEUR]  ... ', Z_Lower)
            print('Iteration         ', itBd, ' Upper bound [MEUR]  ... ', Z_Upper)

            # after convergence allow a final iteration with the optimal solution of the master problem
            if abs(1 - Z_Lower/Z_Upper) < mTEPES.pBdTol and itBd > 1 and itBdFinal < 9999:
                itBdFinal  = 9999
                print('Iteration Final   ', itBdFinal)
            else:
                itBdFinal += 1

            for p,gc       in mTEPES.pgc:
                pGenerationInvestMarginalG_it[itBd,p,gc      ] = mTEPES.pGenerationInvestMarginalG[p,gc      ]()
            for p,gd       in mTEPES.pgd:
                pGenerationInvestMarginalR_it[itBd,p,gd      ] = mTEPES.pGenerationInvestMarginalR[p,gd      ]()
            for p,ec       in mTEPES.pec:
                pGenerationInvestMarginalE_it[itBd,p,ec      ] = mTEPES.pGenerationInvestMarginalE[p,ec      ]()
            for p,ni,nf,cc in mTEPES.plc:
                pNetworkInvestMarginalCap_it [itBd,p,ni,nf,cc] = mTEPES.pNetworkInvestMarginalCap [p,ni,nf,cc]()

            # delete Benders cuts because they are regenerated in each iteration
            if itBd > 1:
                mMaster.del_component(mMaster.eBd_Cuts)
            # add one cut
            mMaster.iter.add(itBd)
            iter = mMaster.iter
            mMaster.eBd_Cuts = Constraint(mMaster.iter, rule=eBd_Cuts, doc='Benders cuts')
            # Benders cuts are considered as lazy
            # for iter in mMaster.iter:
            #     Solver.set_linear_constraint_attr(mMaster.eBd_Cuts[iter], 'Lazy', 1)
    
    SolvingTime = time.time() - StartTime
    print('Time Benders decomposition             ... ', round(SolvingTime), 's')
    
    print('Total system cost [MEUR]                   ', Z_Upper)
