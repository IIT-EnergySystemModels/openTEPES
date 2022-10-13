"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - October 13, 2022
"""

import time
import os
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
    OutputToPlot          = df.reset_index().groupby(['level_3']).sum()
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
    selection = alt.selection_multi(fields=[Category], bind='legend')

    # base  = alt.Chart(Results).mark_area().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=C_C)
    base  = alt.Chart(Results).mark_area().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2))).add_selection(selection)
    chart = base.encode(x=alt.X(C_X, axis=alt.Axis(title=''), scale=alt.Scale(domain=interval.ref()))).properties(width=1200, height=450)
    view  = base.add_selection(interval).properties(width=1200, height=50)
    plot  = chart & view

    return plot


# Definition of Line plots
def LinePlots(period, scenario, df, Category, X, Y, OperationType):
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
    selection = alt.selection_multi(fields=[Category], bind='legend')

    # base  = alt.Chart(Results).mark_line().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=C_C)
    base  = alt.Chart(Results).mark_line().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2))).add_selection(selection)
    chart = base.encode(x=alt.X(C_X, axis=alt.Axis(title=''), scale=alt.Scale(domain=interval.ref()))).properties(width=1200, height=450)
    view  = base.add_selection(interval).properties(width=1200, height=50)
    plot  = chart & view

    return plot


def InvestmentResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the investment decisions
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.gc):
        # Saving generation investment into CSV file
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,gc]()                               for p,gc in mTEPES.p*mTEPES.gc], index=pd.Index(mTEPES.p*mTEPES.gc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='InvestmentDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='InvestmentDecision').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_GenerationInvestment_PerUnit_'+CaseName+'.csv', sep=',', index=True)
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,gc]()*mTEPES.pRatedMaxPower[gc]*1e3 for p,gc in mTEPES.p*mTEPES.gc], index=pd.Index(mTEPES.p*mTEPES.gc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_GenerationInvestment_'+CaseName+'.csv', sep=',', index=False)
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if len(mTEPES.ar) > 1:
            GenInvestToArea   = pd.Series(data=[OutputToFile['MW'][p,gc] for p,ar,gc in mTEPES.p*mTEPES.ar*mTEPES.gc if (ar,gc) in mTEPES.a2g], index=pd.MultiIndex.from_tuples((p,ar,gc) for p,ar,gc in mTEPES.p*mTEPES.ar*mTEPES.gc if (ar,gc) in mTEPES.a2g)).to_frame(name='MW')
            GenInvestToArea.index.names = ['Period', 'Area', 'Generating unit']
            chart = alt.Chart(GenInvestToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
            chart.save(_path+'/oT_Plot_GenerationInvestmentPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})
            TechInvestToArea  = pd.Series(data=[sum(OutputToFile['MW'][p,gc] for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g and (gt,gc) in mTEPES.t2g) for p,ar,gt in mTEPES.p*mTEPES.ar*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.p*mTEPES.ar*mTEPES.gt)).to_frame(name='MW')
            TechInvestToArea.index.names = ['Period', 'Area', 'Technology']
            chart = alt.Chart(TechInvestToArea.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
            chart.save(_path+'/oT_Plot_TechnologyInvestmentPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})

        # Ordering data to plot the investment decision
        OutputResults1 = pd.Series(data=[gt for p,gc,gt in mTEPES.p*mTEPES.gc*mTEPES.gt if (gt,gc) in mTEPES.t2g], index=pd.Index(mTEPES.p*mTEPES.gc))
        OutputResults1 = OutputResults1.to_frame(name='Technology')
        OutputResults2 = OutputToFile
        OutputResults   = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'Generating unit']
        OutputResults   = OutputResults.reset_index().groupby(['Period', 'Technology']).sum()
        OutputResults['MW'] = round(OutputResults['MW'], 2)
        OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_TechnologyInvestment_'+CaseName+'.csv', sep=',', index=True)
        OutputResults = OutputResults.reset_index()

        chart = alt.Chart(OutputResults).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

        # Saving and plotting generation investment cost into CSV file
        OutputResults0 = OutputResults.set_index(['Period', 'Technology'])
        OutputToFile = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.p*mTEPES.gc], index=pd.Index(mTEPES.p*mTEPES.gc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MEUR').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        OutputResults1 = pd.Series(data=[gt for p,gc,gt in mTEPES.p*mTEPES.gc*mTEPES.gt if (gt,gc) in mTEPES.t2g], index=pd.Index(mTEPES.p*mTEPES.gc))
        OutputResults1 = OutputResults1.to_frame(name='Technology')
        OutputResults2 = OutputToFile
        OutputResults   = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'Generating unit']
        OutputResults   = OutputResults.reset_index().groupby(['Period', 'Technology']).sum()
        OutputResults['MEUR'] = round(OutputResults['MEUR'], 2)

        OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_TechnologyInvestmentCost_'+CaseName+'.csv', sep=',', index=True)

        chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyInvestmentCost_'+CaseName+'.html', embed_options={'renderer':'svg'})

        OutputResults = OutputResults['MEUR']/OutputResults0['MW']
        OutputResults = OutputResults.fillna(0).to_frame(name='MEUR/MW')
        OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR/MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_TechnologyInvestmentCostPerMW_'+CaseName+'.csv', sep=',', index=True)

        chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR/MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyInvestmentCostPerMW_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.gd):
        # Saving generation retirement into CSV file
        OutputToFile = pd.Series(data=[mTEPES.pRatedMaxPower[gd]*OptModel.vGenerationRetire[p,gd]()*1e3 for p,gd in mTEPES.p*mTEPES.gd], index=pd.Index(mTEPES.p*mTEPES.gd))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_GenerationRetirement_'+CaseName+'.csv', sep=',', index=True)
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if len(mTEPES.ar) > 1:
            GenRetireToArea   = pd.Series(data=[OutputToFile['MW'][p,gd] for p,ar,gd in mTEPES.p*mTEPES.ar*mTEPES.gd if (ar,gd) in mTEPES.a2g], index=pd.MultiIndex.from_tuples((p,ar,gd) for p,ar,gd in mTEPES.p*mTEPES.ar*mTEPES.gd if (ar,gd) in mTEPES.a2g)).to_frame(name='MW')
            GenRetireToArea.index.names = ['Period', 'Area', 'Generating unit']
            chart = alt.Chart(GenRetireToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
            chart.save(_path+'/oT_Plot_GenerationRetirementPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})
            TechRetireToArea  = pd.Series(data=[sum(OutputToFile['MW'][p,gd] for gd in mTEPES.gd if (ar,gd) in mTEPES.a2g and (gt,gd) in mTEPES.t2g) for p,ar,gt in mTEPES.p*mTEPES.ar*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.p*mTEPES.ar*mTEPES.gt)).to_frame(name='MW')
            TechRetireToArea.index.names = ['Period', 'Area', 'Technology']
            chart = alt.Chart(TechRetireToArea.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
            chart.save(_path+'/oT_Plot_TechnologyRetirementPerArea_'+CaseName+'.html', embed_options={'renderer':'svg'})

        # Ordering data to plot the investment retirement
        OutputResults1 = pd.Series(data=[gt for p,gd,gt in mTEPES.p*mTEPES.gd*mTEPES.gt if (gt,gd) in mTEPES.t2g], index=pd.Index(mTEPES.p*mTEPES.gd))
        OutputResults1 = OutputResults1.to_frame(name='Technology')
        OutputResults2 = OutputToFile
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'Generating unit']
        OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum()
        OutputResults['MW'] = round(OutputResults['MW'], 2)
        OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis([None], axis=0).to_csv(_path+'/oT_Result_TechnologyRetirement_'+CaseName+'.csv', sep=',', index=False)
        OutputResults  = OutputResults.reset_index()

        chart = alt.Chart(OutputResults).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyRetirement_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.lc):
        # Saving investment decisions
        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.p*mTEPES.lc], index=pd.Index(mTEPES.p*mTEPES.lc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='Investment Decision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'InitialNode', 'level_2': 'FinalNode', 'level_3': 'Circuit'})
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='Investment Decision').rename_axis([None,None,None], axis=1).rename_axis([None], axis=0).to_csv(_path+'/oT_Result_NetworkInvestment_'+CaseName+'.csv', sep=',', index=True)

        # Ordering data to plot the investment decision
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.p*mTEPES.lc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.p*mTEPES.lc))
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults   = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults   = OutputResults.reset_index().groupby(['LineType', 'Period']).sum()
        OutputResults['Investment Decision'] = round(OutputResults['Investment Decision'], 2)
        OutputResults   = OutputResults.reset_index()

        chart = alt.Chart(OutputResults).mark_bar().encode(x='LineType:O', y='sum(Investment Decision):Q', color='LineType:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_NetworkInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineNTCFrw[ni,nf,cc]/mTEPES.pLineLength[ni,nf,cc]()*1e3 for p,ni,nf,cc in mTEPES.p*mTEPES.lc], index= pd.MultiIndex.from_tuples(mTEPES.p*mTEPES.lc))
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW-km').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'InitialNode', 'level_2': 'FinalNode', 'level_3': 'Circuit'})
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='MW-km').rename_axis([None,None,None], axis=1).rename_axis([None], axis=0).to_csv(_path+'/oT_Result_NetworkInvestment_MWkm_'+CaseName+'.csv', sep=',')

        # Ordering data to plot the investment decision per kilometer
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.p*mTEPES.lc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.p*mTEPES.lc))
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults   = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults   = OutputResults.reset_index().groupby(['LineType', 'Period']).sum()
        OutputResults['MW-km'] = round(OutputResults['MW-km'], 2)
        OutputResults   = OutputResults.reset_index()

        chart = alt.Chart(OutputResults).mark_bar().encode(x='LineType:O', y='sum(MW-km):Q', color='LineType:N', column='Period:N')
        chart.save(_path+'/oT_Plot_NetworkInvestment_MW-km_'+CaseName+'.html', embed_options={'renderer':'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing           investment results   ... ', round(WritingResultsTime), 's')


def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.nr):
        OutputToFile = pd.Series(data=[OptModel.vCommitment[p,sc,n,nr]() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
        OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCommitment_'+CaseName+'.csv', sep=',')
        OutputToFile = pd.Series(data=[OptModel.vStartUp   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
        OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationStartUp_'   +CaseName+'.csv', sep=',')
        OutputToFile = pd.Series(data=[OptModel.vShutDown  [p,sc,n,nr]() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
        OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationShutDown_'  +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar):
        if len(mTEPES.nr):
            OutputToFile = pd.Series(data=[OptModel.vReserveUp     [p,sc,n,nr]()*1e3 for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveUp_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveUp_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,es]()*1e3 for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeReserveUp_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveUpESS_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar):
        if len(mTEPES.nr):
            OutputToFile = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,nr]()*1e3 for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveDown_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveDown_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,es]()*1e3 for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeReserveDown_'       +CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveDownESS_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]()*1e3                                             for p,sc,n,g  in mTEPES.ps*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.g ))
    OutputToFile.to_frame(name='MW ').reset_index().pivot_table(index=['level_0','level_1','level_2'],        columns='level_3', values='MW ').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutput_'       +CaseName+'.csv', sep=',')

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    SurplusGens  = [(p,sc,n,g) for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pEpsilon]
    OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]())*1e3 for p,sc,n,g in SurplusGens], index=pd.MultiIndex.from_tuples(SurplusGens))
    for p,sc,n,g in SurplusGens:
        if g in mTEPES.gc:
            OutputToFile[p,sc,n,g] *= OptModel.vGenerationInvest[p,g]()
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationSurplus_'+CaseName+'.csv', sep=',')

    OutputResults = []
    for p,sc,st in mTEPES.ps*mTEPES.st:
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        if len(mTEPES.n*mTEPES.nr):
            RampSurplusGens = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first()]
            if len(RampSurplusGens):
                OutputToFile = pd.Series(data=[(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampUp[nr]*1e3*(mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,n,nr in RampSurplusGens], index=pd.MultiIndex.from_tuples(RampSurplusGens))
                OutputResults.append(OutputToFile)
            RampSurplusGens = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first()]
            if len(RampSurplusGens):
                OutputToFile = pd.Series(data=[(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampUp[nr]*1e3*(OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,n,nr in RampSurplusGens], index=pd.MultiIndex.from_tuples(RampSurplusGens))
                OutputResults.append(OutputToFile)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
    if len(OutputResults):
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW/h', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationRampUpSurplus_'+CaseName+'.csv', sep=',')

    OutputResults = []
    for p,sc,st in mTEPES.ps*mTEPES.st:
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        if len(mTEPES.n*mTEPES.nr):
            RampSurplusGens = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first()]
            if len(RampSurplusGens):
                OutputToFile = pd.Series(data=[(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampDw[nr]*1e3*(- mTEPES.pInitialUC[p,sc,n,nr]()                   + OptModel.vShutDown[p,sc,n,nr]()) for p,sc,n,nr in RampSurplusGens], index=pd.MultiIndex.from_tuples(RampSurplusGens))
                OutputResults.append(OutputToFile)
            RampSurplusGens = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first()]
            if len(RampSurplusGens):
                OutputToFile = pd.Series(data=[(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nr].uslack())*mTEPES.pDuration[n]()*mTEPES.pRampDw[nr]*1e3*(- OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() + OptModel.vShutDown[p,sc,n,nr]()) for p,sc,n,nr in RampSurplusGens], index=pd.MultiIndex.from_tuples(RampSurplusGens))
                OutputResults.append(OutputToFile)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
    if len(OutputResults):
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW/h', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationRampDwSurplus_'+CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,r].ub - OptModel.vTotalOutput[p,sc,n,r]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.r))
        OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,r].ub                                    )*mTEPES.pLoadLevelDuration[n]() for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.r))
        for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r:
            if r in mTEPES.gc:
                OutputToFile1[p,sc,n,r] *= OptModel.vGenerationInvest[p,r]()
                OutputToFile2[p,sc,n,r] *= OptModel.vGenerationInvest[p,r]()
        OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
        OutputToFile.to_csv(_path+'/oT_Result_GenerationCurtailmentEnergyRelative_'+CaseName+'.csv', sep=',')

        OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,r] for r in mTEPES.r if (rt,r) in mTEPES.t2g) for p,sc,rt in mTEPES.ps*mTEPES.rt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.rt))
        OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,r] for r in mTEPES.r if (rt,r) in mTEPES.t2g) for p,sc,rt in mTEPES.ps*mTEPES.rt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.rt))
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='%').to_csv(_path+'/oT_Result_TechnologyCurtailmentEnergyRelative_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,r].ub - OptModel.vTotalOutput[p,sc,n,r]())*1e3  for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.r))
        for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r:
            if r in mTEPES.gc:
                OutputToFile[p,sc,n,r] *= OptModel.vGenerationInvest[p,r]()
        OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCurtailmentOutput_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,r].ub - OptModel.vTotalOutput[p,sc,n,r]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.r))
        for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r:
            if r in mTEPES.gc:
                OutputToFile[p,sc,n,r] *= OptModel.vGenerationInvest[p,r]()
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCurtailmentEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,r] for r in mTEPES.r if (rt,r) in mTEPES.t2g) for p,sc,n,rt in mTEPES.ps*mTEPES.n*mTEPES.rt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.rt))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(           index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCurtailmentEnergy_'+CaseName+'.csv', sep=',')
        TechCurt = OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum().rename(columns={0: 'GWh'})
        TechCurt = TechCurt[(TechCurt[['GWh']] != 0).all(axis=1)]

        TechCurt = TechCurt.reset_index()

        chart = alt.Chart(TechCurt).mark_bar().encode(x='Technology', y='GWh', color='Scenario:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyCurtailmentOutput_'+CaseName+'.html', embed_options={'renderer':'svg'})

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g  in mTEPES.ps*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.g ))
    OutputToFile.to_frame(name='GWh'  ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh'  , aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEnergy_'+CaseName+'.csv', sep=',')

    if len(mTEPES.nr):
        OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,nr]()*mTEPES.pLoadLevelDuration[n]()*mTEPES.pCO2EmissionCost[nr]/mTEPES.pCO2Cost() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
        OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEmission_'+CaseName+'.csv', sep=',')

        for ar in mTEPES.ar:
            if len(mTEPES.ar) > 1:
                TechList = [(p,sc,n,gt,nr) for p,sc,n,gt,nr in mTEPES.ps*mTEPES.n*mTEPES.gt*mTEPES.nr if (ar,nr) in mTEPES.a2g and (gt,nr) in mTEPES.t2g]
                if len(TechList):
                    OutputResults= pd.Series(data=[OutputToFile[p,sc,n,nr] for p,sc,n,gt,nr in mTEPES.ps*mTEPES.n*mTEPES.gt*mTEPES.nr if (ar,nr) in mTEPES.a2g and (gt,nr) in mTEPES.t2g], index=pd.MultiIndex.from_tuples(TechList))
                    OutputResults.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEmission_'+ar+'_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(          index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEmission_'+CaseName+'.csv', sep=',')
        TechCO2 = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum().rename(columns={0: 'MtCO2'})
        TechCO2 = TechCO2[(TechCO2[['MtCO2']] != 0).all(axis=1)]

    if len(TechCO2):
        TechCO2 = TechCO2.reset_index()

        chart = alt.Chart(TechCO2).mark_bar().encode(x='Technology', y='MtCO2', color='Scenario:N', column='Period:N').properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyEmission_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutput_'+CaseName+'.csv', sep=',')

    TechnologyOutput = OutputToFile.loc[:,:,:,:]

    for p,sc in mTEPES.ps:
        chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
        chart.save(_path+'/oT_Plot_TechnologyOutput_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.g ))
    OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in mTEPES.g if (gt,g) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+CaseName+'.csv', sep=',')

    for p,sc in mTEPES.ps:
        chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
        chart.save(_path+'/oT_Plot_TechnologyEnergy_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    for ar in mTEPES.ar:
        if len(mTEPES.ar) > 1:
            OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.g ))
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in mTEPES.g if (ar,g) in mTEPES.a2g and (gt,g) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(_path+'/oT_Plot_TechnologyEnergy_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing generation operation results   ... ', round(WritingResultsTime), 's')


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the ESS operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.es):
        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]()*1e3 for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflows_'        +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflows_'        +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [p,sc,n,es]()*1e3 for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeOutput_'              +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutputESS_'       +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [p,sc,n,es]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeEnergy_'            +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis             (['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergyESS_'     +CaseName+'.csv', sep=',')

        OutputToFile *= -1.0
        if OutputToFile.sum() < 0.0:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(_path+'/oT_Plot_TechnologyEnergyESS_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        for ar in mTEPES.ar:
            if len(mTEPES.ar) > 1:
                OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [p,sc,n,es]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g and (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
                OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergyESS_'+ar+'_'+CaseName+'.csv', sep=',')

                OutputToFile *= -1.0
                if OutputToFile.sum() < 0.0:
                    for p,sc in mTEPES.ps:
                        chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                        chart.save(_path+'/oT_Plot_TechnologyEnergyESS_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        InventoryConstraints = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es if mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0]
        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()                               for p,sc,n,es in InventoryConstraints], index=pd.MultiIndex.from_tuples(list(InventoryConstraints)))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationInventory_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()/mTEPES.pMaxStorage[p,sc,n,es] for p,sc,n,es in InventoryConstraints], index=pd.MultiIndex.from_tuples(list(InventoryConstraints)))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False, aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationInventoryUtilization_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSSpillage[p,sc,n,es]()                                for p,sc,n,es in InventoryConstraints], index=pd.MultiIndex.from_tuples(list(InventoryConstraints)))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationSpillage_'+CaseName+'.csv', sep=',')

        ESSTechnologies = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot if sum(1 for es in mTEPES.es if (ot,es) in mTEPES.t2g)]
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g and mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0) for p,sc,n,ot in ESSTechnologies], index=pd.MultiIndex.from_tuples(ESSTechnologies))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologySpillage_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge[p,sc,n,es]()*1e3 for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCharge_'+CaseName+'.csv', sep=',')

        TechnologyCharge = OutputToFile.loc[:,:,:,:]

        for p,sc in mTEPES.ps:
            chart = AreaPlots(p, sc, TechnologyCharge, 'Technology', 'LoadLevel', 'MW', 'sum')
            chart.save(_path+'/oT_Plot_TechnologyCharge_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub                                     )*mTEPES.pLoadLevelDuration[n]() for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es:
            if es in mTEPES.gc:
                OutputToFile1[p,sc,n,es] *= OptModel.vGenerationInvest[p,es]()
                OutputToFile2[p,sc,n,es] *= OptModel.vGenerationInvest[p,es]()
        OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
        OutputToFile.to_csv(_path+'/oT_Result_GenerationSpillageRelative_'+CaseName+'.csv', sep=',')

        OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,ot in mTEPES.ps*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.ot))
        OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for p,sc,ot in mTEPES.ps*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.ot))
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='%').to_csv(_path+'/oT_Result_TechnologySpillageRelative_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing        ESS operation results   ... ', round(WritingResultsTime), 's')


def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
    TechnologyOutput     = OutputToFile.loc[:,:,:,:]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput  = pd.Series([0.0]*len(mTEPES.ps*mTEPES.n*mTEPES.gt), index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
    for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt:
        NetTechnologyOutput[p,sc,n,gt] = TechnologyOutput[p,sc,n,gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnology_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        ESSTechnologies = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.ps*mTEPES.n*mTEPES.ot if sum(1 for es in mTEPES.es if (ot,es) in mTEPES.t2g)]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,es]() for es in mTEPES.es if (ot,es) in mTEPES.t2g)*1e3 for p,sc,n,ot in ESSTechnologies], index=pd.MultiIndex.from_tuples(ESSTechnologies))
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput = pd.Series([0.0] * len(ESSTechnologies), index=pd.MultiIndex.from_tuples(ESSTechnologies))
        for p,sc,n,gt in ESSTechnologies:
            NetESSTechnologyOutput[p,sc,n,gt] = MeanESSTechnologyOutput[gt] - ESSTechnologyOutput[p,sc,n,gt]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnologyESS_'+CaseName+'.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemand[p,sc,n,nd] for nd in mTEPES.nd)*1e3              for p,sc,n in mTEPES.ps*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemand[p,sc,n,nd] for nd in mTEPES.nd)*1e3 - MeanDemand for p,sc,n in mTEPES.ps*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n))
    OutputToFile.to_frame(name='Demand').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityDemand_'+CaseName+'.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in mTEPES.nd)*1e3           for p,sc,n in mTEPES.ps*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]()*1e3 for nd in mTEPES.nd) - MeanENS for p,sc,n in mTEPES.ps*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n))
    OutputToFile.to_frame(name='PNS'   ).reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityPNS_'   +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing          flexibility results   ... ', round(WritingResultsTime), 's')


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the network operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[OptModel.vLineCommit  [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkCommitment_'+CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOnState [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOn_'  +CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOffState[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOff_' +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]()*1e3 for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkFlow_'       +CaseName+'.csv', sep=',')

    if len(mTEPES.la):
        OutputResults = pd.Series(data=[OptModel.vFlow[p,sc,n,ni,nf,cc]()*(mTEPES.pDuration[n]()*mTEPES.pLoadLevelWeight[n]()*mTEPES.pPeriodWeight[p]*mTEPES.pScenProb[p,sc])/mTEPES.pLineLength[ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.p*mTEPES.sc*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.p*mTEPES.sc*mTEPES.n*mTEPES.la))
        OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
        OutputResults = OutputResults.reset_index().groupby(['InitialNode', 'FinalNode', 'Circuit']).sum()[0]
        OutputResults.index.names = [None] * len(OutputResults.index.names)
        OutputResults.to_frame(name='GWh-km').to_csv(_path+'/oT_Result_NetworkEnergyTransport_'+CaseName+'.csv', sep=',')

    # tolerance to consider avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlow[p,sc,n,ni,nf,cc]()/(mTEPES.pLineNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlow[p,sc,n,ni,nf,cc]()/(mTEPES.pLineNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkUtilization_'+CaseName+'.csv', sep=',')

    if mTEPES.pIndBinNetLosses():
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.ll], index= pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.ll))
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
        OutputToFile.index.names = [None] * len(OutputToFile.index.names)
        OutputToFile.to_csv(_path+'/oT_Result_NetworkLosses_' +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTheta[p,sc,n,nd]()                              for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()*1e3                            for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkPNS_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkENS_'  +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    network operation results   ... ', round(WritingResultsTime), 's')


def MarginalResults(DirName, CaseName, OptModel, mTEPES):
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    #%% outputting the incremental variable cost of each generator with power surplus
    SurplusGens  = [(p,sc,n,g) for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pEpsilon and g not in mTEPES.es]
    OutputToFile = pd.Series(data=[(mTEPES.pLinearVarCost[g]+mTEPES.pCO2EmissionCost[g])*1e3 for p,sc,n,g in SurplusGens], index=pd.MultiIndex.from_tuples(SurplusGens))

    OutputToFile = OutputToFile.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='EUR/MWh')
    OutputToFile.rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalIncrementalVariableCost_'+CaseName+'.csv', sep=',')
    IncrementalGens = pd.Series(data=[0 for p,sc,n in list([(p,sc,n) for p,sc,n,g in SurplusGens])], index=pd.MultiIndex.from_tuples(list([(p,sc,n) for p,sc,n,g in SurplusGens]))).to_frame(name='Generator')
    for p,sc,n in list([(p,sc,n) for p,sc,n,g in SurplusGens]):
        IncrementalGens['Generator'][p,sc,n] = OutputToFile.loc[[(p,sc,n)]].squeeze().idxmin()
    IncrementalGens.to_csv(_path+'/oT_Result_MarginalIncrementalGenerator_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pCO2EmissionRate[g] for p,sc,n,g in SurplusGens], index=pd.MultiIndex.from_tuples(SurplusGens))
    OutputToFile.to_frame(name='tCO2/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tCO2/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationIncrementalEmission_'+CaseName+'.csv', sep=',')

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    #%% outputting the LSRMC
    OutputResults = []
    for p,sc,st in mTEPES.ps*mTEPES.st:
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]()*1e3 for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))))
        OutputResults.append(OutputToFile)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
    OutputResults = pd.concat(OutputResults)
    OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='LSRMC').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkSRMC_'+CaseName+'.csv', sep=',')

    OptModel.LSRMC = OutputResults.loc[:,:,:,:]

    for p,sc in mTEPES.ps:
        chart = LinePlots(p, sc, OptModel.LSRMC, 'Node', 'LoadLevel', 'EUR/MWh', 'average')
        chart.save(_path+'/oT_Plot_NetworkSRMC_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if sum(mTEPES.pReserveMargin[ar] for ar in mTEPES.ar):
        OutputResults = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                ListOfIndex_1  = [ar     for ar in mTEPES.ar if mTEPES.pReserveMargin[ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)]
                ListOfIndex_2  = [(p,ar) for ar in mTEPES.ar if mTEPES.pReserveMargin[ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)]
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st))[p,ar]] for ar in ListOfIndex_1], index=pd.MultiIndex.from_tuples(ListOfIndex_2))
                OutputResults.append(OutputToFile)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0'], columns=['level_1'], values='RM').rename_axis(['Period'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalReserveMargin_'+CaseName+'.csv', sep=',')

    #%% outputting the up operating reserve marginal
    if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar) > 0.0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        OutputResults = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*1e3 for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveUp[p,sc,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))))
            OutputResults.append(OutputToFile)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='UORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveUp_'+CaseName+'.csv', sep=',')

        MarginalUpOperatingReserve = OutputResults.loc[:,:,:,:]

        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, MarginalUpOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
            chart.save(_path+'/oT_Plot_MarginalOperatingReserveUpward_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the down operating reserve marginal
    if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar) > 0.0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        OutputResults = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*1e3 for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveDw[p,sc,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))))
            OutputResults.append(OutputToFile)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='DORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveDown_'+CaseName+'.csv', sep=',')

        MarginalDwOperatingReserve = OutputResults.loc[:,:,:,:]

        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, MarginalDwOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
            chart.save(_path+'/oT_Plot_MarginalOperatingReserveDownward_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the water values
    if len(mTEPES.es):
        OutputResults = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                InventoryConstraints = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es if mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0]
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eESSInventory_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,es]]/mTEPES.pPeriodProb[p,sc]()*1e3 for p,sc,n,es in InventoryConstraints], index=pd.MultiIndex.from_tuples(list(InventoryConstraints)))
            InventoryConstraints = []
            OutputResults.append(OutputToFile)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalWaterValue_'+CaseName+'.csv', sep=',')

        WaterValue = OutputResults.loc[:,:,:,:]

        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, WaterValue, 'Generating unit', 'LoadLevel', 'EUR/MWh', 'average')
            chart.save(_path+'/oT_Plot_MarginalWaterValue_'+str(p)+'_'+str(sc)+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% Reduced cost for NetworkInvestment
    ReducedCostActivation = mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)
    if len(mTEPES.lc) and not ReducedCostActivation and OptModel.vNetworkInvest.is_variable_type():
        OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[p,ni,nf,cc]] for p,ni,nf,cc in mTEPES.p*mTEPES.lc], index=pd.MultiIndex.from_tuples(mTEPES.p*mTEPES.lc))
        OutputToFile.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile.to_frame(name='MEUR').to_csv(_path+'/oT_Result_NetworkInvestment_ReducedCost_'+CaseName+'.csv', sep=',')

    #%% Reduced cost for NetworkCommitment
    mTEPES.las = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all real lines with switching decision', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in mTEPES.pLineX and mTEPES.pIndBinLineSwitch[ni,nf,cc])
    if len(mTEPES.las) and not ReducedCostActivation and OptModel.vLineCommit.is_variable_type():
        OutputResults = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[p,sc,n,ni,nf,cc]] for p,sc,n,ni,nf,cc in mTEPES.ps*mTEPES.n*mTEPES.las], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.las))
        OutputResults.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = pd.pivot_table(OutputResults.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
        OutputResults.index.names = [None] * len(OutputResults.index.names)
        OutputResults.to_csv(_path+'/oT_Result_NetworkCommitment_ReducedCost_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing marginal information results   ... ', round(WritingResultsTime), 's')


def ResultsKPI(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the KPIs
    _path = os.path.join(DirName, CaseName)
    StartTime   = time.time()

    # Ratio Fossil Fuel Generation/Total Generation [%]
    TotalGeneration      = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g                 )
    FossilFuelGeneration = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g if g in mTEPES.t)
    # Ratio Total Investments [%]
    TotalInvestmentCost  = sum(mTEPES.pDiscountFactor[p] *                                   OptModel.vTotalFCost      [p]()          for p          in mTEPES.p          )
    GenInvestmentCost    = sum(mTEPES.pDiscountFactor[p] * mTEPES.pGenInvestCost[gc]       * OptModel.vGenerationInvest[p,gc]()       for p,gc       in mTEPES.p*mTEPES.gc)
    GenRetirementCost    = sum(mTEPES.pDiscountFactor[p] * mTEPES.pGenRetireCost[gd]       * OptModel.vGenerationRetire[p,gd]()       for p,gd       in mTEPES.p*mTEPES.gd)
    NetInvestmentCost    = sum(mTEPES.pDiscountFactor[p] * mTEPES.pNetFixedCost [ni,nf,cc] * OptModel.vNetworkInvest   [p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.p*mTEPES.lc)
    # Ratio Generation Investment cost/ Generation Installed Capacity [MEUR-MW]
    GenInvCostCapacity   = sum(mTEPES.pGenInvestCost[gc]       *OptModel.vGenerationInvest[p,gc]()/(mTEPES.pRatedMaxPower[gc]*1e3)    for p,gc       in mTEPES.p*mTEPES.gc)
    # Ratio Additional Transmission Capacity-Length [MW-km]
    NetCapacityLength    = sum(max(mTEPES.pLineNTCFrw[ni,nf,cc], mTEPES.pLineNTCBck[ni,nf,cc])*OptModel.vNetworkInvest[p,ni,nf,cc]()*1e3/mTEPES.pLineLength[ni,nf,cc]() for p,ni,nf,cc in mTEPES.p*mTEPES.lc)
    # Ratio Network Investment Cost/Variable RES Injection [EUR/MWh]
    if len(mTEPES.gc):
        NetInvCostVRESInsCap = NetInvestmentCost*1e6/sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[n]()*1e3 for p,sc,n,gc in mTEPES.ps*mTEPES.n*mTEPES.gc if gc in mTEPES.r)
    else:
        NetInvCostVRESInsCap = 0.0
    # Rate of return for VRE technologies
    VRETechRevenue        = sum(OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,st,n,nd,gc in mTEPES.ps*mTEPES.st*mTEPES.n*mTEPES.nd*mTEPES.gc if (nd,gc) in mTEPES.n2g and (st,n) in mTEPES.s2n and gc in mTEPES.r)
    VREInvCostCapacity    = sum(mTEPES.pGenInvestCost[gc]*OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.p*mTEPES.gc if gc in mTEPES.r)

    K1     = pd.Series(data={'Ratio Fossil Fuel Generation/Total Generation [%]'                       : FossilFuelGeneration / TotalGeneration    *1e2}).to_frame(name='Value')
    if GenInvestmentCost:
        K2 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : GenInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K2 = pd.Series(data={'Ratio Generation Investment Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    if GenRetirementCost:
        K3 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : GenRetirementCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K3 = pd.Series(data={'Ratio Generation Retirement Cost/Total Investment Cost [%]'              : 0.0                                           }).to_frame(name='Value')
    if NetInvestmentCost:
        K4 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : NetInvestmentCost    / TotalInvestmentCost*1e2}).to_frame(name='Value')
    else:
        K4 = pd.Series(data={'Ratio Network Investment Cost/Total Investment Cost [%]'                 : 0.0                                           }).to_frame(name='Value')
    if GenInvCostCapacity:
        K5 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': GenInvCostCapacity                            }).to_frame(name='Value')
    else:
        K5 = pd.Series(data={'Ratio Generation Investment Cost/Additional Installed Capacity [MEUR-MW]': 0.0                                           }).to_frame(name='Value')
    if NetCapacityLength:
        K6 = pd.Series(data={'Ratio Additional Transmission Capacity/Line Length [MW-km]'              : NetCapacityLength                             }).to_frame(name='Value')
    else:
        K6 = pd.Series(data={'Ratio Additional Transmission Capacity/Line Length [MW-km]'              : 0.0                                           }).to_frame(name='Value')
    if NetInvCostVRESInsCap:
        K7 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : NetInvCostVRESInsCap                          }).to_frame(name='Value')
    else:
        K7 = pd.Series(data={'Ratio Network Investment Cost/Variable RES Installed Capacity [EUR/MWh]' : 0.0                                           }).to_frame(name='Value')
    if VREInvCostCapacity:
        K8 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : VRETechRevenue       / VREInvCostCapacity*1e2 }).to_frame(name='Value')
    else:
        K8 = pd.Series(data={'Rate of return for VRE technologies [%]'                                 : 0.0                                           }).to_frame(name='Value')

    OutputResults = pd.concat([K1, K2, K3, K4, K5, K6, K7, K8], axis=0)
    OutputResults.to_csv(_path+'/oT_Result_KPIsSummary_'+CaseName+'.csv', sep=',', index=True)

    # LCOE per technology
    if len(mTEPES.gc):
        GenTechInvestCost     = pd.Series(data=[sum(OptModel.vGenerationInvest[p,gc     ]()*mTEPES.pGenInvestCost    [gc]  *1e6  for p,     gc in mTEPES.p*mTEPES.gc           if (gt,gc) in mTEPES.t2g) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection      = pd.Series(data=[sum(OptModel.vTotalOutput     [p,sc,n,gc]()*mTEPES.pLoadLevelDuration[n ]()*1e3  for p,sc,n,gc in mTEPES.ps*mTEPES.n*mTEPES.gc if (gt,gc) in mTEPES.t2g) for gt in mTEPES.gt], index=mTEPES.gt)
        LCOE = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh')
        LCOE.to_csv(_path+'/oT_Result_TechnologyLCOE_'+CaseName+'.csv', sep=',', index=True)

    WritingResultsTime = time.time() - StartTime
    print('Writing          KPI         indexes   ... ', round(WritingResultsTime), 's')

def ReliabilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the reliability indexes
    _path = os.path.join(DirName, CaseName)
    StartTime   = time.time()

    ExistCapacity = [(p,sc,n,g) for p,sc,n,g  in mTEPES.ps*mTEPES.n*mTEPES.g if g not in mTEPES.gc]

    pDemand       = pd.Series(data=[    mTEPES.pDemand  [p,sc,n,nd]                               for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    pExistMaxPower= pd.Series(data=[    mTEPES.pMaxPower[p,sc,n,g ]                               for p,sc,n,g  in ExistCapacity], index=pd.MultiIndex.from_tuples(list(ExistCapacity)))
    if len(mTEPES.gc):
        CandCapacity  = [(p,sc,n,g) for p,sc,n,g  in mTEPES.ps*mTEPES.n*mTEPES.g if g     in mTEPES.gc]
        pCandMaxPower = pd.Series(data=[    mTEPES.pMaxPower[p,sc,n,g ] * OptModel.vGenerationInvest[p,g]() for p,sc,n,g  in CandCapacity] , index=pd.MultiIndex.from_tuples(list(CandCapacity)))
        frames        = [pExistMaxPower, pCandMaxPower]
        pMaxPower     = pd.concat(frames)
    else:
        pMaxPower     = pExistMaxPower

    # Determination of the net demand
    OutputToFile1 = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,r ]()*1e3 for r in mTEPES.r if (nd,r) in mTEPES.n2g) for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile2 = pd.Series(data=[      mTEPES.pDemand     [p,sc,n,nd]  *1e3                                            for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile  = OutputToFile2 - OutputToFile1
    OutputToFile  = OutputToFile.to_frame(name='MW'  )
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkNetDemand_'+CaseName+'.csv', sep=',')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'],                    values='MW', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetDemand_'       +CaseName+'.csv', sep=',')

    # Determination of the index: Reserve Margin
    OutputToFile1 = pd.Series(data=[      0.0 for p,sc in mTEPES.ps], index=pd.MultiIndex.from_tuples(mTEPES.ps))
    OutputToFile2 = pd.Series(data=[      0.0 for p,sc in mTEPES.ps], index=pd.MultiIndex.from_tuples(mTEPES.ps))
    for p,sc in mTEPES.ps:
        OutputToFile1[p,sc] = pMaxPower.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc = sum).max()
        OutputToFile2[p,sc] =   pDemand.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc = sum).max()
    MarginReserve1 = OutputToFile1 - OutputToFile2
    MarginReserve2 = (OutputToFile1 - OutputToFile2)/OutputToFile2
    MarginReserve1.to_frame(name='GW').to_csv(_path+'/oT_Result_MarginReserve_'        +CaseName+'.csv', sep=',', index=True)
    MarginReserve2.to_frame(name='pu').to_csv(_path+'/oT_Result_MarginReserve_PerUnit_'+CaseName+'.csv', sep=',', index=True)

    # Determination of the index: Largest Unit
    OutputToFile = pd.Series(data=[      0.0 for p,sc in mTEPES.ps], index=pd.MultiIndex.from_tuples(mTEPES.ps))
    for p,sc in mTEPES.ps:
        OutputToFile[p,sc] = pMaxPower.loc[(p,sc)].reset_index().pivot_table(index=['level_1'], values=0, aggfunc = max).max()

    LargestUnit  = MarginReserve1/OutputToFile

    LargestUnit.to_frame(name='pu').to_csv(_path+'/oT_Result_LargestUnit_PerUnit_'+CaseName+'.csv', sep=',', index=True)

    # Determination of the index: Loss Of Load Probability (LOLP)

    WritingResultsTime = time.time() - StartTime
    print('Writing          reliability indexes   ... ', round(WritingResultsTime), 's')

def EconomicResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime   = time.time()

    SysCost     = pd.Series(data=[                                                                                                                           OptModel.vTotalSCost()                                                                                                            ], index=[' ']   ).to_frame(name='Total          System Cost').stack()
    GenInvCost  = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pGenInvestCost[gc  ]                                                              * OptModel.vGenerationInvest[p,gc  ]()  for gc      in mTEPES.gc                                             )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation Investment Cost').stack()
    GenRetCost  = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pGenRetireCost[gd  ]                                                              * OptModel.vGenerationRetire[p,gd  ]()  for gd      in mTEPES.gd                                             )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation Retirement Cost').stack()
    NetInvCost  = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pNetFixedCost [lc  ]                                                              * OptModel.vNetworkInvest   [p,lc  ]()  for lc      in mTEPES.lc                                             )     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Network    Investment Cost').stack()
    GenCost     = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pScenProb     [p,sc]                                                              * OptModel.vTotalGCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if mTEPES.pScenProb[p,sc])     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Generation  Operation Cost').stack()
    ConCost     = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pScenProb     [p,sc]                                                              * OptModel.vTotalCCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if mTEPES.pScenProb[p,sc])     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Consumption Operation Cost').stack()
    EmiCost     = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pScenProb     [p,sc]                                                              * OptModel.vTotalECost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if mTEPES.pScenProb[p,sc])     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Emission              Cost').stack()
    RelCost     = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pScenProb     [p,sc]                                                              * OptModel.vTotalRCost      [p,sc,n]()  for sc,n    in mTEPES.sc*mTEPES.n           if mTEPES.pScenProb[p,sc])     for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability           Cost').stack()
    # DemPayment  = pd.Series(data=[mTEPES.pDiscountFactor[p] * sum(mTEPES.pScenProb     [p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pDemand[p,sc,n,nd] * OptModel.LSRMC            [p,sc,n,nd] for sc,n,nd in mTEPES.sc*mTEPES.n*mTEPES.nd if mTEPES.pScenProb[p,sc])/1e3 for p in mTEPES.p], index=mTEPES.p).to_frame(name='Demand Payment'            ).stack()
    # CostSummary = pd.concat([SysCost, GenInvCost, GenRetCost, NetInvCost, GenCost, ConCost, EmiCost, RelCost, DemPayment])
    CostSummary = pd.concat([SysCost, GenInvCost, GenRetCost, NetInvCost, GenCost, ConCost, EmiCost, RelCost])
    CostSummary = CostSummary.reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Cost/Payment', 0: 'MEUR'})
    CostSummary.to_csv(_path+'/oT_Result_CostSummary_'+CaseName+'.csv', sep=',', index=False)

    for ar in mTEPES.ar:
        if len(mTEPES.ar) > 1:
            OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[n]() for p,sc,n,g in mTEPES.ps*mTEPES.n*mTEPES.g], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.g ))
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in mTEPES.g if (ar,g) in mTEPES.a2g and (gt,g) in mTEPES.t2g) for p,sc,n,gt in mTEPES.ps*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(_path+'/oT_Plot_TechnologyEnergy_'+str(p)+'_'+str(sc)+'_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

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

    NodeTech = [(p,sc,n,nd,gt) for p,sc,n,nd,gt in mTEPES.ps*mTEPES.n*mTEPES.nd*mTEPES.gt if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    NodeList = [(p,sc,n,nd)    for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputResults1 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,g       ]()*mTEPES.pLoadLevelDuration[n]() for g  in mTEPES.g  if (nd,g ) in mTEPES.n2g and (gt,g ) in mTEPES.t2g) for p,sc,n,nd,gt in mTEPES.ps*mTEPES.n*mTEPES.nd*mTEPES.gt if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeTech)).to_frame(name='Generation'   ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='Generation' , aggfunc=sum)
    OutputResults2 = pd.Series(data=[-sum(OptModel.vESSTotalCharge[p,sc,n,es      ]()*mTEPES.pLoadLevelDuration[n]() for es in mTEPES.es if (nd,es) in mTEPES.n2g and (gt,es) in mTEPES.t2g) for p,sc,n,nd,gt in mTEPES.ps*mTEPES.n*mTEPES.nd*mTEPES.gt if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeTech)).to_frame(name='Consumption'  ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='Consumption', aggfunc=sum)
    OutputResults3 = pd.Series(data=[     OptModel.vENS           [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[n]()                                                                         for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='PNS'          )
    OutputResults4 = pd.Series(data=[-      mTEPES.pDemand        [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[n]()                                                                         for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='PowerDemand'  )
    OutputResults5 = pd.Series(data=[-sum(OptModel.vFlow          [p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]() for lout  in lout [nd])                                                 for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='PowerFlowOut' )
    OutputResults6 = pd.Series(data=[ sum(OptModel.vFlow          [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]() for ni,cc in lin  [nd])                                                 for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='PowerFlowIn'  )
    OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,nd,lout ]()*mTEPES.pLoadLevelDuration[n]() for lout  in loutl[nd])                                                 for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='LineLossesOut')
    OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[n]() for ni,cc in linl [nd])                                                 for p,sc,n,nd    in mTEPES.ps*mTEPES.n*mTEPES.nd           if sum(1 for g in mTEPES.g if (nd, g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni, cc in lin[nd])], index=pd.MultiIndex.from_tuples(NodeList)).to_frame(name='LineLossesIn' )
    OutputResults   = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2', 'level_4'], columns='level_3', values=0, aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'], axis=0).to_csv(_path+'/oT_Result_BalanceEnergy_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                    mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pConstantVarCost[nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                    mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pStartUpCost    [nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                    mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pShutDownCost   [nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperation_'  +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[p,sc,n,ar]+mTEPES.pOperReserveDw[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar):
        OutputToFile = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                        mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperReserve_'+CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputToFile = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearOMCost [ r] * OptModel.vTotalOutput   [p,sc,n, r]() for p,sc,n, r in mTEPES.ps*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.r ))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOandM_'      +CaseName+'.csv', sep=',')

    if len(mTEPES.es) and sum(mTEPES.pIndOperReserve[es] for es in mTEPES.es if mTEPES.pIndOperReserve[es] == 0) > 0:
        OutputToFile = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost[es] * OptModel.vESSTotalCharge[p,sc,n,es]()  for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeCostOperation_'      +CaseName+'.csv', sep=',')
        OutputToFile = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveUp  [p,sc,n,es]() +
                                        mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveDown[p,sc,n,es]()) for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeCostOperReserve_'    +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pCO2EmissionCost[nr] * OptModel.vTotalOutput[p,sc,n,nr]() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostEmission_'   +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pENSCost()           * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkCostENS_'           +CaseName+'.csv', sep=',')

    def Transformation1(df, _name):
        df = df.to_frame(name='MEUR')
        df['Cost'] = _name
        df = df.reset_index().pivot_table(index=['level_0','level_1', 'Cost'], values='MEUR', aggfunc=sum)
        return df

    for ar in mTEPES.ar:
        if len(mTEPES.ar) >= 1:
            OutputResults1 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Generation Operation Cost'         ) for p,sc in mTEPES.ps]))
            OutputResults2 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Generation Operating Reserve Cost' ) for p,sc in mTEPES.ps]))
            OutputResults3 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Generation O&M Cost'               ) for p,sc in mTEPES.ps]))
            OutputResults4 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Consumption Operation Cost'        ) for p,sc in mTEPES.ps]))
            OutputResults5 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Consumption Operating Reserve Cost') for p,sc in mTEPES.ps]))
            OutputResults6 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Emission Cost'                     ) for p,sc in mTEPES.ps]))
            OutputResults7 = pd.DataFrame(data={'MEUR': [0.0]}, index=pd.MultiIndex.from_tuples([(p,sc,'Reliability Cost'                  ) for p,sc in mTEPES.ps]))
            if len(mTEPES.nr):
                GenList = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if (ar,nr) in mTEPES.a2g]
                if len(GenList):
                    OutputResults1 = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                                      mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pConstantVarCost[nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                                      mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pStartUpCost    [nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                                      mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight  [n]() * mTEPES.pShutDownCost   [nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if (ar,nr) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                    OutputResults1 = Transformation1(OutputResults1, 'Generation Operation Cost')

                if sum(mTEPES.pOperReserveUp[p,sc,n,ar]+mTEPES.pOperReserveDw[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar) and len(GenList):
                    OutputResults2 = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                                      mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if (ar,nr) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                    OutputResults2 = Transformation1(OutputResults2, 'Generation Operating Reserve Cost')

            if len(mTEPES.r):
                GenList = [(p,sc,n,r) for p,sc,n,r in mTEPES.ps*mTEPES.n*mTEPES.r if (ar,r) in mTEPES.a2g]
                if len(GenList):
                    OutputResults3 = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearOMCost [ r] * OptModel.vTotalOutput   [p,sc,n, r]() for p,sc,n, r in mTEPES.ps*mTEPES.n*mTEPES.r  if (ar,r ) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                    OutputResults3 = Transformation1(OutputResults3, 'Generation O&M Cost')

            if len(mTEPES.es) and sum(mTEPES.pIndOperReserve[es] for es in mTEPES.es if mTEPES.pIndOperReserve[es] == 0) > 0:
                GenList = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es if (ar,es) in mTEPES.a2g]
                if len(GenList):
                    OutputResults4 = pd.Series(data=[ mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pLinearVarCost  [es] * OptModel.vESSTotalCharge[p,sc,n,es]()  for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es if (ar,es) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                    OutputResults5 = pd.Series(data=[(mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]()   * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveUp  [p,sc,n,es]() +
                                                      mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelWeight[n]()   * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveDown[p,sc,n,es]()) for p,sc,n,es in mTEPES.ps*mTEPES.n*mTEPES.es if (ar,es) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                    OutputResults4 = Transformation1(OutputResults4, 'Consumption Operation Cost')
                    OutputResults5 = Transformation1(OutputResults5, 'Consumption Operating Reserve Cost')

            GenList = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if (ar,nr) in mTEPES.a2g]
            if len(GenList):
                OutputResults6 = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pCO2EmissionCost[nr] * OptModel.vTotalOutput[p,sc,n,nr]() for p,sc,n,nr in mTEPES.ps*mTEPES.n*mTEPES.nr if (ar,nr) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(GenList))
                OutputResults6 = Transformation1(OutputResults6, 'Emission Cost')

            NodeList = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd if (nd,ar) in mTEPES.ndar]
            if len(NodeList):
                OutputResults7 = pd.Series(data=[mTEPES.pDiscountFactor[p] * mTEPES.pScenProb[p,sc] * mTEPES.pLoadLevelDuration[n]() * mTEPES.pENSCost()           * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in mTEPES.ps*mTEPES.n*mTEPES.nd if (nd,ar) in mTEPES.ndar], index=pd.MultiIndex.from_tuples(NodeList))
                OutputResults7 = Transformation1(OutputResults7, 'Reliability Cost')
        OutputResults = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7], axis=0)
        OutputResults.rename_axis(['Period', 'Scenario', 'Cost'], axis=0).to_csv(_path+'/oT_Result_CostSummary_'+ar+'_'+CaseName+'.csv', sep=',')

    OutputResults = []
    for p,sc,st in mTEPES.ps*mTEPES.st:
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput[p,sc,n,g]() for p,sc,n,nd,g in mTEPES.ps*mTEPES.n*mTEPES.n2g], index=pd.MultiIndex.from_tuples(mTEPES.ps*mTEPES.n*mTEPES.n2g))
        OutputResults.append(OutputToFile)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
    OutputResults = pd.concat(OutputResults)
    OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyGeneration_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        OutputResults = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile      = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vESSTotalCharge[p,sc,n,es]() for p,sc,n,nd,es in mTEPES.ps*mTEPES.n*mTEPES.n2g if es in mTEPES.es], index=pd.MultiIndex.from_tuples([(p,sc,n,nd,es) for p,sc,n,nd,es in mTEPES.ps*mTEPES.n*mTEPES.n2g if es in mTEPES.es]))
            OutputResults.append(OutputToFile)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        OutputResults = pd.concat(OutputResults)
        OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyCharge_'+CaseName+'.csv', sep=',')

    if len(mTEPES.gc):
        GenRev     = []
        ChargeRev  = []
        for p,sc,st in mTEPES.ps*mTEPES.st:
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToGenRev         = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc                                                 ], index=pd.MultiIndex.from_tuples([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc                                                 ]))
                GenRev.append       (OutputToGenRev    )
                if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc)     in mTEPES.t2g]):
                    OutputChargeRevESS = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[n]() * OptModel.vESSTotalCharge[p,sc,n,gc]() for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc)     in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc)     in mTEPES.t2g]))
                    ChargeRev.append(OutputChargeRevESS)
                if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc)     in mTEPES.t2g]):
                    OutputChargeRevRES = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]() * 0.0                                                                  for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc)     in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc)     in mTEPES.t2g]))
                    ChargeRev.append(OutputChargeRevRES)
                if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g]):
                    OutputChargeRevThr = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,nd]]/mTEPES.pPeriodProb[p,sc]() * 0.0                                                                  for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.ps*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g]))
                    ChargeRev.append(OutputChargeRevThr)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
        GenRev    = pd.concat(GenRev)
        ChargeRev = pd.concat(ChargeRev)
        GenRev    = GenRev.to_frame   ('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        ChargeRev = ChargeRev.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR', aggfunc=sum).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
    else:
        GenRev    = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        ChargeRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pReserveMargin[ar] for ar in mTEPES.ar):
        if len(mTEPES.gc):
            IndexResRev    = [(st,ar,gc) for st,ar,gc in mTEPES.st*mTEPES.ar*mTEPES.gc if mTEPES.pReserveMargin[ar] and (ar,gc) in mTEPES.a2g]
            OutputToResRev = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st))[p,ar]]*mTEPES.pRatedMaxPower[gc]*mTEPES.pAvailability[gc]/1e3 for st,ar,gc in IndexResRev], index=pd.MultiIndex.from_tuples(IndexResRev))
            OutputToResRev = OutputToResRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1'], columns='level_2', values='MEUR').rename_axis(['Stages', 'Areas'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            ResRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            for g in OutputToResRev.index:
                ResRev[g] = OutputToResRev[g]
        else:
            ResRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        ResRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar) > 0.0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and nr in mTEPES.nr]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveUp   [p,sc,n,nr]() for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and nr in mTEPES.nr]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults = pd.concat(OutputResults)
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUp_'+CaseName+'.csv', sep=',')
        if len([(p,sc,n,ar,es) for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and es in mTEPES.es]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,es]() for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,es) for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and es in mTEPES.es]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults = pd.concat(OutputResults)
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUpESS_'+CaseName+'.csv', sep=',')
        if len([(p,sc,n,ar,gc) for p,sc,n,ar,gc in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and gc in mTEPES.gc]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,ec]() for p,sc,n,ar,ec in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and ec in mTEPES.ec], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and ec in mTEPES.ec]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults    = pd.concat(OutputResults)
            OutputToUpRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            UpRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            for g in OutputToUpRev.index:
                UpRev[g] = OutputToUpRev[g]
        else:
            UpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        UpRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for p,sc,n,ar in mTEPES.ps*mTEPES.n*mTEPES.ar) > 0.0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and nr in mTEPES.nr]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and nr in mTEPES.nr]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults = pd.concat(OutputResults)
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDw_'+CaseName+'.csv', sep=',')
        if len([(p,sc,n,ar,es) for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and es in mTEPES.es]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,es]() for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,es) for p,sc,n,ar,es in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and es in mTEPES.es]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults = pd.concat(OutputResults)
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDwESS_'+CaseName+'.csv', sep=',')
        if len([(p,sc,n,ar,gc) for p,sc,n,ar,gc in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[p,sc,n,ar] and gc in mTEPES.gc]):
            OutputResults = []
            for p,sc,st in mTEPES.ps*mTEPES.st:
                mTEPES.del_component(mTEPES.st)
                mTEPES.del_component(mTEPES.n )
                mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
                mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn      in                          mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))[p,sc,n,ar]]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,ec]() for p,sc,n,ar,ec in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and ec in mTEPES.ec], index=pd.MultiIndex.from_tuples([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.ps*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[p,sc,n,ar] and ec in mTEPES.ec]))
                OutputResults.append(OutputToFile)
            mTEPES.del_component(mTEPES.st)
            mTEPES.del_component(mTEPES.n )
            mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
            mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration                                              )
            OutputResults    = pd.concat(OutputResults)
            OutputToDwRev = OutputResults.to_frame('MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
            DwRev         = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            for g in OutputToDwRev.index:
                DwRev[g] = OutputToDwRev[g]
        else:
            DwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
    else:
        DwRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if len(mTEPES.gc):
        InvCost = pd.Series(data=[sum(mTEPES.pGenInvestCost[gc]      * OptModel.vGenerationInvest[p,gc]() for p in mTEPES.p)    for gc       in mTEPES.gc], index= pd.Index(mTEPES.gc), dtype='float64')
        Balance = pd.Series(data=[GenRev[gc]+ChargeRev[gc]+UpRev[gc]+DwRev[gc]+ResRev[gc]-InvCost[gc] for gc in mTEPES.gc], index= pd.Index(mTEPES.gc), dtype='float64')
        CostRecoveryESS = pd.concat([GenRev,ChargeRev,UpRev,DwRev,ResRev,InvCost,Balance], axis=1, keys=['Generation revenue [MEUR]', 'Consumption revenue [MEUR]', 'Up reserve revenue [MEUR]', 'Down reserve revenue [MEUR]', 'Reserve capacity revenue [MEUR]', 'Investment Cost [MEUR]', 'Balance [MEUR]'])
        CostRecoveryESS.stack().to_frame(name='MEUR').reset_index().pivot_table(values='MEUR', index=['level_1'], columns=['level_0']).rename_axis([None], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_CostRecovery_'+CaseName+'.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing             economic results   ... ', round(WritingResultsTime), 's')


def NetworkMapResults(DirName, CaseName, OptModel, mTEPES):
    # %% plotting the network in a map
    _path = os.path.join(DirName, CaseName)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # Sub functions
    def oT_make_series(_var, _sets, _factor):
        return pd.Series(data=[_var[p,sc,n,ni,nf,cc]()*_factor for p,sc,n,ni,nf,cc in _sets], index=pd.MultiIndex.from_tuples(list(_sets)))

    def oT_selecting_data(p,sc,n):
        # Nodes data
        pio.renderers.default = 'chrome'

        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] =  0.0
        loc_df['Zone'  ] =  0.0
        loc_df['Demand'] =  0.0
        loc_df['Size'  ] = 15.0

        for nd,zn in mTEPES.ndzn:
            loc_df['Lon'   ][nd] = mTEPES.pNodeLon[nd]
            loc_df['Zone'  ][nd] = zn
            loc_df['Demand'][nd] = mTEPES.pDemand[p,sc,n,nd]*1e3

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlow, mTEPES.ps*mTEPES.n*mTEPES.la, 1e3)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        # tolerance to consider avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pLineNTCFrw[i] * 1e3 + pEpsilon for i in mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.la)),
                                     'NTCBck': pd.Series(data=[mTEPES.pLineNTCBck[i] * 1e3 + pEpsilon for i in mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.la))}, index=pd.MultiIndex.from_tuples(mTEPES.la))
        line_df['vFlow'      ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = 0.0
        line_df['voltage'    ] = 0.0
        line_df['width'      ] = 0.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = 0.0
        line_df['nf'         ] = 0.0
        line_df['cc'         ] = 0.0

        line_df = line_df.groupby(level=[0,1]).sum()
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

    p = list(mTEPES.p)[0]
    n = list(mTEPES.n)[0]

    if len(mTEPES.sc) > 1:
        for scc in mTEPES.sc:
            if mTEPES.pScenProb[p,scc] == 1.0:
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
    print('Plotting   network maps                ... ', round(PlottingNetMapsTime), 's')
