"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - March 26, 2022
"""

import time
import os
import setuptools

from pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import InvestmentResults, GenerationOperationResults, ESSOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, EconomicResults, NetworkMapResults


def openTEPES_run(DirName, CaseName, SolverName, pIndLogConsole):

    InitialTime = time.time()
    _path = os.path.join(DirName, CaseName)

    #%% replacing string values by numerical values
    idxDict = dict()
    idxDict[0    ] = 0
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
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.5.1 - March 26, 2022')

    pIndLogConsole = [j for i, j in idxDict.items() if i == pIndLogConsole][0]

    # Define sets and parameters
    InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # objective function and investment constraints
    TotalObjectiveFunction    (mTEPES, mTEPES, pIndLogConsole)
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)

    # iterative model formulation for each stage of a year
    for sc,p,st in mTEPES.scc*mTEPES.pp*mTEPES.stt:
        # activate only scenario, period and load levels to formulate
        mTEPES.del_component(mTEPES.p )
        mTEPES.del_component(mTEPES.sc)
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in mTEPES.pp  and p  == pp                              )
        mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and sc == scc                             )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                              mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                              mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)

        print('Period '+str(p)+', Scenario '+str(sc)+', Stage '+str(st))

        # operation model objective function and constraints by stage
        GenerationOperationModelFormulationObjFunct   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationInvestment (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationDemand     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationStorage    (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationCommitment (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationRampMinTime(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkSwitchingModelFormulation              (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkOperationModelFormulation              (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

    if pIndLogConsole == 1:
        StartTime         = time.time()
        mTEPES.write(_path+'/openTEPES_'+CaseName+'.lp', io_options={'symbolic_solver_labels': True})  # create lp-format file
        WritingLPFileTime = time.time() - StartTime
        StartTime         = time.time()
        print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole)

    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in mTEPES.pp                              )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc                             )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration        )

    InvestmentResults         (DirName, CaseName, mTEPES, mTEPES)
    GenerationOperationResults(DirName, CaseName, mTEPES, mTEPES)
    ESSOperationResults       (DirName, CaseName, mTEPES, mTEPES)
    FlexibilityResults        (DirName, CaseName, mTEPES, mTEPES)
    NetworkOperationResults   (DirName, CaseName, mTEPES, mTEPES)
    MarginalResults           (DirName, CaseName, mTEPES, mTEPES)
    EconomicResults           (DirName, CaseName, mTEPES, mTEPES)
    NetworkMapResults         (DirName, CaseName, mTEPES, mTEPES)

    TotalTime = time.time() - InitialTime
    print('Total time                              ... ', round(TotalTime), 's')

    return mTEPES
