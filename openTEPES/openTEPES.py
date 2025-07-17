"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 15, 2025
"""

# import dill as pickle
import math
import os
import setuptools
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set, Block, Param, Boolean

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, ScenarioObjectiveFunction, StageObjectiveFunction, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults

from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
wlp  = True
def WriteLP(mTEPES,_path,CaseName,p,sc,st):
    StartTime = time.time()
    mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
    WritingLPFileTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing LP file                         ... ', round(WritingLPFileTime), 's')
def GenerateModel(mTEPES,pIndLogConsole,pIndCycleFlow,p,sc,st,):
    gentimes = time.perf_counter()
    GenerationOperationModelFormulationObjFunct(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationInvestment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationDemand(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationStorage(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHydroTopology == 1:
        GenerationOperationModelFormulationReservoir(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHydrogen == 1:
        NetworkH2OperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHeat == 1:
        NetworkHeatOperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationCommitment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationRampMinTime(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    NetworkSwitchingModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    NetworkOperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    # introduce cycle flow formulations
    if pIndCycleFlow == 1:
        if st == mTEPES.First_st:
            NetworkCycles(mTEPES, pIndLogConsole)
        CycleConstraints(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    gentimee = time.perf_counter()
    print(f"Generation time:{gentimee -gentimes}, P:{p},ST:{st}")

def GenerateModelwoInv(mTEPES,pIndLogConsole,pIndCycleFlow,p,sc,st,):
    gentimes = time.perf_counter()
    GenerationOperationModelFormulationObjFunct(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    # GenerationOperationModelFormulationInvestment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationDemand(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationStorage(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHydroTopology == 1:
        GenerationOperationModelFormulationReservoir(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHydrogen == 1:
        NetworkH2OperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    if mTEPES.pIndHeat == 1:
        NetworkHeatOperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationCommitment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerationOperationModelFormulationRampMinTime(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    NetworkSwitchingModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    NetworkOperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    # introduce cycle flow formulations
    if pIndCycleFlow == 1:
        if st == mTEPES.First_st:
            NetworkCycles(mTEPES, pIndLogConsole)
        CycleConstraints(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    gentimee = time.perf_counter()
    print(f"Generation time:{gentimee -gentimes}, P:{p},ST:{st}")


def GenerateAndSolveModel(mTEPES,pIndLogConsole,pIndCycleFlow, _path, DirName, CaseName, SolverName):
    # TotalObjectiveFunction(mTEPES, mTEPES, pIndLogConsole)
    # InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)
    # for p, sc, st in mTEPES.psc * mTEPES.stt:
    #     print(f"Generando {p},{sc},{st}")
    #     GenerateModel(mTEPES, pIndLogConsole, pIndCycleFlow, p, sc, st)
    #
    # if pIndLogConsole == 1:
    #     StartTime = time.time()
    #     mTEPES.write(f'{_path}/openTEPES_{CaseName}.lp', io_options={'symbolic_solver_labels': True})
    #     WritingLPFileTime = time.time() - StartTime
    #     StartTime = time.time()
    #     print('Writing LP file                        ... ', round(WritingLPFileTime), 's')
    # ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)

    TotalObjectiveFunction(mTEPES, mTEPES, pIndLogConsole)
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)
    for p in mTEPES.Period:
        Period = mTEPES.Period[p]
        for sc in Period.Scenario:
            Scenario = Period.Scenario[sc]
            for st in Scenario.Stage:
                Stage = Scenario.Stage[st]
                GenerateModel(mTEPES, pIndLogConsole, pIndCycleFlow, p, sc, st)
    if pIndLogConsole == 1 or wlp == True:
        StartTime = time.time()
        mTEPES.write(f'{_path}/openTEPES_{CaseName}_series.lp', io_options={'symbolic_solver_labels': True})
        WritingLPFileTime = time.time() - StartTime
        StartTime = time.time()
        print(f'Writing LP file for                 ... {round(WritingLPFileTime)} s')
    pss = time.perf_counter()
    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    pse = time.perf_counter()
    print(f"Solve time:{pse-pss}")

def GenerateAndSolveScenario(mTEPES, pIndLogConsole, pIndCycleFlow, _path, DirName, CaseName, SolverName,p,sc):
    print(f"gen and solve p:{p},sc:{sc}")
    # This is the actual work for one scenario
    Period = mTEPES.Period[p]
    Scenario = mTEPES.Period[p].Scenario[sc]
    ScenarioObjectiveFunction(mTEPES, mTEPES, pIndLogConsole, p, sc)
    for st in Scenario.Stage:
        Stage = Scenario.Stage[st]
        GenerateModelwoInv(mTEPES, pIndLogConsole, pIndCycleFlow, p, sc, st)

    if pIndLogConsole == 1 or wlp == True:
        StartTime = time.time()
        mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_paral_scenario.lp', io_options={'symbolic_solver_labels': True})
        WritingLPFileTime = time.time() - StartTime
        StartTime = time.time()
        print(f'Writing LP file for {p} {sc}                        ... {round(WritingLPFileTime)} s')
    print(f"barrier reached, p:{p}")
    pss = time.perf_counter()
    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    pse = time.perf_counter()
    print(f"Solve time:{pse - pss}")



def GenerateAndSolveStages(mTEPES,pIndLogConsole,pIndCycleFlow, _path, DirName, CaseName, SolverName,p,sc,st):
    Period = mTEPES.Period[p]
    Scenario = mTEPES.Period[p].Scenario[sc]
    Stage = mTEPES.Period[p].Scenario[sc].Stage[st]
    StageObjectiveFunction(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    GenerateModel(mTEPES, pIndLogConsole, pIndCycleFlow, p, sc, st)

    if pIndLogConsole == 1:
        if pIndLogConsole == 1:
            StartTime = time.time()
            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
            WritingLPFileTime = time.time() - StartTime
            StartTime = time.time()
            print(f'Writing LP file for {p} {sc} {st}   ... {round(WritingLPFileTime)} s')
    pss = time.perf_counter()
    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)
    pse = time.perf_counter()
    print(f"Solve time:{pse - pss}")


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
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.2 - January 15, 2025')
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.2 - January 15, 2025', file=open(f'{_path}/openTEPES_version_{CaseName}.log','w'))

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # introduce cycle flow formulations in DC and AC load flow
    pIndCycleFlow = 0

    # Define sets and parameters
    InputData(DirName, CaseName, mTEPES, pIndLogConsole)

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


    # initialize parameter for dual variables
    mTEPES.pDuals = {}

    # control for not repeating the stages in case of several ones
    mTEPES.NoRepetition = 0
    StIndep = ScIndep = False
    # mTEPES.Parallel = False
    if mTEPES.IndependentPeriods() == False: #There is investment and the problem needs to be solved as a whole
        print("Not parallel")
        GenerateAndSolveModel(mTEPES,pIndLogConsole,pIndCycleFlow, _path, DirName, CaseName, SolverName)

    elif mTEPES.IndependentPeriods() == True and mTEPES.IndependentStages2() == False or True: #No investment but emissions or RES requirements linking stages together
        print("parallel Scenarios")
            # barrier = True
        if mTEPES.Parallel():
            with ProcessPoolExecutor(max_workers=7) as executor:
                futures = []
                for p in mTEPES.Period:
                    for sc in mTEPES.Period[p].Scenario:
                        futures.append(executor.submit(GenerateAndSolveScenario,mTEPES, pIndLogConsole, pIndCycleFlow, _path, DirName, CaseName, SolverName,p,sc))
                for future in as_completed(futures):
                    # Optionally, you can check for exceptions here
                    try:
                        result = future.result()  # This will re-raise any exception raised by the task
                    except Exception as e:
                        print(f"An error occurred: {e}")
        else:
            for p in mTEPES.Period:
                for sc in mTEPES.Period[p].Scenario:
                    GenerateAndSolveScenario(mTEPES, pIndLogConsole, pIndCycleFlow, _path, DirName, CaseName, SolverName, p, sc)



    elif mTEPES.IndependentPeriods() == True and mTEPES.IndependentStages2() == True: #All stages are independent from each other so they can be solved separately
        print("parallel Stages")
        if mTEPES.Parallel():
            with ProcessPoolExecutor(max_workers=8) as executor:
                futures = []
                for p in mTEPES.Period:
                    for sc in mTEPES.Period[p].Scenario:
                        futures.append(executor.submit(GenerateAndSolveStages,mTEPES, pIndLogConsole, pIndCycleFlow, _path, DirName, CaseName, SolverName,p,sc))
        else:
            for p in mTEPES.Period:
                for sc in mTEPES.Period[p].Scenario:
                    for st in mTEPES.Period[p].Scenario[sc].Stage:
                        GenerateAndSolveStages(mTEPES, pIndLogConsole, pIndCycleFlow, _path, DirName, CaseName, SolverName, p, sc)

        # GenerateAndSolveStages(mTEPES,pIndLogConsole,pIndCycleFlow, _path, DirName, CaseName, SolverName)

    PostSolve = time.time()
    print(f"PostSolve time:{PostSolve - InitialTime}")

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 2

    # output results just for the system (0) or for every area (1). Areas correspond usually to countries
    pIndAreaOutput = 1

    # output plot results
    pIndPlotOutput = 1

    # indicators to control the amount of output results
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
        pIndEconomicResults             = 0

    # output parameters, variables, and duals to CSV files
    if pIndDumpRawResults:
        OutputResultsParVarCon(DirName, CaseName, mTEPES, mTEPES)

    if pIndInvestmentResults           == 1:
        InvestmentResults                 (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndGenerationOperationResults  == 1:
        GenerationOperationResults        (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
        if len(mTEPES.ch) and mTEPES.pIndHeat == 1:
            GenerationOperationHeatResults(DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndESSOperationResults         == 1 and len(mTEPES.es):
        ESSOperationResults               (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndReservoirOperationResults   == 1 and len(mTEPES.rs) and mTEPES.pIndHydroTopology == 1:
        ReservoirOperationResults         (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndNetworkH2OperationResults   == 1 and len(mTEPES.pa) and mTEPES.pIndHydrogen == 1:
        NetworkH2OperationResults         (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkHeatOperationResults == 1 and len(mTEPES.ha) and mTEPES.pIndHeat == 1:
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
    FinalTime = time.time()
    print(f"Total time:{FinalTime - InitialTime}")

    return mTEPES
