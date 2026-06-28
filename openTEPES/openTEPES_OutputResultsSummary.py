"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 11, 2026

System summary, flexibility, and reliability results.

This module writes the headline system indicators: summary KPIs and levelized
costs (OperationSummaryResults), flexibility measures by technology, storage,
demand, and network (FlexibilityResults), and the reliability indexes -- net
demand, reserve margin, and largest unit (ReliabilityResults).
"""

import time
import os
import pandas            as     pd
from   collections       import defaultdict

try:
    from .openTEPES_OutputResultsCommon import _outdir
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
    lin   = defaultdict(list)
    linl  = defaultdict(list)
    lout  = defaultdict(list)
    loutl = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin  [nf].append((ni,cc))
        lout [ni].append((nf,cc))
    for ni,nf,cc in mTEPES.ll:
        linl [nf].append((ni,cc))
        loutl[ni].append((nf,cc))

    # generators to nodes (g2n)
    g2n = defaultdict(list)
    for nd,g in mTEPES.n2g:
        g2n[nd].append(g)

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    # Ratio Fossil Fuel Generation/Total Generation [%]
    TotalGeneration       = sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng )
    FossilFuelGeneration  = sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psntr)
    # Ratio Total Investments [%]
    TotalInvestmentCost  = (sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFElecCost  [p   ]()          for p          in mTEPES.p if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc)) +
                            sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFHydroCost [p   ]()          for p          in mTEPES.p if mTEPES.rn) +
                            sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFH2Cost    [p   ]()          for p          in mTEPES.p if mTEPES.pc) +
                            sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFHeatCost  [p   ]()          for p          in mTEPES.p if mTEPES.hc))
    GenInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]       * OptModel.vGenerationInvest[p,gc]()          for p,gc       in mTEPES.pgc)
    GenRetirementCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenRetireCost[gd]       * OptModel.vGenerationRetire[p,gd]()          for p,gd       in mTEPES.pgd)
    if mTEPES.pIndHydroTopology:
        RsrInvestmentCost = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pRsrInvestCost[rc]       * OptModel.vReservoirInvest [p,rc]()          for p,rc       in mTEPES.prc)
    else:
        RsrInvestmentCost = 0.0
    if mTEPES.pIndHydrogen:
        H2InvestmentCost  = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc]()      for p,ni,nf,cc in mTEPES.ppc)
    else:
        H2InvestmentCost  = 0.0
    if mTEPES.pIndHeat:
        HeatInvestmentCost = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.phc)
    else:
        HeatInvestmentCost  = 0.0
    NetInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pNetFixedCost [ni,nf,cc] * OptModel.vNetworkInvest   [p,ni,nf,cc]()    for p,ni,nf,cc in mTEPES.plc)
    # Ratio Generation Investment cost/ Generation Installed Capacity [MEUR-MW]
    GenInvCostCapacity    = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]()/mTEPES.pRatedMaxPowerElec[gc] for p,gc in mTEPES.pgc if mTEPES.pRatedMaxPowerElec[gc])
    # Ratio Additional Transmission Capacity-Length [MWkm]
    NetCapacityLength     = sum(mTEPES.pLineNTCMax[ni,nf,cc]*OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineLength[ni,nf,cc]()           for p,ni,nf,cc in mTEPES.plc)
    # Ratio Network Investment Cost/Variable RES Injection [EUR/MWh]
    if mTEPES.gc and sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re):
        NetInvCostVRESInsCap = NetInvestmentCost*1e6/sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re)
    else:
        NetInvCostVRESInsCap = 0.0
    # Rate of return for VRE technologies
    # warning division and multiplication
    VRETechRevenue     = sum(mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput[p,sc,n,gc]() for p,sc,st,n,nd,gc in mTEPES.s2n*mTEPES.n2g if gc in g2n[nd] and (p,sc,n,gc) in mTEPES.psnre and sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
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

    OutputResults = pd.concat([K01, K02, K03, K05, K04, K10, K11, K06, K07, K08, K09], axis=0)
    OutputResults.oT.write(f'{_path}/oT_Result_SummaryKPIs_{CaseName}.csv', sep=',', index=True)

    # LCOE per technology
    if mTEPES.gc:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]           * OptModel.vGenerationInvest[p,gc]() for p,     gc in mTEPES.pgc   if gc in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection  = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutput[p,sc,n,gc]() for p,sc,n,gc in mTEPES.psngc if gc in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        LCOE = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh').rename_axis(['Technology'], axis=0).oT.write(f'{_path}/oT_Result_TechnologyLCOE_{CaseName}.csv', index=True, sep=',')

    # LCOH per technology
    if mTEPES.gb:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gb]           * OptModel.vGenerationInvest[p,gb]()     for p,     gb in mTEPES.pgb   if gb in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection  = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutputHeat[p,sc,n,gb]() for p,sc,n,gb in mTEPES.psngb if gb in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        LCOH = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh').rename_axis(['Technology'], axis=0).oT.write(f'{_path}/oT_Result_TechnologyLCOH_{CaseName}.csv', index=True, sep=',')

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
    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputResults1     = pd.Series(data=[ ndzn[1][nd]                                                                                                                           for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Zone'               )
    OutputResults2     = pd.Series(data=[ ndar[1][nd]                                                                                                                           for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Area'               )
    OutputResults3     = pd.Series(data=[     OptModel.vENS       [p,sc,n,nd      ]()                                                      *mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='ENS [GWh]'          )
    OutputResults4     = pd.Series(data=[-  mTEPES.pDemandElec    [p,sc,n,nd      ]()                                                        *mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerDemand [GWh]'  )
    OutputResults5     = pd.Series(data=[-sum(OptModel.vFlowElec  [p,sc,n,nd,nf,cc]() for nf,cc in lout [nd] if (p,nd,nf,cc) in mTEPES.pla)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowOut [GWh]' )
    OutputResults6     = pd.Series(data=[ sum(OptModel.vFlowElec  [p,sc,n,ni,nd,cc]() for ni,cc in lin  [nd] if (p,ni,nd,cc) in mTEPES.pla)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowIn [GWh]'  )
    if mTEPES.ll:
        OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,nd,nf,cc]() for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pll)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesOut [GWh]')
        OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc]() for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pll)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesIn [GWh]' )

        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    else:
        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6                                ], axis=1)

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
    o2e = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            o2e[ot].append(es)
    e2e = defaultdict(list)
    for et,eh in mTEPES.et*mTEPES.eh:
        if (et,eh) in mTEPES.t2g:
            e2e[et].append(eh)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    # nodes to area (d2a)
    d2a = defaultdict(list)
    for ar,nd in mTEPES.ar*mTEPES.nd:
        if (nd,ar) in mTEPES.ndar:
            d2a[ar].append(nd)

    OutputToFile         = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
    OutputToFile *= 1e3
    TechnologyOutput     = OutputToFile.loc[:,:,:,:]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput  = pd.Series([0.0] * len(mTEPES.psngt), index=mTEPES.psngt)
    for p,sc,n,gt in mTEPES.psngt:
        NetTechnologyOutput[p,sc,n,gt] = TechnologyOutput[p,sc,n,gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityTechnology_{CaseName}.csv', sep=',')

    if mTEPES.es:
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,es]() for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile *= 1e3
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput  = pd.Series([0.0] * len(mTEPES.psnot), index=mTEPES.psnot)
        for p,sc,n,ot in mTEPES.psnot:
            NetESSTechnologyOutput[p,sc,n,ot] = MeanESSTechnologyOutput[ot] - ESSTechnologyOutput[p,sc,n,ot]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityTechnologyESS_{CaseName}.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemandElec[p,sc,n,nd]() for nd in d2a[ar])                  for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemandElec[p,sc,n,nd]() for nd in d2a[ar]) - MeanDemand[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityDemand_{CaseName}.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in d2a[ar])               for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in d2a[ar]) - MeanENS[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_FlexibilityPNS_{CaseName}.csv', sep=',')

    MeanFlow     = pd.Series(data=[sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc]() for nd,nf,cc,af in mTEPES.laar if nd in d2a[ar] and nf in d2a[af] and af != ar and (p,nd,nf,cc) in mTEPES.pla)                for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc]() for nd,nf,cc,af in mTEPES.laar if nd in d2a[ar] and nf in d2a[af] and af != ar and (p,nd,nf,cc) in mTEPES.pla) - MeanFlow[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
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

    r2r = defaultdict(list)
    for rt,re in mTEPES.rt*mTEPES.re:
        if (rt,re) in mTEPES.t2g:
            r2r[rt].append(re)

    pDemandElec    = pd.Series(data=[mTEPES.pDemandElec[p,sc,n,nd]() for p,sc,n,nd in mTEPES.psnnd ], index=mTEPES.psnnd).sort_index()
    ExistCapacity  = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if g not in mTEPES.gc]
    pExistMaxPower = pd.Series(data=[mTEPES.pMaxPowerElec[p,sc,n,g ] for p,sc,n,g  in ExistCapacity], index=pd.Index(ExistCapacity))
    if mTEPES.gc:
        CandCapacity  = [(p,sc,n,gc) for p,sc,n,gc in mTEPES.psngc]
        pCandMaxPower = pd.Series(data=[mTEPES.pMaxPowerElec[p,sc,n,g ] * OptModel.vGenerationInvest[p,g]() for p,sc,n,g in CandCapacity], index=pd.Index(CandCapacity))
        pMaxPowerElec = pd.concat([pExistMaxPower, pCandMaxPower])
    else:
        pMaxPowerElec = pExistMaxPower
    pMaxPowerElec = pMaxPowerElec.sort_index()

    # Determination of the net demand
    if mTEPES.re:
        OutputToFile1 = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,re]() for rt in mTEPES.rt for re in r2r[rt] if (nd,re) in mTEPES.n2g and (p,re) in mTEPES.pre) for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    else:
        OutputToFile1 = pd.Series(data=[0.0                                                                                                                             for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile2     = pd.Series(data=[      mTEPES.pDemandElec [p,sc,n,nd]()                                                                                            for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile  = OutputToFile2 - OutputToFile1
    OutputToFile  *= 1e3
    OutputToFile  = OutputToFile.to_frame(name='MW')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetDemandNetwork_{CaseName}.csv', sep=',')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'],                    values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetDemand_{CaseName}.csv', sep=',')

    # Determination of the index: Reserve Margin
    OutputToFile1 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    OutputToFile2 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile1[p,sc] = pMaxPowerElec.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum')[0].max()
        OutputToFile2[p,sc] = pDemandElec.loc  [(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum')[0].max()
    ReserveMargin1 =  OutputToFile1 - OutputToFile2
    ReserveMargin2 = (OutputToFile1 - OutputToFile2)/OutputToFile2
    ReserveMargin1.to_frame(name='MW'  ).rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_ReserveMargin_{CaseName}.csv',        sep=',')
    ReserveMargin2.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_ReserveMarginPerUnit_{CaseName}.csv', sep=',')

    # Determination of the index: Largest Unit
    OutputToFile = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile[p,sc] = pMaxPowerElec.loc[(p,sc)].reset_index().pivot_table(index=['level_1'], values=0, aggfunc='sum')[0].max()

    LargestUnit  = ReserveMargin1/OutputToFile
    LargestUnit.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).oT.write(f'{_path}/oT_Result_LargestUnitPerUnit_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing           reliability indexes  ... ', round(WritingResultsTime), 's')
