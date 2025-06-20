"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - May 28, 2025
"""

import time
import datetime
import os
import ast
import math
import csv
import numpy             as     np
import pandas            as     pd
import pyomo.environ     as     pyo
import altair            as     alt
import plotly.io         as     pio
import plotly.graph_objs as     go
from   collections       import defaultdict
from   colour            import Color
from   pyomo.environ     import Suffix


# Definition of Pie plots
def PiePlots(period, scenario, df, Category, Value):
    df                    = df.reset_index()
    df                    = df.loc[(df['level_0'] == period) & (df['level_1'] == scenario)]
    df                    = df.set_index(['level_0','level_1','level_2','level_3'])
    OutputToPlot          = df.reset_index().groupby(['level_3']).sum(numeric_only=True)
    OutputToPlot['%'    ] = (OutputToPlot[0] / OutputToPlot[0].sum()) * 100.0
    OutputToPlot          = OutputToPlot.reset_index().rename(columns={'level_3': Category, 0: 'GWh'})
    OutputToPlot['GWh'  ] = round(OutputToPlot['GWh'], 1)
    OutputToPlot['%'    ] = round(OutputToPlot['%'  ], 1)
    OutputToPlot          = OutputToPlot[(OutputToPlot[['GWh']] != 0).all(axis=1)]
    OutputToPlot['Label'] = [OutputToPlot[Category][i] + ' (' + str(OutputToPlot['%'][i]) + ' %' + ', ' + str(OutputToPlot['GWh'][i]) + ' GWh' + ')' for i in OutputToPlot.index]
    ComposedCategory      = Category+':N'
    ComposedValue         = Value   +':Q'

    base  = alt.Chart(OutputToPlot).encode(theta=alt.Theta(ComposedValue, type="quantitative", stack=True), color=alt.Color(ComposedCategory, scale=alt.Scale(scheme='category20c'), type="nominal", legend=alt.Legend(title=Category))).properties(width=800, height=800)
    pie   = base.mark_arc(outerRadius=240)
    text  = base.mark_text(radius=340, size=15).encode(text='Label:N')
    chart = pie+text
    # chart = chart.resolve_scale(theta="independent")
    chart = alt.layer(pie, text, data=OutputToPlot).resolve_scale(theta="independent")

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


# write parameters, variables, and duals
def OutputResultsParVarCon(DirName, CaseName, OptModel, mTEPES):
    # print('Writing pars, vars, and duals results  ... ', end='')
    # DirName = os.path.dirname(DirName)
    _path   = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # Load the model from the pickle file
    # dump_folder = f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/'
    # with open(dump_folder+f'/oT_Case_{CaseName}.pkl','rb') as f:
    #     OptModel = pickle.load(f)
    # output parameters, variables, and constraints

    # dump_folder = f'{_path}/CaseDumpFolder_{CaseName}_'+str(datetime.datetime.now().strftime('%Y%m%d'))+f'/'
    dump_folder = os.path.join(DirName, CaseName, f'CaseDumpFolder_{CaseName}_'+str(datetime.datetime.now().strftime('%Y%m%d')))
    if not os.path.exists(dump_folder):
        os.makedirs(dump_folder)
    DateName = str(datetime.datetime.now().strftime('%Y%m%d'))

    # Extract and write parameters from the case
    with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Parameters.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Index', 'Value'])
        for par in OptModel.component_objects(pyo.Param):
            par_object = getattr(OptModel, str(par))
            if par_object.is_indexed():
                for index in par_object:
                    if (isinstance(index, tuple) and par_object.mutable == False) or par_object.mutable == False:
                        writer.writerow([str(par), index, par_object[index]])
                    else:
                        writer.writerow([str(par), index, par_object[index].value])
            else:
                writer.writerow        ([str(par), 'NA',  par_object.value])

    # Extract and write variables
    with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Variables.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Index', 'Value', 'Lower Bound', 'Upper Bound'])
        for var in OptModel.component_objects(pyo.Var, active=True):
            var_object = getattr(OptModel, str(var))
            for index in var_object:
                writer.writerow([str(var), index, var_object[index].value, str(var_object[index].lb), str(var_object[index].ub)])

    # Extract and write dual variables
    with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Constraints.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'Index', 'Value', 'Lower Bound', 'Upper Bound'])
        for con in OptModel.component_objects(pyo.Constraint, active=True):
            con_object = getattr(OptModel, str(con))
            if con.is_indexed():
                for index in con_object:
                    writer.writerow([str(con), index, mTEPES.pDuals[str(con_object.name)+str(index)], str(con_object[index].lb), str(con_object[index].ub)])
                    # writer.writerow([str(con), index, OptModel.dual[con_object[index]], str(con_object[index].lb), str(con_object[index].ub)])

    # NameList = ['Parameters', 'Variables', 'Constraints']
    #
    # df  = {}
    # lst = {}
    # for name in NameList:
    #     df[f'{name}'] = pd.read_csv(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_{name}.csv', index_col=[0,1])
    #     # df[f'{name}'].replace('inf',  '')
    #     # df[f'{name}'].replace('None', '')
    #     lst[f'{name}List'] = df[f'{name}'].index.get_level_values(0).unique().tolist()
    #
    # par = {}
    # for pn in NameList:
    #     for name in lst[f'{pn}List']:
    #         par[f'{name}'] = df[f'{pn}'].loc[f'{name}']
    #         if len(par[f'{name}'].index) > 1:
    #             contains_tuples = any('('   in i and ')' in i for i in par[f'{name}'].index)
    #             if contains_tuples:
    #                 # print(par[f'{name}'].index)
    #                 par[f'{name}'].index = pd.MultiIndex.from_tuples(par[f'{name}'].index.map(ast.literal_eval))

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing pars, vars, and duals results  ... ', round(WritingResultsTime), 's')


def InvestmentResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    #%% outputting the investment decisions
    _path = os.path.join(DirName, CaseName)
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
        OutputToFile = OutputToFile.fillna(0).to_frame(name='InvestmentDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='InvestmentDecision').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationInvestmentPerUnit_{CaseName}.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])
        OutputToFile = pd.Series(data=[OptModel.vGenerationInvest[p,eb]()*max(mTEPES.pRatedMaxPowerElec[eb],mTEPES.pRatedMaxCharge[eb]) for p,eb in mTEPES.peb], index=mTEPES.peb)
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW'                ).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW'                ).rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationInvestment_{CaseName}.csv', index=True, sep=',')
        OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput == 1:
                sPAREB           = [(p,ar,eb) for p,ar,eb in mTEPES.par*mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2a[ar]]
                GenInvestToArea  = pd.Series(data=[OutputToFile['MW'][p,eb] for p,ar,eb in sPAREB], index=pd.Index(sPAREB)).to_frame(name='MW')
                GenInvestToArea.index.names = ['Period', 'Area', 'Generating unit']
                chart = alt.Chart(GenInvestToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_GenerationInvestmentPerArea_{CaseName}.html', embed_options={'renderer':'svg'})
                TechInvestToArea = pd.Series(data=[sum(OutputToFile['MW'][p,eb] for eb in mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2a[ar] and eb in g2t[gt]) for p,ar,gt in mTEPES.par*mTEPES.gt], index=mTEPES.par*mTEPES.gt).to_frame(name='MW')
                TechInvestToArea.index.names = ['Period', 'Area', 'Technology'    ]
                chart = alt.Chart(TechInvestToArea.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestmentPerArea_{CaseName}.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment decision
            OutputResults1 = pd.Series(data=[gt for p,eb,gt in mTEPES.peb*mTEPES.gt if (p,eb) in mTEPES.peb and eb in g2t[gt]], index=mTEPES.peb)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyInvestment_{CaseName}.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestment_{CaseName}.html', embed_options={'renderer':'svg'})

            # Saving and plotting generation investment cost
            OutputResults0 = OutputResults
            OutputToFile   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[eb] * OptModel.vGenerationInvest[p,eb]() for p,eb in mTEPES.peb], index=mTEPES.peb)
            OutputToFile   = OutputToFile.fillna(0).to_frame(name='MEUR').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'}).set_index(['Period', 'Generating unit'])

            OutputResults1 = pd.Series(data=[gt for p,eb,gt in mTEPES.peb*mTEPES.gt if eb in g2t[gt]], index=mTEPES.peb)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MEUR'] = round(OutputResults['MEUR'], 2)

            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MEUR').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyInvestmentCost_{CaseName}.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MEUR):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyInvestmentCost_{CaseName}.html', embed_options={'renderer':'svg'})

            sPGT = [(p,gt) for p,gt in mTEPES.p*mTEPES.gt if sum(1 for eb in mTEPES.eb if (p,eb) in mTEPES.peb and eb in g2t[gt])]
            OutputResults = pd.Series(data=[OutputResults['MEUR'][p,gt]/(OutputResults0['MW'][p,gt]+pEpsilon) for p,gt in sPGT], index=pd.Index(sPGT)).to_frame(name='MEUR/MW')
            OutputResults.reset_index().pivot_table(index=['level_0'], columns='level_1', values='MEUR/MW').rename_axis(['Period'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyInvestmentCostPerMW_{CaseName}.csv', index=True, sep=',')

            if pIndPlotOutput == 1:
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
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()                                                           for p,gd in mTEPES.pgd], index=mTEPES.pgd)
            OutputToFile = OutputToFile.fillna(0).to_frame(name='RetirementDecision').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='RetirementDecision').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationRetirementPerUnit_{CaseName}.csv', index=True, sep=',')
            OutputToFile = pd.Series(data=[OptModel.vGenerationRetire[p,gd]()*max(mTEPES.pRatedMaxPowerElec[gd],mTEPES.pRatedMaxCharge[gd]) for p,gd in mTEPES.pgd], index=mTEPES.pgd)
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0).to_frame(name='MW'                ).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Generating unit'})
            OutputToFile.pivot_table(index=['Period'], columns=['Generating unit'], values='MW').rename_axis(['Period'], axis=0).to_csv(f'{_path}/oT_Result_GenerationRetirement_{CaseName}.csv', index=True, sep=',')
            OutputToFile = OutputToFile.set_index(['Period', 'Generating unit'])

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndPlotOutput == 1:
                sPARGD           = [(p,ar,gd) for p,ar,gd in mTEPES.par*mTEPES.gd if (p,gd) in mTEPES.pgd and gd in g2a[ar]]
                GenRetireToArea  = pd.Series(data=[OutputToFile['MW'][p,gd] for p,ar,gd in sPARGD], index=pd.Index(sPARGD)).to_frame(name='MW')
                GenRetireToArea.index.names = ['Period', 'Area', 'Generating unit']
                chart = alt.Chart(GenRetireToArea.reset_index()).mark_bar().encode(x='Generating unit:O', y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_GenerationRetirementPerArea_{CaseName}.html', embed_options={'renderer':'svg'})
                TechRetireToArea = pd.Series(data=[sum(OutputToFile['MW'][p,gd] for gd in mTEPES.gd if gd in g2a[ar] and gd in g2t[gt]) for p,ar,gt in mTEPES.par*mTEPES.gt], index=mTEPES.par*mTEPES.gt).to_frame(name='MW')
                TechRetireToArea.index.names = ['Period', 'Area', 'Technology'    ]
                chart = alt.Chart(TechRetireToArea.reset_index()).mark_bar().encode(x='Technology:O',     y='sum(MW):Q', color='Area:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyRetirementPerArea_{CaseName}.html', embed_options={'renderer':'svg'})

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            # Ordering data to plot the investment retirement
            OutputResults1 = pd.Series(data=[gt for p,gd,gt in mTEPES.pgd*mTEPES.gt if gd in g2t[gt]], index=mTEPES.pgd)
            OutputResults1 = OutputResults1.to_frame(name='Technology')
            OutputResults2 = OutputToFile
            OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
            OutputResults.index.names = ['Period', 'Generating unit']
            OutputResults  = OutputResults.reset_index().groupby(['Period', 'Technology']).sum(numeric_only=True)
            OutputResults['MW'] = round(OutputResults['MW'], 2)
            OutputResults.reset_index().pivot_table(index=['Period'], columns=['Technology'], values='MW').rename_axis([None], axis=0).to_csv(f'{_path}/oT_Result_TechnologyRetirement_{CaseName}.csv', sep=',', index=False)

            if pIndPlotOutput == 1:
                chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='Technology:O', y='sum(MW):Q', color='Technology:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyRetirement_{CaseName}.html', embed_options={'renderer':'svg'})

    if mTEPES.lc:

        # Saving investment decisions
        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
        OutputToFile = OutputToFile.fillna(0).to_frame(name='Investment Decision').rename_axis(['Period', 'InitialNode', 'FinalNode', 'Circuit'], axis=0)
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='Investment Decision').rename_axis([None, None, None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkInvestment_{CaseName}.csv', index=False, sep=',')
        # OutputToFile = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])

        # Ordering data to plot the investment decision
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=mTEPES.plc)
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.reset_index().set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['Investment Decision'] = round(OutputResults['Investment Decision'], 2)

        if pIndPlotOutput == 1:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(Investment Decision):Q', color='LineType:N', column='Period:N').properties(width=600, height=400)
            chart.save(f'{_path}/oT_Plot_NetworkInvestment_{CaseName}.html', embed_options={'renderer':'svg'})

        OutputToFile = pd.Series(data=[OptModel.vNetworkInvest[p,ni,nf,cc]()*mTEPES.pLineNTCFrw[ni,nf,cc]/mTEPES.pLineLength[ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0).to_frame(name='MW-km').reset_index().rename(columns={'level_0': 'Period', 'level_1': 'InitialNode', 'level_2': 'FinalNode', 'level_3': 'Circuit'})
        OutputToFile.reset_index().pivot_table(index=['Period'], columns=['InitialNode','FinalNode','Circuit'], values='MW-km').rename_axis([None,None,None], axis=1).rename_axis(['Period'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkInvestment_MWkm_{CaseName}.csv', index=False, sep=',')

        # Ordering data to plot the investment decision per kilometer
        OutputResults1 = pd.Series(data=[lt for p,ni,nf,cc,lt in mTEPES.plc*mTEPES.lt if (ni,nf,cc,lt) in mTEPES.pLineType], index=mTEPES.plc)
        OutputResults1 = OutputResults1.to_frame(name='LineType')
        OutputResults2 = OutputToFile.set_index(['Period', 'InitialNode', 'FinalNode', 'Circuit'])
        OutputResults  = pd.concat([OutputResults1, OutputResults2], axis=1)
        OutputResults.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults  = OutputResults.reset_index().groupby(['LineType', 'Period']).sum(numeric_only=True)
        OutputResults['MW-km'] = round(OutputResults['MW-km'], 2)

        if pIndPlotOutput == 1:
            chart = alt.Chart(OutputResults.reset_index()).mark_bar().encode(x='LineType:O', y='sum(MW-km):Q', color='LineType:N', column='Period:N')
            chart.save(f'{_path}/oT_Plot_NetworkInvestment_MW-km_{CaseName}.html', embed_options={'renderer':'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing            investment results  ... ', round(WritingResultsTime), 's')


def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to area (n2a)
    # n2a = defaultdict(list)
    # for ar,nr in mTEPES.ar*mTEPES.nr:
    #     if (ar,nr) in mTEPES.a2g:
    #         n2a[ar].append(nr)
    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    # technology to generators (o2e) (n2n) (r2r) (g2t)
    e2e = defaultdict(list)
    for et,eh in mTEPES.et*mTEPES.eh:
        if (et,eh) in mTEPES.t2g:
            e2e[et].append(eh)
    n2n = defaultdict(list)
    for nt,nr in mTEPES.nt*mTEPES.nr:
        if (nt,nr) in mTEPES.t2g:
            n2n[nt].append(nr)
    g2n = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2n[gt].append(g)
    r2r = defaultdict(list)
    for rt,re in mTEPES.rt*mTEPES.re:
        if (rt,re) in mTEPES.t2g:
            r2r[rt].append(re)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    if mTEPES.nr:
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[OptModel.vCommitment[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCommitment_{CaseName}.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vStartUp   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationStartUp_{CaseName}.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vShutDown  [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationShutDown_{CaseName}.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[:,:,:,:]):
        if mTEPES.nr:
            OutputToFile = pd.Series(data=[OptModel.vReserveUp     [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationReserveUp_{CaseName}.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUp_{CaseName}.csv', sep=',')

        if mTEPES.eh:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionReserveUp_{CaseName}.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUpESS_{CaseName}.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[:,:,:,:]):
        if mTEPES.nr:
            OutputToFile = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationReserveDown_{CaseName}.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDown_{CaseName}.csv', sep=',')

        if mTEPES.psnehc:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionReserveDown_{CaseName}.csv', sep=',')

            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDownESS_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]() for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_Generation_{CaseName}.csv', sep=',')

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    sPSNG        = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pEpsilon]
    OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,g].ub*OptModel.vGenerationInvest[p,g]() - OptModel.vTotalOutput[p,sc,n,g]()) if g in mTEPES.gc else
                                   (OptModel.vTotalOutput[p,sc,n,g].ub                                   - OptModel.vTotalOutput[p,sc,n,g]()) for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationSurplus_{CaseName}.csv', sep=',')

    OutputResults = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]                           and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, f'eRampUp_{p}_{sc}_{st}')[n,nr].uslack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampUp[nr]*(OptModel.vCommitment[p,sc,n,nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    if len(OutputToFile):
        OutputToFile.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampUpSurplus_{CaseName}.csv', sep=',')

    OutputResults = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first() and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].uslack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampDw[nr]*(mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vShutDown[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first() and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].uslack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampDw[nr]*(OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vShutDown[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    OutputResults = pd.concat(OutputResults)
    if len(OutputResults):
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampDwSurplus_{CaseName}.csv', sep=',')

    if mTEPES.re and mTEPES.rt:
        OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]() - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() if re in mTEPES.gc else
                                        (OptModel.vTotalOutput[p,sc,n,re].ub                                    - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]()                                     )*mTEPES.pLoadLevelDuration[p,sc,n]() if re in mTEPES.gc else
                                        (OptModel.vTotalOutput[p,sc,n,re].ub                                                                        )*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
            OutputToFile.to_csv(f'{_path}/oT_Result_GenerationCurtailmentEnergyRelative_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,rt in mTEPES.psrt], index=mTEPES.psrt)
            OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,rt in mTEPES.psrt], index=mTEPES.psrt)
            OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile  = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='%').rename_axis(['Period', 'Scenario', 'Technology'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyCurtailmentEnergyRelative_{CaseName}.csv', index=True, sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]() - OptModel.vTotalOutput[p,sc,n,re]()) if re in mTEPES.gc else
                                       (OptModel.vTotalOutput[p,sc,n,re].ub                                    - OptModel.vTotalOutput[p,sc,n,re]()) for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile *= 1e3
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCurtailment_{CaseName}.csv', sep=',')

        OutputToFile = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]() - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() if re in mTEPES.gc else
                                       (OptModel.vTotalOutput[p,sc,n,re].ub                                    - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCurtailmentEnergy_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,n,rt in mTEPES.psnrt], index=mTEPES.psnrt)
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(               index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyCurtailmentEnergy_{CaseName}.csv', sep=',')
            if pIndPlotOutput == 1:
                TechCurt = OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'GWh'})
                TechCurt = TechCurt[(TechCurt[['GWh']] != 0).all(axis=1)]
                chart = alt.Chart(TechCurt.reset_index()).mark_bar().encode(x='Technology', y='GWh', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyCurtailmentEnergy_{CaseName}.html', embed_options={'renderer':'svg'})

    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(      index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationEnergy_{CaseName}.csv', sep=',')

    if len(mTEPES.nr) + len(mTEPES.bo):
        OutputToFile     = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3 if g not in mTEPES.bo else
                                           OptModel.vTotalOutputHeat[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationEmission_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
                if pIndAreaOutput == 1:
                    for ar in mTEPES.ar:
                        if sum(1 for g in g2a[ar] if g in g2t[gt]):
                            sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt])]
                            if sPSNGT:
                                OutputResults = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                                OutputResults.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyEmission_{ar}_{CaseName}.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2n[nt] if (p,g) in mTEPES.pg) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
            OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyEmission_{CaseName}.csv', sep=',')
            if pIndPlotOutput == 1:
                TechEmission = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'MtCO2'})
                TechEmission = TechEmission[(TechEmission[['MtCO2']] != 0).all(axis=1)]
                if len(TechEmission):
                    chart = alt.Chart(TechEmission.reset_index()).mark_bar().encode(x='Technology', y='MtCO2', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                    chart.save(f'{_path}/oT_Plot_TechnologyEmission_{CaseName}.html', embed_options={'renderer': 'svg'})

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGeneration_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            TechnologyOutput = OutputToFile.loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyGeneration_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndAreaOutput == 1:
                for ar in mTEPES.ar:
                    if sum(1 for g in g2a[ar] if g in g2t[gt]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt])]
                        if sPSNGT:
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergy_{ar}_{CaseName}.csv', sep=',')

                            if pIndPlotOutput == 1:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{p}_{sc}_{ar}_{CaseName}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing  generation operation results  ... ', round(WritingResultsTime), 's')


def GenerationOperationHeatResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to area (g2a)
    g2a = defaultdict(list)
    for ar,ch in mTEPES.a2g:
        g2a[ar].append(ch)

    # technology to generators (g2t)
    g2t = defaultdict(list)
    for gt,chp in mTEPES.t2g:
        g2t[gt].append(chp)

    # for p,sc,n,ch in mTEPES.psnch:
    #     if ch not in mTEPES.bo:
    #         OptModel.vTotalOutputHeat[p,sc,n,ch] = OptModel.vTotalOutput[p,sc,n,ch] / mTEPES.pPower2HeatRatio[ch]
    #
    # for p,sc,n,hp in mTEPES.psnhp:
    #     OptModel.vTotalOutputHeat[p,sc,n,hp] = OptModel.vESSTotalCharge[p,sc,n,hp] / mTEPES.pProductionFunctionHeat[hp]

    OutputToFile = pd.Series(data=[OptModel.vTotalOutputHeat[p,sc,n,chp]() for p,sc,n,chp in mTEPES.psnchp], index=mTEPES.psnchp)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationHeat_{CaseName}.csv', sep=',')

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    sPSNG        = [(p,sc,n,ch) for p,sc,n,ch in mTEPES.psnch if OptModel.vTotalOutputHeat[p,sc,n,ch].ub and OptModel.vTotalOutputHeat[p,sc,n,ch].ub       - OptModel.vTotalOutputHeat[p,sc,n,ch]() > pEpsilon]
    OutputToFile = pd.Series(data=[(OptModel.vTotalOutputHeat[p,sc,n,ch].ub*OptModel.vGenerationInvest[p,ch]() - OptModel.vTotalOutputHeat[p,sc,n,ch]()) if ch in mTEPES.gc or ch in mTEPES.bc else
                                   (OptModel.vTotalOutputHeat[p,sc,n,ch].ub                                    - OptModel.vTotalOutputHeat[p,sc,n,ch]()) for p,sc,n,ch in sPSNG], index=pd.Index(sPSNG))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationSurplusHeat_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,chp in mTEPES.psnchp], index=mTEPES.psnchp)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(      index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationEnergyHeat_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for chp in g2t[gt] if (p,chp) in mTEPES.pchp)]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]() for chp in g2t[gt] if (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationHeat_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            TechnologyOutput = OutputToFile.loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationHeat_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2t[gt] if (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for chp in g2a[ar])) > 1:
            if pIndAreaOutput == 1:
                for ar in mTEPES.ar:
                    if sum(1 for chp in g2a[ar] if chp in g2t[gt]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for chp in g2a[ar] if (p,chp) in mTEPES.pchp and chp in g2t[gt])]
                        if sPSNGT:
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2a[ar] if (p,chp) in mTEPES.pchp and chp in g2t[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{ar}_{CaseName}.csv', sep=',')

                            if pIndPlotOutput == 1:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{p}_{sc}_{ar}_{CaseName}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing  heat       operation results  ... ', round(WritingResultsTime), 's')


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the ESS operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # generators to area (e2a)
    e2a = defaultdict(list)
    for ar,eh in mTEPES.ar*mTEPES.eh:
        if (ar,eh) in mTEPES.a2g:
            e2a[ar].append(eh)

    # technology to generators (e2e) (o2e)
    e2e = defaultdict(list)
    for et,eh in mTEPES.et*mTEPES.eh:
        if (et,eh) in mTEPES.t2g:
            e2e[et].append(eh)
    o2e = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            o2e[ot].append(es)

    OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows[p,sc,n,es]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOutflows_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOutflows_{CaseName}.csv', sep=',')

    # Check if there are any ESS with consumption capabilities
    # If there are none, just skip outputting consumption related files
    if mTEPES.psnehc:
        OutputToFile = pd.Series(data=[OptModel.vESSTotalCharge    [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
        OutputToFile *= -1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_Consumption_{CaseName}.csv', sep=',')

        # tolerance to consider that an ESS is not producing or consuming
        pEpsilon = 1e-6
        OutputToFile = pd.Series(data=[0.0 for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
        for p,sc,n,eh in mTEPES.psnehc:
            OutputToFile[p,sc,n,eh] = -1.0                                                                         if OptModel.vESSTotalCharge[p,sc,n,eh]() and OptModel.vTotalOutput   [p,sc,n,eh]() <= pEpsilon * mTEPES.pMaxPowerElec[p,sc,n,eh]                                          else OutputToFile[p,sc,n,eh]
            OutputToFile[p,sc,n,eh] =  1.0                                                                         if OptModel.vTotalOutput   [p,sc,n,eh]() and OptModel.vESSTotalCharge[p,sc,n,eh]() <= pEpsilon * mTEPES.pMaxCharge   [p,sc,n,eh]                                          else OutputToFile[p,sc,n,eh]
            if OptModel.vTotalOutput[p,sc,n,eh]() and OptModel.vESSTotalCharge[p,sc,n,eh]():
                OutputToFile[p,sc,n,eh] = OptModel.vTotalOutput[p,sc,n,eh]()/OptModel.vESSTotalCharge[p,sc,n,eh]() if OptModel.vTotalOutput   [p,sc,n,eh]() >  pEpsilon * mTEPES.pMaxPowerElec[p,sc,n,eh] or OptModel.vESSTotalCharge[p,sc,n,eh]() > pEpsilon * mTEPES.pMaxCharge[p,sc,n,eh] else OutputToFile[p,sc,n,eh]
        OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationConsumptionRatio_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyConsumption_{CaseName}.csv', sep=',')

        OutputToFile = - pd.Series(data=[OptModel.vESSTotalCharge[p, sc, n, eh]() * mTEPES.pLoadLevelDuration[p, sc, n]() for p, sc, n, eh in mTEPES.psnehc], index=mTEPES.psnehc)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionEnergy_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p, sc, n, eh] for eh in e2e[et] if (p, eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p, sc, n, et in mTEPES.psnet], index=mTEPES.psnet)
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyConsumptionEnergy_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            TechnologyCharge = OutputToFile.loc[:, :, :, :]
            for p, sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyCharge, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyConsumption_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        if pIndPlotOutput == 1:
            OutputToFile *= -1.0
            if OutputToFile.sum() < 0.0:
                for p, sc in mTEPES.ps:
                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                    chart.save(f'{_path}/oT_Plot_TechnologyConsumptionEnergy_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for eh in e2a[ar])) > 1:
            if pIndAreaOutput == 1:
                for ar in mTEPES.ar:
                    if sum(1 for eh in e2a[ar] if eh in e2e[et]):
                        sPSNET = [(p, sc, n, et) for p, sc, n, et in mTEPES.psnet if sum(1 for eh in e2a[ar] if (p, sc, n, eh) in mTEPES.psnehc and eh in e2e[et])]
                        if sPSNET:
                            OutputToFile = pd.Series(data=[sum(-OptModel.vESSTotalCharge[p, sc, n, eh]() * mTEPES.pLoadLevelDuration[p, sc, n]() for eh in e2a[ar] if (p,sc,n,eh) in mTEPES.psnehc and eh in e2e[et]) for p,sc,n,et in sPSNET], index=pd.Index(sPSNET))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyConsumptionEnergy_{ar}_{CaseName}.csv', sep=',')

                            if pIndPlotOutput == 1:
                                OutputToFile *= -1.0
                                for p, sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyConsumptionEnergy_{p}_{sc}_{ar}_{CaseName}.html', embed_options={'renderer': 'svg'})

    OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOutflowsEnergy_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOutflowsEnergy_{CaseName}.csv', sep=',')


    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    sPSNES = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.nesc if (p,es) in mTEPES.pes]
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()                                          for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationInventory_{CaseName}.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()/(mTEPES.pMaxStorage[p,sc,n,es]+pEpsilon) for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationInventoryUtilization_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vESSSpillage[p,sc,n,es]()                                               for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationSpillage_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        sPSNESOT = [(p,sc,n,es,ot) for p,sc,n,es,ot in sPSNES*mTEPES.ot if es in o2e[ot]]
        OutputToFile = pd.Series(data=[OutputToFile[p,sc,n,es] for p,sc,n,es,ot in sPSNESOT], index=pd.Index(sPSNESOT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologySpillage_{CaseName}.csv', sep=',')

    OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub*OptModel.vGenerationInvest[p,es]() - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[p,sc,n]() if es in mTEPES.ec else
                                    (OptModel.vTotalOutput[p,sc,n,es].ub                                    - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub*OptModel.vGenerationInvest[p,es]()                                     )*mTEPES.pLoadLevelDuration[p,sc,n]() if es in mTEPES.ec else
                                    (OptModel.vTotalOutput[p,sc,n,es].ub                                                                        )*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)
    OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generating unit'], axis=0).rename_axis([None], axis=1)

    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
        OutputToFile.to_csv(f'{_path}/oT_Result_GenerationSpillageRelative_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,es] for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,ot in mTEPES.psot], index=mTEPES.psot)
        OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,es] for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,ot in mTEPES.psot], index=mTEPES.psot)
        OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
        OutputToFile  = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='%').rename_axis(['Period', 'Scenario', 'Technology'], axis=0).to_csv(f'{_path}/oT_Result_TechnologySpillageRelative_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing         ESS operation results  ... ', round(WritingResultsTime), 's')


def ReservoirOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    # %% outputting the reservoir operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # technology to hydro units (o2h)
    o2h = defaultdict(list)
    for ht,h  in mTEPES.ht*mTEPES.h :
        if (ht,h ) in mTEPES.t2g:
            o2h[ht].append(h )

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    VolumeConstraints = [(p,sc,n,rs) for p,sc,n,rs in mTEPES.ps*mTEPES.nrsc if (p,rs) in mTEPES.prs]
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vReservoirVolume[p,sc,n,rs]()                                         for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ReservoirVolume_{CaseName}.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vReservoirVolume[p,sc,n,rs]()/(mTEPES.pMaxVolume[p,sc,n,rs]+pEpsilon) for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3', dropna=False, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ReservoirVolumeUtilization_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vReservoirSpillage[p,sc,n,rs]()                                           for p,sc,n,rs in VolumeConstraints], index=pd.Index(VolumeConstraints))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ReservoirSpillage_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,rs] for rs in mTEPES.rs if (n,rs) in mTEPES.nrsc) for p,sc,n,ht in mTEPES.psnht], index=mTEPES.psnht)
        OutputToFile.to_frame(name='hm3').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='hm3',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyReservoirSpillage_{CaseName}.csv', sep=',')

    #%% outputting the water volume values
    OutputResults = []
    sPSSTNES      = [(p,sc,st,n,rs) for p,sc,st,n,rs in mTEPES.ps*mTEPES.st*mTEPES.nrsc if (p,rs) in mTEPES.prs and (p,sc,st,n) in mTEPES.s2n and (p,sc,n) in mTEPES.psn]
    OutputToFile = pd.Series(data=[abs(mTEPES.pDuals["".join([f"eHydroInventory_{p}_{sc}_{st}('{n}', '{rs}')"])])*1e3 for p,sc,st,n,rs in sPSSTNES], index=pd.Index(sPSSTNES))
    if len(OutputToFile):
        OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalWaterValue_{CaseName}.csv', sep=',')

    if len(OutputToFile) and pIndPlotOutput == 1:
        WaterValue = OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, WaterValue, 'Generating unit', 'LoadLevel', 'EUR/dam3', 'average')
            chart.save(f'{_path}/oT_Plot_MarginalWaterValue_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing   reservoir operation results  ... ', round(WritingResultsTime), 's')


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

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psnar*mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (nd,ar) in mTEPES.ndar]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for el in e2t[gt] if (p,el) in mTEPES.pg)                                       and (nd,ar) in mTEPES.ndar]

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge[p,sc,n,el      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionH2[el] for el in mTEPES.el if el in e2n[nd] and el in e2t[gt]) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'       ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation', aggfunc='sum')
    OutputResults3 = pd.Series(data=[     OptModel.vH2NS          [p,sc,n,nd      ]()                                                                                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenNotServed')
    OutputResults4 = pd.Series(data=[-      mTEPES.pDemandH2      [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenDemand'   )
    OutputResults5 = pd.Series(data=[-sum(OptModel.vFlowH2        [p,sc,n,nd,nf,cc]()                                                                 for nf,cc in lout[nd])                                       for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowOut'  )
    OutputResults6 = pd.Series(data=[ sum(OptModel.vFlowH2        [p,sc,n,ni,nd,cc]()                                                                 for ni,cc in lin [nd])                                       for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6], axis=1)

    OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'tH2'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceHydrogen_{CaseName}.csv', index=False, sep=',')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerArea_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowH2[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=mTEPES.psnpa)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='tH2'), values='tH2', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkFlowH2PerNode_{CaseName}.csv', index=False, sep=',')

    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vH2NS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile.to_frame(name='tH2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkHNS_{CaseName}.csv', sep=',')

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
            loc_df.loc[nd,'Lon'   ] = mTEPES.pNodeLon[nd]
            loc_df.loc[nd,'Zone'  ] = zn
            loc_df.loc[nd,'Demand'] = mTEPES.pDemandH2[p,sc,n,nd]

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlowH2, mTEPES.psnpa, 1)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='tH2')

        # tolerance to consider avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pH2PipeNTCFrw[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa),
                                     'NTCBck': pd.Series(data=[mTEPES.pH2PipeNTCBck[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa)}, index=mTEPES.pa)
        line_df['vFlowH2'    ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = ''
        line_df['width'      ] = 3.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = ''
        line_df['nf'         ] = ''
        line_df['cc'         ] = 0

        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=False)
        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        for ni,nf,cc in mTEPES.pa:
            line_df.loc[(ni,nf),'vFlowH2'    ] += OutputToFile['tH2'][p,sc,n,ni,nf,cc]
            line_df.loc[(ni,nf),'utilization']  = max(line_df.loc[(ni,nf),'vFlowH2']/line_df.loc[(ni,nf),'NTCFrw'],-line_df.loc[(ni,nf),'vFlowH2']/line_df.loc[(ni,nf),'NTCBck'])*100.0
            line_df.loc[(ni,nf),'lon'        ]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df.loc[(ni,nf),'lat'        ]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
            line_df.loc[(ni,nf),'ni'         ]  = ni
            line_df.loc[(ni,nf),'nf'         ]  = nf
            line_df.loc[(ni,nf),'cc'         ] += 1

            if   0.0 <= line_df.loc[(ni,nf),'utilization'] <= 10.0:
                line_df.loc[(ni,nf),'color'] = colors[0]
            if  10.0 <  line_df.loc[(ni,nf),'utilization'] <= 20.0:
                line_df.loc[(ni,nf),'color'] = colors[1]
            if  20.0 <  line_df.loc[(ni,nf),'utilization'] <= 30.0:
                line_df.loc[(ni,nf),'color'] = colors[2]
            if  30.0 <  line_df.loc[(ni,nf),'utilization'] <= 40.0:
                line_df.loc[(ni,nf),'color'] = colors[3]
            if  40.0 <  line_df.loc[(ni,nf),'utilization'] <= 50.0:
                line_df.loc[(ni,nf),'color'] = colors[4]
            if  50.0 <  line_df.loc[(ni,nf),'utilization'] <= 60.0:
                line_df.loc[(ni,nf),'color'] = colors[5]
            if  60.0 <  line_df.loc[(ni,nf),'utilization'] <= 70.0:
                line_df.loc[(ni,nf),'color'] = colors[6]
            if  70.0 <  line_df.loc[(ni,nf),'utilization'] <= 80.0:
                line_df.loc[(ni,nf),'color'] = colors[7]
            if  80.0 <  line_df.loc[(ni,nf),'utilization'] <= 90.0:
                line_df.loc[(ni,nf),'color'] = colors[8]
            if  90.0 <  line_df.loc[(ni,nf),'utilization'] <= 100.0:
                line_df.loc[(ni,nf),'color'] = colors[9]
            if 100.0 <  line_df.loc[(ni,nf),'utilization']:
                line_df.loc[(ni,nf),'color'] = colors[10]

        # Rounding to decimals of the numerical columns
        line_df = line_df.round(decimals=2)

        return loc_df, line_df

    # tolerance to avoid division by 0
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
    token = open(DIR+f'/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni,nf,cc in mTEPES.pa:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowH2'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': 'Hydrogen Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetworkH2_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting hydrogen    network     maps  ... ', round(PlottingNetMapsTime), 's')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    hydrogen operation results  ... ', round(WritingResultsTime), 's')


def NetworkHeatOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the heat pipe network operation
    _path = os.path.join(DirName, CaseName)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # incoming and outgoing heat pipes (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.ha:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to CHPs (c2n)
    c2n = defaultdict(list)
    for nd,ch in mTEPES.nd*mTEPES.ch:
        if (nd,ch) in mTEPES.n2g:
            c2n[nd].append(ch)

    # CHPs to technology (c2t)
    c2t = defaultdict(list)
    for gt,ch in mTEPES.gt*mTEPES.ch:
        if (gt,ch) in mTEPES.t2g:
            c2t[gt].append(ch)

    # nodes to heat pumps (h2n)
    h2n = defaultdict(list)
    for nd,hp in mTEPES.nd*mTEPES.hp:
        if (nd,hp) in mTEPES.n2g:
            h2n[nd].append(hp)

    # heat pumps to technology (h2t)
    h2t = defaultdict(list)
    for gt,hp in mTEPES.gt*mTEPES.hp:
        if (gt,hp) in mTEPES.t2g:
            h2t[gt].append(hp)

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psnar*mTEPES.nd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (nd,ar) in mTEPES.ndar]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for ch in c2t[gt] if (p,ch) in mTEPES.pg) + sum(1 for hp in h2t[gt] if (p,hp) in mTEPES.pg)                and (nd,ar) in mTEPES.ndar]

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge [p,sc,n,hp      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionHeat[hp] for hp in mTEPES.hp if hp in h2n[nd] and hp in h2t[gt])                         for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationHeatPumps').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationHeatPumps', aggfunc='sum')
    OutputResults3 = pd.Series(data=[ sum(OptModel.vTotalOutput    [p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pPower2HeatRatio       [ch] for ch in mTEPES.ch if ch in c2n[nd] and ch in c2t[gt] and ch not in mTEPES.bo) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationCHPs'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationCHPs'     , aggfunc='sum')
    OutputResults4 = pd.Series(data=[ sum(OptModel.vTotalOutputHeat[p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ch in mTEPES.ch if ch in c2n[nd] and ch in c2t[gt] and ch     in mTEPES.bo) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationBoilers'  ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationBoilers'  , aggfunc='sum')
    OutputResults5 = pd.Series(data=[     OptModel.vHeatNS         [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                                                    for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatNotServed')
    OutputResults6 = pd.Series(data=[-      mTEPES.pDemandHeat     [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                                                    for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatDemand'   )
    OutputResults7 = pd.Series(data=[-sum(OptModel.vFlowHeat       [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for nf,cc in lout[nd])                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowOut'  )
    OutputResults8 = pd.Series(data=[ sum(OptModel.vFlowHeat       [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ni,cc in lin [nd])                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)

    OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceHeat_{CaseName}.csv', index=False, sep=',')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(f'{_path}/oT_Result_BalanceHeatPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHeatPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHeatPerArea_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
    OutputToFile *= 1e3
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkFlowHeatPerNode_{CaseName}.csv', index=False, sep=',')

    PSNHAARAR = [(p,sc,n,ni,nf,cc,ai,af) for p,sc,n,ni,nf,cc,ai,af in mTEPES.psnha*mTEPES.ar*mTEPES.ar if (ni,ai) in mTEPES.ndar and (nf,af) in mTEPES.ndar]
    OutputToFile = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ni,nf,cc,ai,af in PSNHAARAR], index=pd.Index(PSNHAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyHeatPerArea_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ni,nf,cc,ai,af in PSNHAARAR], index=pd.Index(PSNHAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyHeatTotalPerArea_{CaseName}.csv', index=False, sep=',')

    if mTEPES.ha:
        OutputResults = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()*(mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pPeriodProb[p,sc]())*(mTEPES.pHeatPipeLength[ni,nf,cc]()*1e-3) for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
        OutputResults.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = OutputResults.reset_index().groupby(['InitialNode', 'FinalNode', 'Circuit']).sum(numeric_only=True)[0]
        OutputResults.to_frame(name='GWh-Mkm').rename_axis(['InitialNode', 'FinalNode', 'Circuit'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyHeatTransport_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()/(mTEPES.pHeatPipeNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()/(mTEPES.pHeatPipeNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkHeatUtilization_{CaseName}.csv', index=False, sep=',')
    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vHeatNS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkHeatNS_{CaseName}.csv', sep=',')

    # plot heat network map
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
            loc_df.loc[nd,'Lon'   ] = mTEPES.pNodeLon[nd]
            loc_df.loc[nd,'Zone'  ] = zn
            loc_df.loc[nd,'Demand'] = mTEPES.pDemandHeat[p,sc,n,nd]

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlowHeat, mTEPES.psnha, 1)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        # tolerance to consider avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pHeatPipeNTCFrw[i] + pEpsilon for i in mTEPES.ha], index=mTEPES.ha),
                                     'NTCBck': pd.Series(data=[mTEPES.pHeatPipeNTCBck[i] + pEpsilon for i in mTEPES.ha], index=mTEPES.ha)}, index=mTEPES.ha)
        line_df['vFlowHeat'  ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = ''
        line_df['width'      ] = 3.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = ''
        line_df['nf'         ] = ''
        line_df['cc'         ] = 0

        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=False)
        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        for ni,nf,cc in mTEPES.ha:
            line_df.loc[(ni,nf),'vFlowHeat' ] += OutputToFile['MW'][p,sc,n,ni,nf,cc]
            line_df.loc[(ni,nf),'utilization'] = max(line_df.loc[(ni,nf),'vFlowHeat']/line_df.loc[(ni,nf),'NTCFrw'],-line_df.loc[(ni,nf),'vFlowHeat']/line_df.loc[(ni,nf),'NTCBck'])*100.0
            line_df.loc[(ni,nf),'lon']  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df.loc[(ni,nf),'lat']  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
            line_df.loc[(ni,nf),'ni']  = ni
            line_df.loc[(ni,nf),'nf']  = nf
            line_df.loc[(ni,nf),'cc'] += 1

            if   0.0 <= line_df.loc[(ni,nf),'utilization'] <= 10.0:
                line_df.loc[(ni,nf),'color'] = colors[0]
            if  10.0 <  line_df.loc[(ni,nf),'utilization'] <= 20.0:
                line_df.loc[(ni,nf),'color'] = colors[1]
            if  20.0 <  line_df.loc[(ni,nf),'utilization'] <= 30.0:
                line_df.loc[(ni,nf),'color'] = colors[2]
            if  30.0 <  line_df.loc[(ni,nf),'utilization'] <= 40.0:
                line_df.loc[(ni,nf),'color'] = colors[3]
            if  40.0 <  line_df.loc[(ni,nf),'utilization'] <= 50.0:
                line_df.loc[(ni,nf),'color'] = colors[4]
            if  50.0 <  line_df.loc[(ni,nf),'utilization'] <= 60.0:
                line_df.loc[(ni,nf),'color'] = colors[5]
            if  60.0 <  line_df.loc[(ni,nf),'utilization'] <= 70.0:
                line_df.loc[(ni,nf),'color'] = colors[6]
            if  70.0 <  line_df.loc[(ni,nf),'utilization'] <= 80.0:
                line_df.loc[(ni,nf),'color'] = colors[7]
            if  80.0 <  line_df.loc[(ni,nf),'utilization'] <= 90.0:
                line_df.loc[(ni,nf),'color'] = colors[8]
            if  90.0 <  line_df.loc[(ni,nf),'utilization'] <= 100.0:
                line_df.loc[(ni,nf),'color'] = colors[9]
            if 100.0 <  line_df.loc[(ni,nf),'utilization']:
                line_df.loc[(ni,nf),'color'] = colors[10]

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
    token = open(DIR+f'/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni,nf,cc in mTEPES.ha:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowHeat'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': 'Heat Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetworkHeat_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting heat        network     maps  ... ', round(PlottingNetMapsTime), 's')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  heat netwk operation results  ... ', round(WritingResultsTime), 's')


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

    # generators to technology (g2t)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    # Ratio Fossil Fuel Generation/Total Generation [%]
    TotalGeneration       = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng                 )
    FossilFuelGeneration  = sum(OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng if g in mTEPES.t)
    # Ratio Total Investments [%]
    TotalInvestmentCost   = sum(mTEPES.pDiscountedWeight[p] *                                   OptModel.vTotalFCost      [p   ]()       for p          in mTEPES.p  if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc))
    GenInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc]       * OptModel.vGenerationInvest[p,gc]()       for p,gc       in mTEPES.pgc)
    GenRetirementCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenRetireCost[gd]       * OptModel.vGenerationRetire[p,gd]()       for p,gd       in mTEPES.pgd)
    if mTEPES.pIndHydroTopology == 1:
        RsrInvestmentCost = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pRsrInvestCost[rc]       * OptModel.vReservoirInvest [p,rc]()       for p,rc       in mTEPES.prc)
    else:
        RsrInvestmentCost = 0.0
    NetInvestmentCost     = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pNetFixedCost [ni,nf,cc] * OptModel.vNetworkInvest   [p,ni,nf,cc]() for p,ni,nf,cc in mTEPES.plc)
    # Ratio Generation Investment cost/ Generation Installed Capacity [MEUR-MW]
    GenInvCostCapacity    = sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]()/mTEPES.pRatedMaxPowerElec[gc] for p,gc       in mTEPES.pgc if mTEPES.pRatedMaxPowerElec[gc])
    # Ratio Additional Transmission Capacity-Length [MW-km]
    NetCapacityLength     = sum(mTEPES.pLineNTCMax[ni,nf,cc]*OptModel.vNetworkInvest[p,ni,nf,cc]()/mTEPES.pLineLength[ni,nf,cc]()        for p,ni,nf,cc in mTEPES.plc)
    # Ratio Network Investment Cost/Variable RES Injection [EUR/MWh]
    if mTEPES.gc and sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re):
        NetInvCostVRESInsCap = NetInvestmentCost*1e6/sum(OptModel.vTotalOutput[p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,gc in mTEPES.psngc if gc in mTEPES.re)
    else:
        NetInvCostVRESInsCap = 0.0
    # Rate of return for VRE technologies
    # warning division and multiplication
    VRETechRevenue     = sum(mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput[p,sc,n,gc]() for p,sc,st,n,nd,gc in mTEPES.s2n*mTEPES.nd*mTEPES.gc if gc in g2n[nd] and gc in mTEPES.re and (p,gc) in mTEPES.pgc and (p,sc,n) in mTEPES.psn and sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
    VREInvCostCapacity = sum(mTEPES.pDiscountedWeight[p]*mTEPES.pGenInvestCost[gc]*OptModel.vGenerationInvest[p,gc]() for p,gc in mTEPES.pgc if gc in mTEPES.re)

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
    OutputResults.to_csv(f'{_path}/oT_Result_SummaryKPIs_{CaseName}.csv', sep=',', index=True)

    # LCOE per technology
    if mTEPES.gc:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p,     gc in mTEPES.pgc   if gc in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection  = pd.Series(data=[sum(OptModel.vTotalOutput     [p,sc,n,gc]()*mTEPES.pLoadLevelDuration[p,sc,n ]()                 for p,sc,n,gc in mTEPES.psngc if gc in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        LCOE = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh')
        LCOE.rename_axis(['Technology'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyLCOE_{CaseName}.csv', index=True, sep=',')

    # LCOE per technology
    if mTEPES.gb:
        GenTechInvestCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gb] * OptModel.vGenerationInvest[p,gb]() for p,     gb in mTEPES.pgb   if gb in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInjection  = pd.Series(data=[sum(OptModel.vTotalOutputHeat [p,sc,n,gb]()*mTEPES.pLoadLevelDuration[p,sc,n ]()                 for p,sc,n,gb in mTEPES.psngb if gb in g2t[gt]) for gt in mTEPES.gt], index=mTEPES.gt)
        GenTechInvestCost *= 1e3
        LCOH = GenTechInvestCost.div(GenTechInjection).to_frame(name='EUR/MWh')
        LCOH.rename_axis(['Technology'], axis=0).to_csv(f'{_path}/oT_Result_TechnologyLCOH_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing           KPI summary results  ... ', round(WritingResultsTime), 's')

    StartTime = time.time()
    t2g = pd.DataFrame(mTEPES.t2g).set_index(1)
    n2g = pd.DataFrame(mTEPES.n2g).set_index(1)
    z2g = pd.DataFrame(mTEPES.z2g).set_index(1)
    a2g = pd.DataFrame(mTEPES.a2g).set_index(1)
    r2g = pd.DataFrame(mTEPES.r2g).set_index(1)
    OutputToFile01 = pd.Series(data=[t2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Technology'             )
    OutputToFile02 = pd.Series(data=[n2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Node'                   )
    OutputToFile03 = pd.Series(data=[z2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Zone'                   )
    OutputToFile04 = pd.Series(data=[a2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Area'                   )
    OutputToFile05 = pd.Series(data=[r2g[0][g]                                                                                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Region'                 )
    OutputToFile06 = pd.Series(data=[mTEPES.pLoadLevelDuration[p,sc,n  ]()                                                                                                    for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='LoadLevelDuration [h]'  )
    OutputToFile07 = pd.Series(data=[OptModel.vCommitment     [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Commitment {0,1}'       )
    OutputToFile08 = pd.Series(data=[OptModel.vStartUp        [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='StartUp {0,1}'          )
    OutputToFile09 = pd.Series(data=[OptModel.vShutDown       [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ShutDown {0,1}'         )
    OutputToFile10 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g].ub                                                                                                   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='MaxPower [MW]'          )
    OutputToFile11 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g].lb                                                                                                   for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='MinPower [MW]'          )
    OutputToFile12 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='EnergyProduction [GWh]' )
    OutputToFile13 = pd.Series(data=[OptModel.vESSTotalCharge [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                     if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='EnergyConsumption [GWh]')
    OutputToFile14 = pd.Series(data=[OptModel.vEnergyOutflows [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                     if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Outflows [GWh]'         )
    OutputToFile15 = pd.Series(data=[OptModel.vESSInventory   [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Inventory [GWh]'        )
    OutputToFile16 = pd.Series(data=[OptModel.vESSSpillage    [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Spillage [GWh]'         )
    OutputToFile17 = pd.Series(data=[(OptModel.vTotalOutput   [p,sc,n,g].ub-OptModel.vTotalOutput[p,sc,n,g]())*mTEPES.pLoadLevelDuration[p,sc,n]() if g in mTEPES.re else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Curtailment [GWh]'      )
    OutputToFile18 = pd.Series(data=[OptModel.vReserveUp      [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveUpGen [MW]'      )
    OutputToFile19 = pd.Series(data=[OptModel.vReserveDown    [p,sc,n,g]()                                                                         if g in mTEPES.nr else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveDownGen [MW]'    )
    OutputToFile20 = pd.Series(data=[OptModel.vESSReserveUp   [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveUpCons [MW]'     )
    OutputToFile21 = pd.Series(data=[OptModel.vESSReserveDown [p,sc,n,g]()                                                                         if g in mTEPES.es else 0.0 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='ReserveDownCons [MW]'   )
    OutputToFile22 = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]             if g not in mTEPES.bo
                               else OptModel.vTotalOutputHeat [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]                                        for p,sc,n,g in mTEPES.psng], index=mTEPES.psng).to_frame(name='Emissions [MtCO2]'      )

    OutputToFile10 *= 1e3
    OutputToFile11 *= 1e3
    OutputToFile18 *= 1e3
    OutputToFile19 *= 1e3
    OutputToFile20 *= 1e3
    OutputToFile21 *= 1e3
    OutputToFile22 *= 1e-3

    OutputResults   = pd.concat([OutputToFile01, OutputToFile02, OutputToFile03, OutputToFile04, OutputToFile05, OutputToFile06, OutputToFile07, OutputToFile08, OutputToFile09, OutputToFile10,
                                       OutputToFile11, OutputToFile12, OutputToFile13, OutputToFile14, OutputToFile15, OutputToFile16, OutputToFile17, OutputToFile18, OutputToFile19, OutputToFile20,
                                      OutputToFile21, OutputToFile22], axis=1)
    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Generator'], axis=0).to_csv    (f'{_path}/oT_Result_SummaryGeneration_{CaseName}.csv',     sep=',')
    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Generator'], axis=0).to_parquet(f'{_path}/oT_Result_SummaryGeneration_{CaseName}.parquet', engine='pyarrow')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    generation summary results  ... ', round(WritingResultsTime), 's')

    ndzn = pd.DataFrame(mTEPES.ndzn).set_index(0)
    ndar = pd.DataFrame(mTEPES.ndar).set_index(0)
    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputResults1     = pd.Series(data=[ ndzn[1][nd]                                                                                             for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Zone'               )
    OutputResults2     = pd.Series(data=[ ndar[1][nd]                                                                                             for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='Area'               )
    OutputResults3     = pd.Series(data=[     OptModel.vENS       [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                         for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='ENS [GWh]'          )
    OutputResults4     = pd.Series(data=[-  mTEPES.pDemandElec    [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                         for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerDemand [GWh]'  )
    OutputResults5     = pd.Series(data=[-sum(OptModel.vFlowElec  [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in lout [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowOut [GWh]' )
    OutputResults6     = pd.Series(data=[ sum(OptModel.vFlowElec  [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in lin  [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='PowerFlowIn [GWh]'  )
    if mTEPES.ll:
        OutputResults7 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in loutl[nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesOut [GWh]')
        OutputResults8 = pd.Series(data=[-sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in linl [nd]) for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND)).to_frame(name='LineLossesIn [GWh]' )

        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)
    else:
        OutputResults  = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6                                ], axis=1)

    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Node'], axis=0).to_csv    (f'{_path}/oT_Result_SummaryNetwork_{CaseName}.csv',     sep=',')
    # OutputResults.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Node'], axis=0).to_parquet(f'{_path}/oT_Result_SummaryNetwork_{CaseName}.parquet', engine='pyarrow')

    WritingResultsTime = time.time() - StartTime
    print('Writing elect network summary results  ... ', round(WritingResultsTime), 's')


def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = os.path.join(DirName, CaseName)
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
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_FlexibilityTechnology_{CaseName}.csv', sep=',')

    if mTEPES.es:
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,es]() for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile *= 1e3
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput  = pd.Series([0.0] * len(mTEPES.psnot), index=mTEPES.psnot)
        for p,sc,n,ot in mTEPES.psnot:
            NetESSTechnologyOutput[p,sc,n,ot] = MeanESSTechnologyOutput[ot] - ESSTechnologyOutput[p,sc,n,ot]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_FlexibilityTechnologyESS_{CaseName}.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemandElec[p,sc,n,nd] for nd in d2a[ar])                  for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemandElec[p,sc,n,nd] for nd in d2a[ar]) - MeanDemand[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_FlexibilityDemand_{CaseName}.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in d2a[ar])               for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[p,sc,n,nd]() for nd in d2a[ar]) - MeanENS[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_FlexibilityPNS_{CaseName}.csv', sep=',')

    MeanFlow     = pd.Series(data=[sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc]() for nd,nf,cc,af in mTEPES.la*mTEPES.ar if nd in d2a[ar] and nf in d2a[af] and af != ar)                for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar).groupby(level=3).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc]() for nd,nf,cc,af in mTEPES.la*mTEPES.ar if nd in d2a[ar] and nf in d2a[af] and af != ar) - MeanFlow[ar] for p,sc,n,ar in mTEPES.psnar], index=mTEPES.psnar)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_FlexibilityNetwork_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing           flexibility results  ... ', round(WritingResultsTime), 's')


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the electric network operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if sum(mTEPES.pIndBinLineSwitch[:, :, :]):
        if mTEPES.lc:
            OutputToFile = pd.Series(data=[OptModel.vLineCommit  [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
            OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
            OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
            OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkCommitment_{CaseName}.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOnState [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkSwitchOn_{CaseName}.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOffState[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkSwitchOff_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowElec[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
    OutputToFile *= 1e3
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkFlowElecPerNode_{CaseName}.csv', index=False, sep=',')

    PSNLAARAR = [(p,sc,n,ni,nf,cc,ai,af) for p,sc,n,ni,nf,cc,ai,af in mTEPES.psnla*mTEPES.ar*mTEPES.ar if (ni,ai) in mTEPES.ndar and (nf,af) in mTEPES.ndar]
    OutputToFile = pd.Series(data=[OptModel.vFlowElec[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ni,nf,cc,ai,af in PSNLAARAR], index=pd.Index(PSNLAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyElecPerArea_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowElec[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ni,nf,cc,ai,af in PSNLAARAR], index=pd.Index(PSNLAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyElecTotalPerArea_{CaseName}.csv', index=False, sep=',')

    if mTEPES.la:
        OutputResults = pd.Series(data=[OptModel.vFlowElec[p,sc,n,ni,nf,cc]()*(mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pPeriodProb[p,sc]())*(mTEPES.pLineLength[ni,nf,cc]()*1e-3) for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputResults.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = OutputResults.reset_index().groupby(['InitialNode', 'FinalNode', 'Circuit']).sum(numeric_only=True)[0]
        OutputResults.to_frame(name='GWh-Mkm').rename_axis(['InitialNode', 'FinalNode', 'Circuit'], axis=0).reset_index().to_csv(f'{_path}/oT_Result_NetworkEnergyElecTransport_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlowElec[p,sc,n,ni,nf,cc]()/(mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]+pEpsilon),-OptModel.vFlowElec[p,sc,n,ni,nf,cc]()/(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkElecUtilization_{CaseName}.csv', index=False, sep=',')

    if mTEPES.pIndBinNetLosses() and mTEPES.psnll:
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[p,sc,n,ni,nf,cc]()*2*1e3              for p,sc,n,ni,nf,cc in mTEPES.psnll], index=mTEPES.psnll)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkLosses_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTheta[p,sc,n,nd]()                                   for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkAngle_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()                                     for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkPNS_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkENS_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing elect netwk operation results  ... ', round(WritingResultsTime), 's')


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

    # nodes to generators (g2n)
    g2n = defaultdict(list)
    for nd,g in mTEPES.n2g:
        g2n[nd].append(g)

    # nodes to CHPs (c2n), to heat pumps (h2n), to electrolyzers (e2n)
    c2n = defaultdict(list)
    for nd,ch in mTEPES.nd*mTEPES.ch:
        if (nd,ch) in mTEPES.n2g:
            c2n[nd].append(ch)
    h2n = defaultdict(list)
    for nd,hp in mTEPES.nd*mTEPES.hp:
        if (nd,hp) in mTEPES.n2g:
            h2n[nd].append(hp)
    e2n = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            e2n[nd].append(el)

    # generators to area (e2a) (n2a)
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    # tolerance to consider 0 a number
    pEpsilon = 1e-6

    #%% outputting the incremental variable cost of each generating unit (neither ESS nor boilers) with power surplus
    sPSNARG      = [(p,sc,n,ar,g) for p,sc,n,ar,g in mTEPES.psn*mTEPES.a2g if g not in mTEPES.eh and g not in mTEPES.bo and (p,g) in mTEPES.pg]
    OutputToFile = pd.Series(data=[(mTEPES.pLinearVarCost[p,sc,n,g]+mTEPES.pEmissionVarCost[p,sc,n,g]) if OptModel.vTotalOutput[p,sc,n,g].ub - OptModel.vTotalOutput[p,sc,n,g]() > pEpsilon else math.inf for p,sc,n,ar,g in sPSNARG], index=pd.Index(sPSNARG))
    OutputToFile *= 1e3

    OutputToFile = OutputToFile.to_frame(name='EUR/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='EUR/MWh')
    OutputToFile.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalIncrementalVariableCost_{CaseName}.csv', sep=',')
    IncrementalGens = pd.Series('N/A', index=mTEPES.psnar).to_frame(name='Generating unit')
    for p,sc,n,ar in mTEPES.psnar:
        if sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g):
            if len(OutputToFile.loc[(p,sc,n,ar)]) > 1:
                IncrementalGens.loc[p,sc,n,ar] = OutputToFile.loc[[(p,sc,n,ar)]].squeeze().idxmin()
            else:
                IncrementalGens.loc[p,sc,n,ar] = OutputToFile.loc[ (p,sc,n,ar) ].index[0]
    IncrementalGens.rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).to_csv(f'{_path}/oT_Result_MarginalIncrementalGenerator_{CaseName}.csv', index=True, sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pEmissionRate[g] for p,sc,n,ar,g in sPSNARG], index=pd.Index(sPSNARG))
    OutputToFile.to_frame(name='tCO2/MWh').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3'], columns='level_4', values='tCO2/MWh').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationIncrementalEmission_{CaseName}.csv', sep=',')

    #%% outputting the LSRMC of electricity
    sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (p,sc,n) in mTEPES.psn]
    OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
    OutputResults *= 1e3
    OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMC').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkSRMC_{CaseName}.csv', sep=',')

    OptModel.LSRMC = OutputResults.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMC').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]

    if pIndPlotOutput == 1:
        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, OptModel.LSRMC, 'Node', 'LoadLevel', 'EUR/MWh', 'average')
            chart.save(f'{_path}/oT_Plot_NetworkSRMC_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    if mTEPES.pIndHydrogen == 1:

        # incoming and outgoing lines (lin) (lout)
        lin  = defaultdict(list)
        lout = defaultdict(list)
        for ni,nf,cc in mTEPES.pa:
            lin [nf].append((ni,cc))
            lout[ni].append((nf,cc))

        #%% outputting the LSRMC of H2
        sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceH2_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
        OutputResults *= 1e3
        OutputResults.to_frame(name='LSRMCH2').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMCH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkSRMCH2_{CaseName}.csv', sep=',')

        OptModel.LSRMCH2 = OutputResults.to_frame(name='LSRMCH2').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMCH2').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]

        if pIndPlotOutput == 1:
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, OptModel.LSRMCH2, 'Node', 'LoadLevel', 'EUR/tH2', 'average')
                chart.save(f'{_path}/oT_Plot_NetworkSRMCH2_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    if mTEPES.pIndHeat == 1:
        # incoming and outgoing lines (lin) (lout)
        lin  = defaultdict(list)
        lout = defaultdict(list)
        for ni,nf,cc in mTEPES.ha:
            lin [nf].append((ni,cc))
            lout[ni].append((nf,cc))

        #%% outputting the LSRMC of heat
        sPSSTNND      = [(p,sc,st,n,nd) for p,sc,st,n,nd in mTEPES.s2n*mTEPES.nd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceHeat_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,st,n,nd in sPSSTNND], index=pd.Index(sPSSTNND))
        OutputResults *= 1e3
        OutputResults.to_frame(name='LSRMCHeat').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='LSRMCHeat').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkSRMCHeat_{CaseName}.csv', sep=',')

        OptModel.LSRMCHeat = OutputResults.to_frame(name='LSRMCHeat').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='LSRMCHeat').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]

        if pIndPlotOutput == 1:
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, OptModel.LSRMCHeat, 'Node', 'LoadLevel', 'EUR/Gcal', 'average')
                chart.save(f'{_path}/oT_Plot_NetworkSRMCHeat_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    if sum(mTEPES.pReserveMargin[:,:]):
        if mTEPES.gc:
            sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pReserveMargin[p,ar] and st == mTEPES.Last_st and sum(1 for g in mTEPES.g if g in g2a[ar]) and (p,sc,n) in mTEPES.psn and sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if g in g2a[ar] and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]]
            if sPSSTAR:
                OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eAdequacyReserveMarginElec_{p}_{sc}_{st}{ar}"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
                OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalReserveMargin_{CaseName}.csv', sep=',')

    if mTEPES.pIndHeat == 1:
        if sum(mTEPES.pReserveMarginHeat[:,:]):
            if mTEPES.gc:
                sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pReserveMarginHeat[p,ar] and st == mTEPES.Last_st and sum(1 for g in mTEPES.g if g in g2a[ar]) and (p,sc,n) in mTEPES.psn and sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if g in g2a[ar] and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]]
                if sPSSTAR:
                    OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eAdequacyReserveMarginHeat_{p}_{sc}_{st}{ar}"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
                    OutputResults.to_frame(name='RM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalReserveMarginHeat_{CaseName}.csv', sep=',')

    sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pEmission[p,ar] < math.inf and st == mTEPES.Last_st and (p,sc,n) in mTEPES.psn and sum(mTEPES.pEmissionVarCost[p,sc,na,g] for na,g in mTEPES.na*mTEPES.g if (ar,g) in mTEPES.a2g)]
    if sPSSTAR:
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eMaxSystemEmission_{p}_{sc}_{st}{ar}"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
        OutputResults.to_frame(name='EM').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='EM').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalEmission_{CaseName}.csv', sep=',')

    sPSSTAR           = [(p,sc,st,ar) for p,sc,st,ar in mTEPES.ps*mTEPES.st*mTEPES.ar if mTEPES.pRESEnergy[p,ar] and st == mTEPES.Last_st and (p,sc,n) in mTEPES.psn]
    if sPSSTAR:
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eMinSystemRESEnergy_{p}_{sc}_{st}{ar}"])] for p,sc,st,ar in sPSSTAR], index=pd.Index(sPSSTAR))
        OutputResults *= 1e-3*sum(mTEPES.pLoadLevelDuration[p,sc,na]() for na in mTEPES.na)
        OutputResults.to_frame(name='RES').reset_index().pivot_table(index=['level_0','level_1'], columns='level_3', values='RES').rename_axis(['Period', 'Scenario'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalRESEnergy_{CaseName}.csv', sep=',')

    #%% outputting the up operating reserve marginal
    if sum(mTEPES.pOperReserveUp[:,:,:,:]) and sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if nr in n2a[ar] and (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0)) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if es in e2a[ar] if (mTEPES.pIndOperReserveGen[es] == 0 or mTEPES.pIndOperReserveCon[es] == 0)):
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveUp[p,sc,n,ar] and sum(1 for nr in n2a[ar]) + sum(1 for es in e2a[ar]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"])] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults *= 1e3
        OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='UORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalOperatingReserveUp_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            MarginalUpOperatingReserve = OutputResults.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='UORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, MarginalUpOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
                chart.save(f'{_path}/oT_Plot_MarginalOperatingReserveUpward_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    #%% outputting the down operating reserve marginal
    if sum(mTEPES.pOperReserveDw[:,:,:,:]) and sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if nr in n2a[ar] if (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0)) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if es in e2a[ar] if (mTEPES.pIndOperReserveGen[es] == 0 or mTEPES.pIndOperReserveCon[nr] == 0)):
        sPSSTNAR      = [(p,sc,st,n,ar) for p,sc,st,n,ar in mTEPES.s2n*mTEPES.ar if mTEPES.pOperReserveDw[p,sc,n,ar] and sum(1 for nr in n2a[ar]) + sum(1 for es in e2a[ar]) and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"])] for p,sc,st,n,ar in sPSSTNAR], index=pd.Index(sPSSTNAR))
        OutputResults *= 1e3
        OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='DORM').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalOperatingReserveDown_{CaseName}.csv', sep=',')

        if pIndPlotOutput == 1:
            MarginalDwOperatingReserve = OutputResults.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='DORM').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, MarginalDwOperatingReserve, 'Area', 'LoadLevel', 'EUR/MW', 'sum')
                chart.save(f'{_path}/oT_Plot_MarginalOperatingReserveDownward_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    #%% outputting the water values
    if mTEPES.es:
        OutputResults = []
        sPSSTNES      = [(p,sc,st,n,es) for p,sc,st,n,es in mTEPES.ps*mTEPES.st*mTEPES.nesc if (p,es) in mTEPES.pes and (p,sc,st,n) in mTEPES.s2n and (p,sc,n) in mTEPES.psn and (mTEPES.pTotalMaxCharge[es] or mTEPES.pTotalEnergyInflows[es])]
        OutputToFile  = pd.Series(data=[abs(mTEPES.pDuals["".join([f"eESSInventory_{p}_{sc}_{st}('{n}', '{es}')"])])*1e3 for p,sc,st,n,es in sPSSTNES], index=pd.Index(sPSSTNES))
        if len(OutputToFile):
            OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalEnergyValue_{CaseName}.csv', sep=',')

        if len(OutputToFile) and pIndPlotOutput == 1:
            WaterValue = OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = LinePlots(p, sc, WaterValue, 'Generating unit', 'LoadLevel', 'EUR/MWh', 'average')
                chart.save(f'{_path}/oT_Plot_MarginalEnergyValue_{p}_{sc}_{CaseName}.html', embed_options={'renderer': 'svg'})

    # #%% Reduced cost for NetworkInvestment
    # ReducedCostActivation = mTEPES.pIndBinGenInvest()*len(mTEPES.gc) + mTEPES.pIndBinNetElecInvest()*len(mTEPES.lc) + mTEPES.pIndBinGenOperat()*len(mTEPES.nr) + mTEPES.pIndBinLineCommit()*len(mTEPES.la)
    # if len(mTEPES.lc) and not ReducedCostActivation and OptModel.vNetworkInvest.is_variable_type():
    #     OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[p,ni,nf,cc]] for p,ni,nf,cc in mTEPES.plc], index=mTEPES.plc)
    #     OutputToFile.index.names = ['Period', 'InitialNode', 'FinalNode', 'Circuit']
    #     OutputToFile.to_frame(name='MEUR').to_csv(f'{_path}/oT_Result_NetworkInvestment_ReducedCost_{CaseName}.csv', sep=',')
    #
    # #%% Reduced cost for NetworkCommitment
    # if len(mTEPES.ls) and not ReducedCostActivation and OptModel.vLineCommit.is_variable_type():
    #     OutputResults = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[p,sc,n,ni,nf,cc]] for p,sc,n,ni,nf,cc in mTEPES.psnls], index=mTEPES.psnlas)
    #     OutputResults.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    #     OutputResults = pd.pivot_table(OutputResults.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0)
    #     OutputResults.index.names = [None] * len(OutputResults.index.names)
    #     OutputResults.to_csv(f'{_path}/oT_Result_NetworkCommitment_ReducedCost_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  marginal information results  ... ', round(WritingResultsTime), 's')


def ReliabilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the reliability indexes
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    r2r = defaultdict(list)
    for rt,re in mTEPES.rt*mTEPES.re:
        if (rt,re) in mTEPES.t2g:
            r2r[rt].append(re)

    pDemandElec    = pd.Series(data=[mTEPES.pDemandElec[p,sc,n,nd] for p,sc,n,nd in mTEPES.psnnd ], index=mTEPES.psnnd).sort_index()
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
    OutputToFile2     = pd.Series(data=[      mTEPES.pDemandElec [p,sc,n,nd]                                                                                            for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile  = OutputToFile2 - OutputToFile1
    OutputToFile  *= 1e3
    OutputToFile  = OutputToFile.to_frame(name='MW'  )
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetDemandNetwork_{CaseName}.csv', sep=',')
    OutputToFile.reset_index().pivot_table(index=['level_0','level_1','level_2'],                    values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetDemand_{CaseName}.csv', sep=',')

    # Determination of the index: Reserve Margin
    OutputToFile1 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    OutputToFile2 = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile1[p,sc] = pMaxPowerElec.loc[(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum')[0].max()
        OutputToFile2[p,sc] = pDemandElec.loc  [(p,sc)].reset_index().pivot_table(index=['level_0'], values=0, aggfunc='sum')[0].max()
    ReserveMargin1 =  OutputToFile1 - OutputToFile2
    ReserveMargin2 = (OutputToFile1 - OutputToFile2)/OutputToFile2
    ReserveMargin1.to_frame(name='MW'  ).rename_axis(['Period', 'Scenario'], axis=0).to_csv(f'{_path}/oT_Result_ReserveMarginPower_{CaseName}.csv', sep=',')
    ReserveMargin2.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).to_csv(f'{_path}/oT_Result_ReserveMarginPerUnit_{CaseName}.csv', sep=',')

    # Determination of the index: Largest Unit
    OutputToFile = pd.Series(data=[0.0 for p,sc in mTEPES.ps], index=mTEPES.ps)
    for p,sc in mTEPES.ps:
        OutputToFile[p,sc] = pMaxPowerElec.loc[(p,sc)].reset_index().pivot_table(index=['level_1'], values=0, aggfunc='sum')[0].max()

    LargestUnit  = ReserveMargin1/OutputToFile
    LargestUnit.to_frame(name='p.u.').rename_axis(['Period', 'Scenario'], axis=0).to_csv(f'{_path}/oT_Result_LargestUnitPerUnit_{CaseName}.csv', index=True, sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing           reliability indexes  ... ', round(WritingResultsTime), 's')

def CostSummaryResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # SysCost      = pd.Series(data=[                                                                  OptModel.vTotalSCost()                                                                                         ], index=['']    ).to_frame(name='Total          System Cost').stack()
    GenInvCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenInvestCost[gc  ]   * OptModel.vGenerationInvest[p,gc  ]()  for gc   in mTEPES.gc          if (p,gc) in mTEPES.pgc) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Generation').stack()
    GenRetCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pGenRetireCost[gd  ]   * OptModel.vGenerationRetire[p,gd  ]()  for gd   in mTEPES.gd          if (p,gd) in mTEPES.pgd) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Retirement Cost Generation').stack()
    if mTEPES.pIndHydroTopology == 1:
        RsrInvCost = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pRsrInvestCost[rc  ]   * OptModel.vReservoirInvest [p,rc  ]()  for rc   in mTEPES.rn          if (p,rc) in mTEPES.prc) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reservoir' ).stack()
    else:
        RsrInvCost = pd.Series(data=[0.0                                                                                                                                                             for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Reservoir' ).stack()
    NetInvCost     = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pNetFixedCost [lc  ]   * OptModel.vNetworkInvest   [p,lc  ]()  for lc   in mTEPES.lc          if (p,lc) in mTEPES.plc) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Investment Cost Network'   ).stack()
    GenCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * OptModel.vTotalGCost      [p,sc,n]()  for sc,n in mTEPES.sc*mTEPES.n if (p,sc) in mTEPES.ps ) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Operation Cost Generation' ).stack()
    ConCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * OptModel.vTotalCCost      [p,sc,n]()  for sc,n in mTEPES.sc*mTEPES.n if (p,sc) in mTEPES.ps ) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Operation Cost Consumption').stack()
    EmiCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * OptModel.vTotalECost      [p,sc,n]()  for sc,n in mTEPES.sc*mTEPES.n if (p,sc) in mTEPES.ps ) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Emission Cost'             ).stack()
    RelCost        = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * OptModel.vTotalRCost      [p,sc,n]()  for sc,n in mTEPES.sc*mTEPES.n if (p,sc) in mTEPES.ps ) for p in mTEPES.p], index=mTEPES.p).to_frame(name='Reliability Cost'          ).stack()
    CostSummary    = pd.concat([GenInvCost, GenRetCost, RsrInvCost, NetInvCost, GenCost, ConCost, EmiCost, RelCost]).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Cost', 0: 'MEUR'})
    CostSummary['MEUR/year'] = CostSummary['MEUR']
    for p in mTEPES.p:
        CostSummary.loc[CostSummary['Period'] == p, 'MEUR/year'] = CostSummary.loc[CostSummary['Period'] == p, 'MEUR'] / mTEPES.pDiscountedWeight[p]
    CostSummary.to_csv(f'{_path}/oT_Result_CostSummary_{CaseName}.csv', sep=',', index=False)

    # DemPayment   = pd.Series(data=[mTEPES.pDiscountedWeight[p] * sum(mTEPES.pScenProb     [p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pDemandElec[p,sc,n,nd] * OptModel.LSRMC            [p,sc,n,nd] for sc,n,nd in mTEPES.sc*mTEPES.n*mTEPES.nd if (p,sc) in mTEPES.ps )/1e3 for p in mTEPES.p], index=mTEPES.p).to_frame(name='Demand Payment'            ).stack()

    WritingResultsTime = time.time() - StartTime
    print('Writing          cost summary results  ... ', round(WritingResultsTime), 's')


def EconomicResults(DirName, CaseName, OptModel, mTEPES, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # %% Power balance per period, scenario, and load level
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

    # generators to nodes (g2n) (e2n)
    g2n = defaultdict(list)
    for nd,g in mTEPES.n2g:
        g2n[nd].append(g)
    e2n = defaultdict(list)
    for nd,eh in mTEPES.nd*mTEPES.eh:
        if (nd,eh) in mTEPES.n2g:
            e2n[nd].append(eh)
    r2n = defaultdict(list)
    for nd,re in mTEPES.nd*mTEPES.re:
        if (nd,re) in mTEPES.n2g:
            r2n[nd].append(re)

    # generators to area (n2a)(g2a)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    # generators to technology (o2e) (g2t)
    e2e = defaultdict(list)
    for et,eh in mTEPES.et*mTEPES.eh:
        if (et,eh) in mTEPES.t2g:
            e2e[et].append(eh)
    o2e = defaultdict(list)
    for ot,es in mTEPES.ot*mTEPES.es:
        if (ot,es) in mTEPES.t2g:
            o2e[ot].append(es)
    r2r = defaultdict(list)
    for rt,re in mTEPES.rt*mTEPES.re:
        if (rt,re) in mTEPES.t2g:
            r2r[rt].append(re)
    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
        if pIndAreaOutput == 1:
            for ar in mTEPES.ar:
                if sum(1 for g in g2a[ar] if g in g2t[gt]):
                    sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt])]
                    if sPSNGT:
                        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2a[ar] if (p,g) in mTEPES.pg and g in g2t[gt]) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergy_{ar}_{CaseName}.csv', sep=',')

                        if pIndPlotOutput == 1:
                            for p,sc in mTEPES.ps:
                                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{p}_{sc}_{ar}_{CaseName}.html', embed_options={'renderer': 'svg'})

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psnar*mTEPES.nd if sum(1 for g  in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) and (nd,ar) in mTEPES.ndar]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for g  in g2t[gt] if (p,g ) in mTEPES.pg )                                      and (nd,ar) in mTEPES.ndar]
    sPSNARNDRT = [(p,sc,n,ar,nd,rt) for p,sc,n,ar,nd,rt in sPSNARND*mTEPES.rt     if sum(1 for re in r2r[rt] if (p,re) in mTEPES.pre)                                      and (nd,ar) in mTEPES.ndar]
    sPSNARNDET = [(p,sc,n,ar,nd,et) for p,sc,n,ar,nd,et in sPSNARND*mTEPES.et     if sum(1 for eh in e2e[et] if (p,eh) in mTEPES.peh)                                      and (nd,ar) in mTEPES.ndar]

    OutputResults01     = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,nr      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nr in g2n[nd] if (p,nr) in mTEPES.pnr and nr in g2t[gt] and nr not in mTEPES.eh) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.re:
        OutputResults02 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,re      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for re in r2n[nd] if (p,re) in mTEPES.pre and re in r2r[rt]                        ) for p,sc,n,ar,nd,rt in sPSNARNDRT], index=pd.Index(sPSNARNDRT)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
    if mTEPES.eh:
        OutputResults03 = pd.Series(data=[ sum(OptModel.vTotalOutput   [p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for eh in e2n[nd] if (p,eh) in mTEPES.peh and eh in e2e[et]                        ) for p,sc,n,ar,nd,et in sPSNARNDET], index=pd.Index(sPSNARNDET)).to_frame(name='Generation'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation' , aggfunc='sum')
        OutputResults04 = pd.Series(data=[-sum(OptModel.vESSTotalCharge[p,sc,n,eh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for eh in e2n[nd] if (p,eh) in mTEPES.peh and eh in e2e[et]                        ) for p,sc,n,ar,nd,et in sPSNARNDET], index=pd.Index(sPSNARNDET)).to_frame(name='Consumption'    ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Consumption', aggfunc='sum').rename(columns={et: et+str(' -') for et in mTEPES.et})
    OutputResults05     = pd.Series(data=[     OptModel.vENS           [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                      for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyNotServed')
    OutputResults06     = pd.Series(data=[-  mTEPES.pDemandElec        [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                      for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyDemand'   )
    OutputResults07     = pd.Series(data=[-sum(OptModel.vFlowElec      [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in lout [nd])                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowOut'  )
    OutputResults08     = pd.Series(data=[ sum(OptModel.vFlowElec      [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in lin  [nd])                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='EnergyFlowIn'   )
    # OutputResults09   = pd.Series(data=[ ar                                                                                  for ar in mTEPES.ar                                                                  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='Area'           )
    if mTEPES.ll:
        OutputResults09 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for nf,cc in loutl[nd])                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesOut'  )
        OutputResults10 = pd.Series(data=[-sum(OptModel.vLineLosses    [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for ni,cc in linl [nd])                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='LineLossesIn'   )

    if   len(mTEPES.eh) >  0 and len(mTEPES.re) >  0 and len(mTEPES.ll) >  0:
        OutputResults   = pd.concat([OutputResults01, OutputResults02, OutputResults03, OutputResults04, OutputResults05, OutputResults06, OutputResults07, OutputResults08, OutputResults09, OutputResults10], axis=1)
    elif len(mTEPES.eh) >  0 and len(mTEPES.re) >  0 and len(mTEPES.ll) == 0:
        OutputResults   = pd.concat([OutputResults01, OutputResults02, OutputResults03, OutputResults04, OutputResults05, OutputResults06, OutputResults07, OutputResults08                                  ], axis=1)
    elif len(mTEPES.eh) == 0 and len(mTEPES.re) >  0 and len(mTEPES.ll) >  0:
        OutputResults   = pd.concat([OutputResults01, OutputResults02,                                   OutputResults05, OutputResults06, OutputResults07, OutputResults08, OutputResults09, OutputResults10], axis=1)
    elif len(mTEPES.eh) == 0 and len(mTEPES.re) >  0 and len(mTEPES.ll) == 0:
        OutputResults   = pd.concat([OutputResults01, OutputResults02,                                   OutputResults05, OutputResults06, OutputResults07, OutputResults08                                  ], axis=1)
    elif len(mTEPES.eh) >  0 and len(mTEPES.re) == 0 and len(mTEPES.ll) >  0:
        OutputResults   = pd.concat([OutputResults01,                  OutputResults03, OutputResults04, OutputResults05, OutputResults06, OutputResults07, OutputResults08, OutputResults09, OutputResults10], axis=1)
    elif len(mTEPES.eh) >  0 and len(mTEPES.re) == 0 and len(mTEPES.ll) == 0:
        OutputResults   = pd.concat([OutputResults01,                  OutputResults03, OutputResults04, OutputResults05, OutputResults06, OutputResults07, OutputResults08                                  ], axis=1)
    elif len(mTEPES.eh) == 0 and len(mTEPES.re) == 0 and len(mTEPES.ll) >  0:
        OutputResults   = pd.concat([OutputResults01,                                                    OutputResults05, OutputResults06, OutputResults07, OutputResults08, OutputResults09, OutputResults10], axis=1)
    elif len(mTEPES.eh) == 0 and len(mTEPES.re) == 0 and len(mTEPES.ll) == 0:
        OutputResults   = pd.concat([OutputResults01,                                                    OutputResults05, OutputResults06, OutputResults07, OutputResults08                                  ], axis=1)

    # OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv    (f'{_path}/oT_Result_BalanceEnergy_{CaseName}.csv',     index=False, sep=',')
    # OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_parquet(f'{_path}/oT_Result_BalanceEnergy_{CaseName}.parquet', index=False, engine='pyarrow')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(f'{_path}/oT_Result_BalanceEnergyPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceEnergyPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceEnergyPerArea_{CaseName}.csv', sep=',')

    # df=OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index()
    # df['AreaFin'] = df['Area']
    # df['NodeFin'] = df['Node']
    # df.pivot_table(index=['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'AreaFin', 'NodeFin'], columns='Technology', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'AreaFin', 'NodeFin'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceEnergyPerNetwork_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                    mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr if (p,nr) in mTEPES.pnr], index=mTEPES.psnnr)
    if mTEPES.psnnr:
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCostOperation_{CaseName}.csv', sep=',')

    if mTEPES.re:
        OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput [p,sc,n,re]() for p,sc,n,re in mTEPES.psnre if (p,re) in mTEPES.pre], index=mTEPES.psnre)
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCostOandM_{CaseName}.csv', sep=',')

    if mTEPES.nr:
        if sum(mTEPES.pOperReserveUp[:,:,:,:]) + sum(mTEPES.pOperReserveDw[:,:,:,:]):
            OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                            mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in mTEPES.psnnr if (p,nr) in mTEPES.pnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCostOperatingReserve_{CaseName}.csv', sep=',')

    if mTEPES.psnehc:
        OutputToFile = pd.Series(data=[ mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost[p,sc,n,eh] * OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc if (p,eh) in mTEPES.peh], index=mTEPES.psnehc)
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionCostOperation_{CaseName}.csv', sep=',')
        if sum(mTEPES.pIndOperReserveGen[eh] for eh in mTEPES.eh if mTEPES.pIndOperReserveGen[eh] == 0) + sum(mTEPES.pIndOperReserveCon[eh] for eh in mTEPES.eh if mTEPES.pIndOperReserveCon[eh] == 0):
            OutputToFile = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                            mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pOperReserveCost[eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in mTEPES.psnehc if (p,eh) in mTEPES.peh], index=mTEPES.psnehc)
            OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionCostOperatingReserve_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,g] * OptModel.vTotalOutput[p,sc,n,g]() for p,sc,n,g in mTEPES.psng if (p,g) in mTEPES.pg], index=mTEPES.psng)
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationCostEmission_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost()                  * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'],     columns='level_3', values='MEUR', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkCostENS_{CaseName}.csv', sep=',')

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

                    if mTEPES.nr:
                        sPSNNR = [(p,sc,n,nr) for p,sc,n,nr in mTEPES.psnnr if nr in n2a[ar] and (p,nr) in mTEPES.pnr]
                        if sPSNNR:
                            OutputResults1 =     pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment [p,sc,n,nr]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp    [p,sc,n,nr]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown   [p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                            OutputResults1 =     Transformation1(OutputResults1, 'Generation Operation Cost')
                            if sum(mTEPES.pOperReserveUp[:,:,:,:]) + sum(mTEPES.pOperReserveDw[:,:,:,:]):
                                OutputResults2 = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveUp  [p,sc,n,nr]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveDown[p,sc,n,nr]()) for p,sc,n,nr in sPSNNR], index=pd.Index(sPSNNR))
                                OutputResults2 = Transformation1(OutputResults2, 'Generation Operating Reserve Cost')

                    if mTEPES.g :
                        sPSNG  = [(p,sc,n,g ) for p,sc,n,g  in mTEPES.psng  if g  in g2a[ar] and (p,g ) in mTEPES.pg ]
                        if sPSNG:
                            OutputResults6 = pd.Series(data=[ mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,g ] * OptModel.vTotalOutput[p,sc,n,g ]() for p,sc,n,g in sPSNG], index=pd.Index(sPSNG))
                            OutputResults6 = Transformation1(OutputResults6, 'Emission Cost')

                    if mTEPES.re:
                        sPSNRE = [(p,sc,n,re) for p,sc,n,re in mTEPES.psnre if re in g2a[ar] and (p,re) in mTEPES.pre]
                        if sPSNRE:
                            OutputResults3 =     pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearOMCost [re] * OptModel.vTotalOutput   [p,sc,n,re]() for p,sc,n,re in sPSNRE], index=pd.Index(sPSNRE))
                            OutputResults3 =     Transformation1(OutputResults3, 'Generation O&M Cost')

                    if mTEPES.eh:
                        sPSNES = [(p,sc,n,eh) for p,sc,n,eh in mTEPES.psnehc if eh in g2a[ar] and (p,eh) in mTEPES.peh]
                        if sPSNES:
                            OutputResults4 =     pd.Series(data=[ mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,eh] * OptModel.vESSTotalCharge[p,sc,n,eh]()  for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                            OutputResults4 =     Transformation1(OutputResults4, 'Consumption Operation Cost')
                            if sum(mTEPES.pIndOperReserveGen[eh] for eh in mTEPES.eh if mTEPES.pIndOperReserveCon[eh] == 0) + sum(mTEPES.pIndOperReserveGen[eh] for eh in mTEPES.eh if mTEPES.pIndOperReserveCon[eh] == 0):
                                OutputResults5 = pd.Series(data=[(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveUp  [p,sc,n,eh]() +
                                                                  mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveDown[p,sc,n,eh]()) for p,sc,n,eh in sPSNES], index=pd.Index(sPSNES))
                                OutputResults5 = Transformation1(OutputResults5, 'Consumption Operating Reserve Cost')

                    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if (nd,ar) in mTEPES.ndar]
                    if sPSNND:
                        OutputResults7 =         pd.Series(data=[mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost()           * OptModel.vENS        [p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
                        OutputResults7 =         Transformation1(OutputResults7, 'Reliability Cost')

                    OutputResults = pd.concat([OutputResults1, OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7]).reset_index().rename(columns={'level_0': 'Period', 'level_1': 'Scenario', 'level_2': 'Cost', 0: 'MEUR'})
                    OutputResults['MEUR/year'] = OutputResults['MEUR']
                    for p,sc in mTEPES.ps:
                        OutputResults.loc[(OutputResults['Period'] == p) & (OutputResults['Scenario'] == sc), 'MEUR/year'] = OutputResults.loc[(OutputResults['Period'] == p) & (OutputResults['Scenario'] == sc), 'MEUR'] / mTEPES.pDiscountedWeight[p] / mTEPES.pScenProb[p,sc]()
                    OutputResults.to_csv(f'{_path}/oT_Result_CostSummary_{ar}_{CaseName}.csv', sep=',', index=False)

    sPSSTNNDG         = [(p,sc,st,n,nd,g) for p,sc,st,n,nd,g in mTEPES.s2n*mTEPES.n2g if (p,g) in mTEPES.pg and (p,sc,n) in mTEPES.psn]
    OutputResults     = pd.Series(data=[ mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput   [p,sc,n,g]() for p,sc,st,n,nd,g in sPSSTNNDG], index=pd.Index(sPSSTNNDG))
    OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueEnergyGeneration_{CaseName}.csv', sep=',')

    if mTEPES.eh:
        sPSSTNNDES    = [(p,sc,st,n,nd,eh) for p,sc,st,n,nd,eh in mTEPES.s2n*mTEPES.n2g if eh in mTEPES.eh if (p,eh) in mTEPES.peh and (p,sc,n) in mTEPES.psn]
        OutputResults = pd.Series(data=[-mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vESSTotalCharge[p,sc,n,eh]() for p,sc,st,n,nd,eh in sPSSTNNDES], index=pd.Index(sPSSTNNDES))
        OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueEnergyConsumption_{CaseName}.csv', sep=',')

    if mTEPES.gc:
        GenRev    = []
        ChargeRev = []
        sPSSTNNDGC1            = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in mTEPES.s2n*mTEPES.n2g if gc in mTEPES.gc if (p,gc) in mTEPES.pgc and (p,sc,n) in mTEPES.psn]
        OutputToGenRev         = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,st,n,nd,gc in sPSSTNNDGC1], index=pd.Index(sPSSTNNDGC1))
        GenRev.append(OutputToGenRev)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (p,gc) in mTEPES.pgc and gc in o2e[ot]]):
            sPSSTNNDGC2        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for ot in mTEPES.ot if (p,gc) in mTEPES.pgc and gc in o2e[ot] and (p,sc,n) in mTEPES.psn]
            OutputChargeRevESS = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]()*OptModel.vESSTotalCharge[p,sc,n,gc]() for p,sc,st,n,nd,gc in sPSSTNNDGC2], index=pd.Index(sPSSTNNDGC2))
            ChargeRev.append(OutputChargeRevESS)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for rt in mTEPES.rt if (p,gc) in mTEPES.pgc and gc in r2r[rt]]):
            sPSSTNNDGC3        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for rt in mTEPES.rt if (p,gc) in mTEPES.pgc and gc in r2r[rt] and (p,sc,n) in mTEPES.psn]
            OutputChargeRevRES = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() * 0.0                                                                                                                                              for p,sc,st,n,nd,gc in sPSSTNNDGC3], index=pd.Index(sPSSTNNDGC3))
            ChargeRev.append(OutputChargeRevRES)
        if len([(p,sc,n,nd,gc) for p,sc,n,nd,gc in mTEPES.psn*mTEPES.n2g if gc in mTEPES.gc for ot in mTEPES.ot if (p,gc) in mTEPES.pgc and gc in o2e[ot]]):
            sPSSTNNDGC4        = [(p,sc,st,n,nd,gc) for p,sc,st,n,nd,gc in sPSSTNNDGC1      for ot in mTEPES.ot if (p,gc) in mTEPES.pgc and gc in o2e[ot] and (p,sc,n) in mTEPES.psn]
            OutputChargeRevThr = pd.Series(data=[mTEPES.pDuals["".join([f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"])]/mTEPES.pPeriodProb[p,sc]()/mTEPES.pLoadLevelDuration[p,sc,n]() * 0.0                                                                                                                                              for p,sc,st,n,nd,gc in sPSSTNNDGC4], index=pd.Index(sPSSTNNDGC4))
            ChargeRev.append(OutputChargeRevThr)
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

    if sum(mTEPES.pReserveMargin[:,:]):
        if mTEPES.gc:
            sPSSTARGC           = [(p,sc,st,ar,gc) for p,sc,st,ar,gc in mTEPES.ps*mTEPES.st*mTEPES.ar*mTEPES.gc if gc in g2a[ar] and mTEPES.pReserveMargin[p,ar] and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if gc in g2a[ar]) and sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if g in g2a[ar] and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]]
            OutputToResRev      = pd.Series(data=[mTEPES.pDuals["".join([f"eAdequacyReserveMarginElec_{p}_{sc}_{st}{ar}"])]*mTEPES.pRatedMaxPowerElec[gc]*mTEPES.pAvailability[gc]() for p,sc,st,ar,gc in sPSSTARGC], index=pd.Index(sPSSTARGC))
            ResRev              = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
            if sPSSTARGC:
                OutputToResRev /= 1e3
                OutputToResRev  = OutputToResRev.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1'], columns='level_4', values='MEUR').rename_axis(['Stages', 'Areas'], axis=0).rename_axis([None], axis=1).sum(axis=0)
                for g in OutputToResRev.index:
                    ResRev[g] = OutputToResRev[g]
    else:
        ResRev = pd.Series(data=[0.0 for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')

    if sum(mTEPES.pOperReserveUp[:,:,:,:]) and sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if nr in g2a[ar] and (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0) ) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if es in g2a[ar] and (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0)):
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,nr) in mTEPES.psnnr]):
            sPSSTNARNR    = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.s2n*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,nr) in mTEPES.psnnr]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveUp   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueOperatingReserveUp_{CaseName}.csv', sep=',')

        if len([(p,sc,n,ar,eh) for p,sc,n,ar,eh in mTEPES.psn*mTEPES.ar*mTEPES.eh if eh in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,eh) in mTEPES.psnehc]):
            sPSSTNARES    = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.s2n*mTEPES.ar*mTEPES.eh if eh in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,eh) in mTEPES.psnehc]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveUp[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueOperatingReserveUpESS_{CaseName}.csv', sep=',')

        if len([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.psn*mTEPES.ar*mTEPES.gc if ec in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,ec) in mTEPES.psnec]):
            sPSSTNAREC    = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.s2n*mTEPES.ar*mTEPES.ec if ec in g2a[ar] and mTEPES.pOperReserveUp[p,sc,n,ar] and (p,sc,n,ec) in mTEPES.psnec]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveUp_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*(OptModel.vReserveUp[p,sc,n,ec]()+OptModel.vESSReserveUp[p,sc,n,ec]()) for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
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

    if sum(mTEPES.pOperReserveDw[:,:,:,:]) and sum(1 for ar,nr in mTEPES.ar*mTEPES.nr if nr in g2a[ar] and (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveGen[nr] == 0 )) + sum(1 for ar,es in mTEPES.ar*mTEPES.es if es in g2a[ar] and (mTEPES.pIndOperReserveGen[es] == 0 or mTEPES.pIndOperReserveCon[es] == 0 )):
        if len([(p,sc,n,ar,nr) for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,nr) in mTEPES.psnnr]):
            sPSSTNARNR    = [(p,sc,st,n,ar,nr) for p,sc,st,n,ar,nr in mTEPES.s2n*mTEPES.ar*mTEPES.nr if nr in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,nr) in mTEPES.psnnr]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,st,n,ar,nr in sPSSTNARNR], index=pd.Index(sPSSTNARNR))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueOperatingReserveDw_{CaseName}.csv', sep=',')

        if len([(p,sc,n,ar,eh) for p,sc,n,ar,eh in mTEPES.psn*mTEPES.ar*mTEPES.eh if eh in g2a[ar] if mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,eh) in mTEPES.psnehc]):
            sPSSTNARES    = [(p,sc,st,n,ar,eh) for p,sc,st,n,ar,eh in mTEPES.s2n*mTEPES.ar*mTEPES.eh if eh in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,eh) in mTEPES.psnehc]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,st,n,ar,eh in sPSSTNARES], index=pd.Index(sPSSTNARES))
            OutputResults.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_5', values='MEUR').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_RevenueOperatingReserveDwESS_{CaseName}.csv', sep=',')

        if len([(p,sc,n,ar,ec) for p,sc,n,ar,ec in mTEPES.psn*mTEPES.ar*mTEPES.ec if ec in g2a[ar] if mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,ec) in mTEPES.psnec]):
            sPSSTNAREC    = [(p,sc,st,n,ar,ec) for p,sc,st,n,ar,ec in mTEPES.s2n*mTEPES.ar*mTEPES.ec if ec in g2a[ar] and mTEPES.pOperReserveDw[p,sc,n,ar] and (p,sc,n,ec) in mTEPES.psnec]
            OutputResults = pd.Series(data=[mTEPES.pDuals["".join([f"eOperReserveDw_{p}_{sc}_{st}('{n}', '{ar}')"])]/mTEPES.pPeriodProb[p,sc]()*(OptModel.vReserveDown[p,sc,n,ec]()+OptModel.vESSReserveDown[p,sc,n,ec]()) for p,sc,st,n,ar,ec in sPSSTNAREC], index=pd.Index(sPSSTNAREC), dtype='float64')
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

    if mTEPES.gc:
        GenCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,gc] * OptModel.vTotalOutput   [p,sc,n,gc]() +
                                      mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,gc] * OptModel.vCommitment    [p,sc,n,gc]() +
                                      mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       gc] * OptModel.vStartUp       [p,sc,n,gc]() +
                                      mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       gc] * OptModel.vShutDown      [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) if  gc in mTEPES.nr else
                                  sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,gc] * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        EmsCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,gc] * OptModel.vTotalOutput   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        OpGCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       gc] * OptModel.vReserveUp     [p,sc,n,gc]() +
                                      mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       gc] * OptModel.vReserveDown   [p,sc,n,gc]() for p,sc,n in mTEPES.psn if (p,gc) in mTEPES.pgc) if  gc in mTEPES.nr else
                                  0.0                                                                                                                                                                                                                             for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        CnsCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,ec] * OptModel.vESSTotalCharge[p,sc,n,ec]() for p,sc,n in mTEPES.psn if (p,ec) in mTEPES.pec) for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64')
        OpCCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       ec] * OptModel.vESSReserveUp  [p,sc,n,ec]() +
                                      mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       ec] * OptModel.vESSReserveDown[p,sc,n,ec]() for p,sc,n in mTEPES.psn if (p,ec) in mTEPES.pec) for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64')

        for gc in mTEPES.gc:
            CnsCost[gc] = 0.0 if gc not in CnsCost.index else CnsCost[gc]
            OpCCost[gc] = 0.0 if gc not in OpCCost.index else OpCCost[gc]

        InvCost = pd.Series(data=[sum(mTEPES.pDiscountedWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc]() for p in mTEPES.p if (p,gc) in mTEPES.pgc)                   for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        Balance = pd.Series(data=[GenRev[gc]+ChargeRev[gc]+UpRev[gc]+DwRev[gc]+ResRev[gc]-GenCost[gc]-EmsCost[gc]-OpGCost[gc]-CnsCost[gc]-OpCCost[gc]-InvCost[gc] for gc in mTEPES.gc], index=mTEPES.gc, dtype='float64')
        CostRecovery = pd.concat([GenRev,ChargeRev,UpRev,DwRev,ResRev,-GenCost,-EmsCost,-OpGCost,-CnsCost,-OpCCost,-InvCost,Balance], axis=1, keys=['Revenue generation [MEUR]', 'Revenue consumption [MEUR]', 'Revenue operating reserve up [MEUR]', 'Revenue operating reserve down [MEUR]', 'Revenue reserve margin [MEUR]', 'Cost operation generation [MEUR]', 'Cost emission [MEUR]', 'Cost operating reserves generation [MEUR]', 'Cost operation consumption [MEUR]', 'Cost operating reserves consumption [MEUR]', 'Cost investment [MEUR]', ' Total [MEUR]'])
        CostRecovery.stack().to_frame(name='MEUR').reset_index().pivot_table(values='MEUR', index=['level_1'], columns=['level_0']).rename_axis([None], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_CostRecovery_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    print('Writing              economic results  ... ', round(WritingResultsTime), 's')


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
            loc_df.loc[nd,'Lon'   ] = mTEPES.pNodeLon[nd]
            loc_df.loc[nd,'Zone'  ] = zn
            loc_df.loc[nd,'Demand'] = mTEPES.pDemandElec[p,sc,n,nd]*1e3

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = oT_make_series(OptModel.vFlowElec, mTEPES.psnla, 1e3)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        # tolerance to avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pLineNTCFrw[la] * 1e3 + pEpsilon for la in mTEPES.la], index=mTEPES.la),
                                     'NTCBck': pd.Series(data=[mTEPES.pLineNTCBck[la] * 1e3 + pEpsilon for la in mTEPES.la], index=mTEPES.la)}, index=mTEPES.la)

        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=False)
        line_df['vFlowElec'  ] = 0.0
        line_df['utilization'] = 0.0
        line_df['color'      ] = ''
        line_df['voltage'    ] = 0.0
        line_df['width'      ] = 0.0
        line_df['lon'        ] = 0.0
        line_df['lat'        ] = 0.0
        line_df['ni'         ] = ''
        line_df['nf'         ] = ''
        line_df['cc'         ] = 0

        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        for ni,nf,cc in mTEPES.la:
            line_df.loc[(ni,nf),'vFlowElec'  ] += OutputToFile['MW'][p,sc,n,ni,nf,cc]
            line_df.loc[(ni,nf),'utilization']  = max(line_df.loc[(ni,nf),'vFlowElec']/line_df.loc[(ni,nf),'NTCFrw'],-line_df.loc[(ni,nf),'vFlowElec']/line_df.loc[(ni,nf),'NTCBck'])*100.0
            line_df.loc[(ni,nf),'lon'        ]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
            line_df.loc[(ni,nf),'lat'        ]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
            line_df.loc[(ni,nf),'ni'         ]  = ni
            line_df.loc[(ni,nf),'nf'         ]  = nf
            line_df.loc[(ni,nf),'cc'         ] += 1

            for i in range(len(colors)):
                if 10*i <= line_df.loc[(ni,nf),'utilization'] <= 10*(i+1):
                    line_df.loc[(ni,nf),'color'] = colors[i]

            # asnp.signing black color to lines with utilization > 100%
            if line_df.loc[(ni,nf),'utilization'] > 100:
                line_df.loc[(ni,nf),'color'] = 'rgb(0,0,0)'

            line_df.loc[(ni,nf),'voltage'] = mTEPES.pLineVoltage[ni,nf,cc]
            if   700 < line_df.loc[(ni,nf),'voltage'] <= 900:
                line_df.loc[(ni,nf),'width'] = 4
            elif 500 < line_df.loc[(ni,nf),'voltage'] <= 700:
                line_df.loc[(ni,nf),'width'] = 3
            elif 350 < line_df.loc[(ni,nf),'voltage'] <= 500:
                line_df.loc[(ni,nf),'width'] = 2.5
            elif 290 < line_df.loc[(ni,nf),'voltage'] <= 350:
                line_df.loc[(ni,nf),'width'] = 2
            elif 200 < line_df.loc[(ni,nf),'voltage'] <= 290:
                line_df.loc[(ni,nf),'width'] = 1.5
            elif  50 < line_df.loc[(ni,nf),'voltage'] <= 200:
                line_df.loc[(ni,nf),'width'] = 1
            else:
                line_df.loc[(ni,nf),'width'] = 0.5

        # Rounding to decimals
        line_df = line_df.round(decimals=2)

        return loc_df, line_df

    # tolerance to avoid division by 0
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
    token = open(DIR+f'/openTEPES.mapbox_token').read()

    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' MW',))

    # Add edges
    for ni,nf,cc in mTEPES.la:
        fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowElec'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': f'Power Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetwork_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting electricity network     maps  ... ', round(PlottingNetMapsTime), 's')
