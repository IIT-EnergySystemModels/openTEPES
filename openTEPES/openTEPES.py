"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - April 28, 2021
"""

import time
import os
import setuptools

from pyomo.environ import ConcreteModel, Set

from openTEPES.openTEPES_InputData        import InputData, SettingUpVariables
from openTEPES.openTEPES_ModelFormulation import InvestmentModelFormulation, GenerationOperationModelFormulation, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation
from openTEPES.openTEPES_ProblemSolving   import ProblemSolving
from openTEPES.openTEPES_OutputResults    import InvestmentResults, GenerationOperationResults, ESSOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, EconomicResults, NetworkMapResults


def openTEPES_run(DirName, CaseName, SolverName):

    InitialTime = time.time()
    _path = os.path.join(DirName, CaseName)

    #%% model declaration
    mTEPES = ConcreteModel('Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 2.4.1 - April 28, 2021')

    pIndLogConsole = 1

    # Define sets and parameters
    InputData(DirName, CaseName, mTEPES)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # investment model objective function
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)

    # iterative model formulation for each stage of a year
    for sc,p,st in mTEPES.sc*mTEPES.p*range(1,int(sum(mTEPES.pDuration.values())/mTEPES.pStageDuration+1)):
        # activate only scenario, period and load levels to formulate
        mTEPES.del_component(mTEPES.sc)
        mTEPES.del_component(mTEPES.p )
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios'  , filter=lambda mTEPES,scc: scc in mTEPES.scc and sc == scc and mTEPES.pScenProb[scc] > 0.0)
        mTEPES.p  = Set(initialize=mTEPES.pp , ordered=True, doc='periods'    , filter=lambda mTEPES,pp : pp  in                p  == pp                                 )
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in list(mTEPES.pDuration) and mTEPES.nn.ord(nn) > (st-1)*mTEPES.pStageDuration and mTEPES.nn.ord(nn) <= st*mTEPES.pStageDuration)
        mTEPES.n2 = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in list(mTEPES.pDuration) and mTEPES.nn.ord(nn) > (st-1)*mTEPES.pStageDuration and mTEPES.nn.ord(nn) <= st*mTEPES.pStageDuration)

        # operation model objective function and constraints by stage
        GenerationOperationModelFormulation(mTEPES, mTEPES, pIndLogConsole, st)
        NetworkSwitchingModelFormulation   (mTEPES, mTEPES, pIndLogConsole, st)
        NetworkOperationModelFormulation   (mTEPES, mTEPES, pIndLogConsole, st)

    StartTime         = time.time()
    mTEPES.write(_path+'/openTEPES_'+CaseName+'.lp', io_options={'symbolic_solver_labels': True})  # create lp-format file
    WritingLPFileTime = time.time() - StartTime
    StartTime         = time.time()
    print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES)

    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.n )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and mTEPES.pScenProb[scc] > 0.0)
    mTEPES.p  = Set(initialize=mTEPES.pp , ordered=True, doc='periods'                                                                                 )
    mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in list(mTEPES.pDuration)                    )

    InvestmentResults         (DirName, CaseName, mTEPES, mTEPES)
    GenerationOperationResults(DirName, CaseName, mTEPES, mTEPES)
    ESSOperationResults       (DirName, CaseName, mTEPES, mTEPES)
    FlexibilityResults        (DirName, CaseName, mTEPES, mTEPES)
    NetworkOperationResults   (DirName, CaseName, mTEPES, mTEPES)
    MarginalResults           (DirName, CaseName, mTEPES, mTEPES)
    EconomicResults           (DirName, CaseName, mTEPES, mTEPES)
    NetworkMapResults         (DirName, CaseName, mTEPES, mTEPES)

    TotalTime = time.time() - InitialTime
    print('Total time                             ... ', round(TotalTime), 's')

    return mTEPES
