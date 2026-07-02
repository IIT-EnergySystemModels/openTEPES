"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 02, 2026
"""

import math
import os
import time
import psutil
import pyomo.environ as pyo
import pandas as pd
from   collections   import defaultdict
from   pyomo.environ import ConcreteModel, Set, RangeSet, Var, NonNegativeReals, Reals, Constraint, ConstraintList, Objective, minimize, Suffix
from   pyomo.opt     import SolverFactory
from   pyomo.contrib import appsi
from   .openTEPES_ProblemSolving import ProblemSolving


def SectorDecomposition(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Sector Benders decomposition           ****')
    _path = os.path.join(DirName, CaseName)
    InitialTime = time.time()

    # Benders tolerance
    pBdTol = 1e-4

    # export Benders iterations
    pBdConvergenceFile     = os.path.join(_path, f'openTEPES_{SolverName}_BendersConvergence_{CaseName}.csv')

    # export sector Benders cuts at the end
    pSectorProxyRows = []
    pSectorProxyFile       = os.path.join(_path, f'oT_Result_SectorProxy_{CaseName}.csv')
    pSectorProxyPeriodFile = os.path.join(_path, f'oT_Result_SectorProxyPerPeriod_{CaseName}.csv')

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    n2l = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            n2l[el].append(nd)

    # area to generators (a2e)
    a2e = defaultdict(list)
    for ar,el in mTEPES.ar*mTEPES.el:
        if (ar,el) in mTEPES.a2g:
            a2e[el].append(ar)

    e2a = defaultdict(list)
    for ar,el in mTEPES.ar*mTEPES.el:
        if (ar,el) in mTEPES.a2g:
            e2a[ar].append(el)

    mMaster = ConcreteModel('Master problem')
    # maximum number of Benders iterations
    if len(mTEPES.psnel) == 0:
        mMaster.itBd = RangeSet(1)
    else:
        # mMaster.itBd = RangeSet(int(len(mTEPES.psnel)/20))
        mMaster.itBd = RangeSet(200)
    mMaster.itMst = Set(doc='iterations')

    mMaster.vTotalSCost     = Var(                within=Reals,            doc='total system cost [MEUR]'                 )
    mMaster.vTheta          = Var(                within=Reals,            doc='total system cost [MEUR]'                 )

    mMaster.vTotalOutput    = Var(mTEPES.psnel,   within=NonNegativeReals, doc='total output of the unit [GW]'            )
    mMaster.vESSTotalCharge = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS total charge power [GW]'              )
    mMaster.vCharge2ndBlock = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS       charge power [GW]'              )
    mMaster.vESSReserveUp   = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS upward   operating reserve [GW]'      )
    mMaster.vESSReserveDown = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS downward operating reserve [GW]'      )
    mMaster.vEnergyOutflows = Var(mTEPES.psnel,   within=NonNegativeReals, doc='scheduled outflows of all ESS units [GW]' )
    mMaster.vESSInventory   = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS inventory [GWh]'                      )
    mMaster.vIniInventory   = Var(mTEPES.psnel,   within=NonNegativeReals, doc='initial inventory for ESS candidate [GWh]')
    mMaster.vESSSpillage    = Var(mTEPES.psnel,   within=NonNegativeReals, doc='ESS spillage  [GWh]'                      )

    [mMaster.vTotalOutput   [p,sc,n,el].setub(mTEPES.pMaxPowerElec     [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vTotalOutput   [p,sc,n,el].setlb(mTEPES.pMinPowerElec     [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vESSTotalCharge[p,sc,n,el].setub(mTEPES.pMaxCharge        [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vCharge2ndBlock[p,sc,n,el].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vESSReserveUp  [p,sc,n,el].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vESSReserveDown[p,sc,n,el].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vEnergyOutflows[p,sc,n,el].setub(mTEPES.pMaxCapacity      [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vESSInventory  [p,sc,n,el].setlb(mTEPES.pMinStorage       [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vESSInventory  [p,sc,n,el].setub(mTEPES.pMaxStorage       [p,sc,n,el]()) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vIniInventory  [p,sc,n,el].setlb(mTEPES.pMinStorage       [p,sc,n,el]  ) for p,sc,n,el in mTEPES.psnel]
    [mMaster.vIniInventory  [p,sc,n,el].setub(mTEPES.pMaxStorage       [p,sc,n,el]()) for p,sc,n,el in mTEPES.psnel]

    for p,sc,n,el in mTEPES.psnel:
        # if no max power, no total output
        if mTEPES.pMaxPowerElec      [p,sc,n,el]   == 0.0:
            mMaster.vTotalOutput     [p,sc,n,el].fix( 0.0)
        # ESS with no charge capacity
        if  mTEPES.pMaxCharge        [p,sc,n,el]   == 0.0:
            mMaster.vESSTotalCharge  [p,sc,n,el].fix( 0.0)
        # ESS with no charge capacity and no inflows can't produce
        if  mTEPES.pTotalMaxCharge[el] == 0.0 and mTEPES.pTotalEnergyInflows[el] == 0.0:
            mMaster.vTotalOutput     [p,sc,n,el].fix( 0.0)
            mMaster.vOutput2ndBlock  [p,sc,n,el].fix( 0.0)
            mMaster.vRelerveUp       [p,sc,n,el].fix( 0.0)
            mMaster.vReserveDown     [p,sc,n,el].fix( 0.0)
            mMaster.vESSSpillage     [p,sc,n,el].fix( 0.0)
            mMaster.vESSInventory    [p,sc,n,el].fix( 0.0)
        if  mTEPES.pMaxCharge2ndBlock[p,sc,n,el]   == 0.0:
            mMaster.vCharge2ndBlock  [p,sc,n,el].fix( 0.0)
        if  mTEPES.pMaxCharge2ndBlock[p,sc,n,el]   == 0.0 or mTEPES.pIndOperReserveCon[el]:
            mMaster.vESSReserveUp    [p,sc,n,el].fix( 0.0)
            mMaster.vESSReserveDown  [p,sc,n,el].fix( 0.0)
        if  mTEPES.pMaxStorage       [p,sc,n,el]() == 0.0:
            mMaster.vESSInventory    [p,sc,n,el].fix( 0.0)

    # if no operating reserve is required, no variables are needed
    for p,sc,n,ar,el in mTEPES.psn*mTEPES.ar*mTEPES.el:
        if el in e2a[ar] and (p,sc,n,el) in mTEPES.psnel:
            if mTEPES.pOperReserveUp   [p,sc,n,ar] ==  0.0:
                mMaster.vESSReserveUp  [p,sc,n,el].fix(0.0)
            if mTEPES.pOperReserveDw   [p,sc,n,ar] ==  0.0:
                mMaster.vESSReserveDown[p,sc,n,el].fix(0.0)

    # if there are no energy outflows, no variable is needed
    for el in mTEPES.el:
        if sum(mTEPES.pEnergyOutflows[p,sc,n,el]() for p,sc,n in mTEPES.psn if (p,el) in mTEPES.peh) == 0.0:
            for p,sc,n in mTEPES.psn:
                if (p,el) in mTEPES.peh:
                    mMaster.vEnergyOutflows[p,sc,n,el].fix(0.0)

    def eTotalSCost(mMaster):
        return mMaster.vTotalSCost
    mMaster.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalTCost(mMaster):
        return mMaster.vTotalSCost == mMaster.vTheta
    mMaster.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system cost [MEUR]')

    def eBd_Cuts(mMaster, itMst):
        return mMaster.vTheta - pTotalSCost_it[itMst] >= - sum(pESSTotalChargeMarginal_it[itMst,p,sc,n,el] * (pESSTotalCharge[itMst,p,sc,n,el] - mMaster.vESSTotalCharge[p,sc,n,el]) for p,sc,n,el in mTEPES.psnel)
    mMaster.eBd_Cuts = ConstraintList(doc='Benders cuts')

    # this equation is directly taken from ModelFormulation
    def eESSInventory(mMaster,n,es):
        if (p,es) not in mTEPES.pes or (p,sc,st,n) not in mTEPES.s2n or (mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0):
            return Constraint.Skip
        if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
            if es not in mTEPES.ec:
                return mTEPES.pIniInventory[p,sc,n,es]()                                           + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mMaster.vEnergyOutflows[p,sc,n2,es] - mMaster.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * mMaster.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == mMaster.vESSInventory[p,sc,n,es] + mMaster.vESSSpillage[p,sc,n,es]
            else:
                return mMaster.vIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[p,sc,n2]()*(mMaster.vEnergyInflows[p,sc,n2,es]  - mMaster.vEnergyOutflows[p,sc,n2,es] - mMaster.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * mMaster.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == mMaster.vESSInventory[p,sc,n,es] + mMaster.vESSSpillage[p,sc,n,es]
        elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
            if es not in mTEPES.ec:
                return mMaster.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mMaster.vEnergyOutflows[p,sc,n2,es] - mMaster.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * mMaster.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == mMaster.vESSInventory[p,sc,n,es] + mMaster.vESSSpillage[p,sc,n,es]
            else:
                return mMaster.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mMaster.vEnergyInflows[p,sc,n2,es]  - mMaster.vEnergyOutflows[p,sc,n2,es] - mMaster.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * mMaster.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == mMaster.vESSInventory[p,sc,n,es] + mMaster.vESSSpillage[p,sc,n,es]
        else:
            return Constraint.Skip
    setattr(mMaster, f'eESSInventory_{p}_{sc}_{st}', Constraint(mTEPES.nesl, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    # this equation is directly taken from ModelFormulation
    def eMaxCharge(mMaster,n,eh):
        # Check if the generator is available in the period and has variable charging capacity
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        # Hydro units have commitment while ESS units are implicitly always committed
        if eh not in mTEPES.h:
            # ESS units only need this constraint when they can offer operating reserves and the systems demands reserves
            if mTEPES.pIndOperReserveCon[eh] or sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0:
                return Constraint.Skip
            # ESS case equation
            return (mMaster.vCharge2ndBlock[p,sc,n,eh] + mMaster.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0
        # Hydro case equation
        else:
            return (mMaster.vCharge2ndBlock[p,sc,n,eh] + mMaster.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= mMaster.vCommitmentCons[p,sc,n,eh]
    setattr(mMaster, f'eMaxCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.el, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    # this equation is directly taken from ModelFormulation
    def eESSTotalCharge(mMaster,n,eh):
        # Check if the generator is available in the period
        # Constraint only applies to generators with charging capabilities
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        # Hydro generators can have binary commitment, energy modeled ESS do not have commitment
        # ESS Generator
        if eh not in mTEPES.h:
            # Check the minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                return mMaster.vESSTotalCharge[p,sc,n,eh]                                ==        mMaster.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * mMaster.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * mMaster.vESSReserveUp[p,sc,n,eh]
            else:
                return mMaster.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == 1.0 + (mMaster.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * mMaster.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * mMaster.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
        # Hydro generator
        else:
            # Check the minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                return mMaster.vESSTotalCharge[p,sc,n,eh]                                ==                                       mMaster.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * mMaster.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * mMaster.vESSReserveUp[p,sc,n,eh]
            else:
                return mMaster.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == mMaster.vCommitmentCons[p,sc,n,eh] + (mMaster.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * mMaster.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * mMaster.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
    setattr(mMaster, f'eESSTotalCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.el, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    pTotalSCost_it = pd.Series([0.0]*len(mMaster.itBd), index=mMaster.itBd)
    # pMasterCost_it = pd.Series([0.0]*len(mMaster.itBd), index=mMaster.itBd)
    Z_Lower_it     = pd.Series([0.0]*len(mMaster.itBd), index=mMaster.itBd)

    if len(mTEPES.psnel):
        pESSTotalCharge            = pd.Series([0.0]*len(mMaster.itBd*mTEPES.psnel), index=mMaster.itBd*mTEPES.psnel)
        # pCharge2ndBlock            = pd.Series([0.0]*len(mMaster.itBd*mTEPES.psnel), index=mMaster.itBd*mTEPES.psnel)
        # pESSReserveUp              = pd.Series([0.0]*len(mMaster.itBd*mTEPES.psnel), index=mMaster.itBd*mTEPES.psnel)
        # pESSReserveDown            = pd.Series([0.0]*len(mMaster.itBd*mTEPES.psnel), index=mMaster.itBd*mTEPES.psnel)
        pESSTotalChargeMarginal_it = pd.Series([0.0]*len(mMaster.itBd*mTEPES.psnel), index=mMaster.itBd*mTEPES.psnel)

    # initialization
    Z_Lower = -math.inf
    Z_Upper =  math.inf
    pBdConvergenceRows = []

    # Benders algorithm
    mMaster.vTheta.fix(0.0)
    itBdFinal = 0
    itBdOptml = 0
    for itBd in mMaster.itBd:
        if ((abs(1.0-Z_Lower/Z_Upper) > pBdTol or itBd == 1) and Z_Lower < Z_Upper) or itBdFinal <= 9999:

            if pIndLogConsole:
                StartTime         = time.time()
                mMaster.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}_Mst_itBd{itBd}.lp', io_options={'symbolic_solver_labels': True})
                WritingLPFileTime = time.time() - StartTime
                StartTime         = time.time()
                print('Writing Mst LP file iteration', itBd, '       ... ', round(WritingLPFileTime), 's')

            print('Problem solving master                 ####', itBd)

            FileName = f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}_Mst_itBd{itBd}.log'
            if os.path.exists(FileName):
                os.remove(FileName)

            # solving the master problem
            if SolverName != 'gurobi_persistent':
                SolverMst = SolverFactory(SolverName)
            if SolverName in ('appsi_cplex', 'appsi_gurobi', 'gurobi_persistent'):
                solver_attr = f'_{SolverName}_solver'
                init_attr   = f'_{SolverName}_initialized'
                if not hasattr(mMaster, solver_attr):
                    setattr(mMaster, solver_attr, SolverFactory(SolverName))
                if SolverName == 'gurobi_persistent':
                    SolverMst = getattr(mMaster, solver_attr)
                if itBd == 2 or not getattr(mMaster, init_attr, False):
                    SolverMst.set_instance(mMaster)
                    setattr(mMaster, init_attr, True)

            if SolverName in ('gurobi', 'gurobi_direct', 'appsi_gurobi'):
                SolverMst.options['OutputFlag'       ] =   0
                # SolverMst.options['LogFile'        ] = FileName
                SolverMst.options['DisplayInterval'  ] = 100
                SolverMst.options['LPWarmStart'      ] =   2
                # SolverMst.options['LazyConstraints'] =   1   # works only for MIP problems
                SolverMst.options['Method'           ] =  -1
                SolverMst.options['Threads'          ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
            if SolverName == 'gurobi_persistent':
                SolverMst.set_gurobi_param('OutputFlag',        0)
                # SolverMst.set_gurobi_param('LogFile',  FileName)
                SolverMst.set_gurobi_param('DisplayInterval', 100)
                SolverMst.set_gurobi_param('LPWarmStart',       2)
                # SolverMst.set_gurobi_param('LazyConstraints', 1)
                SolverMst.set_gurobi_param('Method',           -1)
                SolverMst.set_gurobi_param('Threads', int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))

            # solving the master problem
            StartTime = time.time()
            if SolverName in ('gurobi', 'gurobi_direct', 'appsi_gurobi'):
                MasterResults = SolverMst.solve(mMaster, tee=False, report_timing=False)
            if SolverName == 'gurobi_persistent':
                MasterResults = SolverMst.solve(mMaster, tee=False, report_timing=False, warmstart=True, keepfiles=False, load_solutions=True, save_results=False)
            MstSolvingTime = time.time() - StartTime
            StartTime = time.time()

            # # After each solve, mark ALL Benders cuts already in the backend as Lazy.
            # # appsi_gurobi and appsi_cplex only add new constraints to the backend during solve() (via check_for_new_or_removed_constraints=True),
            # # so the cut added in the previous iteration is now available in _pyomo_con_to_solver_con_map and can be flagged.
            # if itBd > 1 and (SolverName in ('appsi_gurobi', 'appsi_cplex')):
            #     try:
            #         # grb = SolverMst._solver_model
            #         # grb.update()
            #         # n_lazy = 0
            #         # for idx in mMaster.eBd_Cuts:
            #         #     cut_data = mMaster.eBd_Cuts[idx]
            #         #     if cut_data in SolverMst._pyomo_con_to_solver_con_map:
            #         #         grb_con      = SolverMst._pyomo_con_to_solver_con_map[cut_data]
            #         #         grb_con.Lazy = 1
            #         #         n_lazy      += 1
            #         # grb.update()
            #         Solver = SolverMst._solver_model
            #         backend_cuts = [
            #             SolverMst._pyomo_con_to_solver_con_map[mMaster.eBd_Cuts[idx]]
            #             for idx in mMaster.eBd_Cuts
            #             if mMaster.eBd_Cuts[idx] in SolverMst._pyomo_con_to_solver_con_map
            #         ]
            #         if backend_cuts:
            #             # Mark constraints as lazy in appsi_gurobi or appsi_cplex using LazyConstraint attribute
            #             if   SolverName == 'appsi_gurobi':
            #                Solver.setAttr('Lazy', backend_cuts, [1] * len(backend_cuts))
            #                Solver.update()
            #             elif SolverName == 'appsi_cplex':
            #                 Solver.set_constraint_types([SolverMst._pyomo_con_to_solver_con_map[mMaster.eBd_Cuts[idx]] for idx in mMaster.eBd_Cuts if mMaster.eBd_Cuts[idx] in SolverMst._pyomo_con_to_solver_con_map], Solver.constraint_type.user_cut)
            #
            #         # Export backend model and attributes after Lazy flags are set.
            #         Solver.write(f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}_Mst_itBd{itBd}.mps')
            #         Solver.write(f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}_Mst_itBd{itBd}.attr')
            #     except Exception as _ex:
            #         print(f'could not mark Benders cuts as Lazy with appsi_gurobi: {_ex}')

            # in normal Benders iterations
            if itBdFinal < 9999:

                # storing the master solution and fixing electrolyzer decisions for the subproblem
                for p,sc,n,el in mTEPES.psnel:
                    pESSTotalCharge         [itBd,p,sc,n,el] = 0.0 if itBd == 1 else mMaster.vESSTotalCharge[p,sc,n,el]()
                    # pESSTotalCharge           [itBd,p,sc,n,el] = OptModel.vESSTotalCharge[p,sc,n,el]() if itBd == 1 else mMaster.vESSTotalCharge[p,sc,n,el]()
                    # pCharge2ndBlock         [itBd,p,sc,n,el] = OptModel.vCharge2ndBlock[p,sc,n,el]() if itBd == 1 else mMaster.vCharge2ndBlock[p,sc,n,el]()
                    # pESSReserveUp           [itBd,p,sc,n,el] = OptModel.vESSReserveUp  [p,sc,n,el]() if itBd == 1 else mMaster.vESSReserveUp  [p,sc,n,el]()
                    # pESSReserveDown         [itBd,p,sc,n,el] = OptModel.vESSReserveDown[p,sc,n,el]() if itBd == 1 else mMaster.vESSReserveDown[p,sc,n,el]()
                    # pEnergyOutflows         [itBd,p,sc,n,el] = OptModel.vEnergyOutflows[p,sc,n,el]() if ItBd == 1 else mMaster.vEnergyOutflows[p,sc,n,el]()
                    # OptModel.vESSTotalCharge[     p,sc,n,el].fix  (pESSTotalCharge[itBd,p,sc,n,el])
                    OptModel.vESSTotalCharge[     p,sc,n,el].setlb(pESSTotalCharge[itBd,p,sc,n,el])
                    OptModel.vESSTotalCharge[     p,sc,n,el].setub(pESSTotalCharge[itBd,p,sc,n,el])
                    # OptModel.vCharge2ndBlock[     p,sc,n,el].fix(pCharge2ndBlock [itBd,p,sc,n,el])
                    # OptModel.vESSReserveUp  [     p,sc,n,el].fix(pESSReserveUp   [itBd,p,sc,n,el])
                    # OptModel.vESSReserveDown[     p,sc,n,el].fix(pESSReserveDown [itBd,p,sc,n,el])
                    # OptModel.vEnergyOutflows[     p,sc,n,el].fix(pvEnergyOutflows[itBd,p,sc,n,el])
            else:
                # fixing electrolyzer decisions for the subproblem for the final Benders iteration
                for p,sc,n,el in mTEPES.psnel:
                    pESSTotalCharge         [itBd,p,sc,n,el] =     pESSTotalCharge[itBdOptml,p,sc,n,el]
                    # OptModel.vESSTotalCharge[     p,sc,n,el].fix  (pESSTotalCharge[itBdOptml,p,sc,n,el])
                    OptModel.vESSTotalCharge[     p,sc,n,el].setlb(pESSTotalCharge[itBdOptml,p,sc,n,el])
                    OptModel.vESSTotalCharge[     p,sc,n,el].setub(pESSTotalCharge[itBdOptml,p,sc,n,el])
                    # OptModel.vCharge2ndBlock[     p,sc,n,el].fix(pCharge2ndBlock [itBdOptml,p,sc,n,el])
                    # OptModel.vESSReserveUp  [     p,sc,n,el].fix(pESSReserveUp   [itBdOptml,p,sc,n,el])
                    # OptModel.vESSReserveDown[     p,sc,n,el].fix(pESSReserveDown [itBdOptml,p,sc,n,el])
                    # OptModel.vEnergyOutflows[     p,sc,n,el].fix(pvEnergyOutflows[itBdOptml,p,sc,n,el])

            if pIndLogConsole:
                StartTime         = time.time()
                OptModel.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}_Sbp_itBd{itBd}.lp', io_options={'symbolic_solver_labels': True})
                WritingLPFileTime = time.time() - StartTime
                StartTime         = time.time()
                print('Writing Sbp LP file iteration', itBd, '       ... ', round(WritingLPFileTime), 's')

            # solving the subproblem
            StartTime      = time.time()
            ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, itBd)
            SbpSolvingTime = time.time() - StartTime
            StartTime      = time.time()

            # rename the subproblem log to keep one file per Benders iteration.
            if SolverName in ('gurobi', 'gurobi_direct'):
                pSubproblemLogSrc = f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}.log'
                pSubproblemLogDst = f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}_Sbp_itBd{itBd}.log'
                if os.path.exists(pSubproblemLogSrc):
                    if os.path.exists(pSubproblemLogDst):
                        os.remove(pSubproblemLogDst)
                    os.replace(pSubproblemLogSrc, pSubproblemLogDst)

            pTotalSCost_it[itBd] = OptModel.vTotalSCost()
            print('  Total system                 cost [MEUR] ', OptModel.vTotalSCost())

            # get the duals for the Benders cuts
            pESSTotalChargeMarginal = pd.Series([0.0] * len(mTEPES.psnel), index=mTEPES.psnel)
            for p,sc,n,el in mTEPES.psnel:
                if el in mTEPES.ec:
                    pESSTotalChargeMarginal    [p,sc,n,el] -= mTEPES.pDuals[ f"eInstallConESS_{p}_{sc}_{st}('{n}', '{el}')"]        /mTEPES.pMaxCharge[p,sc,n,el]
                pESSTotalChargeMarginal        [p,sc,n,el] += mTEPES.pDuals[   f"eBalanceElec_{p}_{sc}_{st}('{n}', '{n2l[el][0]}')"]
                pESSTotalChargeMarginal        [p,sc,n,el] -= mTEPES.pDuals[  f"eESSInventory_{p}_{sc}_{st}('{n}', '{el}')"]        *mTEPES.pDuration[p,sc,n]()*math.sqrt(mTEPES.pEfficiency[el])
                if mTEPES.pShiftTime[el]:
                    pESSTotalChargeMarginal    [p,sc,n,el] -= mTEPES.pDuals[  f"eMaxShiftTime_{p}_{sc}_{st}('{n}', '{el}')"]        *mTEPES.pDuration[p,sc,n]()*          mTEPES.pEfficiency[el]
                pESSTotalChargeMarginal        [p,sc,n,el] -= mTEPES.pDuals[f"eESSTotalCharge_{p}_{sc}_{st}('{n}', '{el}')"]
                pESSTotalChargeMarginal        [p,sc,n,el] -= mTEPES.pDuals[     f"eBalanceH2_{p}_{sc}_{st}('{n}', '{n2l[el][0]}')"]*mTEPES.pDuration[p,sc,n]()/mTEPES.pProductionFunctionH2[el]
                pESSTotalChargeMarginal_it[itBd,p,sc,n,el] = pESSTotalChargeMarginal[p,sc,n,el]

            # save one row per (iteration, period, scenario, load level) and one independent column per electrolyzer
            pRowsByKey = {}
            for p,sc,n,el in mTEPES.psnel:
                pKey = (p, sc, n, itBd)
                if pKey not in pRowsByKey:
                    pRowsByKey[pKey] = {'Iteration': itBd, 'Period': p, 'Scenario': sc, 'LoadLevel': n,'TotalSystemCost_[MEUR]': pTotalSCost_it[itBd]}
                pRowsByKey[pKey][f'Consumption_{el}_[MW]'  ] = - pESSTotalCharge           [itBd,p,sc,n,el]*1e3
                pRowsByKey[pKey][f'Marginal_{el}_[EUR/MWh]'] = - pESSTotalChargeMarginal_it[itBd,p,sc,n,el]

            sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt] if (p,g) in mTEPES.pg)]
            if sPSNGT:
                OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                OutputToFile *= 1e3
                # add one production column per technology to the same rows
                for (p,sc,n,gt), val in OutputToFile.items():
                    pKey = (p, sc, n, itBd)
                    if pKey in pRowsByKey:
                        pRowsByKey[pKey][f'Production_{gt}_[MW]'] = val
            pSectorProxyRows.extend(pRowsByKey.values())

            # save the iteration if the o.f. strictly improves
            if Z_Upper >= OptModel.vTotalSCost() and itBdFinal < 9999:
                itBdOptml = itBd
                print('Iteration Optimal ', itBdOptml)

            # updating lower and upper bound
            Z_Lower          =         mMaster.vTotalSCost()
            # if itBd > 1:
            #     Z_Lower_it[itBd]     = mMaster.vTotalSCost()
                # pMasterCost_it[itBd] =  1.0 - Z_Lower/Z_Upper
            if itBdFinal < 9999:
                # if OptModel.vTotalSCost() < Z_Upper*(1-0.001):
                #     Z_Upper = OptModel.vTotalSCost()
                Z_Upper = min(Z_Upper, OptModel.vTotalSCost())
            print('Convergence error ', 1.0 - Z_Lower/Z_Upper, ' [p.u.]')
            print('Iteration         ', itBd, ' Lower bound [MEUR] ... ', Z_Lower, ' Rows', mMaster.nconstraints(), ' Columns', mMaster.nvariables(), ' Seconds', round(MstSolvingTime))
            print('Iteration         ', itBd, ' Upper bound [MEUR] ... ', Z_Upper, ' o.f. in this iteration ', OptModel.vTotalSCost(), ' Rows', OptModel.nconstraints(), ' Columns', OptModel.nvariables(), ' Seconds', round(SbpSolvingTime))

            # store structured convergence data for CSV export
            pBdConvergenceRows.append({'Iteration': itBd, 'ConvergenceError_[p.u.]': 1.0 - Z_Lower/Z_Upper, 'LowerBound_[MEUR]': Z_Lower, 'UpperBound_[MEUR]': Z_Upper, 'O.F.Iteration_[MEUR]': OptModel.vTotalSCost(), 'MstRows': mMaster.nconstraints(), 'MstCols': mMaster.nvariables(), 'MstSecs': round(MstSolvingTime), 'SbpRows': OptModel.nconstraints(), 'SbpCols': OptModel.nvariables(), 'SbpSecs': round(SbpSolvingTime)})

            # after convergence allow a final iteration with the optimal solution of the master problem
            if itBd > 1 and itBdFinal < 9999 and (abs(1 - Z_Lower/Z_Upper) < pBdTol):
                # or abs(1 - (1.0 - Z_Lower/Z_Upper) / pMasterCost_it[itBd-1]) < pBdTol
                itBdFinal  = 9999
                print('Iteration Final   ', itBdFinal)
            else:
                itBdFinal += 1

            # after the first iteration free vTheta
            if itBd == 1:
                mMaster.vTheta.free()
                mMaster.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
            # force a minimum improvement between iterations
            mMaster.vTheta.setlb(Z_Upper * (1 - 0.0001))

            # add one cut
            new_cut = mMaster.eBd_Cuts.add(eBd_Cuts(mMaster, itBd))
            if   SolverName in ('appsi_gurobi', 'appsi_cplex'):
                SolverMst.update_config.check_for_new_or_removed_params      = False
                SolverMst.update_config.check_for_new_or_removed_vars        = False
                SolverMst.update_config.check_for_new_or_removed_constraints = True
                SolverMst.update_config.update_params                        = False
                SolverMst.update_config.update_vars                          = False
                SolverMst.update_config.update_constraints                   = False
                SolverMst.update_config.update_named_expressions             = False
                SolverMst.config.load_solution                               = True
                SolverMst.config.warmstart                                   = True
                SolverMst.config.stream_solver                               = True
            elif SolverName == 'gurobi_persistent':
                SolverMst.add_constraint(new_cut)
                # Benders cuts are considered as lazy
                # SolverMst.set_linear_constraint_attr(new_cut, 'Lazy', 1)

    SolvingTime = time.time() - InitialTime
    print('Sector Benders decomposition           ****')
    print('  Total system                 cost [MEUR] ', Z_Upper, ' Seconds', round(SolvingTime))

    pDuals = {}
    # eBd_Cuts is a ConstraintList indexed by iteration (1,2,...)
    for iter in range(1, itBd):
        try:
            pDuals[f'eBd_Cuts{iter}'] = mMaster.dual[mMaster.eBd_Cuts[iter]]
        except KeyError:
            pDuals[f'eBd_Cuts{iter}'] = None

    pCutDualByIter = {}
    for iter in range(1,itBd):
        pCutDualByIter[iter] = pDuals.get('eBd_Cuts'+str(iter), None)

    # add one dual value per iteration row in BendersConvergence
    for row in pBdConvergenceRows:
        row['BendersCutDualVariable'] = pCutDualByIter.get(row['Iteration'], None)

    # write the Benders convergence file
    if pBdConvergenceRows:
        pBdConvergenceDF = pd.DataFrame(pBdConvergenceRows).sort_values(by='Iteration', ignore_index=True)
        pBdConvergenceDF.to_csv(pBdConvergenceFile, index=False)

    # export Benders cuts (wide format: one column per electrolyzer and one per technology)
    pSectorProxyDF = pd.DataFrame(pSectorProxyRows)
    pBaseCols = ['Iteration', 'Period', 'Scenario', 'LoadLevel', 'TotalSystemCost_[MEUR]']
    pConsCols = sorted([col for col in pSectorProxyDF.columns if col.startswith('Consumption_')])
    pMargCols = sorted([col for col in pSectorProxyDF.columns if col.startswith('Marginal_'   )])
    pProdCols = sorted([col for col in pSectorProxyDF.columns if col.startswith('Production_' )])
    pSectorProxyDF = pSectorProxyDF[pBaseCols + pConsCols + pMargCols + pProdCols]
    pSectorProxyDF.to_csv(pSectorProxyFile, index=False)

    # period aggregation over all Scenario and LoadLevel values
    pSectorProxyPeriodSrc = pSectorProxyDF.copy()
    pPeriodDur = pSectorProxyPeriodSrc.apply(lambda r: mTEPES.pLoadLevelDuration[r['Period'], r['Scenario'], r['LoadLevel']](), axis=1)
    pConsCols  = [col for col in pSectorProxyPeriodSrc.columns if col.startswith('Consumption_')]
    pMargCols  = [col for col in pSectorProxyPeriodSrc.columns if col.startswith('Marginal_'   )]
    pProdCols  = [col for col in pSectorProxyPeriodSrc.columns if col.startswith('Production_' )]
    if pConsCols:
        pSectorProxyPeriodSrc[pConsCols] = pSectorProxyPeriodSrc[pConsCols].mul(pPeriodDur, axis=0)*1e-3
    if pProdCols:
        pSectorProxyPeriodSrc[pProdCols] = pSectorProxyPeriodSrc[pProdCols].mul(pPeriodDur, axis=0)*1e-3

    pMetricCols = [col for col in pSectorProxyPeriodSrc.columns if col not in ['Iteration', 'Period', 'Scenario', 'LoadLevel']]
    pAggMap = {col: 'sum'  for col in pMetricCols}
    if 'TotalSystemCost_[MEUR]' in pAggMap:
        pAggMap['TotalSystemCost_[MEUR]'] = 'mean'
    for col in pMargCols:
        pAggMap[col] = 'mean'
    pSectorProxyPeriodDF = pSectorProxyPeriodSrc.groupby(['Iteration', 'Period'], as_index=False).agg(pAggMap)
    pPeriodCols = ['Iteration', 'Period'] + [col for col in pSectorProxyPeriodSrc.columns if col not in ['Iteration', 'Period', 'Scenario', 'LoadLevel']]
    pSectorProxyPeriodDF = pSectorProxyPeriodDF[pPeriodCols]
    pPeriodRenameMap = {col: col.replace('_[MW]', '_[GWh]') for col in pSectorProxyPeriodDF.columns if col.endswith('_[MW]')}
    if pPeriodRenameMap:
        pSectorProxyPeriodDF = pSectorProxyPeriodDF.rename(columns=pPeriodRenameMap)
    pSectorProxyPeriodDF.to_csv(pSectorProxyPeriodFile, index=False)
