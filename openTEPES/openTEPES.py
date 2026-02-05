"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - February 05, 2026
"""

# import dill as pickle
import math
import os
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, DataConfiguration, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole):

    InitialTime = time.time()
    _path = os.path.join(DirName, CaseName)

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
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.13 - February 05, 2026')
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.13 - February 05, 2026', file=open(f'{_path}/openTEPES_version_{CaseName}.log','w'))

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # introduce cycle flow formulations in DC and AC load flow
    pIndCycleFlow = 0

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
    TotalObjectiveFunction    (mTEPES, mTEPES, pIndLogConsole)
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)

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
        if mTEPES.pIndHydroTopology == 1:
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
            GenerationOperationModelFormulationObjFunct     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationInvestment   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationDemand       (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationStorage      (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydroTopology == 1:
                GenerationOperationModelFormulationReservoir(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydrogen == 1:
                NetworkH2OperationModelFormulation          (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHeat == 1:
                NetworkHeatOperationModelFormulation        (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationCommitment   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationRampMinTime  (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkSwitchingModelFormulation                (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkOperationModelFormulation                (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            # introduce cycle flow formulations
            if pIndCycleFlow == 1:
                if st == mTEPES.First_st:
                    NetworkCycles                           (        mTEPES, pIndLogConsole           )
                CycleConstraints                            (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

            # No generator investments and no generator retirements, and no line investments
            if (    sum(1 for pp,eb in mTEPES.peb if pp <= p) == 0 or mTEPES.pIndBinGenInvest()     == 2
                and sum(1 for pp,gd in mTEPES.pgd if pp <= p) == 0 or mTEPES.pIndBinGenRetire()     == 2
                and sum(1 for pp,rc in mTEPES.prc if pp <= p) == 0 or mTEPES.pIndBinRsrInvest()     == 2
                and sum(1 for pp,lc in mTEPES.plc if pp <= p) == 0 or mTEPES.pIndBinNetElecInvest() == 2
                and sum(1 for pp,pc in mTEPES.ppc if pp <= p) == 0 or mTEPES.pIndBinNetH2Invest()   == 2
                and sum(1 for pp,hc in mTEPES.phc if pp <= p) == 0 or mTEPES.pIndBinNetHeatInvest() == 2):

                # No minimum RES requirements and no emission limit
                if  (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) == 0
                and (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)):

                    if (p,sc) == mTEPES.ps.last() and st == mTEPES.Last_st and mTEPES.NoRepetition == 0:
                        mTEPES.NoRepetition = 1

                    # Writing LP file
                    if pIndLogConsole == 1:
                        StartTime         = time.time()
                        mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                        WritingLPFileTime = time.time() - StartTime
                        StartTime         = time.time()
                        print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                    # there are no expansion decisions, or they are ignored (it is an operation model), or there are no system emission nor minimum RES constraints
                    mTEPES.pScenProb[p,sc] = 1.0
                    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)
                    mTEPES.pScenProb[p,sc] = 0.0

                    # deactivate the constraints of the previous period and scenario
                    for c in mTEPES.component_objects(pyo.Constraint, active=True):
                        if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                            c.deactivate()

                # Minimum RES requirements or emission limit
                elif  (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) > 0
                   or (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) < math.inf and sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) > 0)):

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
                        if mTEPES.pIndHydroTopology == 1:
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
                        if pIndLogConsole == 1:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        # there are investment decisions (it is an expansion and operation model), or there are system emission constraints
                        ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)

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
                        if mTEPES.pIndHydroTopology == 1:
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
                        if pIndLogConsole == 1:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        # there are investment decisions (it is an expansion and operation model), or there are system emission constraints
                        ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)

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
    if mTEPES.pIndHydroTopology == 1:
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
    if pIndOutputResults == 1:
        pIndDumpRawResults              = 0
        pIndInvestmentResults           = 1
        pIndGenerationOperationResults  = 1
        pIndESSOperationResults         = 1
        pIndReservoirOperationResults   = 1
        pIndNetworkH2OperationResults   = 1
        pIndNetworkHeatOperationResults = 1
        pIndFlexibilityResults          = 1
        pIndReliabilityResults          = 1
        pIndNetworkOperationResults     = 1
        pIndNetworkMapResults           = 1
        pIndOperationSummaryResults     = 1
        pIndCostSummaryResults          = 1
        pIndMarginalResults             = 1
        pIndEconomicResults             = 1
        # output plot results
        pIndPlotOutput                  = 1
    else:
        pIndDumpRawResults              = 0
        pIndInvestmentResults           = 1
        pIndGenerationOperationResults  = 0
        pIndESSOperationResults         = 0
        pIndReservoirOperationResults   = 0
        pIndNetworkH2OperationResults   = 0
        pIndNetworkHeatOperationResults = 0
        pIndFlexibilityResults          = 0
        pIndReliabilityResults          = 0
        pIndNetworkOperationResults     = 0
        pIndNetworkMapResults           = 0
        pIndOperationSummaryResults     = 1
        pIndCostSummaryResults          = 1
        pIndMarginalResults             = 0
        pIndEconomicResults             = 1
        # output plot results
        pIndPlotOutput                  = 0

    # output parameters, variables, and duals to CSV files
    if pIndDumpRawResults:
        OutputResultsParVarCon(DirName, CaseName, mTEPES, mTEPES)

    if pIndInvestmentResults           == 1:
        InvestmentResults                 (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndGenerationOperationResults  == 1:
        GenerationOperationResults        (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
        if mTEPES.ch and mTEPES.pIndHeat == 1:
            GenerationOperationHeatResults(DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndESSOperationResults         == 1 and mTEPES.es:
        ESSOperationResults               (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndReservoirOperationResults   == 1 and mTEPES.rs and mTEPES.pIndHydroTopology == 1:
        ReservoirOperationResults         (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndNetworkH2OperationResults   == 1 and mTEPES.pa and mTEPES.pIndHydrogen == 1:
        NetworkH2OperationResults         (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkHeatOperationResults == 1 and mTEPES.ha and mTEPES.pIndHeat == 1:
        NetworkHeatOperationResults       (DirName, CaseName, mTEPES, mTEPES)
    if pIndFlexibilityResults          == 1:
        FlexibilityResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndReliabilityResults          == 1:
        ReliabilityResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkOperationResults     == 1:
        NetworkOperationResults           (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkMapResults           == 1:
        NetworkMapResults                 (DirName, CaseName, mTEPES, mTEPES)
    if pIndOperationSummaryResults     == 1:
        OperationSummaryResults           (DirName, CaseName, mTEPES, mTEPES)
    if pIndCostSummaryResults          == 1:
        CostSummaryResults                (DirName, CaseName, mTEPES, mTEPES)
    if pIndMarginalResults             == 1:
        MarginalResults                   (DirName, CaseName, mTEPES, mTEPES,                 pIndPlotOutput)
    if pIndEconomicResults             == 1:
        EconomicResults                   (DirName, CaseName, mTEPES, mTEPES, pIndAreaOutput, pIndPlotOutput)

    return mTEPES
