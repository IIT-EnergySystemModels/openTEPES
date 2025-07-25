"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 11, 2025
"""

# import dill as pickle
import math
import os
import setuptools
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, DataConfiguration, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults

# Cache static lists of functions for looped calls
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
    ('pIndEconomicResults', EconomicResults, ('DirName', 'CaseName', 'mTEPES', 'mTEPES', 'pIndAreaOutput', 'pIndPlotOutput')),
]


def _initialize_indices():
    """Build mapping from user inputs to boolean flags."""
    zero_map = dict(zip([0, 0.0, 'No', 'NO', 'no', 'N', 'n'], [0]*7))
    one_map  = dict(zip(['Yes', 'YES', 'yes', 'Y', 'y'],           [1]*5))
    return zero_map | one_map


def _build_model(description: str) -> ConcreteModel:
    """Instantiate Pyomo model with a name."""
    return ConcreteModel(description)


def _reading_data(dir, case, model, log_flag):
    InputData(dir, case, model, log_flag)

def _configure_basic_components(dir_, case, model, log_flag):
    DataConfiguration(model)
    SettingUpVariables(model, model)
    model.First_st, model.Last_st = next(iter(model.st)), None
    for st in model.st:
        model.Last_st = st
    model.pDuals, model.na = {}, Set(initialize=[])
    model.NoRepetition = 0
    model._has_run_last_stage = False


def _configure_formulation_flags(model):
    """Generate the formulation control flags dict."""
    base = dict(
        pIndGenerationOperationModelFormulationObjFunct=1,
        pIndGenerationOperationModelFormulationInvestment=1,
        pIndGenerationOperationModelFormulationDemand=1,
        pIndGenerationOperationModelFormulationStorage=1,
        pIndGenerationOperationModelFormulationReservoir=1,
        pIndNetworkH2OperationModelFormulation=1,
        pIndNetworkHeatOperationModelFormulation=1,
        pIndGenerationOperationModelFormulationCommitment=0,
        pIndGenerationOperationModelFormulationRampMinTime=0,
        pIndNetworkSwitchingModelFormulation=0,
        pIndNetworkOperationModelFormulation=0,
        pIndNetworkCycles=0,
        pIndCycleConstraints=0
    )
    model._formulation_flags = base
    return base


def _configure_output_flags(output_flag: int, init_flags: int) -> dict:
    """Generate the output control flags dict."""
    base = dict(
        pIndTechnologyOutput=2,
        pIndAreaOutput=1,
        pIndPlotOutput=0
    )
    detailed = {key: int(output_flag == 1-init_flags) for key,_func,_ in _OUTPUT_FUNCS}
    return {**base, **detailed}


def _check_conditions(model, flag_name: str) -> bool:
    """Ensure additional model-dependent conditions for certain outputs."""
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
    return cond_map.get(flag_name, True)


def _process_stage(dir_, case, solver, model, log_flag, idx0, idx1, idx2):
    """Execute all formulation functions then solve."""
    for flag_name, func in _STAGE_FORMULATIONS:
        if _check_conditions(model, flag_name):
            func(model, model, log_flag, idx0, idx1, idx2)
    ProblemSolving(dir_, case, solver, model, model, log_flag, idx0, idx1, idx2)


def process_stage_loop(dir_, case, solver, model, log_flag):
    """Loop over all scenarios and stages."""
    for p,sc in model.ps:
        for st in model.st:
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
    """Main entry point: configure, solve, and output."""
    start = time.time()
    path = os.path.join(DirName, CaseName)
    idx = _initialize_indices()
    pOut, pLog = idx[pIndOutputResults], idx[pIndLogConsole]

    model_name = (
        'Open Generation, Storage, and Transmission Operation and Expansion Planning Model '
        'with RES and ESS (openTEPES) - Version 4.18.5 - May 19, 2025'
    )

    model = _build_model(model_name)
    with open(os.path.join(path, f'openTEPES_version_{CaseName}.log'), 'w') as logf:
        print(model_name, file=logf)

    _reading_data(DirName, CaseName, model, pLog)
    _configure_basic_components(DirName, CaseName, model, pLog)
    TotalObjectiveFunction(model, model, pLog)
    InvestmentModelFormulation(model, model, pLog)
    process_stage_loop(DirName, CaseName, SolverName, model, pLog)

    # show results or not
    init_flags_value = 0
    flags = _configure_output_flags(pOut, init_flags_value)
    # ensure marginal always on in else-case
    flags['pIndMarginalResults'] = 1
    finalize_and_output(DirName, CaseName, model, flags)
    return model
