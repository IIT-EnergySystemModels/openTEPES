"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 22, 2026

Electric network operation results and network map.

This module writes the electricity transmission operation: line commitment and switching, power flows per node and per area, transport, utilization, losses,
voltage angles, and not-served power and energy. The map function draws a Plotly map of the power network coloured by line utilization. Both work on electric
data only; the hydrogen and heat network maps live in the sector-coupling module. The ``oT_selecting_data`` helper stays nested in the map function because it
builds the electric node and line frame (line set ``pla``). The shared flow-series and snapshot-selection helpers live in ``openTEPES_OutputResultsMapCommon``.
"""

import time
import os
import math
import pandas            as     pd
import plotly.io         as     pio
import plotly.graph_objs as     go
import openTEPES.openTEPES_DataConfiguration as NM
from   collections       import defaultdict
from   colour            import Color

try:
    from          .openTEPES_OutputResultsCommon    import _outdir
    from          .openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon    import _outdir
    from openTEPES.openTEPES_OutputResultsMapCommon import make_flow_series, pick_snapshot


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the electric network operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # cache the Pyomo evaluations reused across the outputs below. Each call to a variable/parameter (e.g. vFlowElec[...]()) is costly, so evaluate the electric
    # flow, the load-level duration and the period probability once per index and reuse the results instead of re-querying the model for every output file.
    # pLoadLevelDuration and pPeriodProb are declared over psn and ps, so build their caches from those sets directly. Deriving them from psnla instead cost one
    # tuple slice and one membership test per line and load level, to end up with the very same |psn| and |ps| entries.
    Dur  = {Psn: mTEPES.pLoadLevelDuration[Psn]() for Psn in mTEPES.psn  }
    Prob = {Ps:  mTEPES.pPeriodProb       [Ps ]() for Ps  in mTEPES.ps   }
    Flow = {Key: OptModel.vFlowElec       [Key]() for Key in mTEPES.psnla}

    if any(mTEPES.pIndBinLineSwitch[idx] for idx in mTEPES.pIndBinLineSwitch):
        if mTEPES.lc:
            OutputToFile = pd.Series(data=[OptModel.vLineCommit  [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
            OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
            OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
            OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkCommitment_{CaseName}.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOnState [p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkSwitchOn_{CaseName}.csv', index=False, sep=',')
        OutputToFile = pd.Series(data=[OptModel.vLineOffState[p,sc,n,ni,nf,cc]() for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkSwitchOff_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.Series(data=[Flow[k] for k in mTEPES.psnla], index=mTEPES.psnla)
    OutputToFile *= 1e3
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkFlowElecPerNode_{CaseName}.csv', index=False, sep=',')

    # map each node to its area(s) once and expand the line flows to area pairs directly. This avoids materialising the psnla x ar x ar product (potentially
    # millions of tuples) only to discard almost all of them with the membership filter.
    Nd2Ar = {}
    for nd, ar in mTEPES.ndar:
        Nd2Ar.setdefault(nd, []).append(ar)
    PSNLAARAR = [(p,sc,n,ni,nf,cc,ai,af) for p,sc,n,ni,nf,cc in mTEPES.psnla for ai in Nd2Ar.get(ni, []) for af in Nd2Ar.get(nf, [])]

    # the per-area energy series is identical for both output files below, so build it once and pivot it two different ways rather than recomputing it twice.
    OutputEnergy = pd.Series(data=[Flow[p,sc,n,ni,nf,cc]*Dur[p,sc,n] for p,sc,n,ni,nf,cc,ai,af in PSNLAARAR], index=pd.Index(PSNLAARAR))
    OutputEnergy.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'InitialArea', 'FinalArea']

    OutputToFile = pd.pivot_table(OutputEnergy.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyElecPerArea_{CaseName}.csv', index=False, sep=',')

    OutputToFile = pd.pivot_table(OutputEnergy.to_frame(name='GWh'), values='GWh', index=['Period', 'Scenario'], columns=['InitialArea', 'FinalArea'], fill_value=0.0).rename_axis([None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyElecTotalPerArea_{CaseName}.csv', index=False, sep=',')

    if mTEPES.la:
        LineLength = {la: mTEPES.pLineLength[la]() for la in mTEPES.la}
        OutputResults = pd.Series(data=[Flow[p,sc,n,ni,nf,cc]*Dur[p,sc,n]*Prob[p,sc]*LineLength[ni,nf,cc]*1e-3 for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
        OutputResults.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputResults = OutputResults.groupby(level=[3,4,5]).sum()
        OutputResults.to_frame(name='GWh-Mkm').rename_axis(['InitialNode', 'FinalNode', 'Circuit'], axis=0).reset_index().oT.write(f'{_path}/oT_Result_NetworkEnergyElecTransport_{CaseName}.csv', index=False, sep=',')

    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    OutputToFile = pd.Series(data=[max(Flow[p,sc,n,ni,nf,cc]/(mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]+pEpsilon),-Flow[p,sc,n,ni,nf,cc]/(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]+pEpsilon)) for p,sc,n,ni,nf,cc in mTEPES.psnla], index=mTEPES.psnla)
    OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
    OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkElecUtilization_{CaseName}.csv', index=False, sep=',')

    if mTEPES.pIndBinNetLosses() and mTEPES.psnll:
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[p,sc,n,ni,nf,cc]()*2*1e3              for p,sc,n,ni,nf,cc in mTEPES.psnll], index=mTEPES.psnll)
        OutputToFile.index.names = ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Period', 'Scenario', 'LoadLevel'], columns=['InitialNode', 'FinalNode', 'Circuit'], fill_value=0.0).rename_axis([None, None, None], axis=1)
        OutputToFile.reset_index().oT.write(f'{_path}/oT_Result_NetworkLosses_{CaseName}.csv', index=False, sep=',')

    if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndPTDF() == 0:
        OutputToFile = pd.Series(data=[OptModel.vTheta[p,sc,n,nd]()                                   for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
        OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkAngle_{CaseName}.csv', sep=',')

        # warn if the voltage-angle bound (pMaxTheta = pi/2) is (nearly) binding -- this indicates either an undersized Big-M on AC candidate lines,
        # an overconstrained network, or genuinely insufficient transmission. A binding pi/2 bound clips the DC-OPF solution non-physically and inflates costs.
        pMaxThetaTol = 1e-2
        pMaxThetaVal = math.pi / 2
        pBindingTheta = OutputToFile.abs().ge((1.0 - pMaxThetaTol) * pMaxThetaVal)
        if pBindingTheta.any():
            nBinding = int(pBindingTheta.sum())
            maxAbs   = float(OutputToFile.abs().max())
            print(f'WARNING: voltage angle bound pMaxTheta = pi/2 is (nearly) binding in {nBinding} (period, scenario, loadlevel, node) entries; max|theta| = {maxAbs:.6f} rad ({maxAbs/pMaxThetaVal*100:.2f} %% of pi/2).\nInspect oT_Result_NetworkAngle_{CaseName}.csv -- the bound may be clipping the DC-OPF solution.')

    # vENS feeds both the power (MW) and the energy (GWh) files, so evaluate it once. Dur already covers every load level, so it needs no completion here
    Ens = {Key: OptModel.vENS[Key]() for Key in mTEPES.psnnd}

    OutputToFile = pd.Series(data=[Ens[k] for k in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkPNS_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[Ens[p,sc,n,nd]*Dur[p,sc,n] for p,sc,n,nd in mTEPES.psnnd], index=mTEPES.psnnd)
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_NetworkENS_{CaseName}.csv', sep=',')

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

        # build each column in one pass instead of writing three scalar .loc cells per node. Nodes that have no zone keep the defaults the columns used to be
        # initialised with, which is what the loop left them at by never visiting them
        pNode2Zone = dict(mTEPES.ndzn)
        loc_df = pd.Series(data=[mTEPES.pNodeLat[i] for i in mTEPES.nd], index=mTEPES.nd).to_frame(name='Lat')
        loc_df['Lon'   ] = [mTEPES.pNodeLon[nd]                 if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Zone'  ] = [pNode2Zone[nd]                      if nd in pNode2Zone else ''  for nd in loc_df.index]
        loc_df['Demand'] = [mTEPES.pDemandElec[p,sc,n,nd]()*1e3 if nd in pNode2Zone else 0.0 for nd in loc_df.index]
        loc_df['Size'  ] = 15.0

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

        ncolors = 11
        colors = list(Color('lightgreen').range_to(Color('darkred'), ncolors))
        colors = ['rgb'+str(x.rgb) for x in colors]

        # accumulate per node pair in plain dictionaries and write the columns once at the end. Reading and writing line_df.loc[(ni,nf),'col'] meant about
        # twenty-five scalar lookups on a MultiIndex per line. The sequence of updates below is unchanged, so each derived value still comes from the same
        # circuit as before: the utilization and the colour from the accumulated flow, the voltage and the width from the last circuit of the pair.
        pMW     = OutputToFile['MW'].to_dict()
        pNTCFrw = line_df['NTCFrw' ].to_dict()
        pNTCBck = line_df['NTCBck' ].to_dict()
        pFlow   = defaultdict(float)
        pCirc   = defaultdict(int  )
        pUtil   = {}
        pColor  = {}
        pVolt   = {}
        pWidth  = {}
        pLon    = {}
        pLat    = {}

        for ni,nf,cc in mTEPES.la:
            if (p,ni,nf,cc) in mTEPES.pla:
                pFlow[ni,nf] += pMW[p,sc,n,ni,nf,cc]
                pUtil[ni,nf]  = max(pFlow[ni,nf]/pNTCFrw[ni,nf],-pFlow[ni,nf]/pNTCBck[ni,nf])*100.0
                pLon [ni,nf]  = (mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf]) * 0.5
                pLat [ni,nf]  = (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf]) * 0.5
                pCirc[ni,nf] += 1

                for i in range(len(colors)):
                    if 10*i <= pUtil[ni,nf] <= 10*(i+1):
                        pColor[ni,nf] = colors[i]

                # assigning black color to lines with utilization > 100%
                if pUtil[ni,nf] > 100:
                    pColor[ni,nf] = 'rgb(0,0,0)'

                pVolt[ni,nf] = mTEPES.pLineVoltage[ni,nf,cc]
                if   700 < pVolt[ni,nf] <= 900:
                    pWidth[ni,nf] = 4
                elif 500 < pVolt[ni,nf] <= 700:
                    pWidth[ni,nf] = 3
                elif 350 < pVolt[ni,nf] <= 500:
                    pWidth[ni,nf] = 2.5
                elif 290 < pVolt[ni,nf] <= 350:
                    pWidth[ni,nf] = 2
                elif 200 < pVolt[ni,nf] <= 290:
                    pWidth[ni,nf] = 1.5
                elif  50 < pVolt[ni,nf] <= 200:
                    pWidth[ni,nf] = 1
                else:
                    pWidth[ni,nf] = 0.5

        # the defaults below are the ones the columns used to be initialised with, so node pairs left untouched by the loop keep exactly the same values
        line_df['vFlowElec'  ] = [pFlow .get(la, 0.0) for la in line_df.index]
        line_df['utilization'] = [pUtil .get(la, 0.0) for la in line_df.index]
        line_df['color'      ] = [pColor.get(la, '' ) for la in line_df.index]
        line_df['voltage'    ] = [pVolt .get(la, 0.0) for la in line_df.index]
        line_df['width'      ] = [pWidth.get(la, 0.0) for la in line_df.index]
        line_df['lon'        ] = [pLon  .get(la, 0.0) for la in line_df.index]
        line_df['lat'        ] = [pLat  .get(la, 0.0) for la in line_df.index]
        line_df['ni'         ] = [ni if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['nf'         ] = [nf if (ni,nf) in pCirc else '' for ni,nf in line_df.index]
        line_df['cc'         ] = [pCirc .get(la, 0  ) for la in line_df.index]

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
    token = open(DIR+'/openTEPES.mapbox_token').read()

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

# ======================================================================================================================
# AC results: voltages, reactive flows, the relaxation gap and the reactive marginal
# ======================================================================================================================

QNS_REPORT_THRESHOLD = 1e-3
GAP_REPORT_THRESHOLD = 0.01


# The index is built explicitly from the keys rather than handed the index set directly: pandas infers a MultiIndex from some
# list-likes of tuples and a flat Index of tuples from others, and which one it picks should not decide whether a result file
# can be written.
def _write(sKeys, pValues, pName, pNames, pColumns, pPath, CaseName, pFile):
    if not sKeys:
        return
    pFrame = pd.Series(data=pValues, index=pd.MultiIndex.from_tuples(sKeys, names=pNames)).to_frame(name=pName)
    (pd.pivot_table(pFrame, values=pName, index=['Period', 'Scenario', 'LoadLevel'], columns=pColumns, fill_value=0.0)
       .rename_axis([None] * len(pColumns), axis=1)
       .reset_index().oT.write(f'{pPath}/oT_Result_{pFile}_{CaseName}.csv', index=False, sep=','))


def _pivot_branch(sKeys, pValues, pName, pPath, CaseName, pFile):
    _write(sKeys, pValues, pName, ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit'],
           ['InitialNode', 'FinalNode', 'Circuit'], pPath, CaseName, pFile)


def _pivot_node(sKeys, pValues, pName, pPath, CaseName, pFile):
    _write(sKeys, pValues, pName, ['Period', 'Scenario', 'LoadLevel', 'Node'], ['Node'], pPath, CaseName, pFile)


def ACRelaxationDiagnostic(DirName, CaseName, OptModel, mTEPES):
    """The conic/piecewise relaxation gap, per branch and summarised.

    Split out of ACNetworkOperationResults so it can sit in a cheap output category of its own: it is two small files, while the
    operation results are eight hourly wide tables. This is the diagnostic that says whether the currents, losses and voltages in
    those tables mean anything, so it should be available in the minimal output mode without dragging the rest along.
    """
    if not mTEPES.pIndACPowerFlow():
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    # Pyomo variable access is costly, so evaluate each index once and reuse.
    pW     = {k: OptModel.vW           [k]() for k in mTEPES.psnnd }
    pPfr   = {k: OptModel.vFlowElec    [k]() for k in mTEPES.psnlaa}
    pQfr   = {k: OptModel.vFlowReactFrw[k]() for k in mTEPES.psnlaa}
    pMode  = mTEPES.pIndACPowerFlow()
    pCurr  = {k: OptModel.vCurr[k]() for k in mTEPES.psnlaa} if pMode == 1 else {}

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # the relaxation diagnostic: everything ACNetworkOperationResults writes depends on this being small
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    pGap = {}
    for k in mTEPES.psnlaa:
        p, sc, n, ni, nf, cc = k
        pNorm = max(mTEPES.pLineSmax[ni,nf,cc] ** 2, 1e-12)
        if pMode == 1:
            pGap[k] = (pW[p,sc,n,ni] * mTEPES.pLineTapFactor[ni,nf,cc] ** 2 * pCurr[k] * pSBase ** 2 - pPfr[k] ** 2 - pQfr[k] ** 2) / pNorm
        elif pMode == 2:
            # the slack in vWre^2 + vWim^2 <= vW_i vW_j, the same quantity the cone relaxes, normalised the same way
            pGap[k] = (pW[p,sc,n,ni] * pW[p,sc,n,nf]
                       - OptModel.vWre[k]() ** 2 - OptModel.vWim[k]() ** 2) * pSBase ** 2 / pNorm
        else:
            pGap[k] = 0.0                                      # rectangular carries the exact products; there is no relaxation to measure

    sBranch = list(mTEPES.psnlaa)
    _pivot_branch(sBranch, [pGap[k] for k in sBranch], 'p.u. of Smax^2', _path, CaseName, 'ACRelaxationGap')

    # per-branch summary, which is what a user actually scans
    pWorst = {}
    for k in mTEPES.psnlaa:
        la = k[3:]
        # seeded from the first value, not from 0.0: a branch whose gap is negative at every load level has the cone VIOLATED beyond
        # tolerance, and seeding at zero would report it as perfectly tight in the summary users are told to read first
        pWorst[la] = pGap[k] if la not in pWorst else max(pWorst[la], pGap[k])
    # Guard the gap report only. AC can be switched on for a case whose links are all DC, and the voltages, angles, currents, reactive flows and shunt
    # injections written below do not depend on there being a cone to measure.
    if pWorst:
        pSummary = pd.Series(pWorst).sort_values(ascending=False)
        pSummary.index.names = ['InitialNode', 'FinalNode', 'Circuit']
        pSummary.to_frame(name='WorstGap [p.u. of Smax^2]').reset_index().oT.write(
            f'{_path}/oT_Result_ACRelaxationGapSummary_{CaseName}.csv', index=False, sep=',')

        pLoose = [la for la, g in pWorst.items() if g > GAP_REPORT_THRESHOLD]
        if pLoose:
            print(f'### WARNING: the AC relaxation is not tight on {len(pLoose)} of {len(pWorst)} branches '
                  f'(worst {max(pWorst.values()):.3f} of Smax^2). On those branches the reported current, loss and loading are')
            print(f'###          not supported by the flows. See oT_Result_ACRelaxationGapSummary_{CaseName}.csv and run the '
                  f'validation pass before using them.')
        else:
            print(f'AC relaxation tight on all {len(pWorst)} branches (worst {max(pWorst.values(), default=0.0):.2e} of Smax^2)')

    # --- do the reported flows satisfy the AC equations? --------------------------------------------------------------------------------------
    # The relaxation gap above says whether the CONE is tight. It does not say whether the operating point is physical: a tight cone with a wrong
    # branch equation is still wrong, which is exactly how the angle-relation sign error survived ten reviews. This recomputes each branch flow from
    # the bus VOLTAGES through the series relation and compares it with the flow the model reports. Deriving it from the flow variables instead
    # would compare the flow equations with themselves and pass whatever they said.
    #
    # Until now this check lived in prototypes/ and needed pandapower, which openTEPES does not ship, so a user could not run it at all.
    pFirst = next(iter(mTEPES.psn), None)
    if pFirst is not None and NM.angles_available(mTEPES, OptModel, *pFirst):
        pRows = []
        for p, sc, n in mTEPES.psn:
            wP, wQ = NM.branch_residuals(mTEPES, OptModel, p, sc, n)
            pRows.append((p, sc, n, wP, wQ))
        if pRows:
            pd.DataFrame(pRows, columns=['Period', 'Scenario', 'LoadLevel', 'WorstP [MW]', 'WorstQ [Mvar]']).oT.write(
                f'{_path}/oT_Result_ACPowerFlowResidual_{CaseName}.csv', index=False, sep=',')
            wP = max(r[3] for r in pRows)
            wQ = max(r[4] for r in pRows)
            # A relaxed solve is not expected to sit exactly on the series relation, so this is reported rather than judged. What it catches is a
            # residual of a size no tolerance explains, which is what a wrong branch equation looks like.
            print(f'AC power flow residual                   ... worst {wP:.5f} MW, {wQ:.5f} Mvar against the bus voltages')
    elif pFirst is not None:
        print('AC power flow residual                   ... not available: this formulation carries no nodal voltage angle. '
              'Set IndACCycle = 1 to tie it to a node potential.')

    print('Writing  AC relaxation diagnostic       ... ', round(time.time() - StartTime), 's')


def ACNetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    """Voltages, angles, reactive flows, currents, losses and shunt injections. A no-op when IndACPowerFlow is 0."""
    if not mTEPES.pIndACPowerFlow():
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    pW     = {k: OptModel.vW           [k]() for k in mTEPES.psnnd }
    # vCurr exists only under branch flow; bus injection reports the flows and voltages it does have
    pCurr  = {k: OptModel.vCurr[k]() for k in mTEPES.psnlaa} if mTEPES.pIndACPowerFlow() == 1 else None
    pPfr   = {k: OptModel.vFlowElec    [k]() for k in mTEPES.psnlaa}
    pQfr   = {k: OptModel.vFlowReactFrw[k]() for k in mTEPES.psnlaa}
    pQbck  = {k: OptModel.vFlowReactBck[k]() for k in mTEPES.psnlaa}
    pPbck  = {k: OptModel.vFlowElecBck [k]() for k in mTEPES.psnlaa}
    sBranch = list(mTEPES.psnlaa)

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    sNode = list(mTEPES.psnnd)
    _pivot_node(sNode, [math.sqrt(max(pW[k], 0.0))               for k in sNode], 'p.u.', _path, CaseName, 'NetworkVoltageMagnitude')
    _pivot_node(sNode, [OptModel.vTheta[k]() * 180.0 / math.pi   for k in sNode], 'deg',  _path, CaseName, 'NetworkVoltageAngle')

    # The reactive slack, reported as a signed net value: positive where the node is short of reactive power, negative where it cannot absorb what the
    # line charging delivers. Without this the slack does its job in the solve and leaves no trace anywhere — a case whose reactive demand cannot be
    # met simply solves with a larger reliability cost and nothing says which node or how much. That is the failure it exists to make visible.
    pQNS = [(OptModel.vQNSPos[k]() - OptModel.vQNSNeg[k]()) * 1e3 for k in sNode]
    _pivot_node(sNode, pQNS, 'Mvar', _path, CaseName, 'NetworkReactiveNotServed')
    # Tested per entry, not on the sum. Summing |slack| over every node and every load level accumulates solver residue — about 2e-06 Mvar across
    # ~79k entries on a converged 9n_AC run — so a total-based test fires on essentially every run and prints a shortfall of 0.000 Mvar.
    if pQNS:
        pWorstQ = max(range(len(sNode)), key=lambda i: abs(pQNS[i]))
        if abs(pQNS[pWorstQ]) > QNS_REPORT_THRESHOLD:
            pShort = sum(abs(q) for q in pQNS)
            print(f'### WARNING: the reactive balance used slack at some nodes, worst {pQNS[pWorstQ]:+.3f} Mvar at {sNode[pWorstQ][3]} '
                  f'({pShort:.3f} Mvar summed over all nodes and load levels). See oT_Result_NetworkReactiveNotServed_{CaseName}.csv — the reactive '
                  f'demand there is not being met by the system, it is being met by the slack.')

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # reactive flows, current and the exact loss
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    _pivot_branch(sBranch, [pQfr [k] * 1e3 for k in sBranch], 'Mvar', _path, CaseName, 'NetworkFlowReactiveFrw')
    _pivot_branch(sBranch, [pQbck[k] * 1e3 for k in sBranch], 'Mvar', _path, CaseName, 'NetworkFlowReactiveBck')

    # Losses come straight from the two ends and need no loss factor. They are the same quantity vLineLosses carries, reported here per branch in MW
    # rather than as the half-loss the DC reports use.
    _pivot_branch(sBranch, [(pPfr[k] + pPbck[k]) * 1e3        for k in sBranch], 'MW',   _path, CaseName, 'NetworkLossesAC')
    if pCurr is not None:                                  # branch flow carries |I|^2 directly; bus injection does not
        _pivot_branch(sBranch, [math.sqrt(max(pCurr[k], 0.0)) for k in sBranch], 'p.u.', _path, CaseName, 'NetworkCurrent')

    # Apparent-power loading against the branch rating. This is the number the DC network map cannot produce, because under DC the binding limit is on
    # active power alone.
    pLoading = {}
    for k in mTEPES.psnlaa:
        ni, nf, cc = k[3:]
        pRating = mTEPES.pLineSmax[ni,nf,cc]
        pLoading[k] = 100.0 * math.hypot(pPfr[k], pQfr[k]) / pRating if pRating > 0.0 else 0.0
    _pivot_branch(sBranch, [pLoading[k] for k in sBranch], '%', _path, CaseName, 'NetworkUtilizationAC')

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # shunt devices
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    if mTEPES.sh:
        sShunt = list(mTEPES.psnsh)
        _write(sShunt, [OptModel.vQShunt[k]() * 1e3 for k in sShunt], 'Mvar',
               ['Period', 'Scenario', 'LoadLevel', 'Shunt'], ['Shunt'], _path, CaseName, 'ShuntReactivePower')

        # the hourly in-service state, for the devices that have one. Q alone is ambiguous: a bank that is open and one that is closed on a bus
        # sitting at zero volts both report zero.
        if mTEPES.shw:
            sSwitch = list(mTEPES.psnshw)
            _write(sSwitch, [OptModel.vShuntSwitch[k]() for k in sSwitch], 'p.u.',
                   ['Period', 'Scenario', 'LoadLevel', 'Shunt'], ['Shunt'], _path, CaseName, 'ShuntCommitment')

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # HVDC converter stations
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # Both stations of a link, summed, in MW. Without this the loss is real in the solve and invisible afterwards: it leaves as extra generation with
    # nothing naming where it went, and a link that quietly eats a few per cent of what it carries looks like a link that carries everything.
    pLossNL = mTEPES.pConverterNoLoadLoss()   if mTEPES.pIndACConverter() else 0.0
    pLossMG = mTEPES.pConverterMarginalLoss() if mTEPES.pIndACConverter() else 0.0
    if mTEPES.lad and (pLossNL or pLossMG):
        sLink = list(mTEPES.psnlad)
        pConvLoss = []
        for k in sLink:
            la = k[3:]
            pAbsP = (OptModel.vDCFlowPos[k]() + OptModel.vDCFlowNeg[k]()) if hasattr(OptModel, 'vDCFlowPos') else abs(OptModel.vFlowElec[k]())
            # two stations, one at each end, each charged the same way
            pConvLoss.append(2.0 * (pLossNL * float(mTEPES.pLineNTCMax[la]) * OptModel.vLineCommit[k]() + pLossMG * pAbsP) * 1e3)
        _pivot_branch(sLink, pConvLoss, 'MW', _path, CaseName, 'NetworkConverterLosses')

    print('Writing  AC network operation results  ... ', round(time.time() - StartTime), 's')


def ACMarginalResults(DirName, CaseName, OptModel, mTEPES):
    """The reactive-power marginal, i.e. the dual of eBalanceReact. A no-op when IndACPowerFlow is 0 or no duals were collected."""
    if not mTEPES.pIndACPowerFlow():
        return
    if not (hasattr(mTEPES, 'pDuals') and mTEPES.pDuals):
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # eBalanceReact is skipped at a node with no reactive unit, no branch and no shunt, so ask only for duals that exist. Keying on the node rather
    # than on position matters: mTEPES.nd is an unordered Set, so iteration order is not stable between runs.
    # The test has to match eBalanceReact, which also builds on a non-zero reactive demand alone — the HVDC-fed node it was written for has no AC
    # branch, no shunt and no reactive unit, and omitting it here drops the marginal for exactly the node the constraint exists to cover.
    pNodeHasBalance = {}
    for nd in mTEPES.nd:
        pHas = (any(nd == la[0] or nd == la[1] for la in mTEPES.laa)
                or any(mTEPES.pReactiveDemand[p,sc,n,nd]() for p,sc,n in mTEPES.psn)
                # a converter model puts a reactive term on an HVDC terminal, so eBalanceReact builds there too
                or (mTEPES.pIndACConverter() and any(nd == la[0] or nd == la[1] for la in mTEPES.lad)))
        if not pHas:
            # n2gq, not n2g filtered by gq: a synchronous condenser is not in mTEPES.g and so not in n2g, which would skip a node whose only reactive
            # device is a condenser and leave its marginal unwritten.
            pHas = any(nd == n2 for n2, sh in mTEPES.n2sh) or any(nd == n2 for n2, gq in mTEPES.n2gq)
        pNodeHasBalance[nd] = pHas

    sKeys, pValues = [], []
    for p, sc, st, n in mTEPES.s2n:
        if (p, sc, n) not in mTEPES.psn:
            continue
        for nd in mTEPES.nd:
            if not pNodeHasBalance[nd]:
                continue
            pKey = f"eBalanceReact_{p}_{sc}_{st}('{n}', '{nd}')"
            if pKey not in mTEPES.pDuals:
                continue
            sKeys.append((p, sc, n, nd))
            pValues.append(mTEPES.pDuals[pKey] / mTEPES.pPeriodProb[p,sc]() / mTEPES.pLoadLevelDuration[p,sc,n]() * 1e3)

    if not sKeys:
        print('Writing  AC marginal results           ...  no reactive duals were collected')
        return

    _pivot_node(sKeys, pValues, 'EUR/Mvarh', _path, CaseName, 'MarginalReactive')

    print('Writing  AC marginal results           ... ', round(time.time() - StartTime), 's')
