"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 23, 2026

Heat network operation results.

This module writes the operation of the heat pipe network: nodal balances per technology, node, and area, pipe flows, utilization, and not-served heat, plus
a Plotly map of the network. The ``oT_selecting_data`` helper stays nested in the function because it builds the heat node and line frame (``pha``). The
shared flow-series and snapshot-selection helpers live in ``openTEPES_OutputResultsMapCommon``.
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


# @profile
def NetworkHeatOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the heat pipe network operation
    _path = _outdir(DirName, CaseName, mTEPES)
    DIR   = os.path.dirname(__file__)
    StartTime = time.time()

    # incoming and outgoing heat pipes (lin) (lout)
    lin  = defaultdict(set)
    lout = defaultdict(set)
    for ni,nf,cc in mTEPES.ha:
        lin [nf].add((ni,cc))
        lout[ni].add((nf,cc))

    # nodes to CHPs (c2n)
    c2n = defaultdict(set)
    # nodes to heat pumps (h2n)
    h2n = defaultdict(set)
    # nodes to CHPs (chp2n)
    chp2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        if g in mTEPES.ch:
            c2n[nd].add(g)
        if g in mTEPES.hp:
            h2n[nd].add(g)
        if g in mTEPES.chp:
            chp2n[nd].add(g)

    # CHPs to technology (c2t)
    c2t = defaultdict(set)
    # heat pumps to technology (h2t)
    h2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        if g in mTEPES.ch:
            c2t[gt].add(g)
        if g in mTEPES.hp:
            h2t[gt].add(g)

    sPSNARND    = [(p,sc,n,ar,nd)    for p,sc,n,ar,nd    in mTEPES.psn*mTEPES.arnd if len(chp2n[nd]) + len(lout[nd]) + len(lin[nd])]
    pTechActive = {(p,gt): any((p,ch) in mTEPES.pch for ch in c2t[gt]) or any((p,hp) in mTEPES.php for hp in h2t[gt]) for p in mTEPES.p for gt in mTEPES.gt}
    sPSNARNDGT  = [(p,sc,n,ar,nd,gt) for p,sc,n,ar,nd,gt in sPSNARND*mTEPES.gt     if pTechActive[p,gt]]

    # node-and-technology member lists, intersected once instead of once per (p,sc,n,ar,nd,gt) tuple; only the period filter stays inside the sums below
    pNodeTechHp = {(nd,gt): [hp for hp in h2n[nd] if hp in h2t[gt]                          ] for nd in mTEPES.nd for gt in mTEPES.gt}
    pNodeTechCh = {(nd,gt): [ch for ch in c2n[nd] if ch in c2t[gt] and ch not in mTEPES.bo  ] for nd in mTEPES.nd for gt in mTEPES.gt}
    pNodeTechBo = {(nd,gt): [ch for ch in c2n[nd] if ch in c2t[gt] and ch     in mTEPES.bo  ] for nd in mTEPES.nd for gt in mTEPES.gt}

    OutputResults2 = pd.Series(data=[ sum(OptModel.vESSTotalCharge [p,sc,n,hp      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pProductionFunctionHeat[hp] for hp in pNodeTechHp[nd,gt] if (p,hp) in mTEPES.php) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationHeatPumps').reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationHeatPumps', aggfunc='sum')
    OutputResults3 = pd.Series(data=[ sum(OptModel.vTotalOutput    [p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()/mTEPES.pPower2HeatRatio       [ch] for ch in pNodeTechCh[nd,gt] if (p,ch) in mTEPES.pch) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationCHPs'     ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationCHPs'     , aggfunc='sum')
    OutputResults4 = pd.Series(data=[ sum(OptModel.vTotalOutputHeat[p,sc,n,ch      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ch in pNodeTechBo[nd,gt] if (p,ch) in mTEPES.pch) for p,sc,n,ar,nd,gt in sPSNARNDGT], index=pd.Index(sPSNARNDGT)).to_frame(name='GenerationBoilers'  ).reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values='GenerationBoilers'  , aggfunc='sum')
    OutputResults5 = pd.Series(data=[     OptModel.vHeatNS         [p,sc,n,nd      ]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatNotServed')
    OutputResults6 = pd.Series(data=[-      mTEPES.pDemandHeat     [p,sc,n,nd      ]  *mTEPES.pLoadLevelDuration[p,sc,n]()                                                                                          for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatDemand'   )
    OutputResults7 = pd.Series(data=[-sum(OptModel.vFlowHeat       [p,sc,n,nd,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pha)  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowOut'  )
    OutputResults8 = pd.Series(data=[ sum(OptModel.vFlowHeat       [p,sc,n,ni,nd,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]()                                    for ni,cc in lin [nd] if (p,ni,nd,cc) in mTEPES.pha)  for p,sc,n,ar,nd    in sPSNARND  ], index=pd.Index(sPSNARND  )).to_frame(name='HeatFlowIn'   )
    OutputResults  = pd.concat([OutputResults2, OutputResults3, OutputResults4, OutputResults5, OutputResults6, OutputResults7, OutputResults8], axis=1)

    # Merge duplicate columns that arise when a technology belongs to multiple generator sets
    if OutputResults.columns.duplicated().any():
        OutputResults = OutputResults.T.groupby(level=0).sum().T

    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2','level_3','level_4'], columns='level_5', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Area', 'Node'], axis=0).oT.write(f'{_path}/oT_Result_BalanceHeatPerTech_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1','level_2'          ,'level_5'], columns='level_4', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceHeatPerNode_{CaseName}.csv', sep=',')
    OutputResults.stack().reset_index().pivot_table(index=['level_0','level_1'                    ,'level_5'], columns='level_3', values=0, aggfunc='sum').rename_axis(['Period', 'Scenario'             , 'Technology'  ], axis=0).oT.write(f'{_path}/oT_Result_BalanceHeatPerArea_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
    OutputToFile *= 1e3
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkFlowHeatPerNode_{CaseName}.csv', index=False, sep=',')

    # map each node to its area(s) once and expand the pipe flows to area pairs directly
    Nd2Ar = {}
    for nd,ar in mTEPES.ndar:
        Nd2Ar.setdefault(nd, []).append(ar)
    PSNHAARAR = [(p,sc,n,ni,nf,cc,ai,af) for p,sc,n,ni,nf,cc in mTEPES.psnha for ai in Nd2Ar.get(ni, []) for af in Nd2Ar.get(nf, [])]
    OutputToFile = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,ni,nf,cc,ai,af in PSNHAARAR], index=pd.Index(PSNHAARAR))
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']
    pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1).reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyHeatPerArea_{CaseName}.csv',      index=False, sep=',')
    pd.pivot_table(OutputToFile.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario'],              columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1).reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyHeatTotalPerArea_{CaseName}.csv', index=False, sep=',')

    if mTEPES.ha:
        OutputResults = pd.Series(data=[OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()*(mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pPeriodProb[p,sc]())*(mTEPES.pHeatPipeLength[ni,nf,cc]()*1e-3) for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
        OutputResults.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = OutputResults.reset_index().groupby(['InitialNode', 'FinalNode', 'Circuit']).sum(numeric_only=True)[0]
        OutputResults.to_frame(name='GWh-Mkm').rename_axis(['InitialNode', 'FinalNode', 'Circuit'], axis=0).reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyHeatTransport_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()/(mTEPES.pHeatPipeNTCFrw[ni,nf,cc]+pEpsilon),-OptModel.vFlowHeat[p,sc,n,ni,nf,cc]()/(mTEPES.pHeatPipeNTCBck[ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnha], index=mTEPES.psnha)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkHeatUtilization_{CaseName}.csv', index=False, sep=',')
    sPSNND = [(p,sc,n,nd) for p,sc,n,nd in mTEPES.psnnd if len(chp2n[nd]) + len(lout[nd]) + len(lin[nd])]
    OutputToFile = pd.Series(data=[OptModel.vHeatNS[p,sc,n,nd]() for p,sc,n,nd in sPSNND], index=pd.Index(sPSNND))
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkHeatNS_{CaseName}.csv', sep=',')

    # the CSV part ends here; report its time and restart the clock, so the map print below measures only the map instead of repeating the whole elapsed time
    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing  heat netwk operation results  ... ', round(WritingResultsTime), 's')

    # plot heat network map
    # Sub functions
    def oT_selecting_data(p,sc,n):
        # Nodes data
        # build each column in one pass instead of writing three scalar .loc cells per node. Nodes that have no zone keep the defaults the columns used to be
        # initialised with, which is what the loop left them at by never visiting them
        # a comprehension, NOT dict(mTEPES.ndzn): dict() on a Pyomo scalar Set goes through the component API and yields {None: <the Set>}, never the elements
        pNode2Zone = {nd: zn for nd,zn in mTEPES.ndzn}
        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] = [mTEPES.pNodeLon[nd]               if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Zone'  ] = [pNode2Zone[nd]                    if nd in pNode2Zone else ''  for nd in loc_df.index]
        loc_df['Demand'] = [mTEPES.pDemandHeat[p,sc,n,nd]*1e3 if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Size'  ] = 15.0

        loc_df = loc_df.reset_index()

        # Edges data
        OutputToFile = make_flow_series(OptModel.vFlowHeat, mTEPES.psnha, 1, mTEPES.pha)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = OutputToFile.to_frame(name='MW')

        # tolerance to avoid division by 0
        pEpsilon = 1e-6

        line_df = pd.DataFrame(data={'NTCFrw': pd.Series(data=[mTEPES.pHeatPipeNTCFrw[i] + pEpsilon for i in mTEPES.ha], index=mTEPES.ha),
                                     'NTCBck': pd.Series(data=[mTEPES.pHeatPipeNTCBck[i] + pEpsilon for i in mTEPES.ha], index=mTEPES.ha)}, index=mTEPES.ha)
        line_df = line_df.groupby(level=[0,1]).sum(numeric_only=False)

        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        # hex, not 'rgb'+str(x.rgb): colour's .rgb components are 0-1 while CSS rgb() expects 0-255, so the browser rounded every line to near-black
        colors = [x.hex_l for x in colors]

        # accumulate per node pair in plain dictionaries and write the columns once at the end. Reading and writing line_df.loc[(ni,nf),'col'] meant about
        # fifteen scalar lookups on a MultiIndex per pipe. The sequence of updates is unchanged: utilization and colour come from the accumulated flow, so
        # only the last circuit of a pair leaves the correct value, exactly as before
        pMW     = OutputToFile['MW'].to_dict()
        pNTCFrw = line_df['NTCFrw' ].to_dict()
        pNTCBck = line_df['NTCBck' ].to_dict()
        pFlow   = defaultdict(float)
        pCirc   = defaultdict(int  )
        pUtil   = {}
        pColor  = {}
        pLon    = {}
        pLat    = {}

        for ni,nf,cc in mTEPES.ha:
            if (p,ni,nf,cc) in mTEPES.pha:
                pFlow[ni,nf] += pMW[p,sc,n,ni,nf,cc]
                pUtil[ni,nf]  = max(pFlow[ni,nf]/pNTCFrw[ni,nf],-pFlow[ni,nf]/pNTCBck[ni,nf])*100.0
                pLon [ni,nf]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
                pLat [ni,nf]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
                pCirc[ni,nf] += 1

                pColorIndex   = min(int(pUtil[ni,nf] // 10), ncolors-1)
                pColor[ni,nf] = colors[max(pColorIndex, 0)]

        # the defaults below are the ones the columns used to be initialised with, so node pairs left untouched by the loop keep exactly the same values
        line_df['vFlowHeat'  ] = [pFlow .get(ha, 0.0) for ha in line_df.index]
        line_df['utilization'] = [pUtil .get(ha, 0.0) for ha in line_df.index]
        line_df['color'      ] = [pColor.get(ha, '' ) for ha in line_df.index]
        line_df['width'      ] = 3.0
        line_df['lon'        ] = [pLon  .get(ha, 0.0) for ha in line_df.index]
        line_df['lat'        ] = [pLat  .get(ha, 0.0) for ha in line_df.index]
        line_df['ni'         ] = [ni if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['nf'         ] = [nf if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['cc'         ] = [pCirc .get(ha, 0  ) for ha in line_df.index]

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
    with open(os.path.join(DIR, 'openTEPES.mapbox_token')) as f:
        token = f.read()

    pio.renderers.default = 'chrome'
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
