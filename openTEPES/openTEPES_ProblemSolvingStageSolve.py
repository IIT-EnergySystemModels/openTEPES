"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 02, 2026
"""

import os
import time
import psutil
from   collections         import defaultdict
import pandas              as     pd
import pyomo.environ       as     pyo
from   pyomo.environ       import Set, Param, Objective, minimize, TerminationCondition, Suffix
from   pyomo.opt           import SolverFactory
from   pyomo.opt.parallel  import SolverManagerFactory
from   pyomo.contrib       import appsi
from   pyomo.common.timing import HierarchicalTimer

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_ModelFormulationObjective         import GenerationOperationModelFormulationObjFunct
    from .openTEPES_ModelFormulationInvestment        import GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment
    from .openTEPES_ModelFormulationElectricity       import GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from .openTEPES_ModelFormulationHydro             import GenerationOperationModelFormulationReservoir
    from .openTEPES_ModelFormulationHydrogen          import NetworkH2OperationModelFormulation
    from .openTEPES_ModelFormulationHeat              import NetworkHeatOperationModelFormulation
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_ModelFormulationObjective         import GenerationOperationModelFormulationObjFunct
    from openTEPES.openTEPES_ModelFormulationInvestment        import GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment
    from openTEPES.openTEPES_ModelFormulationElectricity       import GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from openTEPES.openTEPES_ModelFormulationHydro             import GenerationOperationModelFormulationReservoir
    from openTEPES.openTEPES_ModelFormulationHydrogen          import NetworkH2OperationModelFormulation
    from openTEPES.openTEPES_ModelFormulationHeat              import NetworkHeatOperationModelFormulation

timer = HierarchicalTimer()

def StageSolve(OptModel, mTEPES, DirName, CaseName, SolverName, pIndLogConsole, _path, pIndCycleFlow, itBd, itBdFinal):
    if   mTEPES.pIndSequentialSolving == 0:
        print('Solving stages in parallel             ****')
    elif mTEPES.pIndSequentialSolving == 1:
        print('Solving stages sequentially w LP file  ****')
    elif mTEPES.pIndSequentialSolving == 2:
        print('Solving stages sequentially in memory  ****')
    elif mTEPES.pIndSequentialSolving == 3:
        print('Solving stages by sensitivity analysis ****')

    _path = os.path.join(DirName, CaseName)

    if len(mTEPES.gc):
        pGenerationInvestMarginalG = pd.Series([0.0]*len(mTEPES.pgc), index=mTEPES.pgc)
    if len(mTEPES.gd):
        pGenerationInvestMarginalR = pd.Series([0.0]*len(mTEPES.pgd), index=mTEPES.pgd)
    if len(mTEPES.ec):
        pGenerationInvestMarginalE = pd.Series([0.0]*len(mTEPES.pec), index=mTEPES.pec)
    if len(mTEPES.lc):
        pNetworkInvestMarginalCap  = pd.Series([0.0]*len(mTEPES.plc), index=mTEPES.plc)

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    pTotalOCost = 0.0
    # %% iterative solve for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:

        StartTime = time.time()

        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

        if len(mTEPES.n):

            if mTEPES.pIndSequentialSolving <= 2 or (mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first()) or (mTEPES.pIndSequentialSolving == 3 and itBdFinal == 9999):

                if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first() and itBd == 1:

                    # load level of the first stage
                    mTEPES.n1 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)

                    # define and initialize all the parameters that depend on load level
                    mTEPES.pDuration_Saved          = Param(mTEPES.nn   , initialize=mTEPES.pDuration.extract_values()         )
                    mTEPES.pLoadLevelDuration_Saved = Param(mTEPES.nn   , initialize=mTEPES.pLoadLevelDuration.extract_values())
                    mTEPES.pDemand_Saved            = Param(mTEPES.psnnd, initialize=mTEPES.pDemand.extract_values()           )
                    mTEPES.pMaxTheta_Saved          = Param(mTEPES.psnnd, initialize=mTEPES.pMaxTheta.extract_values()         )
                    mTEPES.pSystemInertia_Saved     = Param(mTEPES.psnar, initialize=mTEPES.pSystemInertia.extract_values()    )
                    mTEPES.pOperReserveUp_Saved     = Param(mTEPES.psnar, initialize=mTEPES.pOperReserveUp.extract_values()    )
                    mTEPES.pOperReserveDw_Saved     = Param(mTEPES.psnar, initialize=mTEPES.pOperReserveDw.extract_values()    )
                    mTEPES.pInitialOutput_Saved     = Param(mTEPES.psng , initialize=mTEPES.pInitialOutput.extract_values()    )
                    mTEPES.pInitialUC_Saved         = Param(mTEPES.psng , initialize=mTEPES.pInitialUC.extract_values()        )
                    mTEPES.pIniInventory_Saved      = Param(mTEPES.psng , initialize=mTEPES.pIniInventory.extract_values()     )
                    mTEPES.pMinPowerElec_Saved      = Param(mTEPES.psng , initialize=mTEPES.pMinPowerElec.extract_values()     )
                    mTEPES.pMaxPowerElec_Saved      = Param(mTEPES.psng , initialize=mTEPES.pMaxPowerElec.extract_values()     )
                    mTEPES.pMinCharge_Saved         = Param(mTEPES.psng , initialize=mTEPES.pMinCharge.extract_values()        )
                    mTEPES.pMaxCharge_Saved         = Param(mTEPES.psng , initialize=mTEPES.pMaxCharge.extract_values()        )
                    mTEPES.pMaxPower2ndBlock_Saved  = Param(mTEPES.psng , initialize=mTEPES.pMaxPower2ndBlock.extract_values() )
                    mTEPES.pMaxCharge2ndBlock_Saved = Param(mTEPES.psng , initialize=mTEPES.pMaxCharge2ndBlock.extract_values())
                    mTEPES.pEnergyInflows_Saved     = Param(mTEPES.psng , initialize=mTEPES.pEnergyInflows.extract_values()    )
                    mTEPES.pEnergyOutflows_Saved    = Param(mTEPES.psng , initialize=mTEPES.pEnergyOutflows.extract_values()   )
                    mTEPES.pMinStorage_Saved        = Param(mTEPES.psng , initialize=mTEPES.pMinStorage.extract_values()       )
                    mTEPES.pMaxStorage_Saved        = Param(mTEPES.psng , initialize=mTEPES.pMaxStorage.extract_values()       )
                    mTEPES.pInitialSwitch_Saved     = Param(mTEPES.psnln, initialize=mTEPES.pInitialSwitch.extract_values()    )

                if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first() and itBdFinal == 9999:
                    # delete the components to be loaded
                    mTEPES.del_component(mTEPES.pDuration         )
                    mTEPES.del_component(mTEPES.pLoadLevelDuration)
                    mTEPES.del_component(mTEPES.pDemand           )
                    mTEPES.del_component(mTEPES.pMaxTheta         )
                    mTEPES.del_component(mTEPES.pSystemInertia    )
                    mTEPES.del_component(mTEPES.pOperReserveUp    )
                    mTEPES.del_component(mTEPES.pOperReserveDw    )
                    mTEPES.del_component(mTEPES.pInitialOutput    )
                    mTEPES.del_component(mTEPES.pInitialUC        )
                    mTEPES.del_component(mTEPES.pIniInventory     )
                    mTEPES.del_component(mTEPES.pMinPowerElec     )
                    mTEPES.del_component(mTEPES.pMaxPowerElec     )
                    mTEPES.del_component(mTEPES.pMinCharge        )
                    mTEPES.del_component(mTEPES.pMaxCharge        )
                    mTEPES.del_component(mTEPES.pMaxPower2ndBlock )
                    mTEPES.del_component(mTEPES.pMaxCharge2ndBlock)
                    mTEPES.del_component(mTEPES.pEnergyInflows    )
                    mTEPES.del_component(mTEPES.pEnergyOutflows   )
                    mTEPES.del_component(mTEPES.pMinStorage       )
                    mTEPES.del_component(mTEPES.pMaxStorage       )
                    mTEPES.del_component(mTEPES.pInitialSwitch    )

                    # define and initialize all the parameters that depend on load level
                    mTEPES.pDuration          = Param(mTEPES.nn   , initialize=mTEPES.pDuration_Saved.extract_values()         )
                    mTEPES.pLoadLevelDuration = Param(mTEPES.nn   , initialize=mTEPES.pLoadLevelDuration_Saved.extract_values())
                    mTEPES.pDemand            = Param(mTEPES.psnnd, initialize=mTEPES.pDemand_Saved.extract_values()           )
                    mTEPES.pMaxTheta          = Param(mTEPES.psnnd, initialize=mTEPES.pMaxTheta_Saved.extract_values()         )
                    mTEPES.pSystemInertia     = Param(mTEPES.psnar, initialize=mTEPES.pSystemInertia_Saved.extract_values()    )
                    mTEPES.pOperReserveUp     = Param(mTEPES.psnar, initialize=mTEPES.pOperReserveUp_Saved.extract_values()    )
                    mTEPES.pOperReserveDw     = Param(mTEPES.psnar, initialize=mTEPES.pOperReserveDw_Saved.extract_values()    )
                    mTEPES.pInitialOutput     = Param(mTEPES.psng , initialize=mTEPES.pInitialOutput_Saved.extract_values()    )
                    mTEPES.pInitialUC         = Param(mTEPES.psng , initialize=mTEPES.pInitialUC_Saved.extract_values()        )
                    mTEPES.pIniInventory      = Param(mTEPES.psng , initialize=mTEPES.pIniInventory_Saved.extract_values()     )
                    mTEPES.pMinPowerElec      = Param(mTEPES.psng , initialize=mTEPES.pMinPowerElec_Saved.extract_values()     )
                    mTEPES.pMaxPowerElec      = Param(mTEPES.psng , initialize=mTEPES.pMaxPowerElec_Saved.extract_values()     )
                    mTEPES.pMinCharge         = Param(mTEPES.psng , initialize=mTEPES.pMinCharge_Saved.extract_values()        )
                    mTEPES.pMaxCharge         = Param(mTEPES.psng , initialize=mTEPES.pMaxCharge_Saved.extract_values()        )
                    mTEPES.pMaxPower2ndBlock  = Param(mTEPES.psng , initialize=mTEPES.pMaxPower2ndBlock_Saved.extract_values() )
                    mTEPES.pMaxCharge2ndBlock = Param(mTEPES.psng , initialize=mTEPES.pMaxCharge2ndBlock_Saved.extract_values())
                    mTEPES.pEnergyInflows     = Param(mTEPES.psng , initialize=mTEPES.pEnergyInflows_Saved.extract_values()    )
                    mTEPES.pEnergyOutflows    = Param(mTEPES.psng , initialize=mTEPES.pEnergyOutflows_Saved.extract_values()   )
                    mTEPES.pMinStorage        = Param(mTEPES.psng , initialize=mTEPES.pMinStorage_Saved.extract_values()       )
                    mTEPES.pMaxStorage        = Param(mTEPES.psng , initialize=mTEPES.pMaxStorage_Saved.extract_values()       )
                    mTEPES.pInitialSwitch     = Param(mTEPES.psnln, initialize=mTEPES.pInitialSwitch_Saved.extract_values()    )

                # delete the o.f. of the complete problem
                if hasattr(mTEPES, 'eTotalSCost'):
                    mTEPES.del_component(mTEPES.eTotalSCost)

                # operation model o.f. by stage
                def eTotalOCost(OptModel):
                    return (sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * (OptModel.vTotalGCost    [p,sc,n] +
                                                                                          OptModel.vTotalCCost    [p,sc,n] +
                                                                                          OptModel.vTotalECost    [p,sc,n] +
                                                                                          OptModel.vTotalNCost    [p,sc,n] +
                                                                                          OptModel.vTotalRElecCost[p,sc,n]) for p,sc,n in mTEPES.psn                       ) +
                            sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() *  OptModel.vTotalRH2Cost  [p,sc,n]  for p,sc,n in mTEPES.psn if mTEPES.pIndHydrogen) +
                            sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() *  OptModel.vTotalRHeatCost[p,sc,n]  for p,sc,n in mTEPES.psn if mTEPES.pIndHeat    ) )
                setattr(OptModel, f'eTotalOCost_{p}_{sc}_{st}', Objective(rule=eTotalOCost, sense=minimize, doc='total system operation cost [MEUR]'))
                # def eTotalSCost(OptModel):
                #     return OptModel.vTotalSCost
                # OptModel.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

                if itBd == 1:
                    # operation model constraints by stage
                    # GenerationOperationModelFormulationObjFunct          (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
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
                    if pIndCycleFlow == 1:
                        if st == mTEPES.stt.first():
                            NetworkCycles          (          mTEPES, pIndLogConsole           )
                        CycleConstraints           (OptModel, mTEPES, pIndLogConsole, p, sc, st)
                else:
                    # activate all the constraints by stage
                    for c in OptModel.component_objects(pyo.Constraint):
                        if c.name.endswith(str(st)):
                            c.activate()

                # send the problem to the solver
                if   mTEPES.pIndSequentialSolving == 0:
                    Solver = SolverFactory(SolverName, symbolic_solver_labels=False)
                    if SolverName == 'gurobi':
                        Solver.options['OutputFlag'] =  0
                        Solver.options['LogFile'   ] = _path+'/openTEPES_gurobi_Sbp_'+CaseName+'.log'
                        Solver.options['Method'    ] =  2
                        Solver.options['Presolve'  ] =  2
                        Solver.options['Crossover' ] = -1
                        Solver.options['BarConvTol'] =  1e-9
                        Solver.options['Threads'   ] =  int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
                    solver_manager = SolverManagerFactory('serial')
                    if p == mTEPES.p.first() and sc == mTEPES.sc.first() and st == mTEPES.st.first():
                        action_handle_map = {}
                        action_handles    = []
                    action_handle = solver_manager.queue(OptModel, opt=Solver, warmstart=False, keepfiles=False, tee=False, load_solutions=True, report_timing=False)
                    action_handle_map    [action_handle] = f'Period {p} Scenario {sc} Stage {st}'
                    action_handles.append(action_handle)
                    # get results from already solved stages
                    for this_action_handle in action_handles:
                        solved_name   = action_handle_map         [this_action_handle]
                        SolverResults = solver_manager.get_results(this_action_handle)
                        if SolverResults is not None:
                            if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                                ObjVal = SolverResults.Problem.__getattr__('Lower bound')
                                pTotalOCost += ObjVal
                            else:
                                print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)
                elif mTEPES.pIndSequentialSolving == 1 or mTEPES.pIndSequentialSolving == 3:
                    Solver = SolverFactory(SolverName, symbolic_solver_labels=False)
                    if SolverName == 'gurobi':
                        Solver.options['OutputFlag'       ] =  0
                        Solver.options['LogFile'          ] = _path+'/openTEPES_gurobi_Sbp_'+CaseName+'.log'
                        Solver.options['Method'           ] =  2
                        Solver.options['Presolve'         ] =  2
                        Solver.options['Crossover'        ] = -1
                        Solver.options['BarConvTol'       ] =  1e-9
                        # Solver.options['relax_integrality'] =  1
                        Solver.options['Threads'          ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
                elif mTEPES.pIndSequentialSolving == 2:
                    Solver = SolverFactory('gurobi_persistent', profile_memory=10)
                    # Solver.set_gurobi_param('OutputFlag', 0)
                    # Solver.set_gurobi_param('LogFile',   _path+'/openTEPES_gurobi_Sbp_'+CaseName+'.log')
                    # Solver.set_gurobi_param('Method',     2)
                    # Solver.set_gurobi_param('Presolve',   2)
                    # Solver.set_gurobi_param('Crossover',   -1)
                    # Solver.set_gurobi_param('BarConvTol', 1e-9)
                    # Solver.set_gurobi_param('Threads',  int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))
                    Solver.set_instance(OptModel, symbolic_solver_labels=True)

                if pIndLogConsole == 1:
                    StartTime      = time.time()
                    OptModel.write(_path+f'/openTEPES_Sbp_itBd{itBd}_{p}_{sc}_{st}_{CaseName}.lp', io_options={'symbolic_solver_labels': True})
                    GeneratingTime = time.time() - StartTime
                    StartTime      = time.time()
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                GeneratingTime = time.time() - StartTime
                StartTime      = time.time()

                if   mTEPES.pIndSequentialSolving == 0:
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')
                elif mTEPES.pIndSequentialSolving == 1 or mTEPES.pIndSequentialSolving == 3:
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')
                    SolverResults = Solver.solve(OptModel, warmstart=False,                  tee=False,                                         report_timing=False)
                    if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                        ObjVal = getattr(OptModel, f'eTotalOCost_{p}_{sc}_{st}').expr()
                        pTotalOCost += ObjVal
                    else:
                        print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)
                elif mTEPES.pIndSequentialSolving == 2:
                    print('Writing subproblem   in memory iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')
                    SolverResults = Solver.solve(OptModel, warmstart=False, keepfiles=False, tee=False, load_solutions=True, save_results=True, report_timing=False)
                    if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                        ObjVal = Solver.get_model_attr('ObjVal')
                        pTotalOCost += ObjVal
                    else:
                        print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)

                # get the duals for the Benders cuts
                for gc       in mTEPES.gc:
                    pGenerationInvestMarginalG       [p,gc      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalGenComm_{p}_{sc}_{st}')  [n,gc]] + OptModel.dual[getattr(OptModel, f'eInstalGenCap_{p}_{sc}_{st}')[n,gc]] for n in mTEPES.n)
                    mTEPES.pGenerationInvestMarginalG[p,gc      ]  = pGenerationInvestMarginalG[p,gc     ]
                for gd       in mTEPES.gd:
                    pGenerationInvestMarginalR       [p,gd      ] += sum(OptModel.dual[getattr(OptModel, f'eUninstalGenComm_{p}_{sc}_{st}')[n,gd]] + OptModel.dual[getattr(OptModel, f'eUninstalGenCap_{p}_{sc}_{st}')[n,gd]] for n in mTEPES.n)
                    mTEPES.pGenerationInvestMarginalR[p,gd      ]  = pGenerationInvestMarginalR[p,gd     ]
                for ec       in mTEPES.ec:
                    pGenerationInvestMarginalE       [p,ec      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalConESS_{p}_{sc}_{st}')   [n,ec]]                                                                            for n in mTEPES.n)
                    mTEPES.pGenerationInvestMarginalE[p,ec      ]  = pGenerationInvestMarginalE[p,ec     ]
                for ni,nf,cc in mTEPES.lc:
                    pNetworkInvestMarginalCap        [p,ni,nf,cc] += sum(OptModel.dual[getattr(OptModel, f'eLineStateCand_{p}_{sc}_{st}')[n,ni,nf,cc]]                                                                        for n in mTEPES.n)
                    mTEPES.pNetworkInvestMarginalCap [p,ni,nf,cc]  = pNetworkInvestMarginalCap[p,ni,nf,cc]

            elif (mTEPES.pIndSequentialSolving == 3 and st != mTEPES.stt.first()) or (mTEPES.pIndSequentialSolving == 3 and itBdFinal < 9999):
                if   mTEPES.pIndSequentialSolving == 3:
                    print('Writing subproblem sensitivity iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                Solver = appsi.solvers.Gurobi()
                # if SolverName == 'gurobi':
                #     Solver.solver_options['OutputFlag'       ] = 0
                #     Solver.solver_options['LogFile'          ] = _path + '/openTEPES_gurobi_Sbp_' + CaseName + '.log'
                #     Solver.solver_options['Method'           ] = 2
                #     Solver.solver_options['Presolve'         ] = 2
                #     Solver.solver_options['Crossover'        ] = -1
                #     Solver.solver_options['BarConvTol'       ] = 1e-9
                #     # Solver.solver_options['relax_integrality'] =  1
                #     Solver.solver_options['Threads'          ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False)) / 2)

                # define and initialize all the parameters that depend on the current stage
                for n1,n in mTEPES.n1*mTEPES.n:
                    if mTEPES.n1.ord(n1) == mTEPES.n.ord(n):
                        mTEPES.pDuration         [     n1   ] = mTEPES.pDuration_Saved         [     n   ]
                        mTEPES.pLoadLevelDuration[     n1   ] = mTEPES.pLoadLevelDuration_Saved[     n   ]
                for p,sc,n1,n,nd in mTEPES.ps*mTEPES.n1*mTEPES.n*mTEPES.nd:
                    if mTEPES.n1.ord(n1) == mTEPES.n.ord(n):
                        mTEPES.pDemand           [p,sc,n1,nd] = mTEPES.pDemand_Saved           [p,sc,n,nd]
                        mTEPES.pMaxTheta         [p,sc,n1,nd] = mTEPES.pMaxTheta_Saved         [p,sc,n,nd]
                for p,sc,n1,n,ar in mTEPES.ps*mTEPES.n1*mTEPES.n*mTEPES.ar:
                    if mTEPES.n1.ord(n1) == mTEPES.n.ord(n):
                        mTEPES.pSystemInertia    [p,sc,n1,ar] = mTEPES.pSystemInertia_Saved    [p,sc,n,ar]
                        mTEPES.pOperReserveUp    [p,sc,n1,ar] = mTEPES.pOperReserveUp_Saved    [p,sc,n,ar]
                        mTEPES.pOperReserveDw    [p,sc,n1,ar] = mTEPES.pOperReserveDw_Saved    [p,sc,n,ar]
                for p,sc,n1,n,g  in mTEPES.ps*mTEPES.n1*mTEPES.n*mTEPES.g :
                    if mTEPES.n1.ord(n1) == mTEPES.n.ord(n):
                        mTEPES.pInitialOutput    [p,sc,n1,g ] = mTEPES.pInitialOutput_Saved    [p,sc,n,g ]
                        mTEPES.pInitialUC        [p,sc,n1,g ] = mTEPES.pInitialUC_Saved        [p,sc,n,g ]
                        mTEPES.pIniInventory     [p,sc,n1,g ] = mTEPES.pIniInventory_Saved     [p,sc,n,g ]
                        mTEPES.pMinPowerElec     [p,sc,n1,g ] = mTEPES.pMinPowerElec_Saved     [p,sc,n,g ]
                        mTEPES.pMaxPowerElec     [p,sc,n1,g ] = mTEPES.pMaxPowerElec_Saved     [p,sc,n,g ]
                        mTEPES.pMinCharge        [p,sc,n1,g ] = mTEPES.pMinCharge_Saved        [p,sc,n,g ]
                        mTEPES.pMaxCharge        [p,sc,n1,g ] = mTEPES.pMaxCharge_Saved        [p,sc,n,g ]
                        mTEPES.pMaxPower2ndBlock [p,sc,n1,g ] = mTEPES.pMaxPower2ndBlock_Saved [p,sc,n,g ]
                        mTEPES.pMaxCharge2ndBlock[p,sc,n1,g ] = mTEPES.pMaxCharge2ndBlock_Saved[p,sc,n,g ]
                        mTEPES.pEnergyInflows    [p,sc,n1,g ] = mTEPES.pEnergyInflows_Saved    [p,sc,n,g ]
                        mTEPES.pEnergyOutflows   [p,sc,n1,g ] = mTEPES.pEnergyOutflows_Saved   [p,sc,n,g ]
                        mTEPES.pMinStorage       [p,sc,n1,g ] = mTEPES.pMinStorage_Saved       [p,sc,n,g ]
                        mTEPES.pMaxStorage       [p,sc,n1,g ] = mTEPES.pMaxStorage_Saved       [p,sc,n,g ]
                for p,sc,n1,n,ni,nf,cc in mTEPES.ps*mTEPES.n1*mTEPES.n*mTEPES.ln:
                    if mTEPES.n1.ord(n1) == mTEPES.n.ord(n):
                        mTEPES.pInitialSwitch    [p,sc,n1,ni,nf,cc] = mTEPES.pInitialSwitch_Saved    [p,sc,n,ni,nf,cc]

                if pIndLogConsole:
                    StartTime      = time.time()
                    # OptModel.write(_path+f'/openTEPES_Sbp_itBd{itBd}_{p}_{sc}_{st}_{CaseName}.lp', io_options={'symbolic_solver_labels': True})
                    GeneratingTime = time.time() - StartTime
                    StartTime      = time.time()
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                SolverResults = Solver.solve(OptModel, timer=timer)
                # if SolverResults.termination_condition == TerminationCondition.optimal:
                ObjVal = Solver.get_model_attr('ObjVal')
                pTotalOCost += ObjVal
                # else:
                #     print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)

                # get the duals for the Benders cuts
                for gc       in mTEPES.gc:
                    pGenerationInvestMarginalG       [p,gc      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalGenComm_{p}_{sc}_{mTEPES.stt.first()}')  [n1,gc]] + OptModel.dual[getattr(OptModel, f'eInstalGenCap_{p}_{sc}_{mTEPES.stt.first()}')  [n1,gc]] for n1 in mTEPES.n1)
                    mTEPES.pGenerationInvestMarginalG[p,gc      ]  = pGenerationInvestMarginalG[p,gc     ]
                for gd       in mTEPES.gd:
                    pGenerationInvestMarginalR       [p,gd      ] += sum(OptModel.dual[getattr(OptModel, f'eUninstalGenComm_{p}_{sc}_{mTEPES.stt.first()}')[n1,gd]] + OptModel.dual[getattr(OptModel, f'eUninstalGenCap_{p}_{sc}_{mTEPES.stt.first()}')[n1,gd]] for n1 in mTEPES.n1)
                    mTEPES.pGenerationInvestMarginalR[p,gd      ]  = pGenerationInvestMarginalR[p,gd     ]
                for ec       in mTEPES.ec:
                    pGenerationInvestMarginalE       [p,ec      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalConESS_{p}_{sc}_{mTEPES.stt.first()}')   [n1,ec]]                                                                                             for n1 in mTEPES.n1)
                    mTEPES.pGenerationInvestMarginalE[p,ec      ]  = pGenerationInvestMarginalE[p,ec     ]
                for ni,nf,cc in mTEPES.lc:
                    pNetworkInvestMarginalCap        [p,ni,nf,cc] += sum(OptModel.dual[getattr(OptModel, f'eLineStateCand_{p}_{sc}_{mTEPES.stt.first()}')  [n1,ni,nf,cc]]                                                                                       for n1 in mTEPES.n1)
                    mTEPES.pNetworkInvestMarginalCap [p,ni,nf,cc]  = pNetworkInvestMarginalCap[p,ni,nf,cc]

            if mTEPES.pIndSequentialSolving <= 2:
                # o.f. must be deleted on every Benders iteration
                OptModel.del_component    (getattr(OptModel, f'eTotalOCost_{p}_{sc}_{st}'))

                if itBdFinal < 9999:
                    # in the final iteration constraints can't be deleted to get the all output results
                    for c in OptModel.component_objects(pyo.Constraint):
                        c.deactivate()

            if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.last() and itBdFinal < 9999:
                # delete the o.f.
                OptModel.del_component    (getattr(OptModel, f'eTotalOCost_{p}_{sc}_{mTEPES.stt.first()}'))

                # delete the constraints
                for c in OptModel.component_objects(pyo.Constraint):
                    c.deactivate()

            GeneratingTime = time.time() - StartTime

            if mTEPES.pIndSequentialSolving > 0:
                print('Solving                        iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's   Total system operation cost [MEUR] ... ', ObjVal)

    # retrieve the stage solution from the solver
    if mTEPES.pIndSequentialSolving == 0:
        for this_action_handle in action_handles:
            solved_name   = action_handle_map         [this_action_handle]
            SolverResults = solver_manager.get_results(this_action_handle)
            if SolverResults is not None:
                if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                    ObjVal = SolverResults.Problem.__getattr__('Lower bound')
                    pTotalOCost += ObjVal
                else:
                    print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)
        print('Solving                        iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's      Total system operation cost [MEUR] ... ', pTotalOCost)

    mTEPES.pTotalOCost = pTotalOCost

    # activate all the periods, scenarios, and load levels again
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
    mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
