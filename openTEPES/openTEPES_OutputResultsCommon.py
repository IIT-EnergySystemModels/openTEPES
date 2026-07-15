"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Shared helpers used by every openTEPES_OutputResults<Concern> module.

This module holds the small pieces that more than one results module needs:
the output-directory resolver and the three Altair plot builders. Each
concern module imports from here so the logic lives in one place and the
plot styling stays the same across investment, generation, storage,
economic, and network outputs.
"""

import os
import pandas as     pd
import altair as     alt


def _outdir(DirName, CaseName, mTEPES):
    """Return effective output directory.

    If `mTEPES.pOutputPath` is set (by openTEPES_run when --out is given) use it;
    otherwise fall back to the case input directory `<DirName>/<CaseName>` —
    preserving the historical behavior. Path is created on first call.
    """
    path = getattr(mTEPES, "pOutputPath", None) or os.path.join(DirName, CaseName)
    os.makedirs(path, exist_ok=True)
    return path

# from line_profiler import profile


# Definition of Pie plots
# @profile
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

    base  = alt.Chart(OutputToPlot).encode(theta=alt.Theta(ComposedValue, type='quantitative', stack=True), color=alt.Color(ComposedCategory, scale=alt.Scale(scheme='category20c'), type='nominal', legend=alt.Legend(title=Category))).properties(width=800, height=800)
    pie   = base.mark_arc(outerRadius=240)
    text  = base.mark_text(radius=340, size=15).encode(text='Label:N')
    chart = pie+text
    # chart = chart.resolve_scale(theta='independent')
    chart = alt.layer(pie, text, data=OutputToPlot).resolve_scale(theta='independent')

    return chart


# Definition of Area plots
# @profile
def AreaPlots(period, scenario, df, Category, X, Y, OperationType):
    Results = df.loc[period,scenario,:,:]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # Change the format of the LoadLevel
    Results[X] = Results[X].str[:14]
    Results[X] = (Results[X]+'+01:00')
    Results[X] = (str(period)+'-'+Results[X])
    Results[X] = pd.to_datetime(Results[X], format='%Y-%m-%d %H:%M:%S%z', errors='coerce')
    # Composed Names
    C_C = Category+':N'

    C_X = X+':T'
    C_Y = Y+':Q'
    # Define and build the chart
    # alt.data_transformers.enable('json')
    alt.data_transformers.disable_max_rows()
    interval  = alt.selection_interval(encodings=['x'])
    selection = alt.selection_point(fields=[Category], bind='legend')

    base  = alt.Chart(Results).mark_area().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2))).add_params(selection)
    chart = base.encode(alt.X(C_X, axis=alt.Axis(title='')).scale(domain=interval)).properties(width=1200, height=450)
    view  = base.add_params(interval).properties(width=1200, height=50)
    plot  = alt.vconcat(chart, view)

    return plot


# Definition of Line plots
# @profile
def LinePlots(period, scenario, df, Category, X, Y, OperationType):
    Results = df.loc[period,scenario,:,:].rename_axis(['level_0', 'level_1'], axis=0)
    Results.columns = [0]
    Results = Results.reset_index().rename(columns={'level_0': X, 'level_1': Category, 0: Y})
    # Change the format of the LoadLevel
    Results[X] = Results[X].str[:14]
    Results[X] = (Results[X]+'+01:00')
    Results[X] = (str(period)+'-'+Results[X])
    Results[X] = pd.to_datetime(Results[X], format='%Y-%m-%d %H:%M:%S%z', errors='coerce')
    # Composed Names
    C_C = Category+':N'

    C_X = X+':T'
    C_Y = Y+':Q'
    # Define and build the chart
    # alt.data_transformers.enable('json')
    alt.data_transformers.disable_max_rows()
    interval = alt.selection_interval(encodings=['x'])
    selection = alt.selection_point(fields=[Category], bind='legend')

    base  = alt.Chart(Results).mark_line().encode(x=alt.X(C_X, axis=alt.Axis(title='')), y=alt.Y(C_Y, axis=alt.Axis(title=Y)), color=alt.Color(C_C, scale=alt.Scale(scheme='category20c')), opacity=alt.condition(selection, alt.value(1), alt.value(0.2)))
    chart = base.encode(alt.X(C_X, axis=alt.Axis(title='')).scale(domain=interval)).properties(width=1200, height=450)
    view  = base.properties(width=1200, height=50)
    plot  = alt.vconcat(chart, view).add_params(selection, interval)

    return plot
