"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - May 28, 2026

Energy-storage and reservoir operation results.

This module writes the hourly storage operation: energy outflows,
consumption (charging), generation-to-consumption ratio, inventory and its
utilization, and spillage, per unit and per technology, with optional Altair
plots. The reservoir function reports hydro reservoir volume, spillage, and
marginal water value.
"""

import time
import pandas            as     pd
from   collections       import defaultdict

from   .openTEPES_OutputResultsCommon import _outdir, AreaPlots, PiePlots, LinePlots


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    # %% outputting the ESS operation
    _path = _outdir(DirName, CaseName, mTEPES)
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

        OutputToFile = - pd.Series(data=[OptModel.vESSTotalCharge[p,sc,n,eh]() * mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionEnergy_{CaseName}.csv', sep=',')

        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyConsumptionEnergy_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            TechnologyCharge = OutputToFile.loc[:, :, :, :]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyCharge, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyConsumption_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if pIndPlotOutput:
            OutputToFile *= -1.0
            if OutputToFile.sum() < 0.0:
                for p,sc in mTEPES.ps:
                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                    chart.save(f'{_path}/oT_Plot_TechnologyConsumptionEnergy_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for eh in e2a[ar])) > 1:
            if pIndAreaOutput:
                for ar in mTEPES.ar:
                    if sum(1 for eh in e2a[ar] if eh in e2e[et]):
                        sPSNET = [(p,sc,n,et) for p,sc,n,et in mTEPES.psnet if sum(1 for eh in e2a[ar] if (p,sc,n,eh) in mTEPES.psnehc and eh in e2e[et])]
                        if sPSNET:
                            OutputToFile = pd.Series(data=[sum(-OptModel.vESSTotalCharge[p,sc,n,eh]() * mTEPES.pLoadLevelDuration[p,sc,n]() for eh in e2a[ar] if (p,sc,n,eh) in mTEPES.psnehc and eh in e2e[et]) for p,sc,n,et in sPSNET], index=pd.Index(sPSNET))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyConsumptionEnergy_{CaseName}_{ar}.csv', sep=',')

                            if pIndPlotOutput:
                                OutputToFile *= -1.0
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyConsumptionEnergy_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [p,sc,n,es]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOutflowsEnergy_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,es] for es in o2e[ot] if (p,es) in mTEPES.pes) for p,sc,n,ot in mTEPES.psnot], index=mTEPES.psnot)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOutflowsEnergy_{CaseName}.csv', sep=',')


    # tolerance to avoid division by 0
    pEpsilon = 1e-6

    sPSNES = [(p,sc,n,es) for p,sc,n,es in mTEPES.ps*mTEPES.nesc if (p,es) in mTEPES.pes and (mTEPES.pTotalMaxCharge[es] or mTEPES.pTotalEnergyInflows[es])]
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()                                          for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationInventory_{CaseName}.csv', sep=',')

        if mTEPES.ec:
           for p,sc,n,ec in mTEPES.psnec:
               mTEPES.pMaxStorage[p,sc,n,ec] = mTEPES.pMaxStorage[p,sc,n,ec]() * OptModel.vGenerationInvest[p,ec]()

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[p,sc,n,es]()/(mTEPES.pMaxStorage[p,sc,n,es]()+pEpsilon) for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False, aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationInventoryUtilization_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vESSSpillage[p,sc,n,es]()                                               for p,sc,n,es in sPSNES], index=pd.Index(sPSNES))
    if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh',               aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationSpillage_{CaseName}.csv', sep=',')

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        sPSNESOT = [(p,sc,n,es,ot) for p,sc,n,es,ot in sPSNES*mTEPES.ot if es in o2e[ot]]
        OutputToFile = pd.Series(data=[OutputToFile[p,sc,n,es] for p,sc,n,es,ot in sPSNESOT], index=pd.Index(sPSNESOT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologySpillage_{CaseName}.csv', sep=',')

    OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub*OptModel.vGenerationInvest[p,es]() - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[p,sc,n]() if es in mTEPES.ec else
                                    (OptModel.vTotalOutput[p,sc,n,es].ub                                    - OptModel.vTotalOutput[p,sc,n,es]())*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,es].ub*OptModel.vGenerationInvest[p,es]()                                     )*mTEPES.pLoadLevelDuration[p,sc,n]() if es in mTEPES.ec else
                                    (OptModel.vTotalOutput[p,sc,n,es].ub                                                                        )*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,es in mTEPES.psnes], index=mTEPES.psnes)
    OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generator'], axis=0).rename_axis([None], axis=1)
    OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generator'], axis=0).rename_axis([None], axis=1)

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


# @profile
def ReservoirOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndPlotOutput):
    # %% outputting the reservoir operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # technology to hydro units (o2h)
    o2h = defaultdict(list)
    for ht,h in mTEPES.ht*mTEPES.h:
        if (ht,h) in mTEPES.t2g:
            o2h[ht].append(h)

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
    sPSSTNES      = [(p,sc,st,n,rs) for p,sc,st,n,rs in mTEPES.s2n*mTEPES.rs if (p,sc,n,rs) in mTEPES.psnrs]
    OutputToFile = pd.Series(data=[abs(mTEPES.pDuals["".join([f"eHydroInventory_{p}_{sc}_{st}('{n}', '{rs}')"])])*1e3 for p,sc,st,n,rs in sPSSTNES], index=pd.Index(sPSSTNES))
    if len(OutputToFile):
        OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='WaterValue').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_MarginalWaterValue_{CaseName}.csv', sep=',')

    if pIndPlotOutput and len(OutputToFile):
        WaterValue = OutputToFile.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_3','level_4'], values='WaterValue').rename_axis(['level_0','level_1','level_2','level_3'], axis=0).loc[:,:,:,:]
        for p,sc in mTEPES.ps:
            chart = LinePlots(p, sc, WaterValue, 'Generator', 'LoadLevel', 'EUR/dam3', 'average')
            chart.save(f'{_path}/oT_Plot_MarginalWaterValue_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing   reservoir operation results  ... ', round(WritingResultsTime), 's')
