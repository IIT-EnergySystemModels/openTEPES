"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 22, 2026
"""

import os
import time
import psutil
import pandas              as     pd
import pyomo.environ       as     pyo
from   pyomo.environ       import Set, Param, Objective, minimize, TerminationCondition
from   pyomo.opt           import SolverFactory
from   pyomo.opt.parallel  import SolverManagerFactory
from   pyomo.contrib       import appsi
from   pyomo.common.timing import HierarchicalTimer

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_ModelFormulationInvestment        import GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment
    from .openTEPES_ModelFormulationElectricity       import GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from .openTEPES_ModelFormulationHydro             import GenerationOperationModelFormulationReservoir
    from .openTEPES_ModelFormulationHydrogen          import NetworkH2OperationModelFormulation
    from .openTEPES_ModelFormulationHeat              import NetworkHeatOperationModelFormulation
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_ModelFormulationInvestment        import GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment
    from openTEPES.openTEPES_ModelFormulationElectricity       import GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from openTEPES.openTEPES_ModelFormulationHydro             import GenerationOperationModelFormulationReservoir
    from openTEPES.openTEPES_ModelFormulationHydrogen          import NetworkH2OperationModelFormulation
    from openTEPES.openTEPES_ModelFormulationHeat              import NetworkHeatOperationModelFormulation

timer = HierarchicalTimer()

# sentinel value of itBdFinal marking the converged, final Benders pass (the extra iteration that regenerates all output results)
FINAL_ITERATION = 9999

# load-level-dependent parameters saved/restored around the sensitivity-analysis stage loop (mode 3): (parameter name, index-set name)
STAGE_PARAMS = (
    ('pDuration',      'nn'  ), ('pLoadLevelDuration', 'nn'   ),
    ('pDemand',        'psnnd'), ('pMaxTheta',         'psnnd'),
    ('pSystemInertia', 'psnar'), ('pOperReserveUp',    'psnar'), ('pOperReserveDw',     'psnar'),
    ('pInitialOutput', 'psng' ), ('pInitialUC',        'psng' ), ('pIniInventory',      'psng' ),
    ('pMinPowerElec',  'psng' ), ('pMaxPowerElec',     'psng' ), ('pMinCharge',         'psng' ),
    ('pMaxCharge',     'psng' ), ('pMaxPower2ndBlock',  'psng'), ('pMaxCharge2ndBlock', 'psng' ),
    ('pEnergyInflows', 'psng' ), ('pEnergyOutflows',   'psng' ), ('pMinStorage',        'psng' ),
    ('pMaxStorage',    'psng' ), ('pInitialSwitch',    'psnln'),
)

def RebuildStageAndLoadLevelSets(mTEPES):
    # rebuild the active stage set (st) and the load-level sets (n, n2) from s2n; shared by the per-stage loop and the final reactivation
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for p,sc,stt,nn in mTEPES.s2n)])
    ActiveLoadLevels = [nn for nn in mTEPES.nn if sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)]
    mTEPES.n  = Set(doc='load levels', initialize=ActiveLoadLevels)
    mTEPES.n2 = Set(doc='load levels', initialize=ActiveLoadLevels)

def ApplyGurobiSubproblemOptions(Solver, SolverName, LogFile):
    # per-subproblem Gurobi options shared by the parallel and LP-file solving paths
    if SolverName == 'gurobi':
        Solver.options['OutputFlag'] =  0
        Solver.options['LogFile'   ] = LogFile
        Solver.options['Method'    ] =  2
        Solver.options['Presolve'  ] =  2
        Solver.options['Crossover' ] = -1
        Solver.options['BarConvTol'] =  1e-9
        Solver.options['Threads'   ] =  int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)

def AccumulateBendersDuals(OptModel, mTEPES, p, sc, StageLabel, LoadLevels, MarginalG, MarginalR, MarginalE, MarginalCap):
    # accumulate the shadow prices of the investment-linking constraints for the Benders cuts; shared by the stage-loop and sensitivity paths
    for gc       in mTEPES.gc:
        MarginalG  [p,gc      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalGenComm_{p}_{sc}_{StageLabel}')  [n,gc]] + OptModel.dual[getattr(OptModel, f'eInstalGenCap_{p}_{sc}_{StageLabel}')[n,gc]] for n in LoadLevels)
        mTEPES.pGenerationInvestMarginalG[p,gc      ]  = MarginalG  [p,gc     ]
    for gd       in mTEPES.gd:
        MarginalR  [p,gd      ] += sum(OptModel.dual[getattr(OptModel, f'eUninstalGenComm_{p}_{sc}_{StageLabel}')[n,gd]] + OptModel.dual[getattr(OptModel, f'eUninstalGenCap_{p}_{sc}_{StageLabel}')[n,gd]] for n in LoadLevels)
        mTEPES.pGenerationInvestMarginalR[p,gd      ]  = MarginalR  [p,gd     ]
    for ec       in mTEPES.ec:
        MarginalE  [p,ec      ] += sum(OptModel.dual[getattr(OptModel, f'eInstalConESS_{p}_{sc}_{StageLabel}')   [n,ec]]                                                                            for n in LoadLevels)
        mTEPES.pGenerationInvestMarginalE[p,ec      ]  = MarginalE  [p,ec     ]
    for ni,nf,cc in mTEPES.lc:
        MarginalCap[p,ni,nf,cc] += sum(OptModel.dual[getattr(OptModel, f'eLineStateCand_{p}_{sc}_{StageLabel}')[n,ni,nf,cc]]                                                                        for n in LoadLevels)
        mTEPES.pNetworkInvestMarginalCap [p,ni,nf,cc]  = MarginalCap[p,ni,nf,cc]

def ReportInfeasible(itBd, p, sc, st):
    print('Subproblem          infeasible iteration', itBd, ', period', p, ', scenario', sc, ', stage', st)

def StageSolve(OptModel, mTEPES, DirName, CaseName, SolverName, pIndLogConsole, pIndCycleFlow, itBd, itBdFinal):
    if   mTEPES.pIndSequentialSolving == 0:
        print('Solving stages in parallel             ****')
    elif mTEPES.pIndSequentialSolving == 1:
        print('Solving stages sequentially w LP file  ****')
    elif mTEPES.pIndSequentialSolving == 2:
        print('Solving stages sequentially in memory  ****')
    elif mTEPES.pIndSequentialSolving == 3:
        print('Solving stages by sensitivity analysis ****')

    _path = os.path.join(DirName, CaseName)

    # investment-constraint shadow-price accumulators (Benders cuts); always defined (empty if no candidates) so they can be passed to AccumulateBendersDuals
    pGenerationInvestMarginalG = pd.Series([0.0]*len(mTEPES.pgc), index=mTEPES.pgc)
    pGenerationInvestMarginalR = pd.Series([0.0]*len(mTEPES.pgd), index=mTEPES.pgd)
    pGenerationInvestMarginalE = pd.Series([0.0]*len(mTEPES.pec), index=mTEPES.pec)
    pNetworkInvestMarginalCap  = pd.Series([0.0]*len(mTEPES.plc), index=mTEPES.plc)

    pTotalOCost = 0.0

    # the parallel path (pIndSequentialSolving == 0) queues one subproblem per stage into a single, persistent
    # solver manager; create it and its handle bookkeeping once here instead of recreating them on every iteration
    if mTEPES.pIndSequentialSolving == 0:
        solver_manager    = SolverManagerFactory('serial')
        action_handle_map = {}
        action_handles    = []

    # %% iterative solve for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:

        StartTime = time.time()

        # activate only period, scenario, and load levels to formulate
        RebuildStageAndLoadLevelSets(mTEPES)

        if len(mTEPES.n):
            ObjVal = None

            if mTEPES.pIndSequentialSolving <= 2 or (mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first()) or (mTEPES.pIndSequentialSolving == 3 and itBdFinal == FINAL_ITERATION):

                if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first() and not hasattr(mTEPES, 'n1'):
                    # load level of the first stage (created once and reused across Benders iterations)
                    mTEPES.n1 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)

                if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first() and itBd == 1:
                    # save all the parameters that depend on load level
                    for ParamName, IndexSet in STAGE_PARAMS:
                        setattr(mTEPES, ParamName + '_Saved', Param(getattr(mTEPES, IndexSet), initialize=getattr(mTEPES, ParamName).extract_values()))

                if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.first() and itBdFinal == FINAL_ITERATION:
                    # delete and reload all the parameters that depend on load level from their saved copies
                    for ParamName, IndexSet in STAGE_PARAMS:
                        mTEPES.del_component(getattr(mTEPES, ParamName))
                        setattr(mTEPES, ParamName, Param(getattr(mTEPES, IndexSet), initialize=getattr(mTEPES, ParamName + '_Saved').extract_values()))

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

                if itBd == 1:
                    # operation model constraints by stage
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
                            NetworkCycles                                (        mTEPES, pIndLogConsole           )
                        CycleConstraints                                 (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
                else:
                    # activate all the constraints by stage
                    for c in OptModel.component_objects(pyo.Constraint):
                        if c.name.endswith(str(st)):
                            c.activate()

                # send the problem to the solver
                if   mTEPES.pIndSequentialSolving == 0:
                    Solver = SolverFactory(SolverName, symbolic_solver_labels=False)
                    ApplyGurobiSubproblemOptions(Solver, SolverName, _path+'/openTEPES_gurobi_Sbp_'+CaseName+'.log')
                    action_handle = solver_manager.queue(OptModel, opt=Solver, warmstart=False, keepfiles=False, tee=False, load_solutions=True, report_timing=False)
                    action_handle_map    [action_handle] = f'Period {p} Scenario {sc} Stage {st}'
                    action_handles.append(action_handle)
                    # get results from already solved stages
                    for this_action_handle in action_handles:
                        SolverResults = solver_manager.get_results(this_action_handle)
                        if SolverResults is not None:
                            if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                                ObjVal = SolverResults.Problem.__getattr__('Lower bound')
                                pTotalOCost += ObjVal
                            else:
                                ReportInfeasible(itBd, p, sc, st)
                elif mTEPES.pIndSequentialSolving == 1 or mTEPES.pIndSequentialSolving == 3:
                    Solver = SolverFactory(SolverName, symbolic_solver_labels=False)
                    ApplyGurobiSubproblemOptions(Solver, SolverName, _path+'/openTEPES_gurobi_Sbp_'+CaseName+'.log')
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

                if mTEPES.pIndSequentialSolving == 2:
                    print('Writing subproblem   in memory iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')
                else:
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                # mode 0 was already queued to the solver manager above; only the sequential modes solve here
                if   mTEPES.pIndSequentialSolving == 1 or mTEPES.pIndSequentialSolving == 3:
                    SolverResults = Solver.solve(OptModel, warmstart=False,                  tee=False,                                         report_timing=False)
                    if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                        ObjVal = getattr(OptModel, f'eTotalOCost_{p}_{sc}_{st}').expr()
                        pTotalOCost += ObjVal
                    else:
                        ReportInfeasible(itBd, p, sc, st)
                elif mTEPES.pIndSequentialSolving == 2:
                    SolverResults = Solver.solve(OptModel, warmstart=False, keepfiles=False, tee=False, load_solutions=True, save_results=True, report_timing=False)
                    if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                        ObjVal = Solver.get_model_attr('ObjVal')
                        pTotalOCost += ObjVal
                    else:
                        ReportInfeasible(itBd, p, sc, st)

                # get the duals for the Benders cuts
                AccumulateBendersDuals(OptModel, mTEPES, p, sc, st, mTEPES.n, pGenerationInvestMarginalG, pGenerationInvestMarginalR, pGenerationInvestMarginalE, pNetworkInvestMarginalCap)

            elif (mTEPES.pIndSequentialSolving == 3 and st != mTEPES.stt.first()) or (mTEPES.pIndSequentialSolving == 3 and itBdFinal < FINAL_ITERATION):
                GeneratingTime = time.time() - StartTime
                if   mTEPES.pIndSequentialSolving == 3:
                    print('Writing subproblem sensitivity iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                if SolverName in ('appsi_highs', 'highs'):
                    Solver = appsi.solvers.Highs()
                else:
                    Solver = appsi.solvers.Gurobi()

                # define and initialize all the parameters that depend on the current stage; pair the first-stage load levels with the
                # current-stage ones by ordinal position (the diagonal n1<->n) instead of scanning the full n1*n product and filtering
                StagePairs = list(zip(mTEPES.n1, mTEPES.n))
                for n1,n in StagePairs:
                    mTEPES.pDuration         [     n1   ] = mTEPES.pDuration_Saved         [     n   ]
                    mTEPES.pLoadLevelDuration[     n1   ] = mTEPES.pLoadLevelDuration_Saved[     n   ]
                for p,sc in mTEPES.ps:
                    for n1,n in StagePairs:
                        for nd in mTEPES.nd:
                            mTEPES.pDemand           [p,sc,n1,nd] = mTEPES.pDemand_Saved           [p,sc,n,nd]
                            mTEPES.pMaxTheta         [p,sc,n1,nd] = mTEPES.pMaxTheta_Saved         [p,sc,n,nd]
                        for ar in mTEPES.ar:
                            mTEPES.pSystemInertia    [p,sc,n1,ar] = mTEPES.pSystemInertia_Saved    [p,sc,n,ar]
                            mTEPES.pOperReserveUp    [p,sc,n1,ar] = mTEPES.pOperReserveUp_Saved    [p,sc,n,ar]
                            mTEPES.pOperReserveDw    [p,sc,n1,ar] = mTEPES.pOperReserveDw_Saved    [p,sc,n,ar]
                        for g in mTEPES.g:
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
                        for ni,nf,cc in mTEPES.ln:
                            mTEPES.pInitialSwitch    [p,sc,n1,ni,nf,cc] = mTEPES.pInitialSwitch_Saved    [p,sc,n,ni,nf,cc]

                if pIndLogConsole == 1:
                    StartTime      = time.time()
                    # OptModel.write(_path+f'/openTEPES_Sbp_itBd{itBd}_{p}_{sc}_{st}_{CaseName}.lp', io_options={'symbolic_solver_labels': True})
                    GeneratingTime = time.time() - StartTime
                    StartTime      = time.time()
                    print('Writing subproblem     LP file iteration', itBd, ', period', p, ', scenario', sc, ', stage', st, ' ... ', round(GeneratingTime), 's')

                SolverResults = Solver.solve(OptModel, timer=timer)
                if SolverResults.termination_condition == appsi.base.TerminationCondition.optimal:
                    ObjVal = SolverResults.best_feasible_objective
                    pTotalOCost += ObjVal
                else:
                    ObjVal = None
                    ReportInfeasible(itBd, p, sc, st)

                # get the duals for the Benders cuts
                AccumulateBendersDuals(OptModel, mTEPES, p, sc, mTEPES.stt.first(), mTEPES.n1, pGenerationInvestMarginalG, pGenerationInvestMarginalR, pGenerationInvestMarginalE, pNetworkInvestMarginalCap)

            if mTEPES.pIndSequentialSolving <= 2:
                # o.f. must be deleted on every Benders iteration
                OptModel.del_component    (getattr(OptModel, f'eTotalOCost_{p}_{sc}_{st}'))

                if itBdFinal < FINAL_ITERATION:
                    # in the final iteration constraints can't be deleted to get all the output results
                    for c in OptModel.component_objects(pyo.Constraint):
                        c.deactivate()

            if mTEPES.pIndSequentialSolving == 3 and st == mTEPES.stt.last() and itBdFinal < FINAL_ITERATION:
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
                    print('Subproblem          infeasible ', solved_name)
        print('Solving                        iteration', itBd, ' ... ', round(GeneratingTime), 's      Total system operation cost [MEUR] ... ', pTotalOCost)

    mTEPES.pTotalOCost = pTotalOCost

    # activate all the periods, scenarios, and load levels again
    RebuildStageAndLoadLevelSets(mTEPES)
