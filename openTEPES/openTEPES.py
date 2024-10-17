"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - October 17, 2024
"""

# import dill as pickle
import math
import os
import time
from dataclasses import dataclass

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults



@dataclass
class Simulation:
    mTEPES: ConcreteModel
    DirName: str
    CaseName: str
    SolverName: str
    pIndOutputResults: int # TODO: make this bool instead
    pIndLogConsole: int # TODO: make this bool instead
    pIndCycleFlow: int = 0 # introduce cycle flow formulations in DC and AC load flow

    def __post_init__(self):
        #%% replacing string values by numerical values
        idxDict        = dict()
        idxDict[False] = 0
        idxDict[0    ] = 0
        idxDict[0.0  ] = 0
        idxDict[0.0  ] = 0
        idxDict['No' ] = 0
        idxDict['NO' ] = 0
        idxDict['no' ] = 0
        idxDict['N'  ] = 0
        idxDict['n'  ] = 0
        idxDict[True ] = 1
        idxDict['Yes'] = 1
        idxDict['YES'] = 1
        idxDict['yes'] = 1
        idxDict['Y'  ] = 1
        idxDict['y'  ] = 1

        self.pIndLogConsole = idxDict[self.pIndLogConsole]
        self.pIndOutputResults = idxDict[self.pIndOutputResults]
        self.path = os.path.join(self.DirName, self.CaseName)

    def input_data(self):
        # Define sets and parameters
        InputData(self.DirName, self.CaseName, self.mTEPES, self.pIndLogConsole)

    def define_variables(self):
        # Define variables
        SettingUpVariables(self.mTEPES, self.mTEPES)

    def setup_first_last_stage(self):
        self.First_st = self.mTEPES.st.first()
        self.Last_st = self.mTEPES.st.last()

    def objective_function_and_investment_constraints(self):
        # objective function and investment constraints
        TotalObjectiveFunction    (self.mTEPES, self.mTEPES, self.pIndLogConsole)
        InvestmentModelFormulation(self.mTEPES, self.mTEPES, self.pIndLogConsole)

    def initialize_pduals_and_na(self):
        # initialize parameter for dual variables
        self.mTEPES.pDuals = {}

        # initialize the set of load levels up to the current stage
        self.mTEPES.na = Set(initialize=[])

    def delete_and_initialize_st_n_n2(self, p, sc, st):
        # activate only load levels to formulate
        self.mTEPES.del_component(self.mTEPES.st)
        self.mTEPES.del_component(self.mTEPES.n )
        self.mTEPES.del_component(self.mTEPES.n2)
        self.mTEPES.st = Set(doc='stages',      initialize=[stt for stt in self.mTEPES.stt if st == stt if self.mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in self.mTEPES.s2n)])
        self.mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in self.mTEPES.nn  if                                                     (p,sc,st,nn) in self.mTEPES.s2n ])
        self.mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in self.mTEPES.nn  if                                                     (p,sc,st,nn) in self.mTEPES.s2n ])

    def calculate_load_levels(self):
        mTEPES = self.mTEPES
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

    def operation_model_objective_function_and_constraints_by_stage(self, p, sc, st):
        mTEPES = self.mTEPES
        pIndLogConsole = self.pIndLogConsole
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
        if self.pIndCycleFlow == 1:
            if st == mTEPES.First_st:
                NetworkCycles                           (        mTEPES, pIndLogConsole           )
            CycleConstraints                            (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

    def is_pcm(self) -> bool:
        mTEPES = self.mTEPES
        is_pcm = (len(mTEPES.gc) == 0 or (len(mTEPES.gc) > 0 and mTEPES.pIndBinGenInvest() == 2)) and (len(mTEPES.gd) == 0 or (len(mTEPES.gd) > 0 and mTEPES.pIndBinGenRetire() == 2)) and (len(mTEPES.lc) == 0 or (len(mTEPES.lc) > 0 and mTEPES.pIndBinNetElecInvest() == 2)) and (min([mTEPES.pEmission[p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)
        return is_pcm

    def write_lp_file(self, p, sc, st):
        mTEPES = self.mTEPES
        pIndLogConsole = self.pIndLogConsole

        StartTime         = time.time()
        mTEPES.write(self.path+'/openTEPES_'+self.CaseName+'_'+str(p)+'_'+str(sc)+'_'+str(st)+'.lp', io_options={'symbolic_solver_labels': True})
        WritingLPFileTime = time.time() - StartTime
        StartTime         = time.time()
        print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

    def output_results(self):
        DirName, CaseName, mTEPES = self.DirName, self.CaseName, self.mTEPES
        # pickle the case study data
        # with open(dump_folder+'/oT_Case_'+CaseName+'.pkl','wb') as f:
        #     pickle.dump(mTEPES, f, pickle.HIGHEST_PROTOCOL)

        # output results only for every unit (0), only for every technology (1), or for both (2)
        pIndTechnologyOutput = 2

        # output results just for the system (0) or for every area (1). Areas correspond usually to countries
        pIndAreaOutput = 1

        # output plot results
        pIndPlotOutput = 1

        # indicators to control the amount of output results
        if self.pIndOutputResults == 1:
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
            pIndInvestmentResults           = 0
            pIndGenerationOperationResults  = 0
            pIndESSOperationResults         = 0
            pIndReservoirOperationResults   = 0
            pIndNetworkH2OperationResults   = 0
            pIndNetworkHeatOperationResults = 0
            pIndFlexibilityResults          = 0
            pIndReliabilityResults          = 0
            pIndNetworkOperationResults     = 0
            pIndNetworkMapResults           = 0
            pIndOperationSummaryResults     = 0
            pIndCostSummaryResults          = 0
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

    def delete_and_initialize_na(self, st):
        mTEPES = self.mTEPES
        # load levels up to the current stage for emission and RES energy constraints
        # if (p != mTEPES.p.first() or sc != mTEPES.sc.first()) and st == mTEPES.First_st:
        #     mTEPES.del_component(mTEPES.na)
        if st == self.First_st:
            mTEPES.del_component(mTEPES.na)
            mTEPES.na = Set(initialize=mTEPES.n)
        else:
            mTEPES.na = mTEPES.na | mTEPES.n

    def solve(self, p, sc, st):
        DirName, CaseName, SolverName, mTEPES, pIndLogConsole = self.DirName, self.CaseName, self.SolverName, self.mTEPES, self.pIndLogConsole
        ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st)

    def build_and_solve_pcm(self):
        mTEPES = self.mTEPES
        # iterative model formulation for each stage of a year
        for p,sc,st in self.mTEPES.ps*self.mTEPES.stt:

            self.delete_and_initialize_st_n_n2(p, sc, st)
            self.calculate_load_levels()

            if not len(mTEPES.st): # TODO: document when this would happen. If this should not happen, throw an error here instead
                continue

            self.delete_and_initialize_na(st)

            print('Period '+str(p)+', Scenario '+str(sc)+', Stage '+str(st))

            self.operation_model_objective_function_and_constraints_by_stage(p, sc, st)

            if pIndLogConsole == 1:
                self.write_lp_file(p, sc, st)

            # there are no expansion decisions, or they are ignored (it is an operation planning model)
            mTEPES.pScenProb[p,sc] = 1.0

            self.solve(p, sc, st)

            mTEPES.pScenProb[p,sc] = 0.0

            # deactivate the constraints of the previous period and scenario
            for c in mTEPES.component_objects(pyo.Constraint, active=True):
                if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                    c.deactivate()

        p, sc = mTEPES.ps.last()
        st = mTEPES.st.last()
        self.delete_and_initialize_st_n_n2(p, sc, st)
        self.calculate_load_levels()

    def build_and_solve_capex(self):
        mTEPES = self.mTEPES
        # iterative model formulation for each stage of a year
        for p,sc,st in self.mTEPES.ps*self.mTEPES.stt:

            self.delete_and_initialize_st_n_n2(p, sc, st)
            self.calculate_load_levels()

            if not len(mTEPES.st): # TODO: document when this would happen. If this should not happen, throw an error here instead
                continue

            self.delete_and_initialize_na(st)

            print('Period '+str(p)+', Scenario '+str(sc)+', Stage '+str(st))

            self.operation_model_objective_function_and_constraints_by_stage(p, sc, st)

        p, sc = mTEPES.ps.last()
        st = mTEPES.st.last()

        self.delete_and_initialize_st_n_n2(p, sc, st)
        self.calculate_load_levels()

        if self.pIndLogConsole == 1:
            self.write_lp_file(p, sc, st)

        # there are investment decisions (it is an expansion and operation planning model)
        self.solve(p, sc, st)

        self.delete_and_initialize_st_n_n2(p, sc, st)
        self.calculate_load_levels()

        # activate the constraints of all the periods and scenarios
        for c in mTEPES.component_objects(pyo.Constraint):
            c.activate()

        # assign probability 1 to all the periods and scenarios
        for p,sc in mTEPES.ps:
            mTEPES.pScenProb[p,sc] = 1.0



def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole):
    InitialTime = time.time()
    _path = os.path.join(DirName, CaseName)

    #%% model declaration
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.17.8 - October 17, 2024')
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.17.8 - October 17, 2024', file=open(_path+'/openTEPES_version_'+CaseName+'.log','w'))

    sim = Simulation(mTEPES, DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole)

    sim.input_data()

    sim.define_variables()

    sim.objective_function_and_investment_constraints()

    sim.initialize_pduals_and_na()

    if sim.is_pcm():
        sim.build_and_solve_pcm()
    else:
        sim.build_and_solve_capex()

    sim.output_results()

    return mTEPES
