"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - January 18, 2024
"""

import math
import os
import setuptools
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set, Param, Reals

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import InvestmentResults, GenerationOperationResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults


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
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.15.4 - January 18, 2024')
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.15.4 - January 18, 2024', file=open(_path+'/openTEPES_version_'+CaseName+'.log','a'))

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # Define sets and parameters
    InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # objective function and investment constraints
    TotalObjectiveFunction    (mTEPES, mTEPES, pIndLogConsole)
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)

    # initialize parameter for dual variables
    mTEPES.pDuals = {}

    # iterative model formulation for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in st == stt and mTEPES.pStageWeight and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in               mTEPES.pDuration    and           (st,nn) in mTEPES.s2n)
        mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in               mTEPES.pDuration    and           (st,nn) in mTEPES.s2n)

        print('Period '+str(p)+', Scenario '+str(sc)+', Stage '+str(st))

        # operation model objective function and constraints by stage
        GenerationOperationModelFormulationObjFunct     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationInvestment   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationDemand       (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationStorage      (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        if mTEPES.pIndHydroTopology == 1:
            GenerationOperationModelFormulationReservoir(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        if mTEPES.pIndHydrogen == 1:
            NetworkH2OperationModelFormulation          (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationCommitment   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationRampMinTime  (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkSwitchingModelFormulation                (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkOperationModelFormulation                (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

        if (len(mTEPES.gc) == 0 or (len(mTEPES.gc) > 0 and mTEPES.pIndBinGenInvest() == 2)) and (len(mTEPES.gd) == 0 or (len(mTEPES.gd) > 0 and mTEPES.pIndBinGenRetire() == 2)) and (len(mTEPES.lc) == 0 or (len(mTEPES.lc) > 0 and mTEPES.pIndBinNetInvest() == 2)) and (min([mTEPES.pEmission[p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0):
            mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] = mTEPES.pScenProb[p,sc] = 1.0

            if pIndLogConsole == 1:
                StartTime         = time.time()
                mTEPES.write(_path+'/openTEPES_'+CaseName+'_'+str(p)+'_'+str(sc)+'.lp', io_options={'symbolic_solver_labels': True})
                WritingLPFileTime = time.time() - StartTime
                StartTime         = time.time()
                print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

            # there are no expansion decisions, or they are ignored (it is an operation planning model)
            ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc)
            mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] = mTEPES.pScenProb[p,sc] = 0.0
            # deactivate the constraints of the previous period and scenario
            for c in mTEPES.component_objects(pyo.Constraint, active=True):
                if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                    c.deactivate()
        else:
            if mTEPES.p.last() == mTEPES.pp.last() and mTEPES.sc.last() == mTEPES.scc.last() and mTEPES.st.last() == mTEPES.stt.last():

                if pIndLogConsole == 1:
                    StartTime         = time.time()
                    mTEPES.write(_path+'/openTEPES_'+CaseName+'_'+str(p)+'_'+str(sc)+'.lp', io_options={'symbolic_solver_labels': True})
                    WritingLPFileTime = time.time() - StartTime
                    StartTime         = time.time()
                    print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                # there are investment decisions (it is an expansion and operation planning model)
                ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc)

    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.pStageWeight and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in mTEPES.pDuration                                         )
    mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in mTEPES.pDuration                                         )

    # activate the constraints of all the periods and scenarios
    for c in mTEPES.component_objects(pyo.Constraint):
        c.activate()

    for p,sc in mTEPES.ps:
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] = mTEPES.pScenProb[p,sc] = 1.0

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 2

    # output results just for the system (0) or for every area (1). Areas correspond usually to countries
    pIndAreaOutput = 1

    # output plot results
    pIndPlotOutput = 1

    # indicators to control the amount of output results
    if pIndOutputResults == 1:
        pIndInvestmentResults          = 1
        pIndGenerationOperationResults = 1
        pIndESSOperationResults        = 1
        pIndReservoirOperationResults  = 1
        pIndNetworkH2OperationResults  = 1
        pIndFlexibilityResults         = 1
        pIndReliabilityResults         = 1
        pIndNetworkOperationResults    = 1
        pIndNetworkMapResults          = 1
        pIndOperationSummaryResults    = 1
        pIndCostSummaryResults         = 1
        pIndMarginalResults            = 1
        pIndEconomicResults            = 1
    else:
        pIndInvestmentResults          = 1
        pIndGenerationOperationResults = 1
        pIndESSOperationResults        = 1
        pIndReservoirOperationResults  = 1
        pIndNetworkH2OperationResults  = 1
        pIndFlexibilityResults         = 0
        pIndReliabilityResults         = 0
        pIndNetworkOperationResults    = 1
        pIndNetworkMapResults          = 0
        pIndOperationSummaryResults    = 1
        pIndCostSummaryResults         = 0
        pIndMarginalResults            = 0
        pIndEconomicResults            = 0

    if pIndInvestmentResults          == 1:
        InvestmentResults         (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndGenerationOperationResults == 1:
        GenerationOperationResults(DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndESSOperationResults        == 1 and len(mTEPES.es):
        ESSOperationResults       (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndReservoirOperationResults  == 1 and len(mTEPES.rs) and mTEPES.pIndHydroTopology == 1:
        ReservoirOperationResults (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndNetworkH2OperationResults  == 1 and len(mTEPES.pa) and mTEPES.pIndHydrogen == 1:
        NetworkH2OperationResults (DirName, CaseName, mTEPES, mTEPES)
    if pIndFlexibilityResults         == 1:
        FlexibilityResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndReliabilityResults         == 1:
        ReliabilityResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkOperationResults    == 1:
        NetworkOperationResults   (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkMapResults          == 1:
        NetworkMapResults         (DirName, CaseName, mTEPES, mTEPES)
    if pIndOperationSummaryResults    == 1:
        OperationSummaryResults   (DirName, CaseName, mTEPES, mTEPES)
    if pIndCostSummaryResults         == 1:
        CostSummaryResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndMarginalResults            == 1:
        MarginalResults           (DirName, CaseName, mTEPES, mTEPES,                 pIndPlotOutput)
    if pIndEconomicResults            == 1:
        EconomicResults           (DirName, CaseName, mTEPES, mTEPES, pIndAreaOutput, pIndPlotOutput)

    TotalTime = time.time() - InitialTime
    print('Total time                             ... ', round(TotalTime), 's')

    return mTEPES
