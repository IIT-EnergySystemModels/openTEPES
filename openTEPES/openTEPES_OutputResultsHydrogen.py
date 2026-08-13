"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 13, 2026

Hydrogen network operation results.

This module writes the operation of the hydrogen pipeline network: nodal balances per technology, node, and area, pipe flows, utilization, and
not-served hydrogen, plus a Plotly map of the network. The ``oT_selecting_data`` helper stays nested in the function because it builds the hydrogen node and
line frame (``ppa``). The shared flow-series and snapshot-selection helpers live in ``openTEPES_OutputResultsMapCommon``.
"""

import time
import os
import pandas            as     pd
import plotly.io         as     pio
import plotly.graph_objs as     go
from   collections       import defaultdict
from   colour            import Color

try:
    from          .openTEPES_OutputResultsCommon import _outdir
    from          .openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot
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
    lin  = defaultdict(set)
    lout = defaultdict(set)
    for ni,nf,cc in mTEPES.pa:
        lin [nf].add((ni,cc))
        lout[ni].add((nf,cc))

    # nodes to electrolyzers (l2n)
    l2n = defaultdict(set)
    # nodes to fuel heaters using H2 (b2n)
    b2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        if g in mTEPES.el:
            l2n[nd].add(g)
        if g in mTEPES.hh:
            b2n[nd].add(g)

    g2t = defaultdict(set)
    # electrolyzers to technology (e2t)
    e2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)
        if g in mTEPES.el:
            e2t[gt].add(g)

    sPSNARND    = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psn*mTEPES.arnd if len(l2n[nd]) + len(b2n[nd]) + len(lout[nd]) + len(lin[nd])]
    # the guard only depends on (p,gt), so evaluate it once per pair instead of once per (p,sc,n,ar,nd,gt) tuple of the product below
    pTechActive = {(p,gt): any((p,el) in mTEPES.pes for el in e2t[gt]) or any((p,hh) in mTEPES.phh for hh in g2t[gt]) for p in mTEPES.p for gt in mTEPES.gt}
    sPSNARNDGT  = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if pTechActive[p,gt]]

    # node-and-technology member lists, intersected once instead of once per (p,sc,n,ar,nd,gt) tuple; only the period filter stays inside the sums below
    pNodeTechEl = {(nd,gt): [el for el in l2n[nd] if el in e2t[gt]] for nd in mTEPES.nd for gt in mTEPES.gt}
    pNodeTechHh = {(nd,gt): [hh for hh in b2n[nd] if hh in g2t[gt]] for nd in mTEPES.nd for gt in mTEPES.gt}

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge [p,sc,n,el      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionH2      [el] for el in pNodeTechEl[nd,gt] if (p,el) in mTEPES.pes) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='Generation'         ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='Generation'         , aggfunc='sum')
    OutputResults3 = pd.Series(data=[ sum(OptModel.vTotalOutputHeat[p,sc,n,hh      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pProductionFunctionH2ToHeat[hh] for hh in pNodeTechHh[nd,gt] if (p,hh) in mTEPES.phh) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='ConsumptionH2ToHeat').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='ConsumptionH2ToHeat', aggfunc='sum')
    OutputResults4 = pd.Series(data=[     OptModel.vH2NS           [p,sc,n,nd      ]()                                                                                                                                  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenNotServed'  )
    OutputResults5 = pd.Series(data=[    -OptModel.vH2Exc          [p,sc,n,nd      ]()                                                                                                                                  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenExcess'     )
    OutputResults6 = pd.Series(data=[-      mTEPES.pDemandH2       [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                              for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenDemand'     )
    OutputResults7 = pd.Series(data=[-sum(OptModel.vFlowH2         [p,sc,n,nd,nf,cc]()                                                                            for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.ppa)  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowOut'    )
    OutputResults8 = pd.Series(data=[ sum(OptModel.vFlowH2         [p,sc,n,ni,nd,cc]()                                                                            for ni,cc in lin [nd] if (p,ni,nd,cc) in mTEPES.ppa)  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HydrogenFlowIn'     )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)

    # Merge duplicate columns that arise when a technology belongs to multiple generator sets
    if OutputResults.columns.duplicated().any():
        OutputResults = OutputResults.T.groupby(level=0).sum().T

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).oT.write(f'{_path}/oT_Result_BalanceHydrogenPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceHydrogenPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceHydrogenPerArea_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowH2[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=mTEPES.psnpa)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='tH2'), values='tH2', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkFlowH2PerNode_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlowH2[p,sc,n,ni,nf,cc]()/(mTEPES.pH2PipeNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlowH2[p,sc,n,ni,nf,cc]()/(mTEPES.pH2PipeNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnpa], index=mTEPES.psnpa)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkH2Utilization_{CaseName}.csv', index=False, sep=',')

    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if len(l2n[nd]) + len(b2n[nd]) + len(lout[nd]) + len(lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vH2NS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile.to_frame(name='tH2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tH2').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkHNS_{CaseName}.csv', sep=',')

    # the CSV part ends here; report its time and restart the clock, so the map print below measures only the map instead of repeating the whole elapsed time
    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    hydrogen operation results  ... ', round(WritingResultsTime), 's')

    # plot hydrogen network map
    # Sub functions
    def oT_selecting_data(p,sc,n):
        # Nodes data
        # build each column in one pass instead of writing three scalar .loc cells per node. Nodes that have no zone keep the defaults the columns used to be
        # initialised with, which is what the loop left them at by never visiting them
        pNode2Zone = dict(mTEPES.ndzn)
        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] = [mTEPES.pNodeLon[nd]          if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Zone'  ] = [pNode2Zone[nd]               if nd in pNode2Zone else ''  for nd in loc_df.index]
        loc_df['Demand'] = [mTEPES.pDemandH2[p,sc,n,nd]  if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Size'  ] = 15.0

        loc_df = loc_df.reset_index()

        # Edges data
        OutputToFile = make_flow_series(OptModel.vFlowH2, mTEPES.psnpa, 1, mTEPES.ppa)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='tH2')

        # tolerance to avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pH2PipeNTCFrw[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa),
                                     'NTCBck': pd.Series(data=[mTEPES.pH2PipeNTCBck[i] + pEpsilon for i in mTEPES.pa], index=mTEPES.pa)}, index=mTEPES.pa)
        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=False)

        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        # accumulate per node pair in plain dictionaries and write the columns once at the end. Reading and writing line_df.loc[(ni,nf),'col'] meant about
        # fifteen scalar lookups on a MultiIndex per pipe. The sequence of updates is unchanged: utilization and colour come from the accumulated flow, so
        # only the last circuit of a pair leaves the correct value, exactly as before
        pTH2    = OutputToFile['tH2'].to_dict()
        pNTCFrw = line_df['NTCFrw' ].to_dict()
        pNTCBck = line_df['NTCBck' ].to_dict()
        pFlow   = defaultdict(float)
        pCirc   = defaultdict(int  )
        pUtil   = {}
        pColor  = {}
        pLon    = {}
        pLat    = {}

        for ni,nf,cc in mTEPES.pa:
            if (p,ni,nf,cc) in mTEPES.ppa:
                pFlow[ni,nf] += pTH2[p,sc,n,ni,nf,cc]
                pUtil[ni,nf]  = max(pFlow[ni,nf]/pNTCFrw[ni,nf],-pFlow[ni,nf]/pNTCBck[ni,nf])*100.0
                pLon [ni,nf]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
                pLat [ni,nf]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
                pCirc[ni,nf] += 1

                pColorIndex   = min(int(pUtil[ni,nf] // 10), ncolors-1)
                pColor[ni,nf] = colors[max(pColorIndex, 0)]

        # the defaults below are the ones the columns used to be initialised with, so node pairs left untouched by the loop keep exactly the same values
        line_df['vFlowH2'    ] = [pFlow .get(pa, 0.0) for pa in line_df.index]
        line_df['utilization'] = [pUtil .get(pa, 0.0) for pa in line_df.index]
        line_df['color'      ] = [pColor.get(pa, '' ) for pa in line_df.index]
        line_df['width'      ] = 3.0
        line_df['lon'        ] = [pLon  .get(pa, 0.0) for pa in line_df.index]
        line_df['lat'        ] = [pLat  .get(pa, 0.0) for pa in line_df.index]
        line_df['ni'         ] = [ni if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['nf'         ] = [nf if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['cc'         ] = [pCirc .get(pa, 0  ) for pa in line_df.index]

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
    with open(os.path.join(DIR, 'openTEPES.mapbox_token')) as f:
        token = f.read()

    pio.renderers.default = 'chrome'
    fig = go.Figure()

    # Add nodes
    fig.add_trace(go.Scattermapbox(lat=loc_df['Lat'], lon=loc_df['Lon'], mode='markers', marker=go.scattermapbox.Marker(size=loc_df['Size']*10, sizeref=1.1, sizemode='area', color='LightSkyBlue',), hoverinfo='text', text='<br>Node: ' + loc_df['index'] + '<br>[Lon, Lat]: ' + '(' + loc_df['Lon'].astype(str) + ', ' + loc_df['Lat'].astype(str) + ')' + '<br>Zone: ' + loc_df['Zone'] + '<br>Demand: ' + loc_df['Demand'].astype(str) + ' tH2',))

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
