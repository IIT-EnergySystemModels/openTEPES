"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Generation operation results, electricity and heat.

This module writes the hourly generation operation: unit commitment,
start-up and shut-down, operating and ramp reserves, output and surplus,
curtailment, energy, and emissions, per generator, per technology, and per
area, with optional Altair plots. The heat function reports the same for
combined heat-and-power and heat-only units.
"""

import time
import os
import pandas            as     pd
import altair            as     alt
from   collections       import defaultdict

try:
    from .openTEPES_OutputResultsCommon import _outdir, AreaPlots, PiePlots
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir, AreaPlots, PiePlots


# @profile
def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # generators to area (n2a)
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
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOperatingReserveUp_{CaseName}.csv', sep=',')
            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUp_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation == 1:
                OutputToFile = pd.Series(data=[OptModel.vReserveUpEnergy[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOperatingReserveUpEnergy_{CaseName}.csv', sep=',')
                if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                    OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUpEnergy_{CaseName}.csv', sep=',')

        if mTEPES.psnehc:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionOperatingReserveUpESS_{CaseName}.csv', sep=',')
            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUpESS_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation == 1:
                OutputToFile = pd.Series(data=[OptModel.vESSReserveUpEnergy[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psneh], index=mTEPES.psneh)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionOperatingReserveUpEnergyESS_{CaseName}.csv', sep=',')
                if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                    OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in n2n[nt] if (p,eh) in mTEPES.peh) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveUpEnergyESS_{CaseName}.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[:,:,:,:]):
        if mTEPES.nr:
            OutputToFile = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOperatingReserveDown_{CaseName}.csv', sep=',')
            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDown_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation == 1:
                OutputToFile = pd.Series(data=[OptModel.vReserveDownEnergy[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationOperatingReserveDownEnergy_{CaseName}.csv', sep=',')
                if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                    OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDownEnergy_{CaseName}.csv', sep=',')

        if mTEPES.psnehc:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionOperatingReserveDownESS_{CaseName}.csv', sep=',')
            if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in e2e[et] if (p,eh) in mTEPES.peh and mTEPES.pRatedMaxCharge[eh]) for p,sc,n,et in mTEPES.psnet], index=mTEPES.psnet)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDownESS_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation == 1:
                OutputToFile = pd.Series(data=[OptModel.vESSReserveDownEnergy[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psneh], index=mTEPES.psneh)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_ConsumptionOperatingReserveDownEnergyESS_{CaseName}.csv', sep=',')
                if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
                    OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,eh] for eh in n2n[nt] if (p,eh) in mTEPES.peh) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyOperatingReserveDownEnergyESS_{CaseName}.csv', sep=',')

    if pIndPlotOutput and mTEPES.nr and mTEPES.pIndRampReserves and sum(mTEPES.pRampReserveUp[:,:,:,:]):
        OutputToFile = pd.Series(data=[OptModel.vRampReserveUp[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile *= 1e3
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampReserveUp_{CaseName}.csv', sep=',')
        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyRampReserveUp_{CaseName}.csv', sep=',')

    if pIndPlotOutput and mTEPES.nr and mTEPES.pIndRampReserves and sum(mTEPES.pRampReserveDw[:,:,:,:]):
        OutputToFile = pd.Series(data=[OptModel.vRampReserveDw[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile *= 1e3
        if pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2:
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampReserveDown_{CaseName}.csv', sep=',')
        if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,nr] for nr in n2n[nt] if (p,nr) in mTEPES.pnr) for p,sc,n,nt in mTEPES.psnnt], index=mTEPES.psnnt)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyRampReserveDown_{CaseName}.csv', sep=',')

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
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() and mTEPES.pRampUp[nr]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]                           and OptModel.vCommitment[p,sc,n,nr]()                - OptModel.vStartUp[p,sc,n,nr]()  and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, f'eRampUp_{p}_{sc}_{st}')[n,nr].slack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampUp[nr]*(OptModel.vCommitment[p,sc,n,nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    if len(OutputToFile):
        OutputToFile.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampUpSurplus_{CaseName}.csv', sep=',')

    OutputResults = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() and mTEPES.pRampDw[nr]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first() and mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vShutDown[p,sc,n,nr]() and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[min((getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].slack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampDw[nr]*(mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vShutDown[p,sc,n,nr]()), OptModel.vOutput2ndBlock[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() and mTEPES.pRampDw[nr]*mTEPES.pDuration[p,sc,n]() < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.first() and OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vShutDown[p,sc,n,nr]() and (p,sc,n,nr) in mTEPES.psnnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr])))]
    OutputToFile  = pd.Series(data=[min((getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].slack())*mTEPES.pDuration[p,sc,n]()*mTEPES.pRampDw[nr]*(OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vShutDown[p,sc,n,nr]()), OptModel.vOutput2ndBlock[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    OutputResults.append(OutputToFile)
    OutputResults = pd.concat(OutputResults)
    OutputResults.index = pd.MultiIndex.from_tuples(OutputResults.index, names=['level_0', 'level_1', 'level_2', 'level_3', 'level_4'])
    if len(OutputResults):
        OutputResults.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_GenerationRampDownSurplus_{CaseName}.csv', sep=',')

    if mTEPES.re and mTEPES.rt:
        OutputToFile1 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]() - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() if re in mTEPES.gc else
                                        (OptModel.vTotalOutput[p,sc,n,re].ub                                    - OptModel.vTotalOutput[p,sc,n,re]())*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile2 = pd.Series(data=[(OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]()                                     )*mTEPES.pLoadLevelDuration[p,sc,n]() if re in mTEPES.gc else
                                        (OptModel.vTotalOutput[p,sc,n,re].ub                                                                        )*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,re in mTEPES.psnre], index=mTEPES.psnre)
        OutputToFile1 = OutputToFile1.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generator'], axis=0).rename_axis([None], axis=1)
        OutputToFile2 = OutputToFile2.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generator'], axis=0).rename_axis([None], axis=1)
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
            if pIndPlotOutput:
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
                if pIndAreaOutput:
                    for ar in mTEPES.ar:
                        if sum(1 for g in g2a[ar]):
                            sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg)]
                            if sPSNGT:
                                if sum(OutputToFile[:,:,:,:]):
                                    OutputResults = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                                    OutputResults.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyEmission_{CaseName}_{ar}.csv', sep=',')

            if sum(OutputToFile[:,:,:,:]):
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
                OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyEmission_{CaseName}.csv', sep=',')
                if pIndPlotOutput:
                    TechEmission = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'MtCO2'})
                    TechEmission = TechEmission[(TechEmission[['MtCO2']] != 0).all(axis=1)]
                    if len(TechEmission):
                        chart = alt.Chart(TechEmission.reset_index()).mark_bar().encode(x='Technology', y='MtCO2', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                        chart.save(f'{_path}/oT_Plot_TechnologyEmission_{CaseName}.html', embed_options={'renderer': 'svg'})

    if pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2:
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGeneration_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            TechnologyOutput = OutputToFile.loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyGeneration_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for g in g2a[ar])) > 1:
            if pIndAreaOutput:
                for ar in mTEPES.ar:
                    if sum(1 for g in g2a[ar]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg)]
                        if sPSNGT:
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}_{ar}.csv', sep=',')

                            if pIndPlotOutput:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing  generation operation results  ... ', round(WritingResultsTime), 's')


# @profile
def GenerationOperationHeatResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # generators to area (g2a)
    g2a = defaultdict(list)
    for ar,ch in mTEPES.ar*mTEPES.ch:
        if (ar,ch) in mTEPES.a2g:
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

        if pIndPlotOutput:
            TechnologyOutput = OutputToFile.loc[:,:,:,:]
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, TechnologyOutput, 'Technology', 'LoadLevel', 'MW', 'sum')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationHeat_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2t[gt] if (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if sum(1 for chp in g2a[ar])) > 1:
            if pIndAreaOutput:
                for ar in mTEPES.ar:
                    if sum(1 for chp in g2t[gt] if chp in g2a[ar]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for chp in g2t[gt] if chp in g2a[ar] and (p,chp) in mTEPES.pchp)]
                        if sPSNGT:
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2a[ar] if chp in g2t[gt] and (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{CaseName}_{ar}.csv', sep=',')

                            if pIndPlotOutput:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing  heat       operation results  ... ', round(WritingResultsTime), 's')
