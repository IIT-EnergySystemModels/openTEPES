"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 11, 2026
"""

# import dill as pickle
import datetime
import json
import math
import os
import time

import pyomo.environ as pyo
from   pyomo.environ import ConcreteModel, Set

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_InputData         import InputData
    from .openTEPES_DataConfiguration import DataConfiguration
    from .openTEPES_SettingUpVariables import SettingUpVariables
    from .openTEPES_InputSource      import open_source
    from .openTEPES_ModelFormulationObjective  import TotalObjectiveFunction
    from .openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation, InvestmentHydroModelFormulation, InvestmentH2ModelFormulation, InvestmentHeatModelFormulation
    from .openTEPES_ProblemSolvingStageIter import StageIterativeSolving
    from .openTEPES_OutputResultsRawDump        import OutputResultsParVarCon
    from .openTEPES_OutputResultsInvestment     import InvestmentResults
    from .openTEPES_OutputResultsGeneration     import GenerationOperationResults, GenerationOperationHeatResults
    from .openTEPES_OutputResultsStorage        import ESSOperationResults, ReservoirOperationResults
    from .openTEPES_OutputResultsHydrogen       import NetworkH2OperationResults
    from .openTEPES_OutputResultsHeat           import NetworkHeatOperationResults
    from .openTEPES_OutputResultsNetwork        import NetworkOperationResults, NetworkMapResults
    from .openTEPES_OutputResultsEconomic       import MarginalResults, CostSummaryResults, EconomicResults
    from .openTEPES_OutputResultsSummary        import OperationSummaryResults, FlexibilityResults, ReliabilityResults
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputData         import InputData
    from openTEPES.openTEPES_DataConfiguration import DataConfiguration
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables
    from openTEPES.openTEPES_InputSource      import open_source
    from openTEPES.openTEPES_ModelFormulationObjective  import TotalObjectiveFunction
    from openTEPES.openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation, InvestmentHydroModelFormulation, InvestmentH2ModelFormulation, InvestmentHeatModelFormulation
    from openTEPES.openTEPES_ProblemSolvingStageIter import StageIterativeSolving
    from openTEPES.openTEPES_OutputResultsRawDump        import OutputResultsParVarCon
    from openTEPES.openTEPES_OutputResultsInvestment     import InvestmentResults
    from openTEPES.openTEPES_OutputResultsGeneration     import GenerationOperationResults, GenerationOperationHeatResults
    from openTEPES.openTEPES_OutputResultsStorage        import ESSOperationResults, ReservoirOperationResults
    from openTEPES.openTEPES_OutputResultsHydrogen       import NetworkH2OperationResults
    from openTEPES.openTEPES_OutputResultsHeat           import NetworkHeatOperationResults
    from openTEPES.openTEPES_OutputResultsNetwork        import NetworkOperationResults, NetworkMapResults
    from openTEPES.openTEPES_OutputResultsEconomic       import MarginalResults, CostSummaryResults, EconomicResults
    from openTEPES.openTEPES_OutputResultsSummary        import OperationSummaryResults, FlexibilityResults, ReliabilityResults
# from openTEPES_SectorDecomposition import SectorDecomposition


# Output categories selectable via --results CLI flag.
# Keys map to the pIndXxxResults flags inside openTEPES_run.
OUTPUT_CATEGORIES = ("investment", "generation", "ess", "reservoir", "h2", "heat", "flexibility", "reliability", "network", "map", "summary", "cost", "marginal", "economic", "plots",)
# Aliases expanded inside openTEPES_run.
OUTPUT_ALIASES = {
    "none": (),                                              # sentinel-only — for inner-loop / feasibility-check solves
    "min":  ("investment", "summary", "cost", "economic"),
    "full": OUTPUT_CATEGORIES,
}


DEFAULT_GZIP_PATTERNS = (
    "Generation", "Consumption", "Balance", "MarketResults", "Network",
)


# Single source of truth for output-writer dispatch in openTEPES_run.
# Each entry is (category_key, writer_fn, extra_args_keys, guard_fn) where:
#   - category_key matches a key in OUTPUT_CATEGORIES; the writer fires only
#     when the corresponding _flags[category_key] is truthy.
#   - extra_args_keys is a tuple of names looked up in a per-run extras dict
#     ("tech" -> pIndTechnologyOutput, "area" -> pIndAreaOutput,
#      "plot" -> pIndPlotOutput). They are spread after (DirName, CaseName,
#     mTEPES, mTEPES) when calling writer_fn.
#   - guard_fn is None or a callable(mTEPES) -> bool. When non-None, it must
#     return truthy for the writer to fire (used for model-state guards such
#     as `mTEPES.es` for ESSOperationResults).
# Order in the tuple is the dispatch order. Tiering preserved from PR #118:
# headline tables first, bulky hourly tables next, plots last. The raw
# parameter/variable/constraint dump (OutputResultsParVarCon) is gated by
# pIndDumpRawResults (not a CLI-selectable category) and stays special-cased
# in the dispatch loop.
OUTPUT_REGISTRY = (
    # --- headline tables (small, structural) ---
    ("investment",  InvestmentResults,              ("tech", "plot"),         None),
    ("cost",        CostSummaryResults,             (),                       None),
    ("summary",     OperationSummaryResults,        (),                       None),
    ("reliability", ReliabilityResults,             (),                       None),
    ("flexibility", FlexibilityResults,             (),                       None),

    # --- bulky hourly tables ---
    ("generation",  GenerationOperationResults,     ("tech", "area", "plot"), None),
    ("generation",  GenerationOperationHeatResults, ("tech", "area", "plot"), lambda m: bool(m.ch and m.pIndHeat)),
    ("ess",         ESSOperationResults,            ("tech", "area", "plot"), lambda m: bool(m.es)),
    ("reservoir",   ReservoirOperationResults,      ("tech", "plot"),         lambda m: bool(m.rs and m.pIndHydroTopology)),
    ("h2",          NetworkH2OperationResults,      (),                       lambda m: bool(m.pa and m.pIndHydrogen)),
    ("heat",        NetworkHeatOperationResults,    (),                       lambda m: bool(m.ha and m.pIndHeat)),
    ("network",     NetworkOperationResults,        (),                       None),
    ("marginal",    MarginalResults,                ("plot",),                None),
    ("economic",    EconomicResults,                ("area", "plot"),         None),

    # --- plots (slow, not data-critical) ---
    ("map",         NetworkMapResults,              (),                       None),
)


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole,
                  *, output_spec=None, out_path=None, gzip_patterns=None):
    """Solve and write results.

    Parameters
    ----------
    DirName, CaseName, SolverName : str
        Standard openTEPES arguments.
    pIndOutputResults : 'Yes' / 'No' / 0 / 1
        Coarse-grained switch (kept for backward compatibility).
    pIndLogConsole : 'Yes' / 'No' / 0 / 1
        Verbose solver / formulation logging.
    output_spec : dict[str, bool] | None, optional
        Fine-grained output toggles. Keys must be OUTPUT_CATEGORIES; values
        truthy/falsy. Overrides the pIndOutputResults default for any key
        explicitly set. None (default) preserves historical behaviour.
    out_path : str | None, optional
        Directory to write all `oT_Result_*.csv` and `oT_Plot_*.html` to.
        Default `None` → write into `<DirName>/<CaseName>` (historical).
    gzip_patterns : tuple[str, ...] | None, optional
        If set, every `oT_Result_<prefix>*.csv` whose `<prefix>` starts with
        any entry in `gzip_patterns` is gzip-compressed in place after all
        writers finish. Default `None` → no compression (historical). Pandas
        reads `.csv.gz` transparently; note that `.csv.gz` cannot be opened
        directly in Excel — users who inspect outputs in Excel should leave
        this disabled.
    """

    InitialTime = time.time()
    _RunStartedUtc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

    # If the caller pointed at a .duckdb file (CaseName carries the
    # suffix), open it as a DuckDBSource; InputData reads tables from
    # this source instead of from disk. CSV cases get a CSVSource later
    # inside InputData (or here if we want to keep the source object on
    # the model from the start).
    _db_input_origin_dir = None
    _input_path_candidate = os.path.join(DirName, CaseName)
    _input_source = None
    if os.path.isfile(_input_path_candidate) and _input_path_candidate.endswith(".duckdb"):
        _db_input_origin_dir = os.path.dirname(os.path.abspath(_input_path_candidate))
        _input_source = open_source(_input_path_candidate)
        # The (DirName, CaseName) pair still drives output paths and per-run
        # log filenames downstream. Use the DB's parent dir and its embedded
        # case name to keep those file conventions stable.
        DirName  = _db_input_origin_dir
        CaseName = _input_source.case_name

    _path = os.path.join(DirName, CaseName)
    # Effective output directory — used by every function in OutputResults via
    # the _outdir() helper. None means "use case input dir" (historical).
    # For DuckDB inputs without an explicit out_path, default to the parent
    # directory of the .duckdb file (the case dir under it does not exist).
    if out_path:
        _OutPath = out_path
    elif _db_input_origin_dir is not None:
        _OutPath = _db_input_origin_dir
    else:
        _OutPath = _path
    if out_path or _db_input_origin_dir is not None:
        os.makedirs(_OutPath, exist_ok=True)

    #%% replacing string values by numerical values
    idxDict        = dict()
    idxDict[0    ] = 0
    idxDict[0.0  ] = 0
    idxDict[0.0  ] = 0
    idxDict['No' ] = 0
    idxDict['NO' ] = 0
    idxDict['no' ] = 0
    idxDict['N'  ] = 0
    idxDict['n'  ] = 0
    idxDict['Yes'] = 1
    idxDict['YES'] = 1
    idxDict['yes'] = 1
    idxDict['Y'  ] = 1
    idxDict['y'  ] = 1

    #%% model declaration
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.17RC - June 5, 2026')
    # In DuckDB-input mode _path may not exist on disk (the case lives in
    # the DB, not in a directory). Ensure the version-log target exists.
    os.makedirs(_path, exist_ok=True)
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.17RC - June 5, 2026', file=open(f'{_path}/openTEPES_version_{CaseName}.log','w'))
    if _input_source is not None:
        mTEPES.pInputSource = _input_source

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # introduce cycle flow formulations in DC and AC load flow
    pIndCycleFlow = 0

    # sector decomposition to get proxy of the hydrogen sector: 0 to solve the complete problem, 1 to solve sector decomposition
    pIndSectorDecomposition = 0
    mTEPES.pIndSectorDecomposition = pIndSectorDecomposition

    # Reading sets and parameters. InputData also stores dfs/par on
    # mTEPES (mTEPES.dFrame / mTEPES.dPar) for backward compatibility,
    # but DataConfiguration takes them explicitly to avoid that coupling.
    dfs, par = InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # Define sets and parameters
    DataConfiguration(mTEPES, dfs, par)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # first/last stage
    FirstST = 0
    for st in mTEPES.st:
        if FirstST == 0:
            FirstST = 1
            mTEPES.First_st = st
        mTEPES.Last_st = st

    # objective function and investment constraints
    TotalObjectiveFunction             (mTEPES, mTEPES, pIndLogConsole)
    if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc) + len(mTEPES.hc):
        InvestmentElecModelFormulation (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydroTopology and mTEPES.rn:
        InvestmentHydroModelFormulation(mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydrogen      and mTEPES.pc:
        InvestmentH2ModelFormulation   (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHeat          and mTEPES.hc:
        InvestmentHeatModelFormulation (mTEPES, mTEPES, pIndLogConsole)

    # initialize parameter for dual variables
    mTEPES.pDuals = {}

    # iterative formulation and solve for every stage of the year. The per-stage operation model and the two
    # solve paths (deterministic per scenario, or one joint stochastic solve) live in
    # openTEPES_ProblemSolvingStageIter; this is a pure extraction, so results are unchanged.
    StageIterativeSolving(mTEPES, DirName, CaseName, SolverName, pIndLogConsole, _path, pIndCycleFlow)

    # pickle the case study data
    # with open(dump_folder+f'/oT_Case_{CaseName}.pkl','wb') as f:
    #     pickle.dump(mTEPES, f, pickle.HIGHEST_PROTOCOL)

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 2

    # output results just for the system (0) or for every area (1). Areas correspond usually to countries
    pIndAreaOutput = 1

    # indicators to control the number of output results
    pIndDumpRawResults                  = 0
    if pIndOutputResults:
        # --result Yes  → full output suite
        _flags = {k: 1 for k in OUTPUT_CATEGORIES}
    else:
        # --result No   → minimal (investment + summary + cost + economic, no plots)
        _flags = {k: 0 for k in OUTPUT_CATEGORIES}
        for k in ("investment", "summary", "cost", "economic"):
            _flags[k] = 1

    # Override with fine-grained output_spec if given (--results CLI flag).
    if output_spec:
        for k, v in output_spec.items():
            if k in OUTPUT_CATEGORIES:
                _flags[k] = 1 if v else 0

    pIndInvestmentResults           = _flags["investment"]
    pIndGenerationOperationResults  = _flags["generation"]
    pIndESSOperationResults         = _flags["ess"]
    pIndReservoirOperationResults   = _flags["reservoir"]
    pIndNetworkH2OperationResults   = _flags["h2"]
    pIndNetworkHeatOperationResults = _flags["heat"]
    pIndFlexibilityResults          = _flags["flexibility"]
    pIndReliabilityResults          = _flags["reliability"]
    pIndNetworkOperationResults     = _flags["network"]
    pIndNetworkMapResults           = _flags["map"]
    pIndOperationSummaryResults     = _flags["summary"]
    pIndCostSummaryResults          = _flags["cost"]
    pIndMarginalResults             = _flags["marginal"]
    pIndEconomicResults             = _flags["economic"]
    pIndPlotOutput                  = _flags["plots"]

    # Tell OutputResults functions where to write (used by _outdir helper).
    # Setting on mTEPES avoids changing 14 function signatures.
    mTEPES.pOutputPath = _OutPath

    # Output results to CSV files. Dispatched via OUTPUT_REGISTRY (defined
    # at module top): each entry fires when its category flag is truthy AND
    # its model-state guard (if any) returns truthy. Registry order is the
    # dispatch order — headlines first, bulky hourly tables next, plots
    # last (per PR #118).
    _OutputStart = time.time()

    # Raw parameter/variable/constraint dump is gated by pIndDumpRawResults
    # (hardcoded, not a CLI category), so it stays a pre-loop special case.
    if pIndDumpRawResults:
        OutputResultsParVarCon            (DirName, CaseName, mTEPES, mTEPES)

    _extras = {
        "tech": pIndTechnologyOutput,
        "area": pIndAreaOutput,
        "plot": pIndPlotOutput,
    }
    for _key, _fn, _extra_keys, _guard in OUTPUT_REGISTRY:
        if not _flags[_key]:
            continue
        if _guard is not None and not _guard(mTEPES):
            continue
        _fn(DirName, CaseName, mTEPES, mTEPES, *(_extras[k] for k in _extra_keys))

    # Optional post-write gzip pass. Rewrite every oT_Result_<prefix>*.csv
    # whose <prefix> matches one of the requested patterns as .csv.gz.
    # Pandas reads .csv.gz transparently; Excel does not.
    _GzipFiles  = 0
    _GzipMbSaved = 0.0
    if gzip_patterns:
        import gzip as _gz
        import shutil as _shutil
        _patterns = tuple(gzip_patterns)
        for _fn in os.listdir(_OutPath):
            if not (_fn.startswith("oT_Result_") and _fn.endswith(".csv")):
                continue
            _stem = _fn[len("oT_Result_"):]
            if not any(_stem.startswith(_p) for _p in _patterns):
                continue
            _src = os.path.join(_OutPath, _fn)
            _src_size = os.path.getsize(_src)
            _dst = _src + ".gz"
            with open(_src, "rb") as _fi, _gz.open(_dst, "wb") as _fo:
                _shutil.copyfileobj(_fi, _fo)
            _dst_size = os.path.getsize(_dst)
            os.remove(_src)
            _GzipFiles  += 1
            _GzipMbSaved += (_src_size - _dst_size) / (1024 * 1024)

    # Run-status sentinel JSON — small machine-readable record of this run.
    # Lets downstream tools detect a fresh run and read top-level adequacy /
    # cost numbers without parsing CSVs.
    _OutputSeconds = time.time() - _OutputStart
    _TotalSeconds  = time.time() - InitialTime
    _SolveSeconds  = max(_TotalSeconds - _OutputSeconds, 0.0)
    try:
        _TotalCost = float(mTEPES.eTotalSCost.expr() if hasattr(mTEPES, "eTotalSCost")
                           else getattr(mTEPES, "vTotalSCost", lambda: float("nan"))())
    except Exception:
        _TotalCost = float("nan")
    # ENS in MWh and HUE in hours — system-wide totals. vENS is in GW (the model's internal power unit), so
    # GW x h is converted to MWh with a factor 1e3. Cheap to compute (one pass over vENS); skipped silently
    # if the variable / index set is missing.
    _EnsMwh = float("nan")
    _HueH   = float("nan")
    try:
        if hasattr(mTEPES, "vENS") and hasattr(mTEPES, "psnnd"):
            _ens_psn = {}  # (p, sc, n) -> sum_nd vENS[p,sc,n,nd]
            for p, sc, n, nd in mTEPES.psnnd:
                _ens_psn[(p, sc, n)] = _ens_psn.get((p, sc, n), 0.0) + float(mTEPES.vENS[p, sc, n, nd]())
            _ens_mwh = 0.0
            _hue_h   = 0.0
            for (p, sc, n), val in _ens_psn.items():
                _dur = float(mTEPES.pLoadLevelDuration[p, sc, n]())
                _ens_mwh += val * _dur * 1e3
                if val > 0:
                    _hue_h += _dur
            _EnsMwh = round(_ens_mwh, 4)
            _HueH   = round(_hue_h,   4)
    except Exception:
        pass
    status = {
        "case":               CaseName,
        "dir":                DirName,
        "out":                _OutPath,
        "status":             "optimal",
        "total_cost_meur":    _TotalCost,
        "ens_mwh":            _EnsMwh,
        "hue_h":              _HueH,
        "solve_seconds":      round(_SolveSeconds,  2),
        "output_seconds":     round(_OutputSeconds, 2),
        "total_seconds":      round(_TotalSeconds,  2),
        "solver":             SolverName,
        "backend":            getattr(mTEPES, "pOutputBackend", "csv"),
        "opentepes_version":  "4.18.17RC",
        "run_started_utc":    _RunStartedUtc,
        "run_finished_utc":   datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
        "outputs_enabled":    [k for k, v in _flags.items() if v],
        "gzip_patterns":      list(gzip_patterns) if gzip_patterns else None,
        "gzip_files":         _GzipFiles,
        "gzip_mb_saved":      round(_GzipMbSaved, 2),
    }
    with open(os.path.join(_OutPath, f'openTEPES_run_status_{CaseName}.json'), 'w') as _f:
        json.dump(status, _f, indent=2)

    # Close the DuckDB connection if we opened one.
    if _input_source is not None:
        _input_source.close()

    return mTEPES
