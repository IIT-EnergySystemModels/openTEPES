"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Investment and retirement results.

This module writes the expansion-planning decisions: generation and storage
build-out, generation retirements, and transmission line investment. It
reports them per unit, per technology, and per area, with investment cost,
LCOE, and cost-per-MW tables, plus optional Altair plots.
"""

import time
import os
import pandas            as     pd
import altair            as     alt
from   collections       import defaultdict

try:
    from .openTEPES_OutputResultsCommon import _outdir
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir


# @profile
def InvestmentResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    #%% outputting the investment decisions
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    if mTEPES.eb:

        # generators to area (g2a)
        g2a = defaultdict(list)
        for ar,eb in mTEPES.ar*mTEPES.eb:
            if (ar,eb) in mTEPES.a2g:
                g2a[ar].append(eb)

        # tolerance to avoid division by 0
        pEpsilon = 1e-6

        # Saving generation investments
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,eb]()                                                               for p,eb in mTEPES.peb], index=mTEPES.peb)
        OutputToFile = OutputToFile.fillna(0).to_frame(name='InvestmentDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generator'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generator'], values='InvestmentDecision').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationInvestmentPerUnit_{CaseName}.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generator'])

        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,eb]()*max(mTEPES.pRatedMaxPowerElec[eb],mTEPES.pRatedMaxCharge[eb]) for p,eb in mTEPES.peb], index=mTEPES.peb)
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generator'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generator'], values='MW').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationInvestment_{CaseName}.csv', index=True, sep=',')
            OutputToFile.pivot_table(index=['Period', 'Generator'], values='MW').rename_axis(['Period', 'Generator'], axis=0).rename(columns={'MW': 'Power [MW]'}, inplace=False).to_csv(f'{_path}/oT_Result_MarketResultsGenerationInvestment_{CaseName}.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generator'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput:
                sPAREB           = [(p,ar,eb) for p,ar,eb in mTEPES.par*mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2a[ar]]
                GenInvestToArea  = pd.Series(data=[OutputToFile['MW'][p,eb] for p,ar,eb in sPAREB], index=pd.Index(sPAREB)).to_frame(name='MW')
                GenInvestToArea.index.names = ['Period', 'Area', 'Generator']
                chart = alt.Chart(GenInvestToArea.reset_index()).mark_bar().encode(x='Generator:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_GenerationInvestmentPerArea_{CaseName}.html', embed_options={'renderer':'svg'})
                TechInvestToArea = pd.Series(data=[sum(OutputToFile['MW'][p,eb] for eb in mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2t[gt] and eb in g2a[ar]) for p,ar,gt in mTEPES.par*mTEPES.gt], index=mTEPES.par*mTEPES.gt).to_frame(name='MW')
                TechInvestToArea.index.names = ['Period', 'Area', 'Technology']
                chart = alt.Chart(TechInvestToArea.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestmentPerArea_{CaseName}.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment decision
            OutputResults1 = pd.Series(data=[gt for p,eb,gt in mTEPES.peb*mTEPES.gt if (p,eb) in mTEPES.peb and eb in g2t[gt]], index=mTEPES.peb)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generator']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyInvestment_{CaseName}.csv', index=True, sep=',')

            MarketResultsInv = pd.DataFrame()
            MarketResultsInv = pd.concat([MarketResultsInv, OutputResults], axis=1)

            if pIndPlotOutput:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestment_{CaseName}.html', embed_options={'renderer':'svg'})

            # Saving and plotting generation investment cost
            OutputResults0 = OutputResults
            OutputToFile   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[eb] * OptModel.vGenerationInvest[p,eb]() for p,eb in mTEPES.peb], index=mTEPES.peb)
            OutputToFile   = OutputToFile.fillna(0).to_frame(name='MEUR').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generator'}).set_index(['Period', 'Generator'])

            OutputResults1 = pd.Series(data=[gt for p,eb,gt in mTEPES.peb*mTEPES.gt if eb in g2t[gt]], index=mTEPES.peb)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generator']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MEUR'] = round(OutputResults['MEUR'], 2)

            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyInvestmentCost_{CaseName}.csv', index=True, sep=',')

            MarketResultsInv  = pd.concat([MarketResultsInv, OutputResults], axis=1)

            GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[eb]           * OptModel.vGenerationInvest[p,eb]() for      eb in                    mTEPES.eb if eb in g2t[gt] and (p,     eb) in mTEPES.peb  ) for p,gt in mTEPES.p*mTEPES.gt], index=mTEPES.p*mTEPES.gt)
            GenTechInvestCost *= 1e3
            GenTechInjection  = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutput[p,sc,n,eb]() for sc,n,eb in mTEPES.sc*mTEPES.n*mTEPES.eb if eb in g2t[gt] and (p,sc,n,eb) in mTEPES.psneb) for p,gt in mTEPES.p*mTEPES.gt], index=mTEPES.p*mTEPES.gt)
            GenTechInjection.name = 'Generation'
            MarketResultsInv  = pd.concat([MarketResultsInv, GenTechInjection], axis=1)
            LCOE = GenTechInvestCost.div(GenTechInjection)
            LCOE.name = 'LCOE'
            MarketResultsInv = pd.concat([MarketResultsInv, LCOE], axis=1)
            MarketResultsInv.stack().reset_index().pivot_table(index=['level_0','level_1'], columns='level_2', values=0, aggfunc='sum').rename_axis(['Period', 'Technology'], axis=0).rename(columns={'MW': 'Power [MW]', 'MEUR': 'Cost [MEUR]', 'Generation': 'Generation [GWh]', 'LCOE': 'LCOE [EUR/MWh]'}, inplace=False).to_csv(f'{_path}/oT_Result_MarketResultsTechnologyInvestment_{CaseName}.csv', sep=',')

            if pIndPlotOutput:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestmentCost_{CaseName}.html', embed_options={'renderer':'svg'})

            sPGT = [(p,gt) for p,gt in mTEPES.p*mTEPES.gt if sum(1 for eb in mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2t[gt])]
            OutputResults = pd.Series(data=[OutputResults['MEUR'][p,gt]/(OutputResults0['MW'][p,gt]+pEpsilon) for p,gt in sPGT], index=pd.Index(sPGT)).to_frame(name='MEUR/MW')
            OutputResults.reset_index().pivot_table(index=['level_0'], columns='level_1', values='MEUR/MW').rename_axis(['Period'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyInvestmentCostPerMW_{CaseName}.csv', index=True, sep=',')

            if pIndPlotOutput:
                chart = alt.Chart(OutputResults.reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Technology'})).mark_bar().encode(x='Technology:O', y='sum(MEUR/MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestmentCostPerMW_{CaseName}.html', embed_options={'renderer':'svg'})

    if mTEPES.gd:

        # generators to area (g2a)
        g2a = defaultdict(list)
        for ar,gd in mTEPES.ar*mTEPES.gd:
            if (ar,gd) in mTEPES.a2g:
                g2a[ar].append(gd)

        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            # Saving generation retirement
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()                                                               for p,gd in mTEPES.pgd], index=mTEPES.pgd)
            OutputToFile = OutputToFile.fillna(0).to_frame(name='RetirementDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generator'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generator'], values='RetirementDecision').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationRetirementPerUnit_{CaseName}.csv', index=True, sep=',')
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()*max(mTEPES.pRatedMaxPowerElec[gd],mTEPES.pRatedMaxCharge[gd]) for p,gd in mTEPES.pgd], index=mTEPES.pgd)
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0).to_frame(name='MW'                ).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generator'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generator'], values='MW').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationRetirement_{CaseName}.csv', index=True, sep=',')
            OutputToFile = OutputToFile.set_index(['Period', 'Generator'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput:
                sPARGD           = [(p,ar,gd) for p,ar,gd in mTEPES.par*mTEPES.gd if (p,gd) in mTEPES.pgd and gd in g2a[ar]]
                GenRetireToArea  = pd.Series(data=[OutputToFile['MW'][p,gd] for p,ar,gd in sPARGD], index=pd.Index(sPARGD)).to_frame(name='MW')
                GenRetireToArea.index.names = ['Period', 'Area', 'Generator']
                chart = alt.Chart(GenRetireToArea.reset_index()).mark_bar().encode(x='Generator:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_GenerationRetirementPerArea_{CaseName}.html', embed_options={'renderer':'svg'})
                TechRetireToArea = pd.Series(data=[sum(OutputToFile['MW'][p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd and gd in g2t[gt] and gd in g2a[ar]) for p,ar,gt in mTEPES.par*mTEPES.gt], index=mTEPES.par*mTEPES.gt).to_frame(name='MW')
                TechRetireToArea.index.names = ['Period', 'Area', 'Technology'    ]
                chart = alt.Chart(TechRetireToArea.reset_index()).mark_bar().encode(x='Technology:O',     y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyRetirementPerArea_{CaseName}.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment retirement
            OutputResults1 = pd.Series(data=[gt for p,gd,gt in mTEPES.pgd*mTEPES.gt if gd in g2t[gt]], index=mTEPES.pgd)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generator']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis([None], axis=0).to_csv(f'{_path}/oT_Result_TechnologyRetirement_{CaseName}.csv', sep=',', index=False)

            if pIndPlotOutput:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyRetirement_{CaseName}.html', embed_options={'renderer':'svg'})

    if mTEPES.lc:

        # Saving investment decisions
        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
        OutputToFile = OutputToFile.fillna(0).to_frame(name='Investment Decision').rename_axis(['Period', 'InitialNode', 'FinalNode', 'Circuit'], axis=0)
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='Investment Decision').rename_axis([None, None, None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkInvestmentPerUnit_{CaseName}.csv', index=False, sep=',')
        # OutputToFile = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])

        # Ordering data to plot the investment decision
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=mTEPES.plc)
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.reset_index().set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['Investment Decision'] = round(OutputResults['Investment Decision'], 2)

        if pIndPlotOutput:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(Investment Decision):Q', color='LineType:N', column='Period:N').properties(width=600, height=400)
            chart.save(f'{_path}/oT_Plot_NetworkInvestment_{CaseName}.html', embed_options={'renderer':'svg'})

        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineNTCFrw[ni,nf,cc]*mTEPES.pLineLength[ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MWkm').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'InitialNode', 'level_2': 'FinalNode', 'level_3': 'Circuit'})
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='MWkm').rename_axis([None,None,None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkInvestmentMWkm_{CaseName}.csv', index=False, sep=',')

        # Ordering data to plot the investment decision per kilometer
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=mTEPES.plc)
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['MWkm'] = round(OutputResults['MWkm'], 2)

        if pIndPlotOutput:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(MWkm):Q', color='LineType:N', column='Period:N')
            chart.save(f'{_path}/oT_Plot_NetworkInvestmentMWkm_{CaseName}.html', embed_options={'renderer':'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing            investment results  ... ', round(WritingResultsTime), 's')
