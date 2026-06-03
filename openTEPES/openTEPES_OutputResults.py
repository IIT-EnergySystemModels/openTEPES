"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - May 28, 2026

Output results facade.

The output-writing code used to live here as one large module. It is now
split by concern into ``openTEPES_OutputResults<Concern>.py`` files. This
module re-exports every public name so existing imports keep working:

    from .openTEPES_OutputResults import InvestmentResults, ...

The split is purely about where the code lives. The order in which the
functions run is still controlled by ``OUTPUT_REGISTRY`` in
``openTEPES.py`` and is unchanged.
"""

from .openTEPES_OutputResultsCommon        import PiePlots, AreaPlots, LinePlots
from .openTEPES_OutputResultsRawDump       import OutputResultsParVarCon, write_model_to_db
from .openTEPES_OutputResultsInvestment    import InvestmentResults
from .openTEPES_OutputResultsGeneration    import GenerationOperationResults, GenerationOperationHeatResults
from .openTEPES_OutputResultsStorage       import ESSOperationResults, ReservoirOperationResults
from .openTEPES_OutputResultsSectorCoupling import NetworkH2OperationResults, NetworkHeatOperationResults
from .openTEPES_OutputResultsNetwork       import NetworkOperationResults, NetworkMapResults
from .openTEPES_OutputResultsEconomic      import MarginalResults, CostSummaryResults, EconomicResults
from .openTEPES_OutputResultsSummary       import OperationSummaryResults, FlexibilityResults, ReliabilityResults

__all__ = [
    # plot helpers (kept public for backward compatibility)
    'PiePlots', 'AreaPlots', 'LinePlots',
    # raw parameter/variable/constraint dump
    'OutputResultsParVarCon', 'write_model_to_db',
    # investment and retirement
    'InvestmentResults',
    # generation operation (electricity and heat)
    'GenerationOperationResults', 'GenerationOperationHeatResults',
    # storage and reservoir operation
    'ESSOperationResults', 'ReservoirOperationResults',
    # sector-coupling network operation (hydrogen and heat)
    'NetworkH2OperationResults', 'NetworkHeatOperationResults',
    # electric network operation and map
    'NetworkOperationResults', 'NetworkMapResults',
    # marginal, cost-summary, and economic results
    'MarginalResults', 'CostSummaryResults', 'EconomicResults',
    # system summary, flexibility, and reliability
    'OperationSummaryResults', 'FlexibilityResults', 'ReliabilityResults',
]
