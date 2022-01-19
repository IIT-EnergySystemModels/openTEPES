"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 12, 2022
"""

import time
import os
import pandas as pd
import altair as alt
import plotly.io as pio
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from   collections   import defaultdict
from   pyomo.environ import Set
from   colour        import Color


# Definition of Pie plots
def PiePlots(df, Category, Value):
    OutputToPlot          = df.groupby(['level_3']).sum()
    OutputToPlot          = OutputToPlot.reset_index().rename(columns={'level_3': Category, '': Value})
    OutputToPlot[Value]   = round(OutputToPlot[Value], 1)
    OutputToPlot          = OutputToPlot[(OutputToPlot[[Value]] != 0).all(axis=1)]
    OutputToPlot['Label'] = [OutputToPlot[Category][i] + ': ' + str(OutputToPlot[Value][i]) for i in OutputToPlot.index]
    ComposedCategory      = Category + ':N'
    ComposedValue         = Value    + ':Q'

    base  = alt.Chart(OutputToPlot).encode(theta=alt.Theta(ComposedValue, stack=True), color=alt.Color(ComposedCategory, legend=alt.Legend(title=Category))).properties(width=800, height=800)
    pie   = base.mark_arc(outerRadius=240)
    text  = base.mark_text(radius=300, size=15).encode(text='Label:N')
    chart = pie + text

    return chart


# Definition of Area plots
def AreaPlots(scenario, period, df, Category, X, Y, OperationType):
    Results = df.loc[scenario,period,:,:]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # # Change the format of the LoadLevel
    Results[X] = Results[X].str[:19]
    Results[X] = (Results[X] + '+01:00')
    Results[X] = pd.to_datetime(Results[X])
    Results[X] = Results[X].dt.strftime('%m-%d %H:%M+01:00')
    # Composed Names
    C_C = Category + ':N'
    C_X = 'monthdate('   + X + '):T'
    if OperationType == 'average':
        C_Y = 'average(' + Y + '):Q'
    else:
        C_Y = 'sum('     + Y + '):Q'

    # Define and build the chart
    alt.data_transformers.disable_max_rows()
    interval = alt.selection_interval(encodings=['x'])

    base  = alt.Chart(Results).mark_area().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=C_C)
    chart = base.encode(x=alt.X(C_X, axis=alt.Axis(title=''), scale=alt.Scale(domain=interval.ref()))).properties(width=1200, height=450)
    view  = base.add_selection(interval).properties(width=1200, height=50)
    plot  = chart & view

    return plot


# Definition of Circle plots
def CirclePlots(scenario, period, df, Category, X, Y, OperationType):
    Results = df.loc[scenario,period,:,:]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # # Change the format of the LoadLevel
    Results[X] = Results[X].str[:19]
    Results[X] = (Results[X] + '+01:00')
    Results[X] = pd.to_datetime(Results[X])
    Results[X] = Results[X].dt.strftime('%m-%d %H:%M+01:00')
    # Composed Names
    C_C = Category + ':N'
    C_X = 'monthdate('   + X + '):T'
    if OperationType == 'average':
        C_Y = 'average(' + Y + '):Q'
    else:
        C_Y = 'sum('     + Y + '):Q'

    # Define and build the chart
    alt.data_transformers.disable_max_rows()
    interval = alt.selection_interval(encodings=['x'])

    base  = alt.Chart(Results).mark_line().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=C_C)
    chart = base.encode(x=alt.X(C_X, axis=alt.Axis(title=''), scale=alt.Scale(domain=interval.ref()))).properties(width=1200, height=450)
    view  = base.add_selection(interval).properties(width=1200, height=50)
    plot  = chart & view

    return plot


def InvestmentResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the investment decisions
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.gc):
        OutputToFile = pd.Series(data=[mTEPES.pRatedMaxPower[gc]*OptModel.vGenerationInvest[gc]() for gc in mTEPES.gc], index=pd.Index(mTEPES.gc))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0)
        OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Generating unit'}).to_csv(_path+'/oT_Result_GenerationInvestment_'+CaseName+'.csv', sep=',', index=False)

        OutputToFile = pd.Series(data=[sum(OutputToFile[gc] for gc in mTEPES.gc if (gt,gc) in mTEPES.t2g) for gt in mTEPES.gt], index=pd.Index(mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Technology'     }).to_csv(_path+'/oT_Result_TechnologyInvestment_'+CaseName+'.csv', sep=',', index=False)
        TechInv = OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Technology'     })
        TechInv = TechInv[(TechInv[['MW']] != 0).all(axis=1)]

        chart = alt.Chart(TechInv).mark_bar().encode(alt.X('Technology:O', axis=alt.Axis(title='Technology')), alt.Y('sum(MW):Q', axis=alt.Axis(title='MW'))).properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.gd):
        OutputToFile = pd.Series(data=[mTEPES.pRatedMaxPower[gd]*OptModel.vGenerationRetire[gd]() for gd in mTEPES.gd], index=pd.Index(mTEPES.gd))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0)
        OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Generating unit'}).to_csv(_path+'/oT_Result_GenerationRetirement_'+CaseName+'.csv', sep=',', index=False)

        OutputToFile = pd.Series(data=[sum(OutputToFile[gd] for gd in mTEPES.gd if (gt,gd) in mTEPES.t2g) for gt in mTEPES.gt], index=pd.Index(mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Technology'     }).to_csv(_path+'/oT_Result_TechnologyRetirement_'+CaseName+'.csv', sep=',', index=False)
        TechDecom = OutputToFile.to_frame(name='MW').reset_index().rename(columns={'index': 'Technology'     })
        TechDecom = TechDecom[(TechDecom[['MW']] != 0).all(axis=1)]

        chart = alt.Chart(TechDecom).mark_bar().encode(alt.X('Technology:O', axis=alt.Axis(title='Technology')), alt.Y('sum(MW):Q', axis=alt.Axis(title='MW'))).properties(width=600, height=400)
        chart.save(_path+'/oT_Plot_TechnologyRetirement_'+CaseName+'.html', embed_options={'renderer':'svg'})

    if len(mTEPES.lc):
        OutputToFile = pd.DataFrame.from_dict(OptModel.vNetworkInvest.extract_values(), orient='index', columns=[str(OptModel.vNetworkInvest)])
        OutputToFile.index = pd.MultiIndex.from_tuples(OutputToFile.index)
        OutputToFile.index.names = ['InitialNode','FinalNode','Circuit']
        OutputToFile = OutputToFile.reset_index()
        OutputToFile.rename(columns={'vNetworkInvest': 'Investment Decision'}).to_csv(_path + '/oT_Result_NetworkInvestment_'+CaseName+'.csv', index=False, sep=',')

        OutputResults_1 = pd.Series(data=[lt for ni,nf,cc,lt in mTEPES.lc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.lc))
        OutputResults_1 = OutputResults_1.to_frame(name='LineType')
        OutputResults_2 = pd.Series(data=[mTEPES.pLineNTCFrw[ni,nf,cc]*1e3 for ni,nf,cc in mTEPES.lc], index=pd.Index(mTEPES.lc))
        OutputResults_2 = OutputResults_2.to_frame(name='MW')
        OutputResults_3 = OutputToFile.set_index(['InitialNode', 'FinalNode', 'Circuit'])
        OutputResults   = pd.concat([OutputResults_1, OutputResults_2, OutputResults_3], axis=1)
        OutputResults.index.names = ['InitialNode','FinalNode','Circuit']
        OutputResults   = OutputResults.reset_index().groupby(['LineType', 'MW']).sum().rename(columns={'vNetworkInvest': 'Investment Decision'})
        OutputResults   = OutputResults.reset_index()
        OutputResults['MW'] = round(OutputResults['MW'], 2)

        chart = alt.Chart(OutputResults).mark_bar().encode(x='LineType:O', y='sum(Investment Decision):Q', color='LineType:N', column='MW:N')
        chart.save(_path+'/oT_Plot_NetworkInvestment_'+CaseName+'.html', embed_options={'renderer':'svg'})

        OutputToFile = pd.Series(data=[(OptModel.vNetworkInvest[ni,nf,cc]()*mTEPES.pLineNTCFrw[ni,nf,cc]*1e3)/mTEPES.pLineLength[ni,nf,cc]() for ni,nf,cc in mTEPES.lc], index= pd.MultiIndex.from_tuples(list(mTEPES.lc)))
        OutputToFile = OutputToFile.to_frame(name='MW-km')
        OutputToFile.to_csv(_path + '/oT_Result_NetworkInvestment_MWkm_'+CaseName+'.csv', sep=',')

        OutputResults_1 = pd.Series(data=[lt for ni,nf,cc,lt in mTEPES.lc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=pd.Index(mTEPES.lc))
        OutputResults_1 = OutputResults_1.to_frame(name='LineType')
        OutputResults_2 = pd.Series(data=[mTEPES.pLineNTCFrw[ni,nf,cc]*1e3 for ni,nf,cc in mTEPES.lc], index=pd.Index(mTEPES.lc))
        OutputResults_2 = OutputResults_2.to_frame(name='MW')
        OutputResults_3 = OutputToFile
        OutputResults   = pd.concat([OutputResults_1, OutputResults_2, OutputResults_3], axis=1)
        OutputResults.index.names = ['InitialNode','FinalNode','Circuit']
        OutputResults   = OutputResults.reset_index().groupby(['LineType', 'MW']).sum()
        OutputResults   = OutputResults.reset_index()
        OutputResults['MW'] = round(OutputResults['MW'], 2)

        chart = alt.Chart(OutputResults).mark_bar().encode(x='LineType:O', y='sum(MW-km):Q', color='LineType:N', column='MW:N')
        chart.save(_path+'/oT_Plot_NetworkInvestment_MW-km_'+CaseName+'.html', embed_options={'renderer':'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing           investment results   ... ', round(WritingResultsTime), 's')


def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[OptModel.vCommitment[sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCommitment_'+CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vStartUp   [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationStartUp_'   +CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vShutDown  [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationShutDown_'  +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        OutputToFile = pd.Series(data=[OptModel.vReserveUp     [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveUp_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveUp_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [sc,p,n,es]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeReserveUp_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveUpESS_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        OutputToFile = pd.Series(data=[OptModel.vReserveDown   [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveDown_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveDown_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[sc,p,n,es]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeReserveDown_'       +CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveDownESS_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*1e3                                             for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
    OutputToFile.to_frame(name='MW ').reset_index().pivot_table(index=['level_0','level_1','level_2'],        columns='level_3', values='MW ').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutput_'       +CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputToFile = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-OptModel.vTotalOutput[sc,p,n,r]())*1e3            for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r))
        for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r:
            if r in mTEPES.gc:
                OutputToFile[sc,p,n,r] = OutputToFile[sc,p,n,r] * OptModel.vGenerationInvest[r]()
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW'  ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_Curtailment_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-OptModel.vTotalOutput[sc,p,n,r]())*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r))
        for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r:
            if r in mTEPES.gc:
                OutputToFile[sc,p,n,r] = OutputToFile[sc,p,n,r] * OptModel.vGenerationInvest[r]()
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_CurtailmentEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,r] for r in mTEPES.r if (rt,r) in mTEPES.t2g) for sc,p,n,rt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.rt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.rt))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCurtailmentEnergy_'+CaseName+'.csv', sep=',')
        TechCurt = OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0).to_frame(name='GWh')
        TechCurt = TechCurt[(TechCurt[['GWh']] != 0).all(axis=1)]

        TechCurt = TechCurt.reset_index()
        TechCurt.rename({'index': 'Technologies'}, axis=1, inplace=True)

        chart = alt.Chart(TechCurt).mark_bar().encode(x='Technologies', y='GWh').properties(width=600, height=400)
        chart.save(_path + '/oT_Plot_TechnologyCurtailment_'+CaseName+'.html', embed_options={'renderer':'svg'})

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g ]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='GWh'  ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEnergy_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,nr]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]()*mTEPES.pCO2EmissionCost[nr]/mTEPES.pCO2Cost() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'],   columns='level_3', values='MtCO2').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEmission_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    #OutputToFile*= 1e3
    OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'],   columns='level_3', values='MtCO2').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEmission_'+CaseName+'.csv', sep=',')
    TechCO2 = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'],   columns='level_3', values='MtCO2').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0).to_frame(name='MtCO2')
    TechCO2 = TechCO2[(TechCO2[['MtCO2']] != 0).all(axis=1)]

    if len(TechCO2) > 0:
        TechCO2 = TechCO2.reset_index()
        TechCO2.rename({'index': 'Technologies'}, axis=1, inplace=True)

        chart = alt.Chart(TechCO2).mark_bar().encode(x='Technologies', y='MtCO2').properties(width=600, height=400)
        chart.save(_path + '/oT_Plot_Emissions_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutput_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
    OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,g] for g in mTEPES.g if (gt,g) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+CaseName+'.csv', sep=',')

    TechnologyEnergy = OutputToFile.to_frame(name='')
    TechnologyEnergy[''] = (TechnologyEnergy[''] / TechnologyEnergy[''].sum()) * 100
    TechnologyEnergy.reset_index(level=3, inplace=True)

    chart = PiePlots(TechnologyEnergy, 'Technology', '%')
    chart.save(_path + '/oT_Plot_TechnologyEnergy_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    for ar in mTEPES.ar:
        if len(mTEPES.ar) > 1:
            OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,g] for g in mTEPES.g if (ar,g) in mTEPES.a2g and (gt,g) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

            TechnologyEnergy = OutputToFile.to_frame(name='')
            TechnologyEnergy[''] = (TechnologyEnergy[''] / TechnologyEnergy[''].sum()) * 100
            TechnologyEnergy.reset_index(level=3, inplace=True)

            chart = PiePlots(TechnologyEnergy, 'Technology', '%')
            chart.save(_path+'/oT_Plot_TechnologyEnergy_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing generation operation results   ... ', round(WritingResultsTime), 's')


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the ESS operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.es):
        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [sc,p,n,es]()*1e3                 for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflows_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflows_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*1e3                 for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeOutput_'       +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutputESS_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeEnergy_'       +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergyESS_'+CaseName+'.csv', sep=',')

        OutputToFile *= -1
        if OutputToFile.sum() < 0:
            ESSTechnologyEnergy = OutputToFile.to_frame(name='')
            ESSTechnologyEnergy[''] = (ESSTechnologyEnergy[''] / ESSTechnologyEnergy[''].sum()) * 100
            ESSTechnologyEnergy.reset_index(level=3, inplace=True)

            chart = PiePlots(ESSTechnologyEnergy, 'Technology', '%')
            chart.save(_path+'/oT_Plot_TechnologyEnergyESS_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        for ar in mTEPES.ar:
            if len(mTEPES.ar) > 1:
                OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
                OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g and (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
                OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergyESS_'+ar+'_'+CaseName+'.csv', sep=',')

                OutputToFile *= -1
                if OutputToFile.sum() < 0:
                    ESSTechnologyEnergy = OutputToFile.to_frame(name='')
                    ESSTechnologyEnergy[''] = (ESSTechnologyEnergy[''] / ESSTechnologyEnergy[''].sum()) * 100
                    ESSTechnologyEnergy.reset_index(level=3, inplace=True)

                    chart = PiePlots(ESSTechnologyEnergy, 'Technology', '%')
                    chart.save(_path+'/oT_Plot_TechnologyEnergyESS_'+ar+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[sc,p,n,es]()                               for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_Inventory_'+CaseName+'.csv', sep=',')

        # OutputToFile = pd.Series(data=[OptModel.vESSInventory[sc,p,n,es]()/mTEPES.pMaxStorage[sc,p,n,es] for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es if mTEPES.pMaxStorage[sc,p,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)[mTEPES.pMaxStorage[sc,p,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0]))
        # OutputToFile = OutputToFile.fillna(0.0)
        # OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_InventoryUtilization_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSSpillage [sc,p,n,es]()                               for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_Spillage_' +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge[sc,p,n,es]()*1e3                        for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ot,es) in mTEPES.t2g) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot))
        OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCharge_'+CaseName+'.csv', sep=',')

        TechnologyCharge = OutputToFile.loc[:,:,:,:]

        for sc,p in mTEPES.sc*mTEPES.p:
            chart = AreaPlots(sc, p, TechnologyCharge, 'Technology', 'LoadLevel', 'MW', 'sum')
            chart.save(_path + '/oT_Plot_TechnologyCharge_'+sc+'_'+p+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing        ESS operation results   ... ', round(WritingResultsTime), 's')


def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    TechnologyOutput     = OutputToFile.loc[:,:,:,:]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput  = pd.Series([0.0]*len(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt), index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt:
        NetTechnologyOutput[sc,p,n,gt] = TechnologyOutput[sc,p,n,gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnology_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        ESSTechnologies = [(sc,p,n,ot) for sc,p,n,ot in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ot if sum(1 for es in mTEPES.es if (ot,es) in mTEPES.t2g)]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,es]() for es in mTEPES.es if (ot,es) in mTEPES.t2g)*1e3 for sc,p,n,ot in ESSTechnologies], index=pd.MultiIndex.from_tuples(ESSTechnologies))
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput = pd.Series([0.0] * len(ESSTechnologies), index=pd.MultiIndex.from_tuples(ESSTechnologies))
        for sc,p,n,gt in ESSTechnologies:
            NetESSTechnologyOutput[sc,p,n,gt] = MeanESSTechnologyOutput[gt] - ESSTechnologyOutput[sc,p,n,gt]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnologyESS_'+CaseName+'.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemand[sc,p,n,nd] for nd in mTEPES.nd)*1e3              for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemand[sc,p,n,nd] for nd in mTEPES.nd)*1e3 - MeanDemand for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n))
    OutputToFile.to_frame(name='Demand').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityDemand_'+CaseName+'.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[sc,p,n,nd]() for nd in mTEPES.nd)*1e3           for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[sc,p,n,nd]()*1e3 for nd in mTEPES.nd) - MeanENS for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n))
    OutputToFile.to_frame(name='PNS'   ).reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityPNS_'   +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing          flexibility results   ... ', round(WritingResultsTime), 's')


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the network operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[OptModel.vLineCommit  [sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkCommitment_'+CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOnState [sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOn_'   +CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOffState[sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOff_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlow[sc,p,n,ni,nf,cc]()*1e3 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkFlow_'       +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[abs(OptModel.vFlow[sc,p,n,ni,nf,cc]()/max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc])) for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkUtilization_'+CaseName+'.csv', sep=',')

    if mTEPES.pIndNetLosses():
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ll], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ll))
        OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
        OutputToFile.index.names = [None] * len(OutputToFile.index.names)
        OutputToFile.to_csv(_path+'/oT_Result_NetworkLosses_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTheta[sc,p,n,nd]()                   for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[sc,p,n,nd]()*1e3                 for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkPNS_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[sc,p,n,nd]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkENS_'  +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    network operation results   ... ', round(WritingResultsTime), 's')


def MarginalResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the up operating reserve marginal
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    #%% outputting the LSRMC
    AppendData = []
    for st in mTEPES.st:
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n] for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eBalance_'+st)))
        AppendData.append(OutputToFile)
    mTEPES.del_component(mTEPES.n)
    mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
    AppendData = pd.concat(AppendData)
    AppendData.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='LSRMC').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_LSRMC_'+CaseName+'.csv', sep=',')

    LSRMC = OutputToFile.loc[:,:]

    for sc,p in mTEPES.sc*mTEPES.p:
        chart = CirclePlots(sc, p, LSRMC, 'Node', 'LoadLevel', 'EUR/MWh', 'average')
        chart.save(_path + '/oT_Plot_LSRMC_'+sc+'_'+p+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    if sum(mTEPES.pReserveMargin[ar] for ar in mTEPES.ar):
        OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eAdequacyReserveMargin_'+st)[ar]] for st,ar in mTEPES.st*mTEPES.ar if mTEPES.pReserveMargin[ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(list(mTEPES.st*list(getattr(OptModel, 'eAdequacyReserveMargin_'+st)))))
        OutputToFile.to_frame(name='RM').reset_index().pivot_table(index=['level_0'], columns=['level_1'], values='RM').rename_axis(['Stage'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalReserveMargin_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar) > 0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveUp_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='UORM').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveUp_'+CaseName+'.csv', sep=',')

        MarginalUpOperatingReserve = OutputToFile.loc[:,:]

        for sc,p in mTEPES.sc*mTEPES.p:
            chart = CirclePlots(sc, p, MarginalUpOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
            chart.save(_path + '/oT_Plot_MarginalOperatingReserveUpward_'+sc+'_'+p+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the down operating reserve marginal
    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar) > 0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveDw_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='DORM').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveDown_'+CaseName+'.csv', sep=',')

        MarginalDwOperatingReserve = OutputToFile.loc[:,:]

        for sc,p in mTEPES.sc*mTEPES.p:
            chart = CirclePlots(sc, p, MarginalDwOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
            chart.save(_path + '/oT_Plot_MarginalOperatingReserveDownward_'+sc+'_'+p+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% outputting the water values
    if len(mTEPES.es):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eESSInventory_'+st)[sc,p,n,es]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es if mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eESSInventory_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='WaterValue').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_WaterValue_'+CaseName+'.csv', sep=',')

        WaterValue = OutputToFile.loc[:,:]

        for sc,p in mTEPES.sc*mTEPES.p:
            chart = CirclePlots(sc, p, WaterValue, 'Unit', 'LoadLevel', 'EUR/MWh', 'average')
            chart.save(_path + '/oT_Plot_WaterValue_'+sc+'_'+p+'_'+CaseName+'.html', embed_options={'renderer': 'svg'})

    #%% Reduced cost for NetworkInvestment
    ReducedCostActivation = mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)
    if len(mTEPES.lc) and not ReducedCostActivation:
        OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[ni,nf,cc]] for ni,nf,cc in mTEPES.lc], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'vNetworkInvest')))
        OutputToFile.index.names = ['InitialNode', 'FinalNode', 'Circuit']
        OutputToFile.to_frame(name='p.u.').to_csv(_path + '/oT_Result_NetworkInvestment_ReducedCost_'+CaseName+'.csv', sep=',')

    # %% Reduced cost for NetworkCommitment
    mTEPES.las = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all real lines with switching decision', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in mTEPES.pLineX and mTEPES.pIndBinLineSwitch[ni,nf,cc])
    if len(mTEPES.las) and not ReducedCostActivation:
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[sc,p,n,ni,nf,cc]] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.las], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.las))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
        AppendData = pd.pivot_table(AppendData.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
        AppendData.index.names = [None] * len(AppendData.index.names)
        AppendData.to_csv(_path+'/oT_Result_NetworkCommitment_ReducedCost_' +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing marginal information results   ... ', round(WritingResultsTime), 's')


def EconomicResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    SysCost     = OptModel.eTotalTCost.expr()
    GenInvCost  = sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[gc]() for gc     in mTEPES.gc)
    GenRetCost  = sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[gd]() for gd     in mTEPES.gd)
    NetInvCost  = sum(mTEPES.pNetFixedCost [lc] * OptModel.vNetworkInvest   [lc]() for lc     in mTEPES.lc)
    GenCost     = sum(mTEPES.pScenProb[sc]      * OptModel.vTotalGCost  [sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    ConCost     = sum(mTEPES.pScenProb[sc]      * OptModel.vTotalCCost  [sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    EmiCost     = sum(mTEPES.pScenProb[sc]      * OptModel.vTotalECost  [sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    RelCost     = sum(mTEPES.pScenProb[sc]      * OptModel.vTotalRCost  [sc,p,n]() for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    Costs       = {'':['System Cost', 'Generation Investment Cost', 'Generation Retirement Cost', 'Network Investment Cost', 'Generation Cost', 'Consumption Cost', 'Emissions Cost', 'Reliability Cost'], 'MEUR': [SysCost, GenInvCost, GenRetCost, NetInvCost, GenCost, ConCost, EmiCost, RelCost]}
    CostSummary = pd.DataFrame(Costs)
    CostSummary.to_csv(_path+'/oT_Result_CostSummary_'+CaseName+'.csv', sep=',', index=False)

    OutputToFile = pd.Series(data=[(mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pDuration[n] * mTEPES.pLinearVarCost  [nr] * OptModel.vTotalOutput   [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pDuration[n] * mTEPES.pConstantVarCost[nr] * OptModel.vCommitment    [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pStartUpCost    [nr] * OptModel.vStartUp       [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pShutDownCost   [nr] * OptModel.vShutDown      [sc,p,n,nr]()) for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperation_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[(mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp     [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown   [sc,p,n,nr]()) for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperReserve_'+CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pLinearOMCost [ r] * OptModel.vTotalOutput   [sc,p,n, r]() for sc,p,n, r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOandM_'   +CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        OutputToFile = pd.Series(data=[ mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pLinearVarCost  [es] * OptModel.vESSTotalCharge[sc,p,n,es]()  for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeCostOperation_'   +CaseName+'.csv', sep=',')
        OutputToFile = pd.Series(data=[(mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveUp  [sc,p,n,es]() +
                                        mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pOperReserveCost[es] * OptModel.vESSReserveDown[sc,p,n,es]()) for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostOperReserveESS_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pCO2EmissionCost[nr] * OptModel.vTotalOutput[sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCostEmission_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pENSCost()           * OptModel.vENS        [sc,p,n,nd]() for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ReliabilityCost_'       +CaseName+'.csv', sep=',')

    AppendData = []
    for st in mTEPES.st:
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vTotalOutput[sc,p,n,g]() for sc,p,n,nd,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g))
        AppendData.append(OutputToFile)
    mTEPES.del_component(mTEPES.n)
    mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
    AppendData = pd.concat(AppendData)
    AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyGeneration_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile      = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vESSTotalCharge[sc,p,n,es]() for sc,p,n,nd,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,es) for sc,p,n,nd,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if es in mTEPES.es]))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueEnergyCharge_'+CaseName+'.csv', sep=',')

    if len(mTEPES.gc):
        GenRev     = []
        ChargeRev  = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToGenRev       = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vTotalOutput   [sc,p,n,gc]() for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,gc) for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc]))
                OutputChargeRevESS   = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vESSTotalCharge[sc,p,n,gc]() for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,gc) for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) in mTEPES.t2g]))
                OutputChargeRevRES   = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * 0 for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc) in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,gc) for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (rt,gc) in mTEPES.t2g]))
                OutputChargeRevThr   = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * 0 for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,gc) for sc,p,n,nd,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (ot,gc) not in mTEPES.t2g]))
            GenRev.append   (OutputToGenRev    )
            ChargeRev.append(OutputChargeRevESS)
            ChargeRev.append(OutputChargeRevRES)
            ChargeRev.append(OutputChargeRevThr)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        GenRev    = pd.concat(GenRev)
        ChargeRev = pd.concat(ChargeRev)
        GenRev    = GenRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        ChargeRev = ChargeRev.to_frame('MEUR').reset_index().pivot_table(  index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
    else:
        GenRev    = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)
        ChargeRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)

    if sum(mTEPES.pReserveMargin[ar] for ar in mTEPES.ar):
        if len(mTEPES.gc):
            ResRev = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eAdequacyReserveMargin_'+st)[ar]]*mTEPES.pRatedMaxPower[gc]*mTEPES.pAvailability[gc]()/1e3 for st,ar,gc in mTEPES.st*mTEPES.ar*mTEPES.gc if mTEPES.pReserveMargin[ar] and (ar,gc) in mTEPES.a2g], index=pd.MultiIndex.from_tuples(mTEPES.st*mTEPES.ar*mTEPES.gc))
            ResRev = ResRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1'], columns='level_2', values='MEUR').rename_axis(['Stages','Areas'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        else:
            ResRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)
    else:
        ResRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar) > 0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        if len([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vReserveUp   [sc,p,n,nr]() for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUp_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveUp[sc,p,n,es]() for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveUpESS_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,gc) for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and gc in mTEPES.gc]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveUp[sc,p,n,gc]() for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and gc in mTEPES.gc], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,gc) for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and gc in mTEPES.gc]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            UpRev = AppendData.to_frame('MEUR').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        else:
            UpRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)
    else:
        UpRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)

    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar) > 0 and (sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0)) > 0:
        if len([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vReserveDown   [sc,p,n,nr]() for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and nr in mTEPES.nr]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDw_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveDown[sc,p,n,es]() for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and es in mTEPES.es]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RevenueOperatingReserveDwESS_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,gc) for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and gc in mTEPES.gc]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveDown[sc,p,n,gc]() for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and gc in mTEPES.gc], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,gc) for sc,p,n,ar,gc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and gc in mTEPES.gc]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            DwRev = AppendData.to_frame('MEUR').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).sum(axis=0)
        else:
            DwRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)
    else:
        DwRev     = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc)

    InvCost = pd.Series(data=[mTEPES.pGenInvestCost[gc] for gc in mTEPES.gc], index= pd.Index(mTEPES.gc))
    Balance = pd.Series(data=[GenRev[gc]+ChargeRev[gc]+UpRev[gc]+DwRev[gc]+ResRev[gc]-InvCost[gc] for gc in mTEPES.gc], index= pd.Index(mTEPES.gc))
    CostRecoveryESS = pd.concat([GenRev,ChargeRev,UpRev,DwRev,ResRev,InvCost,Balance], axis=1, keys=['Generation revenue [MEUR]','Consumption revenue [MEUR]','Up reserve revenue [MEUR]','Down reserve revenue [MEUR]','Reserve capacity revenue [MEUR]','Investment Cost [MEUR]','Balance [MEUR]'])
    CostRecoveryESS.stack().to_frame(name='MEUR').reset_index().pivot_table(values='MEUR', index=['level_1'], columns=['level_0']).rename_axis([None], axis=0).rename_axis([None], axis=1).to_csv(_path + '/oT_Result_CostRecovery_'+CaseName+'.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing             economic results   ... ', round(WritingResultsTime), 's')


def NetworkMapResults(DirName, CaseName, OptModel, mTEPES):
    # %% plotting the network in a map
    _path = os.path.join(DirName, CaseName)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # Sub functions
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and mTEPES.pScenProb   [scc])
    mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp                                            )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt, nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration        )

    def oT_make_series(_var, _sets, _factor):
        return pd.Series(data=[_var[sc, p, n, ni, nf, cc]()*_factor for sc, p, n, ni, nf, cc in _sets],
                         index=pd.MultiIndex.from_tuples(list(_sets)))


    def oT_selecting_data(sc, p, n):
        # Nodes data
        pio.renderers.default = 'chrome'

        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'] = 0.0
        loc_df['Zone'] = 0.0
        loc_df['Demand'] = 0.0
        loc_df['Size'] = 15.0

        for nd, zn in mTEPES.ndzn:
            loc_df['Lon'][nd]  = mTEPES.pNodeLon[nd]
            loc_df['Zone'][nd] = zn
            loc_df['Demand'][nd] = mTEPES.pDemand[sc, p, n, nd]*1e3

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlow, mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.la, 1e3)
        OutputToFile.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        line_df = pd.Series(data=[mTEPES.pLineNTCFrw[i]*1e3 for i in mTEPES.la], index=pd.MultiIndex.from_tuples(list(mTEPES.la))).to_frame(name='NTC')
        line_df['vFlow'] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'] = 0.0
        line_df['voltage'] = 0.0
        line_df['width'] = 0.0
        line_df['lon'] = 0.0
        line_df['lat'] = 0.0
        line_df['ni'] = 0.0
        line_df['nf'] = 0.0
        line_df['cc'] = 0.0

        line_df = line_df.groupby(level=[0, 1]).sum()
        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb' + str(x.rgb) for x in colors]

        for ni, nf, cc in mTEPES.la:
            line_df['vFlow'][ni, nf] += OutputToFile['MW'][sc, p, n, ni, nf, cc]
            line_df['utilization'][ni, nf] = abs(line_df['vFlow'][ni, nf]/line_df['NTC'][ni, nf])*100
            line_df['lon'][ni, nf] = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df['lat'][ni, nf] = (mTEPES.pNodeLat[ni] + mTEPES.pNodeLat[nf]) * 0.5
            line_df['ni'][ni, nf] = ni
            line_df['nf'][ni, nf] = nf
            line_df['cc'][ni, nf] += 1

            if 0.0 <= line_df['utilization'][ni, nf] <= 10.0:
                line_df['color'][ni, nf] = colors[0]
            if 10.0 < line_df['utilization'][ni, nf] <= 20.0:
                line_df['color'][ni, nf] = colors[1]
            if 20.0 < line_df['utilization'][ni, nf] <= 30.0:
                line_df['color'][ni, nf] = colors[2]
            if 30.0 < line_df['utilization'][ni, nf] <= 40.0:
                line_df['color'][ni, nf] = colors[3]
            if 40.0 < line_df['utilization'][ni, nf] <= 50.0:
                line_df['color'][ni, nf] = colors[4]
            if 50.0 < line_df['utilization'][ni, nf] <= 60.0:
                line_df['color'][ni, nf] = colors[5]
            if 60.0 < line_df['utilization'][ni, nf] <= 70.0:
                line_df['color'][ni, nf] = colors[6]
            if 70.0 < line_df['utilization'][ni, nf] <= 80.0:
                line_df['color'][ni, nf] = colors[7]
            if 80.0 < line_df['utilization'][ni, nf] <= 90.0:
                line_df['color'][ni, nf] = colors[8]
            if 90.0 < line_df['utilization'][ni, nf] <= 100.0:
                line_df['color'][ni, nf] = colors[9]
            if 100.0 < line_df['utilization'][ni, nf]:
                line_df['color'][ni, nf] = colors[10]

            line_df['voltage'][ni, nf] = mTEPES.pLineVoltage[ni, nf, cc]
            if 700 < line_df['voltage'][ni, nf] <= 900:
                line_df['width'][ni, nf] = 4
            elif 500 < line_df['voltage'][ni, nf] <= 700:
                line_df['width'][ni, nf] = 3
            elif 350 < line_df['voltage'][ni, nf] <= 500:
                line_df['width'][ni, nf] = 2.5
            elif 290 < line_df['voltage'][ni, nf] <= 350:
                line_df['width'][ni, nf] = 2
            elif 200 < line_df['voltage'][ni, nf] <= 290:
                line_df['width'][ni, nf] = 1.5
            elif 50 < line_df['voltage'][ni, nf] <= 200:
                line_df['width'][ni, nf] = 1
            else:
                line_df['width'][ni, nf] = 0.5

        # Rounding to decimals
        line_df = line_df.round(decimals=2)

        return loc_df, line_df

    sc = list(mTEPES.sc)[0]
    p = list(mTEPES.p)[0]
    n = list(mTEPES.n)[0]

    loc_df, line_df = oT_selecting_data(sc, p, n)

    # Making the network
    # Get node position dict
    x, y = loc_df['Lon'].values, loc_df['Lat'].values
    pos_dict = {}
    for index, iata in enumerate(loc_df['index']):
        pos_dict[iata] = (x[index], y[index])

    # Setting up the figure
    token = open(DIR + '/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode="area", color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni, nf, cc in mTEPES.la:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'titleside': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df['width'][ni, nf], color=line_df['color'][ni, nf]), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode="area", color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: ' + line_df['ni'] + ' --> ' + line_df['nf'] + '<br># Of circuits: ' + line_df['cc'].astype(str) + '<br>Total NTC: ' + line_df['NTC'].astype(str) + '<br>Power flow: ' + line_df['vFlow'].astype(str) + '<br>Utilization [%]: ' + line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': "Power Network: " + str(CaseName) + '<br>Scenario: ' + str(sc) + '; Period: ' + str(p) + '; LoadLevel: ' + str(n), 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style="dark", accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(_path + '/oT_Plot_MapNetwork_' + CaseName + '.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting network maps                  ... ', round(PlottingNetMapsTime), 's')
