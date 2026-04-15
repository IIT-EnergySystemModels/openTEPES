"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - April 15, 2026
"""

import time
import os
import pyomo.environ as pyo
import psutil
import logging
from   pyomo.opt             import SolverFactory, SolverStatus, TerminationCondition
from   pyomo.util.infeasible import log_infeasible_constraints
from   pyomo.environ         import Suffix, UnitInterval


def ProblemSolving(DirName, CaseName, SolverName, OptModel, mTEPES, pIndLogConsole, p, sc, st, ncall):
    print('Problem solving                        ####', ncall)
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    FileName = f'{_path}/openTEPES_{SolverName}_{CaseName}_{p}_{sc}_{st}.log'

    #%% solving the problem
    if SolverName != 'appsi_gurobi' and SolverName != 'gurobi_persistent':
        Solver = SolverFactory(SolverName)
        if os.path.exists(FileName):
            os.remove(FileName)
    elif SolverName == 'appsi_gurobi':
        if not hasattr(OptModel, '_appsi_gurobi_solver'):
            OptModel._appsi_gurobi_solver = SolverFactory(SolverName)
        Solver = OptModel._appsi_gurobi_solver
        if ncall == 1 or not getattr(OptModel, '_appsi_gurobi_initialized', False):
            Solver.set_instance(OptModel)
            OptModel._appsi_gurobi_initialized = True
        # else:
        #     Solver.update_config.check_for_new_or_removed_params      = False
        #     Solver.update_config.check_for_new_or_removed_vars        = False
        #     Solver.update_config.check_for_new_or_removed_constraints = False
        #     Solver.update_config.update_params                        = False
        #     Solver.update_config.update_vars                          = True
        #     Solver.update_config.update_constraints                   = False
        #     Solver.update_config.update_named_expressions             = False
        #     Solver.config.load_solution                               = True
        #     Solver.config.warmstart                                   = True
        #     Solver.config.stream_solver                               = True
    elif SolverName == 'gurobi_persistent':
        if not hasattr(OptModel, '_gurobi_persistent_solver'):
            OptModel._gurobi_persistent_solver = SolverFactory(SolverName)
        Solver = OptModel._gurobi_persistent_solver
        if ncall == 1 or not getattr(OptModel, '_gurobi_persistent_initialized', False):
            Solver.set_instance(OptModel)
            OptModel._gurobi_persistent_initialized = True
        # else:
        #     for n,el in mTEPES.n*mTEPES.el:
        #         Solver.update_var(OptModel.vESSTotalCharge[p,sc,n,el])

    if SolverName == 'gurobi' or SolverName == 'gurobi_direct' or SolverName == 'appsi_gurobi':
        Solver.options['OutputFlag'      ] = 1                                                 # suppress log file
        Solver.options['LogFile'         ] = FileName
        Solver.options['DisplayInterval' ] = 100
        Solver.options['LPWarmStart'     ] =  2
        Solver.options['Method'          ] =  2
        Solver.options['Crossover'       ] = -1
        Solver.options['MIPGap'          ] = 0.01
        Solver.options['Threads'         ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'       ] =    36000
        Solver.options['IterationLimit'  ] = 36000000
        # Solver.options['SolutionTarget'] = 1                                                 # optimal solution with or without basic solutions
        # Solver.options['MIPFocus'      ] = 3
        # Solver.options['Seed'          ] = 104729
        # Solver.options['RINS'          ] = 100
        # Solver.options['BarConvTol'    ] = 1e-10
        # Solver.options['BarQCPConvTol' ] = 0.025
    if SolverName == 'gurobi_persistent':
        Solver.set_gurobi_param('OutputFlag',        1)
        Solver.set_gurobi_param('LogFile',    FileName)
        Solver.set_gurobi_param('DisplayInterval', 100)
        Solver.set_gurobi_param('LPWarmStart',       2)
        Solver.set_gurobi_param('Method',            2)
        Solver.set_gurobi_param('Crossover',        -1)
        Solver.set_gurobi_param('MIPGap',         0.01)
        Solver.set_gurobi_param('Threads', int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))
        Solver.set_gurobi_param('TimeLimit',      36000   )
        Solver.set_gurobi_param('IterationLimit', 36000000)
    if SolverName == 'cplex':
        # Solver.options['LogFile'          ] = FileName
        Solver.options['LPMethod'           ] = 4                                                 # barrier method
        Solver.options['Threads'            ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['TimeLimit'          ] =    72000
        # Solver.options['BarCrossAlg'      ] = 0
        # Solver.options['NumericalEmphasis'] = 1
        # Solver.options['PreInd'           ] = 1
        # Solver.options['RINSHeur'         ] = 100
        # Solver.options['EpGap'            ] = 0.01
    if SolverName == 'appsi_highs':
        Solver.options['log_file'               ] = FileName
        Solver.options['solver'                 ] = 'choose'
        Solver.options['simplex_strategy'       ] = 0
        Solver.options['run_crossover'          ] = 'on'
        Solver.options['mip_rel_gap'            ] = 0.01
        Solver.options['parallel'               ] = 'choose'
        # Solver.options['primal_feasibility_tolerance'] = 1e-3
        Solver.options['threads'                ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        Solver.options['time_limit'             ] =    72000
        Solver.options['simplex_iteration_limit'] = 72000000
    if SolverName == 'gams':
        solver_options = {
            'file COPT / cplex.opt / ; put COPT putclose "LPMethod 4" / "EpGap 0.01" / ; GAMS_MODEL.OptFile = 1 ; '
            'option SysOut  = off   ;',
            'option LP      = cplex ; option MIP     = cplex    ;',
            'option ResLim  = 72000 ; option IterLim = 72000000 ;',
            'option Threads = '+str(int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))+' ;'
        }

    nUnfixedVars = 0
    for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
        if not var.is_continuous() and not var.is_fixed() and var.value != None:
            nUnfixedVars += 1

    if nUnfixedVars == 0:
        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)

    if   SolverName == 'gams':
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True, symbolic_solver_labels=False, add_options=solver_options, logfile=FileName)
    elif SolverName == 'gurobi_persistent':
        SolverResults = Solver.solve(OptModel, warmstart=True, keepfiles=False, tee=False, load_solutions=True, save_results=False, report_timing=False)
    else:
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    print('Termination condition: ', SolverResults.solver.termination_condition)
    if SolverResults.solver.termination_condition == TerminationCondition.infeasible or SolverResults.solver.termination_condition == TerminationCondition.maxTimeLimit or SolverResults.solver.termination_condition == TerminationCondition.infeasible.maxIterations:
        log_infeasible_constraints(OptModel, log_expression=True, log_variables=True)
        logging.basicConfig(filename=f'{_path}/openTEPES_infeasibilities_{CaseName}_{p}_{sc}_{st}.log', level=logging.INFO)
        raise ValueError(f'### Problem infeasible for period {p}, scenario {sc}, stage {st}')

    #%% fix values of some variables to get duals and solve it again
    # binary/continuous investment decisions are fixed to their optimal values
    # binary            operation  decisions are fixed to their optimal values
    # if NoRepetition == 1, all variables are fixed
    # if NoRepetition == 0, only the variables of the current period and scenario are fixed
    nUnfixedVars = 0
    if mTEPES.NoRepetition == 1:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed() and var.value != None:
                var.fixed  = True          # fix the current value
                var.domain = UnitInterval  # change the domain to continuous
                nUnfixedVars += 1
    else:
        for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
            if not var.is_continuous() and not var.is_fixed() and var.value != None and var.index()[0] == p and var.index()[1] == sc:
                var.fixed  = True          # fix the current value
                var.domain = UnitInterval  # change the domain to continuous
                nUnfixedVars += 1

    # continuous investment decisions are fixed to their optimal values
    for eb in mTEPES.eb:
        if (p,eb) in mTEPES.peb:
            OptModel.vGenerationInvest[p,eb].fix(        OptModel.vGenerationInvest[p,eb      ]())
    for gd in mTEPES.gd:
        if (p,gd) in mTEPES.pgd:
            OptModel.vGenerationRetire[p,gd].fix(        OptModel.vGenerationRetire[p,gd      ]())
    for ni,nf,cc in mTEPES.lc:
        if (p,ni,nf,cc) in mTEPES.plc:
            OptModel.vNetworkInvest[p,ni,nf,cc].fix(     OptModel.vNetworkInvest   [p,ni,nf,cc]())
    if mTEPES.pIndHydroTopology:
        for rc in mTEPES.rn:
            if (p,rc) in mTEPES.prc:
                OptModel.vReservoirInvest[p,rc].fix(     OptModel.vReservoirInvest [p,rc      ]())
    if mTEPES.pIndHydrogen:
        for ni,nf,cc in mTEPES.pc:
            if (p,ni,nf,cc) in mTEPES.ppc:
                OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(OptModel.vH2PipeInvest    [p,ni,nf,cc]())
    if mTEPES.pIndHeat:
        for ni,nf,cc in mTEPES.hc:
            if (p,ni,nf,cc) in mTEPES.phc:
                OptModel.vHeatPipeInvest[p,ni,nf,cc].fix(OptModel.vHeatPipeInvest  [p,ni,nf,cc]())

    if nUnfixedVars > 0:
        ncall += 1
        print('Problem solving with fixed investments ####', ncall)

        if SolverName == 'appsi_gurobi':
            Solver.update_config.check_for_new_or_removed_params      = False
            Solver.update_config.check_for_new_or_removed_vars        = False
            Solver.update_config.check_for_new_or_removed_constraints = False
            Solver.update_config.update_params                        = False
            Solver.update_config.update_vars                          = True
            Solver.update_config.update_constraints                   = False
            Solver.update_config.update_named_expressions             = False
            Solver.config.load_solution                               = True
            Solver.config.warmstart                                   = True
            Solver.config.stream_solver                               = True
        if SolverName == 'gurobi_persistent':
            for var in OptModel.component_data_objects(pyo.Var, active=True, descend_into=True):
                Solver.update_var(var)

        # if SolverName == 'gurobi' or SolverName == 'gurobi_direct' or SolverName == 'appsi_gurobi':
        #     Solver.options['OutputFlag'      ] = 1                                                 # suppress log file
        #     Solver.options['LogFile'         ] = FileName
        #     Solver.options['DisplayInterval' ] = 100
        #     Solver.options['LPWarmStart'     ] =  2
        #     Solver.options['Crossover'       ] = -1
        #     Solver.options['MIPGap'          ] = 0.01
        #     Solver.options['Threads'         ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        #     Solver.options['TimeLimit'       ] =    36000
        #     Solver.options['IterationLimit'  ] = 36000000
        #     # Solver.options['SolutionTarget'] = 1                                                 # optimal solution with or without basic solutions
        #     # Solver.options['MIPFocus'      ] = 3
        #     # Solver.options['Seed'          ] = 104729
        #     # Solver.options['RINS'          ] = 100
        #     # Solver.options['BarConvTol'    ] = 1e-10
        #     # Solver.options['BarQCPConvTol' ] = 0.025
        # if SolverName == 'gurobi_persistent':
        #     Solver.set_gurobi_param('OutputFlag',        1)
        #     Solver.set_gurobi_param('LogFile',    FileName)
        #     Solver.set_gurobi_param('DisplayInterval', 100)
        #     Solver.set_gurobi_param('LPWarmStart',       2)
        #     Solver.set_gurobi_param('Crossover',        -1)
        #     Solver.set_gurobi_param('MIPGap',         0.01)
        #     Solver.set_gurobi_param('Threads', int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2))
        #     Solver.set_gurobi_param('TimeLimit',      36000   )
        #     Solver.set_gurobi_param('IterationLimit', 36000000)
        # if SolverName == 'cplex':
        #     # Solver.options['LogFile'          ] = FileName
        #     Solver.options['Threads'            ] = int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False))/2)
        #     Solver.options['TimeLimit'          ] = 72000
        #     # Solver.options['BarCrossAlg'      ] = 0
        #     # Solver.options['NumericalEmphasis'] = 1
        #     # Solver.options['PreInd'           ] = 1
        #     # Solver.options['RINSHeur'         ] = 100
        #     # Solver.options['EpGap'            ] = 0.01

        OptModel.dual = Suffix(direction=Suffix.IMPORT_EXPORT)
        SolverResults = Solver.solve(OptModel, tee=True, report_timing=True)

    # saving the dual variables for writing in output results
    pDuals = {}
    for con in OptModel.component_objects(pyo.Constraint, active=True):
        if con.is_indexed():
            for index in con:
                pDuals[str(con.name)+str(index)] = OptModel.dual[con[index]]
    mTEPES.pDuals.update(pDuals)
    # delete dual suffix
    OptModel.del_component(OptModel.dual)

    # save values of each stage
    # for n in mTEPES.n:
    #     OptModel.vTotalGCost        [p,sc,n].fix(OptModel.vTotalGCost    [p,sc,n]())
    #     OptModel.vTotalCCost        [p,sc,n].fix(OptModel.vTotalCCost    [p,sc,n]())
    #     OptModel.vTotalECost        [p,sc,n].fix(OptModel.vTotalECost    [p,sc,n]())
    #     OptModel.vTotalRElecCost    [p,sc,n].fix(OptModel.vTotalRElecCost[p,sc,n]())
    #     if mTEPES.pIndHydrogen:
    #         OptModel.vTotalRH2Cost  [p,sc,n].fix(OptModel.vTotalRH2Cost  [p,sc,n]())
    #     if mTEPES.pIndHeat:
    #         OptModel.vTotalRHeatCost[p,sc,n].fix(OptModel.vTotalRHeatCost[p,sc,n]())

    SolvingTime = time.time() - StartTime

    #%% writing the results
    print            ('  Total system                 cost [MEUR] ', OptModel.vTotalSCost(), ' Constraints', OptModel.model().nconstraints(), ' Variables', OptModel.model().nvariables()-mTEPES.nFixedVariables+1, ' Seconds', round(SolvingTime))
    if mTEPES.NoRepetition == 1:
        for pp,scc in mTEPES.ps:
            print    (f'***** Period: {pp}, Scenario: {scc}, Stage: {st} ******')
            print    ('  Total generation  investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenInvestCost    [eb      ]   * OptModel.vGenerationInvest    [pp,eb      ]() for eb       in mTEPES.eb if (pp,eb)       in mTEPES.peb) +
                                                                     mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenInvestCost    [bc      ]   * OptModel.vGenerationInvestHeat[pp,bc      ]() for bc       in mTEPES.bc if (pp,bc)       in mTEPES.pbc))
            print    ('  Total generation  retirement cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire    [pp,gd      ]() for gd       in mTEPES.gd if (pp,gd)       in mTEPES.pgd))
            if mTEPES.pIndHydroTopology and mTEPES.rn:
                print('  Total reservoir   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest     [pp,rc      ]() for rc       in mTEPES.rn if (pp,rc)       in mTEPES.prc))
            else:
                print('  Total reservoir   investment cost [MEUR] ', 0.0)
            print    ('  Total network     investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest       [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.lc if (pp,ni,nf,cc) in mTEPES.plc))
            if mTEPES.pIndHydrogen      and mTEPES.pc:
                print('  Total H2   pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest        [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.pc if (pp,ni,nf,cc) in mTEPES.ppc))
            else:
                print('  Total H2   pipe   investment cost [MEUR] ', 0.0)
            if mTEPES.pIndHeat          and mTEPES.hc:
                print('  Total heat pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest      [pp,ni,nf,cc]() for ni,nf,cc in mTEPES.hc if (pp,ni,nf,cc) in mTEPES.phc))
            else:
                print('  Total heat pipe   investment cost [MEUR] ', 0.0)
            print    ('  Total generation  operation  cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalGCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total consumption operation  cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalCCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total emission               cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalECost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total network losses penalty cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalNCost          [pp,scc,n    ]() for n        in mTEPES.n ))
            print    ('  Total reliability electr     cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRElecCost      [pp,scc,n    ]() for n        in mTEPES.n ))
            if mTEPES.pIndHydrogen:
                print('  Total reliability hydrogen   cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRH2Cost        [pp,scc,n    ]() for n        in mTEPES.n ))
            if mTEPES.pIndHeat:
                print('  Total reliability heat       cost [MEUR] ', mTEPES.pDiscountedWeight[pp] * sum(mTEPES.pScenProb         [pp,scc  ]() * OptModel.vTotalRHeatCost      [pp,scc,n    ]() for n        in mTEPES.n ))
    else:
        print        (f'***** Period: {p}, Scenario: {sc}, Stage: {st} ******')
        print        ('  Total generation  investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenInvestCost    [eb      ]   * OptModel.vGenerationInvest    [p,eb        ]() for eb       in mTEPES.eb if (p,eb)       in mTEPES.peb) +
                                                                     mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenInvestCost    [bc      ]   * OptModel.vGenerationInvestHeat[p,bc        ]() for bc       in mTEPES.bc if (p,bc)       in mTEPES.pbc))
        print        ('  Total generation  retirement cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pGenRetireCost    [gd      ]   * OptModel.vGenerationRetire    [p,gd        ]() for gd       in mTEPES.gd if (p,gd)       in mTEPES.pgd))
        if mTEPES.pIndHydroTopology and mTEPES.rn:
            print    ('  Total reservoir   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pRsrInvestCost    [rc      ]   * OptModel.vReservoirInvest     [p,rc        ]() for rc       in mTEPES.rn if (p,rc)       in mTEPES.prc))
        else:
            print    ('  Total reservoir   investment cost [MEUR] ', 0.0)
        print        ('  Total network     investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pNetFixedCost     [ni,nf,cc]   * OptModel.vNetworkInvest       [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc))
        if mTEPES.pIndHydrogen      and mTEPES.pc:
            print    ('  Total H2   pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pH2PipeFixedCost  [ni,nf,cc]   * OptModel.vH2PipeInvest        [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc))
        else:
            print    ('  Total H2   pipe   investment cost [MEUR] ', 0.0)
        if mTEPES.pIndHeat          and mTEPES.hc:
            print    ('  Total heat pipe   investment cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc]   * OptModel.vHeatPipeInvest      [p,ni,nf,cc  ]() for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc))
        else:
            print    ('  Total heat pipe   investment cost [MEUR] ', 0.0)
        print        ('  Total generation  operation  cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalGCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total consumption operation  cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalCCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total emission               cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalECost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total network losses penalty cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalNCost          [p,sc,n      ]() for n        in mTEPES.n ))
        print        ('  Total reliability electr     cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRElecCost      [p,sc,n      ]() for n        in mTEPES.n ))
        if mTEPES.pIndHydrogen      and mTEPES.pc:
            print    ('  Total reliability H2         cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRH2Cost        [p,sc,n      ]() for n        in mTEPES.n ))
        if mTEPES.pIndHeat          and mTEPES.hc:
            print    ('  Total reliability heat       cost [MEUR] ', mTEPES.pDiscountedWeight[p]  * sum(mTEPES.pScenProb         [p,sc    ]() * OptModel.vTotalRHeatCost      [p,sc,n      ]() for n        in mTEPES.n ))

    # Adding SolverResults to mTEPES
    mTEPES.SolverResults = SolverResults
