"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 12, 2026

Electric network operation results and network map.

This module writes the electricity transmission operation: line commitment
and switching, power flows per node and per area, transport, utilization,
losses, voltage angles, and not-served power and energy. The map function
draws a Plotly map of the power network coloured by line utilization. Both
work on electric data only; the hydrogen and heat network maps live in the
sector-coupling module. The ``oT_selecting_data`` helper stays nested in the
map function because it builds the electric node and line frame (line set
``pla``). The shared flow-series and snapshot-selection helpers live in
``openTEPES_OutputResultsMapCommon``.
"""

import time
import os
import math
import pandas            as     pd
import plotly.io         as     pio
import plotly.graph_objs as     go
from   colour            import Color

try:
    from .openTEPES_OutputResultsCommon import _outdir
    from .openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir
    from openTEPES.openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the electric network operation
    _path = _outdir(DirName, CaseName, mTEPES)
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
        OutputResults = pd.Series(data=[OptModel.vFlowElec[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pPeriodProb[p,sc]()*mTEPES.pLineLength[ni,nf,cc]()*1e-3 for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
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

    if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndPTDF == 0:
        OutputToFile = pd.Series(data=[OptModel.vTheta[p,sc,n,nd]()                                   for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
        OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkAngle_{CaseName}.csv', sep=',')

        # warn if the voltage-angle bound (pMaxTheta = pi/2) is (nearly) binding -- this
        # indicates either an undersized Big-M on AC candidate lines, an overconstrained
        # network, or genuinely insufficient transmission. A binding pi/2 bound clips
        # the DC-OPF solution non-physically and inflates costs.
        pMaxThetaTol = 1e-2
        pMaxThetaVal = math.pi / 2
        pBindingTheta = OutputToFile.abs().ge((1.0 - pMaxThetaTol) * pMaxThetaVal)
        if pBindingTheta.any():
            nBinding = int(pBindingTheta.sum())
            maxAbs   = float(OutputToFile.abs().max())
            print(f'WARNING: voltage angle bound pMaxTheta = pi/2 is (nearly) binding in {nBinding} (period, scenario, loadlevel, node) entries; max|theta| = {maxAbs:.6f} rad ({maxAbs/pMaxThetaVal*100:.2f} %% of pi/2). Inspect oT_Result_NetworkAngle_{CaseName}.csv -- the bound may be clipping the DC-OPF solution.')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()                                     for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkPNS_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[p,sc,n,nd]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkENS_{CaseName}.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing elect netwk operation results  ... ', round(WritingResultsTime), 's')


# @profile
def NetworkMapResults(DirName, CaseName, OptModel, mTEPES):
    # %% plotting the network in a map
    _path = _outdir(DirName, CaseName, mTEPES)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # Sub functions
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
            loc_df.loc[nd,'Demand'] = mTEPES.pDemandElec[p,sc,n,nd]()*1e3

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = make_flow_series(OptModel.vFlowElec, mTEPES.psnla, 1e3, mTEPES.pla)
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
            if (p,ni,nf,cc) in mTEPES.pla:
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

                # assigning black color to lines with utilization > 100%
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

    p, sc, n = pick_snapshot(mTEPES)

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
        if (p,ni,nf,cc) in mTEPES.pla:
            fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowElec'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': f'Power Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetwork_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting electricity network     maps  ... ', round(PlottingNetMapsTime), 's')
