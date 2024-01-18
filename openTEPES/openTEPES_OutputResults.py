"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 18, 2024
"""

import time
import os
import math
import pandas            as     pd
import altair            as     alt
import plotly.io         as     pio
import plotly.graph_objs as     go
from   collections       import defaultdict
from   pyomo.environ     import Set
from   colour            import Color


# Definition of Pie plots
def PiePlots(period, scenario, df, Category, Value):
    df                    = df.reset_index()
    df                    = df.loc[(df['level_0'] == period) & (df['level_1'] == scenario)]
    df                    = df.set_index(['level_0','level_1','level_2','level_3'])
    OutputToPlot          = df.reset_index().groupby(['level_3']).sum(numeric_only=True)
    OutputToPlot['%']     = (OutputToPlot[0] / OutputToPlot[0].sum()) * 100.0
    OutputToPlot          = OutputToPlot.reset_index().rename(columns={'level_3': Category, 0: 'GWh'})
    OutputToPlot['GWh']   = round(OutputToPlot['GWh'], 1)
    OutputToPlot['%'  ]   = round(OutputToPlot['%'  ], 1)
    OutputToPlot          = OutputToPlot[(OutputToPlot[['GWh']] != 0).all(axis=1)]
    OutputToPlot['Label'] = [OutputToPlot[Category][i] + ' (' + str(OutputToPlot['%'][i]) + ' %' + ', ' + str(OutputToPlot['GWh'][i]) + ' GWh' + ')' for i in OutputToPlot.index]
    ComposedCategory      = Category+':N'
    ComposedValue         = Value   +':Q'

    base  = alt.Chart(OutputToPlot).encode(theta=alt.Theta(ComposedValue, stack=True), color=alt.Color(ComposedCategory, legend=alt.Legend(title=Category))).properties(width=800, height=800)
    pie   = base.mark_arc(outerRadius=240)
    text  = base.mark_text(radius=340, size=15).encode(text='Label:N')
    chart = pie+text

    return chart


# Definition of Area plots
def AreaPlots(period, scenario, df, Category, X, Y, OperationType):
    Results = df.loc[period,scenario,:,:]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # Change the format of the LoadLevel
    Results[X] = Results[X].str[:14]
    Results[X] = (Results[X]+'+01:00')
    Results[X] = (str(period)+'-'+Results[X])
    Results[X] = pd.to_datetime(Results[X])
    Results[X] = Results[X].dt.strftime('%Y-%m-%d %H:%M:%S')
    # Composed Names
    C_C = Category+':N'

    C_X = X+':T'
    C_Y = Y+':Q'
    # Define and build the chart
    # alt.data_transformers.enable('json')
    alt.data_transformers.disable_max_rows()
    interval = alt.selection_interval(encodings=['x'])
    selection = alt.selection_point(fields=[Category], bind='legend')

    base  = alt.Chart(Results).mark_area().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2))).add_params(selection)
    chart = base.encode(alt.X(C_X, axis=alt.Axis(title='')).scale(domain=interval)).properties(width=1200, height=450)
    view  = base.add_params(interval).properties(width=1200, height=50)
    plot  = alt.vconcat(chart, view)

    return plot


# Definition of Line plots
def LinePlots(period, scenario, df, Category, X, Y, OperationType):
    Results = df.loc[period,scenario,:,:].rename_axis(['level_0', 'level_1'], axis=0)
    Results.columns = [0]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # Change the format of the LoadLevel
    Results[X] = Results[X].str[:14]
    Results[X] = (Results[X]+'+01:00')
    Results[X] = (str(period)+'-'+Results[X])
    Results[X] = pd.to_datetime(Results[X])
    Results[X] = Results[X].dt.strftime('%Y-%m-%d %H:%M:%S')
    # Composed Names
    C_C = Category+':N'

    C_X = X+':T'
    C_Y = Y+':Q'
    # Define and build the chart
    # alt.data_transformers.enable('json')
    alt.data_transformers.disable_max_rows()
    interval = alt.selection_interval(encodings=['x'])
    selection = alt.selection_point(fields=[Category], bind='legend')

    base  = alt.Chart(Results).mark_line().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2))).add_params(selection)
    chart = base.encode(alt.X(C_X, axis=alt.Axis(title='')).scale(domain=interval)).properties(width=1200, height=450)
    view  = base.add_params(interval).properties(width=1200, height=50)
    plot  = alt.vconcat(chart, view)

    return plot


def InvestmentResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    #%% outputting the investment decisions
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.gc):

        # generators to area (g2a)
        g2a = defaultdict(list)
        for ar,gc in mTEPES.ar*mTEPES.gc:
            if (ar,gc) in mTEPES.a2g:
                g2a[ar].append(gc)

        # Saving generation investment into CSV file
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,gc]()                                                           for p,gc in mTEPES.pgc], index=pd.Index(mTEPES.pgc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='InvestmentDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='InvestmentDecision').rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_GenerationInvestmentPerUnit_'+CaseName+'.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,gc]()*max(mTEPES.pRatedMaxPower[gc],mTEPES.pRatedMaxCharge[gc]) for p,gc in mTEPES.pgc], index=pd.Index(mTEPES.pgc))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW'                ).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW'                ).rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_GenerationInvestment_'       +CaseName+'.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput == 1:
                sPARGC           = [(p,ar,gc) for p,ar,gc in mTEPES.par*mTEPES.gc if (ar,gc) in mTEPES.a2g]
                GenInvestToArea  = pd.Series(data=[OutputToFile['MW'][p,gc] for p,ar,gc in sPARGC], index=pd.Index(sPARGC)).to_frame(name='MW')
                GenInvestToArea.index.names = ['Period', 'Area', 'Generating unit']
                chart = alt.Chart(GenInvestToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_GenerationInvestmentPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})
                TechInvestToArea = pd.Series(data=[sum(OutputToFile['MW'][p,gc] for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g if (gt,gc) in mTEPES.t2g) for p,ar,gt in mTEPES.par*mTEPES.gt], index=pd.Index(mTEPES.par*mTEPES.gt)).to_frame(name='MW')
                TechInvestToArea.index.names = ['Period', 'Area', 'Technology'    ]
                chart = alt.Chart(TechInvestToArea.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyInvestmentPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment decision
            OutputResults1 = pd.Series(data=[gt for p,gc,gt in mTEPES.pgc*mTEPES.gt if (gt,gc) in mTEPES.t2g], index=pd.Index(mTEPES.pgc))
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_TechnologyInvestment_'+CaseName+'.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

            # Saving and plotting generation investment cost into CSV file
            OutputResults0 = OutputResults
            OutputToFile   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.pgc], index=pd.Index(mTEPES.pgc))
            OutputToFile   = OutputToFile.fillna(0).to_frame(name='MEUR').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'}).set_index(['Period', 'Generating unit'])

            OutputResults1 = pd.Series(data=[gt for p,gc,gt in mTEPES.pgc*mTEPES.gt if (gt,gc) in mTEPES.t2g], index=pd.Index(mTEPES.pgc))
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MEUR'] = round(OutputResults['MEUR'], 2)

            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR').rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_TechnologyInvestmentCost_'+CaseName+'.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyInvestmentCost_'+CaseName+'.html', embed_options={'renderer':'svg'})

            OutputResults = pd.Series(data=[OutputResults['MEUR'][p,gc]/OutputResults0['MW'][p,gc] for p,gc in OutputResults.index], index=pd.Index(list(OutputResults.index))).to_frame(name='MEUR/MW')
            OutputResults.rename_axis(['Period','Technology'], axis=0).reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR/MW').to_csv(_path+'/oT_Result_TechnologyInvestmentCostPerMW_'+CaseName+'.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR/MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyInvestmentCostPerMW_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.gd):

        # generators to area (g2a)
        g2a = defaultdict(list)
        for ar,gd in mTEPES.ar*mTEPES.gd:
            if (ar,gd) in mTEPES.a2g:
                g2a[ar].append(gd)

        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            # Saving generation retirement into CSV file
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()                                                           for p,gd in mTEPES.pgd], index=pd.Index(mTEPES.pgd))
            OutputToFile = OutputToFile.fillna(0).to_frame(name='RetirementDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='RetirementDecision').rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_GenerationRetirementPerUnit_'+CaseName+'.csv', index=True, sep=',')
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()*max(mTEPES.pRatedMaxPower[gd],mTEPES.pRatedMaxCharge[gd]) for p,gd in mTEPES.pgd], index=pd.Index(mTEPES.pgd))
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0).to_frame(name='MW'                ).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW').rename_axis(['Period'], axis=0).to_csv(_path+'/oT_Result_GenerationRetirement_'+CaseName+'.csv', index=True, sep=',')
            OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput == 1:
                sPARGD           = [(p,ar,gd) for p,ar,gd in mTEPES.par*mTEPES.gd if (ar,gd) in mTEPES.a2g]
                GenRetireToArea  = pd.Series(data=[OutputToFile['MW'][p,gd] for p,ar,gd in sPARGD], index=pd.Index(sPARGD)).to_frame(name='MW')
                GenRetireToArea.index.names = ['Period', 'Area', 'Generating unit']
                chart = alt.Chart(GenRetireToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_GenerationRetirementPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})
                TechRetireToArea = pd.Series(data=[sum(OutputToFile['MW'][p,gd] for gd in mTEPES.gd if (ar,gd) in mTEPES.a2g if (gt,gd) in mTEPES.t2g) for p,ar,gt in mTEPES.par*mTEPES.gt], index=pd.Index(mTEPES.par*mTEPES.gt)).to_frame(name='MW')
                TechRetireToArea.index.names = ['Period', 'Area', 'Technology'    ]
                chart = alt.Chart(TechRetireToArea.reset_index()).mark_bar().encode(x='Technology:O',     y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyRetirementPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment retirement
            OutputResults1 = pd.Series(data=[gt for p,gd,gt in mTEPES.pgd*mTEPES.gt if (gt,gd) in mTEPES.t2g], index=pd.Index(mTEPES.pgd))
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_TechnologyRetirement_'+CaseName+'.csv', sep=',', index=False)

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyRetirement_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.lc):

        # Saving investment decisions
        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=pd.Index(mTEPES.plc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='Investment Decision').rename_axis(['Period', 'InitialNode', 'FinalNode', 'Circuit'], axis=0)
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='Investment Decision').rename_axis([None, None, None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(_path+'/oT_Result_NetworkInvestment_'+CaseName+'.csv', index=False, sep=',')
        # OutputToFile = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])

        # Ordering data to plot the investment decision
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.plc))
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.reset_index().set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['Investment Decision'] = round(OutputResults['Investment Decision'], 2)

        if pIndPlotOutput == 1:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(Investment Decision):Q', color='LineType:N', column='Period:N').properties(width=600, height=400)
            chart.save(_path+'/oT_Plot_NetworkInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineNTCFrw[ni,nf,cc]/mTEPES.pLineLength[ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=pd.Index(mTEPES.plc))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW-km').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'InitialNode', 'level_2': 'FinalNode', 'level_3': 'Circuit'})
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='MW-km').rename_axis([None,None,None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(_path+'/oT_Result_NetworkInvestment_MWkm_'+CaseName+'.csv', index=False, sep=',')

        # Ordering data to plot the investment decision per kilometer
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.plc))
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['MW-km'] = round(OutputResults['MW-km'], 2)

        if pIndPlotOutput == 1:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(MW-km):Q', color='LineType:N', column='Period:N')
            chart.save(_path+'/oT_Plot_NetworkInvestment_MW-km_'+CaseName+'.html', embed_options={'renderer':'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing           investment results   ... ', round(WritingResultsTime), 's')


def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to area (n2a)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)

    # generators to area (g2a)
    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    # technology to generators (o2e) (g2n)
    o2e = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            o2e[ot].append(es)
    g2n = defaultdict(list)
    for gt,nr in mTEPES.gt*mTEPES.nr:
        if (gt,nr) in mTEPES.t2g:
            g2n[gt].append(nr)

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    if len(mTEPES.nr):
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[OptModel.vCommitment[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCommitment_'+CaseName+'.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vStartUp   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationStartUp_'   +CaseName+'.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vShutDown  [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationShutDown_'  +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[:,:,:,:]):
        if len(mTEPES.nr):
            OutputToFile = pd.Series(data=[OptModel.vReserveUp     [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveUp_'+CaseName+'.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                sPSNGT       = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for nr in g2n[gt])]
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in g2n[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOperatingReserveUp_'+CaseName+'.csv', sep=',')

        if len(mTEPES.eh):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psneh))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ConsumptionReserveUp_'+CaseName+'.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                sPSNOT       = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for es in o2e[ot])]
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot]) for p,sc,n,ot in sPSNOT], index=pd.Index(sPSNOT))
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOperatingReserveUpESS_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[:,:,:,:]):
        if len(mTEPES.nr):
            OutputToFile = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveDown_'+CaseName+'.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                sPSNGT       = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for nr in g2n[gt])]
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in g2n[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOperatingReserveDown_'+CaseName+'.csv', sep=',')

        if len(mTEPES.eh):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psneh))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ConsumptionReserveDown_'       +CaseName+'.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                sPSNOT       = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for es in o2e[ot])]
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot]) for p,sc,n,ot in sPSNOT], index=pd.Index(sPSNOT))
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOperatingReserveDownESS_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]()                                             for p,sc,n,g  in mTEPES.psng ], index=pd.Index(mTEPES.psng))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'],        columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_Generation_'       +CaseName+'.csv', sep=',')

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    sPSNG        = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pEpsilon]
    OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]()) for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
    OutputToFile *= 1e3
    for p,sc,n,g in sPSNG:
        if g in mTEPES.gc:
            OutputToFile[p,sc,n,g] *= OptModel.vGenerationInvest[p,g]()
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationSurplus_'+CaseName+'.csv', sep=',')

    OutputResults = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.ps*mTEPES.s2n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first()]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))[n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampUp[nr]*(mTEPES.pInitialUC[p,sc,n,nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.ps*mTEPES.s2n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first()]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))[n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampUp[nr]*(mTEPES.pInitialUC[p,sc,n,nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    OutputResults = pd.concat(OutputResults)
    if len(OutputResults.index):
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationRampUpSurplus_'+CaseName+'.csv', sep=',')

    OutputResults = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.ps*mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first()]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))[n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampDw[nr]*(mTEPES.pInitialUC[p,sc,n,nr]() - OptModel.vShutDown[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.ps*mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first()]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))[n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampDw[nr]*(mTEPES.pInitialUC[p,sc,n,nr]() - OptModel.vShutDown[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    OutputResults = pd.concat(OutputResults)
    if len(OutputResults.index):
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationRampDwSurplus_'+CaseName+'.csv', sep=',')

    if len(mTEPES.re) and len(mTEPES.rt):
        OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,re in mTEPES.psnre], index=pd.Index(mTEPES.psnre))
        OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub                                     )*mTEPES.pLoadLevelDuration[n]() for p,sc,n,re in mTEPES.psnre], index=pd.Index(mTEPES.psnre))
        for p,sc,n,re in mTEPES.psnre:
            if re in mTEPES.gc:
                OutputToFile1[p,sc,n,re] *= OptModel.vGenerationInvest[p,re]()
                OutputToFile2[p,sc,n,re] *= OptModel.vGenerationInvest[p,re]()
        OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
            OutputToFile.to_csv(_path+'/oT_Result_GenerationCurtailmentEnergyRelative_'+CaseName+'.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,re] for re in mTEPES.re if (rt,re) in mTEPES.t2g) for p,sc,rt in mTEPES.psrt], index=pd.Index(mTEPES.psrt))
            OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,re] for re in mTEPES.re if (rt,re) in mTEPES.t2g) for p,sc,rt in mTEPES.psrt], index=pd.Index(mTEPES.psrt))
            OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile  = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='%').rename_axis(['Period', 'Scenario', 'Technology'], axis=0).to_csv(_path+'/oT_Result_TechnologyCurtailmentEnergyRelative_'+CaseName+'.csv', index=True, sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub - OptModel.vTotalOutput[p,sc,n,re]())  for p,sc,n,re in mTEPES.psnre], index=pd.Index(mTEPES.psnre))
        OutputToFile *= 1e3
        for p,sc,n,re in mTEPES.psnre:
            if re in mTEPES.gc:
                OutputToFile[p,sc,n,re] *= OptModel.vGenerationInvest[p,re]()
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCurtailmentOutput_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,re in mTEPES.psnre], index=pd.Index(mTEPES.psnre))
        for p,sc,n,re in mTEPES.psnre:
            if re in mTEPES.gc:
                OutputToFile[p,sc,n,re] *= OptModel.vGenerationInvest[p,re]()
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCurtailmentEnergy_'+CaseName+'.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,re] for re in mTEPES.re if (rt,re) in mTEPES.t2g) for p,sc,n,rt in mTEPES.psnrt], index=pd.Index(mTEPES.psnrt))
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(               index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCurtailmentEnergy_'+CaseName+'.csv', sep=',')
            if pIndPlotOutput == 1:
                TechCurt = OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'GWh'})
                TechCurt = TechCurt[(TechCurt[['GWh']] != 0).all(axis=1)]
                chart = alt.Chart(TechCurt.reset_index()).mark_bar().encode(x='Technology', y='GWh', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                chart.save(_path+'/oT_Plot_TechnologyCurtailmentEnergy_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(      index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEnergy_'+CaseName+'.csv', sep=',')

    if len(mTEPES.nr):
        OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,nr]()*mTEPES.pLoadLevelDuration[n]()*mTEPES.pEmissionRate[nr]/1e3 for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEmission_'+CaseName+'.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            if sum(1 for ar in mTEPES.ar if sum(1 for nr in n2a[ar])) > 1:
                if pIndAreaOutput == 1:
                    for ar in mTEPES.ar:
                        if sum(1 for nr in n2a[ar]):
                            sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for nr in g2n[gt])]
                            if len(sPSNGT):
                                OutputResults = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in g2n[gt] if (ar,nr) in mTEPES.a2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                                OutputResults.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEmission_'+ar+'_'+CaseName+'.csv', sep=',')

            sPSNGT       = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for nr in g2n[gt])]
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in g2n[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
            OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEmission_'+CaseName+'.csv', sep=',')
            if pIndPlotOutput == 1:
                TechEmission = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'MtCO2'})
                TechEmission = TechEmission[(TechEmission[['MtCO2']] != 0).all(axis=1)]
                if len(TechEmission):
                    chart = alt.Chart(TechEmission.reset_index()).mark_bar().encode(x='Technology', y='MtCO2', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                    chart.save(_path+'/oT_Plot_TechnologyEmission_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        sPSNGT       = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt])]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyGeneration_'+CaseName+'.csv', sep=',')

        if pIndPlotOutput == 1:
            TechnologyOutput = OutputToFile.loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(_path+'/oT_Plot_TechnologyGeneration_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for g in mTEPES.g if (gt,g) in mTEPES.t2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyGenerationEnergy_'+CaseName+'.csv', sep=',')

        if pIndPlotOutput == 1:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(_path+'/oT_Plot_TechnologyGenerationEnergy_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndAreaOutput == 1:
                for ar in mTEPES.ar:
                    if sum(1 for g in g2a[ar]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in mTEPES.t2g if (ar,g) in mTEPES.a2g)]
                        if len(sPSNGT):
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for g in mTEPES.t2g if (ar,g) in mTEPES.a2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyGenerationEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

                            if pIndPlotOutput == 1:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(_path+'/oT_Plot_TechnologyGenerationEnergy_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing generation operation results   ... ', round(WritingResultsTime), 's')


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the ESS operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to area (e2a) (n2a)
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)

    # technology to generators (o2e)
    o2e = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            o2e[ot].append(es)

    OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]() for p,sc,n,es in mTEPES.psnes], index=pd.Index(mTEPES.psnes))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflows_'        +CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot]) for p,sc,n,ot in mTEPES.psnot], index=pd.Index(mTEPES.psnot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflows_'        +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psneh))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_Consumption_'                   +CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in o2e[ot]) for p,sc,n,ot in mTEPES.psnot], index=pd.Index(mTEPES.psnot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyConsumption_'     +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.psnes], index=pd.Index(mTEPES.psnes))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflowsEnergy_'+CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot]) for p,sc,n,ot in mTEPES.psnot], index=pd.Index(mTEPES.psnot))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflowsEnergy_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [p,sc,n,eh]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psneh))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ConsumptionEnergy_'            +CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        sPSNOT = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for es in o2e[ot])]
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in o2e[ot]) for p,sc,n,ot in sPSNOT], index=pd.Index(sPSNOT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis             (['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyConsumptionEnergy_'     +CaseName+'.csv', sep=',')

    if pIndPlotOutput == 1:
        TechnologyCharge = OutputToFile.loc[:,:,:,:]
        for p,sc in mTEPES.ps:
            chart = AreaPlots(p, sc, TechnologyCharge, 'Technology', 'LoadLevel', 'MW', 'sum')
            chart.save(_path+'/oT_Plot_TechnologyConsumption_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if pIndPlotOutput == 1:
        OutputToFile *= -1.0
        if OutputToFile.sum() < 0.0:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(_path+'/oT_Plot_TechnologyConsumptionEnergy_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if sum(1 for ar in mTEPES.ar if sum(1 for eh in e2a[ar])) > 1:
        if pIndAreaOutput == 1:
            for ar in mTEPES.ar:
                if sum(1 for eh in e2a[ar]):
                    sPSNOT = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for eh in e2a[ar] if (ot,eh) in mTEPES.t2g)]
                    if len(sPSNOT):
                        OutputToFile = pd.Series(data=[sum(-OptModel.vESSTotalCharge[p,sc,n,eh]()*mTEPES.pLoadLevelDuration[n]() for eh in e2a[ar] if (ot,eh) in mTEPES.t2g) for p,sc,n,ot in sPSNOT], index=pd.Index(sPSNOT))
                        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyConsumptionEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

                        if pIndPlotOutput == 1:
                            OutputToFile *= -1.0
                            for p,sc in mTEPES.ps:
                                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                chart.save(_path+'/oT_Plot_TechnologyConsumptionEnergy_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    InventoryConstraints = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.nesc if mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es]]
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()                                          for p,sc,n,es in InventoryConstraints], index=pd.Index(InventoryConstraints))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationInventory_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()/(mTEPES.pMaxStorage[p,sc,n,es]+pEpsilon) for p,sc,n,es in InventoryConstraints], index=pd.Index(InventoryConstraints))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationInventoryUtilization_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vESSSpillage[p,sc,n,es]()                                               for p,sc,n,es in InventoryConstraints], index=pd.Index(InventoryConstraints))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationSpillage_'+CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        ESSTechnologies = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for es in o2e[ot])]
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot] if (n,es) in mTEPES.nesc and mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es]) for p,sc,n,ot in ESSTechnologies], index=pd.Index(ESSTechnologies))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologySpillage_'+CaseName+'.csv', sep=',')

    OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.psnes], index=pd.Index(mTEPES.psnes))
    OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub                                     )*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.psnes], index=pd.Index(mTEPES.psnes))
    for p,sc,n,es in mTEPES.psnes:
        if es in mTEPES.gc:
            OutputToFile1[p,sc,n,es] *= OptModel.vGenerationInvest[p,es]()
            OutputToFile2[p,sc,n,es] *= OptModel.vGenerationInvest[p,es]()
    OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
    OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
        OutputToFile.to_csv(_path+'/oT_Result_GenerationSpillageRelative_'+CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,es] for es in o2e[ot]) for p,sc,ot in mTEPES.psot], index=pd.Index(mTEPES.psot))
        OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,es] for es in o2e[ot]) for p,sc,ot in mTEPES.psot], index=pd.Index(mTEPES.psot))
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='%').rename_axis(['Period', 'Scenario', 'Technology'], axis=0).to_csv(_path+'/oT_Result_TechnologySpillageRelative_'+CaseName+'.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing        ESS operation results   ... ', round(WritingResultsTime), 's')


def ReservoirOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    # %% outputting the reservoir operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # technology to hydro units (o2h)
    o2h = defaultdict(list)
    for ht,h  in mTEPES.ht*mTEPES.h :
        if (ht,h ) in mTEPES.t2g:
            o2h[ht].append(h )

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    VolumeConstraints = [(p,sc,n,rs) for p,sc,n,rs in mTEPES.ps*mTEPES.nrsc if sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r)]
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vReservoirVolume[p,sc,n,rs]()                                         for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ReservoirVolume_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vReservoirVolume[p,sc,n,rs]()/(mTEPES.pMaxVolume[p,sc,n,rs]+pEpsilon) for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3', dropna=False, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ReservoirVolumeUtilization_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vReservoirSpillage[p,sc,n,rs]()                                           for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ReservoirSpillage_'+CaseName+'.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        HydroTechnologies = [(p,sc,n,ht) for p,sc,n,ht in mTEPES.psnht if sum(1 for h in o2h[ht])]
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,rs] for rs in mTEPES.rs if (n,rs) in mTEPES.nrsc and sum(1 for h in o2h[ht] if (rs,h) in mTEPES.r2h)) for p,sc,n,ht in HydroTechnologies], index=pd.Index(HydroTechnologies))
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReservoirSpillage_'+CaseName+'.csv', sep=',')

    #%% outputting the water volume values
    OutputResults = []
    sPSSTNES      = [(p,sc,st,n,rs) for p,sc,st,n,rs in mTEPES.ps*mTEPES.s2n*mTEPES.rs if (n,rs) in mTEPES.nrsc and sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r or (rs,h) in mTEPES.r2p or (h,rs) in mTEPES.p2r)]
    OutputToFile = pd.Series(data=[-mTEPES.pDuals["".join(["eHydroInventory_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(rs), "')"])]*1e3 for p,sc,st,n,rs in sPSSTNES], index=pd.Index(sPSSTNES))
    OutputResults.append(OutputToFile)
    OutputResults = pd.concat(OutputResults)
    if len(OutputResults.index):
        OutputResults.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalWaterVolumeValue_'+CaseName+'.csv', sep=',')

    if pIndPlotOutput == 1:
        WaterValue = OutputResults.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, WaterValue, 'Generating unit', 'LoadLevel', 'EUR/dam3', 'average')
            chart.save(_path+'/oT_Plot_MarginalWaterVolumeValue_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  reservoir operation results   ... ', round(WritingResultsTime), 's')


def NetworkH2OperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the hydrogen pipeline network operation
    _path = os.path.join(DirName, CaseName)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # incoming and outgoing pipelines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.pa:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to electrolyzers (e2n)
    e2n = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            e2n[nd].append(el)

    # electrolyzers to technology (e2t)
    e2t = defaultdict(list)
    for gt,el in mTEPES.gt*mTEPES.el:
        if (gt,el) in mTEPES.t2g:
            e2t[gt].append(el)

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psnar*mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (nd,ar) in mTEPES.ndar]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for el in e2t[gt])                                                             and (nd,ar) in mTEPES.ndar]

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge[p,sc,n,el      ]()*mTEPES.pDuration[n]()/mTEPES.pProductionFunctionH2[el] for el in mTEPES.el if (nd,el) in mTEPES.n2g and (gt,el) in mTEPES.t2g) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'       ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation', aggfunc='sum')
    OutputResults3 = pd.Series(data=[     OptModel.vHNS           [p,sc,n,nd      ]()                                                                                                                                for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenNotServed')
    OutputResults4 = pd.Series(data=[-      mTEPES.pDemandH2      [p,sc,n,nd      ]  *mTEPES.pDuration[n]()                                                                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenDemand'   )
    OutputResults5 = pd.Series(data=[-sum(OptModel.vFlowH2        [p,sc,n,nd,lout ]()                                                        for lout  in lout[nd])                                                  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowOut'  )
    OutputResults6 = pd.Series(data=[ sum(OptModel.vFlowH2        [p,sc,n,ni,nd,cc]()                                                        for ni,cc in lin [nd])                                                  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6], axis=1)

    OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'tH2'}, inplace=False).to_csv(_path+'/oT_Result_BalanceHydrogen_'+CaseName+'.csv', index=False, sep=',')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(_path+'/oT_Result_BalanceHydrogenPerTech_'+CaseName+'.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(_path+'/oT_Result_BalanceHydrogenPerNode_'+CaseName+'.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(_path+'/oT_Result_BalanceHydrogenPerArea_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowH2[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=pd.Index(mTEPES.psnpa))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='tH2'), values='tH2', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkFlowH2PerNode_'     +CaseName+'.csv', index=False, sep=',')

    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for el in e2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vHNS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile.to_frame(name='tH2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkHNS_'  +CaseName+'.csv', sep=',')

    # plot hydrogen network map
    # Sub functions
    def oT_make_series(_var, _sets, _factor):
        return pd.Series(data=[_var[p,sc,n,ni,nf,cc]()*_factor for p,sc,n,ni,nf,cc in _sets], index=pd.Index(list(_sets)))

    def oT_selecting_data(p,sc,n):
        # Nodes data
        pio.renderers.default = 'chrome'

        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] =  0.0
        loc_df['Zone'  ] =  ''
        loc_df['Demand'] =  0.0
        loc_df['Size'  ] = 15.0

        for nd,zn in mTEPES.ndzn:
            loc_df['Lon'   ][nd] = mTEPES.pNodeLon[nd]
            loc_df['Zone'  ][nd] = zn
            loc_df['Demand'][nd] = mTEPES.pDemandH2[p,sc,n,nd]

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlowH2, mTEPES.psnpa, 1)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='tH2')

        # tolerance to consider avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pPipeNTCFrw[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa),
                                     'NTCBck': pd.Series(data=[mTEPES.pPipeNTCBck[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa)}, index=mTEPES.pa)
        line_df['vFlowH2'    ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = 0.0
        line_df['width'      ] = 3.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = 0.0
        line_df['nf'         ] = 0.0
        line_df['cc'         ] = 0.0

        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=True)
        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        for ni,nf,cc in mTEPES.pa:
            line_df['vFlowH2'    ][ni,nf] += OutputToFile['tH2'][p,sc,n,ni,nf,cc]
            line_df['utilization'][ni,nf]  = max(line_df['vFlowH2'][ni,nf]/line_df['NTCFrw'][ni,nf],-line_df['vFlowH2'][ni,nf]/line_df['NTCBck'][ni,nf])*100.0
            line_df['lon'        ][ni,nf]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df['lat'        ][ni,nf]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
            line_df['ni'         ][ni,nf]  = ni
            line_df['nf'         ][ni,nf]  = nf
            line_df['cc'         ][ni,nf] += 1

            if   0.0 <= line_df['utilization'][ni,nf] <= 10.0:
                line_df['color'][ni,nf] = colors[0]
            if  10.0 <  line_df['utilization'][ni,nf] <= 20.0:
                line_df['color'][ni,nf] = colors[1]
            if  20.0 <  line_df['utilization'][ni,nf] <= 30.0:
                line_df['color'][ni,nf] = colors[2]
            if  30.0 <  line_df['utilization'][ni,nf] <= 40.0:
                line_df['color'][ni,nf] = colors[3]
            if  40.0 <  line_df['utilization'][ni,nf] <= 50.0:
                line_df['color'][ni,nf] = colors[4]
            if  50.0 <  line_df['utilization'][ni,nf] <= 60.0:
                line_df['color'][ni,nf] = colors[5]
            if  60.0 <  line_df['utilization'][ni,nf] <= 70.0:
                line_df['color'][ni,nf] = colors[6]
            if  70.0 <  line_df['utilization'][ni,nf] <= 80.0:
                line_df['color'][ni,nf] = colors[7]
            if  80.0 <  line_df['utilization'][ni,nf] <= 90.0:
                line_df['color'][ni,nf] = colors[8]
            if  90.0 <  line_df['utilization'][ni,nf] <= 100.0:
                line_df['color'][ni,nf] = colors[9]
            if 100.0 <  line_df['utilization'][ni,nf]:
                line_df['color'][ni,nf] = colors[10]

        # Rounding to decimals
        line_df = line_df.round(decimals=2)

        return loc_df, line_df

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    p = list(mTEPES.p)[0]
    n = list(mTEPES.n)[0]

    if len(mTEPES.sc) > 1:
        for scc in mTEPES.sc:
            if (p,scc) in mTEPES.ps:
                if abs(mTEPES.pScenProb[p,scc]() - 1.0) < pEpsilon:
                    sc = scc
    else:
        sc = list(mTEPES.sc)[0]

    loc_df, line_df = oT_selecting_data(p,sc,n)

    # Making the network
    # Get node position dict
    x, y = loc_df['Lon'].values, loc_df['Lat'].values
    pos_dict = {}
    for index, iata in enumerate(loc_df['index']):
        pos_dict[iata] = (x[index], y[index])

    # Setting up the figure
    token = open(DIR+'/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni,nf,cc in mTEPES.pa:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'titleside': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df['width'][ni,nf], color=line_df['color'][ni,nf]), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowH2'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': 'Hydrogen Network: '+CaseName+'<br>Period: '+str(p)+'; Scenario: '+str(sc)+'; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(_path+'/oT_Plot_MapNetworkH2_'+CaseName+'.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting  hydrogen network maps        ... ', round(PlottingNetMapsTime), 's')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing   hydrogen operation results   ... ', round(WritingResultsTime), 's')


def OperationSummaryResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
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

    # Ratio Fossil Fuel Generation/Total Generation [%]
    TotalGeneration       = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.psng                 )
    FossilFuelGeneration  = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.psng if g in mTEPES.t)
    # Ratio Total Investments [%]
    TotalInvestmentCost   = sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFCost      [p]()          for p          in mTEPES.p  if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc))
    GenInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]       * OptModel.vGenerationInvest[p,gc]()       for p,gc       in mTEPES.pgc)
    GenRetirementCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenRetireCost[gd]       * OptModel.vGenerationRetire[p,gd]()       for p,gd       in mTEPES.pgd)
    if mTEPES.pIndHydroTopology == 1:
        RsrInvestmentCost = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pRsrInvestCost[rc]       * OptModel.vReservoirInvest [p,rc]()       for p,rc       in mTEPES.prc)
    else:
        RsrInvestmentCost = 0.0
    NetInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pNetFixedCost [ni,nf,cc] * OptModel.vNetworkInvest   [p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc)
    # Ratio Generation Investment cost/ Generation Installed Capacity [MEUR-MW]
    GenInvCostCapacity    = sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]()/mTEPES.pRatedMaxPower[gc]               for p,gc       in mTEPES.pgc if mTEPES.pRatedMaxPower[gc])
    # Ratio Additional Transmission Capacity-Length [MW-km]
    NetCapacityLength     = sum(mTEPES.pLineNTCMax[ni,nf,cc]*OptModel.vNetworkInvest[p,ni,nf,cc]()/mTEPES.pLineLength[ni,nf,cc]()      for p,ni,nf,cc in mTEPES.plc)
    # Ratio Network Investment Cost/Variable RES Injection [EUR/MWh]
    if len(mTEPES.gc) and sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re):
        NetInvCostVRESInsCap = NetInvestmentCost*1e6/sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re)
    else:
        NetInvCostVRESInsCap = 0.0
    # Rate of return for VRE technologies
    VRETechRevenue     = sum(mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput[p,sc,n,gc]() for p,sc,st,n,nd,gc in mTEPES.ps*mTEPES.s2n*mTEPES.nd*mTEPES.gc if (nd,gc) in mTEPES.n2g and gc in mTEPES.re and sum(1 for g in g2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]))
    VREInvCostCapacity = sum(mTEPES.pGenInvestCost[gc]*OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.pgc if gc in mTEPES.re)

    K1     = pd.Series(data={'Ratio Fossil Fuel Generation/Total Generation [%]'                       : FossilFuelGeneration / TotalGeneration    *1e2}).to_frame(name='Value')
    if GenInvestmentCost:
        K2 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : GenInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K2 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    if GenRetirementCost:
        K3 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : GenRetirementCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K3 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    if RsrInvestmentCost:
        K4 = pd.Series(data={'Ratio Reservoir Investment Cost/Total Investment Cost [%]'               : RsrInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K4 = pd.Series(data={'Ratio Reservoir Investment Cost/Total Investment Cost [%]'               : 0.0                                           }).to_frame(name='Value')
    if NetInvestmentCost:
        K5 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : NetInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K5 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : 0.0                                           }).to_frame(name='Value')
    if GenInvCostCapacity:
        K6 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': GenInvCostCapacity   / 1e3                    }).to_frame(name='Value')
    else:
        K6 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': 0.0                                           }).to_frame(name='Value')
    if NetCapacityLength:
        K7 = pd.Series(data={'Ratio Additional Transmission Capacity/Line Length [MW-km]'              : NetCapacityLength    * 1e3                    }).to_frame(name='Value')
    else:
        K7 = pd.Series(data={'Ratio Additional Transmission Capacity/Line Length [MW-km]'              : 0.0                                           }).to_frame(name='Value')
    if NetInvCostVRESInsCap:
        K8 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : NetInvCostVRESInsCap * 1e3                    }).to_frame(name='Value')
    else:
        K8 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : 0.0                                           }).to_frame(name='Value')
    if VREInvCostCapacity:
        K9 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : VRETechRevenue       / VREInvCostCapacity*1e2 }).to_frame(name='Value')
    else:
        K9 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : 0.0                                           }).to_frame(name='Value')

    OutputResults = pd.concat([K1, K2, K3, K4, K5, K6, K7, K8, K9], axis=0)
    OutputResults.to_csv(_path+'/oT_Result_SummaryKPIs_'+CaseName+'.csv', sep=',', index=True)

    # LCOE per technology
    if len(mTEPES.gc):
        GenTechInvestCost = pd.Series(data=[sum(OptModel.vGenerationInvest[p,     gc]()*mTEPES.pGenInvestCost    [gc]   for p,     gc in mTEPES.pgc   if (gt,gc) in mTEPES.t2g) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection  = pd.Series(data=[sum(OptModel.vTotalOutput     [p,sc,n,gc]()*mTEPES.pLoadLevelDuration[n ]() for p,sc,n,gc in mTEPES.psngc if (gt,gc) in mTEPES.t2g) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        LCOE = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh')
        LCOE.rename_axis(['Technology'], axis=0).to_csv(_path+'/oT_Result_TechnologyLCOE_'+CaseName+'.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing          KPI summary results   ... ', round(WritingResultsTime), 's')

    StartTime = time.time()
    n2g = pd.DataFrame(mTEPES.n2g).set_index(1)
    z2g = pd.DataFrame(mTEPES.z2g).set_index(1)
    a2g = pd.DataFrame(mTEPES.a2g).set_index(1)
    r2g = pd.DataFrame(mTEPES.r2g).set_index(1)
    t2g = pd.DataFrame(mTEPES.t2g).set_index(1)
    OutputToFile01 = pd.Series(data=[OptModel.vTotalOutput   [p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]()                                                                      for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='EnergyProduction [GWh]' )
    OutputToFile02 = pd.Series(data=[OptModel.vESSTotalCharge[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]()                                           if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='EnergyConsumption [GWh]')
    OutputToFile03 = pd.Series(data=[n2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Node'                   )
    OutputToFile04 = pd.Series(data=[z2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Zone'                   )
    OutputToFile05 = pd.Series(data=[a2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Area'                   )
    OutputToFile06 = pd.Series(data=[r2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Region'                 )
    OutputToFile07 = pd.Series(data=[t2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Technology'             )
    OutputToFile08 = pd.Series(data=[OptModel.vTotalOutput   [p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]()*mTEPES.pEmissionVarCost[p,sc,n,g]/mTEPES.pCO2Cost()                  for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Emissions [MtCO2]'      )
    OutputToFile09 = pd.Series(data=[OptModel.vTotalOutput   [p,sc,n,g].ub                                                                                                    for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='MaxPower [MW]'          )
    OutputToFile10 = pd.Series(data=[OptModel.vTotalOutput   [p,sc,n,g].lb                                                                                                    for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='MinPower [MW]'          )
    OutputToFile11 = pd.Series(data=[mTEPES.pLoadLevelDuration[n]()                                                                                                           for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='LoadLevelDuration [h]'  )
    OutputToFile12 = pd.Series(data=[OptModel.vCommitment    [p,sc,n,g]()                                                                          if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Commitment {0,1}'       )
    OutputToFile13 = pd.Series(data=[OptModel.vStartUp       [p,sc,n,g]()                                                                          if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='StartUp {0,1}'          )
    OutputToFile14 = pd.Series(data=[OptModel.vShutDown      [p,sc,n,g]()                                                                          if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='Shutdown {0,1}'         )
    OutputToFile15 = pd.Series(data=[OptModel.vReserveUp     [p,sc,n,g]()                                                                          if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='ReserveUp [MW]'         )
    OutputToFile16 = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,g]()                                                                          if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='ReserveDown [MW]'       )
    OutputToFile17 = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,g]()                                                                          if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='ESSReserveUp [MW]'      )
    OutputToFile18 = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,g]()                                                                          if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='ESSReserveDown [MW]'    )
    OutputToFile19 = pd.Series(data=[OptModel.vESSSpillage   [p,sc,n,g]()                                                                          if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=pd.Index(mTEPES.psng)).to_frame(name='ESSSpillage [GWh]'      )

    OutputToFile15 *= 1e3
    OutputToFile16 *= 1e3
    OutputToFile17 *= 1e3
    OutputToFile18 *= 1e3

    OutputResults   = pd.concat([OutputToFile01, OutputToFile02, OutputToFile03, OutputToFile04, OutputToFile05, OutputToFile06, OutputToFile07, OutputToFile08, OutputToFile09,
                                 OutputToFile11, OutputToFile12, OutputToFile13, OutputToFile14, OutputToFile15, OutputToFile16, OutputToFile17, OutputToFile18, OutputToFile19], axis=1)
    OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'GenerationUnit'], axis=0).to_csv(_path+'/oT_Result_SummaryGeneration_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing   generation summary results   ... ', round(WritingResultsTime), 's')

    ndzn = pd.DataFrame(mTEPES.ndzn).set_index(0)
    ndar = pd.DataFrame(mTEPES.ndar).set_index(0)
    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for g in g2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputResults1     = pd.Series(data=[ ndzn[1][nd]                                                                                        for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Zone'               )
    OutputResults2     = pd.Series(data=[ ndar[1][nd]                                                                                        for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Area'               )
    OutputResults3     = pd.Series(data=[     OptModel.vENS       [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[n]()                         for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='ENS [GWh]'          )
    OutputResults4     = pd.Series(data=[-      mTEPES.pDemand    [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[n]()                         for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerDemand [GWh]'  )
    OutputResults5     = pd.Series(data=[-sum(OptModel.vFlow      [p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]() for lout  in lout [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowOut [GWh]' )
    OutputResults6     = pd.Series(data=[ sum(OptModel.vFlow      [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]() for ni,cc in lin  [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowIn [GWh]'  )
    if len(mTEPES.ll):
        OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]() for lout  in loutl[nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesOut [GWh]')
        OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]() for ni,cc in linl [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesIn [GWh]' )

        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    else:
        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6                                ], axis=1)

    OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Node'], axis=0).to_csv(_path+'/oT_Result_SummaryNetwork_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing elec network summary results   ... ', round(WritingResultsTime), 's')


def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to technology (e2o)
    e2o = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            e2o[ot].append(es)

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g  in mTEPES.t2g:
        g2t[gt].append(g)

    sPSNGT               = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt])]
    OutputToFile         = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
    OutputToFile *= 1e3
    TechnologyOutput     = OutputToFile.loc[:,:,:,:]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput  = pd.Series([0.0]*len(sPSNGT), index=pd.Index(sPSNGT))
    for p,sc,n,gt in sPSNGT:
        NetTechnologyOutput[p,sc,n,gt] = TechnologyOutput[p,sc,n,gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnology_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        ESSTechnologies = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psnot if sum(1 for es in e2o[ot])]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,es]() for es in e2o[ot]) for p,sc,n,ot in ESSTechnologies], index=pd.Index(ESSTechnologies))
        OutputToFile *= 1e3
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput  = pd.Series([0.0] * len(ESSTechnologies), index=pd.Index(ESSTechnologies))
        for p,sc,n,gt in ESSTechnologies:
            NetESSTechnologyOutput[p,sc,n,gt] = MeanESSTechnologyOutput[gt] - ESSTechnologyOutput[p,sc,n,gt]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnologyESS_'+CaseName+'.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemand[p,sc,n,nd] for nd in mTEPES.nd)              for p,sc,n in mTEPES.psn], index=pd.Index(mTEPES.psn)).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemand[p,sc,n,nd] for nd in mTEPES.nd) - MeanDemand for p,sc,n in mTEPES.psn], index=pd.Index(mTEPES.psn))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='Demand').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityDemand_'+CaseName+'.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in mTEPES.nd)           for p,sc,n in mTEPES.psn], index=pd.Index(mTEPES.psn)).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in mTEPES.nd) - MeanENS for p,sc,n in mTEPES.psn], index=pd.Index(mTEPES.psn))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='PNS').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityPNS_'   +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing          flexibility results   ... ', round(WritingResultsTime), 's')


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the electric network operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if sum(mTEPES.pIndBinLineSwitch[:, :, :]):
        if len(mTEPES.lc):
            OutputToFile = pd.Series(data=[OptModel.vLineCommit  [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
            OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
            OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
            OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkCommitment_'+CaseName+'.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOnState [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkSwitchOn_'  +CaseName+'.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOffState[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkSwitchOff_' +CaseName+'.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
    OutputToFile *= 1e3
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkFlowPerNode_'       +CaseName+'.csv', index=False, sep=',')

    PSNLAARAR = [(p,sc,n,ni,nf,cc,ai,af) for p,sc,n,ni,nf,cc,ai,af in mTEPES.psnla*mTEPES.ar*mTEPES.ar if (ni,ai) in mTEPES.ndar and (nf,af) in mTEPES.ndar]
    OutputToFile = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,ni,nf,cc,ai,af in PSNLAARAR], index=pd.Index(PSNLAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkEnergyPerArea_'+CaseName+'.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,ni,nf,cc,ai,af in PSNLAARAR], index=pd.Index(PSNLAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkEnergyTotalPerArea_'+CaseName+'.csv', index=False, sep=',')

    if len(mTEPES.la):
        OutputResults = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]()*(mTEPES.pDuration[n]()*mTEPES.pLoadLevelWeight[n]()*mTEPES.pPeriodWeight[p]()*mTEPES.pScenProb[p,sc]())*(mTEPES.pLineLength[ni,nf,cc]()*1e-3) for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
        OutputResults.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = OutputResults.reset_index().groupby(['InitialNode', 'FinalNode', 'Circuit']).sum(numeric_only=True)[0]
        OutputResults.to_frame(name='GWh-Mkm').rename_axis(['InitialNode', 'FinalNode', 'Circuit'], axis=0).reset_index().to_csv(_path+'/oT_Result_NetworkEnergyTransport_'+CaseName+'.csv', index=False, sep=',')

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlow[p,sc,n,ni,nf,cc]()/(mTEPES.pLineNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlow[p,sc,n,ni,nf,cc]()/(mTEPES.pLineNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnla], index=pd.Index(mTEPES.psnla))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkUtilization_'+CaseName+'.csv', index=False, sep=',')

    if mTEPES.pIndBinNetLosses():
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnll], index=pd.Index(mTEPES.psnll))
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(_path+'/oT_Result_NetworkLosses_' +CaseName+'.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTheta[p,sc,n,nd]()                              for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()                            for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkPNS_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkENS_'  +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing el network operation results   ... ', round(WritingResultsTime), 's')


def MarginalResults(DirName, CaseName, OptModel, mTEPES, pIndPlotOutput):
    # %% outputting marginal results
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # generators to nodes (g2n)
    g2n = defaultdict(list)
    for nd,g  in mTEPES.n2g:
        g2n[nd].append(g)

    # generators to area (e2a) (n2a)
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    #%% outputting the incremental variable cost of each generating unit with power surplus
    sPSNG        = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if g not in mTEPES.es]
    OutputToFile = pd.Series(data=[(mTEPES.pLinearVarCost[p,sc,n,g]+mTEPES.pEmissionVarCost[p,sc,n,g]) for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
    OutputToFile *= 1e3

    OutputToFile = OutputToFile.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='EUR/MWh')
    OutputToFile.rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalIncrementalVariableCost_'+CaseName+'.csv', sep=',')
    IncrementalGens = pd.Series('N/A', index=pd.Index(mTEPES.psn)).to_frame(name='Generating unit')
    for p,sc,n in mTEPES.psn:
        IncrementalGens['Generating unit'][p,sc,n] = OutputToFile.loc[[(p,sc,n)]].squeeze().idxmin()
    IncrementalGens.rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).to_csv(_path+'/oT_Result_MarginalIncrementalGenerator_'+CaseName+'.csv', index=True, sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pEmissionRate[g] for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
    OutputToFile.to_frame(name='tCO2/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tCO2/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationIncrementalEmission_'+CaseName+'.csv', sep=',')

    #%% outputting the LSRMC
    sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.ps*mTEPES.s2n*mTEPES.nd if sum(1 for g in g2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
    OutputResults *= 1e3
    OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMC').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkSRMC_'+CaseName+'.csv', sep=',')

    OptModel.LSRMC = OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMC').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]

    if pIndPlotOutput == 1:
        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, OptModel.LSRMC, 'Node', 'LoadLevel', 'EUR/MWh', 'average')
            chart.save(_path+'/oT_Plot_NetworkSRMC_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if sum(mTEPES.pReserveMargin[:,:]):
        if len(mTEPES.gc):
            sPSSTAR       = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pReserveMargin[p,ar] and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g) and sum(mTEPES.pRatedMaxPower[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (ar,g) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pPeakDemand[p,ar] * mTEPES.pReserveMargin[p,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eAdequacyReserveMargin_", str(p), "_", str(sc), "_", str(st), "(", str(p), ", '", str(ar), "')"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
            OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalReserveMargin_'+CaseName+'.csv', sep=',')

    sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pEmission[p,ar] < math.inf and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g)]
    if len(sPSSTAR):
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eMaxSystemEmission_", str(p), "_", str(sc), "_", str(st),  "(", str(p), ", '", str(ar), "')"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
        OutputResults.to_frame(name='EM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='EM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalEmission_'+CaseName+'.csv', sep=',')

    #%% outputting the up operating reserve marginal
    if sum(mTEPES.pOperReserveUp[:,:,:,:]) and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g if mTEPES.pIndOperReserve[es] == 0)):
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.ps*mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveUp[p,sc,n,ar] and sum(1 for nr in n2a[ar]) + sum(1 for es in e2a[ar])]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveUp_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='UORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveUp_'+CaseName+'.csv', sep=',')

        if pIndPlotOutput == 1:
            MarginalUpOperatingReserve = OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='UORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, MarginalUpOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
                chart.save(_path+'/oT_Plot_MarginalOperatingReserveUpward_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the down operating reserve marginal
    if sum(mTEPES.pOperReserveDw[:,:,:,:]) and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g if mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g if mTEPES.pIndOperReserve[es] == 0)):
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.ps*mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveDw[p,sc,n,ar] and sum(1 for nr in n2a[ar]) + sum(1 for es in e2a[ar])]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveDw_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='DORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveDown_'+CaseName+'.csv', sep=',')

        if pIndPlotOutput == 1:
            MarginalDwOperatingReserve = OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='DORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, MarginalDwOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
                chart.save(_path+'/oT_Plot_MarginalOperatingReserveDownward_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the water values
    if len(mTEPES.es):
        OutputResults = []
        sPSSTNES      = [(p,sc,st,n,es) for p,sc,st,n,es in mTEPES.ps*mTEPES.s2n*mTEPES.es if (n,es) in mTEPES.nesc and mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es]]
        OutputToFile  = pd.Series(data=[-mTEPES.pDuals["".join(["eESSInventory_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(es), "')"])]*1e3 for p,sc,st,n,es in sPSSTNES], index=pd.Index(sPSSTNES))
        OutputResults.append(OutputToFile)
        OutputResults = pd.concat(OutputResults)
        if len(OutputResults.index):
            OutputResults.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalWaterValue_'+CaseName+'.csv', sep=',')

        if pIndPlotOutput == 1:
            WaterValue = OutputResults.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, WaterValue, 'Generating unit', 'LoadLevel', 'EUR/MWh', 'average')
                chart.save(_path+'/oT_Plot_MarginalWaterValue_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% Reduced cost for NetworkInvestment
    ReducedCostActivation = mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)
    if len(mTEPES.lc) and not ReducedCostActivation and OptModel.vNetworkInvest.is_variable_type():
        OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[p,ni,nf,cc]] for p,ni,nf,cc in mTEPES.plc], index=pd.Index(mTEPES.plc))
        OutputToFile.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile.to_frame(name='MEUR').to_csv(_path+'/oT_Result_NetworkInvestment_ReducedCost_'+CaseName+'.csv', sep=',')

    #%% Reduced cost for NetworkCommitment
    if len(mTEPES.ls) and not ReducedCostActivation and OptModel.vLineCommit.is_variable_type():
        OutputResults = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[p,sc,n,ni,nf,cc]] for p,sc,n,ni,nf,cc in mTEPES.psnls], index=pd.Index(mTEPES.psnlas))
        OutputResults.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = pd.pivot_table(OutputResults.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
        OutputResults.index.names = [None] * len(OutputResults.index.names)
        OutputResults.to_csv(_path+'/oT_Result_NetworkCommitment_ReducedCost_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing marginal information results   ... ', round(WritingResultsTime), 's')


def ReliabilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the reliability indexes
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to nodes (r2n)
    r2n = defaultdict(list)
    for nd,re in mTEPES.nd*mTEPES.re:
        if (nd,re) in mTEPES.n2g:
            r2n[nd].append(re)

    pDemand        = pd.Series(data=[mTEPES.pDemand  [p,sc,n,nd] for p,sc,n,nd in mTEPES.psnnd ], index=pd.Index(mTEPES.psnnd))
    ExistCapacity  = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if g not in mTEPES.gc]
    pExistMaxPower = pd.Series(data=[mTEPES.pMaxPower[p,sc,n,g ] for p,sc,n,g  in ExistCapacity], index=pd.Index(ExistCapacity))
    if len(mTEPES.gc):
        CandCapacity  = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if g in mTEPES.gc]
        pCandMaxPower = pd.Series(data=[mTEPES.pMaxPower[p,sc,n,g ] * OptModel.vGenerationInvest[p,g]() for p,sc,n,g in CandCapacity], index=pd.Index(CandCapacity))
        pMaxPower     = pd.concat([pExistMaxPower, pCandMaxPower])
    else:
        pMaxPower     = pExistMaxPower

    # Determination of the net demand
    OutputToFile1 = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,re]() for re in r2n[nd]) for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile2 = pd.Series(data=[      mTEPES.pDemand     [p,sc,n,nd]                      for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile  = OutputToFile2 - OutputToFile1
    OutputToFile  *= 1e3
    OutputToFile  = OutputToFile.to_frame(name='MW'  )
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkNetDemand_'+CaseName+'.csv', sep=',')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'],                    values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetDemand_'       +CaseName+'.csv', sep=',')

    # Determination of the index: Reserve Margin
    OutputToFile1 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    OutputToFile2 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile1[p,sc] = pMaxPower.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum').max().iloc[0]
        OutputToFile2[p,sc] =   pDemand.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum').max().iloc[0]
    ReserveMargin1 =  OutputToFile1 - OutputToFile2
    ReserveMargin2 = (OutputToFile1 - OutputToFile2)/OutputToFile2
    ReserveMargin1.to_frame(name='MW'  ).rename_axis(['Period', 'Scenario'], axis=0).to_csv(_path+'/oT_Result_ReserveMarginPower_'  +CaseName+'.csv', sep=',')
    ReserveMargin2.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).to_csv(_path+'/oT_Result_ReserveMarginPerUnit_'+CaseName+'.csv', sep=',')

    # Determination of the index: Largest Unit
    OutputToFile = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile[p,sc] = pMaxPower.loc[(p,sc)].reset_index().pivot_table(index=['level_1'], values=0, aggfunc='sum').max().iloc[0]

    LargestUnit  = ReserveMargin1/OutputToFile
    LargestUnit.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).to_csv(_path+'/oT_Result_LargestUnitPerUnit_'+CaseName+'.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing          reliability indexes   ... ', round(WritingResultsTime), 's')

def CostSummaryResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    SysCost        = pd.Series(data=[                                                                                                                               OptModel.vTotalSCost()                                                                                                         ], index=[' ']   ).to_frame(name='Total          System Cost').stack()
    GenInvCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenInvestCost[gc  ]                                                                * OptModel.vGenerationInvest[p,gc  ]()  for gc      in mTEPES.gc                                          )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation Investment Cost').stack()
    GenRetCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenRetireCost[gd  ]                                                                * OptModel.vGenerationRetire[p,gd  ]()  for gd      in mTEPES.gd                                          )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation Retirement Cost').stack()
    if mTEPES.pIndHydroTopology == 1:
        RsrInvCost = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pRsrInvestCost[rc  ]                                                                * OptModel.vReservoirInvest [p,rc  ]()  for rc      in mTEPES.rn                                          )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reservoir  Investment Cost').stack()
    else:
        RsrInvCost = pd.Series(data=[0.0                                                                                                                                                                                                                                          for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reservoir  Investment Cost').stack()
    NetInvCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pNetFixedCost [lc  ]                                                                * OptModel.vNetworkInvest   [p,lc  ]()  for lc      in mTEPES.lc                                          )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Network    Investment Cost').stack()
    GenCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]()                                                              * OptModel.vTotalGCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if (p,sc) in mTEPES.ps)     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation  Operation Cost').stack()
    ConCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]()                                                              * OptModel.vTotalCCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if (p,sc) in mTEPES.ps)     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Consumption Operation Cost').stack()
    EmiCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]()                                                              * OptModel.vTotalECost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if (p,sc) in mTEPES.ps)     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Emission              Cost').stack()
    RelCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]()                                                              * OptModel.vTotalRCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if (p,sc) in mTEPES.ps)     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability           Cost').stack()
    # DemPayment   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pDemand[p,sc,n,nd] * OptModel.LSRMC            [p,sc,n,nd] for sc,n,nd in mTEPES.sc*mTEPES.n*mTEPES.nd if (p,sc) in mTEPES.ps)/1e3 for p in mTEPES.p], index=mTEPES.p).to_frame(name='Demand Payment'            ).stack()
    CostSummary    = pd.concat([SysCost, GenInvCost, GenRetCost, RsrInvCost, NetInvCost, GenCost, ConCost, EmiCost, RelCost]).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Costs', 0: 'MEUR'}).to_csv(_path+'/oT_Result_CostSummary_'+CaseName+'.csv', sep=',', index=False)

    WritingResultsTime = time.time() - StartTime
    print('Writing         cost summary results   ... ', round(WritingResultsTime), 's')


def EconomicResults(DirName, CaseName, OptModel, mTEPES, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # %%  Power balance per period, scenario, and load level
    # incoming and outgoing lines (lin) (lout)
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
    for nd,g  in mTEPES.n2g:
        g2n[nd].append(g)
    e2n = defaultdict(list)
    for nd,es in mTEPES.nd*mTEPES.es:
        if (nd,es) in mTEPES.n2g:
            e2n[nd].append(es)

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g  in mTEPES.t2g:
        g2t[gt].append(g)

    # generators to area (g2a)
    g2a = defaultdict(list)
    for ar,g  in mTEPES.a2g:
        g2a[ar].append(g)

    if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
        if pIndAreaOutput == 1:
            for ar in mTEPES.ar:
                if sum(1 for g in g2a[ar]):
                    sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in mTEPES.t2g if (ar,g) in mTEPES.a2g)]
                    if len(sPSNGT):
                        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for g in mTEPES.t2g if (ar,g) in mTEPES.a2g) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyGenerationEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

                        if pIndPlotOutput == 1:
                            for p,sc in mTEPES.ps:
                                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                chart.save(_path+'/oT_Plot_TechnologyGenerationEnergy_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psnar*mTEPES.nd if sum(1 for g in g2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (nd,ar) in mTEPES.ndar]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for g in g2t[gt])                                                             and (nd,ar) in mTEPES.ndar]

    OutputResults1     = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,g       ]()*mTEPES.pLoadLevelDuration[n]()                        for g  in mTEPES.g  if (nd,g ) in mTEPES.n2g and (gt,g ) in mTEPES.t2g) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'    ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    OutputResults2     = pd.Series(data=[-sum(OptModel.vESSTotalCharge[p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[n]()*mTEPES.pEfficiency[eh] for eh in mTEPES.eh if (nd,eh) in mTEPES.n2g and (gt,eh) in mTEPES.t2g) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Consumption'   ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Consumption', aggfunc='sum')
    OutputResults3     = pd.Series(data=[     OptModel.vENS           [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[n]()                                                                                                for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='PowerNotServed')
    OutputResults4     = pd.Series(data=[-      mTEPES.pDemand        [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[n]()                                                                                                for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyDemand'  )
    OutputResults5     = pd.Series(data=[-sum(OptModel.vFlow          [p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]()                        for lout  in lout [nd])                                                 for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowOut' )
    OutputResults6     = pd.Series(data=[ sum(OptModel.vFlow          [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]()                        for ni,cc in lin  [nd])                                                 for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowIn'  )
    # OutputResults9   = pd.Series(data=[ ar                                                                                                    for ar in mTEPES.ar                          for p,sc,n,ar,nd    in sPSNND if (nd,ar) in mTEPES.ndar     ], index=pd.Index(sPSNARND  )).to_frame(name='Area'          )
    if len(mTEPES.ll):
        OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]()                        for lout  in loutl[nd])                                                 for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesOut' )
        OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]()                        for ni,cc in linl [nd])                                                 for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesIn'  )

        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    else:
        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6                                ], axis=1)

    OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv(_path+'/oT_Result_BalanceEnergy_'+CaseName+'.csv', index=False, sep=',')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(_path+'/oT_Result_BalanceEnergyPerTech_'+CaseName+'.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(_path+'/oT_Result_BalanceEnergyPerNode_'+CaseName+'.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(_path+'/oT_Result_BalanceEnergyPerArea_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperation_'       +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[:,:,:,:]) + sum(mTEPES.pOperReserveDw[:,:,:,:]):
        OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                        mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperReserve_' +CaseName+'.csv', sep=',')

    if len(mTEPES.re):
        OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput [p,sc,n,re]() for p,sc,n,re in mTEPES.psnre], index=pd.Index(mTEPES.psnre))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOandM_'       +CaseName+'.csv', sep=',')

    if len(mTEPES.es) and sum(mTEPES.pIndOperReserve[es] for es in mTEPES.es if mTEPES.pIndOperReserve[es] == 0):
        OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost[p,sc,n,eh] * OptModel.vESSTotalCharge[p,sc,n,eh]()  for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psnes))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ConsumptionCostOperation_'  +CaseName+'.csv', sep=',')
        OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                        mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in mTEPES.psneh], index=pd.Index(mTEPES.psneh))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ConsumptionCostOperReserve_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pEmissionVarCost[p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=pd.Index(mTEPES.psnnr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostEmission_'    +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pENSCost()                  * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in mTEPES.psnnd], index=pd.Index(mTEPES.psnnd))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkCostENS_'            +CaseName+'.csv', sep=',')

    def Transformation1(df, _name):
        df = df.to_frame(name='MEUR')
        df['Cost'] = _name
        df = df.reset_index().pivot_table(index=['level_0', 'level_1', 'Cost'], values='MEUR', aggfunc='sum')
        return df

    if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
        if pIndAreaOutput == 1:
            for ar in mTEPES.ar:
                if sum(1 for g in g2a[ar]):
                    OutputResults1 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Generation Operation Cost'         ) for p,sc in mTEPES.ps]))
                    OutputResults2 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Generation Operating Reserve Cost' ) for p,sc in mTEPES.ps]))
                    OutputResults3 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Generation O&M Cost'               ) for p,sc in mTEPES.ps]))
                    OutputResults4 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Consumption Operation Cost'        ) for p,sc in mTEPES.ps]))
                    OutputResults5 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Consumption Operating Reserve Cost') for p,sc in mTEPES.ps]))
                    OutputResults6 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Emission Cost'                     ) for p,sc in mTEPES.ps]))
                    OutputResults7 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.Index([(p,sc,'Reliability Cost'                  ) for p,sc in mTEPES.ps]))
                    if len(mTEPES.nr):
                        sPSNNR = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.psnnr if (ar,nr) in mTEPES.a2g]
                        if len(sPSNNR):
                            OutputResults1 = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                                              mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                                              mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                                              mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                            OutputResults1 = Transformation1(OutputResults1, 'Generation Operation Cost')
                            OutputResults6 = pd.Series(data=[ mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pEmissionVarCost[p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                            OutputResults6 = Transformation1(OutputResults6, 'Emission Cost')

                            if sum(mTEPES.pOperReserveUp[:,:,:,:]) + sum(mTEPES.pOperReserveDw[:,:,:,:]):
                                OutputResults2 = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                                OutputResults2 = Transformation1(OutputResults2, 'Generation Operating Reserve Cost')

                    if len(mTEPES.re):
                        sPSNRE = [(p,sc,n,re) for p,sc,n,re in mTEPES.psnre if (ar,re) in mTEPES.a2g]
                        if len(sPSNRE):
                            OutputResults3 = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput   [p,sc,n,re]() for p,sc,n,re in sPSNRE], index=pd.Index(sPSNRE))
                            OutputResults3 = Transformation1(OutputResults3, 'Generation O&M Cost')

                    if len(mTEPES.eh) and sum(mTEPES.pIndOperReserve[eh] for eh in mTEPES.eh if mTEPES.pIndOperReserve[eh] == 0):
                        sPSNES = [(p,sc,n,eh) for p,sc,n,eh in mTEPES.psneh if (ar,eh) in mTEPES.a2g]
                        if len(sPSNES):
                            OutputResults4 = pd.Series(data=[ mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [p,sc,n,eh] * OptModel.vESSTotalCharge[p,sc,n,eh]()  for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                            OutputResults5 = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                                              mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                            OutputResults4 = Transformation1(OutputResults4, 'Consumption Operation Cost')
                            OutputResults5 = Transformation1(OutputResults5, 'Consumption Operating Reserve Cost')

                    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if (nd,ar) in mTEPES.ndar]
                    if len(sPSNND):
                        OutputResults7 = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[n]() * mTEPES.pENSCost()           * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
                        OutputResults7 = Transformation1(OutputResults7, 'Reliability Cost')

                    OutputResults = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7], axis=0)
                    OutputResults.rename_axis(['Period', 'Scenario', 'Cost'], axis=0).to_csv(_path+'/oT_Result_CostSummary_'+ar+'_'+CaseName+'.csv', sep=',')

    sPSSTNNDG     = [(p,sc,st,n,nd,g) for p,sc,st,n,nd,g in mTEPES.ps*mTEPES.s2n*mTEPES.n2g]
    OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput[p,sc,n,g]() for p,sc,st,n,nd,g in sPSSTNNDG], index=pd.Index(sPSSTNNDG))
    OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyGeneration_'+CaseName+'.csv', sep=',')

    if len(mTEPES.eh):
        sPSSTNNDES    = [(p,sc,st,n,nd,eh) for p,sc,st,n,nd,eh in mTEPES.ps*mTEPES.s2n*mTEPES.n2g if eh in mTEPES.eh]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,st,n,nd,eh in sPSSTNNDES], index=pd.Index(sPSSTNNDES))
        OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyConsumption_'+CaseName+'.csv', sep=',')

    if len(mTEPES.gc):
        GenRev    = []
        ChargeRev = []
        sPSSTNNDGC1    = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in mTEPES.ps*mTEPES.s2n*mTEPES.n2g if gc in mTEPES.gc]
        OutputToGenRev = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput   [p,sc,n,gc]()         for p,sc,st,n,nd,gc in sPSSTNNDGC1], index=pd.Index(sPSSTNNDGC1))
        GenRev.append(OutputToGenRev)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc)     in mTEPES.t2g]):
            sPSSTNNDGC2        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for ot in mTEPES.ot if (ot,gc)     in mTEPES.t2g]
            OutputChargeRevESS = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vESSTotalCharge[p,sc,n,gc]() for p,sc,st,n,nd,gc in sPSSTNNDGC2], index=pd.Index(sPSSTNNDGC2))
            ChargeRev.append(OutputChargeRevESS)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc)     in mTEPES.t2g]):
            sPSSTNNDGC3        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for rt in mTEPES.rt if (rt,gc)     in mTEPES.t2g]
            OutputChargeRevRES = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]() * 0.0                                                                  for p,sc,st,n,nd,gc in sPSSTNNDGC3], index=pd.Index(sPSSTNNDGC3))
            ChargeRev.append(OutputChargeRevRES)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g]):
            sPSSTNNDGC4        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g]
            OutputChargeRevThr = pd.Series(data=[mTEPES.pDuals["".join(["eBalance_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(nd), "')"])]/mTEPES.pPeriodProb[p,sc]() * 0.0                                                                  for p,sc,st,n,nd,gc in sPSSTNNDGC4], index=pd.Index(sPSSTNNDGC4))
            ChargeRev.append(OutputChargeRevThr)
        GenRev    = pd.concat(GenRev)
        ChargeRev = pd.concat(ChargeRev)
        GenRev    = GenRev.to_frame   ('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        ChargeRev = ChargeRev.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
    else:
        GenRev    = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        ChargeRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pReserveMargin[:,:]):
        if len(mTEPES.gc):
            sPSSTARGC      = [(p,sc,st,ar,gc) for p,sc,st,ar,gc in mTEPES.ps*mTEPES.st*mTEPES.ar*mTEPES.gc if (ar,gc) in mTEPES.a2g and mTEPES.pReserveMargin[p,ar] and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g) and sum(mTEPES.pRatedMaxPower[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (ar,g) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pPeakDemand[p,ar] * mTEPES.pReserveMargin[p,ar]]
            OutputToResRev = pd.Series(data=[mTEPES.pDuals["".join(["eAdequacyReserveMargin_", str(p), "_", str(sc), "_", str(st),  "(", str(p), ", '", str(ar), "')"])]*mTEPES.pRatedMaxPower[gc]*mTEPES.pAvailability[gc]() for p,sc,st,ar,gc in sPSSTARGC], index=pd.Index(sPSSTARGC))
            OutputToResRev /= 1e3
            OutputToResRev = OutputToResRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1'], columns='level_4', values='MEUR').rename_axis(['Stages', 'Areas'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            ResRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            for g in OutputToResRev.index:
                ResRev[g] = OutputToResRev[g]
        else:
            ResRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        ResRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pOperReserveUp[:,:,:,:]) and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)):
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]):
            sPSSTNARNR    = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveUp_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveUp   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUp_'+CaseName+'.csv', sep=',')

        if len([(p,sc,n,ar,eh) for p,sc,n,ar,eh in mTEPES.psn*mTEPES.ar*mTEPES.eh if (ar,eh) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]):
            sPSSTNARES    = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.eh if (ar,eh) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveUp_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUpESS_'+CaseName+'.csv', sep=',')

        if len([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.psn*mTEPES.ar*mTEPES.gc if (ar,ec) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]):
            sPSSTNAREC    = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.ec if (ar,ec) in mTEPES.a2g and mTEPES.pOperReserveUp[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveUp_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,ec]() for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
            if len(OutputResults):
                OutputToUpRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            else:
                OutputToUpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            UpRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

            for g in OutputToUpRev.index:
                UpRev[g] = OutputToUpRev[g]
        else:
            UpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        UpRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pOperReserveDw[:,:,:,:]) and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)):
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pOperReserveDw[p,sc,n,ar]]):
            sPSSTNARNR    = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pOperReserveDw[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveDw_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDw_'+CaseName+'.csv', sep=',')

        if len([(p,sc,n,ar,eh) for p,sc,n,ar,eh in mTEPES.psn*mTEPES.ar*mTEPES.eh if (ar,eh) in mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar]]):
            sPSSTNARES    = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.eh if (ar,eh) in mTEPES.a2g and mTEPES.pOperReserveDw[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveDw_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDwESS_'+CaseName+'.csv', sep=',')

        if len([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.psn*mTEPES.ar*mTEPES.gc if (ar,ec) in mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar]]):
            sPSSTNAREC    = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.ps*mTEPES.s2n*mTEPES.ar*mTEPES.ec if (ar,ec) in mTEPES.a2g and mTEPES.pOperReserveDw[p,sc,n,ar]]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join(["eOperReserveUp_", str(p), "_", str(sc), "_", str(st), "('", str(n), "', '", str(ar), "')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,ec]() for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
            if len(OutputResults):
                OutputToDwRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            else:
                OutputToDwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            DwRev             = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            for g in OutputToDwRev.index:
                DwRev[g] = OutputToDwRev[g]
        else:
            DwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        DwRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if len(mTEPES.gc):
        InvCost = pd.Series(data=[sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p in mTEPES.p) for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        Balance = pd.Series(data=[GenRev[gc]+ChargeRev[gc]+UpRev[gc]+DwRev[gc]+ResRev[gc]-InvCost[gc]                   for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        CostRecoveryESS = pd.concat([GenRev,ChargeRev,UpRev,DwRev,ResRev,InvCost,Balance], axis=1, keys=['Generation revenue [MEUR]', 'Consumption revenue [MEUR]', 'Up reserve revenue [MEUR]', 'Down reserve revenue [MEUR]', 'Reserve capacity revenue [MEUR]', 'Investment Cost [MEUR]', 'Balance [MEUR]'])
        CostRecoveryESS.stack().to_frame(name='MEUR').reset_index().pivot_table(values='MEUR', index=['level_1'], columns=['level_0']).rename_axis([None], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_CostRecovery_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing             economic results   ... ', round(WritingResultsTime), 's')


def NetworkMapResults(DirName, CaseName, OptModel, mTEPES):
    # %% plotting the network in a map
    _path = os.path.join(DirName, CaseName)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # Sub functions
    def oT_make_series(_var, _sets, _factor):
        return pd.Series(data=[_var[p,sc,n,ni,nf,cc]()*_factor for p,sc,n,ni,nf,cc in _sets], index=pd.Index(list(_sets)))

    def oT_selecting_data(p,sc,n):
        # Nodes data
        pio.renderers.default = 'chrome'

        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] =  0.0
        loc_df['Zone'  ] =  ''
        loc_df['Demand'] =  0.0
        loc_df['Size'  ] = 15.0

        for nd,zn in mTEPES.ndzn:
            loc_df['Lon'   ][nd] = mTEPES.pNodeLon[nd]
            # warnings
            loc_df['Zone'  ][nd] = zn
            loc_df['Demand'][nd] = mTEPES.pDemand[p,sc,n,nd]*1e3

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlow, mTEPES.psnla, 1e3)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        # tolerance to consider avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pLineNTCFrw[i] * 1e3 + pEpsilon for i in mTEPES.la], index=mTEPES.la),
                                     'NTCBck': pd.Series(data=[mTEPES.pLineNTCBck[i] * 1e3 + pEpsilon for i in mTEPES.la], index=mTEPES.la)}, index=mTEPES.la)

        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=True)
        line_df['vFlow'      ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = ''
        line_df['voltage'    ] = 0.0
        line_df['width'      ] = 0.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = '0.0'
        line_df['nf'         ] = '0.0'
        line_df['cc'         ] = 0.0

        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        for ni,nf,cc in mTEPES.la:
            line_df['vFlow'      ][ni,nf] += OutputToFile['MW'][p,sc,n,ni,nf,cc]
            line_df['utilization'][ni,nf]  = max(line_df['vFlow'][ni,nf]/line_df['NTCFrw'][ni,nf],-line_df['vFlow'][ni,nf]/line_df['NTCBck'][ni,nf])*100.0
            line_df['lon'        ][ni,nf]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df['lat'        ][ni,nf]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
            line_df['ni'         ][ni,nf]  = ni
            line_df['nf'         ][ni,nf]  = nf
            line_df['cc'         ][ni,nf] += 1

            for i in range(len(colors)):
                if 10*i <= line_df['utilization'][ni,nf] <= 10*(i+1):
                    line_df['color'][ni,nf] = colors[i]

            # assigning black color to lines with utilization > 100%
            if line_df['utilization'][ni,nf] > 100:
                line_df['color'][ni,nf] = 'rgb(0,0,0)'

            line_df['voltage'][ni,nf] = mTEPES.pLineVoltage[ni,nf,cc]
            if   700 < line_df['voltage'][ni,nf] <= 900:
                line_df['width'][ni,nf] = 4
            elif 500 < line_df['voltage'][ni,nf] <= 700:
                line_df['width'][ni,nf] = 3
            elif 350 < line_df['voltage'][ni,nf] <= 500:
                line_df['width'][ni,nf] = 2.5
            elif 290 < line_df['voltage'][ni,nf] <= 350:
                line_df['width'][ni,nf] = 2
            elif 200 < line_df['voltage'][ni,nf] <= 290:
                line_df['width'][ni,nf] = 1.5
            elif  50 < line_df['voltage'][ni,nf] <= 200:
                line_df['width'][ni,nf] = 1
            else:
                line_df['width'][ni,nf] = 0.5

        # Rounding to decimals
        line_df = line_df.round(decimals=2)

        return loc_df, line_df

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    p = list(mTEPES.p)[0]
    n = list(mTEPES.n)[0]

    if len(mTEPES.sc) > 1:
        for scc in mTEPES.sc:
            if (p,scc) in mTEPES.ps:
                if abs(mTEPES.pScenProb[p,scc]() - 1.0) < pEpsilon:
                    sc = scc
    else:
        sc = list(mTEPES.sc)[0]

    loc_df, line_df = oT_selecting_data(p,sc,n)

    # Making the network
    # Get node position dict
    x, y = loc_df['Lon'].values, loc_df['Lat'].values
    pos_dict = {}
    for index, iata in enumerate(loc_df['index']):
        pos_dict[iata] = (x[index], y[index])

    # Setting up the figure
    token = open(DIR+'/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni,nf,cc in mTEPES.la:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'titleside': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df['width'][ni,nf], color=line_df['color'][ni,nf]), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlow'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': 'Power Network: '+CaseName+'<br>Period: '+str(p)+'; Scenario: '+str(sc)+'; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(_path+'/oT_Plot_MapNetwork_'+CaseName+'.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting  electric network maps        ... ', round(PlottingNetMapsTime), 's')
