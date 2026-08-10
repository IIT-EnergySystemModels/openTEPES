"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 10, 2026

Generation operation results, electricity and heat.

This module writes the hourly generation operation: unit commitment, start-up and shut-down, operating and ramp reserves, output and surplus,
curtailment, energy, and emissions, per generator, per technology, and per area, with optional Altair plots. The heat function reports the same for
combined heat-and-power and heat-only units.
"""

import time
import os
import pandas            as     pd
import altair            as     alt
from   collections       import defaultdict

try:
    from          .openTEPES_OutputResultsCommon import _outdir, AreaPlots, PiePlots
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir, AreaPlots, PiePlots


# @profile
def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # output indicators: per unit (0 or 2) and per technology (1 or 2)
    pIndUnitOutput = pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2
    pIndTechOutput = pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2

    # generators to area (g2a)
    g2a = defaultdict(set)
    for ar,g in mTEPES.a2g:
        g2a[ar].add(g)

    # technology to generators (e2e) (n2n) (r2r) (g2t)
    e2e = defaultdict(set)
    n2n = defaultdict(set)
    r2r = defaultdict(set)
    g2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)
        if g in mTEPES.eh:
            e2e[gt].add(g)
        if g in mTEPES.nr:
            n2n[gt].add(g)
        if g in mTEPES.re:
            r2r[gt].add(g)

    # generator -> technology, so the per-technology aggregations below are one vectorised groupby instead of a scalar lookup per pair
    pGen2Tech = {g: gt for gt in mTEPES.gt for g in g2t[gt]}
    pNr2Tech  = {g: gt for gt in mTEPES.gt for g in n2n[gt]}
    pEh2Tech  = {g: gt for gt in mTEPES.gt for g in e2e[gt]}
    pRe2Tech  = {g: gt for gt in mTEPES.gt for g in r2r[gt]}

    # same map restricted to the ESS units that can actually charge: pRatedMaxCharge does not depend on (p,sc,n), so fold
    # it into the map once instead of testing it inside every sum of the consumption-reserve aggregations below
    pEh2TechCharge = {g: gt for g,gt in pEh2Tech.items() if mTEPES.pRatedMaxCharge[g]}

    # target index of the per-technology aggregations, built once instead of once per aggregation. MultiIndex.from_tuples
    # cannot infer the number of levels from an empty set, so leave it as None there: Series.reindex(None) is a no-op,
    # which is the right degenerate behavior because an empty psnnt means there is no technology row to produce.
    pIdxPSNNT = pd.MultiIndex.from_tuples(mTEPES.psnnt) if mTEPES.psnnt else None
    pIdxPSNET = pd.MultiIndex.from_tuples(mTEPES.psnet) if mTEPES.psnet else None

    # which (period, technology) pairs have any generator in each area: the predicate does not depend on the scenario or the load level,
    # so build it once here instead of rescanning mTEPES.psngt for every area below. Only the per-area outputs need it.
    pTechInArea = defaultdict(set)
    if pIndAreaOutput:
        for ar in mTEPES.ar:
            for gt in mTEPES.gt:
                for p in mTEPES.p:
                    if any(g in g2a[ar] and (p,g) in mTEPES.pg for g in g2t[gt]):
                        pTechInArea[ar].add((p,gt))

    if mTEPES.nr:
        if pIndUnitOutput:
            OutputToFile = pd.Series(data=[OptModel.vCommitment[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCommitment_{CaseName}.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vStartUp   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationStartUp_{CaseName}.csv', sep=',')
            OutputToFile = pd.Series(data=[OptModel.vShutDown  [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationShutDown_{CaseName}.csv', sep=',')

    if any(mTEPES.pOperReserveUp[idx] for idx in mTEPES.pOperReserveUp):
        if mTEPES.nr:
            OutputToFile = pd.Series(data=[OptModel.vReserveUp     [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndUnitOutput:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationOperatingReserveUp_{CaseName}.csv', sep=',')
            if pIndTechOutput:
                OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenOperatingReserveUp_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation() == 1:
                OutputToFile = pd.Series(data=[OptModel.vReserveUpEnergy[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndUnitOutput:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationOperatingReserveUpEnergy_{CaseName}.csv', sep=',')
                if pIndTechOutput:
                    OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenOperatingReserveUpEnergy_{CaseName}.csv', sep=',')

        if mTEPES.psnehc:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndUnitOutput:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionOperatingReserveUp_{CaseName}.csv', sep=',')
            if pIndTechOutput:
                OutputToFile = OutputToFile[[(p,eh) in mTEPES.peh and eh in pEh2TechCharge for p,sc,n,eh in OutputToFile.index]].rename(index=pEh2TechCharge, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNET, fill_value=0.0)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyConOperatingReserveUp_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation() == 1:
                OutputToFile = pd.Series(data=[OptModel.vESSReserveUpEnergy[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndUnitOutput:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionOperatingReserveUpEnergy_{CaseName}.csv', sep=',')
                if pIndTechOutput:
                    OutputToFile = OutputToFile[[(p,eh) in mTEPES.peh and eh in pEh2TechCharge for p,sc,n,eh in OutputToFile.index]].rename(index=pEh2TechCharge, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNET, fill_value=0.0)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyConOperatingReserveUpEnergy_{CaseName}.csv', sep=',')

    if any(mTEPES.pOperReserveDw[idx] for idx in mTEPES.pOperReserveDw):
        if mTEPES.nr:
            OutputToFile = pd.Series(data=[OptModel.vReserveDown   [p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndUnitOutput:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationOperatingReserveDown_{CaseName}.csv', sep=',')
            if pIndTechOutput:
                OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenOperatingReserveDown_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation() == 1:
                OutputToFile = pd.Series(data=[OptModel.vReserveDownEnergy[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndUnitOutput:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationOperatingReserveDownEnergy_{CaseName}.csv', sep=',')
                if pIndTechOutput:
                    OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenOperatingReserveDownEnergy_{CaseName}.csv', sep=',')

        if mTEPES.psnehc:
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile *= 1e3
            if pIndUnitOutput:
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionOperatingReserveDown_{CaseName}.csv', sep=',')
            if pIndTechOutput:
                OutputToFile = OutputToFile[[(p,eh) in mTEPES.peh and eh in pEh2TechCharge for p,sc,n,eh in OutputToFile.index]].rename(index=pEh2TechCharge, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNET, fill_value=0.0)
                OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyConOperatingReserveDown_{CaseName}.csv', sep=',')

            if mTEPES.pIndReserveActivation() == 1:
                OutputToFile = pd.Series(data=[OptModel.vESSReserveDownEnergy[p,sc,n,eh]() for p,sc,n,eh in mTEPES.psnehc], index=mTEPES.psnehc)
                OutputToFile = OutputToFile.fillna(0.0)
                OutputToFile *= 1e3
                if pIndUnitOutput:
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_ConsumptionOperatingReserveDownEnergy_{CaseName}.csv', sep=',')
                if pIndTechOutput:
                    OutputToFile = OutputToFile[[(p,eh) in mTEPES.peh and eh in pEh2TechCharge for p,sc,n,eh in OutputToFile.index]].rename(index=pEh2TechCharge, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNET, fill_value=0.0)
                    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyConOperatingReserveDownEnergy_{CaseName}.csv', sep=',')

    pHasRampReserveUp = hasattr(mTEPES, 'pRampReserveUp') and any(mTEPES.pRampReserveUp[idx] for idx in mTEPES.pRampReserveUp)
    pHasRampReserveDw = hasattr(mTEPES, 'pRampReserveDw') and any(mTEPES.pRampReserveDw[idx] for idx in mTEPES.pRampReserveDw)

    if mTEPES.nr and mTEPES.pIndRampReserves() and pHasRampReserveUp:
        OutputToFile = pd.Series(data=[OptModel.vRampReserveUp[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile *= 1e3
        if pIndUnitOutput:
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationRampReserveUp_{CaseName}.csv', sep=',')
        if pIndTechOutput:
            OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyRampReserveUp_{CaseName}.csv', sep=',')

    if mTEPES.nr and mTEPES.pIndRampReserves() and pHasRampReserveDw:
        OutputToFile = pd.Series(data=[OptModel.vRampReserveDw[p,sc,n,nr]() for p,sc,n,nr in mTEPES.psnnr], index=mTEPES.psnnr)
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile *= 1e3
        if pIndUnitOutput:
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationRampReserveDown_{CaseName}.csv', sep=',')
        if pIndTechOutput:
            OutputToFile = OutputToFile[[(p,nr) in mTEPES.pnr and nr in pNr2Tech for p,sc,n,nr in OutputToFile.index]].rename(index=pNr2Tech, level=3).groupby(level=[0,1,2,3]).sum().reindex(pIdxPSNNT, fill_value=0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyRampReserveDown_{CaseName}.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g]() for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_Generation_{CaseName}.csv', sep=',')

    # tolerance to treat a number as 0
    pEpsilon = 1e-6

    sPSNG, pSurplus = [], []
    for p,sc,n,g in mTEPES.psng:
        pUpperBound = OptModel.vTotalOutput[p,sc,n,g].ub
        pOutput     = OptModel.vTotalOutput[p,sc,n,g]()
        if pUpperBound - pOutput > pEpsilon:
            sPSNG.append((p,sc,n,g))
            pSurplus.append((pUpperBound*OptModel.vGenerationInvest[p,g]() - pOutput) if g in mTEPES.gc else (pUpperBound - pOutput))
    OutputToFile = pd.Series(data=pSurplus, index=pd.Index(sPSNG))

    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationSurplus_{CaseName}.csv', sep=',')

    # The three ramp-surplus filters below share this prefix. They differ only in the ramp parameter (pRampUp / pRampDw), in whether they take the
    # first load level or the rest, and in the commitment term compared against the start-up / shut-down decision; keeping the common part here makes
    # that difference visible. The storage clause is the original `nr not in es or (nr in es and X)`, which is just `nr not in es or X`.
    def _num(v):
        return v() if callable(v) else v

    def RampSurplusCandidate(p,sc,n,nr,pRamp):
        pRampValue     = _num(pRamp[nr])
        pDurationValue = _num(mTEPES.pDuration[p,sc,n])
        pBlockValue    = _num(mTEPES.pMaxPower2ndBlock[p,sc,n,nr])
        return (mTEPES.pIndBinGenRamps() and pRampValue and pRampValue*pDurationValue < pBlockValue
                and (p,sc,n,nr) in mTEPES.psnnr
                and (nr not in mTEPES.es or _num(mTEPES.pTotalMaxCharge[nr]) or _num(mTEPES.pTotalEnergyInflows[nr])))

    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if                            RampSurplusCandidate(p,sc,n,nr,mTEPES.pRampUp) and abs(OptModel.vCommitment[p,sc,n,nr]()                - OptModel.vStartUp[p,sc,n,nr]()) > pEpsilon]
    OutputToFile  = pd.Series(data=[(getattr(OptModel, f'eRampUp_{p}_{sc}_{st}')[n,nr].slack())*_num(mTEPES.pDuration[p,sc,n])*_num(mTEPES.pRampUp[nr])*(OptModel.vCommitment[p,sc,n,nr]() - OptModel.vStartUp[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    if len(OutputToFile):
        OutputToFile.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationRampUpSurplus_{CaseName}.csv', sep=',')

    # the ramp-down surplus is built in two parts, the first load level and the rest, and written as one frame
    RampDwSurplusParts = []
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if n == mTEPES.n.first() and RampSurplusCandidate(p,sc,n,nr,mTEPES.pRampDw) and abs(mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vShutDown[p,sc,n,nr]()) > pEpsilon]
    OutputToFile  = pd.Series(data=[min((getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].slack())*_num(mTEPES.pDuration[p,sc,n])*_num(mTEPES.pRampDw[nr])*(mTEPES.pInitialUC[p,sc,n,nr]()                   - OptModel.vShutDown[p,sc,n,nr]()), OptModel.vOutput2ndBlock[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    RampDwSurplusParts.append(OutputToFile)
    sPSSTNNR      = [(p,sc,st,n,nr) for p,sc,st,n,nr in mTEPES.s2n*mTEPES.nr if n != mTEPES.n.first() and RampSurplusCandidate(p,sc,n,nr,mTEPES.pRampDw) and abs(OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vShutDown[p,sc,n,nr]()) > pEpsilon]
    OutputToFile  = pd.Series(data=[min((getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')[n,nr].slack())*_num(mTEPES.pDuration[p,sc,n])*_num(mTEPES.pRampDw[nr])*(OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr]() - OptModel.vShutDown[p,sc,n,nr]()), OptModel.vOutput2ndBlock[p,sc,n,nr]()) for p,sc,st,n,nr in sPSSTNNR], index=pd.Index(sPSSTNNR), dtype='float64')
    OutputToFile *= 1e3
    RampDwSurplusParts.append(OutputToFile)
    RampDwSurplus = pd.concat(RampDwSurplusParts)
    if len(RampDwSurplus):
        RampDwSurplus.index = pd.MultiIndex.from_tuples(RampDwSurplus.index, names=['level_0', 'level_1', 'level_2', 'level_3', 'level_4'])
        RampDwSurplus.to_frame(name='MW/h').reset_index().pivot_table(index=['level_0','level_1','level_3'], columns='level_4', values='MW/h', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationRampDownSurplus_{CaseName}.csv', sep=',')

    if mTEPES.re and mTEPES.rt:
        # curtailment is reported four times over the same set: as power, as energy, and as the relative ratio of both. Evaluate every
        # Pyomo value once per tuple here and derive the rest by vectorised multiplication.
        pDuration, pCurtail, pMaximum = [], [], []
        for p,sc,n,re in mTEPES.psnre:
            pUpperBound = OptModel.vTotalOutput[p,sc,n,re].ub*OptModel.vGenerationInvest[p,re]() if re in mTEPES.gc else OptModel.vTotalOutput[p,sc,n,re].ub
            pDuration.append(mTEPES.pLoadLevelDuration[p,sc,n]())
            pMaximum.append(pUpperBound)
            pCurtail.append(pUpperBound - OptModel.vTotalOutput[p,sc,n,re]())
        CurtailDuration = pd.Series(data=pDuration, index=mTEPES.psnre)
        CurtailPower    = pd.Series(data=pCurtail , index=mTEPES.psnre)
        MaxPower        = pd.Series(data=pMaximum , index=mTEPES.psnre)
        OutputToFile1   = CurtailPower*CurtailDuration
        OutputToFile2   = MaxPower    *CurtailDuration
        # both curtailment frames are summed over the load levels the same way; only the input series differs
        def EnergyPerGenerator(SeriesPSNRE):
            return SeriesPSNRE.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_3'], values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'Generator'], axis=0).rename_axis([None], axis=1)

        OutputToFile1 = EnergyPerGenerator(OutputToFile1)
        OutputToFile2 = EnergyPerGenerator(OutputToFile2)
        if pIndUnitOutput:
            OutputToFile = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.rename(columns = {'GWh':'%'}, inplace = True)
            OutputToFile.oT.write(f'{_path}/oT_Result_GenerationCurtailmentEnergyRelative_{CaseName}.csv', sep=',')

        if pIndTechOutput:
            OutputToFile1 = pd.Series(data=[sum(OutputToFile1['GWh'][p,sc,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,rt in mTEPES.psrt], index=mTEPES.psrt)
            OutputToFile2 = pd.Series(data=[sum(OutputToFile2['GWh'][p,sc,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,rt in mTEPES.psrt], index=mTEPES.psrt)
            OutputToFile  = OutputToFile1.div(OutputToFile2)*1e2
            OutputToFile  = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='%').rename_axis(['Period', 'Scenario', 'Technology'], axis=0).oT.write(f'{_path}/oT_Result_TechnologyCurtailmentEnergyRelative_{CaseName}.csv', index=True, sep=',')

        OutputToFile = CurtailPower*1e3
        if pIndUnitOutput:
            OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' , aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCurtailment_{CaseName}.csv', sep=',')

        OutputToFile = CurtailPower*CurtailDuration
        if pIndUnitOutput:
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationCurtailmentEnergy_{CaseName}.csv', sep=',')

        if pIndTechOutput:
            OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,re] for re in r2r[rt] if (p,re) in mTEPES.pre) for p,sc,n,rt in mTEPES.psnrt], index=mTEPES.psnrt)
            # the plot below reuses this pivot instead of rebuilding it
            TechCurtPivot = OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
            TechCurtPivot.oT.write(f'{_path}/oT_Result_TechnologyCurtailmentEnergy_{CaseName}.csv', sep=',')
            if pIndPlotOutput:
                TechCurt = TechCurtPivot.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'GWh'})
                TechCurt = TechCurt[(TechCurt[['GWh']] != 0).all(axis=1)]
                chart = alt.Chart(TechCurt.reset_index()).mark_bar().encode(x='Technology', y='GWh', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                chart.save(f'{_path}/oT_Plot_TechnologyCurtailmentEnergy_{CaseName}.html', embed_options={'renderer':'svg'})

    if pIndUnitOutput:
        OutputToFile = pd.Series(data=[OptModel.vTotalOutput[p,sc,n,g ]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(      index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationEnergy_{CaseName}.csv', sep=',')

    if mTEPES.nr or mTEPES.bo:
        OutputToFile     = pd.Series(data=[OptModel.vTotalOutput    [p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3 if g not in mTEPES.bo else
                                           OptModel.vTotalOutputHeat[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]()*mTEPES.pEmissionRate[g]/1e3 for p,sc,n,g in mTEPES.psng], index=mTEPES.psng)
        if pIndUnitOutput:
            OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationEmission_{CaseName}.csv', sep=',')

        # a sum of exactly zero would hide a case whose emissions cancel out: ask whether any value is non-zero instead
        pHasEmissions = bool((OutputToFile != 0.0).any())

        if pIndTechOutput:
            if sum(1 for ar in mTEPES.ar if len(g2a[ar])) > 1 and pIndAreaOutput and pHasEmissions:
                for ar in mTEPES.ar:
                    if len(g2a[ar]):
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if (p,gt) in pTechInArea[ar]]
                        if sPSNGT:
                            TechEmissionArea = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            TechEmissionArea.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyEmission_{CaseName}_{ar}.csv', sep=',')

            if pHasEmissions:
                OutputToFile = pd.Series(data=[sum(OutputToFile[p,sc,n,g] for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
                # the plot below reuses this pivot instead of rebuilding it
                TechEmissionPivot = OutputToFile.to_frame(name='MtCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MtCO2', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
                TechEmissionPivot.oT.write(f'{_path}/oT_Result_TechnologyEmission_{CaseName}.csv', sep=',')
                if pIndPlotOutput:
                    TechEmission = TechEmissionPivot.stack().rename_axis(['Period', 'Scenario', 'LoadLevel', 'Technology']).reset_index().groupby(['Period', 'Scenario', 'Technology']).sum(numeric_only=True).rename(columns={0: 'MtCO2'})
                    TechEmission = TechEmission[(TechEmission[['MtCO2']] != 0).all(axis=1)]
                    if len(TechEmission):
                        chart = alt.Chart(TechEmission.reset_index()).mark_bar().encode(x='Technology', y='MtCO2', color='Scenario:N', column='Period:N').properties(width=600, height=400)
                        chart.save(f'{_path}/oT_Plot_TechnologyEmission_{CaseName}.html', embed_options={'renderer': 'svg'})

    if pIndTechOutput:
        # the per-technology output is written twice, as power and as energy. The load-level duration does not depend on the generator,
        # so sum(vTotalOutput*duration) == sum(vTotalOutput)*duration: build the GW series once and derive both from it.
        TechOutput   = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]() for g in g2t[gt] if (p,g) in mTEPES.pg) for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        TechDuration = pd.Series(data=[mTEPES.pLoadLevelDuration[p,sc,n]()                                           for p,sc,n,gt in mTEPES.psngt], index=mTEPES.psngt)
        OutputToFile = TechOutput*1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGeneration_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, OutputToFile, 'Technology', 'LoadLevel', 'MW')
                chart.save(f'{_path}/oT_Plot_TechnologyGeneration_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        OutputToFile = TechOutput*TechDuration
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if len(g2a[ar])) > 1 and pIndAreaOutput:
            for ar in mTEPES.ar:
                if len(g2a[ar]):
                    sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if (p,gt) in pTechInArea[ar]]
                    if sPSNGT:
                        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[p,sc,n,g]()*mTEPES.pLoadLevelDuration[p,sc,n]() for g in g2t[gt] if g in g2a[ar] and (p,g) in mTEPES.pg) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationEnergy_{CaseName}_{ar}.csv', sep=',')

                        if pIndPlotOutput:
                            for p,sc in mTEPES.ps:
                                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergy_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    print('Writing  generation operation results  ... ', round(WritingResultsTime), 's')


# @profile
def GenerationOperationHeatResults(DirName, CaseName, OptModel, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput):
    #%% outputting the generation operation
    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # output indicators: per unit (0 or 2) and per technology (1 or 2)
    pIndUnitOutput = pIndTechnologyOutput == 0 or pIndTechnologyOutput == 2
    pIndTechOutput = pIndTechnologyOutput == 1 or pIndTechnologyOutput == 2

    # generators to area (g2a)
    g2a = defaultdict(set)
    for ar,g in mTEPES.a2g:
        if g in mTEPES.ch:
            g2a[ar].add(g)

    # technology to generators (g2t)
    g2t = defaultdict(set)
    for gt,g in mTEPES.t2g:
        g2t[gt].add(g)

    # which (period, technology) pairs have any heat unit in each area: the predicate does not depend on the scenario or the load level,
    # so build it once here instead of rescanning mTEPES.psngt for every area below. Only the per-area outputs need it.
    pTechInArea = defaultdict(set)
    if pIndAreaOutput:
        for ar in mTEPES.ar:
            for gt in mTEPES.gt:
                for p in mTEPES.p:
                    if any(chp in g2a[ar] and (p,chp) in mTEPES.pchp for chp in g2t[gt]):
                        pTechInArea[ar].add((p,gt))

    # for p,sc,n,ch in mTEPES.psnch:
    #     if ch not in mTEPES.bo:
    #         OptModel.vTotalOutputHeat[p,sc,n,ch] = OptModel.vTotalOutput[p,sc,n,ch] / mTEPES.pPower2HeatRatio[ch]
    #
    # for p,sc,n,hp in mTEPES.psnhp:
    #     OptModel.vTotalOutputHeat[p,sc,n,hp] = OptModel.vESSTotalCharge[p,sc,n,hp] / mTEPES.pProductionFunctionHeat[hp]

    OutputToFile = pd.Series(data=[OptModel.vTotalOutputHeat[p,sc,n,chp]() for p,sc,n,chp in mTEPES.psnchp], index=mTEPES.psnchp)
    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationHeat_{CaseName}.csv', sep=',')

    # tolerance to treat a number as 0
    pEpsilon = 1e-6

    sPSNG, pSurplus = [], []
    for p,sc,n,ch in mTEPES.psnch:
        pUpperBound = OptModel.vTotalOutputHeat[p,sc,n,ch].ub
        pOutput     = OptModel.vTotalOutputHeat[p,sc,n,ch]()
        if pUpperBound - pOutput > pEpsilon:
            sPSNG.append((p,sc,n,ch))
            pSurplus.append((pUpperBound*OptModel.vGenerationInvest[p,ch]() - pOutput) if ch in mTEPES.gc else (pUpperBound - pOutput))
    OutputToFile = pd.Series(data=pSurplus, index=pd.Index(sPSNG))

    OutputToFile *= 1e3
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationSurplusHeat_{CaseName}.csv', sep=',')

    if pIndUnitOutput:
        OutputToFile = pd.Series(data=[OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for p,sc,n,chp in mTEPES.psnchp], index=mTEPES.psnchp)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(      index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_GenerationEnergyHeat_{CaseName}.csv', sep=',')

    if pIndTechOutput:
        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if sum(1 for chp in g2t[gt] if (p,chp) in mTEPES.pchp)]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]() for chp in g2t[gt] if (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationHeat_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = AreaPlots(p, sc, OutputToFile, 'Technology', 'LoadLevel', 'MW')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationHeat_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2t[gt] if (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{CaseName}.csv', sep=',')

        if pIndPlotOutput:
            for p,sc in mTEPES.ps:
                chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{CaseName}_{p}_{sc}.html', embed_options={'renderer': 'svg'})

        if sum(1 for ar in mTEPES.ar if len(g2a[ar])) > 1:
            if pIndAreaOutput:
                for ar in mTEPES.ar:
                    if len(g2a[ar]) > 1:
                        sPSNGT = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psngt if (p,gt) in pTechInArea[ar]]
                        if sPSNGT:
                            OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutputHeat[p,sc,n,chp]()*mTEPES.pLoadLevelDuration[p,sc,n]() for chp in g2a[ar] if chp in g2t[gt] and (p,chp) in mTEPES.pchp) for p,sc,n,gt in sPSNGT], index=pd.Index(sPSNGT))
                            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', aggfunc='sum').rename_axis(['Period', 'Scenario', 'LoadLevel'], axis=0).rename_axis([None], axis=1).oT.write(f'{_path}/oT_Result_TechnologyGenerationEnergyHeat_{CaseName}_{ar}.csv', sep=',')

                            if pIndPlotOutput:
                                for p,sc in mTEPES.ps:
                                    chart = PiePlots(p, sc, OutputToFile, 'Technology', '%')
                                    chart.save(f'{_path}/oT_Plot_TechnologyGenerationEnergyHeat_{CaseName}_{p}_{sc}_{ar}.html', embed_options={'renderer': 'svg'})

    WritingResultsTime = time.time() - StartTime
    print('Writing  heat       operation results  ... ', round(WritingResultsTime), 's')
