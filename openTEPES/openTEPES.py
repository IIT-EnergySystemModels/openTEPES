"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - April 17, 2026
"""

# import dill as pickle
import datetime
import json
import math
import os
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, DataConfiguration, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentElecModelFormulation, InvestmentHydroModelFormulation, InvestmentH2ModelFormulation, InvestmentHeatModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults
# from openTEPES_SectorDecomposition import SectorDecomposition


# Output categories selectable via --results CLI flag.
# Keys map to the pIndXxxResults flags inside openTEPES_run.
OUTPUT_CATEGORIES = (
    "investment", "generation", "ess", "reservoir", "h2", "heat",
    "flexibility", "reliability", "network", "map", "summary",
    "cost", "marginal", "economic", "plots",
)
# Aliases expanded inside openTEPES_run.
OUTPUT_ALIASES = {
    "none": (),                                              # sentinel-only — for inner-loop / feasibility-check solves
    "min":  ("investment", "summary", "cost", "economic"),
    "full": OUTPUT_CATEGORIES,
}


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole,
                  *, output_spec=None, out_path=None):
    """Solve and write results.

    Parameters
    ----------
    DirName, CaseName, SolverName : str
        Standard openTEPES arguments.
    pIndOutputResults : 'Yes' / 'No' / 0 / 1
        Coarse-grained switch (kept for backward compatibility).
    pIndLogConsole : 'Yes' / 'No' / 0 / 1
        Verbose solver / formulation logging.
    output_spec : dict[str, bool] | None, optional
        Fine-grained output toggles. Keys must be OUTPUT_CATEGORIES; values
        truthy/falsy. Overrides the pIndOutputResults default for any key
        explicitly set. None (default) preserves historical behaviour.
    out_path : str | None, optional
        Directory to write all `oT_Result_*.csv` and `oT_Plot_*.html` to.
        Default `None` → write into `<DirName>/<CaseName>` (historical).
    """

    InitialTime = time.time()
    _RunStartedUtc = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    _path = os.path.join(DirName, CaseName)
    # Effective output directory — used by every function in OutputResults via
    # the _outdir() helper. None means "use case input dir" (historical).
    _OutPath = out_path if out_path else _path
    if out_path:
        os.makedirs(_OutPath, exist_ok=True)

    #%% replacing string values by numerical values
    idxDict        = dict()
    idxDict[0    ] = 0
    idxDict[0.0  ] = 0
    idxDict[0.0  ] = 0
    idxDict['No' ] = 0
    idxDict['NO' ] = 0
    idxDict['no' ] = 0
    idxDict['N'  ] = 0
    idxDict['n'  ] = 0
    idxDict['Yes'] = 1
    idxDict['YES'] = 1
    idxDict['yes'] = 1
    idxDict['Y'  ] = 1
    idxDict['y'  ] = 1

    #%% model declaration
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.17RC - April 17, 2026')
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.17RC - April 17, 2026', file=open(f'{_path}/openTEPES_version_{CaseName}.log','w'))

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # introduce cycle flow formulations in DC and AC load flow
    pIndCycleFlow = 0

    # sector decomposition to get proxy of the hydrogen sector: 0 to solve the complete problem, 1 to solve sector decomposition
    pIndSectorDecomposition = 0
    mTEPES.pIndSectorDecomposition = pIndSectorDecomposition

    # Reading sets and parameters
    InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # Define sets and parameters
    DataConfiguration(mTEPES)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # first/last stage
    FirstST = 0
    for st in mTEPES.st:
        if FirstST == 0:
            FirstST = 1
            mTEPES.First_st = st
        mTEPES.Last_st = st

    # objective function and investment constraints
    TotalObjectiveFunction             (mTEPES, mTEPES, pIndLogConsole)
    if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc) + len(mTEPES.hc):
        InvestmentElecModelFormulation (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydroTopology and mTEPES.rn:
        InvestmentHydroModelFormulation(mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydrogen      and mTEPES.pc:
        InvestmentH2ModelFormulation   (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHeat          and mTEPES.hc:
        InvestmentHeatModelFormulation (mTEPES, mTEPES, pIndLogConsole)

    # initialize parameter for dual variables
    mTEPES.pDuals = {}

    # initialize the set of load levels up to the current stage
    mTEPES.na = Set(initialize=[])

    # iterative model formulation for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:

        # control for not repeating the stages in case of several ones
        mTEPES.NoRepetition = 0

        # activate only load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt if mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                     (p,sc,st,nn) in mTEPES.s2n ])
        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                     (p,sc,st,nn) in mTEPES.s2n ])

        # load levels multiple of cycles for each ESS/generator
        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
        if mTEPES.pIndHydroTopology:
            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
            if sum(1 for h,rs in mTEPES.p2r):
                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
            else:
                mTEPES.np2c = []
            if sum(1 for rs,h in mTEPES.r2p):
                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
            else:
                mTEPES.npc = []
            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

        if mTEPES.st:

            # load levels up to the current stage for emission and RES energy constraints
            # if (p != mTEPES.p.first() or sc != mTEPES.sc.first()) and st == mTEPES.First_st:
            #     mTEPES.del_component(mTEPES.na)
            if st == mTEPES.First_st:
                mTEPES.del_component(mTEPES.na)
                mTEPES.na = Set(initialize=mTEPES.n)
            else:
                temp_na = mTEPES.na | mTEPES.n  # Create a temporary set
                mTEPES.del_component(mTEPES.na)  # Delete the existing set to avoid overwriting
                mTEPES.na = Set(initialize=temp_na)  # Assign the new set

            print(f'Period {p}, Scenario {sc}, Stage {st}')

            # operation model objective function and constraints by stage
            GenerationOperationModelFormulationObjFunct          (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationElecModelFormulationInvestment    (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHeat:
                GenerationOperationHeatModelFormulationInvestment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationDemand            (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationStorage           (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydroTopology:
                GenerationOperationModelFormulationReservoir     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydrogen:
                NetworkH2OperationModelFormulation               (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHeat:
                NetworkHeatOperationModelFormulation             (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationCommitment        (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationRampMinTime       (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkSwitchingModelFormulation                     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkOperationModelFormulation                     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            # introduce cycle flow formulations
            if pIndCycleFlow:
                if st == mTEPES.First_st:
                    NetworkCycles                                (        mTEPES, pIndLogConsole           )
                CycleConstraints                                 (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

            # No generator investments and no generator retirements, and no line investments
            if (    sum(1 for pp,eb in mTEPES.peb if pp <= p) == 0 or mTEPES.pIndBinGenInvest()     == 2
                and sum(1 for pp,gd in mTEPES.pgd if pp <= p) == 0 or mTEPES.pIndBinGenRetire()     == 2
                and sum(1 for pp,rc in mTEPES.prc if pp <= p) == 0 or mTEPES.pIndBinRsrInvest()     == 2
                and sum(1 for pp,lc in mTEPES.plc if pp <= p) == 0 or mTEPES.pIndBinNetElecInvest() == 2
                and sum(1 for pp,pc in mTEPES.ppc if pp <= p) == 0 or mTEPES.pIndBinNetH2Invest()   == 2
                and sum(1 for pp,hc in mTEPES.phc if pp <= p) == 0 or mTEPES.pIndBinNetHeatInvest() == 2):

                # No minimum RES requirements and no emission limit
                if (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) == 0 and (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)):

                    if (p,sc) == mTEPES.ps.last() and st == mTEPES.Last_st and mTEPES.NoRepetition == 0:
                        mTEPES.NoRepetition = 1

                    # Writing LP file
                    if pIndLogConsole:
                        StartTime         = time.time()
                        mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                        WritingLPFileTime = time.time() - StartTime
                        StartTime         = time.time()
                        print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                    # there are no expansion decisions, or they are ignored (it is an operation model), or there are no system emission nor minimum RES constraints
                    mTEPES.pScenProb[p,sc] = 1.0
                    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                    mTEPES.pScenProb[p,sc] = 0.0

                    # deactivate the constraints of the previous period and scenario
                    for c in mTEPES.component_objects(pyo.Constraint, active=True):
                        if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                            c.deactivate()

                # Minimum RES requirements or emission limit
                elif (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) > 0 or (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) < math.inf and sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) > 0)):

                    if st == mTEPES.Last_st and mTEPES.NoRepetition == 0:

                        if (p,sc) == mTEPES.ps.last():
                            mTEPES.NoRepetition = 1

                        mTEPES.del_component(mTEPES.st)
                        mTEPES.del_component(mTEPES.n )
                        mTEPES.del_component(mTEPES.n2)
                        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
                        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
                        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

                        # load levels multiple of cycles for each ESS/generator
                        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
                        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
                        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
                        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
                        if mTEPES.pIndHydroTopology:
                            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                            if sum(1 for h,rs in mTEPES.p2r):
                                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                            else:
                                mTEPES.np2c = []
                            if sum(1 for rs,h in mTEPES.r2p):
                                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                            else:
                                mTEPES.npc  = []
                            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

                        # Writing an LP file
                        if pIndLogConsole:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        mTEPES.pScenProb[p,sc] = 1.0
                        # there are system emission or RES requirement constraints
                        ProblemSolving           (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                        # if pIndSectorDecomposition and len(mTEPES.psnel):
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        #     SectorDecomposition(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st   )
                        # else:
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                        mTEPES.pScenProb[p,sc] = 0.0

                        # deactivate the constraints of the previous period and scenario
                        for c in mTEPES.component_objects(pyo.Constraint, active=True):
                            if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                                c.deactivate()

            # generator investments or generator retirements, or line investments
            elif (  sum(1 for pp,eb in mTEPES.peb if pp <= p) > 0 and mTEPES.pIndBinGenInvest()     < 2
                 or sum(1 for pp,gd in mTEPES.pgd if pp <= p) > 0 and mTEPES.pIndBinGenRetire()     < 2
                 or sum(1 for pp,rc in mTEPES.prc if pp <= p) > 0 and mTEPES.pIndBinRsrInvest()     < 2
                 or sum(1 for pp,lc in mTEPES.plc if pp <= p) > 0 and mTEPES.pIndBinNetElecInvest() < 2
                 or sum(1 for pp,pc in mTEPES.ppc if pp <= p) > 0 and mTEPES.pIndBinNetH2Invest()   < 2
                 or sum(1 for pp,hc in mTEPES.phc if pp <= p) > 0 and mTEPES.pIndBinNetHeatInvest() < 2):

                    if (p,sc) == mTEPES.ps.last() and st == mTEPES.Last_st and mTEPES.NoRepetition == 0:
                        mTEPES.NoRepetition = 1

                        mTEPES.del_component(mTEPES.st)
                        mTEPES.del_component(mTEPES.n )
                        mTEPES.del_component(mTEPES.n2)
                        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
                        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
                        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

                        # load levels multiple of cycles for each ESS/generator
                        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
                        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
                        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
                        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
                        if mTEPES.pIndHydroTopology:
                            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                            if sum(1 for h,rs in mTEPES.p2r):
                                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                            else:
                                mTEPES.np2c = []
                            if sum(1 for rs,h in mTEPES.r2p):
                                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                            else:
                                mTEPES.npc  = []
                            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

                        # Writing an LP file
                        if pIndLogConsole:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        # there are investment decisions (it is an expansion and operation model), or there are system emission constraints
                        ProblemSolving           (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        # if pIndSectorDecomposition and len(mTEPES.psnel):
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        #     SectorDecomposition(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st   )
                        # else:
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)

    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
    mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
    if mTEPES.pIndHydroTopology:
        mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
        if sum(1 for h,rs in mTEPES.p2r):
            mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
        else:
            mTEPES.np2c = []
        if sum(1 for rs,h in mTEPES.r2p):
            mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
        else:
            mTEPES.npc  = []
        mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

    # activate the constraints of all the periods and scenarios
    for c in mTEPES.component_objects(pyo.Constraint):
        c.activate()

    # assign probability 1 to all the periods and scenarios
    for p,sc in mTEPES.ps:
        mTEPES.pScenProb[p,sc] = 1.0

    # pickle the case study data
    # with open(dump_folder+f'/oT_Case_{CaseName}.pkl','wb') as f:
    #     pickle.dump(mTEPES, f, pickle.HIGHEST_PROTOCOL)

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 2

    # output results just for the system (0) or for every area (1). Areas correspond usually to countries
    pIndAreaOutput = 1

    # indicators to control the number of output results
    pIndDumpRawResults                  = 0
    if pIndOutputResults:
        # --result Yes  → full output suite
        _flags = {k: 1 for k in OUTPUT_CATEGORIES}
    else:
        # --result No   → minimal (investment + summary + cost + economic, no plots)
        _flags = {k: 0 for k in OUTPUT_CATEGORIES}
        for k in ("investment", "summary", "cost", "economic"):
            _flags[k] = 1

    # Override with fine-grained output_spec if given (--results CLI flag).
    if output_spec:
        for k, v in output_spec.items():
            if k in OUTPUT_CATEGORIES:
                _flags[k] = 1 if v else 0

    pIndInvestmentResults           = _flags["investment"]
    pIndGenerationOperationResults  = _flags["generation"]
    pIndESSOperationResults         = _flags["ess"]
    pIndReservoirOperationResults   = _flags["reservoir"]
    pIndNetworkH2OperationResults   = _flags["h2"]
    pIndNetworkHeatOperationResults = _flags["heat"]
    pIndFlexibilityResults          = _flags["flexibility"]
    pIndReliabilityResults          = _flags["reliability"]
    pIndNetworkOperationResults     = _flags["network"]
    pIndNetworkMapResults           = _flags["map"]
    pIndOperationSummaryResults     = _flags["summary"]
    pIndCostSummaryResults          = _flags["cost"]
    pIndMarginalResults             = _flags["marginal"]
    pIndEconomicResults             = _flags["economic"]
    pIndPlotOutput                  = _flags["plots"]

    # Tell OutputResults functions where to write (used by _outdir helper).
    # Setting on mTEPES avoids changing 14 function signatures.
    mTEPES.pOutputPath = _OutPath

    # output parameters, variables, and duals to CSV files
    _OutputStart = time.time()
    if pIndDumpRawResults:
        OutputResultsParVarCon(DirName, CaseName, mTEPES, mTEPES)

    if pIndInvestmentResults:
        InvestmentResults                 (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndGenerationOperationResults:
        GenerationOperationResults        (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
        if mTEPES.ch and mTEPES.pIndHeat:
            GenerationOperationHeatResults(DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndESSOperationResults         and mTEPES.es:
        ESSOperationResults               (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndReservoirOperationResults   and mTEPES.rs and mTEPES.pIndHydroTopology:
        ReservoirOperationResults         (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndNetworkH2OperationResults   and mTEPES.pa and mTEPES.pIndHydrogen:
        NetworkH2OperationResults         (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkHeatOperationResults and mTEPES.ha and mTEPES.pIndHeat:
        NetworkHeatOperationResults       (DirName, CaseName, mTEPES, mTEPES)
    if pIndFlexibilityResults:
        FlexibilityResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndReliabilityResults:
        ReliabilityResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkOperationResults:
        NetworkOperationResults           (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkMapResults:
        NetworkMapResults                 (DirName, CaseName, mTEPES, mTEPES)
    if pIndOperationSummaryResults:
        OperationSummaryResults           (DirName, CaseName, mTEPES, mTEPES)
    if pIndCostSummaryResults:
        CostSummaryResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndMarginalResults:
        MarginalResults                   (DirName, CaseName, mTEPES, mTEPES,                 pIndPlotOutput)
    if pIndEconomicResults:
        EconomicResults                   (DirName, CaseName, mTEPES, mTEPES, pIndAreaOutput, pIndPlotOutput)

    # Run-status sentinel JSON — small machine-readable record of this run.
    # Lets downstream tools detect a fresh run and read top-level adequacy /
    # cost numbers without parsing CSVs.
    _OutputSeconds = time.time() - _OutputStart
    _TotalSeconds  = time.time() - InitialTime
    _SolveSeconds  = max(_TotalSeconds - _OutputSeconds, 0.0)
    try:
        _TotalCost = float(mTEPES.eTotalSCost.expr() if hasattr(mTEPES, "eTotalSCost")
                           else getattr(mTEPES, "vTotalSCost", lambda: float("nan"))())
    except Exception:
        _TotalCost = float("nan")
    # ENS in MWh and HUE in hours — system-wide totals. Cheap to compute (one
    # pass over vENS); skipped silently if the variable / index set is missing.
    _EnsMwh = float("nan")
    _HueH   = float("nan")
    try:
        if hasattr(mTEPES, "vENS") and hasattr(mTEPES, "psnnd"):
            _ens_psn = {}  # (p, sc, n) -> sum_nd vENS[p,sc,n,nd]
            for p, sc, n, nd in mTEPES.psnnd:
                _ens_psn[(p, sc, n)] = _ens_psn.get((p, sc, n), 0.0) + float(mTEPES.vENS[p, sc, n, nd]())
            _ens_mwh = 0.0
            _hue_h   = 0.0
            for (p, sc, n), val in _ens_psn.items():
                _dur = float(mTEPES.pLoadLevelDuration[p, sc, n]())
                _ens_mwh += val * _dur
                if val > 0:
                    _hue_h += _dur
            _EnsMwh = round(_ens_mwh, 4)
            _HueH   = round(_hue_h,   4)
    except Exception:
        pass
    status = {
        "case":               CaseName,
        "dir":                DirName,
        "out":                _OutPath,
        "status":             "optimal",
        "total_cost_meur":    _TotalCost,
        "ens_mwh":            _EnsMwh,
        "hue_h":              _HueH,
        "solve_seconds":      round(_SolveSeconds,  2),
        "output_seconds":     round(_OutputSeconds, 2),
        "total_seconds":      round(_TotalSeconds,  2),
        "solver":             SolverName,
        "backend":            getattr(mTEPES, "pOutputBackend", "csv"),
        "opentepees_version": "4.18.17RC",
        "run_started_utc":    _RunStartedUtc,
        "run_finished_utc":   datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "outputs_enabled":    [k for k, v in _flags.items() if v],
    }
    with open(os.path.join(_OutPath, f"oT_Run_Status_{CaseName}.json"), "w") as _f:
        json.dump(status, _f, indent=2)

    return mTEPES
