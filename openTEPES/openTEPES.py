"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 16, 2026
"""

# import dill as pickle
import datetime
import json
import os
import time

from   pyomo.environ import ConcreteModel, Param, Binary, NonNegativeIntegers

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the relative imports below have no parent package;
# fall back to absolute package imports in that case.
try:
    from          .openTEPES_InputData                  import InputData
    from          .openTEPES_DataConfiguration          import DataConfiguration
    from          .openTEPES_SettingUpVariables         import SettingUpVariables
    from          .openTEPES_InputSource                import open_source
    from          .openTEPES_ModelFormulationObjective  import TotalObjectiveFunction
    from          .openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation, InvestmentHydroModelFormulation, InvestmentH2ModelFormulation, InvestmentHeatModelFormulation
    from          .openTEPES_ProblemSolvingStageIter    import StageIterativeSolving
    from          .openTEPES_ModelFormulationAC        import ACRestorationPass
    from          .openTEPES_OutputResultsRawDump       import OutputResultsParVarCon
    from          .openTEPES_OutputResultsInvestment    import InvestmentResults
    from          .openTEPES_OutputResultsGeneration    import GenerationOperationResults, GenerationOperationHeatResults
    from          .openTEPES_OutputResultsStorage       import ESSOperationResults, ReservoirOperationResults
    from          .openTEPES_OutputResultsHydrogen      import NetworkH2OperationResults
    from          .openTEPES_OutputResultsHeat          import NetworkHeatOperationResults
    from          .openTEPES_OutputResultsNetwork       import NetworkOperationResults, NetworkMapResults
    from          .openTEPES_OutputResultsAC            import ACRelaxationDiagnostic, ACNetworkOperationResults, ACMarginalResults
    from          .openTEPES_OutputResultsEconomic      import MarginalResults, CostSummaryResults, EconomicResults
    from          .openTEPES_OutputResultsSummary       import OperationSummaryResults, FlexibilityResults, ReliabilityResults
    from          .openTEPES_OutputResultsSink          import ResultSink, set_active_sink, clear_active_sink
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputData                  import InputData
    from openTEPES.openTEPES_DataConfiguration          import DataConfiguration
    from openTEPES.openTEPES_SettingUpVariables         import SettingUpVariables
    from openTEPES.openTEPES_InputSource                import open_source
    from openTEPES.openTEPES_ModelFormulationObjective  import TotalObjectiveFunction
    from openTEPES.openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation, InvestmentHydroModelFormulation, InvestmentH2ModelFormulation, InvestmentHeatModelFormulation
    from openTEPES.openTEPES_ProblemSolvingStageIter    import StageIterativeSolving
    from openTEPES.openTEPES_ModelFormulationAC        import ACRestorationPass
    from openTEPES.openTEPES_OutputResultsRawDump       import OutputResultsParVarCon
    from openTEPES.openTEPES_OutputResultsInvestment    import InvestmentResults
    from openTEPES.openTEPES_OutputResultsGeneration    import GenerationOperationResults, GenerationOperationHeatResults
    from openTEPES.openTEPES_OutputResultsStorage       import ESSOperationResults, ReservoirOperationResults
    from openTEPES.openTEPES_OutputResultsHydrogen      import NetworkH2OperationResults
    from openTEPES.openTEPES_OutputResultsHeat          import NetworkHeatOperationResults
    from openTEPES.openTEPES_OutputResultsNetwork       import NetworkOperationResults, NetworkMapResults
    from openTEPES.openTEPES_OutputResultsAC            import ACRelaxationDiagnostic, ACNetworkOperationResults, ACMarginalResults
    from openTEPES.openTEPES_OutputResultsEconomic      import MarginalResults, CostSummaryResults, EconomicResults
    from openTEPES.openTEPES_OutputResultsSummary       import OperationSummaryResults, FlexibilityResults, ReliabilityResults
    from openTEPES.openTEPES_OutputResultsSink          import ResultSink, set_active_sink, clear_active_sink


# Output categories selectable via --results CLI flag. Keys map to the pIndXxxResults flags inside openTEPES_run.
OUTPUT_CATEGORIES = ("investment", "generation", "ess", "reservoir", "h2", "heat", "flexibility", "reliability", "network", "acnetwork", "acdiag", "map", "summary", "cost", "marginal", "economic", "plots",)
# Aliases expanded inside openTEPES_run.
OUTPUT_ALIASES = {
    "none": (),                                              # sentinel-only — for inner-loop / feasibility-check solves
    # acdiag is the relaxation gap alone, two small files: it says whether the AC currents, losses and voltages mean anything, so it is never
    # optional. acnetwork is the eight hourly wide tables and stays out of the mode whose purpose is to be minimal.
    "min":  ("investment", "summary", "cost", "economic", "acdiag"),
    "full": OUTPUT_CATEGORIES,
}


DEFAULT_GZIP_PATTERNS = (
    "Generation", "Consumption", "Balance", "MarketResults", "Network",
)


# Single source of truth for output-writer dispatch in openTEPES_run. Each entry is (category_key, writer_fn, extra_args_keys, guard_fn) where:
#   - category_key matches a key in OUTPUT_CATEGORIES; the writer fires only when the corresponding _flags[category_key] is truthy.
#   - extra_args_keys is a tuple of names looked up in a per-run extras dict ("tech" -> pIndTechnologyOutput, "area" -> pIndAreaOutput, "plot" -> pIndPlotOutput).
#     They are spread after (DirName, CaseName, mTEPES, mTEPES) when calling writer_fn.
#   - guard_fn is None or a callable(mTEPES) -> bool. When non-None, it must return truthy for the writer to fire (used for model-state guards such
#     as `mTEPES.es` for ESSOperationResults).
# Order in the tuple is the dispatch order. Tiering preserved from PR #118: headline tables first, bulky hourly tables next, plots last. The raw
# parameter/variable/constraint dump (OutputResultsParVarCon) is gated by pIndDumpRawResults (not a CLI-selectable category) and stays special-cased in the dispatch loop.
OUTPUT_REGISTRY = (
    # --- headline tables (small, structural) ---
    ("investment",  InvestmentResults,              ("tech", "area", "plot"), None),
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
    ("acdiag",      ACRelaxationDiagnostic,         (),                       lambda m: m.pIndACPowerFlow()),
    ("acnetwork",   ACNetworkOperationResults,      (),                       lambda m: m.pIndACPowerFlow()),
    ("acnetwork",   ACMarginalResults,              (),                       lambda m: m.pIndACPowerFlow()),
    ("marginal",    MarginalResults,                ("plot",),                None),
    ("economic",    EconomicResults,                (        "area", "plot"), None),

    # --- plots (slow, not data-critical) ---
    ("map",         NetworkMapResults,              (),                       None),
)



def ValidateConfiguration(mTEPES, pIndCycleFlow):
    """Check every combination of options at once and report all of them together.

    Collected rather than raised one at a time on purpose. These checks used to sit apart from each other, so a case with
    three incompatible flags was told about one, fixed it, and was told about the next. The list below fits on a screen
    and can be worked through in a single pass.
    """
    pProblems = []

    if pIndCycleFlow and mTEPES.pIndACPowerFlow():
        pProblems.append('IndCycleFlow applies to the DC network model only and cannot be combined with IndACPowerFlow. '
                         'See doc/design/AC_OPF_Formulation_Choices.md section 4.')

    # Single-node mode fixes every vLineLosses to zero, and under AC that variable is tied to the exact loss 0.5*r*vCurr, so the fix drives vCurr to
    # zero and the current definition then drives P and Q to zero on every AC branch. The result is not "the network ignored" but "every node
    # islanded": load is met by ENS everywhere and nothing says why.
    if mTEPES.pIndBinSingleNode() and mTEPES.pIndACPowerFlow():
        pProblems.append('IndBinSingleNode ignores the network entirely and cannot be combined with IndACPowerFlow, which models it in detail. '
                         'Switch one of the two off.')

    # Variable TTC gives each branch a rating per load level. Under AC the thermal limit is written on vCurr from the STATIC pLineSmax, so the varying
    # ratings would be read in and then ignored; and a branch the case declared out of service would still carry reactive power and losses.
    if mTEPES.pIndVarTTC() and mTEPES.pIndACPowerFlow():
        pProblems.append('IndVarTTC cannot be combined with IndACPowerFlow: the AC thermal limit is written on the current from the static rating, '
                         'so per-load-level ratings would be silently ignored. See doc/design/AC_OPF_Implementation_Plan.md.')

    # PTDF pins vFlowElec to sum(pPTDF * vNetPosition) as a hard equality. Under AC the branch flow equations already determine vFlowElec, so the two
    # together over-determine it: infeasible if you are lucky, quietly wrong if not.
    if mTEPES.pIndPTDF() and mTEPES.pIndACPowerFlow():
        pProblems.append('IndPTDF is a DC network representation and cannot be combined with IndACPowerFlow: both determine the branch flows, and '
                         'together they over-determine them. Switch one of the two off.')

    # A PTDF matrix belongs to ONE topology. Computing it fixes that topology at build time, so a case that can change it invalidates the factors the
    # moment a decision differs from the assumption. Generation, storage and DC-link candidates are fine: none of them enter the susceptance matrix.
    if mTEPES.pIndPTDF() == 2 and mTEPES.lca:
        pOffenders = ', '.join('-'.join(la) for la in list(mTEPES.lca)[:5])
        pProblems.append(f'IndPTDF = 2 computes the factors for one fixed topology, and this case can change it: '
                         f'{len(mTEPES.lca)} AC line(s) are candidates or switchable ({pOffenders}'
                         f'{", ..." if len(mTEPES.lca) > 5 else ""}). Use IndPTDF = 1 and supply factors per load '
                         f'level, or remove the candidate and switchable AC lines.')

    if pProblems:
        raise ValueError('The options of this case cannot be combined:\n' + '\n'.join(f'  {i}. {t}' for i, t in enumerate(pProblems, 1)))


def ReportConfiguration(mTEPES):
    """Print the configuration the model RESOLVED to, not the one the case files appear to ask for.

    The two can differ, and when they do the run still finishes and still reports a solved case. IndACPowerFlow written
    into oT_Data_Parameter rather than oT_Data_Option used to build a full AC model whose reactive demand and shunt
    tables were never read: 1438 Mvar of load silently became zero, and only a warning marked it. The counts below are
    read back off the built model, so a table that did not arrive shows up as a zero here before the solve rather than
    as a puzzling result after it.
    """
    pAC = {0: 'DC', 1: 'AC, branch flow', 2: 'AC, bus injection (W space)', 3: 'AC, bus injection (rectangular)'}
    print('')
    print('Configuration                          ****')
    print(f'  network model                        ... {pAC.get(mTEPES.pIndACPowerFlow(), mTEPES.pIndACPowerFlow())}')

    if mTEPES.pIndACPowerFlow():
        pType = {0: 'SOCP relaxation', 1: 'piecewise linear', 2: 'exact non-linear'}
        print(f'  AC current definition                ... {pType.get(mTEPES.pIndACModelType(), mTEPES.pIndACModelType())}')
        print(f'  AC restoration pass                  ... {"on" if mTEPES.pIndACRestore() else "off"}')
        if mTEPES.pIndACPowerFlow() == 2:
            print(f'  loop condition (IndACCycle)          ... {"on" if mTEPES.pIndACCycle() else "off"}')
        pConv = {0: 'none', 1: 'line-commutated', 2: 'voltage-source'}
        print(f'  HVDC converters                      ... {pConv.get(mTEPES.pIndACConverter(), mTEPES.pIndACConverter())}')

        # the two AC-only tables, reported as what reached the model rather than as what the case directory holds
        pQd = sum(mTEPES.pReactiveDemand[k]() for k in mTEPES.psnnd) * 1e3 if hasattr(mTEPES, 'pReactiveDemand') else 0.0
        print(f'  reactive demand                      ... {pQd:.1f} Mvar over the horizon')
        if pQd == 0.0:
            print('  ### WARNING: an AC run with no reactive demand anywhere. Check that oT_Data_ReactiveDemand reached the model.')
        pSh = len(mTEPES.sh) if hasattr(mTEPES, 'sh') else 0
        pSw = len(mTEPES.shw) if hasattr(mTEPES, 'shw') else 0
        print(f'  bus shunt devices                    ... {pSh} ({pSw} switchable)')

    pSolve = {0: 'stages in parallel', 1: 'stages sequentially, LP file', 2: 'stages sequentially, in memory',
              3: 'stages by sensitivity analysis'}
    print(f'  problem                              ... {"complete" if mTEPES.pIndCompleteProblem() else "time Benders decomposition"}'
          f'{", sector Benders decomposition" if mTEPES.pIndSectorDecomposition() else ""}')
    print(f'  stage solving                        ... {pSolve.get(mTEPES.pIndSequentialSolving(), mTEPES.pIndSequentialSolving())}')
    print(f'  network losses                       ... {"on" if mTEPES.pIndBinNetLosses() else "off"}')
    print(f'  flow-based coupling (IndPTDF)        ... {"on" if mTEPES.pIndPTDF() else "off"}')
    # PTDF is a lossless representation: the loss constraints are skipped whenever it is on, so a case asking for both
    # gets no losses at all. That is not wrong, but it is not what the case asked for either, so say so.
    if mTEPES.pIndPTDF() and mTEPES.pIndBinNetLosses():
        print('  ### NOTE: IndPTDF is a lossless representation, so IndBinNetLosses is ignored and no losses are modelled.')
    pOn = [pName for pName, pFlag in (('variable TTC', mTEPES.pIndVarTTC()), ('hydro topology', mTEPES.pIndHydroTopology()),
                                      ('hydrogen', mTEPES.pIndHydrogen()), ('heat', mTEPES.pIndHeat()),
                                      ('single node', mTEPES.pIndBinSingleNode())) if pFlag]
    print(f'  other active features                ... {", ".join(pOn) if pOn else "none"}')
    print('')


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole,
                  *, output_spec=None, out_path=None, gzip_patterns=None, output_format="csv",
                  input_source=None):
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
        Fine-grained output toggles. Keys must be OUTPUT_CATEGORIES; values truthy/falsy. Overrides the pIndOutputResults default for any key
        explicitly set. None (default) preserves historical behavior.
    out_path : str | None, optional
        Directory to write all `oT_Result_*.csv` and `oT_Plot_*.html` to Default `None` → write into `<DirName>/<CaseName>` (historical).
    gzip_patterns : tuple[str, ...] | None, optional
        If set, every `oT_Result_<prefix>*.csv` whose `<prefix>` starts with any entry in `gzip_patterns` is gzip-compressed in place after all
        writers finish. Default `None` → no compression (historical). Pandas reads `.csv.gz` transparently; note that `.csv.gz` cannot be opened
        directly in Excel — users who inspect outputs in Excel should leave this disabled.
    output_format : {'csv', 'duckdb', 'both'}, optional
        Where the result tables go. ``'csv'`` (default) writes the historical ``oT_Result_*.csv`` files only. ``'duckdb'`` writes one
        ``oT_Results_<CaseName>.duckdb`` (one table per result) and no CSVs. ``'both'`` writes both. The same in-memory frame is written to each
        target, so the DuckDB copy is not re-read from the CSV. One DuckDB file per case keeps a parallel sweep single-writer-safe.
    input_source : InputSource | None, optional
        An already-open input source to read the case from, bypassing the ``(DirName, CaseName)`` path sniff. Used by the Mode B sweep
        (``openTEPES_Runner.run(mode="in-memory")``) to hand each worker a shared in-memory baseline plus an overlay. ``CaseName`` and ``DirName`` are
        taken from the source; pass ``out_path`` so per-worker results land in distinct directories. Default ``None`` preserves historical behaviour.
    """

    InitialTime = time.time()
    _RunStartedUtc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

    # If the caller pointed at a .duckdb file (CaseName carries the suffix), open it as a DuckDBSource; InputData reads tables from this source instead of
    # from disk. CSV cases get a CSVSource later inside InputData (or here if we want to keep the source object on the model from the start).
    _db_input_origin_dir = None
    _input_source = None
    if input_source is not None:
        # Mode B / direct injection: the caller supplies an already-open source (e.g. an InMemorySource carrying baseline frames + an overlay).
        # Skip the path sniff and read through it; take CaseName/DirName from the source so the log and output filename conventions stay stable.
        # The caller is expected to pass out_path so per-worker results do not collide on the shared baseline directory.
        _input_source = input_source
        CaseName = _input_source.case_name
        DirName  = getattr(_input_source, "dir_name", DirName) or DirName
    else:
        _input_path_candidate = os.path.join(DirName, CaseName)
        if os.path.isfile(_input_path_candidate) and _input_path_candidate.endswith(".duckdb"):
            _db_input_origin_dir = os.path.dirname(os.path.abspath(_input_path_candidate))
            _input_source = open_source(_input_path_candidate)
            # The (DirName, CaseName) pair still drives output paths and per-run log filenames downstream. Use the DB's parent dir and its embedded
            # case name to keep those file conventions stable.
            DirName  = _db_input_origin_dir
            CaseName = _input_source.case_name

    _path = os.path.join(DirName, CaseName)
    # Effective output directory — used by every function in OutputResults via the _outdir() helper. None means "use case input dir" (historical).
    # For DuckDB inputs without an explicit out_path, default to the parent directory of the .duckdb file (the case dir under it does not exist).
    if out_path:
        _OutPath = out_path
    elif _db_input_origin_dir is not None:
        _OutPath = _db_input_origin_dir
    else:
        _OutPath = _path
    if out_path or _db_input_origin_dir is not None:
        os.makedirs(_OutPath, exist_ok=True)

    #%% replacing string values by numerical values
    # the integer keys also match their float spellings (0.0, 1.0): Python hashes 0.0 as 0 and 1.0 as 1, so no separate float entries are needed
    idxDict        = dict()
    idxDict[0    ] = 0
    idxDict[1    ] = 1
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
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.18RC - August 07, 2026')
    # In DuckDB-input mode _path may not exist on disk (the case lives in the DB, not in a directory). Ensure the version-log target exists.
    os.makedirs(_path, exist_ok=True)
    print(                 'Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.18.18RC - August 07, 2026', file=open(f'{_path}/openTEPES_version_{CaseName}.log','w'))
    if _input_source is not None:
        mTEPES.pInputSource = _input_source

    # direct lookup instead of a linear scan; an unknown value used to die with a bare IndexError, now it names the offending value and the accepted ones
    try:
        pIndOutputResults = idxDict[pIndOutputResults]
        pIndLogConsole    = idxDict[pIndLogConsole   ]
    except KeyError as e:
        raise ValueError(f'### Invalid Yes/No option value {e.args[0]!r} for pIndOutputResults or pIndLogConsole; accepted values: {list(idxDict)}') from None

    mTEPES.pBdTol = 1e-6

    # Reading sets and parameters. InputData also stores dfs/par on mTEPES (mTEPES.dFrame / mTEPES.dPar) for backward compatibility,
    # but DataConfiguration takes them explicitly to avoid that coupling.
    dfs, par = InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # How the problem is SOLVED, as opposed to what is modelled. These four were literals in this file until now, so a
    # case could not select any of them: the four stage-solving strategies below were all implemented and none reachable.
    # The defaults are the values that used to be hard-coded, so a case that says nothing behaves exactly as before.
    pIndCycleFlow           = par['pIndCycleFlow']
    pIndSectorDecomposition = par['pIndSectorDecomposition']
    pIndCompleteProblem     = par['pIndCompleteProblem']
    pIndSequentialSolving   = par['pIndSequentialSolving']
    mTEPES.pIndSectorDecomposition = Param(initialize=pIndSectorDecomposition, within=Binary,             doc='Sector Benders decomposition: 0 complete problem, 1 by sector', mutable=True)
    mTEPES.pIndCompleteProblem     = Param(initialize=pIndCompleteProblem,     within=Binary,             doc='Solve the complete problem: 0 by time decomposition, 1 complete', mutable=True)
    # NOT Binary: StageSolve branches on 0 parallel, 1 sequential with an LP file, 2 sequential in memory and
    # 3 sensitivity analysis. Declaring it Binary made two of its own strategies impossible to select.
    mTEPES.pIndSequentialSolving   = Param(initialize=pIndSequentialSolving,   within=NonNegativeIntegers, doc='Stage solving: 0 parallel, 1 sequential LP file, 2 sequential in memory, 3 sensitivity', mutable=True)

    # Define sets and parameters
    DataConfiguration(mTEPES, dfs, par)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # The cycle formulation is a way of eliminating vTheta from the DC model: it deletes eKirchhoff2ndLaw1/2 and imposes sum(x*flow) = 0 around each
    # independent cycle instead. Under the AC model those constraints are never built, so CycleConstraints would try to delete components that do not
    # exist. The AC analogue of the loop condition is sum(arctan(vWS/vWC)) = 0, which is non-convex and is handled by the tangent bounds plus the
    # Phase 7 restoration instead. Refuse the combination rather than fail obscurely deep in the stage loop.
    ValidateConfiguration(mTEPES, pIndCycleFlow)

    ReportConfiguration(mTEPES)

    # first/last stage
    FirstST = 0
    for st in mTEPES.st:
        if FirstST == 0:
            FirstST = 1
            mTEPES.First_st = st
        mTEPES.Last_st = st

    # objective function and investment constraints
    TotalObjectiveFunction             (mTEPES, mTEPES, pIndLogConsole)
    # shc/sqc carry the AC reactive candidates. Their cost terms live inside eTotalFElecCost, so a case whose only expansion is a shunt or a
    # synchronous condenser needs this block built too — otherwise the objective has no fixed-cost term at all and the devices come out free.
    if mTEPES.gc or mTEPES.gd or mTEPES.lc or mTEPES.rn or mTEPES.pc or mTEPES.hc or mTEPES.shc or mTEPES.sqc:
        InvestmentElecModelFormulation (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydroTopology() and mTEPES.rn:
        InvestmentHydroModelFormulation(mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHydrogen()      and mTEPES.pc:
        InvestmentH2ModelFormulation   (mTEPES, mTEPES, pIndLogConsole)
    if mTEPES.pIndHeat()          and mTEPES.hc:
        InvestmentHeatModelFormulation (mTEPES, mTEPES, pIndLogConsole)

    # initialize parameter for dual variables
    mTEPES.pDuals = {}

    # iterative formulation and solve for every stage of the year. The per-stage operation model and the two solve paths (deterministic per scenario,
    # or one joint stochastic solve) live in openTEPES_ProblemSolvingStageIter; this is a pure extraction, so results are unchanged.
    StageIterativeSolving(mTEPES, DirName, CaseName, SolverName, pIndLogConsole, _path, pIndCycleFlow)

    # The relaxed AC optimum is a LOWER bound on the true one, and how much lower depends entirely on whether the cone came out tight. This pass holds
    # the plan the relaxed solve produced and re-solves the network at the exact equality, so the reported operating point satisfies the AC equations.
    # It runs on ipopt regardless of the solver used above, because no mixed-integer solver takes the non-convex equality.
    if mTEPES.pIndACPowerFlow() and mTEPES.pIndACRestore():
        ACRestorationPass(mTEPES, mTEPES, 'ipopt', pIndLogConsole)

    # pickle the case study data with open(dump_folder+f'/oT_Case_{CaseName}.pkl','wb') as f:
    #     pickle.dump(mTEPES, f, pickle.HIGHEST_PROTOCOL)

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 2

    # output results just for the system (0) or for every area (1). Areas usually correspond to countries
    pIndAreaOutput = 1

    # indicators to control the number of output results
    pIndDumpRawResults = 0
    if pIndOutputResults:
        # --result Yes  → full output suite
        _flags = {k: 1 for k in OUTPUT_CATEGORIES}
    else:
        # --result No   → minimal (investment + summary + cost + economic, no plots)
        _flags = {k: 0 for k in OUTPUT_CATEGORIES}
        for k in ("investment", "summary", "cost", "economic", "acdiag"):
            _flags[k] = 1

    # Override with fine-grained output_spec if given (--results CLI flag).
    if output_spec:
        for k, v in output_spec.items():
            if k in OUTPUT_CATEGORIES:
                _flags[k] = 1 if v else 0

    # Only pIndPlotOutput is still read directly (via _extras below); every other output category is dispatched straight from _flags through OUTPUT_REGISTRY.
    pIndPlotOutput                  = _flags["plots"]

    # Tell OutputResults functions where to write (used by _outdir helper). Setting on mTEPES avoids changing 14 function signatures.
    mTEPES.pOutputPath = _OutPath
    mTEPES.pOutputBackend = output_format

    # Output results to CSV files. Dispatched via OUTPUT_REGISTRY (defined at module top): each entry fires when its category flag is truthy AND
    # its model-state guard (if any) returns truthy. Registry order is the dispatch order — headlines first, bulky hourly tables next, plots last (per PR #118).
    _OutputStart = time.time()

    # Raw parameter/variable/constraint dump is gated by pIndDumpRawResults (hardcoded, not a CLI category), so it stays a pre-loop special case.
    if pIndDumpRawResults:
        OutputResultsParVarCon            (DirName, CaseName, mTEPES, mTEPES)

    _extras = {
        "tech": pIndTechnologyOutput,
        "area": pIndAreaOutput,
        "plot": pIndPlotOutput,
    }
    # When DuckDB output is requested, install a per-case sink the .oT accessor routes every result write through. 'csv' leaves no sink, so the accessor
    # falls back to plain to_csv and the run is byte-identical to before. The sink is opened here (in this worker, after any fork) and closed below.
    _result_sink = None
    if output_format != "csv":
        _result_sink = ResultSink(_OutPath, CaseName, fmt=output_format)
        set_active_sink(_result_sink)
    try:
        for _key, _fn, _extra_keys, _guard in OUTPUT_REGISTRY:
            if not _flags[_key]:
                continue
            if _guard is not None and not _guard(mTEPES):
                continue
            _fn(DirName, CaseName, mTEPES, mTEPES, *(_extras[k] for k in _extra_keys))
    finally:
        if _result_sink is not None:
            _result_sink.close()
            clear_active_sink()

    # Optional post-write gzip pass. Rewrite every oT_Result_<prefix>*.csv whose <prefix> matches one of the requested patterns as .csv.gz.
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

    # Run-status sentinel JSON — small machine-readable record of this run. Let's downstream tools detect a fresh run and read top-level adequacy / cost numbers without parsing CSVs.
    _OutputSeconds = time.time() - _OutputStart
    _TotalSeconds  = time.time() - InitialTime
    _SolveSeconds  = max(_TotalSeconds - _OutputSeconds, 0.0)
    try:
        _TotalCost = float(mTEPES.eTotalSCost.expr() if hasattr(mTEPES, "eTotalSCost") else getattr(mTEPES, "vTotalSCost", lambda: float("nan"))())
    except Exception:
        _TotalCost = float("nan")
    # ENS in MWh and HUE in hours — system-wide totals. vENS is in GW (the model's internal power unit), so
    # GW x h is converted to MWh with a factor 1e3. Cheap to compute (one pass over vENS); skipped silently if the variable / index set is missing.
    _EnsMwh = float("nan")
    _HueH   = float("nan")
    try:
        if hasattr(mTEPES, "vENS") and hasattr(mTEPES, "psnnd"):
            _ens_psn = {}  # (p,sc,n) -> sum_nd vENS[p,sc,n,nd]
            for p,sc,n,nd in mTEPES.psnnd:
                _ens_psn[(p,sc,n)] = _ens_psn.get((p,sc,n), 0.0) + float(mTEPES.vENS[p,sc,n,nd]())
            _ens_mwh = 0.0
            _hue_h   = 0.0
            for (p,sc,n), val in _ens_psn.items():
                _dur = float(mTEPES.pLoadLevelDuration[p,sc,n]())
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
        "opentepes_version":  "4.18.18RC",
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
