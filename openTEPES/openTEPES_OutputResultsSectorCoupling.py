"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Sector-coupling network operation results, hydrogen and heat.

This module writes the operation of the hydrogen pipeline network and the
heat pipe network: nodal balances per technology, node, and area, pipe
flows, utilization, and not-served energy, plus a Plotly map of each network.
The ``oT_selecting_data`` helper stays nested in each function because it
builds a sector-specific node and line frame (``ppa`` for hydrogen, ``pha``
for heat). The shared flow-series and snapshot-selection helpers live in
``openTEPES_OutputResultsMapCommon``.
"""

import time
import os
import pandas            as     pd
import plotly.io         as     pio
import plotly.graph_objs as     go
from   collections       import defaultdict
from   colour            import Color

try:
    from .openTEPES_OutputResultsCommon import _outdir
    from .openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir
    from openTEPES.openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot


def NetworkH2OperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the hydrogen pipeline network operation
    _path = _outdir(DirName, CaseName, mTEPES)
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

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psn*mTEPES.arnd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for el in e2t[gt] if (p,el) in mTEPES.pg)                                      ]

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge[p,sc,n,el      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionH2[el] for el in mTEPES.el if (p,el) in mTEPES.pes and el in e2n[nd] and el in e2t[gt]) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'       ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation', aggfunc='sum')
    OutputResults3 = pd.Series(data=[     OptModel.vH2NS          [p,sc,n,nd      ]()                                                                                                                                                       for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenNotServed')
    OutputResults4 = pd.Series(data=[-      mTEPES.pDemandH2      [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                                                   for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenDemand'   )
    OutputResults5 = pd.Series(data=[-sum(OptModel.vFlowH2        [p,sc,n,nd,nf,cc]()                                                                      for nf,cc in lout[nd])                                                           for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowOut'  )
    OutputResults6 = pd.Series(data=[ sum(OptModel.vFlowH2        [p,sc,n,ni,nd,cc]()                                                                      for ni,cc in lin [nd])                                                           for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6], axis=1)

    # OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'tH2'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceHydrogen_{CaseName}.csv', index=False, sep=',')

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).to_csv(f'{_path}/oT_Result_BalanceHydrogenPerArea_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowH2[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=mTEPES.psnpa)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='tH2'), values='tH2', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkFlowH2PerNode_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlowH2[p,sc,n,ni,nf,cc]()/(mTEPES.pH2PipeNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlowH2[p,sc,n,ni,nf,cc]()/(mTEPES.pH2PipeNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=mTEPES.psnpa)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().to_csv(f'{_path}/oT_Result_NetworkH2Utilization_{CaseName}.csv', index=False, sep=',')

    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vH2NS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile.to_frame(name='tH2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_NetworkHNS_{CaseName}.csv', sep=',')

    # plot hydrogen network map
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
            loc_df.loc[nd,'Demand'] = mTEPES.pDemandH2[p,sc,n,nd]

        loc_df = loc_df.reset_index().rename(columns={'Type': 'Scenario'}, inplace=False)

        # Edges data
        OutputToFile = make_flow_series(OptModel.vFlowH2, mTEPES.psnpa, 1, mTEPES.ppa)
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
            if (p,ni,nf,cc) in mTEPES.ppa:
                line_df.loc[(ni,nf),'vFlowH2'    ] += OutputToFile['tH2'][p,sc,n,ni,nf,cc]
                line_df.loc[(ni,nf),'utilization']  = max(line_df.loc[(ni,nf),'vFlowH2']/line_df.loc[(ni,nf),'NTCFrw'],-line_df.loc[(ni,nf),'vFlowH2']/line_df.loc[(ni,nf),'NTCBck'])*100.0
                line_df.loc[(ni,nf),'lon'        ]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
                line_df.loc[(ni,nf),'lat'        ]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
                line_df.loc[(ni,nf),'ni'         ]  = ni
                line_df.loc[(ni,nf),'nf'         ]  = nf
                line_df.loc[(ni,nf),'cc'         ] += 1

                for i in range(len(colors)):
                    if 10*i <= line_df.loc[(ni,nf),'utilization'] <= 10*(i+1):
                        line_df.loc[(ni,nf),'color'] = colors[i]

        # Rounding to decimals of the numerical columns
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
    for ni,nf,cc in mTEPES.pa:
        if (p,ni,nf,cc) in mTEPES.ppa:
            fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowH2'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': f'Hydrogen Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetworkH2_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting hydrogen    network     maps  ... ', round(PlottingNetMapsTime), 's')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    hydrogen operation results  ... ', round(WritingResultsTime), 's')


# @profile
def NetworkHeatOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the heat pipe network operation
    _path = _outdir(DirName, CaseName, mTEPES)
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

    sPSNARND   = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psn*mTEPES.arnd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])]
    sPSNARNDGT = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if sum(1 for ch in c2t[gt] if (p,ch) in mTEPES.pg) + sum(1 for hp in h2t[gt] if (p,hp) in mTEPES.pg)               ]

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge [p,sc,n,hp      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionHeat[hp] for hp in mTEPES.hp if hp in h2n[nd] and hp in h2t[gt])                         for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationHeatPumps').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationHeatPumps', aggfunc='sum')
    OutputResults3 = pd.Series(data=[ sum(OptModel.vTotalOutput    [p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pPower2HeatRatio       [ch] for ch in mTEPES.ch if ch in c2n[nd] and ch in c2t[gt] and ch not in mTEPES.bo) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationCHPs'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationCHPs'     , aggfunc='sum')
    OutputResults4 = pd.Series(data=[ sum(OptModel.vTotalOutputHeat[p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ch in mTEPES.ch if ch in c2n[nd] and ch in c2t[gt] and ch     in mTEPES.bo) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationBoilers'  ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationBoilers'  , aggfunc='sum')
    OutputResults5 = pd.Series(data=[     OptModel.vHeatNS         [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                                                    for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatNotServed')
    OutputResults6 = pd.Series(data=[-      mTEPES.pDemandHeat     [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                                                    for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatDemand'   )
    OutputResults7 = pd.Series(data=[-sum(OptModel.vFlowHeat       [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for nf,cc in lout[nd])                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowOut'  )
    OutputResults8 = pd.Series(data=[ sum(OptModel.vFlowHeat       [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ni,cc in lin [nd])                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)

    # OutputResults.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node', 'Technology'], axis=0).reset_index().rename(columns={0: 'GWh'}, inplace=False).to_csv(f'{_path}/oT_Result_BalanceHeat_{CaseName}.csv', index=False, sep=',')

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
        OutputToFile = make_flow_series(OptModel.vFlowHeat, mTEPES.psnha, 1, mTEPES.pha)
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
            if (p,ni,nf,cc) in mTEPES.pha:
                line_df.loc[(ni,nf),'vFlowHeat' ] += OutputToFile['MW'][p,sc,n,ni,nf,cc]
                line_df.loc[(ni,nf),'utilization'] = max(line_df.loc[(ni,nf),'vFlowHeat']/line_df.loc[(ni,nf),'NTCFrw'],-line_df.loc[(ni,nf),'vFlowHeat']/line_df.loc[(ni,nf),'NTCBck'])*100.0
                line_df.loc[(ni,nf),'lon']  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
                line_df.loc[(ni,nf),'lat']  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
                line_df.loc[(ni,nf),'ni']  = ni
                line_df.loc[(ni,nf),'nf']  = nf
                line_df.loc[(ni,nf),'cc'] += 1

                for i in range(len(colors)):
                    if 10*i <= line_df.loc[(ni,nf),'utilization'] <= 10*(i+1):
                        line_df.loc[(ni,nf),'color'] = colors[i]

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
    for ni,nf,cc in mTEPES.ha:
        if (p,ni,nf,cc) in mTEPES.pha:
            fig.add_trace(go.Scattermapbox(lon=[pos_dict[ni][0], pos_dict[nf][0]], lat=[pos_dict[ni][1], pos_dict[nf][1]], mode='lines+markers', marker=dict(size=0, showscale=True, colorbar={'title': 'Utilization [%]', 'title_side': 'top', 'thickness': 8, 'ticksuffix': '%'}, colorscale=[[0, 'lightgreen'], [1, 'darkred']], cmin=0, cmax=100,), line=dict(width=line_df.loc[(ni,nf),'width'], color=line_df.loc[(ni,nf),'color']), opacity=1, hoverinfo='text', textposition='middle center',))

    # Add legends related to the lines
    fig.add_trace(go.Scattermapbox(lat=line_df['lat'], lon=line_df['lon'], mode='markers', marker=go.scattermapbox.Marker(size=20, sizeref=1.1, sizemode='area', color='LightSkyBlue',), opacity=0, hoverinfo='text', text='<br>Line: '+line_df['ni']+' → '+line_df['nf']+'<br># circuits: '+line_df['cc'].astype(str)+'<br>NTC Forward: '+line_df['NTCFrw'].astype(str)+'<br>NTC Backward: '+line_df['NTCBck'].astype(str)+'<br>Power flow: '+line_df['vFlowHeat'].astype(str)+'<br>Utilization [%]: '+line_df['utilization'].astype(str),))

    # Setting up the layout
    fig.update_layout(title={'text': f'Heat Network: {CaseName}<br>Period: {p}; Scenario: {sc}; LoadLevel: '+n, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}, font=dict(size=14), hovermode='closest', geo=dict(projection_type='azimuthal equal area', showland=True,), mapbox=dict(style='dark', accesstoken=token, bearing=0, center=dict(lat=(loc_df['Lat'].max()+loc_df['Lat'].min())*0.5, lon=(loc_df['Lon'].max()+loc_df['Lon'].min())*0.5), pitch=0, zoom=5), showlegend=False,)

    # Saving the figure
    fig.write_html(f'{_path}/oT_Plot_MapNetworkHeat_{CaseName}.html')

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting heat        network     maps  ... ', round(PlottingNetMapsTime), 's')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  heat netwk operation results  ... ', round(WritingResultsTime), 's')
