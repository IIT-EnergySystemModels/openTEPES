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

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import OutputResultsParVarCon, InvestmentResults, GenerationOperationResults, GenerationOperationHeatResults, ESSOperationResults, ReservoirOperationResults, NetworkH2OperationResults, NetworkHeatOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults

# Cache static lists of functions for looped calls
_STAGE_FORMULATIONS = [
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
    CycleConstraints,
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
    return dict(
        zip([0, 0.0, 'No', 'NO', 'no', 'N', 'n'], [0]*7) |
        dict(zip(['Yes', 'YES', 'yes', 'Y', 'y'], [1]*5))
    )


def _build_model(description: str) -> ConcreteModel:
    """Instantiate Pyomo model with a name."""
    return ConcreteModel(description)


def _configure_basic_components(dir_, case, model, log_flag):
    """Load data sets and initialize model variables and indices."""
    InputData(dir_, case, model, log_flag)
    SettingUpVariables(model, model)
    model.First_st, model.Last_st = next(iter(model.st)), None
    for st in model.st:
        model.Last_st = st
    model.pDuals, model.na = {}, Set(initialize=[])


def _configure_output_flags(output_flag: int) -> dict:
    """Generate the output control flags dict."""
    base = dict(
        pIndTechnologyOutput=2,
        pIndAreaOutput=1,
        pIndPlotOutput=0
    )
    detailed = {key: int(output_flag == 1) for key,_func,_ in _OUTPUT_FUNCS}
    # ensure marginal always on in else-case
    detailed.setdefault('pIndMarginalResults', 1)
    return {**base, **detailed}


def _process_stage(model, solver, log_flag):
    """Execute all formulation functions then solve."""
    for func in _STAGE_FORMULATIONS:
        func(model, model, log_flag)
    ProblemSolving(model, solver, log_flag)


def process_stage_loop(model, solver, log_flag):
    """Loop over all scenarios and stages."""
    for _ in model.sc:
        for _ in model.st:
            _process_stage(model, solver, log_flag)


def finalize_and_output(dir_, case, model, flags):
    """Run output routines based on computed flags."""
    for flag_name, func, args in _OUTPUT_FUNCS:
        if flags.get(flag_name, 0) and _check_conditions(model, flag_name):
            func(*[locals().get(arg) if isinstance(arg,str) else arg for arg in args])


def _check_conditions(model, flag_name: str) -> bool:
    """Ensure additional model-dependent conditions for certain outputs."""
    cond_map = {
        'pIndGenerationOperationResults': True,
        'pIndNetworkH2OperationResults': getattr(model, 'pa', False) and getattr(model, 'pIndHydrogen', 0)==1,
        'pIndNetworkHeatOperationResults': getattr(model, 'ha', False) and getattr(model, 'pIndHeat', 0)==1,
        'pIndReservoirOperationResults': getattr(model, 'rs', False) and getattr(model, 'pIndHydroTopology', 0)==1,
        'pIndESSOperationResults': getattr(model, 'es', False),
    }
    return cond_map.get(flag_name, True)


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

    _configure_basic_components(DirName, CaseName, model, pLog)
    TotalObjectiveFunction(model, model, pLog)
    InvestmentModelFormulation(model, model, pLog)
    process_stage_loop(model, SolverName, pLog)

    flags = _configure_output_flags(pOut)
    finalize_and_output(DirName, CaseName, model, flags)
    return model
