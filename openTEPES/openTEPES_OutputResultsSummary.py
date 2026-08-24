"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 23, 2026

System summary, flexibility, and reliability results.

This module writes the headline system indicators: summary KPIs and levelized costs (OperationSummaryResults), flexibility measures by technology, storage,
demand, and network (FlexibilityResults), and the reliability indexes -- net demand, reserve margin, and largest unit (ReliabilityResults).
"""

import time
import os
import pandas            as     pd
from   collections       import defaultdict

try:
    from          .openTEPES_OutputResultsCommon import _outdir
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir


def OperationSummaryResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the generation operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # %%  Power balance per period, scenario, and load level
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

    # generators to nodes (g2n)
    g2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        g2n[nd].add(g)

    # generators to technology (g2t)
    g2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)

    pGen2Tech = {g: gt for gt in mTEPES.gt for g in g2t[gt]}

    # nodes that have at least one generator or one line: the guard only depends on the node, so evaluate it once here instead of once per (p,sc,n,nd) tuple
    pNodeConnected = {nd for nd in mTEPES.nd if g2n[nd] or lout[nd] or lin[nd]}

    # Ratio Fossil Fuel Generation/Total Generation [%]
    TotalGeneration       = sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng )
    FossilFuelGeneration  = sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psntr)
    # Ratio Total Investments [%]
    # vTotalFElecCost now also carries the AC reactive-compensation investments, so the gate has to admit a case whose only candidate is a shunt or a
    # synchronous condenser. Without this the reported total investment cost silently omits them.
    pElecInvest = len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) > 0 or (mTEPES.pIndACPowerFlow() and len(mTEPES.shc) + len(mTEPES.sqc) > 0)
    TotalInvestmentCost   = (sum(mTEPES.pDiscountedWeight[p] *                                       OptModel.vTotalFElecCost  [p   ]()     for p          in mTEPES.p if pElecInvest) +
                             sum(mTEPES.pDiscountedWeight[p] *                                       OptModel.vTotalFHydroCost [p   ]()     for p          in mTEPES.p if mTEPES.rn) +
                             sum(mTEPES.pDiscountedWeight[p] *                                       OptModel.vTotalFH2Cost    [p   ]()     for p          in mTEPES.p if mTEPES.pc) +
                             sum(mTEPES.pDiscountedWeight[p] *                                       OptModel.vTotalFHeatCost  [p   ]()     for p          in mTEPES.p if mTEPES.hc))
    GenInvestmentCost      = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]           * OptModel.vGenerationInvest[p,gc]()     for p,gc       in mTEPES.pgc)
    GenRetirementCost      = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenRetireCost[gd]           * OptModel.vGenerationRetire[p,gd]()     for p,gd       in mTEPES.pgd)
    if mTEPES.pIndHydroTopology():
        RsrInvestmentCost  = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pRsrInvestCost[rc]           * OptModel.vReservoirInvest [p,rc]()     for p,rc       in mTEPES.prc)
    else:
        RsrInvestmentCost  = 0.0
    if mTEPES.pIndHydrogen():
        H2InvestmentCost   = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pH2PipeFixedCost  [ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc]()   for p,ni,nf,cc in mTEPES.ppc)
    else:
        H2InvestmentCost  = 0.0
    if mTEPES.pIndHeat():
        HeatInvestmentCost = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.phc)
    else:
        HeatInvestmentCost  = 0.0
    NetInvestmentCost      = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pNetFixedCost [ni,nf,cc]     * OptModel.vNetworkInvest [p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc)
    if mTEPES.pIndACPowerFlow() and (mTEPES.shc or mTEPES.sqc):
        ReactiveInvestmentCost = (sum(mTEPES.pDiscountedWeight[p] * mTEPES.pShuntFixedCost[sh] * OptModel.vShuntInvest[p,sh]() for p,sh in mTEPES.pshc) +
                                  sum(mTEPES.pDiscountedWeight[p] * mTEPES.pSynchFixedCost[sq] * OptModel.vSynchInvest[p,sq]() for p,sq in mTEPES.psqc))
    else:
        ReactiveInvestmentCost = 0.0
    # Ratio Generation Investment cost/ Generation Installed Capacity [MEUR-MW]
    GenInvCostCapacity     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]()/mTEPES.pRatedMaxPowerElec[gc] for p,gc in mTEPES.pgc if mTEPES.pRatedMaxPowerElec[gc])
    # Ratio Additional Transmission Capacity-Length [MWkm]
    NetCapacityLength      = sum(mTEPES.pLineNTCMax[ni,nf,cc]*OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineLength[ni,nf,cc]()          for p,ni,nf,cc in mTEPES.plc)
    # Ratio Network Investment Cost/Variable RES Injection [EUR/MWh]
    VRESInjection = sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re) if mTEPES.gc else 0.0
    if VRESInjection:
        NetInvCostVRESInsCap = NetInvestmentCost*1e6/VRESInjection
    else:
        NetInvCostVRESInsCap = 0.0
    # Rate of return for VRE technologies
    # warning division and multiplication
    if hasattr(mTEPES, 'pDuals') and mTEPES.pDuals is not None and hasattr(mTEPES.pDuals, '__len__') and len(mTEPES.pDuals) > 0:
        # walk psnre directly instead of the s2n x n2g product: 'gc in g2n[nd]' discarded nothing there, because g2n is the inverse of n2g and every pair of the
        # product already satisfies it. The stage and the node come from two maps built once, so each renewable injection is visited exactly one time
        pLevelToStg    = {(p,sc,n): st for p,sc,st,n in mTEPES.s2n}
        pGen2Node      = {g: nd for nd,g in mTEPES.n2g}
        VRETechRevenue = sum(mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{pLevelToStg[p,sc,n]}('{n}', '{pGen2Node[gc]}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput[p,sc,n,gc]() for p,sc,n,gc in mTEPES.psnre if (p,sc,n) in pLevelToStg and gc in pGen2Node and pGen2Node[gc] in pNodeConnected)
    else:
        VRETechRevenue = 0.0
    VREInvCostCapacity = sum(mTEPES.pDiscountedWeight[p]*mTEPES.pGenInvestCost[gc]*OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.pgc if gc in mTEPES.re)

    K01     = pd.Series(data={'Ratio Fossil Fuel Generation/Total Generation [%]'                       : FossilFuelGeneration / TotalGeneration    *1e2}).to_frame(name='Value')
    if GenInvestmentCost:
        K02 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : GenInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K02 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    if GenRetirementCost:
        K03 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : GenRetirementCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K03 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    K05b = pd.DataFrame()
    if ReactiveInvestmentCost:
        K05b = pd.Series(data={'Ratio Reactive Compensation Investment Cost/Total Investment Cost [%]'    : ReactiveInvestmentCost / TotalInvestmentCost*1e2}).to_frame(name='Value')
    if NetInvestmentCost:
        K05 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : NetInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K05 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : 0.0                                           }).to_frame(name='Value')
    if RsrInvestmentCost:
        K04 = pd.Series(data={'Ratio Reservoir Investment Cost/Total Investment Cost [%]'               : RsrInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K04 = pd.Series(data={'Ratio Reservoir Investment Cost/Total Investment Cost [%]'               : 0.0                                           }).to_frame(name='Value')
    if H2InvestmentCost:
        K10 = pd.Series(data={'Ratio Hydrogen Investment Cost/Total Investment Cost [%]'               : H2InvestmentCost     / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K10 = pd.Series(data={'Ratio Hydrogen Investment Cost/Total Investment Cost [%]'               : 0.0                                           }).to_frame(name='Value')
    if HeatInvestmentCost:
        K11 = pd.Series(data={'Ratio Heat Investment Cost/Total Investment Cost [%]'                   : HeatInvestmentCost   / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K11 = pd.Series(data={'Ratio Heat Investment Cost/Total Investment Cost [%]'                   : 0.0                                           }).to_frame(name='Value')
    if GenInvCostCapacity:
        K06 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': GenInvCostCapacity   / 1e3                    }).to_frame(name='Value')
    else:
        K06 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': 0.0                                           }).to_frame(name='Value')
    if NetCapacityLength:
        K07 = pd.Series(data={'Ratio Additional Transmission Capacity * Line Length [MW-km]'            : NetCapacityLength    * 1e3                    }).to_frame(name='Value')
    else:
        K07 = pd.Series(data={'Ratio Additional Transmission Capacity * Line Length [MW-km]'            : 0.0                                           }).to_frame(name='Value')
    if NetInvCostVRESInsCap:
        K08 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : NetInvCostVRESInsCap * 1e3                    }).to_frame(name='Value')
    else:
        K08 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : 0.0                                           }).to_frame(name='Value')
    if VREInvCostCapacity:
        K09 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : VRETechRevenue       / VREInvCostCapacity*1e2 }).to_frame(name='Value')
    else:
        K09 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : 0.0                                           }).to_frame(name='Value')

    OutputResults = pd.concat([K01, K02, K03, K05, K05b, K04, K10, K11, K06, K07, K08, K09], axis=0)
    OutputResults.oT.write(f'{_path}/oT_Result_SummaryKPIs_{CaseName}.csv', sep=',', index=True)

    # LCOE per technology
    if mTEPES.gc:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]           * OptModel.vGenerationInvest[p,gc]() for p,     gc in mTEPES.pgc   if gc in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        pTechInjection    = defaultdict(float)
        for p,sc,n,gc in mTEPES.psngc:
            pTechInjection[pGen2Tech[gc]] += mTEPES.pDiscountedWeight[p] * mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutput[p,sc,n,gc]()
        GenTechInjection  = pd.Series(data=[pTechInjection[gt] for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh').rename_axis(['Technology'], axis=0).oT.write(f'{_path}/oT_Result_TechnologyLCOE_{CaseName}.csv', index=True, sep=',')

    # LCOH per technology
    if mTEPES.gb:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gb]           * OptModel.vGenerationInvest[p,gb]()     for p,     gb in mTEPES.pgb   if gb in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        pTechInjection    = defaultdict(float)
        for p,sc,n,gb in mTEPES.psngb:
            pTechInjection[pGen2Tech[gb]] += mTEPES.pDiscountedWeight[p] * mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutputHeat[p,sc,n,gb]()
        GenTechInjection  = pd.Series(data=[pTechInjection[gt] for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh').rename_axis(['Technology'], axis=0).oT.write(f'{_path}/oT_Result_TechnologyLCOH_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing           KPI summary results  ... ', round(WritingResultsTime), 's')
    #
    # StartTime = time.time()
    # t2g = pd.DataFrame(mTEPES.t2g).set_index(1)
    # n2g = pd.DataFrame(mTEPES.n2g).set_index(1)
    # z2g = pd.DataFrame(mTEPES.z2g).set_index(1)
    # a2g = pd.DataFrame(mTEPES.a2g).set_index(1)
    # r2g = pd.DataFrame(mTEPES.r2g).set_index(1)
    # OutputToFile01 = pd.Series(data=[t2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Technology'             )
    # OutputToFile02 = pd.Series(data=[n2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Node'                   )
    # OutputToFile03 = pd.Series(data=[z2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Zone'                   )
    # OutputToFile04 = pd.Series(data=[a2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Area'                   )
    # OutputToFile05 = pd.Series(data=[r2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Region'                 )
    # OutputToFile06 = pd.Series(data=[mTEPES.pLoadLevelDuration[p,sc,n  ]()                                                                                                    for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='LoadLevelDuration [h]'  )
    # OutputToFile07 = pd.Series(data=[OptModel.vCommitment     [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Commitment {0,1}'       )
    # OutputToFile08 = pd.Series(data=[OptModel.vStartUp        [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='StartUp {0,1}'          )
    # OutputToFile09 = pd.Series(data=[OptModel.vShutDown       [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ShutDown {0,1}'         )
    # OutputToFile10 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g].ub                                                                                                   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='MaxPower [MW]'          )
    # OutputToFile11 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g].lb                                                                                                   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='MinPower [MW]'          )
    # OutputToFile12 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='EnergyProduction [GWh]' )
    # OutputToFile13 = pd.Series(data=[OptModel.vESSTotalCharge [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                     if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='EnergyConsumption [GWh]')
    # OutputToFile14 = pd.Series(data=[OptModel.vEnergyOutflows [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                     if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Outflows [GWh]'         )
    # OutputToFile15 = pd.Series(data=[OptModel.vESSInventory   [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Inventory [GWh]'        )
    # OutputToFile16 = pd.Series(data=[OptModel.vESSSpillage    [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Spillage [GWh]'         )
    # OutputToFile17 = pd.Series(data=[(OptModel.vTotalOutput   [p,sc,n,g].ub-OptModel.vTotalOutput[p,sc,n,g]())*mTEPES.pLoadLevelDuration[p,sc,n]() if g in mTEPES.re else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Curtailment [GWh]'      )
    # OutputToFile18 = pd.Series(data=[OptModel.vReserveUp      [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveUpGen [MW]'      )
    # OutputToFile19 = pd.Series(data=[OptModel.vReserveDown    [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveDownGen [MW]'    )
    # OutputToFile20 = pd.Series(data=[OptModel.vESSReserveUp   [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveUpCons [MW]'     )
    # OutputToFile21 = pd.Series(data=[OptModel.vESSReserveDown [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveDownCons [MW]'   )
    # OutputToFile22 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]             if g not in mTEPES.bo
    #                            else OptModel.vTotalOutputHeat [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]                                        for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Emissions [MtCO2]'      )
    #
    # OutputToFile10 *= 1e3
    # OutputToFile11 *= 1e3
    # OutputToFile18 *= 1e3
    # OutputToFile19 *= 1e3
    # OutputToFile20 *= 1e3
    # OutputToFile21 *= 1e3
    # OutputToFile22 *= 1e-3
    #
    # OutputResults   = pd.concat([OutputToFile01, OutputToFile02, OutputToFile03, OutputToFile04, OutputToFile05, OutputToFile06, OutputToFile07, OutputToFile08, OutputToFile09, OutputToFile10,
    #                                   OutputToFile11, OutputToFile12, OutputToFile13, OutputToFile14, OutputToFile15, OutputToFile16, OutputToFile17, OutputToFile18, OutputToFile19, OutputToFile20,
    #                                   OutputToFile21, OutputToFile22], axis=1)
    # # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Generator'], axis=0).to_csv    (f'{_path}/oT_Result_SummaryGeneration_{CaseName}.csv',     sep=',')
    # # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Generator'], axis=0).to_parquet(f'{_path}/oT_Result_SummaryGeneration_{CaseName}.parquet', engine='pyarrow')
    #
    # WritingResultsTime = time.time() - StartTime
    # StartTime = time.time()
    # print('Writing    generation summary results  ... ', round(WritingResultsTime), 's')

    ndzn = pd.DataFrame(mTEPES.ndzn).set_index(0)
    ndar = pd.DataFrame(mTEPES.ndar).set_index(0)
    # comprehensions, NOT dict(mTEPES.ndzn): dict() on a Pyomo scalar Set goes through the component API and yields {None: <the Set>}, never the elements
    pNode2Zone         = {nd: zn for nd,zn in mTEPES.ndzn}
    pNode2Area         = {nd: ar for nd,ar in mTEPES.ndar}
    sPSNND             = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if nd in pNodeConnected]
    OutputResults1     = pd.Series(data=[ ndzn[1][nd]                                                                                                                           for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Zone'               )
    OutputResults2     = pd.Series(data=[ ndar[1][nd]                                                                                                                           for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Area'               )
    OutputResults3     = pd.Series(data=[     OptModel.vENS       [p,sc,n,nd      ]()                                                      *mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='ENS [GWh]'          )
    OutputResults4     = pd.Series(data=[-  mTEPES.pDemandElec    [p,sc,n,nd      ]()                                                        *mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerDemand [GWh]'  )
    OutputResults5     = pd.Series(data=[-sum(OptModel.vFlowElec  [p,sc,n,nd,nf,cc]() for nf,cc in lout [nd] if (p,nd,nf,cc) in mTEPES.pla)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowOut [GWh]' )
    # Under DC the flow variable is lossless, so the power leaving ni and the power arriving at nd are the same number and the sending-end value is the
    # only one available. Under AC they differ by the branch loss, and the arriving power is the negative of what leaves nd into the branch, which the
    # model carries exactly as vFlowElecBck. Using the sending-end value there would overstate every node's inflow by its share of the losses.
    if mTEPES.pIndACPowerFlow():
        # AC branches use the receiving end; HVDC links have no vFlowElecBck and enter the AC balance with the sending-end flow exactly as they
        # do under DC, so they need their own term or a node fed by HVDC reports no inflow at all.
        OutputResults6 = pd.Series(data=[(-sum(OptModel.vFlowElecBck[p,sc,n,ni,nd,cc]() for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.pla and (ni,nd,cc) in mTEPES.laa)
                                          +sum(OptModel.vFlowElec   [p,sc,n,ni,nd,cc]() for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.pla and (ni,nd,cc) in mTEPES.lad))*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowIn [GWh]'  )
    else:
        OutputResults6 = pd.Series(data=[ sum(OptModel.vFlowElec  [p,sc,n,ni,nd,cc]() for ni,cc in lin  [nd] if (p,ni,nd,cc) in mTEPES.pla)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowIn [GWh]'  )
    if mTEPES.ll:
        # under AC the loss is inside the flows already, so only DC branches contribute here
        _lossOK = (lambda la: la in mTEPES.lad) if mTEPES.pIndACPowerFlow() else (lambda la: True)
        OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,nd,nf,cc]() for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pll and _lossOK((nd,nf,cc)))*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesOut [GWh]')
        OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc]() for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pll and _lossOK((ni,nd,cc)))*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesIn [GWh]' )

        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    else:
        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6                                ], axis=1)

    # eBalanceElecAC carries the active draw of a conducting shunt, so this frame needs it too or its rows sum to that draw instead of to zero. The
    # variable exists only when some device has a non-zero Gshb.
    if mTEPES.pIndACPowerFlow() and hasattr(OptModel, 'vPShunt'):
        pShuntAt = defaultdict(list)
        for nd, sh in mTEPES.n2sh:
            pShuntAt[nd].append(sh)
        OutputResults9 = pd.Series(data=[sum(OptModel.vPShunt[p,sc,n,sh]() for sh in pShuntAt[nd] if (p,sc,n,sh) in mTEPES.psnsh)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='ShuntDraw [GWh]')
        OutputResults  = pd.concat([OutputResults, OutputResults9], axis=1)

    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Node'], axis=0).to_csv    (f'{_path}/oT_Result_SummaryNetwork_{CaseName}.csv',     sep=',')
    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Node'], axis=0).to_parquet(f'{_path}/oT_Result_SummaryNetwork_{CaseName}.parquet', engine='pyarrow')

    WritingResultsTime = time.time() - StartTime
    print('Writing elect network summary results  ... ', round(WritingResultsTime), 's')


# @profile
def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # generators to technology (o2e)
    o2e = defaultdict(set)
    e2e = defaultdict(set)
    g2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)
        if g in mTEPES.es:
            o2e[gt].add(g)
        if g in mTEPES.eh:
            e2e[gt].add(g)

    # nodes to area (d2a)
    d2a = defaultdict(set)
    for nd,ar in mTEPES.ndar:
        d2a[ar].add(nd)

    OutputToFile         = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
    OutputToFile *= 1e3
    # the mean per technology needs no pivot table: grouping by the technology level gives the same values. The .to_numpy() below is required -- without it pandas
    # aligns on a non-unique index and raises NotImplementedError, so the subtraction must be positional against the technology of each row
    MeanTechnologyOutput = OutputToFile.groupby(level=3).mean()
    NetTechnologyOutput  = OutputToFile - MeanTechnologyOutput.reindex(OutputToFile.index.get_level_values(3)).to_numpy()
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityTechnology_{CaseName}.csv', sep=',')

    if mTEPES.es:
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,es]() for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile *= 1e3
        # same rewrite as above, keeping the sign convention: here the mean is negated and added instead of subtracted
        MeanESSTechnologyOutput = -OutputToFile.groupby(level=3).mean()
        NetESSTechnologyOutput  =  OutputToFile + MeanESSTechnologyOutput.reindex(OutputToFile.index.get_level_values(3)).to_numpy()
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityTechnologyESS_{CaseName}.csv', sep=',')

    # build the per-area series once and subtract its own mean per area; computing the inner sum twice (once for the mean, once for the value) doubled the cost
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemandElec[p,sc,n,nd]() for nd in d2a[ar])                  for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile = OutputToFile - OutputToFile.groupby(level=3).transform('mean')
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityDemand_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in d2a[ar])               for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile = OutputToFile - OutputToFile.groupby(level=3).transform('mean')
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityPNS_{CaseName}.csv', sep=',')

    # laar is built requiring both line ends to be in the area, so 'nd in d2a[ar]' and 'nf in d2a[af]' are implied by 'af == ar' and only cost a set lookup each
    OutputToFile = pd.Series(data=[sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc]() for nd,nf,cc,af in mTEPES.laar if af == ar and (p,nd,nf,cc) in mTEPES.pla)                for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile = OutputToFile - OutputToFile.groupby(level=3).transform('mean')
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityNetwork_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing           flexibility results  ... ', round(WritingResultsTime), 's')


# @profile
def ReliabilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the reliability indexes
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # Ensure tuple-like indexes are promoted to MultiIndex before groupby(level=...).
    def _ensure_multiindex(series, names):
        if isinstance(series.index, pd.MultiIndex):
            return series
        if len(series.index) == 0:
            series.index = pd.MultiIndex.from_tuples([], names=names)
            return series
        if len(series.index) > 0 and isinstance(series.index[0], tuple):
            series.index = pd.MultiIndex.from_tuples(series.index, names=names)
        return series

    r2r = defaultdict(set)
    for gt,g in mTEPES.t2g:
        if g in mTEPES.re:
            r2r[gt].add(g)

    pDemandElec    = pd.Series(data=[mTEPES.pDemandElec[p,sc,n,nd]() for p,sc,n,nd in mTEPES.psnnd ], index=mTEPES.psnnd).sort_index()
    pDemandElec    = _ensure_multiindex(pDemandElec, ['Period', 'Scenario', 'LoadLevel', 'Node'])
    ExistCapacity  = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if g not in mTEPES.gc]
    pExistMaxPower = pd.Series(data=[mTEPES.pMaxPowerElec[p,sc,n,g ] for p,sc,n,g  in ExistCapacity], index=pd.Index(ExistCapacity))
    pExistMaxPower = _ensure_multiindex(pExistMaxPower, ['Period', 'Scenario', 'LoadLevel', 'Generator'])
    if mTEPES.gc:
        CandCapacity  = [(p,sc,n,gc) for p,sc,n,gc in mTEPES.psngc]
        pCandMaxPower = pd.Series(data=[mTEPES.pMaxPowerElec[p,sc,n,g ] * OptModel.vGenerationInvest[p,g]() for p,sc,n,g in CandCapacity], index=pd.Index(CandCapacity))
        pCandMaxPower = _ensure_multiindex(pCandMaxPower, ['Period', 'Scenario', 'LoadLevel', 'Generator'])
        pMaxPowerElec = pd.concat([pExistMaxPower, pCandMaxPower])
    else:
        pMaxPowerElec = pExistMaxPower
    pMaxPowerElec = pMaxPowerElec.sort_index()

    # Determination of the net demand
    if mTEPES.re:
        pGen2Node = {g: nd for nd,g in mTEPES.n2g}
        pNode2Res = defaultdict(list)
        for rt in mTEPES.rt:
            for re in r2r[rt]:
                if re in pGen2Node:
                    pNode2Res[pGen2Node[re]].append(re)
        OutputToFile1 = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,re]() for re in pNode2Res[nd] if (p,re) in mTEPES.pre) for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    else:
        OutputToFile1 = pd.Series(data=[0.0                                                                                                                             for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile2     = pd.Series(data=[      mTEPES.pDemandElec [p,sc,n,nd]()                                                                                            for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile  = OutputToFile2 - OutputToFile1
    OutputToFile  *= 1e3
    OutputToFile  = OutputToFile.to_frame(name='MW')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetDemandNetwork_{CaseName}.csv', sep=',')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'],                    values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetDemand_{CaseName}.csv', sep=',')

    # Determination of the index: Reserve Margin
    # peak of the per-load-level total: sum over generators (nodes) within each load level, then take the maximum load level of each period and scenario
    OutputToFile1 = pMaxPowerElec.groupby(level=[0,1,2]).sum().groupby(level=[0,1]).max()
    OutputToFile2 = pDemandElec.groupby  (level=[0,1,2]).sum().groupby(level=[0,1]).max()
    ReserveMargin1 =  OutputToFile1 - OutputToFile2
    ReserveMargin2 = (OutputToFile1 - OutputToFile2)/OutputToFile2
    ReserveMargin1.to_frame(name='MW'  ).rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_ReserveMargin_{CaseName}.csv',        sep=',')
    ReserveMargin2.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_ReserveMarginPerUnit_{CaseName}.csv', sep=',')

    # Determination of the index: Largest Unit
    # the largest unit is the plain maximum: taking the maximum per generator first and then the maximum over generators gave the same value
    OutputToFile = pMaxPowerElec.groupby(level=[0,1]).max()

    LargestUnit  = ReserveMargin1/OutputToFile
    LargestUnit.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_LargestUnitPerUnit_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing           reliability indexes  ... ', round(WritingResultsTime), 's')

