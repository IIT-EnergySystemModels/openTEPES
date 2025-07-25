import math
import os
import time
import pyomo.environ as pyo
from pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import (
    TotalObjectiveFunction,
    InvestmentModelFormulation,
    GenerationOperationModelFormulationObjFunct,
    GenerationOperationModelFormulationInvestment,
    GenerationOperationModelFormulationDemand,
    GenerationOperationModelFormulationStorage,
    GenerationOperationModelFormulationReservoir,
    NetworkH2OperationModelFormulation,
    NetworkHeatOperationModelFormulation,
    GenerationOperationModelFormulationCommitment,
    GenerationOperationModelFormulationRampMinTime,
    NetworkSwitchingModelFormulation,
    NetworkOperationModelFormulation,
    NetworkCycles,
    CycleConstraints
)
from .openTEPES_ProblemSolving import ProblemSolving
from .openTEPES_OutputResults import (
    OutputResultsParVarCon,
    InvestmentResults,
    GenerationOperationResults,
    GenerationOperationHeatResults,
    ESSOperationResults,
    ReservoirOperationResults,
    NetworkH2OperationResults,
    NetworkHeatOperationResults,
    FlexibilityResults,
    NetworkOperationResults,
    MarginalResults,
    OperationSummaryResults,
    ReliabilityResults,
    CostSummaryResults,
    EconomicResults,
    NetworkMapResults
)

# Static lists of formulation and output functions
_STAGE_FORMULATIONS = [
    ('pIndGenerationOperationModelFormulationObjFunct', GenerationOperationModelFormulationObjFunct),
    ('pIndGenerationOperationModelFormulationInvestment', GenerationOperationModelFormulationInvestment),
    ('pIndGenerationOperationModelFormulationDemand', GenerationOperationModelFormulationDemand),
    ('pIndGenerationOperationModelFormulationStorage', GenerationOperationModelFormulationStorage),
    ('pIndGenerationOperationModelFormulationReservoir', GenerationOperationModelFormulationReservoir),
    ('pIndNetworkH2OperationModelFormulation', NetworkH2OperationModelFormulation),
    ('pIndNetworkHeatOperationModelFormulation', NetworkHeatOperationModelFormulation),
    ('pIndGenerationOperationModelFormulationCommitment', GenerationOperationModelFormulationCommitment),
    ('pIndGenerationOperationModelFormulationRampMinTime', GenerationOperationModelFormulationRampMinTime),
    ('pIndNetworkSwitchingModelFormulation', NetworkSwitchingModelFormulation),
    ('pIndNetworkOperationModelFormulation', NetworkOperationModelFormulation),
    ('pIndNetworkCycles', NetworkCycles),
    ('pIndCycleConstraints', CycleConstraints)
]

_OUTPUT_FUNCS = [
    ('pIndDumpRawResults', OutputResultsParVarCon, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndInvestmentResults', InvestmentResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndTechnologyOutput', 'pIndPlotOutput')),
    ('pIndGenerationOperationResults', GenerationOperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndTechnologyOutput', 'pIndAreaOutput', 'pIndPlotOutput')),
    ('pIndESSOperationResults', ESSOperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndTechnologyOutput', 'pIndAreaOutput', 'pIndPlotOutput')),
    ('pIndReservoirOperationResults', ReservoirOperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndTechnologyOutput', 'pIndPlotOutput')),
    ('pIndNetworkH2OperationResults', NetworkH2OperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndNetworkHeatOperationResults', NetworkHeatOperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndFlexibilityResults', FlexibilityResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndReliabilityResults', ReliabilityResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndNetworkOperationResults', NetworkOperationResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndNetworkMapResults', NetworkMapResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndOperationSummaryResults', OperationSummaryResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndCostSummaryResults', CostSummaryResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES')),
    ('pIndMarginalResults', MarginalResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndPlotOutput')),
    ('pIndEconomicResults', EconomicResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndAreaOutput', 'pIndPlotOutput'))
]


def _initialize_indices():
    zero_map = dict(zip([0, 0.0, 'No', 'NO', 'no', 'N', 'n'], [0]*7))
    one_map = dict(zip(['Yes', 'YES', 'yes', 'Y', 'y'], [1]*5))
    return {**zero_map, **one_map}


def _build_model(desc: str) -> ConcreteModel:
    model = ConcreteModel()
    model.name = desc
    return model

def _reading_data(dir, case, model, log_flag):
    InputData(dir, case, model, log_flag)

def _configure_basic_components(dir_, case, model, log_flag):
    SettingUpVariables(model, model)
    model.First_st, model.Last_st = next(iter(model.st)), None
    for st in model.st:
        model.Last_st = st
    model.pDuals, model.na = {}, Set(initialize=[])
    model.NoRepetition = 0
    model._has_run_last_stage = False


def _configure_formulation_flags(model):
    flags = dict(
        pIndGenerationOperationModelFormulationObjFunct=1,
        pIndGenerationOperationModelFormulationInvestment=1,
        pIndGenerationOperationModelFormulationDemand=1,
        pIndGenerationOperationModelFormulationStorage=1,
        pIndGenerationOperationModelFormulationReservoir=1,
        pIndNetworkH2OperationModelFormulation=1,
        pIndNetworkHeatOperationModelFormulation=1,
        pIndGenerationOperationModelulationCommitment=0,
        pIndGenerationOperationModelulationRampMinTime=0,
        pIndNetworkSwitchingModelulation=0,
        pIndNetworkOperationModelulation=0,
        pIndNetworkCycles=0,
        pIndCycleConstraints=0
    )
    model._formulation_flags = flags
    return flags


def _configure_output_flags(output_flag: int, init_flags: int) -> dict:
    """Generate the output control flags dict."""
    base = dict(
        pIndTechnologyOutput=2,
        pIndAreaOutput=1,
        pIndPlotOutput=0
    )
    detailed = {key: int(output_flag == init_flags) for key,_func,_ in _OUTPUT_FUNCS}
    return {**base, **detailed}


def _check_conditions(model, flag_name: str) -> bool:
    enabled = model._formulation_flags.get(flag_name, 1)
    cond_map = {
        'pIndGenerationOperationResults': True,
        'pIndNetworkH2OperationResults': getattr(model, 'pa', False) and getattr(model, 'pIndHydrogen', 0)==1,
        'pIndNetworkHeatOperationResults': getattr(model, 'ha', False) and getattr(model, 'pIndHeat', 0)==1,
        'pIndReservoirOperationResults': getattr(model, 'rs', False) and getattr(model, 'pIndHydroTopology', 0)==1,
        'pIndESSOperationResults': getattr(model, 'es', False),
        'pIndGenerationOperationModelFormulationReservoir': getattr(model, 'rs', False) and getattr(model, 'pIndHydroTopology', 0)==1,
        'pIndNetworkH2OperationModelFormulation': getattr(model, 'pa', False) and getattr(model, 'pIndHydrogen', 0)==1,
        'pIndNetworkHeatOperationModelFormulation': getattr(model, 'ha', False) and getattr(model, 'pIndHeat', 0)==1,
        'pIndNetworkCycles': getattr(model, 'pIndCycleFlow', 0) == 1,
        'pIndCycleConstraints': getattr(model, 'pIndCycleFlow', 0) == 1,
    }
    return bool(enabled and cond_map.get(flag_name, True))


def _rebuild_stage_sets(model, p, sc, st):
    model.del_component(model.st)
    model.del_component(model.n)
    model.del_component(model.n2)
    model.st = Set(doc='stages', initialize=[
        stt for stt in model.stt
        if stt == st
           and model.pStageWeight[stt]
           and any((p, sc, stt, nn) in model.s2n for nn in model.nn)
    ])
    model.n = Set(doc='load levels', initialize=[
        nn for nn in model.nn
        if (p, sc, st, nn) in model.s2n
    ])
    model.n2 = Set(doc='load levels', initialize=model.n)


def _compute_cycle_lists(model):
    model.nesc = [(n, es) for n, es in model.n * model.es if model.n.ord(n) % model.pStorageTimeStep[es] == 0]
    model.necc = [(n, ec) for n, ec in model.n * model.ec if model.n.ord(n) % model.pStorageTimeStep[ec] == 0]
    model.neso = [(n, es) for n, es in model.n * model.es if model.n.ord(n) % model.pOutflowsTimeStep[es] == 0]
    model.ngen = [(n, g) for n, g in model.n * model.g if model.n.ord(n) % model.pEnergyTimeStep[g] == 0]
    if getattr(model, 'pIndHydroTopology', 0) == 1:
        model.nhc = [(n, h) for n, h in model.n * model.h
                     if model.n.ord(n) % sum(model.pReservoirTimeStep[rs] for rs in model.rs if (rs, h) in model.r2h) == 0]
        model.np2c = [(n, h) for n, h in model.n * model.h
                      if any((h, rs) in model.p2r for rs in model.rs)
                      and model.n.ord(n) % sum(model.pReservoirTimeStep[rs] for rs in model.rs if (h, rs) in model.p2r) == 0]
        model.npc = [(n, h) for n, h in model.n * model.h
                     if any((rs, h) in model.r2p for rs in model.rs)
                     and model.n.ord(n) % sum(model.pReservoirTimeStep[rs] for rs in model.rs if (rs, h) in model.r2p) == 0]
        model.nrsc = [(n, rs) for n, rs in model.n * model.rs if model.n.ord(n) % model.pReservoirTimeStep[rs] == 0]
        model.nrcc = [(n, rs) for n, rs in model.n * model.rn if model.n.ord(n) % model.pReservoirTimeStep[rs] == 0]
        model.nrso = [(n, rs) for n, rs in model.n * model.rs if model.n.ord(n) % model.pWaterOutTimeStep[rs] == 0]


def _accumulate_na(model, st):
    if st == model.First_st:
        model.del_component(model.na)
        model.na = Set(initialize=model.n)
    else:
        temp = set(model.na) | set(model.n)
        model.del_component(model.na)
        model.na = Set(initialize=temp)


def _apply_formulations(model, log_flag, p, sc, st):
    for flag_name, func in _STAGE_FORMULATIONS:
        if _check_conditions(model, flag_name):
            func(model, model, log_flag, p, sc, st)


def _solve_branch(dir_, case, solver, model, log_flag, p, sc, st):
    no_invest = (
        (sum(1 for rec in model.peb if rec[0] <= p) == 0 or model.pIndBinGenInvest() == 2) and
        (sum(1 for rec in model.pgd if rec[0] <= p) == 0 or model.pIndBinGenRetire() == 2) and
        (sum(1 for rec in model.prc if rec[0] <= p) == 0 or model.pIndBinRsrInvest() == 2) and
        (sum(1 for rec in model.plc if rec[0] <= p) == 0 or model.pIndBinNetElecInvest() == 2) and
        (sum(1 for rec in model.ppc if rec[0] <= p) == 0 or model.pIndBinNetH2Invest() == 2) and
        (sum(1 for rec in model.phc if rec[0] <= p) == 0 or model.pIndBinNetHeatInvest() == 2)
    )
    min_res = (
        max(model.pRESEnergy[p, ar] for ar in model.ar) > 0 or
        (min(model.pEmission[p, ar] for ar in model.ar) < math.inf and sum(model.pEmissionRate[nr] for nr in model.nr) > 0)
    )
    no_res = (
        max(model.pRESEnergy[p, ar] for ar in model.ar) == 0 and
        (min(model.pEmission[p, ar] for ar in model.ar) == math.inf or sum(model.pEmissionRate[nr] for nr in model.nr) == 0)
    )

    def write_lp():
        if log_flag == 1:
            t0 = time.time()
            model.write(f"{dir_}/{case}/openTEPES_{case}_{p}_{sc}_{st}.lp",
                        io_options={'symbolic_solver_labels': True})
            print('Writing LP file ...', round(time.time() - t0), 's')

    if no_invest and no_res:
        write_lp()
        model.pScenProb[p, sc] = 1.0
        ProblemSolving(dir_, case, solver, model, model, log_flag, p, sc, st)
        model.pScenProb[p, sc] = 0.0
    elif no_invest and min_res:
        write_lp()
        ProblemSolving(dir_, case, solver, model, model, log_flag, p, sc, st)
    else:
        write_lp()
        ProblemSolving(dir_, case, solver, model, model, log_flag, p, sc, st)

    for c in model.component_objects(pyo.Constraint, active=True):
        if str(p) in c.name and str(sc) in c.name:
            c.deactivate()


def _process_stage(dir_, case, solver, model, log_flag, p, sc, st):
    _rebuild_stage_sets(model, p, sc, st)
    _compute_cycle_lists(model)
    _accumulate_na(model, st)
    _apply_formulations(model, log_flag, p, sc, st)
    _solve_branch(dir_, case, solver, model, log_flag, p, sc, st)

    if st == model.Last_st and not model._has_run_last_stage:
        model.NoRepetition = 1
        model._has_run_last_stage = True


def process_stage_loop(dir_, case, solver, model, log_flag):
    for p, sc in model.ps:
        model._has_run_last_stage = False
        for st in model.stt:
            _process_stage(dir_, case, solver, model, log_flag, p, sc, st)


def finalize_and_output(dir_, case, model, flags):
    """Run output routines based on computed flags."""
    context = {
        'DirName':  dir_,
        'CaseName': case,
        'OptModel': model,
        'mTEPES':   model,
        'pIndTechnologyOutput': flags['pIndTechnologyOutput'],
        'pIndAreaOutput':       flags['pIndAreaOutput'],
        'pIndPlotOutput':       flags['pIndPlotOutput']
    }

    for flag_name, func, args in _OUTPUT_FUNCS:
        if not (flags.get(flag_name) and _check_conditions(model, flag_name)):
            continue
        # build a list of actual values, not raw strings
        r_args = [context[a] if isinstance(a, str) else a for a in args]
        # unpack them into separate parameters
        func(*r_args)


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole):
    start = time.time()
    path = os.path.join(DirName, CaseName)

    idx = _initialize_indices()
    pOut, pLog = idx[pIndOutputResults], idx[pIndLogConsole]

    model_name = (
        'Open Generation, Storage, and Transmission Operation and Expansion Planning Model '
        'with RES and ESS (openTEPES) - Version 4.18.6 - July 22, 2025'
    )
    mTEPES = _build_model(model_name)
    with open(os.path.join(path, f'openTEPES_version_{CaseName}.log'), 'w') as logf:
        print(model_name, file=logf)

    _reading_data(DirName, CaseName, mTEPES, pLog)
    _configure_basic_components(DirName, CaseName, mTEPES, pLog)
    TotalObjectiveFunction(mTEPES, mTEPES, pLog)
    InvestmentModelFormulation(mTEPES, mTEPES, pLog)
    _configure_formulation_flags(mTEPES)
    mTEPES.pWriteLP = False

    try:
        process_stage_loop(DirName, CaseName, SolverName, mTEPES, pLog)
        # show results or not
        init_flags_value = 0
        flags = _configure_output_flags(pOut, init_flags_value)
        # ensure marginal always on in else-case
        flags['pIndMarginalResults'] = 1
        finalize_and_output(DirName, CaseName, mTEPES, flags)
    finally:
        for c in mTEPES.component_objects(pyo.Constraint):
            c.activate()
        for p, sc in mTEPES.ps:
            mTEPES.pScenProb[p, sc] = 1.0

    return mTEPES
