"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 23, 2021
"""

import os
import time
import psutil
from   collections        import defaultdict
import pandas as pd
import pyomo.environ as pyo
from   pyomo.environ      import Set, Objective, minimize, TerminationCondition, Suffix
from   pyomo.opt          import SolverFactory
from   pyomo.opt.parallel import SolverManagerFactory

import openTEPES.openTEPES_Modules as oTM
import openTEPES.openTEPES_Modules.ACLoadFlow_Modules as ACLF


def StageSolve(DirName, CaseName, OptModel, mTEPES, pIndPowerFlow, pIndModelType, pIndCycleFlow, pIndSequentialSolving, itBd, pIndWriteLP, pIndLogConsole):
    if   pIndSequentialSolving == 0:
        print('Solving stages in parallel             ****')
    elif pIndSequentialSolving == 1:
        print('Solving stages sequentially w lp file  ****')
    elif pIndSequentialSolving == 2:
        print('Solving stages sequentially in memory  ****')

    _path = os.path.join(DirName, CaseName)

    if len(mTEPES.gc):
        pGenerationInvestMarginalG = pd.Series([0.0]*len(mTEPES.gc), index=pd.Index                 (mTEPES.gc))
    if len(mTEPES.ec):
        pGenerationInvestMarginalE = pd.Series([0.0]*len(mTEPES.ec), index=pd.Index                 (mTEPES.ec))
    if len(mTEPES.lc):
        pNetworkInvestMarginalCap  = pd.Series([0.0]*len(mTEPES.lc), index=pd.MultiIndex.from_tuples(mTEPES.lc))

    # delete the original complete o.f.
    OptModel.eTotalTCost.deactivate()
    OptModel.eTotalFCost.deactivate()

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni, cc))
        lout[ni].append((nf, cc))

    pTotalOCost = 0
    # %% iterative solve for each stage of a year
    for sc,p,st in mTEPES.scc*mTEPES.pp*mTEPES.stt:

        StartTime = time.time()

        # activate only scenario, period and load levels to formulate
        mTEPES.del_component(mTEPES.sc)
        mTEPES.del_component(mTEPES.p )
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and sc == scc and mTEPES.pScenProb   [scc])
        mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in                p  == pp                              )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.pDuration and (st,nn) in mTEPES.s2n           )
        mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.pDuration and (st,nn) in mTEPES.s2n           )

        if len(mTEPES.n):

            # define the operation model o.f.
            def eTotalOCost(model):
                return sum(mTEPES.pScenProb[sc]*(OptModel.vTotalGCost[sc,p,n] + OptModel.vTotalCCost[sc,p,n] + OptModel.vTotalECost[sc,p,n] + OptModel.vTotalRCost[sc,p,n]) for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
            # create the operation model o.f.
            setattr(OptModel, 'eTotalOCost_' + st, Objective(rule=eTotalOCost, sense=minimize, doc='total system cost [MEUR]'))

            # operation model objective function and constraints by stage
            oTM.GenerationOperationModelFormulation         (OptModel, mTEPES, pIndLogConsole, st)

            # introduce AC power flow formulation
            if pIndPowerFlow == 0:  # DC Power Flow
                oTM.NetworkSwitchingModelFormulation        (OptModel, mTEPES, pIndLogConsole, st)
                oTM.NetworkOperationModelFormulation        (OptModel, mTEPES, pIndLogConsole, st)
            elif pIndPowerFlow == 1:  # Bus Injection OPF
                ACLF.BusInj_OperationModelFormulation_AC    (OptModel, mTEPES, pIndLogConsole, st)
                if pIndModelType == 1:
                    ACLF.BusInj_OperationModelFormulation_AC(OptModel, mTEPES, pIndLogConsole, st)
                elif pIndModelType == 2:
                    ACLF.BusInj_SOCP_AC                     (OptModel, mTEPES, pIndLogConsole, st)
            elif pIndPowerFlow == 2:  # DistFlow OPF
                ACLF.DistFlow_OperationModelFormulation_AC  (OptModel, mTEPES, pIndLogConsole, st)
                if pIndModelType == 1:
                    ACLF.DistFlow_LP_AC                     (OptModel, mTEPES, pIndLogConsole, st)
                elif pIndModelType == 2:
                    ACLF.DistFlow_SOCP_AC                   (OptModel, mTEPES, pIndLogConsole, st)

            # introduce cycle flow formulations
            if pIndCycleFlow == 1:
                if st == 1:
                    oTM.NetworkCycles      (mTEPES, pIndLogConsole, pIndPowerFlow)
                if pIndPowerFlow == 0:
                    oTM.CycleConstraints   (OptModel, mTEPES, pIndLogConsole, st)
                elif pIndPowerFlow == 2 and pIndModelType != 0:
                    oTM.CycleConstraints_AC(OptModel, mTEPES, pIndLogConsole, st)

            # send the problem to the solver
            if   pIndSequentialSolving == 0:
                Solver = SolverFactory('gurobi', symbolic_solver_labels=False)
                Solver.options['OutputFlag'] =        0
                # Solver.options['LogFile' ] =       _path+'/openTEPES_Sbp_itBd'+str(itBd)+'_'+sc+'_'+p+'_'+CaseName+'.log'
                Solver.options['Method'    ] =        2
                Solver.options['Presolve'  ] =        2
                Solver.options['Crossover' ] =       -1
                Solver.options['BarConvTol'] =        1e-9
                Solver.options['Threads'   ] =        int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
                solver_manager = SolverManagerFactory('serial')
                if sc == mTEPES.sc.first() and p == mTEPES.p.first() and st == mTEPES.st.first():
                    action_handle_map = {}
                    action_handles    = []
                action_handle = solver_manager.queue(OptModel, opt=Solver, warmstart=False, keepfiles=False, tee=False, load_solutions=True, report_timing=False)
                action_handle_map[action_handle] = 'Scenario '+sc+' Period '+p+' Stage '+st
                action_handles.append(action_handle)
                # get results from already solved stages
                for this_action_handle in action_handles:
                    solved_name = action_handle_map[this_action_handle]
                    SolverResults = solver_manager.get_results(this_action_handle)
                    if SolverResults is not None:
                        if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                            ObjVal = SolverResults.Problem.__getattr__('Lower bound')
                            pTotalOCost += ObjVal
                        else:
                            print('Subproblem infeasible')
            elif pIndSequentialSolving == 1:
                Solver = SolverFactory('gurobi', symbolic_solver_labels=False)
                Solver.options['OutputFlag'       ] =  0
                # Solver.options['LogFile'          ] = _path+'/openTEPES_Sbp_itBd'+str(itBd)+'_'+sc+'_'+p+'_'+CaseName+'.log'
                Solver.options['Method'           ] =  2
                Solver.options['Presolve'         ] =  2
                Solver.options['Crossover'        ] = -1
                Solver.options['BarConvTol'       ] =  1e-9
                # Solver.options['relax_integrality'] =  1
                Solver.options['Threads'          ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
            elif pIndSequentialSolving == 2:
                Solver = SolverFactory('gurobi_persistent', profile_memory=10)
                # Solver.set_gurobi_param('OutputFlag', 0)
                # Solver.set_gurobi_param('LogFile',   _path+'/openTEPES_Sbp_itBd'+str(itBd)+'_'+sc+'_'+p+'_'+CaseName+'.log')
                # Solver.set_gurobi_param('Method',     2)
                # Solver.set_gurobi_param('Presolve',   2)
                # Solver.set_gurobi_param('Crossover',   -1)
                # Solver.set_gurobi_param('BarConvTol', 1e-9)
                # Solver.set_gurobi_param('Threads',  int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))
                Solver.set_instance(mTEPES, symbolic_solver_labels=True)

            if pIndWriteLP == 1 and pIndModelType != 0:
                StartTime         = time.time()
                OptModel.write(_path+'/openTEPES_Sbp_itBd'+str(itBd)+'_'+sc+'_'+p+'_'+st+'_'+CaseName+'.lp', io_options={'symbolic_solver_labels': True})
                WritingLPFileTime = time.time() - StartTime
                StartTime         = time.time()
                print('Writing subproblem LP file             ... ', round(WritingLPFileTime), 's')

            StageSolutionTime = time.time() - StartTime
            StartTime         = time.time()

            if   pIndSequentialSolving == 0:
                print('Writing lp file   iteration', itBd, ', scenario', sc, ', period', p, ', stage', st, ' ... ', round(StageSolutionTime), 's')
            elif pIndSequentialSolving == 1:
                print('Writing lp file   iteration', itBd, ', scenario', sc, ', period', p, ', stage', st, ' ... ', round(StageSolutionTime), 's')
                SolverResults = Solver.solve(OptModel, warmstart=False,                  tee=False,                                         report_timing=False)
                if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                     ObjVal = getattr(OptModel, 'eTotalOCost_'+st).expr()
                     pTotalOCost += ObjVal
                else:
                     print('Subproblem infeasible')
            elif pIndSequentialSolving == 2:
                print('Writing in memory iteration', itBd, ', scenario', sc, ', period', p, ', stage', st, ' ... ', round(StageSolutionTime), 's')
                SolverResults = Solver.solve(OptModel, warmstart=False, keepfiles=False, tee=False, load_solutions=True, save_results=True, report_timing=False)
                if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                    ObjVal = Solver.get_model_attr('ObjVal')
                    pTotalOCost += ObjVal
                else:
                    print('Subproblem infeasible')

            for gc in mTEPES.gc:
                pGenerationInvestMarginalG       [gc      ] = sum(OptModel.dual[getattr(OptModel, 'eInstalGenComm_'+st)[sc,p,n,gc      ]] + mTEPES.dual[getattr(OptModel, 'eInstalGenCap_'+st)[sc,p,n,gc]] for n in mTEPES.n) + pGenerationInvestMarginalG[gc     ]
                mTEPES.pGenerationInvestMarginalG[gc      ] = pGenerationInvestMarginalG[gc]
            for ec in mTEPES.ec:
                pGenerationInvestMarginalE       [ec      ] = sum(OptModel.dual[getattr(OptModel, 'eInstalConESS_' +st)[sc,p,n,ec      ]]                                                                  for n in mTEPES.n) + pGenerationInvestMarginalE[ec     ]
                mTEPES.pGenerationInvestMarginalE[ec      ] = pGenerationInvestMarginalE[ec]
            for ni, nf, cc in mTEPES.lc:
                pNetworkInvestMarginalCap        [ni,nf,cc] = sum(OptModel.dual[getattr(OptModel, 'eLineStateCand_'+st)[sc,p,n,ni,nf,cc]]                                                                  for n in mTEPES.n) + pNetworkInvestMarginalCap[ni,nf,cc]
                mTEPES.pNetworkInvestMarginalCap [ni,nf,cc] = pNetworkInvestMarginalCap[ni, nf, cc]

            # delete the o.f.
            OptModel.del_component    (getattr(OptModel, 'eTotalOCost_'            +st))

            # delete all the constraints
            OptModel.del_component    (getattr(OptModel, 'eTotalGCost_'            +st))
            OptModel.del_component    (getattr(OptModel, 'eTotalCCost_'            +st))
            OptModel.del_component    (getattr(OptModel, 'eTotalECost_'            +st))
            OptModel.del_component    (getattr(OptModel, 'eTotalRCost_'            +st))
            OptModel.del_component    (getattr(OptModel, 'eInstalGenComm_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eInstalGenCap_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eInstalConESS_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eAdequacyReserveMargin_' +st))
            OptModel.del_component    (getattr(OptModel, 'eSystemInertia_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eOperReserveUp_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eOperReserveDw_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eReserveUpIfEnergy_'     +st))
            OptModel.del_component    (getattr(OptModel, 'eReserveDwIfEnergy_'     +st))
            OptModel.del_component    (getattr(OptModel, 'eESSReserveUpIfEnergy_'  +st))
            OptModel.del_component    (getattr(OptModel, 'eESSReserveDwIfEnergy_'  +st))
            OptModel.del_component    (getattr(OptModel, 'eBalance_'               +st))
            OptModel.del_component    (getattr(OptModel, 'eESSInventory_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eMaxCharge_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eMinCharge_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eChargeDischarge_'       +st))
            OptModel.del_component    (getattr(OptModel, 'eESSTotalCharge_'        +st))
            OptModel.del_component    (getattr(OptModel, 'eEnergyOutflows_'        +st))
            OptModel.del_component    (getattr(OptModel, 'eMaxOutput2ndBlock_'     +st))
            OptModel.del_component    (getattr(OptModel, 'eMinOutput2ndBlock_'     +st))
            OptModel.del_component    (getattr(OptModel, 'eTotalOutput_'           +st))
            OptModel.del_component    (getattr(OptModel, 'eUCStrShut_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eRampUp_'                +st))
            OptModel.del_component    (getattr(OptModel, 'eRampDw_'                +st))
            OptModel.del_component    (getattr(OptModel, 'eRampUpChr_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eRampDwChr_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eMinUpTime_'             +st))
            OptModel.del_component    (getattr(OptModel, 'eMinDownTime_'           +st))
            OptModel.del_component    (getattr(OptModel, 'eLineStateCand_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eSWOnOff_'               +st))
            OptModel.del_component    (getattr(OptModel, 'eMinSwOnState_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eMinSwOffState_'         +st))
            OptModel.del_component    (getattr(OptModel, 'eExistNetCap1_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eExistNetCap2_'          +st))
            OptModel.del_component    (getattr(OptModel, 'eCandNetCap1_'           +st))
            OptModel.del_component    (getattr(OptModel, 'eCandNetCap2_'           +st))
            if pIndCycleFlow == 0:
                OptModel.del_component(getattr(OptModel, 'eKirchhoff2ndLaw1_'      +st))
                OptModel.del_component(getattr(OptModel, 'eKirchhoff2ndLaw2_'      +st))
            else:
                OptModel.del_component(getattr(OptModel, 'eCycleKirchhoff2ndLaw1_' +st))
                OptModel.del_component(getattr(OptModel, 'eCycleKirchhoff2ndLaw2_' +st))
                OptModel.del_component(getattr(OptModel, 'eFlowParallelCandidate1_'+st))
                OptModel.del_component(getattr(OptModel, 'eFlowParallelCandidate2_'+st))
            OptModel.del_component    (getattr(OptModel, 'eLineLosses1_'           +st))
            OptModel.del_component    (getattr(OptModel, 'eLineLosses2_'           +st))

            # delete all the indexes of the constraints
            OptModel.del_component     (getattr(OptModel, 'eTotalGCost_'           +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eTotalCCost_'           +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eTotalECost_'           +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eTotalRCost_'           +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eInstalGenComm_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eInstalGenCap_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eInstalConESS_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eAdequacyReserveMargin_'+st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eSystemInertia_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eOperReserveUp_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eOperReserveDw_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eReserveUpIfEnergy_'    +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eReserveDwIfEnergy_'    +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eESSReserveUpIfEnergy_' +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eESSReserveDwIfEnergy_' +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eBalance_'              +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eESSInventory_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMaxCharge_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinCharge_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eChargeDischarge_'      +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eESSTotalCharge_'       +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eEnergyOutflows_'       +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMaxOutput2ndBlock_'    +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinOutput2ndBlock_'    +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eTotalOutput_'          +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eUCStrShut_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eRampUp_'               +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eRampDw_'               +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eRampUpChr_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eRampDwChr_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinUpTime_'            +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinDownTime_'          +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eLineStateCand_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eSWOnOff_'              +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinSwOnState_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eMinSwOffState_'        +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eExistNetCap1_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eExistNetCap2_'         +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eCandNetCap1_'          +st+'_index'))
            OptModel.del_component     (getattr(OptModel, 'eCandNetCap2_'          +st+'_index'))
            if pIndCycleFlow == 0:
                OptModel.del_component(getattr(OptModel, 'eKirchhoff2ndLaw1_'      +st+'_index'))
                OptModel.del_component(getattr(OptModel, 'eKirchhoff2ndLaw2_'      +st+'_index'))
            else:
                OptModel.del_component(getattr(OptModel, 'eCycleKirchhoff2ndLaw1_' +st+'_index'))
                OptModel.del_component(getattr(OptModel, 'eCycleKirchhoff2ndLaw2_' +st+'_index'))
                OptModel.del_component(getattr(OptModel, 'eFlowParallelCandidate1_'+st+'_index'))
                OptModel.del_component(getattr(OptModel, 'eFlowParallelCandidate2_'+st+'_index'))
            OptModel.del_component    (getattr(OptModel, 'eLineLosses1_'           +st+'_index'))
            OptModel.del_component    (getattr(OptModel, 'eLineLosses2_'           +st+'_index'))

            StageSolutionTime = time.time() - StartTime

            if pIndSequentialSolving > 0:
                print('Solving           iteration', itBd, ', scenario', sc, ', period', p, ', stage', st, ' ... ', round(StageSolutionTime), 's      Total system operation cost [MEUR] ... ', ObjVal)

    # retrieve the stage solution from the solver
    if pIndSequentialSolving == 0:
        for this_action_handle in action_handles:
            solved_name = action_handle_map[this_action_handle]
            SolverResults = solver_manager.get_results(this_action_handle)
            if SolverResults is not None:
                if SolverResults.solver.termination_condition == TerminationCondition.optimal:
                    ObjVal = SolverResults.Problem.__getattr__('Lower bound')
                    pTotalOCost += ObjVal
                else:
                    print('Subproblem infeasible')
        print('Solving           iteration', itBd, ', scenario', sc, ', period', p, ', stage', st, ' ... ', round(StageSolutionTime), 's      Total system operation cost [MEUR] ... ', pTotalOCost)

    mTEPES.pTotalOCost = pTotalOCost

    # activate all the scenarios, periods and load levels again
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and mTEPES.pScenProb   [scc])
    mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in p == pp                                )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in                mTEPES.pDuration        )
