"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 11, 2026

Marginal, cost-summary, and economic results.

This module writes the price and money side of the solution: locational short-run marginal costs (electricity, hydrogen, heat), reserve-margin, emission, and
RES-energy marginals, and water values (MarginalResults); the system cost breakdown by period (CostSummaryResults); and the full economic report -- energy
balances, market results, operation costs, revenues, and per-generator cost recovery (EconomicResults). These functions read the dual values stored in ``mTEPES.pDuals``.
"""

import time
import os
import math
import pandas            as     pd
from   collections       import defaultdict

try:
    from          .openTEPES_OutputResultsCommon import _outdir, PiePlots, LinePlots
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir, PiePlots, LinePlots


def MarginalResults(DirName, CaseName, OptModel, mTEPES, pIndPlotOutput):
    # %% outputting marginal results
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(set)
    lout = defaultdict(set)
    for ni,nf,cc in mTEPES.la:
        lin [nf].add((ni,cc))
        lout[ni].add((nf,cc))

    # nodes to generators (g2n)
    g2n = defaultdict(set)
    # nodes to CHPs (c2n), to heat pumps (h2n), to electrolyzers (e2n)
    c2n = defaultdict(set)
    h2n = defaultdict(set)
    e2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.ch:
            c2n[nd].add(g)
        if g in mTEPES.hp:
            h2n[nd].add(g)
        if g in mTEPES.el:
            e2n[nd].add(g)

    # generators to area (e2a) (n2a)
    g2a = defaultdict(set)
    e2a = defaultdict(set)
    n2a = defaultdict(set)
    for ar,g in mTEPES.a2g:
        g2a[ar].add(g)
        if g in mTEPES.es:
            e2a[ar].add(g)
        if g in mTEPES.nr:
            n2a[ar].add(g)

    # the reserve guards below ask the same yes/no questions twice over, each one scanning a whole 4-D Param or a dense area x unit
    # product. Answer them once here. pOperReserve* is declared without mutable=, so Param[idx] is a float and must NOT be called.
    pHasOperReserveUp = any(mTEPES.pOperReserveUp[idx] for idx in mTEPES.pOperReserveUp)
    pHasOperReserveDw = any(mTEPES.pOperReserveDw[idx] for idx in mTEPES.pOperReserveDw)
    pHasRampReserveUp  = hasattr(mTEPES, 'pRampReserveUp') and any(mTEPES.pRampReserveUp[idx] for idx in mTEPES.pRampReserveUp)
    pHasRampReserveDw  = hasattr(mTEPES, 'pRampReserveDw') and any(mTEPES.pRampReserveDw[idx] for idx in mTEPES.pRampReserveDw)
    # eOperReserveUp / eOperReserveDw exist only where some unit can actually offer reserve in that period: mirror nr2aRsrv / eh2aRsrv of openTEPES_ModelFormulationElectricity.py:67-68, and note that eh = es | h, so hydro consumption counts too
    pRsrvOfferArea    = {(p,ar): any(nr in g2a[ar] and mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr for nr in mTEPES.nr) or any(eh in g2a[ar] and mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh for eh in mTEPES.eh) for p in mTEPES.p for ar in mTEPES.ar}
    pHasReserveOffer  = any(pRsrvOfferArea.values())

    # tolerance to treat a number as 0
    pSlackTolerance = 1e-6

    #%% outputting the incremental variable cost of each Generator (neither ESS nor boilers) with power surplus
    sPSNARG      = [(p,sc,n,ar,g) for p,sc,n,ar,g in mTEPES.psn*mTEPES.a2g if g not in mTEPES.eh and g not in mTEPES.bo and (p,g) in mTEPES.pg]
    OutputToFile = pd.Series(data=[(mTEPES.pLinearVarCost[p,sc,n,g]()+mTEPES.pEmissionVarCost[p,sc,n,g]) if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pSlackTolerance else math.inf for p,sc,n,ar,g in sPSNARG], index=pd.Index(sPSNARG))
    OutputToFile *= 1e3

    OutputToFile = OutputToFile.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='EUR/MWh')
    OutputToFile.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalIncrementalVariableCost_{CaseName}.csv', sep=',')
    IncrementalGens = OutputToFile.idxmin(axis=1)
    IncrementalGens[~(OutputToFile.lt(math.inf).any(axis=1))] = 'N/A'
    IncrementalGens = IncrementalGens.reindex(pd.Index(list(mTEPES.psnar)), fill_value='N/A').to_frame(name='Generator')
    IncrementalGens.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).oT.write(f'{_path}/oT_Result_MarginalIncrementalGenerator_{CaseName}.csv', index=True, sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pEmissionRate[g] for p,sc,n,ar,g in sPSNARG], index=pd.Index(sPSNARG))
    OutputToFile.to_frame(name='tCO2/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='tCO2/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationIncrementalEmission_{CaseName}.csv', sep=',')

    pHasDuals = hasattr(mTEPES, 'pDuals') and mTEPES.pDuals is not None and hasattr(mTEPES.pDuals, '__len__') and len(mTEPES.pDuals) > 0

    # eBalanceElec is skipped at nodes with no line and no generator available in the period (openTEPES_ModelFormulationElectricity.py:241): counting every generator of the node asks for a dual that was never created
    pNodeHasBalanceElec = {(p,nd): bool(lout[nd]) or bool(lin[nd]) or any((p,g) in mTEPES.pg for g in g2n[nd]) for p in mTEPES.p for nd in mTEPES.nd}

    #%% outputting the LSRMC of electricity
    if pHasDuals:
        sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if pNodeHasBalanceElec[p,nd] and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
        OutputResults *= 1e3
        OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMC').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkSRMC_{CaseName}.csv', sep=',')
        OptModel.LSRMC = OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMC').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, OptModel.LSRMC, 'Node', 'LoadLevel', 'EUR/MWh')
                chart.save(f'{_path}/oT_Plot_NetworkSRMC_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    if mTEPES.pIndHydrogen() and pHasDuals:

        # incoming and outgoing lines (lin) (lout)
        lin  = defaultdict(set)
        lout = defaultdict(set)
        for ni,nf,cc in mTEPES.pa:
            lin [nf].add((ni,cc))
            lout[ni].add((nf,cc))

        # nodes to hydrogen boilers (b2n): eBalanceH2 also exists at a node that only hosts an H2 boiler (openTEPES_ModelFormulationHydrogen.py:36)
        b2n = defaultdict(set)
        for nd,g in mTEPES.n2g:
            if g in mTEPES.hh:
                b2n[nd].add(g)

        #%% outputting the LSRMC of H2
        sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if len(e2n[nd]) + len(b2n[nd]) + len(lout[nd]) + len(lin[nd]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eBalanceH2_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
        OutputResults *= 1e3
        OutputResults.to_frame(name='LSRMCH2').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMCH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkSRMCH2_{CaseName}.csv', sep=',')
        OptModel.LSRMCH2 = OutputResults.to_frame(name='LSRMCH2').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMCH2').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, OptModel.LSRMCH2, 'Node', 'LoadLevel', 'EUR/tH2')
                chart.save(f'{_path}/oT_Plot_NetworkSRMCH2_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    if mTEPES.pIndHeat() and pHasDuals:
        # incoming and outgoing lines (lin) (lout)
        lin  = defaultdict(set)
        lout = defaultdict(set)
        for ni,nf,cc in mTEPES.ha:
            lin [nf].add((ni,cc))
            lout[ni].add((nf,cc))

        #%% outputting the LSRMC of heat
        sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if len(c2n[nd]) + len(h2n[nd]) + len(lout[nd]) + len(lin[nd]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eBalanceHeat_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
        OutputResults *= 1e3
        OutputResults.to_frame(name='LSRMCHeat').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMCHeat').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkSRMCHeat_{CaseName}.csv', sep=',')

        OptModel.LSRMCHeat = OutputResults.to_frame(name='LSRMCHeat').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMCHeat').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, OptModel.LSRMCHeat, 'Node', 'LoadLevel', 'EUR/GJ')
                chart.save(f'{_path}/oT_Plot_NetworkSRMCHeat_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    if (mTEPES.gc or mTEPES.gd) and sum(mTEPES.pReserveMargin[:,:]()) and pHasDuals:
        # the firm-capacity sum per area does not depend on (period, scenario, stage); precompute it once per area instead of re-summing over all generators for every tuple
        pExistingFirmCapacity = {(p, ar): sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] if (p,g) in mTEPES.pg and g not in mTEPES.gc and g not in mTEPES.gd) for p in mTEPES.p for ar in mTEPES.ar}
        # eAdequacyReserveMarginElec is skipped in areas without a candidate unit available in the period (openTEPES_ModelFormulationInvestment.py:202): len(g2a[ar]) asks for a dual that was never created
        pHasCandidateInArea   = {(p, ar): any(gc in g2a[ar] and (p,gc) in mTEPES.pgc for gc in mTEPES.gc) for p in mTEPES.p for ar in mTEPES.ar}
        sPSSTAR               = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pReserveMargin[p,ar]() and st == mTEPES.Last_st and pHasCandidateInArea[p,ar] and pExistingFirmCapacity[p,ar] <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]()]
        if sPSSTAR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f'eAdequacyReserveMarginElec_{p}_{sc}_{st}{ar}'] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
            OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalReserveMargin_{CaseName}.csv', sep=',')

    if mTEPES.pIndHeat() and (mTEPES.gc or mTEPES.gd) and sum(mTEPES.pReserveMarginHeat[:,:]) and pHasDuals:
        # the firm-capacity sum per area does not depend on (period, scenario, stage); precompute it once per area
        pExistingFirmCapacity = {(p,ar): sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] if (p,g) in mTEPES.pg and g not in mTEPES.gc and g not in mTEPES.gd) for p in mTEPES.p for ar in mTEPES.ar}
        # same skip condition as eAdequacyReserveMarginHeat (openTEPES_ModelFormulationInvestment.py:261)
        pHasCandidateInArea   = {(p,ar): any(gc in g2a[ar] and (p,gc) in mTEPES.pgc for gc in mTEPES.gc) for p in mTEPES.p for ar in mTEPES.ar}
        sPSSTAR               = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pReserveMarginHeat[p,ar] and st == mTEPES.Last_st and pHasCandidateInArea[p,ar] and pExistingFirmCapacity[p,ar] <= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]]
        if sPSSTAR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f'eAdequacyReserveMarginHeat_{p}_{sc}_{st}{ar}'] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
            OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalReserveMarginHeat_{CaseName}.csv', sep=',')

    if pHasDuals:
        # mirror the skip condition of eMaxSystemEmission (openTEPES_ModelFormulationInvestment.py:214): the constraint looks at the emission rate, not at the emission cost, and the rate does not depend on (sc,n)
        pHasEmissionRate  = {ar: sum(mTEPES.pEmissionRate[g] for g in g2a[ar]) != 0.0 for ar in mTEPES.ar}
        sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pEmission[p,ar] < math.inf and st == mTEPES.Last_st and pHasEmissionRate[ar]]
        if sPSSTAR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f'eMaxSystemEmission_{p}_{sc}_{st}{ar}'] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
            OutputResults.to_frame(name='EM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='EM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalEmission_{CaseName}.csv', sep=',')

        sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pRESEnergy[p,ar]() and st == mTEPES.Last_st]
        if sPSSTAR:
            pTotalDuration = {(p,sc): sum(mTEPES.pLoadLevelDuration[p,sc,na]() for na in mTEPES.na) for p,sc in mTEPES.ps}
            OutputResults  = pd.Series(data=[mTEPES.pDuals[f'eMinSystemRESEnergy_{p}_{sc}_{st}{ar}']*1e-3*pTotalDuration[p,sc] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
            OutputResults.to_frame(name='RES').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RES').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalRESEnergy_{CaseName}.csv', sep=',')

    #%% outputting the up operating reserve marginal
    if pHasOperReserveUp and pHasReserveOffer and pHasDuals:
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveUp[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults *= 1e3
        OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='UORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalOperatingReserveUp_{CaseName}.csv', sep=',')
        if pIndPlotOutput:
            MarginalUpOperatingReserve = OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='UORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)
            available_period_scenario = set(MarginalUpOperatingReserve.index.droplevel([2,3]).unique().tolist())
            for p,sc in mTEPES.ps:
                if (p,sc) in available_period_scenario:
                    chart = LinePlots(p, sc, MarginalUpOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW')
                    chart.save(f'{_path}/oT_Plot_MarginalOperatingReserveUp_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    #%% outputting the down operating reserve marginal
    if pHasOperReserveDw and pHasReserveOffer and pHasDuals:
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveDw[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults *= 1e3
        OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='DORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalOperatingReserveDown_{CaseName}.csv', sep=',')
        if pIndPlotOutput:
            MarginalDwOperatingReserve = OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='DORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)
            available_period_scenario = set(MarginalDwOperatingReserve.index.droplevel([2,3]).unique().tolist())
            for p,sc in mTEPES.ps:
                if (p,sc) in available_period_scenario:
                    chart = LinePlots(p, sc, MarginalDwOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW')
                    chart.save(f'{_path}/oT_Plot_MarginalOperatingReserveDown_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    #%% outputting the water values
    if mTEPES.es and pHasDuals:
        # eESSInventory is declared over mTEPES.nesc (openTEPES_ModelFormulationElectricity.py:312), i.e. only the load levels that close a storage cycle; mTEPES.nesc is a plain list, so test membership against a set built once
        pNESC         = set(mTEPES.nesc)
        sPSSTNES      = [(p,sc,st,n,es) for p,sc,st,n,es in mTEPES.s2n*mTEPES.es if (p,sc,n,es) in mTEPES.psnes and (n,es) in pNESC and (mTEPES.pTotalMaxCharge[es] or mTEPES.pTotalEnergyInflows[es])]
        OutputToFile  = pd.Series(data=[abs(mTEPES.pDuals[f"eESSInventory_{p}_{sc}_{st}('{n}', '{es}')"])*1e3 for p,sc,st,n,es in sPSSTNES], index=pd.Index(sPSSTNES))
        if len(OutputToFile):
            OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_MarginalEnergyValue_{CaseName}.csv', sep=',')
        if pIndPlotOutput and len(OutputToFile):
            WaterValue = OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0)
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, WaterValue, 'Generator', 'LoadLevel', 'EUR/MWh')
                chart.save(f'{_path}/oT_Plot_MarginalEnergyValue_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    # #%% Reduced cost for NetworkInvestment
    # ReducedCostActivation = mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetElecInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)
    # if mTEPES.lc and not ReducedCostActivation and OptModel.vNetworkInvest.is_variable_type():
    #     OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[p,ni,nf,cc]] for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
    #     OutputToFile.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
    #     OutputToFile.to_frame(name='MEUR').to_csv(f'{_path}/oT_Result_NetworkInvestment_ReducedCost_{CaseName}.csv', sep=',')
    #
    # #%% Reduced cost for NetworkCommitment
    # if mTEPES.ls and not ReducedCostActivation and OptModel.vLineCommit.is_variable_type():
    #     OutputResults = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[p,sc,n,ni,nf,cc]] for p,sc,n,ni,nf,cc in mTEPES.psnls], index=mTEPES.psnlas)
    #     OutputResults.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    #     OutputResults = pd.pivot_table(OutputResults.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    #     OutputResults.index.names = [None] * len(OutputResults.index.names)
    #     OutputResults.to_csv(f'{_path}/oT_Result_NetworkCommitment_ReducedCost_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  marginal information results  ... ', round(WritingResultsTime), 's')


# @profile
def CostSummaryResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # SysCost       = pd.Series(data=[                                                                  OptModel.vTotalSCost()                                                                                         ], index=['']    ).to_frame(name='Total          System Cost').stack()
    GenInvCost      = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenInvestCost[gc  ]          * OptModel.vGenerationInvest[p,gc  ]()  for gc   in mTEPES.gc    if (p,gc) in mTEPES.pgc)         for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Generation').stack()
    GenRetCost      = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenRetireCost[gd  ]          * OptModel.vGenerationRetire[p,gd  ]()  for gd   in mTEPES.gd    if (p,gd) in mTEPES.pgd)         for p in mTEPES.p], index=mTEPES.p).to_frame(name='Retirement Cost Generation').stack()
    NetInvCost      = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pNetFixedCost [lc  ]          * OptModel.vNetworkInvest   [p,lc  ]()  for lc   in mTEPES.lc    if (p,lc) in mTEPES.plc)         for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Network'   ).stack()
    if mTEPES.pIndHydroTopology():
        RsrInvCost  = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pRsrInvestCost[rc  ]          * OptModel.vReservoirInvest [p,rc  ]()  for rc   in mTEPES.rn    if (p,rc) in mTEPES.prc)         for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reservoir' ).stack()
    else:
        RsrInvCost  = pd.Series(data=[0.0                                                                                                                                                                      for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reservoir' ).stack()
    if mTEPES.pIndHydrogen():
        H2InvCost   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pH2PipeFixedCost  [ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc]() for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc)   for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Hydrogen'  ).stack()
    else:
        H2InvCost   = pd.Series(data=[0.0                                                                                                                                                                      for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Hydrogen'  ).stack()
    if mTEPES.pIndHeat():
        HeatInvCost = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc]() for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Heat'      ).stack()
    else:
        HeatInvCost = pd.Series(data=[0.0                                                                                                                                                                     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Heat'      ).stack()
    # cache the (scenario, load level) product once; it is reused by every operation-cost series below instead of rebuilding the Pyomo set product for each period and each cost
    pScenFactor = {(p,sc): mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() for p,sc in mTEPES.ps}
    pSNofP          = {p: [(sc,n) for sc in mTEPES.sc if (p,sc) in mTEPES.ps for n in mTEPES.n] for p in mTEPES.p}
    GenCost         = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalGCost    [p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Operation Cost Generation' ).stack()
    ConCost         = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalCCost    [p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Operation Cost Consumption').stack()
    EmiCost         = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalECost    [p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Emission Cost'             ).stack()
    NetCost         = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalNCost    [p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Operation Cost Network'    ).stack()

    # The AC reactive investments have their own row: their cost is inside vTotalFElecCost and therefore inside the reported total, so without a row
    # here the summary no longer adds up to the total system cost.
    if mTEPES.pIndACPowerFlow() and (mTEPES.shc or mTEPES.sqc):
        ReactInvCost = pd.Series(data=[mTEPES.pDiscountedWeight[p] * (sum(mTEPES.pShuntFixedCost[sh] * OptModel.vShuntInvest[p,sh]() for sh in mTEPES.shc if (p,sh) in mTEPES.pshc)
                                                                    + sum(mTEPES.pSynchFixedCost[sq] * OptModel.vSynchInvest[p,sq]() for sq in mTEPES.sqc if (p,sq) in mTEPES.psqc)) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reactive'  ).stack()
    else:
        ReactInvCost = pd.Series(data=[0.0                                                                                                                                           for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reactive'  ).stack()

    # The AC current penalty is broken out of the network operation cost rather than left inside it. On 9n_AC it is 3.83 of 157.27 MEUR — 2.4% of the
    # reported total — and merged into 'Operation Cost Network' a reader takes it for ohmic losses, which are a tiny fraction of that number. It is a
    # numerical device, not a physical cost, so it is named as one. See the pEpsilonCurrent block in openTEPES_ModelFormulationObjective.
    if mTEPES.pIndACPowerFlow() == 1:                          # the current penalty prices vCurr, which only branch flow has
        try:
            from .openTEPES_ModelFormulationObjective          import AC_CURRENT_PENALTY as pEpsCurr
        except ImportError:
            from openTEPES.openTEPES_ModelFormulationObjective import AC_CURRENT_PENALTY as pEpsCurr
        CurrPen  = pd.Series(data=[sum(pScenFactor[p,sc] * pEpsCurr * mTEPES.pLoadLevelDuration[p,sc,n]() * sum(OptModel.vCurr[p,sc,n,ni,nf,cc]() for ni,nf,cc in mTEPES.laa if (p,ni,nf,cc) in mTEPES.pla) for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='AC Current Penalty'        ).stack()
        # subtract by value: both are one entry per period in the same order, but their stacked indices carry different row names
        NetCost  = NetCost.sub(CurrPen.values)
    else:
        CurrPen  = pd.Series(data=[0.0                                                                                                                                               for p in mTEPES.p], index=mTEPES.p).to_frame(name='AC Current Penalty'        ).stack()
    ElecRelCost     = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalRElecCost[p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost'          ).stack()
    if mTEPES.pIndHydrogen():
        H2RelCost   = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalRH2Cost  [p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost Hydrogen' ).stack()
    else:
        H2RelCost   = pd.Series(data=[0.0                                                                               for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost Hydrogen' ).stack()
    if mTEPES.pIndHeat():
        HeatRelCost = pd.Series(data=[sum(pScenFactor[p,sc] * OptModel.vTotalRHeatCost[p,sc,n]() for sc,n in pSNofP[p]) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost Heat'     ).stack()
    else:
        HeatRelCost = pd.Series(data=[0.0                                                                               for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost Heat'     ).stack()
    CostSummary    = pd.concat([GenInvCost, GenRetCost, NetInvCost, ReactInvCost, RsrInvCost, H2InvCost, HeatInvCost, GenCost, ConCost, EmiCost, NetCost, CurrPen, ElecRelCost, H2RelCost, HeatRelCost]).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Cost', 0: 'MEUR'})

    CostSummary['MEUR/year'] = CostSummary['MEUR']
    for p in mTEPES.p:
        CostSummary.loc[CostSummary['Period'] == p, 'MEUR/year'] = CostSummary.loc[CostSummary['Period'] == p, 'MEUR'] / mTEPES.pDiscountedWeight[p]
    CostSummary.oT.write(f'{_path}/oT_Result_CostSummary_{CaseName}.csv', sep=',', index=False)

    # DemPayment   = pd.Series(data=[sum(pScenFactor     [p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pDemandElec[p,sc,n,nd]() * OptModel.LSRMC            [p,sc,n,nd] for sc,n,nd in mTEPES.sc*mTEPES.n*mTEPES.nd if (p,sc) in mTEPES.ps )/1e3 for p in mTEPES.p], index=mTEPES.p).to_frame(name='Demand Payment'            ).stack()

    WritingResultsTime = time.time() - StartTime
    print('Writing          cost summary results  ... ', round(WritingResultsTime), 's')


# @profile
def EconomicResults(DirName, CaseName, OptModel, mTEPES, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the system costs and revenues
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # %% Power balance per period, scenario, and load level
    # incoming and outgoing lines (lin) (lout)
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

    # generators to nodes (g2n) (e2n)
    g2n = defaultdict(set)
    e2n = defaultdict(set)
    r2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.eh:
            e2n[nd].add(g)
        if g in mTEPES.re:
            r2n[nd].add(g)

    # generators to area (n2a)(g2a)
    g2a = defaultdict(set)
    n2a = defaultdict(set)
    for ar,g in mTEPES.a2g:
        g2a[ar].add(g)
        if g in mTEPES.nr:
            n2a[ar].add(g)

    # same guards as in MarginalResults: answer once instead of rescanning a 4-D Param and a dense area x unit product per use.
    # pOperReserve* is declared without mutable=, so Param[idx] is a float and must NOT be called.
    pHasOperReserveUp = any(mTEPES.pOperReserveUp[idx] for idx in mTEPES.pOperReserveUp)
    pHasOperReserveDw = any(mTEPES.pOperReserveDw[idx] for idx in mTEPES.pOperReserveDw)
    # eOperReserveUp / eOperReserveDw exist only where some unit can actually offer reserve in that period: mirror nr2aRsrv / eh2aRsrv of
    # openTEPES_ModelFormulationElectricity.py:67-68, and note that eh = es | h, so hydro consumption counts too. This function has no e2a,
    # only g2a; testing membership there selects the same units because the comprehensions already iterate mTEPES.nr and mTEPES.eh.
    pRsrvOfferArea    = {(p,ar): any(nr in g2a[ar] and mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr for nr in mTEPES.nr) or any(eh in g2a[ar] and mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh for eh in mTEPES.eh) for p in mTEPES.p for ar in mTEPES.ar}
    pHasReserveOffer  = any(pRsrvOfferArea.values())

    # eBalanceElec is skipped at nodes with no line and no generator available in the period (openTEPES_ModelFormulationElectricity.py:241):
    # counting every generator of the node asks for a dual that was never created. lin / lout are not reassigned in this function.
    pNodeHasBalanceElec = {(p,nd): bool(lout[nd]) or bool(lin[nd]) or any((p,g) in mTEPES.pg for g in g2n[nd]) for p in mTEPES.p for nd in mTEPES.nd}

    # generators to technology (o2e) (g2t)
    g2t = defaultdict(set)
    e2e = defaultdict(set)
    o2e = defaultdict(set)
    r2r = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)
        if g in mTEPES.eh:
            e2e[gt].add(g)
        if g in mTEPES.es:
            o2e[gt].add(g)
        if g in mTEPES.re:
            r2r[gt].add(g)

    if sum(1 for ar in mTEPES.ar if len(g2a[ar])) > 1:
        if pIndAreaOutput:
            for ar in mTEPES.ar:
                if len(g2a[ar]):
                    sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg)]
                    if sPSNGT:
                        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}_{ar}.csv', sep=',')

                        if pIndPlotOutput:
                            for p,sc in mTEPES.ps:
                                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    sPSNARND = [(p,sc,n,ar,nd) for p,sc,n,ar,nd in mTEPES.psn*mTEPES.arnd if len(g2n[nd]) + len(lout[nd]) + len(lin[nd])]

    # precompute valid technologies and resources per period to avoid recomputing for each tuple
    _valid_gt_per_p = {}
    _valid_rt_per_p = {}
    _valid_et_per_p = {}
    _periods = {p for p,_,_,_,_ in sPSNARND}
    for p in _periods:
        _valid_gt_per_p[p] = [gt for gt in mTEPES.gt if any((p,g ) in mTEPES.pg  for g  in g2t.get(gt,[]))]
        _valid_rt_per_p[p] = [rt for rt in mTEPES.rt if any((p,re) in mTEPES.pre for re in r2r.get(rt,[]))]
        _valid_et_per_p[p] = [et for et in mTEPES.et if any((p,eh) in mTEPES.peh for eh in e2e.get(et,[]))]

    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd in sPSNARND for gt in _valid_gt_per_p.get(p,[])]
    sPSNARNDRT = [(p,sc,n,ar,nd,rt) for p,sc,n,ar,nd in sPSNARND for rt in _valid_rt_per_p.get(p,[])]
    sPSNARNDET = [(p,sc,n,ar,nd,et) for p,sc,n,ar,nd in sPSNARND for et in _valid_et_per_p.get(p,[])]

    # the three membership tests inside the sums below do not depend on (sc,n,ar): resolve them once per (p,nd,gt) instead of once per tuple and generator, keeping the iteration order of g2n[nd] so the sums are unchanged
    pNodeTechNR = {(p,nd,gt): [nr for nr in g2n[nd] if (p,nr) in mTEPES.pnr and nr in g2t[gt] and nr not in mTEPES.eh] for p in mTEPES.p for nd in mTEPES.nd for gt in mTEPES.gt}
    pNodeTechRE = {(p,nd,rt): [re for re in r2n[nd] if (p,re) in mTEPES.pre and re in r2r[rt]                        ] for p in mTEPES.p for nd in mTEPES.nd for rt in mTEPES.rt}
    pNodeTechEH = {(p,nd,et): [eh for eh in e2n[nd] if (p,eh) in mTEPES.peh and eh in e2e[et]                        ] for p in mTEPES.p for nd in mTEPES.nd for et in mTEPES.et}

    if sum(1 for nr in mTEPES.nr if nr not in mTEPES.eh):
        OutputResults01 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,nr      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nr in pNodeTechNR[p,nd,gt]) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.re:
        OutputResults02 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,re      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for re in pNodeTechRE[p,nd,rt]) for p,sc,n,ar,nd,rt in sPSNARNDRT], index=pd.Index(sPSNARNDRT)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.eh:
        OutputResults03 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for eh in pNodeTechEH[p,nd,et]) for p,sc,n,ar,nd,et in sPSNARNDET], index=pd.Index(sPSNARNDET)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
        OutputResults04 = pd.Series(data=[-sum(OptModel.vESSTotalCharge[p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for eh in pNodeTechEH[p,nd,et]) for p,sc,n,ar,nd,et in sPSNARNDET], index=pd.Index(sPSNARNDET)).to_frame(name='Consumption'    ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Consumption', aggfunc='sum').rename(columns={et: et+str(' -') for et in mTEPES.et})
    OutputResults05     = pd.Series(data=[     OptModel.vENS           [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                      for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyNotServed')
    OutputResults06     = pd.Series(data=[-  mTEPES.pDemandElec        [p,sc,n,nd      ]()  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                      for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyDemand'   )
    OutputResults07     = pd.Series(data=[-sum(OptModel.vFlowElec      [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in lout [nd] if (p,nd,nf,cc) in mTEPES.pla                               ) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowOut'  )
    # Under AC the loss lives INSIDE the pair (vFlowElec, vFlowElecBck) — eBalanceElecAC carries no separate loss term for an AC branch — so the
    # arriving energy is -vFlowElecBck and the loss must not be subtracted a second time. Taking the sending-end value and then also subtracting
    # vLineLosses at both ends leaves oT_Result_BalanceEnergyPerNode / PerTech / PerArea short by roughly the total AC losses. HVDC links keep the DC
    # treatment: sending-end flow with the loss factor accounted separately.
    if mTEPES.pIndACPowerFlow():
        OutputResults08 = pd.Series(data=[(-sum(OptModel.vFlowElecBck  [p,sc,n,ni,nd,cc]()                                    for ni,cc in lin  [nd] if (p,ni,nd,cc) in mTEPES.pla and (ni,nd,cc) in mTEPES.laa)
                                           +sum(OptModel.vFlowElec     [p,sc,n,ni,nd,cc]()                                    for ni,cc in lin  [nd] if (p,ni,nd,cc) in mTEPES.pla and (ni,nd,cc) in mTEPES.lad))*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ar,nd in sPSNARND], index=pd.Index(sPSNARND)).to_frame(name='EnergyFlowIn'   )
    else:
        OutputResults08 = pd.Series(data=[ sum(OptModel.vFlowElec      [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in lin  [nd] if (p,ni,nd,cc) in mTEPES.pla                               ) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowIn'   )
    if mTEPES.ll:
        # only branches whose loss is NOT already inside the reported flows, i.e. the DC ones once AC is on
        _lossOK = (lambda la: la in mTEPES.lad) if mTEPES.pIndACPowerFlow() else (lambda la: True)
        OutputResults09 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pla and _lossOK((nd,nf,cc))     ) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesOut'  )
        OutputResults10 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pla and _lossOK((ni,nd,cc))     ) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesIn'   )

    # A shunt with a non-zero conductance draws active power and eBalanceElecAC carries that term, so the report needs it too or the rows sum to the
    # shunt draw instead of to zero. The variable only exists when some device actually has a conductance, which is why this is conditional.
    pHasPShunt = mTEPES.pIndACPowerFlow() and hasattr(OptModel, 'vPShunt')
    if pHasPShunt:
        pShuntAt = defaultdict(list)
        for nd, sh in mTEPES.n2sh:
            pShuntAt[nd].append(sh)
        OutputResults11 = pd.Series(data=[sum(OptModel.vPShunt[p,sc,n,sh]() for sh in pShuntAt[nd] if (p,sc,n,sh) in mTEPES.psnsh)*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ar,nd in sPSNARND], index=pd.Index(sPSNARND)).to_frame(name='ShuntDraw'      )

    OutputResults = pd.DataFrame()
    # Check if there are any non-RES generators
    if sum(1 for nr in mTEPES.nr if nr not in mTEPES.eh):
        OutputResults  = pd.concat([OutputResults,OutputResults01]                                                ,axis=1)
    if mTEPES.re:
        OutputResults  = pd.concat([OutputResults,OutputResults02]                                                ,axis=1)
    if mTEPES.eh:
        OutputResults  = pd.concat([OutputResults,OutputResults03,OutputResults04]                                ,axis=1)
    OutputResults      = pd.concat([OutputResults,OutputResults05,OutputResults06,OutputResults07,OutputResults08],axis=1)
    if mTEPES.ll:
        OutputResults  = pd.concat([OutputResults,OutputResults09,OutputResults10]                                ,axis=1)
    if pHasPShunt:
        OutputResults  = pd.concat([OutputResults,OutputResults11]                                                ,axis=1)

    # Merge duplicate columns that arise when a technology belongs to multiple sets (gt ∩ rt, gt ∩ et, …)
    if OutputResults.columns.duplicated().any():
        OutputResults = OutputResults.T.groupby(level=0).sum().T

    # the three aggregations below start from the same stacked frame: build it once instead of three times over the largest frame of the module
    OutputStacked = OutputResults.stack().reset_index()
    OutputStacked.pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).oT.write(f'{_path}/oT_Result_BalanceEnergyPerTech_{CaseName}.csv', sep=',')
    OutputStacked.pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceEnergyPerNode_{CaseName}.csv', sep=',')
    OutputStacked.pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceEnergyPerArea_{CaseName}.csv', sep=',')

    #%% outputting the demand and the LSRMC of electricity
    sPSSTNARND    = [(p,sc,st,n,ar,nd) for p,sc,st,n,ar,nd in mTEPES.s2n*mTEPES.arnd if pNodeHasBalanceElec[p,nd] and (p,sc,n) in mTEPES.psn]

    pHasDuals = hasattr(mTEPES, 'pDuals') and mTEPES.pDuals is not None and hasattr(mTEPES.pDuals, '__len__') and len(mTEPES.pDuals) > 0
    pHasRampReserveUp = hasattr(mTEPES, 'pRampReserveUp') and any(mTEPES.pRampReserveUp[idx] for idx in mTEPES.pRampReserveUp)
    pHasRampReserveDw = hasattr(mTEPES, 'pRampReserveDw') and any(mTEPES.pRampReserveDw[idx] for idx in mTEPES.pRampReserveDw)

    if pHasDuals:
        # keep the LSRMC under its own name: OutputResults still holds the energy balance built above, and concatenating that by mistake writes GWh into a price file
        LSRMCElec     = pd.Series(data=[mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,ar,nd in sPSSTNARND], index=pd.Index(sPSSTNARND))
        LSRMCElec *= 1e3
        LSRMCElec.index = LSRMCElec.index.droplevel(2)
        OutputResults = pd.Series(data=[mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,ar,nd in sPSSTNARND], index=pd.Index(sPSSTNARND))
        OutputResults *= 1e3
        OutputResults.index = OutputResults.index.droplevel(2)

    # generate the sets for the different generator types
    sPSNARNDG  = []
    sPSNARNDNR = []
    sPSNARNDRE = []
    sPSNARNDEH = []
    for p,sc,n,ar,nd in sPSNARND:
        for g in g2n.get(nd,[]):
            if (p,g) in mTEPES.pg:
                sPSNARNDG.append((p,sc,n,ar,nd,g))
            if (p,g) in mTEPES.pnr and g not in mTEPES.eh:
                sPSNARNDNR.append((p,sc,n,ar,nd,g))
            if (p,g) in mTEPES.pre:
                sPSNARNDRE.append((p,sc,n,ar,nd,g))
            if (p,g) in mTEPES.peh:
                sPSNARNDEH.append((p,sc,n,ar,nd,g))

    #%% outputting the generator power output
    if sum(1 for nr in mTEPES.nr if nr not in mTEPES.eh):
        OutputResults01 = pd.Series(data=[    OptModel.vTotalOutput   [p,sc,n,nr      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                       for p,sc,n,ar,nd,nr in sPSNARNDNR], index=pd.Index(sPSNARNDNR)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.re:
        OutputResults02 = pd.Series(data=[    OptModel.vTotalOutput   [p,sc,n,re      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                       for p,sc,n,ar,nd,re in sPSNARNDRE], index=pd.Index(sPSNARNDRE)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.eh:
        OutputResults03 = pd.Series(data=[    OptModel.vTotalOutput   [p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                       for p,sc,n,ar,nd,eh in sPSNARNDEH], index=pd.Index(sPSNARNDEH)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
        OutputResults04 = pd.Series(data=[   -OptModel.vESSTotalCharge[p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                       for p,sc,n,ar,nd,eh in sPSNARNDEH], index=pd.Index(sPSNARNDEH)).to_frame(name='Consumption'    ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Consumption', aggfunc='sum').rename(columns={et: et+str(' -') for et in mTEPES.et})
    # OutputResults05 (EnergyNotServed) and OutputResults08 (EnergyFlowIn) used to be rebuilt here and were never read again: the two
    # frames written below take 04, 06, 09 and 10, and the generation block takes 01, 02 and 03. Two full passes over sPSNARND removed.
    OutputResults06     = pd.Series(data=[   -mTEPES.pDemandElec      [p,sc,n,nd      ]()  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                       for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyDemand'   )
    if mTEPES.ll:
        # same reason as the balance-report pair above: under AC the loss is already inside vFlowElec/vFlowElecBck, so adding vLineLosses again
        # overstates the demand column of oT_Result_MarketResultsDemand and therefore the demand payment computed from it and the LSRMC
        _lossOK2 = (lambda la: la in mTEPES.lad) if mTEPES.pIndACPowerFlow() else (lambda la: True)
        OutputResults09 = pd.Series(data=[-sum(OptModel.vLineLosses   [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pla and _lossOK2((nd,nf,cc))) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesOut'  )
        OutputResults10 = pd.Series(data=[-sum(OptModel.vLineLosses   [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pla and _lossOK2((ni,nd,cc))) for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesIn'   )

    MarketResultsDem     = pd.DataFrame()
    if mTEPES.eh:
        MarketResultsDem = pd.concat([MarketResultsDem, OutputResults04],axis=1)
    MarketResultsDem     = pd.concat([MarketResultsDem, OutputResults06],axis=1)
    if mTEPES.ll:
        MarketResultsDem = pd.concat([MarketResultsDem, OutputResults09, OutputResults10], axis=1)

    MarketResultsDem *= -1e3
    if pHasDuals:
        MarketResultsDem = pd.concat([MarketResultsDem.sum(axis=1), LSRMCElec], axis=1)
        MarketResultsDem.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).rename(columns={0: 'Demand [MWh]', 1: 'LSRMC [EUR/MWh]'}, inplace=False).oT.write(f'{_path}/oT_Result_MarketResultsDemand_{CaseName}.csv', sep=',')

    MarketResultsGen     = pd.DataFrame()
    # Check if there are non-RES generators
    if sum(1 for nr in mTEPES.nr if nr not in mTEPES.eh):
        MarketResultsGen = pd.concat([MarketResultsGen, OutputResults01], axis=1)
    if mTEPES.re:
        MarketResultsGen = pd.concat([MarketResultsGen, OutputResults02], axis=1)
    if mTEPES.eh:
        MarketResultsGen = pd.concat([MarketResultsGen, OutputResults03], axis=1)

    OutputResults11 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,g].ub*OptModel.vGenerationInvest[p,g]() - OptModel.vTotalOutput[p,sc,n,g]())*mTEPES.pLoadLevelDuration[p,sc,n]() if g in mTEPES.re and g     in mTEPES.gc else
                                      (OptModel.vTotalOutput[p,sc,n,g].ub                                   - OptModel.vTotalOutput[p,sc,n,g]())*mTEPES.pLoadLevelDuration[p,sc,n]() if g in mTEPES.re and g not in mTEPES.gc else
                                       OptModel.vESSSpillage[p,sc,n,g]()                                                                                                             if g in mTEPES.es else 0.0 for p,sc,n,ar,nd,g in sPSNARNDG], index=pd.Index(sPSNARNDG))
    OutputResults12 = pd.Series(data=[ OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3                                         if g not in mTEPES.bo else
                                       OptModel.vTotalOutputHeat[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3                                                                    for p,sc,n,ar,nd,g in sPSNARNDG], index=pd.Index(sPSNARNDG))

    OutputResults11.index = [idx[:6] for idx in OutputResults11.index]
    OutputResults12.index = [idx[:6] for idx in OutputResults12.index]

    MarketResultsGen *= 1e3
    if MarketResultsGen.columns.duplicated().any():
        MarketResultsGen = MarketResultsGen.T.groupby(level=0).sum().T
    MarketResultsGen = pd.concat([MarketResultsGen.stack(), OutputResults11, OutputResults12], axis=1)
    MarketResultsGen.reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4','level_5']).rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Generator'], axis=0).rename(columns={0: 'Generation [MWh]', 1: 'Curtailment [MWh]', 2: 'Emissions [MtCO2]'}, inplace=False).oT.write(f'{_path}/oT_Result_MarketResultsGeneration_{CaseName}.csv', sep=',')

    # df=OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index()
    # df['AreaFin'] = df['Area']
    # df['NodeFin'] = df['Node']
    # df.pivot_table(index=['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'AreaFin', 'NodeFin'], columns='Technology', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'AreaFin', 'NodeFin'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceEnergyPerNetwork_{CaseName}.csv', index=False, sep=',')
    pScenFactor = {(p,sc): mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() for p,sc in mTEPES.ps}
    # these four yes/no questions do not depend on the area, and three of them scan a Param indexed over psng: answer them once instead of once per area
    pHasEmissionCost  = any(mTEPES.pEmissionVarCost[idx]   for idx in mTEPES.pEmissionVarCost)
    pHasLinearOMCost  = any(mTEPES.pLinearOMCost   [gg ]   for gg  in mTEPES.gg)
    pHasLinearVarCost = any(mTEPES.pLinearVarCost  [idx]() for idx in mTEPES.pLinearVarCost)
    pHasESSReserve    = any(mTEPES.pIndOperReserveGen[eh] == 0 or mTEPES.pIndOperReserveCon[eh] == 0 for eh in mTEPES.eh)
    OutputToFile = pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,nr]() * OptModel.vTotalOutput[p,sc,n,nr]() +
                                    pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,nr]   * OptModel.vCommitment [p,sc,n,nr]() +
                                    pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       nr]   * OptModel.vStartUp    [p,sc,n,nr]() +
                                    pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       nr]   * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
    if mTEPES.nr:
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCostOperation_{CaseName}.csv', sep=',')

    if mTEPES.re:
        OutputToFile = pd.Series(data=[pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput [p,sc,n,re]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCostOandM_{CaseName}.csv', sep=',')

    if mTEPES.nr and (pHasOperReserveUp or pHasOperReserveDw):
        OutputToFile = pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                        pScenFactor[p,sc] * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCostOperatingReserve_{CaseName}.csv', sep=',')

    if mTEPES.psnehc:
        OutputToFile = pd.Series(data=[     pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost[p,sc,n,eh]() * OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionCostOperation_{CaseName}.csv', sep=',')
        if pHasESSReserve:
            OutputToFile = pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                            pScenFactor[p,sc] * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionCostOperatingReserve_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,g] * OptModel.vTotalOutput[p,sc,n,g]() for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCostEmission_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost()                  * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkCostENS_{CaseName}.csv', sep=',')

    def Transformation1(df, _name):
        df = df.to_frame(name='MEUR')
        df['Cost'] = _name
        df = df.reset_index().pivot_table(index=['level_0', 'level_1', 'Cost'], values='MEUR', aggfunc='sum')
        return df

    if sum(1 for ar in mTEPES.ar if len(g2a[ar])) > 1:
        if pIndAreaOutput:
            for ar in mTEPES.ar:
                if len(g2a[ar]):
                    OutputResults1 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Operation Cost Generation'         ) for p,sc in mTEPES.ps]))
                    OutputResults2 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Operating Reserve Cost Generation' ) for p,sc in mTEPES.ps]))
                    OutputResults3 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'O&M Cost Generation'               ) for p,sc in mTEPES.ps]))
                    OutputResults4 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Operation Cost Consumption'        ) for p,sc in mTEPES.ps]))
                    OutputResults5 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Operating Reserve Cost Consumption') for p,sc in mTEPES.ps]))
                    OutputResults6 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Emission Cost'                     ) for p,sc in mTEPES.ps]))
                    OutputResults7 = pd.DataFrame(data={'MEUR': 0.0}, index=pd.Index([(p,sc,'Reliability Cost'                  ) for p,sc in mTEPES.ps]))

                    if mTEPES.nr:
                        sPSNNR = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.psnnr if nr in n2a[ar]]
                        if sPSNNR:
                            OutputResults1 =     pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,nr]() * OptModel.vTotalOutput[p,sc,n,nr]() +
                                                                  pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                                                  pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                                                  pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                            OutputResults1 =     Transformation1(OutputResults1, 'Operation Cost Generation')
                            sPSNNR = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.psnnr if nr in n2a[ar]]
                            if pHasOperReserveUp or pHasOperReserveDw:
                                OutputResults2 = pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                                                  pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                                OutputResults2 = Transformation1(OutputResults2, 'Operating Reserve Cost Generation')

                    if mTEPES.g :
                        sPSNG  = [(p,sc,n,g ) for p,sc,n,g  in mTEPES.psng  if g  in g2a[ar]]
                        if sPSNG:
                            if pHasEmissionCost:
                                OutputResults6 = pd.Series(data=[ pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,g ] * OptModel.vTotalOutput[p,sc,n,g ]() for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
                                OutputResults6 = Transformation1(OutputResults6, 'Emission Cost')

                    if mTEPES.re:
                        sPSNRE = [(p,sc,n,re) for p,sc,n,re in mTEPES.psnre if re in g2a[ar]]
                        if sPSNRE:
                            if pHasLinearOMCost:
                                OutputResults3 = pd.Series(data=[pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput   [p,sc,n,re]() for p,sc,n,re in sPSNRE], index=pd.Index(sPSNRE))
                                OutputResults3 = Transformation1(OutputResults3, 'O&M Cost Generation')

                    if mTEPES.psnehc:
                        sPSNES = [(p,sc,n,eh) for p,sc,n,eh in mTEPES.psnehc if eh in g2a[ar]]
                        if sPSNES:
                            if pHasLinearVarCost:
                                OutputResults4 = pd.Series(data=[ pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,eh]() * OptModel.vESSTotalCharge[p,sc,n,eh]()  for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                                OutputResults4 = Transformation1(OutputResults4, 'Operation Cost Consumption')
                            if pHasESSReserve:
                                OutputResults5 = pd.Series(data=[(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                                                  pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                                OutputResults5 = Transformation1(OutputResults5, 'Operating Reserve Cost Consumption')

                    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if (nd,ar) in mTEPES.ndar]
                    if sPSNND:
                        OutputResults7 =         pd.Series(data=[pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost()           * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
                        OutputResults7 =         Transformation1(OutputResults7, 'Reliability Cost')

                    OutputResults = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7]).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Scenario', 'level_2': 'Cost', 0: 'MEUR'})
                    OutputResults['MEUR/year'] = OutputResults['MEUR']
                    for p,sc in mTEPES.ps:
                        OutputResults.loc[(OutputResults['Period'] == p) & (OutputResults['Scenario'] == sc), 'MEUR/year'] = OutputResults.loc[(OutputResults['Period'] == p) & (OutputResults['Scenario'] == sc), 'MEUR'] / mTEPES.pDiscountedWeight[p] / mTEPES.pScenProb[p,sc]()
                    OutputResults.oT.write(f'{_path}/oT_Result_CostSummary_{CaseName}_{ar}.csv', sep=',', index=False)

    # tolerance to avoid division by 0
    pMinMeanOutput = 1e-10

    sPSSTNG               = [(p,sc,st,n,   g) for p,sc,st,n,   g in mTEPES.s2n*mTEPES.g   if (p,sc,n,g) in mTEPES.psng]
    sPSSTNNDG             = [(p,sc,st,n,nd,g) for p,sc,st,n,nd,g in mTEPES.s2n*mTEPES.n2g if (p,sc,n,g) in mTEPES.psng]
    # every other revenue series below leaves a zero series behind when its guard is false; these two did not, and the cost-recovery block at the end reads them whenever there are candidate units
    GenRev                = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    ChargeRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    if pHasDuals:
        OutputResults     = pd.Series(data=[ mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput   [p,sc,n,g]() for p,sc,st,n,nd,g in sPSSTNNDG], index=pd.Index(sPSSTNNDG))
        MeanOutput        = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]() for p,sc,st,n,g in sPSSTNG], index=pd.Index(sPSSTNG)).groupby(level=4).mean()
        MeanOutput        = MeanOutput.where(MeanOutput > pMinMeanOutput) * 1e-3
        OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueEnergyGeneration_{CaseName}.csv', sep=',')
        # reuse the revenue series above (dual x output) and divide it by the mean output per generator (level 5) instead of recomputing
        # every dual lookup and variable evaluation
        OutputResults     = OutputResults.div(MeanOutput, level=5)
        OutputResults.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='EUR/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCapturedSRMC_{CaseName}.csv', sep=',')

        if mTEPES.eh:
            sPSSTNES      = [(p,sc,st,n,   eh) for p,sc,st,n,   eh in mTEPES.s2n*mTEPES.eh  if (p,sc,n,eh) in mTEPES.psneh]
            sPSSTNNDEH    = [(p,sc,st,n,nd,eh) for p,sc,st,n,nd,eh in mTEPES.s2n*mTEPES.n2g if (p,sc,n,eh) in mTEPES.psneh]
            OutputResults = pd.Series(data=[-mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,st,n,nd,eh in sPSSTNNDEH], index=pd.Index(sPSSTNNDEH))
            MeanOutput    = pd.Series(data=[OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,st,n,eh in sPSSTNES], index=pd.Index(sPSSTNES)).groupby(level=4).mean()
            MeanOutput    = MeanOutput.where(MeanOutput > pMinMeanOutput) * 1e-3
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueEnergyConsumption_{CaseName}.csv', sep=',')
            # reuse the consumption revenue series above and divide it by the mean charge per consumption unit (level 5) rather than recomputing
            # all dual lookups and variable evaluations
            OutputResults = OutputResults.div(MeanOutput, level=5)
            OutputResults.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='EUR/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionCapturedSRMC_{CaseName}.csv', sep=',')

        if mTEPES.gc:
            GenRev    = []
            ChargeRev = []
            # gc units that belong to some ESS technology: the two set comprehensions below only need the yes/no answer, and asking it once per tuple over mTEPES.ot both costs and risks emitting the same tuple twice
            pGcInESSTech           = {gc for ot in mTEPES.ot for gc in o2e[ot]}
            sPSSTNNDGC1            = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in mTEPES.s2n*mTEPES.n2g if (p,sc,n,gc) in mTEPES.psngc]
            OutputToGenRev         = pd.Series(data=[mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,st,n,nd,gc in sPSSTNNDGC1], index=pd.Index(sPSSTNNDGC1))
            GenRev.append(OutputToGenRev)
            sPSSTNNDGC2            = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1 if (p,sc,n,gc) in mTEPES.psngc and gc in pGcInESSTech]
            if sPSSTNNDGC2:
                OutputChargeRevESS = pd.Series(data=[mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vESSTotalCharge[p,sc,n,gc]() for p,sc,st,n,nd,gc in sPSSTNNDGC2], index=pd.Index(sPSSTNNDGC2))
                ChargeRev.append(OutputChargeRevESS)
            sPSSTNNDGC3            = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1 if gc not in pGcInESSTech]
            if sPSSTNNDGC3:
                ChargeRev.append(pd.Series(0.0, index=pd.Index(sPSSTNNDGC3), dtype='float64'))
            if len(GenRev):
                GenRev    = pd.concat(GenRev)
                GenRev    = GenRev.to_frame   ('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            if len(ChargeRev):
                ChargeRev = pd.concat(ChargeRev)
                ChargeRev = ChargeRev.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)

        for gc in mTEPES.gc:
            if len(GenRev):
                GenRev   [gc] = 0.0 if gc not in GenRev.index    else GenRev   [gc]
            else:
                GenRev        = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            if len(ChargeRev):
                ChargeRev[gc] = 0.0 if gc not in ChargeRev.index else ChargeRev[gc]
            else:
                ChargeRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if (mTEPES.gc or mTEPES.gd) and sum(mTEPES.pReserveMargin[:,:]()) and pHasDuals:
        pExistingFirmCapacity = {(p, ar): sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] if (p,g) in mTEPES.pg and g not in mTEPES.gc and g not in mTEPES.gd) for p in mTEPES.p for ar in mTEPES.ar}
        sPSSTARGC             = [(p,sc,st,ar,gc) for p,sc,st,ar,gc in mTEPES.ps*mTEPES.st*mTEPES.ar*mTEPES.gc if gc in g2a[ar] and (p,gc) in mTEPES.pgc and mTEPES.pReserveMargin[p,ar]() and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if gc in g2a[ar]) and pExistingFirmCapacity[p,ar] <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]()]
        OutputToResRev        = pd.Series(data=[mTEPES.pDuals[f'eAdequacyReserveMarginElec_{p}_{sc}_{st}{ar}']*mTEPES.pRatedMaxPowerElec[gc]*mTEPES.pAvailability[gc]() for p,sc,st,ar,gc in sPSSTARGC], index=pd.Index(sPSSTARGC))
        ResRev                = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        if sPSSTARGC:
            OutputToResRev /= 1e3
            OutputToResRev  = OutputToResRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1'], columns='level_4', values='MEUR').rename_axis(['Stages', 'Areas'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            for g in OutputToResRev.index:
                ResRev[g] = OutputToResRev[g]
    else:
        ResRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if pHasOperReserveUp and pHasReserveOffer and pHasDuals:
        sPSSTNARNR        = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.s2n*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,nr) in mTEPES.psnnr]
        if sPSSTNARNR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveUp   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueGenOperatingReserveUp_{CaseName}.csv', sep=',')

        sPSSTNARES        = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.s2n*mTEPES.ar*mTEPES.eh if eh in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,eh) in mTEPES.psnehc]
        if sPSSTNARES:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueConOperatingReserveUp_{CaseName}.csv', sep=',')

        sPSSTNAREC        = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.s2n*mTEPES.ar*mTEPES.ec if ec in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,ec) in mTEPES.psnec]
        if sPSSTNAREC:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*(OptModel.vReserveUp[p,sc,n,ec]()+OptModel.vESSReserveUp[p,sc,n,ec]()) for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
            OutputToUpRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        else:
            OutputToUpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        UpRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        for g in OutputToUpRev.index:
            UpRev[g] = OutputToUpRev[g]
    else:
        UpRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if pHasOperReserveDw and pHasReserveOffer and pHasDuals:
        sPSSTNARNR        = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.s2n*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,nr) in mTEPES.psnnr]
        if sPSSTNARNR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueGenOperatingReserveDown_{CaseName}.csv', sep=',')

        sPSSTNARES        = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.s2n*mTEPES.ar*mTEPES.eh if eh in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,eh) in mTEPES.psnehc]
        if sPSSTNARES:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueConOperatingReserveDown_{CaseName}.csv', sep=',')

        sPSSTNAREC        = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.s2n*mTEPES.ar*mTEPES.ec if ec in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and pRsrvOfferArea[p,ar] and (p,sc,n,ec) in mTEPES.psnec]
        if sPSSTNAREC:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"]/mTEPES.pPeriodProb[p,sc]()*(OptModel.vReserveDown[p,sc,n,ec]()+OptModel.vESSReserveDown[p,sc,n,ec]()) for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
            OutputToDwRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        else:
            OutputToDwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        DwRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        for g in OutputToDwRev.index:
            DwRev[g] = OutputToDwRev[g]
    else:
        DwRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    # the ramp reserve requirement depends on (p,sc,n) only: summing it again for every unit costs |nr| (or |ec|) times more than it should
    if mTEPES.pIndRampReserves() and pHasRampReserveUp and pHasDuals:
        pRampReserveUpPSN = {(p,sc,n): sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) for p,sc,n in mTEPES.psn}
        sPSSTNNR          = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if pRampReserveUpPSN[p,sc,n] and (p,sc,n,nr) in mTEPES.psnnr]
        if sPSSTNNR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampUp_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveUp[p,sc,n,nr]() for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueRampReserveUp_{CaseName}.csv', sep=',')

        # if len([(p,sc,n,eh)                 for p,sc,   n,eh in mTEPES.psneh         if sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) and (p,sc,n,eh) in mTEPES.psnehc]):
        #     sPSSTNES      = [(p,sc,st,n,eh) for p,sc,st,n,eh in mTEPES.s2n*mTEPES.eh if sum(mTEPES.pRampReserveUp[p,sc,n,ar] for ar in mTEPES.ar) and (p,sc,n,eh) in mTEPES.psnehc]
        #     OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampUp_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveUp[p,sc,n,eh]() for p,sc,st,n,eh in sPSSTNES], index=pd.Index(sPSSTNES))
        #     OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueRampReserveUpESS_{CaseName}.csv', sep=',')

        sPSSTNEC          = [(p,sc,st,n,ec) for p,sc,st,n,ec in mTEPES.s2n*mTEPES.ec if pRampReserveUpPSN[p,sc,n] and (p,sc,n,ec) in mTEPES.psnec]
        if sPSSTNEC:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampUp_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveUp[p,sc,n,ec]() for p,sc,st,n,ec in sPSSTNEC], index=pd.Index(sPSSTNEC), dtype='float64')
            if len(OutputResults):
                OutputToUpRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            else:
                OutputToUpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            RampUpRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

            for g in OutputToUpRev.index:
                RampUpRev[g] = OutputToUpRev[g]
        else:
            RampUpRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        RampUpRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if mTEPES.pIndRampReserves() and pHasRampReserveDw and pHasDuals:
        pRampReserveDwPSN = {(p,sc,n): sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) for p,sc,n in mTEPES.psn}
        sPSSTNNR          = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if pRampReserveDwPSN[p,sc,n] and (p,sc,n,nr) in mTEPES.psnnr]
        if sPSSTNNR:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampDw_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveDw[p,sc,n,nr]() for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_RevenueRampReserveDw_{CaseName}.csv', sep=',')

        # if len([(p,sc,n,eh)                 for p,sc,   n,eh in mTEPES.psneh         if sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) and (p,sc,n,eh) in mTEPES.psnehc]):
        #     sPSSTNES      = [(p,sc,st,n,eh) for p,sc,st,n,eh in mTEPES.s2n*mTEPES.eh if sum(mTEPES.pRampReserveDw[p,sc,n,ar] for ar in mTEPES.ar) and (p,sc,n,eh) in mTEPES.psnehc]
        #     OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampDw_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveDw[p,sc,n,eh]() for p,sc,st,n,eh in sPSSTNES], index=pd.Index(sPSSTNES))
        #     OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueRampReserveDwESS_{CaseName}.csv', sep=',')

        sPSSTNEC          = [(p,sc,st,n,ec) for p,sc,st,n,ec in mTEPES.s2n*mTEPES.ec if pRampReserveDwPSN[p,sc,n] and (p,sc,n,ec) in mTEPES.psnec]
        if sPSSTNEC:
            OutputResults = pd.Series(data=[mTEPES.pDuals[f"eSystemRampDw_{p}_{sc}_{st}{n}"]/mTEPES.pPeriodProb[p,sc]()*OptModel.vRampReserveDw[p,sc,n,ec]() for p,sc,st,n,ec in sPSSTNEC], index=pd.Index(sPSSTNEC), dtype='float64')
            if len(OutputResults):
                OutputToDwRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            else:
                OutputToDwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            RampDwRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

            for g in OutputToDwRev.index:
                RampDwRev[g] = OutputToDwRev[g]
        else:
            RampDwRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        RampDwRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if mTEPES.gc:
        GenCost = pd.Series(data=[sum(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,gc]() * OptModel.vTotalOutput   [p,sc,n,gc]() +
                                      pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,gc]   * OptModel.vCommitment    [p,sc,n,gc]() +
                                      pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       gc]   * OptModel.vStartUp       [p,sc,n,gc]() +
                                      pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       gc]   * OptModel.vShutDown      [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) if  gc in mTEPES.nr else
                                  sum(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,gc]() * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        EmsCost = pd.Series(data=[sum(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,gc]   * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        OpGCost = pd.Series(data=[sum(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       gc]   * OptModel.vReserveUp     [p,sc,n,gc]() +
                                      pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       gc]   * OptModel.vReserveDown   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) if  gc in mTEPES.nr else
                                  0.0                                                                                                                                                                                                 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        CnsCost = pd.Series(data=[sum(pScenFactor[p,sc] * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,ec]() * OptModel.vESSTotalCharge[p,sc,n,ec]() for p,sc,n in mTEPES.psn if (p,ec) in mTEPES.pec) for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64')
        OpCCost = pd.Series(data=[sum(pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       ec]   * OptModel.vESSReserveUp  [p,sc,n,ec]() +
                                      pScenFactor[p,sc] * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       ec]   * OptModel.vESSReserveDown[p,sc,n,ec]() for p,sc,n in mTEPES.psn if (p,ec) in mTEPES.pec) for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64')

        for gc in mTEPES.gc:
            CnsCost[gc] = 0.0 if gc not in CnsCost.index else CnsCost[gc]
            OpCCost[gc] = 0.0 if gc not in OpCCost.index else OpCCost[gc]

        InvCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p in mTEPES.p if (p,gc) in mTEPES.pgc)                 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        Balance = pd.Series(data=[GenRev[gc]+ChargeRev[gc]+UpRev[gc]+DwRev[gc]+RampUpRev[gc]+RampDwRev[gc]+ResRev[gc]-GenCost[gc]-EmsCost[gc]-OpGCost[gc]-CnsCost[gc]-OpCCost[gc]-InvCost[gc] for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        CostRecovery = pd.concat([GenRev,ChargeRev,UpRev,DwRev,RampUpRev,RampDwRev,ResRev,-GenCost,-EmsCost,-OpGCost,-CnsCost,-OpCCost,-InvCost,Balance], axis=1, keys=['Revenue generation [MEUR]', 'Revenue consumption [MEUR]', 'Revenue operating reserve up [MEUR]', 'Revenue operating reserve down [MEUR]', 'Revenue ramp reserve up [MEUR]', 'Revenue ramp reserve down [MEUR]', 'Revenue reserve margin [MEUR]', 'Cost operation generation [MEUR]', 'Cost emission [MEUR]', 'Cost operating reserves generation [MEUR]', 'Cost operation consumption [MEUR]', 'Cost operating reserves consumption [MEUR]', 'Cost investment [MEUR]', ' Total [MEUR]'])
        CostRecovery.stack().to_frame(name='MEUR').reset_index().pivot_table(values='MEUR', index=['level_1'], columns=['level_0']).rename_axis([None], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_CostRecovery_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing              economic results  ... ', round(WritingResultsTime), 's')
