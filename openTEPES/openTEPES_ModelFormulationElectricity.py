"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 13, 2026

openTEPES.openTEPES_ModelFormulationElectricity — electricity-sector formulation: demand balance, operating reserves and inertia, storage (ESS),
unit commitment and ramping, line switching, DC network operation, and the cycle-based network constraints. Granular per-concern functions so
a caller can pick which to build (e.g. with or without unit commitment).
"""
from __future__ import annotations

import time
import math
import networkx as nx
import pandas   as pd
from collections   import defaultdict
from pyomo.environ import Constraint, Set, RangeSet, Param, Reals, Var, tan, NonNegativeReals, Objective, SolverFactory, sin, sqrt


def GenerationOperationModelFormulationDemand(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Inertia, oper resr, demand constraints ****')

    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout) and lines with losses (linl) (loutl)
    lin   = defaultdict(set)
    linl  = defaultdict(set)
    lout  = defaultdict(set)
    loutl = defaultdict(set)
    for ni,nf,cc in mTEPES.la:
        lin  [nf].add((ni,cc))
        lout [ni].add((nf,cc))
    for ni,nf,cc in mTEPES.ll:
        linl [nf].add((ni,cc))
        loutl[ni].add((nf,cc))

    # nodes to generators (g2n)
    g2n = defaultdict(set)
    e2n = defaultdict(set)
    l2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.eh:
            e2n[nd].add(g)
        if g in mTEPES.el:
            l2n[nd].add(g)

    # area to generators (e2a) (n2a) and generators to area (a2e) (a2n)
    e2a = defaultdict(set)
    a2e = defaultdict(set)
    n2a = defaultdict(set)
    a2n = defaultdict(set)
    for ar,g in mTEPES.a2g:
        if g in mTEPES.eh:
            e2a[ar].add(g); a2e[g].add(ar)
        if g in mTEPES.nr:
            n2a[ar].add(g); a2n[g].add(ar)

    def eSystemInertia(OptModel,n,ar):
        if mTEPES.pSystemInertia[p,sc,n,ar] == 0.0 or len([nr for nr in n2a[ar] if (p,nr) in mTEPES.pnr]) == 0:
            return Constraint.Skip
        return sum(OptModel.vCommitment[p,sc,n,nr] * mTEPES.pInertia[nr] for nr in n2a[ar] if (p,nr) in mTEPES.pnr) >= mTEPES.pSystemInertia[p,sc,n,ar]
    setattr(OptModel, f'eSystemInertia_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eSystemInertia, doc='system inertia [s]'))

    if pIndLogConsole:
        print('eSystemInertia            ... ', len(getattr(OptModel, f'eSystemInertia_{p}_{sc}_{st}')), ' rows')

    # generators and ESS of every area that can provide operating reserves in this period, filtered once instead of per load level
    nr2aRsrv = {ar: [nr for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr] for ar in mTEPES.ar}
    eh2aRsrv = {ar: [eh for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh] for ar in mTEPES.ar}

    def eOperReserveUp(OptModel,n,ar):
        # Skip if there are no upward operating reserves or there are no generators in this area which can provide reserves
        if mTEPES.pOperReserveUp[p,sc,n,ar] == 0.0 or len(nr2aRsrv[ar]) + len(eh2aRsrv[ar]) == 0:
            return Constraint.Skip
        return sum(OptModel.vReserveUp  [p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveUp  [p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveUp[p,sc,n,ar]
    setattr(OptModel, f'eOperReserveUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole:
        print('eOperReserveUp            ... ', len(getattr(OptModel, f'eOperReserveUp_{p}_{sc}_{st}')), ' rows')

    def eOperReserveDw(OptModel,n,ar):
        # Skip if there are no downward operating reserves or there are no generators in this area which can provide reserves
        if mTEPES.pOperReserveDw[p,sc,n,ar] == 0.0 or len(nr2aRsrv[ar]) + len(eh2aRsrv[ar]) == 0:
            return Constraint.Skip
        return sum(OptModel.vReserveDown[p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveDown[p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveDw[p,sc,n,ar]
    setattr(OptModel, f'eOperReserveDw_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole:
        print('eOperReserveDw            ... ', len(getattr(OptModel, f'eOperReserveDw_{p}_{sc}_{st}')), ' rows')

    def eReserveMinRatioDwUp(OptModel,n,nr):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pMinRatioDwUp == 0.0 or mTEPES.pIndOperReserveGen[nr] or (p,nr) not in mTEPES.pnr or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        return OptModel.vReserveDown[p,sc,n,nr] >= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMinRatioDwUp
    setattr(OptModel, f'eReserveMinRatioDwUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eReserveMinRatioDwUp, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole:
        print('eReserveMinRatioDwUp      ... ', len(getattr(OptModel, f'eReserveMinRatioDwUp_{p}_{sc}_{st}')), ' rows')

    def eReserveMaxRatioDwUp(OptModel,n,nr):
        # Skip if there is no maximum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pMaxRatioDwUp >= 1.0 or mTEPES.pIndOperReserveGen[nr] or (p,nr) not in mTEPES.pnr or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        return OptModel.vReserveDown[p,sc,n,nr] <= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMaxRatioDwUp
    setattr(OptModel, f'eReserveMaxRatioDwUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eReserveMaxRatioDwUp, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole:
        print('eReserveMaxRatioDwUp      ... ', len(getattr(OptModel, f'eReserveMaxRatioDwUp_{p}_{sc}_{st}')), ' rows')

    def eRsrvMinRatioDwUpESS(OptModel,n,eh):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pMinRatioDwUp == 0.0 or mTEPES.pIndOperReserveCon[eh] or (p,eh) not in mTEPES.peh or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return OptModel.vESSReserveDown[p,sc,n,eh] >= OptModel.vESSReserveUp[p,sc,n,eh] * mTEPES.pMinRatioDwUp
    setattr(OptModel, f'eRsrvMinRatioDwUpESS_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eRsrvMinRatioDwUpESS, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole:
        print('eRsrvMinRatioDwUpESS      ... ', len(getattr(OptModel, f'eRsrvMinRatioDwUpESS_{p}_{sc}_{st}')), ' rows')

    def eRsrvMaxRatioDwUpESS(OptModel,n,eh):
        # Skip if there is no maximum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pMaxRatioDwUp >= 1.0 or mTEPES.pIndOperReserveCon[eh] or (p,eh) not in mTEPES.peh or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return OptModel.vESSReserveDown[p,sc,n,eh] <= OptModel.vESSReserveUp[p,sc,n,eh] * mTEPES.pMaxRatioDwUp
    setattr(OptModel, f'eRsrvMaxRatioDwUpESS_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eRsrvMaxRatioDwUpESS, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole:
        print('eRsrvMaxRatioDwUpESS      ... ', len(getattr(OptModel, f'eRsrvMaxRatioDwUpESS_{p}_{sc}_{st}')), ' rows')

    def eReserveUpIfEnergy(OptModel,n,es):
        # When ESS units offer operating reserves, they must be able to provide the corresponding energy
        # This means they must have enough stored energy to provide all reserves if they were to have 100% activation
        # Skip if generator is not available in the period or generator cannot provide operating reserves while generating power or no upward reserves are needed in the area where the generator is located or the ESS has no charging capabilities and receives no Inflows
        if (p,es) not in mTEPES.pes or mTEPES.pIndOperReserveGen[es] or mTEPES.pMaxPower2ndBlock [p,sc,n,es] == 0.0 or mTEPES.pMaxStorage[p,sc,n,es]() == 0.0 or sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) == 0.0 or (mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0):
            return Constraint.Skip
        else:
            return (OptModel.vOutput2ndBlock[p,sc,n,es] + OptModel.vReserveUp[p,sc,n,es] + mTEPES.pMinPowerElec[p,sc,n,es]) * mTEPES.pDuration[p,sc,n]() / math.sqrt(mTEPES.pEfficiency[es]) <= OptModel.vESSInventory[p,sc,n,es] - mTEPES.pMinStorage[p,sc,n,es]
    setattr(OptModel, f'eReserveUpIfEnergy_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GWh]'))

    if pIndLogConsole:
        print('eReserveUpIfEnergy        ... ', len(getattr(OptModel, f'eReserveUpIfEnergy_{p}_{sc}_{st}')), ' rows')

    def eESSReserveDwIfEnergy(OptModel,n,es):
        # When ESS units offer operating reserves, they must be able to provide the corresponding energy
        # This means they must have enough stored energy to provide all reserves if they were to have 100% activation
        # Skip if generator is not available in the period or generator cannot provide operating reserves while generating power or no downward reserves are needed in the area where the generator is located
        if (p,es) not in mTEPES.pes or mTEPES.pIndOperReserveCon[es] or mTEPES.pMaxCharge2ndBlock[p,sc,n,es] == 0.0 or mTEPES.pMaxStorage[p,sc,n,es]() == 0.0 or sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) == 0.0 or (mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0):
            return Constraint.Skip
        else:
            return (OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es] + mTEPES.pMinCharge[p,sc,n,es]) * mTEPES.pDuration[p,sc,n]() * math.sqrt(mTEPES.pEfficiency[es]) <= mTEPES.pMaxStorage[p,sc,n,es]() - OptModel.vESSInventory[p,sc,n,es]
    setattr(OptModel, f'eESSReserveDwIfEnergy_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GWh]'))

    if pIndLogConsole:
        print('eESSReserveDwIfEnergy     ... ', len(getattr(OptModel, f'eESSReserveDwIfEnergy_{p}_{sc}_{st}')), ' rows')

    # units that can provide reserve activations in this period; the lists do not depend on the area, so they are plain lists on purpose
    nrRsrvAct = [nr for nr in mTEPES.nr if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr]
    ehRsrvAct = [eh for eh in mTEPES.eh if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh]

    def eOperReserveUpEnergy(OptModel,n):
        # Skip if there are no upward operating reserves activation or there are no generators in this area which can provide reserves
        if mTEPES.pIndReserveActivation() == 0 or sum(mTEPES.pOperReserveUpEnergy[p,sc,n,ar] for ar in mTEPES.ar) == 0.0 or len(nrRsrvAct) + len(ehRsrvAct) == 0:
            return Constraint.Skip
        return sum(OptModel.vReserveUpEnergy  [p,sc,n,nr] for nr in nrRsrvAct if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveUpEnergy  [p,sc,n,eh] for eh in ehRsrvAct if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == sum(mTEPES.pOperReserveUpEnergy[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eOperReserveUpEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eOperReserveUpEnergy, doc='up   operating reserve activation [GW]'))

    if pIndLogConsole:
        print('eOperReserveUpEnergy      ... ', len(getattr(OptModel, f'eOperReserveUpEnergy_{p}_{sc}_{st}')), ' rows')

    def eOperReserveDwEnergy(OptModel,n):
        # Skip if there are no upward operating reserves activation or there are no generators in this area which can provide reserves
        if mTEPES.pIndReserveActivation() == 0 or sum(mTEPES.pOperReserveDwEnergy[p,sc,n,ar] for ar in mTEPES.ar) == 0.0 or len(nrRsrvAct) + len(ehRsrvAct) == 0:
            return Constraint.Skip
        return sum(OptModel.vReserveDownEnergy[p,sc,n,nr] for nr in nrRsrvAct if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveDownEnergy[p,sc,n,eh] for eh in ehRsrvAct if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == sum(mTEPES.pOperReserveDwEnergy[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eOperReserveDwEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eOperReserveDwEnergy, doc='down operating reserve activation [GW]'))

    if pIndLogConsole:
        print('eOperReserveDwEnergy      ... ', len(getattr(OptModel, f'eOperReserveDwEnergy_{p}_{sc}_{st}')), ' rows')

    # def eOperReserveUpEnergy(OptModel,n,ar):
    #     # Skip if there are no upward operating reserves activation or there are no generators in this area which can provide reserves
    #     if mTEPES.pIndReserveActivation() == 0 or mTEPES.pOperReserveUpEnergy[p,sc,n,ar] == 0.0 or len([nr for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr]) + len([eh for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh]) == 0:
    #         return Constraint.Skip
    #     return sum(OptModel.vReserveUpEnergy  [p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveUpEnergy  [p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveUpEnergy[p,sc,n,ar]
    # setattr(OptModel, f'eOperReserveUpEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eOperReserveUpEnergy, doc='up   operating reserve activation [GW]'))
    #
    # if pIndLogConsole:
    #     print('eOperReserveUpEnergy      ... ', len(getattr(OptModel, f'eOperReserveUpEnergy_{p}_{sc}_{st}')), ' rows')
    #
    # def eOperReserveDwEnergy(OptModel,n,ar):
    #     # Skip if there are no upward operating reserves activation or there are no generators in this area which can provide reserves
    #     if mTEPES.pIndReserveActivation() == 0 or mTEPES.pOperReserveDwEnergy[p,sc,n,ar] == 0.0 or len([nr for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr]) + len([eh for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh]) == 0:
    #         return Constraint.Skip
    #     return sum(OptModel.vReserveDownEnergy  [p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveDownEnergy  [p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveDwEnergy[p,sc,n,ar]
    # setattr(OptModel, f'eOperReserveDwEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eOperReserveDwEnergy, doc='down operating reserve activation [GW]'))
    #
    # if pIndLogConsole:
    #     print('eOperReserveDwEnergy      ... ', len(getattr(OptModel, f'eOperReserveDwEnergy_{p}_{sc}_{st}')), ' rows')

    def eReserveUpEnergy(OptModel,n,nr):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pIndReserveActivation() == 0 or mTEPES.pIndOperReserveGen[nr] or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        return OptModel.vReserveUpEnergy[p,sc,n,nr] <= OptModel.vReserveUp[p,sc,n,nr]
    setattr(OptModel, f'eReserveUpEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eReserveUpEnergy, doc='operating reserve activation lower than offered [GW]'))

    if pIndLogConsole:
        print('eReserveUpEnergy          ... ', len(getattr(OptModel, f'eReserveUpEnergy_{p}_{sc}_{st}')), ' rows')

    def eReserveDwEnergy(OptModel,n,nr):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while generating power
        if mTEPES.pIndReserveActivation() == 0 or mTEPES.pIndOperReserveGen[nr] or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        return OptModel.vReserveDownEnergy[p,sc,n,nr] <= OptModel.vReserveDown[p,sc,n,nr]
    setattr(OptModel, f'eReserveDwEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eReserveDwEnergy, doc='operating reserve activation lower than offered [GW]'))

    if pIndLogConsole:
        print('eReserveDwEnergy          ... ', len(getattr(OptModel, f'eReserveDwEnergy_{p}_{sc}_{st}')), ' rows')

    def eESSReserveUpEnergy(OptModel,n,eh):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while consuming power
        if mTEPES.pIndReserveActivation() == 0 or mTEPES.pIndOperReserveCon[eh] or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return OptModel.vESSReserveUpEnergy[p,sc,n,eh] <= OptModel.vESSReserveUp[p,sc,n,eh]
    setattr(OptModel, f'eESSReserveUpEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eESSReserveUpEnergy, doc='operating reserve activation lower than offered [GW]'))

    if pIndLogConsole:
        print('eESSReserveUpEnergy       ... ', len(getattr(OptModel, f'eESSReserveUpEnergy_{p}_{sc}_{st}')), ' rows')

    def eESSReserveDwEnergy(OptModel,n,eh):
        # Skip if there is no minimum up/down reserve ratio or no reserves are needed in the Area where the generator is located or generator cannot provide reserves while consuming power
        if mTEPES.pIndReserveActivation() == 0 or mTEPES.pIndOperReserveCon[eh] or sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return OptModel.vESSReserveDownEnergy[p,sc,n,eh] <= OptModel.vESSReserveDown[p,sc,n,eh]
    setattr(OptModel, f'eESSReserveDwEnergy_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eESSReserveDwEnergy, doc='operating reserve activation lower than offered [GW]'))

    if pIndLogConsole:
        print('eESSReserveDwEnergy       ... ', len(getattr(OptModel, f'eESSReserveDwEnergy_{p}_{sc}_{st}')), ' rows')

    pACNetwork = mTEPES.pIndACPowerFlow()          # hoisted: a rule fires once per index, the flag cannot change during the build

    def eBalanceElec(OptModel,n,nd):
        # Under the AC model the balance is rebuilt by openTEPES_ModelFormulationElectricity under this same name, because ten places read its dual back by
        # string. Building the DC version first would be overwritten, so skip it here rather than pay for it.
        if pACNetwork:
            return Constraint.Skip
        if len([g for g in g2n[nd] if (p,g) in mTEPES.pg]) + len(lout[nd]) + len(lin[nd]) == 0:
            return Constraint.Skip
        return (sum(OptModel.vTotalOutput[p,sc,n,g] for g in g2n[nd] if (p,g) in mTEPES.pg) - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh) + OptModel.vENS[p,sc,n,nd] -
                sum(OptModel.vLineLosses[p,sc,n,nd,nf,cc] for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pll) - sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pla) -
                sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc] for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pll) + sum(OptModel.vFlowElec[p,sc,n,ni,nd,cc] for ni,cc in lin [nd] if (p,ni,nd,cc) in mTEPES.pla)) == mTEPES.pDemandElec[p,sc,n,nd]
    # Under AC the component is created by openTEPES_ModelFormulationElectricity under this same name. Creating an empty one here first would make Pyomo
    # warn about an implicit replacement, so don't create it at all.
    if not pACNetwork:
        setattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceElec, doc='electric load generation balance [GW]'))

    if pIndLogConsole and not pACNetwork:
        print('eBalanceElec              ... ', len(getattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating inertia/reserves/balance    ... ', round(GeneratingTime), 's')


# @profile
def GenerationOperationModelFormulationStorage(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Storage   scheduling       constraints ****')

    StartTime = time.time()

    n2list = list(mTEPES.n2)

    # generators to area (a2e)
    a2e = defaultdict(set)
    for ar,g in mTEPES.a2g:
        if g in mTEPES.eh:
            a2e[g].add(ar)

    def eMaxInventory2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] == 0 or (p,ec) not in mTEPES.pec or mTEPES.pMaxStorage[p,sc,n,ec]() == 0.0:
            return Constraint.Skip
        return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMaxStorage[p,sc,n,ec]() <= OptModel.vCommitment[p,sc,n,ec]
    setattr(OptModel, f'eMaxInventory2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eMaxInventory2Comm, doc='ESS maximum inventory limited by commitment [p.u.]'))

    if pIndLogConsole:
        print('eMaxInventory2Comm        ... ', len(getattr(OptModel, f'eMaxInventory2Comm_{p}_{sc}_{st}')), ' rows')

    def eMinInventory2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] == 0 or (p,ec) not in mTEPES.pec or mTEPES.pMinStorage[p,sc,n,ec] == 0.0:
            return Constraint.Skip
        return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMinStorage[p,sc,n,ec] >= OptModel.vCommitment[p,sc,n,ec]
    setattr(OptModel, f'eMinInventory2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eMinInventory2Comm, doc='ESS minimum inventory limited by commitment [p.u.]'))

    if pIndLogConsole:
        print('eMinInventory2Comm        ... ', len(getattr(OptModel, f'eMinInventory2Comm_{p}_{sc}_{st}')), ' rows')

    def eInflows2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] == 0 or (p,ec) not in mTEPES.pec or mTEPES.pEnergyInflows[p,sc,n,ec]() == 0.0:
            return Constraint.Skip
        return OptModel.vEnergyInflows[p,sc,n,ec] / mTEPES.pEnergyInflows[p,sc,n,ec]() <= OptModel.vCommitment[p,sc,n,ec]
    setattr(OptModel, f'eInflows2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eInflows2Comm, doc='ESS inflows limited by commitment [p.u.]'))

    if pIndLogConsole:
        print('eInflows2Comm             ... ', len(getattr(OptModel, f'eInflows2Comm_{p}_{sc}_{st}')), ' rows')

    def eESSInventory(OptModel,n,es):
        if (p,es) not in mTEPES.pes or (p,sc,st,n) not in mTEPES.s2n or (mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0):
            return Constraint.Skip
        if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
            if es not in mTEPES.ec:
                return mTEPES.pIniInventory[p,sc,n,es]()                                            + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            else:
                return OptModel.vIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
        elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
            if es not in mTEPES.ec:
                return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            else:
                return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) * OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eESSInventory_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole:
        print('eESSInventory             ... ', len(getattr(OptModel, f'eESSInventory_{p}_{sc}_{st}')), ' rows')

    def eIniFinInventory(OptModel,n,ec):
        if (p,ec) not in mTEPES.pec or mTEPES.n.ord(n) != mTEPES.pStorageTimeStep[ec]:
            return Constraint.Skip
        return OptModel.vIniInventory[p,sc,n,ec] == OptModel.vESSInventory[p,sc,mTEPES.n.last(),ec]
    setattr(OptModel, f'eIniFinInventory_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eIniFinInventory, doc='Initial equal to final inventory for ESS candidates [p.u.]'))

    if pIndLogConsole:
        print('eIniFinInventory          ... ', len(getattr(OptModel, f'eIniFinInventory_{p}_{sc}_{st}')), ' rows')

    def eIniInventory(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] == 0 or (p,ec) not in mTEPES.pec or (p,sc,st,n) not in mTEPES.s2n or mTEPES.n.ord(n) != mTEPES.pStorageTimeStep[ec] or mTEPES.pIniInventory[p,sc,n,ec]() == 0.0:
            return Constraint.Skip
        return OptModel.vIniInventory[p,sc,n,ec] / mTEPES.pIniInventory[p,sc,n,ec]() <= OptModel.vCommitment[p,sc,n,ec]
    setattr(OptModel, f'eIniInventory_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eIniInventory, doc='Initial inventory for ESS candidates [p.u.]'))

    if pIndLogConsole:
        print('eIniInventory             ... ', len(getattr(OptModel, f'eIniInventory_{p}_{sc}_{st}')), ' rows')

    def eMaxShiftTime(OptModel,n,eh):
        if mTEPES.pShiftTime[eh] == 0 or (p,eh) not in mTEPES.peh:
            return Constraint.Skip
        return mTEPES.pDuration[p,sc,n]()*mTEPES.pEfficiency[eh]*OptModel.vESSTotalCharge[p,sc,n,eh] <= sum(mTEPES.pDuration[p,sc,n2]()*OptModel.vTotalOutput[p,sc,n2,eh] for n2 in n2list[mTEPES.n.ord(n):mTEPES.n.ord(n)+mTEPES.pShiftTime[eh]])
    setattr(OptModel, f'eMaxShiftTime_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eMaxShiftTime, doc='Maximum shift time [GWh]'))

    if pIndLogConsole:
        print('eMaxShiftTime             ... ', len(getattr(OptModel, f'eMaxShiftTime_{p}_{sc}_{st}')), ' rows')

    def eMaxCharge(OptModel,n,eh):
        # Check if generator is available in the period and has variable charging capacity
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        # Hydro units have commitment while ESS units are implicitly always committed
        if eh not in mTEPES.h:
            # ESS units only need this constraint when they can offer operating reserves and the system demands reserves
            if mTEPES.pIndOperReserveCon[eh] or sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]) == 0.0:
                return Constraint.Skip
            # ESS case equation
            return (OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0
        # Hydro case equation
        else:
            return (OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= OptModel.vCommitmentCons[p,sc,n,eh]
    setattr(OptModel, f'eMaxCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole:
        print('eMaxCharge                ... ', len(getattr(OptModel, f'eMaxCharge_{p}_{sc}_{st}')), ' rows')

    def eMinCharge(OptModel, n, eh):
        # Skip if ESS is not available in the period or ESS cannot provide reserves while consuming power or no reserves are demanded in the area where the ESS is located or the ESS cannot consume at variable power
        if mTEPES.pIndOperReserveCon[eh] or (p,eh) not in mTEPES.peh or sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[eh]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return OptModel.vCharge2ndBlock[p,sc,n,eh] - OptModel.vESSReserveUp[p,sc,n,eh] >= 0.0
    setattr(OptModel, f'eMinCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole:
        print('eMinCharge                ... ', len(getattr(OptModel, f'eMinCharge_{p}_{sc}_{st}')), ' rows')

    # def eChargeDischarge(OptModel,n,eh):
    #     if mTEPES.pMaxCharge[p,sc,n,eh]:
    #         return OptModel.vTotalOutput[p,sc,n,eh] / mTEPES.pMaxPowerElec[p,sc,n,eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] / mTEPES.pMaxCharge[p,sc,n,eh] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.n*mTEPES.eh, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    # Generators with consumption capability cannot be consuming and generating simultaneously
    def eChargeDischarge(OptModel,n,eh):
        # Check if generator is available in the period
        # Constraint only relevant to generators which can consume and generate power
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxPower2ndBlock [p,sc,n,eh] == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        # Hydro generators can have binary commitment, energy modeled ESS do not have commitment
        # ESS Generator
        if eh not in mTEPES.h and mTEPES.pIndReserveActivation() == 0:
            return ((OptModel.vOutput2ndBlock[p,sc,n,eh] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [p,sc,n,eh]) / mTEPES.pMaxPower2ndBlock [p,sc,n,eh] +
                    (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0)
        if eh not in mTEPES.h and mTEPES.pIndReserveActivation() == 1:
            return ((OptModel.vOutput2ndBlock[p,sc,n,eh] +                         OptModel.vReserveUpEnergy     [p,sc,n,eh]) / mTEPES.pMaxPower2ndBlock [p,sc,n,eh] +
                    (OptModel.vCharge2ndBlock[p,sc,n,eh] +                         OptModel.vESSReserveDownEnergy[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0)
        # Hydro Generator
        else:
            return OptModel.vCommitment[p,sc,n,eh] + OptModel.vCommitmentCons[p,sc,n,eh] <= 1.0
    setattr(OptModel, f'eChargeDischarge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole:
        print('eChargeDischarge          ... ', len(getattr(OptModel, f'eChargeDischarge_{p}_{sc}_{st}')), ' rows')

    def eESSTotalCharge(OptModel,n,eh):
        # Check if the generator is available in the period
        # Constraint only applies to generators with charging capabilities
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        # Hydro generators can have binary commitment, energy modeled ESS do not have commitment
        # ESS Generator
        if eh not in mTEPES.h:
            # Check the minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pIndReserveActivation() == 0:
                if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                    return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==        OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]
                else:
                    return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == 1.0 + (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
            if mTEPES.pIndReserveActivation() == 1:
                if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                    return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==        OptModel.vCharge2ndBlock[p,sc,n,eh] +                         OptModel.vESSReserveDownEnergy[p,sc,n,eh] -                         OptModel.vESSReserveUpEnergy[p,sc,n,eh]
                else:
                    return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == 1.0 + (OptModel.vCharge2ndBlock[p,sc,n,eh] +                         OptModel.vESSReserveDownEnergy[p,sc,n,eh] -                         OptModel.vESSReserveUpEnergy[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
        # Hydro generator
        else:
            # Check the minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pIndReserveActivation() == 0:
                if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                    return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==                                        OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]
                else:
                    return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == OptModel.vCommitmentCons[p,sc,n,eh] + (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
            if mTEPES.pIndReserveActivation() == 1:
                if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                    return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==                                        OptModel.vCharge2ndBlock[p,sc,n,eh] +                         OptModel.vESSReserveDownEnergy[p,sc,n,eh] -                         OptModel.vESSReserveUpEnergy[p,sc,n,eh]
                else:
                    return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == OptModel.vCommitmentCons[p,sc,n,eh] + (OptModel.vCharge2ndBlock[p,sc,n,eh] +                         OptModel.vESSReserveDownEnergy[p,sc,n,eh] -                         OptModel.vESSReserveUpEnergy[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
    setattr(OptModel, f'eESSTotalCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole:
        print('eESSTotalCharge           ... ', len(getattr(OptModel, f'eESSTotalCharge_{p}_{sc}_{st}')), ' rows')

    def eChargeOutflows(OptModel,n,eh):
        if mTEPES.pIndOutflowIncomp[eh] == 0 or (p,eh) not in mTEPES.peh or (p,sc,eh) not in mTEPES.eo or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0.0:
            return Constraint.Skip
        return (OptModel.vEnergyOutflows[p,sc,n,eh] + OptModel.vCharge2ndBlock[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0
    setattr(OptModel, f'eChargeOutflows_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eChargeOutflows, doc='incompatibility between charge and outflows use [p.u.]'))

    if pIndLogConsole:
        print('eChargeOutflows           ... ', len(getattr(OptModel, f'eChargeOutflows_{p}_{sc}_{st}')), ' rows')

    def eEnergyOutflows(OptModel,n,es):
        if (p,sc,es) not in mTEPES.eo:
            return Constraint.Skip
        return sum((OptModel.vEnergyOutflows[p,sc,n2,es] - mTEPES.pEnergyOutflows[p,sc,n2,es]())*mTEPES.pDuration[p,sc,n2]() for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)]) == 0.0
    setattr(OptModel, f'eEnergyOutflows_{p}_{sc}_{st}', Constraint(mTEPES.neso, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole:
        print('eEnergyOutflows           ... ', len(getattr(OptModel, f'eEnergyOutflows_{p}_{sc}_{st}')), ' rows')

    def eMinimumEnergy(OptModel,n,g):
        if (p,g) not in mTEPES.pg or (p,sc,g) not in mTEPES.gm or sum((mTEPES.pMinPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) > 0.0:
            return Constraint.Skip
        return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) >= 0.0
    setattr(OptModel, f'eMinimumEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ngen, rule=eMinimumEnergy, doc='minimum energy of a unit [GWh]'))

    if pIndLogConsole:
        print('eMinimumEnergy            ... ', len(getattr(OptModel, f'eMinimumEnergy_{p}_{sc}_{st}')), ' rows')

    def eMaximumEnergy(OptModel,n,g):
        if (p,g) not in mTEPES.pg or (p,sc,g) not in mTEPES.gM or sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMaxEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
            return Constraint.Skip
        return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMaxEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) <= 0.0
    setattr(OptModel, f'eMaximumEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ngen, rule=eMaximumEnergy, doc='maximum energy of a unit [GWh]'))

    if pIndLogConsole:
        print('eMaximumEnergy            ... ', len(getattr(OptModel, f'eMaximumEnergy_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating storage operation           ... ', round(GeneratingTime), 's')

# @profile


def GenerationOperationModelFormulationCommitment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Unit commitment            constraints ****')

    StartTime = time.time()

    # generators to area (a2n)
    a2n = defaultdict(set)
    for ar,g in mTEPES.a2g:
        if g in mTEPES.nr:
            a2n[g].add(ar)

    def eMaxOutput2ndBlock(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        if (nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr])):
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2n[nr]) >  0.0:
                if   mTEPES.pIndRampReserves() == 0 or  sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
                    if   mTEPES.pIndOperReserveGen[nr] == 0 and n != mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]                                       ) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,mTEPES.n.next(n),nr]
                    elif mTEPES.pIndOperReserveGen[nr] == 0 and n == mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]                                       ) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                    else:
                        return Constraint.Skip
                elif mTEPES.pIndRampReserves() == 1 and sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) >  0.0:
                    if   mTEPES.pIndOperReserveGen[nr] == 0 and n != mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr] + OptModel.vRampReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,mTEPES.n.next(n),nr]
                    elif mTEPES.pIndOperReserveGen[nr] == 0 and n == mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr] + OptModel.vRampReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2n[nr]) == 0.0:
                if   mTEPES.pIndRampReserves() == 0 or  sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
                    if   n != mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr]                                                                          ) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,mTEPES.n.next(n),nr]
                    elif n == mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr]                                                                          ) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                    else:
                        return Constraint.Skip
                elif mTEPES.pIndRampReserves() == 1 and sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) >  0.0:
                    if   n != mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr]                                    + OptModel.vRampReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,mTEPES.n.next(n),nr]
                    elif n == mTEPES.n.last():
                        return (OptModel.vOutput2ndBlock[p,sc,n,nr]                                    + OptModel.vRampReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxOutput2ndBlock_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole:
        print('eMaxOutput2ndBlock        ... ', len(getattr(OptModel, f'eMaxOutput2ndBlock_{p}_{sc}_{st}')), ' rows')

    def eMinOutput2ndBlock(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        if (nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr])):
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) > 0.0:
                if   mTEPES.pIndOperReserveGen[nr] == 0 and (mTEPES.pIndRampReserves() == 0 or  sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) == 0.0):
                    return  OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]                                      >= 0.0
                elif mTEPES.pIndOperReserveGen[nr] == 0 and  mTEPES.pIndRampReserves() == 1 and sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) >  0.0:
                    return  OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr] - OptModel.vRampReserveDw[p,sc,n,nr] >= 0.0
                else:
                    return Constraint.Skip
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0.0:
                if mTEPES.pIndRampReserves() == 1 and sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) >  0.0:
                    return  OptModel.vOutput2ndBlock[p,sc,n,nr]                                    - OptModel.vRampReserveDw[p,sc,n,nr] >= 0.0
                else:
                    return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinOutput2ndBlock_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole:
        print('eMinOutput2ndBlock        ... ', len(getattr(OptModel, f'eMinOutput2ndBlock_{p}_{sc}_{st}')), ' rows')

    def eTotalOutput(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        if (mTEPES.pMustRun[nr] == 0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] or nr in mTEPES.gc) and (nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr])):
            if mTEPES.pMaxPowerElec[p,sc,n,nr]:
                if   mTEPES.pIndReserveActivation() == 0:
                    if mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0:
                        return OptModel.vTotalOutput[p,sc,n,nr]                                   ==                                    OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]
                    else:
                        return OptModel.vTotalOutput[p,sc,n,nr] / mTEPES.pMinPowerElec[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr] + (OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pMinPowerElec[p,sc,n,nr]
                else:
                    if mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0:
                        return OptModel.vTotalOutput[p,sc,n,nr]                                   ==                                    OptModel.vOutput2ndBlock[p,sc,n,nr] +                         OptModel.vReserveUpEnergy[p,sc,n,nr] -                         OptModel.vReserveDownEnergy[p,sc,n,nr]
                    else:
                        return OptModel.vTotalOutput[p,sc,n,nr] / mTEPES.pMinPowerElec[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr] + (OptModel.vOutput2ndBlock[p,sc,n,nr] +                         OptModel.vReserveUpEnergy[p,sc,n,nr] -                         OptModel.vReserveDownEnergy[p,sc,n,nr]) / mTEPES.pMinPowerElec[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalOutput_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole:
        print('eTotalOutput              ... ', len(getattr(OptModel, f'eTotalOutput_{p}_{sc}_{st}')), ' rows')

    def eUCStrShut(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or nr in mTEPES.eh or mTEPES.pMustRun[nr] or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or mTEPES.pVariableMinPowerElec[p,sc,n,nr] > 0.0:
            return Constraint.Skip
        if n == mTEPES.n.first():
            return OptModel.vCommitment[p,sc,n,nr] - mTEPES.pInitialUC[p,sc,n,nr]()                 == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
        else:
            return OptModel.vCommitment[p,sc,n,nr] - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
    setattr(OptModel, f'eUCStrShut_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown [p.u.]'))

    if pIndLogConsole:
        print('eUCStrShut                ... ', len(getattr(OptModel, f'eUCStrShut_{p}_{sc}_{st}')), ' rows')

    def eStableStates(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        return OptModel.vStableState[p,sc,n,nr] + OptModel.vRampUpState[p,sc,n,nr] + OptModel.vRampDwState[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr]
    setattr(OptModel, f'eStableStates_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eStableStates, doc='relation among stable, ramp up and ramp down states [p.u.]'))

    if pIndLogConsole:
        print('eStableStates             ... ', len(getattr(OptModel, f'eStableStates_{p}_{sc}_{st}')), ' rows')

    pnrGensAll    = {gen for period,gen in mTEPES.pnr}
    pnrGensP      = {gen for period,gen in mTEPES.pnr if period == p}
    pYearlyActive = {group: len(mTEPES.GeneratorsInYearlyGroup[group] & pnrGensAll) > 1 for group in mTEPES.ExclusiveGroupsYearly}
    pHourlyActive = {group: len(mTEPES.GeneratorsInHourlyGroup[group] & pnrGensP  ) > 1 for group in mTEPES.ExclusiveGroupsHourly}

    def eMaxCommitmentYearly(OptModel,n,group,nr):
        # Skip if generator not available on period
        # Skip if the generator is not part of the exclusive group
        # Skip if there are one or fewer generators in the group
        if (p,nr) not in mTEPES.pnr or nr not in mTEPES.GeneratorsInYearlyGroup[group] or not pYearlyActive[group]:
            return Constraint.Skip
        return OptModel.vCommitment[p,sc,n,nr]                                  <= OptModel.vMaxCommitmentYearly[p,sc,nr,group]

    setattr(OptModel, f'eMaxCommitmentYearly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsYearly*mTEPES.nr, rule=eMaxCommitmentYearly, doc='maximum of all the commitments [p.u.]'))

    if pIndLogConsole:
        print('eMaxCommitmentYearly      ... ', len(getattr(OptModel, f'eMaxCommitmentYearly_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitmentConsYearly(OptModel,n,group,nr):
        # Skip if generator not available on period
        # Skip if the generator is not part of the exclusive group
        # Skip if the generator has no consumption commitment (only hydro units do)
        # Skip if there are one or fewer generators in the group
        if (p,nr) not in mTEPES.pnr or nr not in mTEPES.GeneratorsInYearlyGroup[group] or nr not in mTEPES.h or not pYearlyActive[group]:
            return Constraint.Skip
        return OptModel.vCommitmentCons[p,sc,n,nr]                           <= OptModel.vMaxCommitmentConsYearly[p,sc,nr,group]

    setattr(OptModel, f'eMaxCommitmentConsYearly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsYearly*mTEPES.nr, rule=eMaxCommitmentConsYearly, doc='maximum of all the consumption commitments [p.u.]'))

    if pIndLogConsole:
        print('eMaxCommitmentConsYearly  ... ', len(getattr(OptModel, f'eMaxCommitmentConsYearly_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitGenYearly(OptModel,n,group,nr):
        # Skip if generator not available on period
        # Skip if the generator is not part of the exclusive group
        # Avoid division by 0. If Maximum power is 0 this equation is not needed anyway
        # Skip if there are one or fewer generators in the group
        if (p,nr) not in mTEPES.pnr or nr not in mTEPES.GeneratorsInYearlyGroup[group] or mTEPES.pMaxPowerElec[p,sc,n,nr] == 0.0 or not pYearlyActive[group]:
            return Constraint.Skip
        return OptModel.vTotalOutput[p,sc,n,nr]/mTEPES.pMaxPowerElec[p,sc,n,nr] <= OptModel.vMaxCommitmentYearly[p,sc,nr,group]
    setattr(OptModel, f'eMaxCommitGenYearly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsYearly*mTEPES.nr, rule=eMaxCommitGenYearly, doc='maximum of all the capacity factors'))

    if pIndLogConsole:
        print('eMaxCommitGenYearly       ... ', len(getattr(OptModel, f'eMaxCommitGenYearly_{p}_{sc}_{st}')), ' rows')

    def eExclusiveGensYearly(OptModel,group):
        # Skip if there are one or fewer generators in the group
        if not pYearlyActive[group]:
            return Constraint.Skip
        return sum(OptModel.vMaxCommitmentYearly[p,sc,nr,group] + (OptModel.vMaxCommitmentConsYearly[p,sc,nr,group] if nr in mTEPES.h else 0) for nr in mTEPES.GeneratorsInYearlyGroup[group] if (p,nr) in mTEPES.pnr) <= 1
    setattr(OptModel, f'eExclusiveGensYearly_{p}_{sc}_{st}', Constraint(mTEPES.ExclusiveGroupsYearly, rule=eExclusiveGensYearly, doc='mutually exclusive generators'))

    if pIndLogConsole:
        print('eExclusiveGensYearly      ... ', len(getattr(OptModel, f'eExclusiveGensYearly_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')

    def eMaxCommitmentHourly(OptModel,n,group,nr):
        # Skip if generator not available on period
        # Skip if the generator is not part of the exclusive group
        # Skip if there are one or fewer generators in the group
        if (p,nr) not in mTEPES.pnr or nr not in mTEPES.GeneratorsInHourlyGroup[group] or not pHourlyActive[group]:
            return Constraint.Skip
        return OptModel.vCommitment[p,sc,n,nr]                               <= OptModel.vMaxCommitmentHourly[p,sc,n,nr,group]
    setattr(OptModel, f'eMaxCommitmentHourly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsHourly*mTEPES.nr, rule=eMaxCommitmentHourly, doc='maximum of all the commitments [p.u.]'))

    if pIndLogConsole:
        print('eMaxCommitmentHourly      ... ', len(getattr(OptModel, f'eMaxCommitmentHourly_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitGenHourly(OptModel,n,group,nr):
        # Skip if generator not available on period or the generator is not part of the exclusive group
        # Avoid division by 0. If Maximum power is 0 this equation is not needed anyway
        # Skip if there are one or fewer generators in the group
        if (p,nr) not in mTEPES.pnr or nr not in mTEPES.GeneratorsInHourlyGroup[group] or mTEPES.pMaxPowerElec[p,sc,n,nr] == 0.0 or not pHourlyActive[group]:
            return Constraint.Skip
        return OptModel.vTotalOutput[p,sc,n,nr]/mTEPES.pMaxPowerElec[p,sc,n,nr] <= OptModel.vMaxCommitmentHourly[p,sc,n,nr,group]
    setattr(OptModel, f'eMaxCommitGenHourly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsHourly*mTEPES.nr, rule=eMaxCommitGenHourly, doc='maximum of all the capacity factors'))

    if pIndLogConsole:
        print('eMaxCommitGenHourly       ... ', len(getattr(OptModel, f'eMaxCommitGenHourly_{p}_{sc}_{st}')), ' rows')

    def eExclusiveGensHourly(OptModel,n,group):
        # Skip if there are one or fewer generators in the group
        # This is written in a different way from the rest of the code to avoid variable shadowing due to comprehension
        pnrGens = {gen for period, gen in mTEPES.pnr if period == p}
        if not pHourlyActive[group]:
            return Constraint.Skip
        return sum(OptModel.vMaxCommitmentHourly[p,sc,n,nr,group] + (OptModel.vCommitmentCons[p,sc,n,nr] if nr in mTEPES.h else 0) for nr in mTEPES.GeneratorsInHourlyGroup[group] if (p,nr) in mTEPES.pnr) <= 1
    setattr(OptModel, f'eExclusiveGensHourly_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ExclusiveGroupsHourly, rule=eExclusiveGensHourly, doc='mutually exclusive generators'))

    if pIndLogConsole:
        print('eExclusiveGensHourly      ... ', len(getattr(OptModel, f'eExclusiveGensHourly_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')


# @profile
def GenerationOperationModelFormulationRampMinTime(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Ramp and min up/down time  constraints ****')

    StartTime = time.time()

    n2list = list(mTEPES.n2)

    def eSystemRampUp(OptModel,n):
        if mTEPES.pIndRampReserves() == 0 or sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
            return Constraint.Skip
        return sum(OptModel.vRampReserveUp[p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr]))) / mTEPES.pDuration[p,sc,n]() >= sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eSystemRampUp_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eSystemRampUp, doc='minimum system ramp up   [p.u.]'))

    if pIndLogConsole:
        print('eSystemRampUp             ... ', len(getattr(OptModel, f'eSystemRampUp_{p}_{sc}_{st}')), ' rows')

    def eSystemRampDw(OptModel,n):
        if mTEPES.pIndRampReserves() == 0 or sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
            return Constraint.Skip
        return sum(OptModel.vRampReserveDw[p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr]))) / mTEPES.pDuration[p,sc,n]() >= sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eSystemRampDw_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eSystemRampDw, doc='minimum system ramp down [p.u.]'))

    if pIndLogConsole:
        print('eSystemRampDw             ... ', len(getattr(OptModel, f'eSystemRampDw_{p}_{sc}_{st}')), ' rows')

    def eRampUp(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        if nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr]):
            if mTEPES.pIndBinGenRamps() and mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr],0.0)                        + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveDown[p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole:
        print('eRampUp                   ... ', len(getattr(OptModel, f'eRampUp_{p}_{sc}_{st}')), ' rows')

    def eRampDw(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        if nr not in mTEPES.es or (nr in mTEPES.es and mTEPES.pTotalMaxCharge[nr]+mTEPES.pTotalEnergyInflows[nr]):
            if mTEPES.pIndBinGenRamps() and mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr],0.0)                        + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[p,sc,n,nr]()                 + OptModel.vShutDown[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveUp  [p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] + OptModel.vShutDown[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampDw_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole:
        print('eRampDw                   ... ', len(getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')), ' rows')

    def eRampUpCharge(OptModel,n,eh):
        if (p,eh) in mTEPES.peh:
            if mTEPES.pIndBinGenRamps() and mTEPES.pRampUp[eh] and mTEPES.pRampUp[eh]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]:
                if n == mTEPES.n.first():
                    return (                                                                                                            OptModel.vCharge2ndBlock[p,sc,n,eh] - OptModel.vESSReserveUp  [p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[eh] >= - 1.0
                else:
                    return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),eh] + OptModel.vESSReserveDown[p,sc,mTEPES.n.prev(n),eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] - OptModel.vESSReserveUp  [p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[eh] >= - 1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampUpCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole:
        print('eRampUpCharge             ... ', len(getattr(OptModel, f'eRampUpCharge_{p}_{sc}_{st}')), ' rows')

    def eRampDwCharge(OptModel,n,eh):
        if (p,eh) in mTEPES.peh:
            if mTEPES.pIndBinGenRamps() and mTEPES.pRampDw[eh] and mTEPES.pRampDw[eh]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]:
                if n == mTEPES.n.first():
                    return (                                                                                                          + OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[eh] <=   1.0
                else:
                    return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),eh] - OptModel.vESSReserveUp  [p,sc,mTEPES.n.prev(n),eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[eh] <=   1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampDwCharge_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.eh, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole:
        print('eRampDwCharge             ... ', len(getattr(OptModel, f'eRampDwCharge_{p}_{sc}_{st}')), ' rows')

    pIndSimplexFormulation = True  # Parameter to choose if minimum stable time should be physically accurate or computationally efficient. True for efficiency, False for accuracy
    pIndStableTimeDeadBand = True  # Parameter to choose if ramps below a certain threshold set by pEpsilon should not be restricted. True for having dead band, False for restricting all ramps

    if pIndStableTimeDeadBand:
        pEpsilon = 1e-2
    else:
        pEpsilon = 1e-4

    def eRampUpState(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        if pIndStableTimeDeadBand:
            if mTEPES.pRampUp[nr]:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
            else:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
        else:
            if mTEPES.pRampUp[nr]:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
            else:
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
    setattr(OptModel, f'eRampUpState_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eRampUpState, doc='ramp up state  [p.u.]'))

    if pIndLogConsole:
        print('eRampUpState              ... ', len(getattr(OptModel, f'eRampUpState_{p}_{sc}_{st}')), ' rows')

    def eRampDwState(OptModel,n,nr):
        if (p,nr) not in mTEPES.pnr or mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
            return Constraint.Skip
        if pIndStableTimeDeadBand:
            if mTEPES.pRampDw[nr]:
                if n == mTEPES.n.first():
                    return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
            else:
                if n == mTEPES.n.first():
                    return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
        else:
            if mTEPES.pRampDw[nr]:
                if n == mTEPES.n.first():
                    return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
                else:
                    return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
            else:
                if n == mTEPES.n.first():
                    return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
                else:
                    return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
    setattr(OptModel, f'eRampDwState_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eRampDwState, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole:
        print('eRampDwState              ... ', len(getattr(OptModel, f'eRampDwState_{p}_{sc}_{st}')), ' rows')

    def eMinUpTime(OptModel,n,t):
        if (p,t) not in mTEPES.pg or t in mTEPES.eh or mTEPES.pMustRun[t] or mTEPES.pIndBinGenMinTime() == 0 or (mTEPES.pMinPowerElec[p,sc,n,t] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,t] == 0.0) or mTEPES.pUpTime[t] <= 1 or mTEPES.n.ord(n) <= mTEPES.pUpTime[t]:
            return Constraint.Skip
        return sum(OptModel.vStartUp [p,sc,n2,t] for n2 in n2list[mTEPES.n.ord(n)+1-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[p,sc,n,t]
    setattr(OptModel, f'eMinUpTime_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.tr, rule=eMinUpTime  , doc='minimum up   time [p.u.]'))

    if pIndLogConsole:
        print('eMinUpTime                ... ', len(getattr(OptModel, f'eMinUpTime_{p}_{sc}_{st}')), ' rows')

    def eMinDownTime(OptModel,n,t):
        if (p,t) not in mTEPES.pg or t in mTEPES.eh or mTEPES.pMustRun[t] or mTEPES.pIndBinGenMinTime() == 0 or (mTEPES.pMinPowerElec[p,sc,n,t] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,t] == 0.0) or mTEPES.pDwTime[t] <= 1 or mTEPES.n.ord(n) <= mTEPES.pDwTime[t]:
            return Constraint.Skip
        return sum(OptModel.vShutDown[p,sc,n2,t] for n2 in n2list[mTEPES.n.ord(n)+1-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[p,sc,n,t]
    setattr(OptModel, f'eMinDownTime_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.tr, rule=eMinDownTime, doc='minimum down time [p.u.]'))

    if pIndLogConsole:
        print('eMinDownTime              ... ', len(getattr(OptModel, f'eMinDownTime_{p}_{sc}_{st}')), ' rows')

    if pIndSimplexFormulation:
        def eMinStableTime(OptModel,n,nr):
            if (mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.n.ord(n) >= mTEPES.pStableTime[nr] + 2):
                return OptModel.vRampUpState[p,sc,n,nr] + sum(OptModel.vRampDwState[p,sc,n2,nr] for n2 in n2list[mTEPES.n.ord(n)-1-mTEPES.pStableTime[nr]:mTEPES.n.ord(n)-1]) <= 1
            else:
                return Constraint.Skip
        setattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nr, rule=eMinStableTime, doc='minimum stable time [p.u.]'))
    else:
        MinStableTimeLoadLevels = []
        if sum(mTEPES.pStableTime[nr] for nr in mTEPES.nr):
            for n,nr in mTEPES.n*mTEPES.nr:
                if (mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.n.ord(n) >= mTEPES.pStableTime[nr] + 2):
                    for n2 in n2list[mTEPES.n.ord(n)-mTEPES.pStableTime[nr]-1:mTEPES.n.ord(n)-1]:
                        MinStableTimeLoadLevels.append((n,n2,nr))

        def eMinStableTime(OptModel,n,n2,nr):
            return OptModel.vRampUpState[p,sc,n,nr] + OptModel.vRampDwState[p,sc,n2,nr] <= 1
        setattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}', Constraint(MinStableTimeLoadLevels, rule=eMinStableTime, doc='minimum stable time [p.u.]'))

    if pIndLogConsole:
        print('eMinStableTime            ... ', len(getattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating ramps & minimum time        ... ', round(GeneratingTime), 's')


# @profile
def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    switching model constraints ****')

    StartTime = time.time()

    n2list = list(mTEPES.n2)

    def eLineStateCand(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or (p,ni,nf,cc) not in mTEPES.plc:
            return Constraint.Skip
        if mTEPES.pIndBinLineSwitch[ni,nf,cc]:
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] <= OptModel.vNetworkInvest[p,ni,nf,cc]
        else:
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] == OptModel.vNetworkInvest[p,ni,nf,cc]
    setattr(OptModel, f'eLineStateCand_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole:
        print('eLineStateCand            ... ', len(getattr(OptModel, f'eLineStateCand_{p}_{sc}_{st}')), ' rows')

    def eSWOnOff(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla or (mTEPES.pSwOnTime[ni,nf,cc] <= 1 and mTEPES.pSwOffTime[ni,nf,cc] <= 1):
            return Constraint.Skip
        if n == mTEPES.n.first():
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - mTEPES.pInitialSwitch[p,sc,n,ni,nf,cc]()             == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
        else:
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - OptModel.vLineCommit[p,sc,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eSWOnOff_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole:
        print('eSWOnOff                  ... ', len(getattr(OptModel, f'eSWOnOff_{p}_{sc}_{st}')), ' rows')

    def eMinSwOnState(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla or mTEPES.pSwOnTime [ni,nf,cc] <= 1 or mTEPES.n.ord(n) <= mTEPES.pSwOnTime [ni,nf,cc]:
            return Constraint.Skip
        return sum(OptModel.vLineOnState [p,sc,n2,ni,nf,cc] for n2 in n2list[mTEPES.n.ord(n)+1-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eMinSwOnState_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole:
        print('eMinSwOnState             ... ', len(getattr(OptModel, f'eMinSwOnState_{p}_{sc}_{st}')), ' rows')

    def eMinSwOffState(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla or mTEPES.pSwOffTime[ni,nf,cc] <= 1 or mTEPES.n.ord(n) <= mTEPES.pSwOffTime[ni,nf,cc]:
            return Constraint.Skip
        return sum(OptModel.vLineOffState[p,sc,n2,ni,nf,cc] for n2 in n2list[mTEPES.n.ord(n)+1-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eMinSwOffState_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole:
        print('eMinSwOffState            ... ', len(getattr(OptModel, f'eMinSwOffState_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Switching minimum on/off state         ... ', round(GeneratingTime), 's')


# @profile
def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    operation model constraints ****')

    StartTime = time.time()

    def eNetCapacity1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or (p,ni,nf,cc) not in mTEPES.pla or ((ni,nf,cc) not in mTEPES.lc and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0) or mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] == 0.0:
            return Constraint.Skip
        return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] >= - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eNetCapacity1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eNetCapacity1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole:
        print('eNetCapacity1             ... ', len(getattr(OptModel, f'eNetCapacity1_{p}_{sc}_{st}')), ' rows')

    def eNetCapacity2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or (p,ni,nf,cc) not in mTEPES.pla or ((ni,nf,cc) not in mTEPES.lc and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0) or mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] == 0.0:
            return Constraint.Skip
        return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] <=   OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eNetCapacity2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eNetCapacity2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole:
        print('eNetCapacity2             ... ', len(getattr(OptModel, f'eNetCapacity2_{p}_{sc}_{st}')), ' rows')

    def eKirchhoff2ndLaw1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndACPowerFlow() or mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() or (p,ni,nf,cc) not in mTEPES.pla or mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]+mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0:
            return Constraint.Skip
        if (ni,nf,cc) in mTEPES.lca:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() * mTEPES.pSBase ==   0
    setattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eKirchhoff2ndLaw1, doc='flow for each AC line, existing or candidate [rad]'))

    if pIndLogConsole:
        print('eKirchhoff2ndLaw1         ... ', len(getattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}')), ' rows')

    def eKirchhoff2ndLaw2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndACPowerFlow() or mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() or (p,ni,nf,cc) not in mTEPES.pla or mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]+mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0:
            return Constraint.Skip
        return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc]() * mTEPES.pSBase <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lca, rule=eKirchhoff2ndLaw2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole:
        print('eKirchhoff2ndLaw2         ... ', len(getattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}')), ' rows')

    def eLineLosses1(OptModel,n,ni,nf,cc):
        # Under AC the loss of an AC branch comes from vFlowElec + vFlowElecBck (eLineLossesAC). A DC branch has no AC physics, so it keeps the
        # loss factor — dropping it there would make every HVDC link lossless.
        if (mTEPES.pIndACPowerFlow() and (ni,nf,cc) in mTEPES.laa) or mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() or mTEPES.pIndBinNetLosses() == 0 or (p,ni,nf,cc) not in mTEPES.pll:
            return Constraint.Skip
        return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlowElec[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eLineLosses1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole:
        print('eLineLosses1              ... ', len(getattr(OptModel, f'eLineLosses1_{p}_{sc}_{st}')), ' rows')

    def eLineLosses2(OptModel,n,ni,nf,cc):
        # Under AC the loss of an AC branch comes from vFlowElec + vFlowElecBck (eLineLossesAC). A DC branch has no AC physics, so it keeps the
        # loss factor — dropping it there would make every HVDC link lossless.
        if (mTEPES.pIndACPowerFlow() and (ni,nf,cc) in mTEPES.laa) or mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() or mTEPES.pIndBinNetLosses() == 0 or (p,ni,nf,cc) not in mTEPES.pll:
            return Constraint.Skip
        return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlowElec[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eLineLosses2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole:
        print('eLineLosses2              ... ', len(getattr(OptModel, f'eLineLosses2_{p}_{sc}_{st}')), ' rows')

    # nodes to generators (g2n)
    g2n = defaultdict(set)
    e2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.eh:
            e2n[nd].add(g)

    def eNetPosition(OptModel,n,nd):
        # net position NP_n = sum of the output of the generators in node n minus its demand
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() == 0:
            return Constraint.Skip
        return (OptModel.vNetPosition[p,sc,n,nd] == sum(OptModel.vTotalOutput[p,sc,n,g] for g in g2n[nd] if (p,g) in mTEPES.pg) - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh) + OptModel.vENS[p,sc,n,nd] - mTEPES.pDemandElec[p,sc,n,nd])
    setattr(OptModel, f'eNetPosition_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eNetPosition, doc='net position [GW]'))

    if pIndLogConsole:
        print('eNetPosition              ... ', len(getattr(OptModel, f'eNetPosition_{p}_{sc}_{st}')), ' rows')

    # The factors come from the case (IndPTDF = 1) or from the reactances (IndPTDF = 2). The computed ones carry no load
    # level index: the topology is fixed for a period, so an hourly index would repeat the same numbers every hour.
    def _pFlowBased(OptModel,n,ni,nf,cc):
        if mTEPES.pIndPTDF() == 2:
            return sum(mTEPES.pPTDFCalc[p,ni,nf,cc,nd] * OptModel.vNetPosition[p,sc,n,nd] for nd in mTEPES.nd if (p,ni,nf,cc,nd) in mTEPES.pland)
        return     sum(mTEPES.pPTDF[p,sc,n,ni,nf,cc,nd] * OptModel.vNetPosition[p,sc,n,nd] for nd in mTEPES.nd if (p,sc,n,ni,nf,cc,nd) in mTEPES.psnland)

    def eFlowBasedCalcu1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() == 0 or mTEPES.pIndBinLinePTDF[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla:
            return Constraint.Skip
        if (ni,nf,cc) in mTEPES.lca:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - _pFlowBased(OptModel,n,ni,nf,cc) >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - _pFlowBased(OptModel,n,ni,nf,cc) ==   0
    setattr(OptModel, f'eFlowBasedCalcu1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.la, rule=eFlowBasedCalcu1, doc='flow based calculation [p.u.]'))

    if pIndLogConsole:
        print('eFlowBasedCalcu1          ... ', len(getattr(OptModel, f'eFlowBasedCalcu1_{p}_{sc}_{st}')), ' rows')

    def eFlowBasedCalcu2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() == 0 or mTEPES.pIndBinLinePTDF[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla:
            return Constraint.Skip
        return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - _pFlowBased(OptModel,n,ni,nf,cc) <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eFlowBasedCalcu2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lca, rule=eFlowBasedCalcu2, doc='flow based calculation [p.u.]'))

    if pIndLogConsole:
        print('eFlowBasedCalcu2          ... ', len(getattr(OptModel, f'eFlowBasedCalcu2_{p}_{sc}_{st}')), ' rows')

    # def eSecurityMargingTTCFrw(OptModel,n,ni,nf,cc):
    #     if mTEPES.pIndBinSingleNode()or mTEPES.pIndPTDF() == 0 or mTEPES.pIndBinLinePTDF[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla:
    #         return Constraint.Skip
    #     return OptModel.vFlowElec[p,sc,n,ni,nf,cc] <=   mTEPES.pVariableTTCFrw[p,sc,n,ni,nf,cc]
    # setattr(OptModel, f'eSecurityMargingTTCFrw_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lca, rule=eSecurityMargingTTCFrw, doc='security margin TTC for flow based calculation [p.u.]'))
    #
    # if pIndLogConsole:
    #     print('eSecurityMargingTTCFrw... ', len(getattr(OptModel, f'eSecurityMargingTTCFrw_{p}_{sc}_{st}')), ' rows')
    #
    # def eSecurityMargingTTCBck(OptModel,n,ni,nf,cc):
    #     if mTEPES.pIndBinSingleNode()or mTEPES.pIndPTDF() == 0 or mTEPES.pIndBinLinePTDF[ni,nf,cc] == 0 or (p,ni,nf,cc) not in mTEPES.pla:
    #         return Constraint.Skip
    #     return OptModel.vFlowElec[p,sc,n,ni,nf,cc] >= - mTEPES.pVariableTTCBck[p,sc,n,ni,nf,cc]
    # setattr(OptModel, f'eSecurityMargingTTCBck_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lca, rule=eSecurityMargingTTCBck, doc='security margin TTC for flow based calculation [p.u.]'))
    #
    # if pIndLogConsole:
    #     print('eSecurityMargingTTCBck... ', len(getattr(OptModel, f'eSecurityMargingTTCBck_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating network    constraints      ... ', round(GeneratingTime), 's')


# @profile
def NetworkCycles(mTEPES, pIndLogConsole):
    print('Network               Cycles Detection ****')

    StartTime = time.time()

    NetworkGraph = nx.Graph()
    NetworkGraph.add_nodes_from(mTEPES.nd)
    NetworkGraph.add_edges_from((ni,nf) for ni,nf,cc in mTEPES.lea)

    # cycles for AC existing lines and non-switchable lines
    mTEPES.nce = nx.cycle_basis(NetworkGraph, list(mTEPES.rf)[0])

    # determining the set of unique existing circuits (only one in case of several circuits in //) and the parallel circuits
    pUniqueCircuits = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.lea, names=('NodeI', 'NodeF', 'Circuit')), columns=['0/1'        ])
    pNoCircuits     = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.br , names=('NodeI', 'NodeF'           )), columns=['No.Circuits'])
    for ni,nf,cc in mTEPES.lea:
        pNoCircuits.loc[ni,nf] += 1
        if pNoCircuits.loc[ni,nf]['No.Circuits'] <= 1:
            pUniqueCircuits.at[(ni,nf,cc),'0/1'] = 1
    pNoCircuits     = pNoCircuits.replace(1,0)
    pNoCircuits     = pNoCircuits[pNoCircuits['No.Circuits'] >  0]
    pUniqueCircuits = pUniqueCircuits[pUniqueCircuits['0/1'] == 1]

    # unique and parallel circuits of existing lines
    mTEPES.ucte = Set(doc='unique   circuits', initialize=[lea for lea in mTEPES.lea if lea in pUniqueCircuits['0/1'    ]])
    mTEPES.pct  = Set(doc='parallel circuits', initialize=[br  for br  in mTEPES.br  if br  in pNoCircuits['No.Circuits']])
    mTEPES.cye  = RangeSet(0,len(mTEPES.nce)-1)

    # graph with all AC existing and candidate lines
    NetworkGraph.add_edges_from((ni,nf) for ni,nf,cc in mTEPES.laa)

    # cycles with AC existing and candidate lines
    mTEPES.ncc = nx.cycle_basis(NetworkGraph, list(mTEPES.rf)[0])

    # cycles added due to considering candidate lines
    mTEPES.ncd = [nc for nc in mTEPES.ncc if nc not in mTEPES.nce]

    # determining the set of unique existing and candidate circuits (only one in case of several circuits in //) and the parallel circuits
    pUniqueCircuits = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.laa, names=('NodeI', 'NodeF', 'Circuit')), columns=['0/1'        ])
    pNoCircuits     = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.br , names=('NodeI', 'NodeF'           )), columns=['No.Circuits'])
    for ni,nf,cc in mTEPES.laa:
        pNoCircuits.loc[ni,nf] += 1
        if pNoCircuits.loc[ni,nf]['No.Circuits'] <= 1:
            pUniqueCircuits.at[(ni,nf,cc),'0/1'] = 1
    pNoCircuits     = pNoCircuits.replace(1,0)
    pNoCircuits     = pNoCircuits[pNoCircuits['No.Circuits'] >  0]
    pUniqueCircuits = pUniqueCircuits[pUniqueCircuits['0/1'] == 1]

    # unique and parallel circuits of candidate lines
    mTEPES.uctc = Set(doc='unique   circuits', initialize=[laa for laa in mTEPES.laa if laa in pUniqueCircuits['0/1']])
    mTEPES.cyc  = RangeSet(0,len(mTEPES.ncd)-1)
    # edges of every cycle, computed once instead of per (cycle, candidate line) pair, same hoist as in CycleConstraints. The list keeps the cycle order for
    # the pBigMTheta sums below; the set makes the membership tests O(1) instead of a scan of the cycle
    pCycleEdges    = {cyc: list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cyc in mTEPES.cyc}
    pCycleEdgesSet = {cyc: set(pCycleEdges[cyc]) for cyc in mTEPES.cyc}
    # candidate lines included in every cycle
    mTEPES.lcac = Set(doc='AC candidate circuits in a cycle', initialize=[(cyc,ni,nf,cc) for cyc,ni,nf,cc in mTEPES.cyc*mTEPES.lca if (ni,nf) in pCycleEdgesSet[cyc] or (nf,ni) in pCycleEdgesSet[cyc]])

    pBigMTheta = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.cyc*mTEPES.lca, names=('No.Cycle', 'NodeI', 'NodeF', 'Circuit')), columns=['rad'])
    # for cyc,nii,nff,ccc in mTEPES.cyc*mTEPES.lca:
    #     if (nii,nff) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) or (nff,nii) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])):
    #         pBigMTheta.loc[cyc,nii,nff,ccc] = (sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) +
    #                                            sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) )
    for cyc,nii,nff,ccc in mTEPES.cyc*mTEPES.lca:
        if (nii,nff) in pCycleEdgesSet[cyc] or (nff,nii) in pCycleEdgesSet[cyc]:
            pBigMTheta.loc[cyc,nii,nff,ccc] = (sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc and (ni!=nii or nf!=nff)) +
                                               sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc and (ni!=nii or nf!=nff)) )

    mTEPES.pBigMTheta = Param(mTEPES.cyc, mTEPES.lca, initialize=pBigMTheta['rad'].to_dict(), doc='big M for an AC candidate line in a cycle [rad]')

    CyclesDetectionTime = time.time() - StartTime
    if pIndLogConsole:
        print('Cycles detection                      ... ', round(CyclesDetectionTime), 's')


# @profile
def CycleConstraints(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network              cycle constraints ****')

    StartTime = time.time()

    # edges of every cycle, computed once instead of twice per constraint row
    pCycleEdges = {cyc: list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cyc in mTEPES.cyc}

    # remove the Kirchhoff's second law for AC existing and candidate lines
    OptModel.del_component(getattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}'))
    OptModel.del_component(getattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}'))

    #%% cycle Kirchhoff's second law with some candidate lines
    # this equation is formulated for every AC candidate line included in the cycle
    def eCycleKirchhoff2ndLawCnd1(OptModel,n,cyc,nii,nff,cc):
        if mTEPES.pIndPTDF() or (p,nii,nff,cc) not in mTEPES.pla:
            return Constraint.Skip
        return (sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) -
                sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) ) / mTEPES.pBigMTheta[cyc,nii,nff,cc] <=   1 - OptModel.vLineCommit[p,sc,n,nii,nff,cc]
    setattr(OptModel, f'eCycleKirchhoff2ndLawCnd1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lcac, rule=eCycleKirchhoff2ndLawCnd1, doc='cycle flow for with some AC candidate lines [rad]'))

    if pIndLogConsole:
        print('eCycleKirchhoff2ndLC1     ... ', len(getattr(OptModel, f'eCycleKirchhoff2ndLawCnd1_{p}_{sc}_{st}')), ' rows')

    def eCycleKirchhoff2ndLawCnd2(OptModel,n,cyc,nii,nff,cc):
        if mTEPES.pIndPTDF() or (p,nii,nff,cc) not in mTEPES.pla:
            return Constraint.Skip
        return (sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) -
                sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in pCycleEdges[cyc] for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) ) / mTEPES.pBigMTheta[cyc,nii,nff,cc] >= - 1 + OptModel.vLineCommit[p,sc,n,nii,nff,cc]
    setattr(OptModel, f'eCycleKirchhoff2ndLawCnd2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lcac, rule=eCycleKirchhoff2ndLawCnd2, doc='cycle flow for with some AC candidate lines [rad]'))

    if pIndLogConsole:
        print('eCycleKirchhoff2ndLC2     ... ', len(getattr(OptModel, f'eCycleKirchhoff2ndLawCnd2_{p}_{sc}_{st}')), ' rows')

    def eFlowParallelCandidate1(OptModel,n,ni,nf,cc,c2):
        if (cc < c2 and (ni,nf,cc) in mTEPES.lea and (ni,nf,c2) in mTEPES.lca) and mTEPES.pIndPTDF() == 0:
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] - OptModel.vFlowElec[p,sc,n,ni,nf,c2] * mTEPES.pLineX[ni,nf,c2] / mTEPES.pLineX[ni,nf,cc]) / max(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc],mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]) <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,c2]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowParallelCandidate1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.pct, mTEPES.cc, mTEPES.c2, rule=eFlowParallelCandidate1, doc='unitary flow for each AC candidate parallel circuit [p.u.]'))

    if pIndLogConsole:
        print('eFlowParallelCnddate1     ... ', len(getattr(OptModel, f'eFlowParallelCandidate1_{p}_{sc}_{st}')), ' rows')

    def eFlowParallelCandidate2(OptModel,n,ni,nf,cc,c2):
        if (cc < c2 and (ni,nf,cc) in mTEPES.lea and (ni,nf,c2) in mTEPES.lca) and mTEPES.pIndPTDF() == 0:
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] - OptModel.vFlowElec[p,sc,n,ni,nf,c2] * mTEPES.pLineX[ni,nf,c2] / mTEPES.pLineX[ni,nf,cc]) / max(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc],mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]) >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,c2]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowParallelCandidate2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.pct, mTEPES.cc, mTEPES.c2, rule=eFlowParallelCandidate2, doc='unitary flow for each AC candidate parallel circuit [p.u.]'))

    if pIndLogConsole:
        print('eFlowParallelCnddate2     ... ', len(getattr(OptModel, f'eFlowParallelCandidate2_{p}_{sc}_{st}')), ' rows')

    CycleFlowTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating cycle flow constraints       ... ', round(CycleFlowTime), 's')

# ======================================================================================================================
# Bus injection AC formulation, in W space and in rectangular coordinates
# ======================================================================================================================

def _tap(mTEPES, la):
    return mTEPES.pLineTapFactor[la]


def SettingUpVariablesBIM(OptModel, mTEPES):
    """Declare the bus-injection voltage variables. Returns the number of variables fixed."""
    pMode = mTEPES.pIndACPowerFlow()
    if pMode not in (2, 3):
        return 0

    StartTime, nFixed = time.time(), 0

    if pMode == 2:
        # The off-diagonal of W, one entry per branch rather than a full matrix: only pairs joined by a branch appear in any constraint.
        OptModel.vWre = Var(mTEPES.psnlaa, within=Reals, doc='real part of W_ij = V_i conj(V_j) [p.u.]')
        OptModel.vWim = Var(mTEPES.psnlaa, within=Reals, doc='imag part of W_ij = V_i conj(V_j) [p.u.]')
        for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
            # |W_ij| <= |V_i||V_j|, so each part is bounded by the product of the voltage ceilings.
            pBound = mTEPES.pVMaxBus[ni] * mTEPES.pVMaxBus[nf]
            for v in (OptModel.vWre, OptModel.vWim):
                v[p,sc,n,ni,nf,cc].setlb(-pBound)
                v[p,sc,n,ni,nf,cc].setub( pBound)
            # the real part is positive for any sane operating point: it is |V_i||V_j| cos(theta_ij) and the angle stays well inside +/- 90 degrees
            OptModel.vWre[p,sc,n,ni,nf,cc].setlb(0.0)
        # u = (W_i + W_j)/2 and v = (W_i - W_j)/2, so that W_i W_j = u^2 - v^2 and the cone becomes the STANDARD form
        # ||(Wre, Wim, v)|| <= u. See the header: the rotated form is only convex if the solver recognises it, and that recognition is brittle.
        OptModel.vWsum = Var(mTEPES.psnlaa, within=Reals, doc='half sum of the two bus |V|^2 [p.u.]')
        OptModel.vWdif = Var(mTEPES.psnlaa, within=Reals, doc='half difference of the two bus |V|^2 [p.u.]')
        for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
            pHi = (mTEPES.pVMaxBus[ni] ** 2 + mTEPES.pVMaxBus[nf] ** 2) / 2.0
            OptModel.vWsum[p,sc,n,ni,nf,cc].setlb(0.0)  ; OptModel.vWsum[p,sc,n,ni,nf,cc].setub(pHi)
            OptModel.vWdif[p,sc,n,ni,nf,cc].setlb(-pHi) ; OptModel.vWdif[p,sc,n,ni,nf,cc].setub(pHi)
    else:
        OptModel.vVre = Var(mTEPES.psnnd, within=Reals, initialize=1.0, doc='real part of the bus voltage [p.u.]')
        OptModel.vVim = Var(mTEPES.psnnd, within=Reals, initialize=0.0, doc='imag part of the bus voltage [p.u.]')
        for p, sc, n, nd in mTEPES.psnnd:
            OptModel.vVre[p,sc,n,nd].setlb(-mTEPES.pVMaxBus[nd]); OptModel.vVre[p,sc,n,nd].setub(mTEPES.pVMaxBus[nd])
            OptModel.vVim[p,sc,n,nd].setlb(-mTEPES.pVMaxBus[nd]); OptModel.vVim[p,sc,n,nd].setub(mTEPES.pVMaxBus[nd])
        # the reference bus fixes the angle as well as the magnitude, which is what removes the rotational degeneracy
        ref = mTEPES.rf.first()
        for p, sc, n in mTEPES.psn:
            OptModel.vVre[p,sc,n,ref].fix(mTEPES.pVNom())
            OptModel.vVim[p,sc,n,ref].fix(0.0)
            nFixed += 2

    print('Setting up BIM variables               ... ', round(time.time() - StartTime), 's')
    return nFixed


def NetworkBIMOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Bus-injection network constraints for one (period, scenario, stage)."""
    pMode = mTEPES.pIndACPowerFlow()
    if pMode not in (2, 3):
        return

    print(f'BIM network model ({"W space" if pMode == 2 else "rectangular"}) ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    def _y(la):
        pZ2 = mTEPES.pLineZ2[la]
        return mTEPES.pLineR[la] / pZ2, -mTEPES.pLineX[la] / pZ2       # g, b of the series admittance

    # --- voltage magnitude, the link to the shared AC machinery ---------------------------------------------------------------------------------
    # vW is declared by the shared AC block and used by the shunts, the bounds and every writer, so both modes must define it rather than invent a
    # second voltage variable.
    if pMode == 3:
        def eVoltageSquare(OptModel, n, nd):
            return OptModel.vW[p,sc,n,nd] == OptModel.vVre[p,sc,n,nd] ** 2 + OptModel.vVim[p,sc,n,nd] ** 2
        setattr(OptModel, f'eVoltageSquare_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eVoltageSquare, doc='|V|^2 from the rectangular parts'))

    # --- branch flows ---------------------------------------------------------------------------------------------------------------------------
    def _flows(OptModel, n, ni, nf, cc):
        """(P_ij, Q_ij, P_ji, Q_ji) in per unit, from whichever voltage representation is active."""
        g, b   = _y((ni,nf,cc))
        bsh    = mTEPES.pLineBsh[ni,nf,cc]() / 2.0
        a      = _tap(mTEPES, (ni,nf,cc))
        if pMode == 2:
            Wii, Wjj = OptModel.vW[p,sc,n,ni], OptModel.vW[p,sc,n,nf]
            Wre, Wim = OptModel.vWre[p,sc,n,ni,nf,cc], OptModel.vWim[p,sc,n,ni,nf,cc]
        else:
            ei, fi = OptModel.vVre[p,sc,n,ni], OptModel.vVim[p,sc,n,ni]
            ej, fj = OptModel.vVre[p,sc,n,nf], OptModel.vVim[p,sc,n,nf]
            Wii, Wjj = ei*ei + fi*fi, ej*ej + fj*fj
            Wre, Wim = ei*ej + fi*fj, fi*ej - ei*fj
        # SERIES flows only, with the charging term bsh deliberately left OUT.
        #
        # eBalanceReact is shared with branch flow, where vFlowReactFrw carries the series flow and the pi-model charging is added separately as
        # pFixedCharge * vW * pSBase. Including bsh here as well counts the charging TWICE: the branch equation injects it and the balance injects it
        # again, which hands the system free reactive power and drops the objective. On 9n_AC that was most of a 10.5% gap against branch flow.
        Pij =  g * a*a * Wii - a * ( g * Wre + b * Wim)
        Qij = -b * a*a * Wii - a * ( g * Wim - b * Wre)
        Pji =  g * Wjj       - a * ( g * Wre - b * Wim)
        Qji = -b * Wjj       - a * (-g * Wim - b * Wre)
        return Pij, Qij, Pji, Qji

    for pIdx, (pVar, pName) in enumerate((('vFlowElec', 'eBIMFlowP'), ('vFlowReactFrw', 'eBIMFlowQ'),
                                          ('vFlowElecBck', 'eBIMFlowPBck'), ('vFlowReactBck', 'eBIMFlowQBck'))):
        def rule(OptModel, n, ni, nf, cc, k=pIdx, v=pVar):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return getattr(OptModel, v)[p,sc,n,ni,nf,cc] == _flows(OptModel, n, ni, nf, cc)[k] * pSBase
        setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=rule, doc='bus-injection branch flow [GW/Gvar]'))

    # --- the relaxation, and the thermal limit --------------------------------------------------------------------------------------------------
    if pMode == 2:
        # W = V V^H is rank one; dropping the rank and keeping only the 2x2 minor gives the standard SOC relaxation. Equality would be exact.
        # Written in STANDARD cone form, not as Wre^2 + Wim^2 <= W_i W_j. The natural form leaves a negative bilinear term, so the quadratic matrix
        # is indefinite and Gurobi treats the whole model as non-convex: barrier reports "numerical trouble" and only a spatial branch and bound with
        # NonConvex=2 gets an answer, which is not what a convex relaxation is for. The identity below is the usual rotated-to-standard transformation
        # and is recognised as a second-order cone:
        #     Wre^2 + Wim^2 <= W_i W_j    <=>    || (2 Wre, 2 Wim, W_i - W_j) || <= W_i + W_j        for W_i, W_j >= 0
        def eBIMWsum(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return 2.0 * OptModel.vWsum[p,sc,n,ni,nf,cc] == OptModel.vW[p,sc,n,ni] + OptModel.vW[p,sc,n,nf]
        setattr(OptModel, f'eBIMWsum_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMWsum, doc='half sum of the bus voltages squared'))

        def eBIMWdif(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return 2.0 * OptModel.vWdif[p,sc,n,ni,nf,cc] == OptModel.vW[p,sc,n,ni] - OptModel.vW[p,sc,n,nf]
        setattr(OptModel, f'eBIMWdif_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMWdif, doc='half difference of the bus voltages squared'))

        # STANDARD second-order cone: ||(Wre, Wim, v)|| <= u, one negative eigenvalue on a non-negative variable. The equivalent rotated form
        # Wre^2 + Wim^2 <= W_i W_j leaves an indefinite bilinear term whose convexity the solver has to infer.
        def eBIMCone(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vWre[p,sc,n,ni,nf,cc] ** 2 + OptModel.vWim[p,sc,n,ni,nf,cc] ** 2
                    + OptModel.vWdif[p,sc,n,ni,nf,cc] ** 2 <= OptModel.vWsum[p,sc,n,ni,nf,cc] ** 2)
        setattr(OptModel, f'eBIMCone_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMCone, doc='SOC relaxation of the rank-one condition'))

    # Plain Smax, which is NOT what branch flow admits: there the limit is on the current, so apparent power up to Smax Vmax / Vmin gets through. The
    # matched version was tried and is left out, because widening this limit by that 1.5% was on its own enough to turn a model that solved into one
    # where barrier reports numerical trouble. That fragility is worth knowing about and is recorded in the module header; it also means the two
    # formulations do not yet have the same feasible set.
    def eBIMSLimit(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        pSmax = mTEPES.pLineSmax[ni,nf,cc]
        # LINEAR in vLineCommit, not squared. Squaring puts a variable product on the right of a <=, which is non-convex and stops the barrier
        # dead with "numerical trouble" even when the variable is fixed. vLineCommit is 0 or 1, so the two forms agree where it matters.
        # Exactly what branch flow admits, transcribed. There the limit is on the current, vCurr <= (Smax/(Vmin tau))^2, and with
        # P^2 + Q^2 <= vW tau^2 vCurr S^2 that comes to P^2 + Q^2 <= (Smax/Vmin)^2 vW_i: voltage-DEPENDENT, not a flat cap at Smax. Writing it this
        # way keeps the right-hand side linear in vW, so the constraint stays a cone, and gives the two formulations the same feasible set.
        pVmin = mTEPES.pVMinBus[ni] * _tap(mTEPES, (ni,nf,cc))
        return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                <= (pSmax / pVmin) ** 2 * OptModel.vW[p,sc,n,ni] * OptModel.vLineCommit[p,sc,n,ni,nf,cc])
    setattr(OptModel, f'eBIMSLimit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMSLimit, doc='apparent power limit, gated on service [GVA]'))

    # --- angle-difference bounds ----------------------------------------------------------------------------------------------------------------
    # The same band branch flow imposes on vTheta, and in W space it is LINEAR: Wre is |V_i||V_j| cos(theta_ij) and Wim is |V_i||V_j| sin(theta_ij),
    # so tan(theta_ij) = Wim / Wre and a bound on the angle is a bound on that ratio. Without these, bus injection would be missing the tightening
    # that TightenACBounds computes and the comparison would flatter branch flow for a reason that has nothing to do with the representation.
    # The same band branch flow imposes on vTheta. It still defeats the barrier even with the cone in standard form, so the rotated form was NOT the
    # cause -- an earlier version of this comment said it was, on one experiment, and that was wrong.
    # Both modes, not just W space. Rectangular carried no angle band at all until this was noticed, which left mode 3 solving a DIFFERENT problem
    # from modes 1 and 2: on a 24 hour RTS window it returned 5.53 MEUR against 8.06 for branch flow, below a valid relaxation of the same system,
    # which is only possible if the feasible set is larger. It also let the pglib case118 check land 0.117% BELOW the published optimum, because
    # pglib imposes a 30 degree band that our model was ignoring.
    if pMode in (2, 3):
        pTanMax = math.tan(math.pi / 2 * 0.999)                 # the band is clamped below pi/2, but keep tan finite whatever arrives

        def _wparts(OptModel, n, ni, nf, cc):
            """(Wre, Wim) of W_ij = V_i conj(V_j), from whichever voltage representation is active."""
            if pMode == 2:
                return OptModel.vWre[p,sc,n,ni,nf,cc], OptModel.vWim[p,sc,n,ni,nf,cc]
            pEi, pFi = OptModel.vVre[p,sc,n,ni], OptModel.vVim[p,sc,n,ni]
            pEj, pFj = OptModel.vVre[p,sc,n,nf], OptModel.vVim[p,sc,n,nf]
            return pEi * pEj + pFi * pFj, pFi * pEj - pEi * pFj

        def _band(pSign, pName):
            def rule(OptModel, n, ni, nf, cc):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                pLim = mTEPES.pMaxAngleDiff[ni,nf,cc] if pSign > 0 else mTEPES.pMinAngleDiff[ni,nf,cc]
                pTan = max(-pTanMax, min(pTanMax, math.tan(pLim)))
                pRe, pIm = _wparts(OptModel, n, ni, nf, cc)
                if pSign > 0:
                    return pIm <= pTan * pRe
                return     pIm >= pTan * pRe
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=rule, doc='angle-difference band'))

        _band(+1, 'eBIMAngleUp')
        _band(-1, 'eBIMAngleLo')

    # --- the loop condition ------------------------------------------------------------------------------------------------------------------
    # The tangent equality PowerModels uses in ACTPowerModel:  Wim == tan(theta_i - theta_j) Wre.
    #
    # In W space the angle lives in arg(W_ij) and nothing ties it around a loop, so a solution can carry branch flows that no set of bus angles
    # reproduces. Measured on 9n_AC without this, the recovered angles missed closing by 3.6e-04 rad. Tying them to vTheta -- which is a NODE
    # POTENTIAL, so its differences sum to zero around any cycle by construction -- is what makes them consistent. That is also why PowerModels has no
    # cycle constraints anywhere: once an angle variable exists, the loop condition follows from the tangent coupling.
    #
    # An earlier version summed Wim / Vnom^2 around each independent cycle instead. It cut the loop mismatch about fourfold and moved the objective
    # only in the eighth digit, because arg(W_ij) is Wim/Wre and not Wim over a constant.
    #
    # The tangent is non-convex, so this turns the relaxation into something closer to the exact model and needs a non-linear solver. Mode 2 already
    # wants ipopt for the reasons in the header.
    if pMode == 2 and mTEPES.pIndACCycle():
        def eBIMTangent(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vWim[p,sc,n,ni,nf,cc]
                    == tan(OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) * OptModel.vWre[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eBIMTangent_{p}_{sc}_{st}',
                Constraint(mTEPES.n*mTEPES.laa, rule=eBIMTangent, doc='angle tied to the voltage product, ACT form'))

    print('Generating BIM network constraints     ... ', round(time.time() - StartTime), 's')

# ======================================================================================================================
# Branch flow AC formulation, the converter models and the exact restoration pass
# ======================================================================================================================

PWL_SEGMENTS = 10


# Tangent lines used to approximate the converter capability disc. Twelve leaves the bound loose by 1/cos(pi/12), i.e. 3.5%.
CONV_CUTS = 12

def _smax_pu(mTEPES, la):
    """Largest apparent power the model permits on a branch, in per unit.

    The thermal limit is written on the current as ``vCurr <= (Smax/Vmin)^2``, and the current definition gives ``P^2 + Q^2 <= vW*vCurr``, so the
    apparent power the model actually admits is ``Smax * Vmax / Vmin`` — not ``Smax``. Every big-M and every variable box derived in this module uses
    this value, so that they dominate what the model can reach rather than what a first reading of the rating suggests.
    """
    return mTEPES.pLineSmax[la] / mTEPES.pSBase * mTEPES.pVMaxBus[la[0]] / mTEPES.pVMinBus[la[0]]


def _z(mTEPES, la):
    return math.sqrt(mTEPES.pLineZ2[la])


# An off-nominal transformer is an ideal ratio tau at the sending end followed by the series impedance. The impedance therefore sees |V_i|/tau, not
# |V_i|, and every branch equation that reads the sending-end voltage has to read the transformed one. pLineTapFactor is 1/tau, so the effective
# sending voltage is |V_i| * pLineTapFactor and the effective squared voltage is w_i * pLineTapFactor^2.
#
# Leaving this out solves every transformer as 1:1. It is silent: the model stays feasible and the voltages simply come out wrong. RTS-GMLC_AC ships
# 16 transformers with taps of 1.015 and 1.03, so roughly a 3% error in the voltage the impedance sees, and a matching error in the reactive flow.
def _tap2(mTEPES, la):
    return mTEPES.pLineTapFactor[la] ** 2


def _vlo_from(mTEPES, la):
    """Lowest voltage the series impedance sees at the sending end, tap included."""
    return mTEPES.pVMinBus[la[0]] * mTEPES.pLineTapFactor[la]


def _vhi_from(mTEPES, la):
    """Highest voltage the series impedance sees at the sending end, tap included."""
    return mTEPES.pVMaxBus[la[0]] * mTEPES.pLineTapFactor[la]


def NetworkACOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Add the AC network constraints for one (period, scenario, stage).

    The nodal balances, the shunts, the reactive capability and the HVDC converters are shared by every AC formulation and are built here for all of
    them. Only the branch flow relations -- the voltage drop, the far-end flow definitions, the current limit and the angle envelope -- are specific
    to mode 1; bus injection supplies its own in openTEPES_ModelFormulationElectricity. Guarding the WHOLE function on mode 1 left modes 2 and 3 with no
    power balance at all, because the DC balance is already skipped whenever AC is on.
    """
    if not mTEPES.pIndACPowerFlow():
        return
    pBFM = mTEPES.pIndACPowerFlow() == 1

    print('AC network operation model constraints ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    # --- topology, hoisted once ------------------------------------------------------------------------------------------------------------------
    acOut, acIn = defaultdict(list), defaultdict(list)
    for la in mTEPES.laa:
        if _live(la):
            acOut[la[0]].append(la)
            acIn [la[1]].append(la)

    dcOut, dcIn = defaultdict(list), defaultdict(list)
    for la in mTEPES.lad:
        if _live(la):
            dcOut[la[0]].append(la)
            dcIn [la[1]].append(la)

    g2n, e2n = defaultdict(set), defaultdict(set)
    for nd, g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.eh:
            e2n[nd].add(g)

    # from n2gq, not from n2g filtered by gq: a synchronous condenser has MaximumPower = 0 and so is not in mTEPES.g, hence not in n2g
    q2n = defaultdict(set)
    for nd, gq in mTEPES.n2gq:
        q2n[nd].add(gq)

    sh2nd = defaultdict(list)
    for nd, sh in mTEPES.n2sh:
        sh2nd[nd].append(sh)

    # HVDC converter model, if any. pConvTan is tan(acos(pf)): the reactive power a station draws per unit of active power it carries (LCC), or the
    # most it can supply or absorb at its rating (VSC).
    pConvLCC = mTEPES.pIndACConverter() == 1 and bool(mTEPES.lad)
    pConvVSC = mTEPES.pIndACConverter() == 2 and bool(mTEPES.lad)
    pConvTan = math.tan(math.acos(min(max(mTEPES.pConverterPF(), 1e-3), 1.0)))

    # Converter station losses. Each terminal of a DC link carries a station, and each station is charged separately, which is the same convention the
    # existing DC line loss factor already uses. The no-load part is paid whenever the link is in service; the marginal part is paid on what the
    # station carries, either way it flows. Both are zero unless the case asks for them.
    pConvLossNL = mTEPES.pConverterNoLoadLoss()   if (pConvLCC or pConvVSC) else 0.0
    pConvLossMG = mTEPES.pConverterMarginalLoss() if (pConvLCC or pConvVSC) else 0.0
    pConvLoss   = bool(pConvLossNL or pConvLossMG)

    # A shunt conductance draws active power. It is zero in almost every case, so the whole active-shunt block is built only when some device has one.
    pShuntG = any(mTEPES.pBusGshb[sh]() for sh in mTEPES.sh) if mTEPES.sh else False

    # Unfiltered branch incidence, matching what the dual readers in OutputResultsEconomic use to decide a node has a balance.
    ndHasBranch = defaultdict(bool)
    for la in mTEPES.la:
        ndHasBranch[la[0]] = True
        ndHasBranch[la[1]] = True

    # Half the line charging susceptance at each end, the pi model, for branches that exist in this period. A branch whose commitment can fall to zero
    # contributes through the switched term instead: a line out of service charges nothing.
    pFixedCharge, pSwitchedChrg = defaultdict(float), defaultdict(list)
    for la in mTEPES.laa:
        if not _live(la):
            continue
        for nd in (la[0], la[1]):
            # a switchable EXISTING line has a free vLineCommit too, so its charging is switched, not fixed
            if la in mTEPES.lca or mTEPES.pIndBinLineSwitch[la]:
                pSwitchedChrg[nd].append(la)
            else:
                pFixedCharge[nd] += mTEPES.pLineBsh[la]() / 2.0

    # --- (11) active power balance ---------------------------------------------------------------------------------------------------------------
    def eBalanceElecAC(OptModel, n, nd):
        # The demand test is load-bearing. acOut/acIn/dcOut/dcIn are filtered by _live(), so a node whose only connection is a candidate line
        # not yet in its period window has all four empty. Skipping there would delete pDemandElec from the model rather than report it as
        # ENS, and the run would understate served demand with no infeasibility and no message. The DC balance does not have this problem
        # because it builds lout/lin over all of mTEPES.la with no period filter.
        # The test uses the UNFILTERED branch lists. OutputResultsEconomic decides whether a node has a dual to read with
        # `bool(lout[nd]) or bool(lin[nd]) or any generator`, built over all of mTEPES.la with no period filter. Skipping on the _live()-filtered
        # lists would make this constraint absent where the reader still expects it, and the run would die with a KeyError on pDuals after solving
        # successfully. The demand term is kept so a node with no branch at all still reports its load as ENS.
        if not (g2n[nd] or ndHasBranch[nd] or mTEPES.pDemandElec[p,sc,n,nd]()):
            return Constraint.Skip
        return (sum(OptModel.vTotalOutput   [p,sc,n,g ] for g  in g2n[nd] if (p,g ) in mTEPES.pg )
              - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh)
              + OptModel.vENS[p,sc,n,nd]
              # a shunt with a non-zero conductance draws active power; pShuntG is empty for the usual Gshb = 0 case
              + sum(OptModel.vPShunt[p,sc,n,sh] for sh in sh2nd[nd] if pShuntG and (p,sc,n,sh) in mTEPES.psnsh)
              # AC branches: the near end injects vFlowElec, the far end vFlowElecBck, and their sum is the loss
              - sum(OptModel.vFlowElec   [(p,sc,n)+la] for la in acOut[nd])
              - sum(OptModel.vFlowElecBck[(p,sc,n)+la] for la in acIn [nd])
              # DC branches: a controllable link with the loss factor, exactly as the DC balance treats them
              - sum(OptModel.vFlowElec  [(p,sc,n)+la] for la in dcOut[nd])
              + sum(OptModel.vFlowElec  [(p,sc,n)+la] for la in dcIn [nd])
              - sum(OptModel.vLineLosses[(p,sc,n)+la] for la in dcOut[nd] if (p,)+la in mTEPES.pll)
              - sum(OptModel.vLineLosses[(p,sc,n)+la] for la in dcIn [nd] if (p,)+la in mTEPES.pll)
              # HVDC converter stations. The station standing at this node draws its no-load loss while the link is in service and its marginal loss on
              # whatever it carries. vLineCommit is fixed at 1 for a link that is neither switchable nor a candidate, so for those the first term is a
              # constant and costs the solver nothing.
              - (pConvLossNL * sum(mTEPES.pLineNTCMax[la] * OptModel.vLineCommit[(p,sc,n)+la] for la in dcOut[nd] + dcIn[nd]) if pConvLossNL else 0.0)
              - (pConvLossMG * sum(OptModel.vDCFlowPos[(p,sc,n)+la] + OptModel.vDCFlowNeg[(p,sc,n)+la] for la in dcOut[nd] + dcIn[nd]) if pConvLossMG else 0.0)
              == mTEPES.pDemandElec[p,sc,n,nd])
    setattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceElecAC, doc='electric load generation balance [GW]'))
    if pIndLogConsole:
        print('eBalanceElec (AC)         ... ', len(getattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}')), ' rows')

    # The two halves of |P_dc|. Pinning only the difference is NOT conservative: the draw enters the reactive balance with a MINUS, so a node whose
    # charging exceeds its demand gains by inflating both halves, absorbing the surplus for free and hiding it from the results. vDCFlowDir fixes it.
    if pConvLCC or pConvLoss:
        def eDCFlowSplit(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] - OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc]
                    == OptModel.vFlowElec[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eDCFlowSplit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowSplit, doc='signed parts of the DC link flow [GW]'))

        # Only one half may be non-zero, so pos + neg is exactly |P|. Without this the pair can both be inflated, and because the converter draw enters
        # the reactive balance with a minus, a node with surplus reactive power gains by doing so: the converter becomes a free reactive sink and the
        # surplus never appears in oT_Result_NetworkQNS.
        def eDCFlowDirPos(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] <= mTEPES.pLineNTCMax[ni,nf,cc] * OptModel.vDCFlowDir[p,sc,n,ni,nf,cc]
        setattr(OptModel, f'eDCFlowDirPos_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowDirPos, doc='forward part only when the flow is forward [GW]'))

        def eDCFlowDirNeg(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc] <= mTEPES.pLineNTCMax[ni,nf,cc] * (1 - OptModel.vDCFlowDir[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eDCFlowDirNeg_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowDirNeg, doc='reverse part only when the flow is reverse [GW]'))

    # A converter that is not there supplies nothing. vLineCommit is fixed at 1 for a DC link that is neither switchable nor a candidate, so for those
    # this is slack; for a candidate it is what stops the model taking free reactive support from a link it never builds.
    if pConvVSC:
        def _eQConvOff(vVar, pName):
            def rule(OptModel, n, ni, nf, cc, s=+1):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                pQMax = pConvTan * mTEPES.pLineNTCMax[ni,nf,cc]
                return (vVar[p,sc,n,ni,nf,cc] <=  pQMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc]) if s > 0 else \
                       (vVar[p,sc,n,ni,nf,cc] >= -pQMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc])
            return rule

        for vVar, pStem in ((OptModel.vQConvFrw, 'eQConvFrw'), (OptModel.vQConvBck, 'eQConvBck')):
            setattr(OptModel, f'{pStem}OffUp_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc, v=vVar: _eQConvOff(v, '')(m, n, ni, nf, cc, +1),
                               doc='an out-of-service converter injects nothing [Gvar]'))
            setattr(OptModel, f'{pStem}OffLo_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc, v=vVar: _eQConvOff(v, '')(m, n, ni, nf, cc, -1),
                               doc='an out-of-service converter absorbs nothing [Gvar]'))

    # --- converter capability: the station rating is on the APPARENT power ------------------------------------------------------------------------
    # Active and reactive power were bounded separately, so a station could sit at P = NTC and Q = tan(acos(pf)) NTC at the same time and deliver
    # |S| = NTC / pf. At the default power factor of 0.85 that is 17.6% more apparent power than the converter has, and 5.3% at 0.95.
    #
    # The limit is a disc, P^2 + Q^2 <= S^2, and it is written as a ring of linear cuts rather than as that disc. Two reasons. A quadratic constraint
    # would put a cone into IndACModelType = 1, whose whole purpose is to stay a MILP that an LP/MIP solver can take, and on a tightly rated link the
    # disc made the barrier stop with "numerical trouble" where the same case solved without it.
    #
    # CONV_CUTS tangent lines circumscribe the disc, so the bound is loose by 1/cos(pi/CONV_CUTS): 3.5% at 12 cuts. That is an approximation, and it
    # is a fifth of the 17.6% it replaces.
    if pConvLCC or pConvVSC:
        def eConvSLimit(OptModel, n, ni, nf, cc, k=0, pSide=+1):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            pSmax = mTEPES.pLineNTCMax[ni,nf,cc]
            if pConvVSC:
                pQ = OptModel.vQConvFrw[p,sc,n,ni,nf,cc] if pSide > 0 else OptModel.vQConvBck[p,sc,n,ni,nf,cc]
                pAng = 2.0 * math.pi * k / CONV_CUTS
                return (math.cos(pAng) * OptModel.vFlowElec[p,sc,n,ni,nf,cc] + math.sin(pAng) * pQ <= pSmax)
            # An LCC draws tan(acos(pf)) |P|, so P^2 + Q^2 = P^2 (1 + tan^2) and the disc collapses to a linear bound on |P|, exactly and with no
            # cuts. |P| is already split for the reactive draw.
            return (OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] + OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc]
                    <= pSmax * min(max(mTEPES.pConverterPF(), 1e-3), 1.0))

        if pConvLCC:
            setattr(OptModel, f'eConvSLimit_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc: eConvSLimit(m, n, ni, nf, cc),
                               doc='converter apparent power within its rating [GVA]'))
        else:
            for pSide, pTag in ((+1, 'Frw'), (-1, 'Bck')):
                for k in range(CONV_CUTS):
                    setattr(OptModel, f'eConvSLimit{pTag}{k}_{p}_{sc}_{st}',
                            Constraint(mTEPES.n*mTEPES.lad,
                                       rule=lambda m, n, ni, nf, cc, kk=k, t=pSide: eConvSLimit(m, n, ni, nf, cc, kk, t),
                                       doc='converter apparent power within its rating [GVA]'))

    # --- (12) reactive power balance -------------------------------------------------------------------------------------------------------------
    def eBalanceReact(OptModel, n, nd):
        # the demand test matters: a node fed only by an HVDC link has no AC branch and no reactive device, but it still has reactive demand, and
        # skipping here would drop that demand from the model altogether instead of surfacing it as vQNSPos
        # DC terminals count too once a converter model is on: a node whose only connection is an HVDC link still has a converter sitting on it,
        # and skipping here would drop that reactive draw or supply from the model entirely.
        if not (q2n[nd] or acOut[nd] or acIn[nd] or sh2nd[nd] or mTEPES.pReactiveDemand[p,sc,n,nd]()
                or ((pConvLCC or pConvVSC) and (dcOut[nd] or dcIn[nd]))):
            return Constraint.Skip
        return (sum(OptModel.vReactiveTotalOutput[p,sc,n,gq] for gq in q2n[nd] if (p,gq) in mTEPES.pgq)
              + sum(OptModel.vQShunt[p,sc,n,sh] for sh in sh2nd[nd] if (p,sc,n,sh) in mTEPES.psnsh)
              + pFixedCharge[nd] * OptModel.vW[p,sc,n,nd] * pSBase
              # A switchable or candidate branch charges only while in service. The exact term would be Bsh/2 * vW * vLineCommit, a product of two
              # variables; the voltage is held at nominal instead, which keeps it linear at the cost of the voltage band's spread — at most about
              # +/-10% of the charging on a 0.95-1.05 band. This is the one place the reactive balance is not exact.
              + sum(mTEPES.pLineBsh[la]() / 2.0 * mTEPES.pVNom ** 2 * pSBase * OptModel.vLineCommit[(p,sc,n)+la] for la in pSwitchedChrg[nd])
              + OptModel.vQNSPos[p,sc,n,nd] - OptModel.vQNSNeg[p,sc,n,nd]
              - sum(OptModel.vFlowReactFrw[(p,sc,n)+la] for la in acOut[nd])
              - sum(OptModel.vFlowReactBck[(p,sc,n)+la] for la in acIn [nd])
              # HVDC converters. An LCC station DRAWS reactive power at both terminals, proportional to the active power it transfers; a VSC station
              # supplies or absorbs it within its rating. The two enter with opposite signs, which is exactly why a single loss factor cannot stand in
              # for either of them.
              - (pConvTan * sum(OptModel.vDCFlowPos[(p,sc,n)+la] + OptModel.vDCFlowNeg[(p,sc,n)+la] for la in dcOut[nd] + dcIn[nd]) if pConvLCC else 0.0)
              + (             sum(OptModel.vQConvFrw[(p,sc,n)+la] for la in dcOut[nd])
                            + sum(OptModel.vQConvBck[(p,sc,n)+la] for la in dcIn [nd])                                             if pConvVSC else 0.0)
              == mTEPES.pReactiveDemand[p,sc,n,nd])
    setattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceReact, doc='reactive load generation balance [Gvar]'))
    if pIndLogConsole:
        print('eBalanceReact             ... ', len(getattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}')), ' rows')

    # ONLY the branch flow relations are mode 1. Everything after this block -- the reactive capability limits, the idle-unit gate, the
    # shunt definitions and the condenser investment gates -- is shared by every AC formulation, so it must not sit behind this guard.
    # An earlier version returned here instead of wrapping, which left bus injection with no reactive capability limit at all: generators
    # supplied their full nameplate Mvar untied to any active output, and used eight times the reactive power branch flow did.
    if pBFM:
        # --- the far end of the branch, and the loss -------------------------------------------------------------------------------------------------
        # Power arriving at nf is what entered at ni less the series loss, so the power leaving nf into the branch is its negative. Chowdhury et al. write
        # (P_ij - r_ij l_ij) inline and carry no far-end variable; one is kept here so vLineLosses can be defined and every existing loss report stays
        # correct. Declaring it without these equations leaves it free, and the model then reports zero losses.
        def eFlowElecBck(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowElecBck[p,sc,n,ni,nf,cc]
                    == -OptModel.vFlowElec[p,sc,n,ni,nf,cc] + mTEPES.pLineR[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase)
        setattr(OptModel, f'eFlowElecBck_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eFlowElecBck, doc='active power leaving nf into the branch [GW]'))

        def eFlowReactBck(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowReactBck[p,sc,n,ni,nf,cc]
                    == -OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] + mTEPES.pLineX[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase)
        setattr(OptModel, f'eFlowReactBck_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eFlowReactBck, doc='reactive power leaving nf into the branch [Gvar]'))

        def eLineLossesAC(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)) or (p,ni,nf,cc) not in mTEPES.pll:
                return Constraint.Skip
            # vLineLosses is documented as HALF the branch loss, and the output layer multiplies by two
            return (OptModel.vLineLosses[p,sc,n,ni,nf,cc]
                    == 0.5 * (OptModel.vFlowElec[p,sc,n,ni,nf,cc] + OptModel.vFlowElecBck[p,sc,n,ni,nf,cc]))
        setattr(OptModel, f'eLineLossesAC_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eLineLossesAC, doc='half the exact AC branch loss [GW]'))

        # --- (7) the thermal limit, gated on service -------------------------------------------------------------------------------------------------
        # A branch out of service carries no current, and with vCurr driven to zero the current definition — cone or staircase — forces both flows to zero
        # too, because vW is bounded below by a positive number. One constraint therefore gates P, Q and the loss together. vLineCommit is fixed at 1 for
        # a line that is neither switchable nor a candidate, so for those this is a plain thermal limit.
        def eCurrentLimit(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            pIMax = (mTEPES.pLineSmax[ni,nf,cc] / pSBase / _vlo_from(mTEPES, (ni,nf,cc))) ** 2
            return OptModel.vCurr[p,sc,n,ni,nf,cc] <= pIMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        setattr(OptModel, f'eCurrentLimit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentLimit, doc='thermal limit, released out of service [p.u.]'))

        # --- (9) voltage drop ------------------------------------------------------------------------------------------------------------------------
        # The big-M is derived from the three terms of the expression rather than guessed. The flow term dominates and was omitted once, leaving an
        # arbitrary constant as the only thing keeping the relaxation valid.
        def _pDropExpr(n, ni, nf, cc):
            return (OptModel.vW[p,sc,n,nf] - OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))
                    + 2.0 * (mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                           + mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                    - mTEPES.pLineZ2[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc])

        pDropM = {}
        for la in mTEPES.laa:
            ni, nf, cc = la
            pFlow = 2.0 * _z(mTEPES, la) * _smax_pu(mTEPES, la)                                                    # |2(rP+xQ)|/S, by Cauchy-Schwarz
            pLoss = mTEPES.pLineZ2[la] * (mTEPES.pLineSmax[la] / pSBase / _vlo_from(mTEPES, la)) ** 2
            pDropM[la] = (max((mTEPES.pVMaxBus[nf] ** 2 - _vlo_from(mTEPES, la) ** 2) + pFlow,         0.0),        # largest the expression can be
                          min((mTEPES.pVMinBus[nf] ** 2 - _vhi_from(mTEPES, la) ** 2) - pFlow - pLoss, 0.0))       # and the smallest

        def eVoltageDropUp(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return _pDropExpr(n,ni,nf,cc) <= pDropM[ni,nf,cc][0] * (1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eVoltageDropUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eVoltageDropUp, doc='voltage drop along an AC branch, upper [p.u.]'))

        def eVoltageDropLo(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return _pDropExpr(n,ni,nf,cc) >= pDropM[ni,nf,cc][1] * (1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eVoltageDropLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eVoltageDropLo, doc='voltage drop along an AC branch, lower [p.u.]'))
        if pIndLogConsole:
            print('eVoltageDrop              ... ', 2*len(getattr(OptModel, f'eVoltageDropUp_{p}_{sc}_{st}')), ' rows')

        # --- (16)/(17) the angle envelope ------------------------------------------------------------------------------------------------------------
        def eAngleEnvM(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            # MINUS, not plus. With y = (r - jx)/z^2, P = [(v_i^2 - v_i v_j cos th) r + (v_i v_j sin th) x]/z^2 and Q the same with x and -r, so
            # x P - r Q = v_i v_j sin th. Written as a plus it costs 38 MW of branch flow error and closes no network loop, and no self-consistency
            # check can see it: the envelope, the band and the gap all measure the model against its own definition of this relation.
            return (OptModel.vMPos[p,sc,n,ni,nf,cc] - OptModel.vMNeg[p,sc,n,ni,nf,cc]
                    == (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase)
        setattr(OptModel, f'eAngleEnvM_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvM, doc='signed parts of the envelope numerator [p.u.]'))

        # vMPos and vMNeg are only tied to their DIFFERENCE above, and adding the same amount to both relaxes BOTH envelope inequalities, because the two
        # appear with different voltage divisors. That is free slack — on a 0.95-1.05 band it comes to roughly 18% of the implied angle bound per branch,
        # which loosens how tightly the reported angles are tied to the flows. Capping the sum removes it without cutting anything off: the minimal split
        # (vMPos, vMNeg) = (max(M,0), max(-M,0)) always satisfies it, and the envelope is tightest at that split anyway.
        def eAngleEnvMSum(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vMPos[p,sc,n,ni,nf,cc] + OptModel.vMNeg[p,sc,n,ni,nf,cc]
                    <= _z(mTEPES, (ni,nf,cc)) * _smax_pu(mTEPES, (ni,nf,cc)))
        setattr(OptModel, f'eAngleEnvMSum_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvMSum, doc='minimal split of the envelope numerator [p.u.]'))

        # Both sides carry the same release, so a branch out of service imposes no angle relation on the two buses it would have joined. Releasing only
        # one side leaves the other binding on an unbuilt candidate, which is a quiet way to force a build.
        # vTheta is bounded at +/- pi/2, so the difference spans [-pi, pi] and a release of pi alone is not always enough: for a branch whose limits sit
        # on ONE side, say +5 to +30 degrees, eAngleBandLo would still read theta_ij >= 0.087 - pi, which is tighter than the variable range and so keeps
        # coupling two buses joined only by an unbuilt candidate. Adding the branch's own widest limit clears it in every case.
        pBandM = {la: math.pi + max(abs(mTEPES.pMaxAngleDiff[la]), abs(mTEPES.pMinAngleDiff[la])) for la in mTEPES.laa}

        def _pRelease(n, la):
            return pBandM[la] * (1 - OptModel.vLineCommit[(p,sc,n)+la])

        def eAngleEnvUp(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            # the polyhedral envelope is derived for a symmetric band, so it takes the wider of the two sides: a wider envelope is still a valid
            # relaxation, while the true asymmetric limits are imposed by eAngleBandUp/Lo below.
            t = max(mTEPES.pMaxAngleDiff[ni,nf,cc], -mTEPES.pMinAngleDiff[ni,nf,cc])
            return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                    <= ( OptModel.vMPos[p,sc,n,ni,nf,cc] / (_vlo_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMinBus[nf])
                       - OptModel.vMNeg[p,sc,n,ni,nf,cc] / (_vhi_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMaxBus[nf])) / math.cos(t/2)
                       + math.tan(t/2) - t/2 + _pRelease(n,(ni,nf,cc)))
        setattr(OptModel, f'eAngleEnvUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvUp, doc='upper envelope on the angle difference [rad]'))

        def eAngleEnvLo(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            # the polyhedral envelope is derived for a symmetric band, so it takes the wider of the two sides: a wider envelope is still a valid
            # relaxation, while the true asymmetric limits are imposed by eAngleBandUp/Lo below.
            t = max(mTEPES.pMaxAngleDiff[ni,nf,cc], -mTEPES.pMinAngleDiff[ni,nf,cc])
            return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                    >= ( OptModel.vMPos[p,sc,n,ni,nf,cc] / (_vhi_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMaxBus[nf])
                       - OptModel.vMNeg[p,sc,n,ni,nf,cc] / (_vlo_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMinBus[nf])) / math.cos(t/2)
                       - math.tan(t/2) + t/2 - _pRelease(n,(ni,nf,cc)))
        setattr(OptModel, f'eAngleEnvLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvLo, doc='lower envelope on the angle difference [rad]'))

        # Two one-sided constraints rather than one banded one. The release term carries vLineCommit, so a ranged inequality would have a VARIABLE bound
        # on each side, and Pyomo refuses to normalise that: 'Ranged Inequality with a variable lower bound'. Only a case with a candidate or switchable
        # AC branch reaches it, which is why the bundled cases did not show it.
        def eAngleBandUp(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                    <= mTEPES.pMaxAngleDiff[ni,nf,cc] + _pRelease(n,(ni,nf,cc)))
        setattr(OptModel, f'eAngleBandUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleBandUp, doc='tightened angle-difference band, upper [rad]'))

        def eAngleBandLo(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                    >= mTEPES.pMinAngleDiff[ni,nf,cc] - _pRelease(n,(ni,nf,cc)))
        setattr(OptModel, f'eAngleBandLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleBandLo, doc='tightened angle-difference band, lower [rad]'))

    # --- reactive capability ---------------------------------------------------------------------------------------------------------------------
    # A machine that is off supplies nothing, and one that is on supplies at most tan(acos(pf)) times its active output. Without this a unit that is
    # not running still delivers its full rated Mvar for free, which systematically understates how much compensation a system needs. Synchronous
    # condensers are excluded: reactive power at zero active power is their entire purpose, and vSynchInvest governs their availability.
    pTanInd    = math.tan(math.acos(min(max(mTEPES.pInductivePF(),  1e-3), 1.0)))
    pTanCap    = math.tan(math.acos(min(max(mTEPES.pCapacitivePF(), 1e-3), 1.0)))
    pCondenser = set(mTEPES.sq)

    def _pHasOutput(gq):
        return gq not in pCondenser and gq in mTEPES.g and (p, gq) in mTEPES.pg

    # A unit derated to nothing (EFOR = 1.0) has a non-zero NAMEPLATE rating, so it is not a reactive-only device and not in sq; and it has zero
    # available power, so it is not in g either. It therefore escapes both the capability constraints below and the condenser gate, and would deliver
    # its full rated Mvar at every load level for free. It cannot run, so it supplies nothing.
    pIdleReactive = [gq for gq in mTEPES.gq if gq not in pCondenser and gq not in mTEPES.g]

    def eReactiveIdle(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq:
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] == 0.0
    if pIdleReactive:
        setattr(OptModel, f'eReactiveIdle_{p}_{sc}_{st}',
                Constraint(mTEPES.n*pIdleReactive, rule=eReactiveIdle, doc='a unit with no available power supplies no reactive power [Gvar]'))

    def eReactiveCapabilityUp(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq or not _pHasOutput(gq):
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] <=  pTanInd * OptModel.vTotalOutput[p,sc,n,gq]
    setattr(OptModel, f'eReactiveCapabilityUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gq, rule=eReactiveCapabilityUp, doc='lagging power factor limit [Gvar]'))

    def eReactiveCapabilityLo(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq or not _pHasOutput(gq):
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] >= -pTanCap * OptModel.vTotalOutput[p,sc,n,gq]
    setattr(OptModel, f'eReactiveCapabilityLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gq, rule=eReactiveCapabilityLo, doc='leading power factor limit [Gvar]'))

    # --- (6a-c) shunt reactive injection ---------------------------------------------------------------------------------------------------------
    if mTEPES.sh:
        def _pShuntM(sh):
            return abs(mTEPES.pBusBshb[sh]()) * mTEPES.pVMaxBus[mTEPES.sh2n[sh]] ** 2 * pSBase

        # Devices split three ways. A fixed existing shunt is wired in and always injects, so it gets a plain equality. A switchable device has an
        # hourly on/off state and a candidate a per-period build decision; both are the SAME disjunction and differ only in which variable plays the
        # state, so they share one set of constraints. A device that is both is switched hourly and may only close in an hour once it has been built.
        pDisj = [sh for sh in mTEPES.sh if sh in mTEPES.shc or sh in mTEPES.shw]

        def _state(m, n, sh):
            return m.vShuntSwitch[p,sc,n,sh] if sh in mTEPES.shw else m.vShuntInvest[p,sh]

        def eShuntQExisting(OptModel, n, sh):
            if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she or sh in mTEPES.shw:
                return Constraint.Skip
            return OptModel.vQShunt[p,sc,n,sh] == mTEPES.pBusBshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
        setattr(OptModel, f'eShuntQExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntQExisting, doc='reactive injection of an existing shunt [Gvar]'))

        if pDisj:
            # A device in service injects Bshb*vW and out of service exactly nothing: two inequalities to pin it to the physics when in, two to force
            # it to zero when out. The device's own rating is the big-M, so the disjunction is as tight as the device.
            def _cand(rule_body, name, doc, pSub=None):
                pOn = pDisj if pSub is None else pSub
                def rule(OptModel, n, sh):
                    if (p,sc,n,sh) not in mTEPES.psnsh or sh not in pOn:
                        return Constraint.Skip
                    return rule_body(OptModel, n, sh)
                setattr(OptModel, f'{name}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=rule, doc=doc))

            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    <=  _pShuntM(sh) * (1 - _state(m, n, sh))), 'eShuntQCandUp', 'shunt injection when in service [Gvar]')
            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    >= -_pShuntM(sh) * (1 - _state(m, n, sh))), 'eShuntQCandLo', 'shunt injection when in service [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] <=  _pShuntM(sh) * _state(m, n, sh), 'eShuntQOffUp', 'a shunt out of service injects nothing [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] >= -_pShuntM(sh) * _state(m, n, sh), 'eShuntQOffLo', 'a shunt out of service injects nothing [Gvar]')

            # a candidate that is also switchable may only close in an hour if the investment was made
            pBoth = [sh for sh in mTEPES.shc if sh in mTEPES.shw]
            if pBoth:
                _cand(lambda m, n, sh: m.vShuntSwitch[p,sc,n,sh] <= m.vShuntInvest[p,sh], 'eShuntSwitchInvest',
                      'a switchable candidate shunt closes only once built [0,1]', pBoth)

        # Units of one bank are identical, so on their own the states would let branch and bound walk every permutation of the same answer: three
        # units of a four unit bank can be in service in four different ways that cost the same. Requiring a unit to follow the one before it leaves
        # exactly one of those, and turns the states of a bank into the count that are in service.
        if mTEPES.shp:
            def eShuntStepOrder(OptModel, n, sh, sn):
                if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.shw:
                    return Constraint.Skip
                return OptModel.vShuntSwitch[p,sc,n,sn] <= OptModel.vShuntSwitch[p,sc,n,sh]
            setattr(OptModel, f'eShuntStepOrder_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.shp, rule=eShuntStepOrder,
                    doc='a bank unit is in service only if the one before it is [0,1]'))

            # The same for the build decision, which has no hour index. It repeats identically for each scenario and stage; the rows are redundant
            # rather than wrong, and an AC case normally carries one of each.
            def eShuntBuildOrder(OptModel, sh, sn):
                if sh not in mTEPES.shc or (p,sh) not in mTEPES.pshc:
                    return Constraint.Skip
                return OptModel.vShuntInvest[p,sn] <= OptModel.vShuntInvest[p,sh]
            setattr(OptModel, f'eShuntBuildOrder_{p}_{sc}_{st}', Constraint(mTEPES.shp, rule=eShuntBuildOrder,
                    doc='a bank unit is built only if the one before it is [0,1]'))

        # the active side of the same device, present only when some shunt has a conductance
        if pShuntG:
            def _pShuntMG(sh):
                return abs(mTEPES.pBusGshb[sh]()) * mTEPES.pVMaxBus[mTEPES.sh2n[sh]] ** 2 * pSBase

            def eShuntPExisting(OptModel, n, sh):
                if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she or sh in mTEPES.shw:
                    return Constraint.Skip
                return OptModel.vPShunt[p,sc,n,sh] == -mTEPES.pBusGshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
            setattr(OptModel, f'eShuntPExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntPExisting, doc='active draw of an existing shunt [GW]'))

            if pDisj:
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        <=  _pShuntMG(sh) * (1 - _state(m, n, sh))), 'eShuntPCandUp', 'shunt draw when in service [GW]')
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        >= -_pShuntMG(sh) * (1 - _state(m, n, sh))), 'eShuntPCandLo', 'shunt draw when in service [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] <=  _pShuntMG(sh) * _state(m, n, sh), 'eShuntPOffUp', 'a shunt out of service draws nothing [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] >= -_pShuntMG(sh) * _state(m, n, sh), 'eShuntPOffLo', 'a shunt out of service draws nothing [GW]')

    # --- candidate synchronous condensers --------------------------------------------------------------------------------------------------------
    if mTEPES.sqc:
        def eSynchQOffUp(OptModel, n, sq):
            if (p,sq) not in mTEPES.psqc:
                return Constraint.Skip
            return OptModel.vReactiveTotalOutput[p,sc,n,sq] <= mTEPES.pMaxReactivePower[sq] * OptModel.vSynchInvest[p,sq]
        setattr(OptModel, f'eSynchQOffUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sqc, rule=eSynchQOffUp, doc='an unbuilt condenser injects nothing [Gvar]'))

        def eSynchQOffLo(OptModel, n, sq):
            if (p,sq) not in mTEPES.psqc:
                return Constraint.Skip
            return OptModel.vReactiveTotalOutput[p,sc,n,sq] >= mTEPES.pMinReactivePower[sq] * OptModel.vSynchInvest[p,sq]
        setattr(OptModel, f'eSynchQOffLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sqc, rule=eSynchQOffLo, doc='an unbuilt condenser absorbs nothing [Gvar]'))

    print('Generating AC network constraints      ... ', round(time.time() - StartTime), 's')


# ------------------------------------------------------------------------------------------------------------------------------------------------
# (13) the branch current: the only equation that differs between the AC formulations
# ------------------------------------------------------------------------------------------------------------------------------------------------

def NetworkACCurrentModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Supply ``vCurr = (P^2 + Q^2) / vW`` according to ``IndACModelType``.

      0  SOCP        ``vW_i * vCurr >= P^2 + Q^2``, a rotated second-order cone. The only variant whose objective is a valid bound on the true AC
                     optimum. Inside a MIP the cone is outer-approximated at nodes of the tree, which is what makes it scale worse than the linear
                     form as the horizon grows.
      1  piecewise   The square terms become a staircase of L segments, exact at the breakpoints and above the true square between them, so the
         linear      current is never under-estimated and the model is a RESTRICTION rather than a relaxation — a conservative, higher cost.
      2  exact NLP   The equation as written. Non-convex, so no mixed-integer solver takes it; for the validation pass with the binaries fixed.

    The staircase holds the voltage at nominal, because the exact equation divides by ``vW`` and that division is what makes the cone conic. Its range
    spans ``Smax*Vmax/Vmin``, matching what the other two admit: sizing it on ``Smax`` alone silently gives the piecewise variant a tighter feasible
    set than the formulation it approximates.
    """
    if mTEPES.pIndACPowerFlow() != 1:
        return

    pModelType = mTEPES.pIndACModelType()

    # Record which blocks carry a relaxed current definition. ACRestorationPass needs this and cannot recover it by pulling constraint names apart,
    # because a period label is free-form and may itself contain an underscore.
    if not hasattr(mTEPES, 'pACCurrentBlocks'):
        mTEPES.pACCurrentBlocks = []
    if (p, sc, st) not in mTEPES.pACCurrentBlocks:
        mTEPES.pACCurrentBlocks.append((p, sc, st))

    print(f'AC current definition   ({["SOCP", "piecewise linear", "exact NLP"][pModelType]}) ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    if pModelType == 0:
        def eCurrentSOC(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    <= OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentSOC_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentSOC, doc='rotated SOC relaxation of the branch current'))

    elif pModelType == 1:
        pSegments = RangeSet(1, PWL_SEGMENTS)
        setattr(OptModel, f'sACSeg_{p}_{sc}_{st}', pSegments)
        # divided by the tap factor so that PWL_SEGMENTS * pDelta reaches the same |P| the vFlowElec box allows, which carries the tap. Without
        # it a transformer with tap > 1 has a strictly smaller feasible set under IndACModelType 1 than under 0 and 2.
        pDelta = {la: _smax_pu(mTEPES, la) / mTEPES.pLineTapFactor[la] * pSBase / PWL_SEGMENTS for la in mTEPES.laa}

        vSegP = Var(mTEPES.n, mTEPES.laa, pSegments, within=NonNegativeReals, doc='active   power segment of the piecewise square [GW]'  )
        vSegQ = Var(mTEPES.n, mTEPES.laa, pSegments, within=NonNegativeReals, doc='reactive power segment of the piecewise square [Gvar]')
        vAbsP = Var(mTEPES.n, mTEPES.laa,            within=NonNegativeReals, doc='absolute active   power flow [GW]'  )
        vAbsQ = Var(mTEPES.n, mTEPES.laa,            within=NonNegativeReals, doc='absolute reactive power flow [Gvar]')
        for pName, pVar in (('vSegP',vSegP), ('vSegQ',vSegQ), ('vAbsP',vAbsP), ('vAbsQ',vAbsQ)):
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', pVar)
        for n in mTEPES.n:
            for la in mTEPES.laa:
                for k in pSegments:
                    vSegP[n, la, k].setub(pDelta[la])
                    vSegQ[n, la, k].setub(pDelta[la])

        # |P| >= P and |P| >= -P suffices: nothing rewards a larger |P|, because a larger |P| forces a larger vCurr and therefore a larger loss.
        def _abs_rule(pAbs, pFlow, pSign):
            def rule(OptModel, n, ni, nf, cc):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                return pAbs[n,ni,nf,cc] >= pSign * pFlow[p,sc,n,ni,nf,cc]
            return rule
        for pName, pAbs, pFlow, pSign in (('eAbsP1', vAbsP, OptModel.vFlowElec,      1), ('eAbsP2', vAbsP, OptModel.vFlowElec,     -1),
                                          ('eAbsQ1', vAbsQ, OptModel.vFlowReactFrw,  1), ('eAbsQ2', vAbsQ, OptModel.vFlowReactFrw, -1)):
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=_abs_rule(pAbs, pFlow, pSign), doc='absolute branch flow'))

        def eSegSumP(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return vAbsP[n,ni,nf,cc] == sum(vSegP[n,ni,nf,cc,k] for k in pSegments)
        setattr(OptModel, f'eSegSumP_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eSegSumP, doc='active flow split across the segments'))

        def eSegSumQ(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return vAbsQ[n,ni,nf,cc] == sum(vSegQ[n,ni,nf,cc,k] for k in pSegments)
        setattr(OptModel, f'eSegSumQ_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eSegSumQ, doc='reactive flow split across the segments'))

        def eCurrentPWL(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            # The staircase holds the voltage at nominal: the exact relation is P^2 + Q^2 = w * l * S^2, and this substitutes a constant reference
            # for the variable w. That reference is the TRANSFORMED nominal, (pVNom/tau)^2 — writing it as 1.0 is only correct when pVNom is 1.0 and
            # the branch has no tap, which is true of both bundled cases and of nothing else.
            pWRef = mTEPES.pVNom() ** 2 * _tap2(mTEPES, (ni,nf,cc))
            return (OptModel.vCurr[p,sc,n,ni,nf,cc] * pWRef * pSBase ** 2
                    >= sum((2*k - 1) * pDelta[ni,nf,cc] * (vSegP[n,ni,nf,cc,k] + vSegQ[n,ni,nf,cc,k]) for k in pSegments))
        setattr(OptModel, f'eCurrentPWL_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentPWL, doc='piecewise-linear branch current'))

    else:
        def eCurrentExact(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    == OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentExact_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentExact, doc='exact branch current definition'))

    print('Generating AC current definition       ... ', round(time.time() - StartTime), 's')


# Decisions held at their relaxed values through the restoration: the point of the pass is to recover the physical operating point behind a plan, not
# to let the plan move. Continuous operation — output, flows, voltages — stays free, because it has to absorb the true losses.
#
# The names are checked against the model at run time and a miss is reported. An earlier version listed 'vMaxCommitment', which is not a variable in
# this codebase at all (the real ones are vMaxCommitmentYearly, vMaxCommitmentConsYearly and vMaxCommitmentHourly), and getattr simply returned None,
# so the entry did nothing and said nothing. A stale name here means the plan quietly moves and the pass silently becomes a re-optimisation.
# Of the list below, only these exist on every model. The rest depend on options the case may not use, so their absence is not a defect.
RESTORE_ALWAYS = ('vCommitment', 'vStartUp', 'vShutDown')

RESTORE_FIXED = ('vCommitment', 'vCommitmentCons', 'vStartUp', 'vShutDown',
                 'vStableState', 'vRampUpState', 'vRampDwState',
                 'vMaxCommitmentYearly', 'vMaxCommitmentConsYearly', 'vMaxCommitmentHourly',
                 'vLineCommit', 'vLineOnState', 'vLineOffState',
                 'vGenerationInvest', 'vGenerationRetire', 'vNetworkInvest', 'vReservoirInvest',
                 'vShuntInvest', 'vSynchInvest', 'vH2PipeInvest', 'vHeatPipeInvest',
                 'vShuntSwitch')


def ACRestorationPass(OptModel, mTEPES, SolverName='ipopt', pIndLogConsole=0):
    """Re-solve a relaxed AC solution at the exact current equality, with the discrete decisions held fixed.

    The cone and the staircase both leave ``vCurr`` free above the value the flows imply. Where the cone is tight that costs nothing — measured on
    9n_AC the relaxed and exact optima agree to four decimal places. Where it is loose it costs a great deal: on a 24 hour RTS-GMLC window the
    relaxed total was 15.37 MEUR against 18.01 MEUR exact, so the relaxation understated the true cost by 14.7%.

    This pass keeps the plan and corrects the physics. Commitment, switching and every investment stay where the relaxed solve put them; the current
    definition becomes the equality; the network re-solves on a non-linear solver. The result is an operating point that satisfies the AC equations,
    and the difference between the two objectives is what the relaxation was hiding.

    Returns a dict of before/after figures, or None when there is nothing to do.
    """
    if mTEPES.pIndACPowerFlow() != 1:                          # it swaps the branch flow current and angle relations
        return None
    if mTEPES.pIndACModelType() == 2:
        print('AC restoration                         ...  skipped, the model already uses the exact current definition')
        return None

    pBlocks = getattr(mTEPES, 'pACCurrentBlocks', [])
    if not pBlocks:
        print('### WARNING: AC restoration found no current-definition blocks to restore; nothing was done.')
        return None

    StartTime = time.time()
    pSBase    = mTEPES.pSBase
    pBefore   = OptModel.vTotalSCost()

    # The stage loop deactivates each block's constraints once it has moved past them, so the whole model has to be live again before re-solving.
    # Only the blocks recorded above are touched: constraints deactivated for other reasons are left alone.
    nWoken = 0
    for p, sc, st in pBlocks:
        pSuffix = f'_{p}_{sc}_{st}'
        for c in OptModel.component_objects(Constraint):
            if c.name.endswith(pSuffix) and not c.active:
                c.activate()
                nWoken += 1

    # Hold the plan, in two passes.
    #
    # First by DOMAIN: ipopt cannot accept a discrete variable at all, so every binary or integer column is fixed whatever it is called. This is the
    # backstop that makes the pass safe against a variable being added or renamed later.
    nFixed = 0
    for vVar in OptModel.component_objects(Var, active=True):
        for idx in vVar:
            vData = vVar[idx]
            if vData.fixed or vData.value is None:
                continue
            if vData.is_binary() or vData.is_integer():
                vData.fix(vData.value)
                nFixed += 1

    # Then by NAME, for the decisions that must not move even when they have been relaxed to a continuous range: a relaxed commitment or investment
    # variable is not discrete, so the sweep above leaves it free, and the pass would re-optimise the plan instead of restoring it.
    # Most of these are declared conditionally -- a case with no hydrogen has no vH2PipeInvest, a case with no switching has no vLineOnState -- so
    # "absent" is normal and only vCommitment is present on every run. Warning about every optional name told the user the plan was free to move on
    # essentially every run, which was false and trained them to ignore the message.
    pMissing = []
    for pName in RESTORE_FIXED:
        vVar = getattr(OptModel, pName, None)
        if vVar is None:
            if pName in RESTORE_ALWAYS:
                pMissing.append(pName)
            continue
        for idx in vVar:
            if vVar[idx].value is not None and not vVar[idx].fixed:
                vVar[idx].fix(vVar[idx].value)
                nFixed += 1
    if pMissing:
        print(f'### WARNING: AC restoration expected to hold {pMissing} but no such variables exist on this model. If they were renamed, the plan is '
              f'free to move and this pass is re-optimising rather than restoring.')

    # Swap the relaxation for the equality, on the relaxed constraint's OWN index set so the two cover exactly the same branches and load levels.
    nRows = 0
    for p, sc, st in pBlocks:
        pRelaxed = None
        for pStem in ('eCurrentSOC', 'eCurrentPWL'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                pRelaxed = c
        if pRelaxed is None:
            continue
        # the staircase carries its own segment machinery, which has to go with it
        for pStem in ('eCurrentSOC', 'eCurrentPWL', 'eSegSumP', 'eSegSumQ'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                c.deactivate()

        pKeys = list(pRelaxed.keys())

        # The angle envelope has to go too, and this is the half that matters most.
        #
        # vTheta is a node potential, so the sum of (theta_i - theta_j) around any cycle is identically zero and a "cycle constraint" on it would say
        # nothing. What is loose is the tie between the angles and the FLOWS: the envelope only brackets it. Recovering each branch's angle from its
        # own flows and summing around the cycles of 9n_AC gave a mismatch of 0.634 degrees, which means no set of bus angles reproduces those flows —
        # the solution was not an AC operating point at all, however tight the cone was. Imposing the relation exactly closes the loops by
        # construction, because the angles are node potentials and now genuinely carry the flows.
        for pStem in ('eAngleEnvUp', 'eAngleEnvLo', 'eAngleEnvM', 'eAngleEnvMSum'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                c.deactivate()

        # An out-of-service branch must be released here exactly as eAngleEnvUp/Lo release it. Without that, a candidate inside its period window gets
        # a bare equality: eCurrentLimit drives its current to zero, hence P = Q = 0, and the equality then reads sin(theta_i - theta_j) = 0 and pins
        # two buses together through a line that was never built. Written as a pair of inequalities because the release carries vLineCommit and Pyomo
        # will not take a ranged inequality with a variable bound.
        # The band is recomputed here rather than borrowed: pBandM is a local of NetworkACOperationModelFormulation and is not in scope in this
        # function. Referencing it across the two was a NameError that only the restoration tests could see.
        pBandM = {la: math.pi + max(abs(mTEPES.pMaxAngleDiff[la]), abs(mTEPES.pMinAngleDiff[la])) for la in mTEPES.laa}

        def _pReleasedBand(OptModel, n, la):
            return pBandM[la] * (1 - OptModel.vLineCommit[(p,sc,n)+la])

        def eAngleRestoredUp(OptModel, n, ni, nf, cc, p=p, sc=sc):
            # |Vi/tau| |Vj| sin(theta_i - theta_j) = (x P - r Q) / S, the exact series relation. MINUS: see the derivation at eAngleEnvM. vW is bounded below by a positive number, so the
            # square roots are safe. eAngleBandUp/Lo stay active: they are valid bounds on the angle and they help the solver.
            return (sqrt(OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))) * sqrt(OptModel.vW[p,sc,n,nf])
                    * sin(OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf])
                    <= (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                      + _pReleasedBand(OptModel, n, (ni,nf,cc)))
        setattr(OptModel, f'eAngleRestoredUp_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eAngleRestoredUp, doc='exact angle-to-flow relation, upper, restoration pass'))

        def eAngleRestoredLo(OptModel, n, ni, nf, cc, p=p, sc=sc):
            return (sqrt(OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))) * sqrt(OptModel.vW[p,sc,n,nf])
                    * sin(OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf])
                    >= (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                      - _pReleasedBand(OptModel, n, (ni,nf,cc)))
        setattr(OptModel, f'eAngleRestoredLo_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eAngleRestoredLo, doc='exact angle-to-flow relation, lower, restoration pass'))

        def eCurrentRestored(OptModel, n, ni, nf, cc, p=p, sc=sc):
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    == OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentRestored_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eCurrentRestored, doc='exact branch current, restoration pass'))
        nRows += len(pKeys)

    if not nRows:
        print('### WARNING: AC restoration found no relaxed current constraints to replace; nothing was done.')
        return None

    # Exactly one objective may be active for the solve.
    pObjectives = [o for o in OptModel.component_objects(Objective) if o.active]
    if len(pObjectives) != 1:
        for o in pObjectives:
            o.deactivate()
        OptModel.eTotalSCost.activate()

    print(f'AC restoration                         ...  {nRows} branch-hours at the exact equality, {nFixed} decisions held, '
          f'{nWoken} constraints reactivated')

    Solver  = SolverFactory(SolverName)
    Results = Solver.solve(OptModel, tee=bool(pIndLogConsole))
    pStatus = str(Results.solver.termination_condition)

    if pStatus not in ('optimal', 'locallyOptimal', 'feasible'):
        print(f'### WARNING: the AC restoration did not converge ({pStatus}). The relaxed solution is unchanged in the results, and it is a LOWER '
              f'bound on the true cost, not the true cost.')
        return {'status': pStatus, 'before': pBefore, 'after': None, 'seconds': time.time() - StartTime}

    pAfter = OptModel.vTotalSCost()
    pGap   = 100.0 * (pAfter - pBefore) / abs(pAfter) if pAfter else 0.0

    # The duals in mTEPES.pDuals belong to the relaxed solve and describe a solution that no longer exists. Reporting them beside the restored primal
    # values would publish locational prices from one operating point and voltages, flows and costs from another, differing by exactly the amount this
    # pass just moved. Clearing them makes the marginal writers skip: OutputResultsEconomic guards on pHasDuals and ACMarginalResults on key presence,
    # so an absent price is reported as absent rather than as a wrong number.
    if getattr(mTEPES, 'pDuals', None):
        mTEPES.pDuals = {}
        print('AC restoration                         ...  marginal prices dropped: the duals were the relaxed solve\'s and do not describe the '
              'restored operating point. Re-run with IndACRestore = 0 if you need them.')
    print(f'AC restoration                         ...  {pStatus}, total cost {pBefore:.4f} -> {pAfter:.4f} MEUR '
          f'({pGap:+.2f}% the relaxation was understating), {round(time.time() - StartTime)} s')
    return {'status': pStatus, 'before': pBefore, 'after': pAfter, 'gap_percent': pGap, 'rows': nRows,
            'fixed': nFixed, 'seconds': time.time() - StartTime}
