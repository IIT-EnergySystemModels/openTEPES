"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 04, 2026

openTEPES.openTEPES_ModelFormulationHydrogen — hydrogen network operation: H2 balance and hydrogen-not-served cost.
"""
from __future__ import annotations

import time
from collections import defaultdict
from pyomo.environ import Constraint


def NetworkH2OperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Hydrogen  scheduling       constraints ****')

    StartTime = time.time()

    # incoming and outgoing pipelines (lin) (lout)
    lin  = defaultdict(set)
    lout = defaultdict(set)
    for ni,nf,cc in mTEPES.pa:
        lin [nf].add((ni,cc))
        lout[ni].add((nf,cc))

    # nodes to electrolyzers (l2n)
    l2n = defaultdict(set)
    # nodes to fuel heaters using H2 (b2n)
    b2n = defaultdict(set)
    # nodes to hydrogen-fired generators (g2n)
    g2n = defaultdict(set)
    # nodes to hydrogen stores (s2nd), from n2hs: a cavern is not in the generating set
    s2nd = defaultdict(set)
    for nd,hs in mTEPES.n2hs:
        s2nd[nd].add(hs)
    # nodes to hydrogen sources (r2n): reformers and imports, from n2sr
    r2n = defaultdict(set)
    for nd,sr in mTEPES.n2sr:
        r2n[nd].add(sr)
    for nd,g in mTEPES.n2g:
        if g in mTEPES.el:
            l2n[nd].add(g)
        if g in mTEPES.hh:
            b2n[nd].add(g)
        if g in mTEPES.h2p:
            g2n[nd].add(g)


    def eBalanceH2(OptModel,n,nd):
        if len(l2n[nd]) + len(b2n[nd]) + len(g2n[nd]) + len(s2nd[nd]) + len(r2n[nd]) + len(lout[nd]) + len(lin[nd]) == 0:
            return Constraint.Skip
        return (sum(OptModel.vH2Production[p,sc,n,sr] for sr in r2n[nd]) + mTEPES.pDuration[p,sc,n]()*sum(OptModel.vESSTotalCharge[p,sc,n,el]/mTEPES.pProductionFunctionH2[el] for el in l2n[nd] if (p,el) in mTEPES.peh) - mTEPES.pDuration[p,sc,n]()*sum(OptModel.vTotalOutputHeat[p,sc,n,hh]*mTEPES.pProductionFunctionH2ToHeat[hh] for hh in b2n[nd] if (p,hh) in mTEPES.phh) - mTEPES.pDuration[p,sc,n]()*sum(OptModel.vTotalOutput[p,sc,n,h2p]*mTEPES.pProductionFunctionH2ToPower[h2p] for h2p in g2n[nd] if (p,h2p) in mTEPES.pg) - sum(OptModel.vH2StorCharge[p,sc,n,hs] - OptModel.vH2StorDischarge[p,sc,n,hs] for hs in s2nd[nd]) + OptModel.vH2NS[p,sc,n,nd] - OptModel.vH2Exc[p,sc,n,nd] -
                sum(OptModel.vFlowH2[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.ppa) + sum(OptModel.vFlowH2[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.ppa)) == mTEPES.pDemandH2[p,sc,n,nd]*mTEPES.pDuration[p,sc,n]()
    setattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceH2, doc='H2 load generation balance [tH2]'))

    if pIndLogConsole:
        print('eBalanceH2                ... ', len(getattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}')), ' rows')

    # hydrogen inventory over each storage cycle, as eESSInventory does for electricity
    n2list_h2 = list(mTEPES.n2)

    def eH2Inventory(OptModel,n,hs):
        step = mTEPES.pStorageTimeStepH2[hs]
        if mTEPES.n.ord(n) % step != 0:
            return Constraint.Skip
        window = n2list_h2[mTEPES.n.ord(n)-step:mTEPES.n.ord(n)]
        net = sum(OptModel.vH2StorCharge[p,sc,n2,hs] - OptModel.vH2StorDischarge[p,sc,n2,hs] for n2 in window)
        if   mTEPES.n.ord(n) == step:
            return mTEPES.pIniStorageH2[hs] + net == OptModel.vH2Inventory[p,sc,n,hs]
        elif mTEPES.n.ord(n) >  step:
            return OptModel.vH2Inventory[p,sc,mTEPES.n.prev(n,step),hs] + net == OptModel.vH2Inventory[p,sc,n,hs]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eH2Inventory_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.hs, rule=eH2Inventory, doc='hydrogen inventory balance [tH2]'))

    if pIndLogConsole:
        print('eH2Inventory              ... ', len(getattr(OptModel, f'eH2Inventory_{p}_{sc}_{st}')), ' rows')

    # the cavern ends the horizon at its initial inventory, as eIniFinInventory does
    def eH2IniFinInventory(OptModel,hs):
        return OptModel.vH2Inventory[p,sc,mTEPES.n.last(),hs] == mTEPES.pIniStorageH2[hs]
    setattr(OptModel, f'eH2IniFinInventory_{p}_{sc}_{st}', Constraint(mTEPES.hs, rule=eH2IniFinInventory, doc='hydrogen inventory returns to its starting level [tH2]'))

    if pIndLogConsole:
        print('eH2IniFinInventory        ... ', len(getattr(OptModel, f'eH2IniFinInventory_{p}_{sc}_{st}')), ' rows')

    def eTotalH2SrcCost(OptModel,n):
        # pProductionCostH2 carries fuel, O&M and carbon; vH2Production is already tonnes
        return OptModel.vTotalH2SrcCost[p,sc,n] == sum(mTEPES.pProductionCostH2[sr] * OptModel.vH2Production[p,sc,n,sr] for sr in mTEPES.sr)
    setattr(OptModel, f'eTotalH2SrcCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalH2SrcCost, doc='hydrogen source cost [MEUR]'))

    def eTotalRH2Cost(OptModel,n):
        # guard matches eBalanceH2: a node outside this sum carries a cost-free unserved variable.
        # Stage weight alone, not pLoadLevelDuration: vH2NS is tonnes over the load level, not a
        # rate, so the duration is already in it. The electricity term needs both, vENS being a power
        return OptModel.vTotalRH2Cost[p,sc,n] == mTEPES.pLoadLevelWeight[p,sc,n]() * sum(mTEPES.pH2NSCost * OptModel.vH2NS[p,sc,n,nd] + mTEPES.pH2ExcCost * OptModel.vH2Exc[p,sc,n,nd] for nd in mTEPES.nd if len(l2n[nd]) + len(b2n[nd]) + len(g2n[nd]) + len(s2nd[nd]) + len(r2n[nd]) + len(lout[nd]) + len(lin[nd]))
    setattr(OptModel, f'eTotalRH2Cost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRH2Cost, doc='H2 system reliability cost [MEUR]'))

    if pIndLogConsole:
        print('eTotalRH2Cost             ... ', len(getattr(OptModel, f'eTotalRH2Cost_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating hydrogen  operation         ... ', round(GeneratingTime), 's')
