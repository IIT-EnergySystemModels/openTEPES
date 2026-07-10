# Change Log

## [4.18.17RC] - 2026-07-09 Unreleased in PyPI

- [CHANGED] update InputData docs: the CSV<->DuckDB converter tools now exist (drop the "planned" note), with the bundled `9n` DuckDB example.
- [FIXED] fix syntactic errors in time Benders decomposition modules
- [FIXED] fix syntactic errors in openTEPES_ModelFormulationElectricity
- [CHANGED] change OutputResultsNetwork and OutputResultsEconomic for reducing execution time
- [FIXED] fix vNetworkInvPer at the same time that vNetworkInvest to avoid having vNetworkInvPer as binary variables when there are relaxed investments
- [ADDED] two figures on the multiple-runs page: a concept diagram of the three modes as a reuse matrix over the pipeline, and a Mode B flow diagram drawn against the shipped `openTEPES_Runner` / `openTEPES_Cases` API. Static images in `doc/img/`; no code change.
- [CHANGED] retitled the sweep page to "Multiple runs" (the code still calls a related set of runs a sweep) and expanded each mode with its mechanics — backends and the status-JSON round-trip for Modes A/B, the mutable-Param `store_values` hot-swap and non-persistent-solver requirement for Mode C. Fixed the Mode C note: the shipped `resolve` loop is serial and cross-platform, not Unix-only (fork copy-on-write belongs to Mode B's multiprocessing backend).
- [ADDED] a "Solver interface: persistent vs non-persistent" section in SolutionMethods: which solver names use the persistent Gurobi path (`appsi_gurobi` / `gurobi_persistent`) versus the non-persistent default, where reuse pays off (the stage loop and the Benders / dual re-solves), why Mode C must stay non-persistent, and examples.
- [ADDED] DuckDB data-management examples: querying a per-case `oT_Results_<case>.duckdb` and the swept `oT_Sweep.duckdb` in OutputResults, and inspecting a `.duckdb` input case in InputData (noting that openTEPES reads but does not yet create input DuckDB files).
- [ADDED] CSV<->DuckDB input converter tools (`scripts/openTEPES_DuckDB/`): `Tool_CSV_to_DuckDB` writes a CSV case to a `.duckdb`, `Tool_DuckDB_to_CSV` exports it back. Both are driven by `openTEPES_InputSchema` and reuse the DuckDB reader, so they cannot drift.
- [CHANGED] documentation: new Read the Docs page for parameter sweeps (Modes A/B/C via `openTEPES_Runner` + `openTEPES_Cases` and `resolve`). Document the `output_format` DuckDB result output and the `aggregate` sweep merger in OutputResults, the `.duckdb` input option and the integer form of the Yes/No flags in InputData, and Benders decomposition in Characteristics. No model or behaviour change.
- [ADDED] a CI `docs` job builds the Read the Docs site with warnings treated as errors, so a broken cross-reference or a missing toctree entry fails the PR; `conf.py` silences only the project's front-matter convention warning.
- [FIXED] CI on the sector/stage Benders commit. `openTEPES_ProblemSolvingStageSolve.py` called the cycle-flow builders through an undefined `oTM` alias with undefined flags; it now calls `NetworkCycles` and `CycleConstraints` directly, like the stage iterator (DC cycle path). `openTEPES_ProblemSolvingSectorDecomposition.py` and `openTEPES_ProblemSolvingStageDecomposition.py` now use the same relative-import guard as the other split modules, so they import both when installed and when run as a script.
- [ADDED] added sector and stage Benders decomposition
- [CHANGED] if a thermal unit has a variable minimum generation > 0 in a load level it is considered committed in this load level
- [CHANGED] fix the energy activation variables if no operating reserve activation constraint is formulated in a time step
- [ADDED] Mode B in-memory overlay sweep (RFC §4.2): `openTEPES_Runner.run(mode="in-memory")` reads the baseline case once into a new `openTEPES_InMemorySource` and re-uses it per case through an overlay (a data-table stem mapped to a scale factor, a `df->df` callable, or a replacement frame), so a parameter sweep pays the input I/O once and only rebuilds + solves per case (forked workers share the baseline copy-on-write). `openTEPES_run` gains `input_source=` to read from an already-open `InputSource`; `InputSource` gains `list_dict_stems()` (implemented in `CSVSource` and `DuckDBSource`). Additive only — an identity overlay reproduces a direct run (9n parity). New tests in `tests/test_run.py`. The architecture diagram's sweep-modes panel now marks all three modes (A, B, C) implemented.
- [FIXED] the twelve technology- and consumption-level operating-reserve result writers in `openTEPES_OutputResultsGeneration.py` used plain `to_csv`, so they bypassed the result sink and were missing from the DuckDB output. They now use `.oT.write` like every other writer, so the DuckDB file has one table per result CSV again (fixes `test_output_format_both_csv_parity`).
- [CHANGED] change names of the operating reserve file results
- [ADDED] DuckDB result output and a sweep merger (`openTEPES_OutputResultsSink.py` + `openTEPES_ResultAggregate.py`), the output-side mirror of the DuckDB input source. `openTEPES_run` gains `output_format` (`"csv"` default / `"duckdb"` / `"both"`); with DuckDB on, each case also writes one `oT_Results_<case>.duckdb` (one table per result) straight from the in-memory frame. A pandas `oT` accessor routes every writer's `.oT.write(path, ...)` through the sink; with no sink it is plain `to_csv`, so a `"csv"` run is byte-identical (output parity on 9n / 9n_heat / 9n_H2). One DuckDB per case keeps a sweep single-writer-safe. `aggregate(sources, out_path, to=...)` stacks a sweep's cases into one long table per result with a leading `case` column, reading the per-case DuckDBs or CSV folders, and writes `oT_Sweep_<Table>.csv` and/or one `oT_Sweep.duckdb`. `openTEPES_Runner.run` exposes both as opt-in `output_format` / `aggregate_to`. New tests in `tests/test_run.py`.
- [FIXED] formulation of eOperReserveUpEnergy and eOperReserveDwEnergy constraints
- [FIXED] failure in plotting up and down operating reserve marginals when the constraint has not been formulated
- [ADDED] Mode A pre-build sweep runner (`openTEPES_Runner.py` + `openTEPES_Cases.py`): `run(cases, solver_name, backend=...)` runs many cases through `openTEPES_run`, one independent build-and-solve per case, over a `serial` (default), `multiprocessing`, or `joblib` backend. A `Case` names one input source (a CSV directory or a `.duckdb` file) plus an optional output directory and label. The runner reads back each case's `openTEPES_run_status_*.json` and returns one summary dict per case in input order, so nothing has to pickle the Pyomo model across workers; a case that raises is captured as `status="error"` instead of aborting the sweep. Additive only — no existing module changes, and a single-case serial sweep reproduces a direct `openTEPES_run`. Mode B (in-memory overlay) and Mode C (`openTEPES_ProblemSolvingResolve`) are separate. New tests in `tests/test_run.py`. The architecture diagram (`doc/img/openTEPES_architecture.svg` and the rendered `.png`) marks the `runner.py` and `cases.py` boxes implemented, and also the `resolve.py` box now that Mode C has merged.
- [ADDED] add CSV output file TechnologyInvestment per area 
- [CHANGED] change eOperReserveUpEnergy and eOperReserveDwEnergy to system-wide constraints, instead of area constraints
- [CHANGED] fix some errors in writing H2 and heat network output results
- [FIXED] `setup_solver` no longer crashes on Windows when an earlier in-process solve still holds the stale log file open.
- [FIXED] deprecated `datetime.utcnow()` replaced with timezone-aware UTC; emitted timestamp unchanged.
- [ADDED] Mode C post-build hot-swap re-solve (`openTEPES_ProblemSolvingResolve.py`): `resolve(OptModel, SolverName, overlays)` re-solves a built model once per parameter overlay without rebuilding, so a sweep reuses the single slow build; `overlay_scaled` makes a scale-factor overlay. Overlays apply relative to the baseline, which is restored at the end. Only `mutable=True` Params hot-swap, so the operational set (`pDemandElec`, `pENSCost`, `pLinearVarCost`, `pEFOR`, `pReserveMargin`, `pRESEnergy`) is promoted to mutable and read by call in the build-time guards; structural and topology Params stay immutable. No behaviour change: 9n solves bit-identical (164.382043867 MEUR, `PYTHONHASHSEED=0`). New test `test_mode_c_resolve_demand_hot_swap`.
- [CHANGED] split the ~2900-line `openTEPES_InputData.py` into three modules at the package root, one per model-build step — the input-side counterpart of the earlier Formulation, Solver and Output splits, and the last of the three mega-file splits. `openTEPES_InputData.py` keeps `InputData`, which reads the raw sets and parameters from the case source (a CSV directory or a DuckDB file). The new `openTEPES_DataConfiguration.py` holds `DataConfiguration`, which builds the derived and instrumental sets and the flag-driven branches (hydro topology, hydrogen, heat, PTDF). The new `openTEPES_SettingUpVariables.py` holds `SettingUpVariables`, which creates the decision variables and their bounds, fixes the generators' commitment, relaxes or forbids investment conditions, zeroes out epsilon values, and screens for infeasibilities. `openTEPES.py` imports each function from its own module, and `__init__.py` re-exports all three, so a user who imported `DataConfiguration` or `SettingUpVariables` from `openTEPES.openTEPES_InputData` moves to the matching module (e.g. `...DataConfiguration`). This is a pure move — the three functions are byte-identical to before, checked function by function, and none of them calls another — so results do not change: the whole solve test suite passes with the same locked costs. The two new modules import only pandas and Pyomo (no sibling `openTEPES` modules), so they need no relative-import guard; `tests/test_direct_run.py` still runs them as scripts like every other module. This finishes the Layer-3 model-build split from the architecture RFC. Separating set construction from parameter construction inside `InputData` (groundwork for the planned overlay and mutable-parameter work) is function surgery rather than a pure move and is left for its own later change.
- [CHANGED] document every bundled case on the Download & Installation page (`doc/md/Download.md`). The list now covers all ten cases under `openTEPES/cases/`, not just seven: the three 9-node variants that were missing are added — `9n_PTDF` (the 9-node case solved with the PTDF network formulation instead of the angle-based DC power flow), `9n_heat` (the 9-node case coupled with a heat network), and `9n_H2` (the 9-node case coupled with a hydrogen network) — and the `sSEP` entry now notes it also includes a hydrogen network. Each entry says in one line what makes the case different, so a new user can pick the right starting point.
- [CHANGED] split the ~1770-line `openTEPES_ModelFormulation.py` into six per-concern modules at the package root — the formulation-side counterpart of the earlier Input, Solver and Output splits. The two cross-sector concerns are `openTEPES_ModelFormulationObjective.py` (the total-cost objective and the per-stage operation-cost accumulation) and `openTEPES_ModelFormulationInvestment.py` (the four investment builders plus the installed-capacity, adequacy-reserve-margin and emission / RES-energy limits). Each energy sector then gets its own module: `openTEPES_ModelFormulationElectricity.py` (demand balance, operating reserves and inertia, storage, unit commitment, ramping, line switching, DC network operation and the cycle constraints), `openTEPES_ModelFormulationHydro.py` (reservoir water balance), `openTEPES_ModelFormulationHydrogen.py` (H2 network) and `openTEPES_ModelFormulationHeat.py` (heat network). The old `openTEPES_ModelFormulation.py` is removed: `openTEPES.py` imports the objective and investment builders from their modules, `openTEPES_ProblemSolvingStageIter.py` imports the per-stage operation builders, and `__init__.py` re-exports all six (so `from openTEPES.openTEPES_ModelFormulation import ...` users move to the concern module — e.g. `...Investment`). This is a pure move — the 19 builder functions are byte-identical to before, checked function by function — so results do not change: the whole solve test suite passes with the same locked costs. Keeping each sector in one file, with its existing granular per-constraint functions inside, is the groundwork for selectable formulations later (for example a DC vs AC network build, or unit commitment on or off) chosen by which functions the stage driver calls. The new modules use the descriptive-docstring convention of the other split modules; the standalone test `tests/test_heat_investment_typo.py` now imports `InvestmentHeatModelFormulation` from `...Investment`.
- [CHANGED] update the architecture diagram (`doc/img/openTEPES_architecture.svg` and the rendered `.png`) to show the new `openTEPES_ProblemSolvingStageIter.py` as an implemented (green) box in the solver layer, alongside `ProblemSolving`, `Tuning`, `DualExtraction`, `Persistent` and `Benders`; `resolve.py` stays white as the one solver module still planned. The seven boxes are re-spaced to fit the layer's existing width — no other layer changes.
- [ADDED] a test (`tests/test_direct_run.py`) that runs every `openTEPES_*.py` module as a script (via `runpy`, with `__name__ == "__main__"`) to check that each one still imports cleanly that way — i.e. the `try`/`except ImportError` relative-import guard's fallback works. A normal `import openTEPES` only ever takes the relative-import path, so until now nothing checked the fallback; a broken guard, a missing import, or a circular import in any module would only surface when a user runs the file directly (VS Code "Run Python File"). The test solves no model, so it runs in the fast CI job; it excludes `openTEPES_Main.py`, which has a real `__main__` block that would launch the command-line interface.
- [CHANGED] move the per-stage solve loop out of `openTEPES_run` into a new module `openTEPES_ProblemSolvingStageIter.py`. The `(period, scenario, stage)` loop — which activates one stage's load levels, builds that stage's operation constraints, and calls `ProblemSolving` — now lives in a function `StageIterativeSolving`, together with the post-loop work that rebuilds the full stage and load-level sets, reactivates every constraint, and restores the scenario probabilities. `openTEPES.py` still builds the objective and the investment constraints, sets `First_st` / `Last_st` and the empty `pDuals`, and then calls the new driver. The two solve paths are unchanged: a deterministic solve per scenario when there are no expansion decisions and no system emission or RES-energy limit, and one joint stochastic solve at the last period-scenario otherwise. This is a pure move — the loop body is copied unchanged — so results do not change: the whole solve test suite passes with the same locked costs, and a full-output run of case 9n gives the same total cost (252.20132998 MEUR, matching to 13 significant figures; only the per-unit dispatch tables move, by the amount HiGHS already varies run-to-run when it picks among equally optimal storage schedules). The new module uses the same `try`/`except ImportError` relative-import guard as the other split modules, so "Run Python File" still works on it. This continues the solver-layer split (after the Persistent, Tuning and DualExtraction modules) and gives the later re-solve and decomposition drivers a single place to call the stage loop from.
- [CHANGED] split the ~2800-line `openTEPES_OutputResults.py` into per-concern modules at the package root — the output-side counterpart of the earlier `openTEPES_Input*` and `openTEPES_ProblemSolving*` splits. The result writers now live in `openTEPES_OutputResultsInvestment.py`, `...Generation.py`, `...Storage.py`, `...Hydrogen.py` (hydrogen network), `...Heat.py` (heat network), `...Network.py` (electricity network and map), `...Economic.py` (marginal, cost-summary, economic), `...Summary.py` (system summary, flexibility, reliability), and `...RawDump.py` (the raw parameter/variable/constraint DuckDB dump). Shared pieces sit in `openTEPES_OutputResultsCommon.py` (the output-directory helper and the three Altair plot builders) and `openTEPES_OutputResultsMapCommon.py` (the flow-series and snapshot-period helpers the three network maps had each copied). The old `openTEPES_OutputResults.py` is removed: `__init__.py` and `openTEPES.py` import the result functions from the concern modules directly, the same way the Input and ProblemSolving splits are wired (no re-export facade). Functions are grouped by topic; the dispatch order is still controlled by `OUTPUT_REGISTRY` in `openTEPES.py` and is unchanged. Every cross-module import uses the same `try`/`except ImportError` relative-import guard as the other split modules, so "Run Python File" works. Verified bit-identical with the output parity tool on case 9n (`PYTHONHASHSEED=0`, all 87 result tables; total cost 164.382043867 MEUR). Two small cleanups made while moving the code: removed 34 no-op `"".join([f"..."])` wrappers (each is just the f-string) and stopped `ESSOperationResults` from writing its inventory-utilization scaling back into `mTEPES.pMaxStorage` (the denominator is now computed locally, so the scaled value no longer leaks to later reads of the parameter).
- [ADDED] a `9n_H2` example case (the hydrogen counterpart of `9n_heat`): the minimal 9-node electricity system plus two electrolyzers, hydrogen demand at three nodes, and a hydrogen pipe network. Added to the single-stage CI solve suite in `tests/test_run.py` (expected cost 259.547 MEUR under the 7-day HiGHS fixture, verified deterministic across reruns), so CI exercises the hydrogen result writer (`NetworkH2OperationResults`) directly on a small fast case rather than only through `sSEP`. Output verified bit-identical before and after the sector-coupling module split, for both CSV and DuckDB inputs.
- [FIXED] two operating-reserve guards in the marginal and economic results read a leaked loop variable. The down-reserve-marginal guard and the up-reserve-revenue guard loop over storage units (`for ar,es in mTEPES.ar*mTEPES.es`) but checked `pIndOperReserveGen[nr]` / `pIndOperReserveCon[nr]` — `nr` only existed as a leftover from the earlier `for ar,nr ...` loop that builds the area-to-generator map. They now check the loop's own `es`, matching the two sibling guards (up-reserve-marginal, down-reserve-revenue) that were already correct. The down-reserve-revenue guard also read `pIndOperReserveGen[nr]` twice (`Gen ... or ... Gen`) where its siblings read `Gen ... or ... Con`; the second is now `Con`. On case 9n the result is unchanged; on a case where the leftover unit's reserve flags differ from the storage units' these guards now correctly decide which operating-reserve-revenue tables are written.
- [CHANGED] update the architecture diagram (`doc/img/openTEPES_architecture.svg`) so it matches the code. The old picture used the planned folder names (`io/`, `schema.py`, `solver/`, `solve.py`); it now shows the real flat module names (`openTEPES_InputSchema.py`, `openTEPES_ProblemSolving.py`, and so on), with the five real solver modules. Implemented modules are shaded green and planned ones are left white, with a small legend. Also commit a rendered `doc/img/openTEPES_architecture.png` and point the `README.md` at the PNG instead of the SVG, so the diagram shows on pages that do not display SVG (such as the PyPI project page). Added a short `doc/img/README.md` explaining the SVG is the hand-drawn source (there is no generator script), that the PNG is rendered from it, and how to regenerate the PNG on Windows, macOS and Linux.
- [FIXED] a binary investment problem (for example `IndBinNetInvest=1`) crashed under the HiGHS solver with `NoDualsError` on the first solve. `ProblemSolving` attaches the `dual` Suffix before the first solve only for a pure-LP model, because a mixed-integer problem has no duals; it then recovers the duals later by fixing the integer variables and re-solving as an LP. The check that decided "is this a pure LP" also required each variable to already have a value, but before the first solve no variable has a value yet, so a model with binary *investment* variables was wrongly treated as an LP, got the Suffix, and crashed when HiGHS was asked for duals it does not have. The check now looks only at whether a variable is integer/binary and unfixed, not at its value. Unit-commitment models did not hit this because their binary variables are given starting values. No change for any model that already worked.
- [ADDED] a test (`test_binary_investment` in `tests/test_run.py`) for a binary (integer) investment decision, which no other test covered — every other case solves the investment variables as a continuous relaxation. It switches on `IndBinNetInvest` for the `9n` case so the single candidate line becomes a {0,1} build-or-not decision; the cost (254.337 MEUR) differs from the continuous result (252.201 MEUR) because the binary decision forces a full line build. The test also guards the fix above. A companion fixture `case_7d_binary` runs the case from a private temporary copy (so its solver log files do not clash with the other 9n tests on Windows, where a log file can stay open after a solve), applies the 7-day truncation, and overrides one or more columns of the Option file.
- [CHANGED] split the CI workflow (`.github/workflows/ci.yml`) into two jobs to save time. A `fast` job runs the linter and the tests that do not solve a model, on all three operating systems and all three Python versions (3.11, 3.12, 3.13) — this is where import, packaging and Python-version problems show up. A `solve` job runs the full model test suite (every case, the multi-stage case, and Benders) once per operating system on Python 3.12, since the model results are the same on every Python version. Tests that solve a model are now marked with `@pytest.mark.solve` (registered in `pyproject.toml`); the `fast` job runs `-m "not solve"` and the `solve` job runs `-m solve`. Also added a per-test timeout on the solve job so a stuck solver fails quickly instead of using up the whole job, and turned on dependency caching for `uv`. No test was removed; the same tests still run, just spread across the two jobs.
- [ADDED] a tool to check that two runs produce the same result files: `openTEPES/_output_parity_test.py` (with tests in `tests/test_output_parity.py`). It is the output-side version of the existing `_input_parity_test.py`. You take a snapshot of all the `oT_Result_*.csv` files a run writes, then compare two snapshots: numbers are compared with a small tolerance, text labels exactly. Run it from the command line with `python -m openTEPES._output_parity_test snapshot <output_folder> <file.pkl>` and then `diff <a.pkl> <b.pkl>`. The purpose is to safely refactor the output code: a future change that reorganises `openTEPES_OutputResults.py` should still write identical result files, and this tool proves it. This change adds the tool only and does not affect any existing run.
- [CHANGED] allow finding the case in the same folder or in the cases folder 
- [FIXED] allow running `openTEPES_Main.py` directly (e.g. VS Code "Run Python File"). Executed as a script the file is `__main__` with an empty `__package__`, so the top-level `from .openTEPES import ...` relative import fails with `attempted relative import with no known parent package`. The import is now wrapped in a `try`/`except ImportError` that puts the repository root on `sys.path` and retries as an absolute package import. The relative import — the correct form for the PyPI-distributed package, used by the `openTEPES_Main` console script and `python -m openTEPES.openTEPES_Main` — stays the primary path and is unchanged, so installed / `-m` behaviour is byte-for-byte identical; the fallback only triggers on direct-script execution. The same module-level relative-import guard is applied to every other module that imports from sibling package modules at load time — `openTEPES.py`, `openTEPES_InputData.py`, `openTEPES_InputSource.py`, `openTEPES_InputCSVSource.py`, `openTEPES_InputDuckDBSource.py`, and `openTEPES_ProblemSolving.py` — so "Run Python File" on any of them no longer raises `attempted relative import with no known parent package`. The lazy backend imports inside `open_source()` and the package `__init__.py` are intentionally left as plain relative imports (they never execute at direct-run module-load time, and `__init__.py` only ever runs as part of the package).
- [CHANGED] untrack accidentally committed per-run status sentinels (`openTEPES/cases/{9n,9n_heat,sSEP}/openTEPES_[Rr]un_[Ss]tatus_*.json`, test-case workspace pollution; removed from the index, kept on disk) and extend `.gitignore` with the `openTEPES_[Rr]un_[Ss]tatus_*.json` pattern — the existing `oT_Run_Status_*.json` rule matched neither the `openTEPES_` prefix nor the lower-case `run_status` variant.
- [ADDED] architecture diagram in `README.md` (`doc/img/openTEPES_architecture.svg`) — visual summary of the six-layer package structure that PR #120 (`InputSource`), this PR (the flat `openTEPES_Input*` I/O modules + `openTEPES_ProblemSolving*` solver modules at the package root), and the planned RFC follow-on PRs (`Model`, `Formulation`, `Results`) build toward. Inserted before the "How to Cite" section under a new "Architecture" heading. Source diagram lives in the architecture RFC under `Docs/architecture/opentepes_architecture_proposal.md` (parent repo); the README embeds the rendered SVG only.
- [CHANGED] **BREAKING**: move every bundled case study from `openTEPES/<case>/` to `openTEPES/cases/<case>/`. The 9 cases (`9n`, `9n7y`, `9n_PTDF`, `9n_heat`, `NG2030`, `RTS-GMLC`, `RTS-GMLC_6y`, `RTS24`, `sSEP`) all live under the new `cases/` subfolder — the set packaged and distributed on PyPI. The Python package directory `openTEPES/` now holds all source modules at the top level (`openTEPES_*.py`, including the split-out `openTEPES_Input*` I/O and `openTEPES_ProblemSolving*` solver modules) plus the `cases/` data folder. The repository-root `cases/` folder (the larger paper/study cases `Optimal-Power-Grid-Design`, `TSO-DSO_coordination`, not packaged) is renamed to `case_studies/` so the two no longer collide on the name `cases`. CLI default in `openTEPES_Main.py` updated; `tests/test_run.py` fixture path updated; case URLs in `README.md` and `doc/md/Download.md` rewritten. **External users running `openTEPES_run(DirName="<path>/openTEPES", CaseName="9n")` or the CLI with `--dir <pkg>` must update their path to `<path>/openTEPES/cases`.** No backwards-compat shim — clean break, documented here.
- [CHANGED] split the input-source layer of `openTEPES_InputSource.py` into four single-responsibility modules at the package root — pure-pandas I/O, no Pyomo dependency. The module becomes `openTEPES_InputSchema.py` (TABLE_SPECS catalogue + transform-kind constants + DEFAULT_IDX_COLS, single source of truth used by every backend, the C2 ingest migrator, and the case-management CLI), `openTEPES_InputSource.py` (`InputSource` ABC + `open_source()` factory + post-read shape helpers `_apply_index` / `df_to_set_values`), `openTEPES_InputCSVSource.py` (`CSVSource`), and `openTEPES_InputDuckDBSource.py` (`DuckDBSource`; `duckdb` is lazily imported by `open_source()` only when a `.duckdb` path is opened, so CSV-only environments do not need the dependency). The split-out modules sit flat alongside the other `openTEPES_*.py` modules; the layer is encoded in the file name (`openTEPES_Input*` for the input-source layer), keeping the `openTEPES_<Layer>_<Concern>` convention of the rest of the package without a nested folder tree. The `open_source()` / `InputSource` / `CSVSource` / `DuckDBSource` / `TABLE_SPECS` names remain re-exported from the package top level (`from openTEPES import open_source`). Internal modules (`openTEPES.openTEPES_InputData`, `openTEPES.openTEPES`, `openTEPES._input_parity_test`) import from the specific flat modules. No behaviour change to existing pipelines. First step of the layered-architecture restructure.
- [CHANGED] extend the CI matrix in `tests/test_run.py`. Single-stage 7-day fixture now covers 6 cases (was 3): adds `9n_heat` (heat-sector code path, `pIndHeat=1`; expected cost 247.196 MEUR), `NG2030` (Nigeria 2030 baseline, multi-area state-level network; 1041.342 MEUR), `RTS-GMLC` (single-stage GMLC reference system; 1091.094 MEUR). A new multi-stage 7-day-per-stage fixture (`case_multi_stage_7d_system`) keeps the first 168 hours of *each* `(Period, Scenario, Stage)` group — leaving `StageWeight` as authored — and covers `9n7y` (13 stages × 4-week weight × 7 periods; 9019.299 MEUR), enabling the multi-stage rolling layout to receive CI coverage for the first time. A third test under the same single-stage fixture validates classical L-shaped Benders convergence on `9n` against the joint LP (relative error 5.78e-08, ~5 s under HiGHS). Expected costs locked at 7 significant figures; HiGHS reproducibility verified to ≥13 sig figs across multiple reruns for every case. `RTS24` was evaluated but excluded — three identical runs returned 1107.185, 1107.400, and 1110.174 (HiGHS non-determinism); coverage preserved indirectly through `RTS-GMLC`. `RTS-GMLC_6y` not yet parametrised — its multi-stage solve under HiGHS runs >10 minutes locally and needs CI-hardware profiling before merging; multi-stage fixture itself verified correct via `9n7y`. Hydrogen sector (sSEP: DemandHydrogen + NetworkHydrogen + 9 H2-related generators), water-reservoir hydropower (sSEP: 7 reservoirs + reservoir maps + inflows/outflows/MaxVolume + pumped hydro), and the rolling-mean time aggregation `pTimeStep ≥ 2` (every case) are now documented as already-covered code paths via an inline feature-coverage matrix in `test_run.py`. Full matrix wall-clock: single-stage block ~40 s, multi-stage block ~90 s, Benders block ~6 s.
- [CHANGED] split `openTEPES_ProblemSolving.py` into four single-responsibility modules at the package root per RFC §3 Layer 5.a: `openTEPES_ProblemSolvingPersistent.py` (the `appsi_gurobi` / `gurobi_persistent` lifecycle with the `ncall` state machine + `set_instance` / `update_config` toggles), `openTEPES_ProblemSolvingTuning.py` (per-solver option presets for Gurobi / CPLEX / HiGHS / GAMS; both initial-solve and fix-and-resolve LP-pass tunings), `openTEPES_ProblemSolvingDualExtraction.py` (fix-integers + fix-continuous-investments → re-solve as LP → walk every active constraint to copy duals into `mTEPES.pDuals`), and `openTEPES_ProblemSolving.py` (slim orchestrator that composes the three primitives + keeps the cost-summary print block for now — that moves to Layer 6 results in a follow-on PR). `from openTEPES import ProblemSolving` (or `from openTEPES.openTEPES_ProblemSolving import ProblemSolving`) continues to work. Internal imports updated. No behaviour change — all 10 CI tests pass bit-identical to pre-split. The split sets up the contract that future orchestration drivers (RFC PR #6 `openTEPES_ProblemSolvingStageIter.py`, PR #8 `openTEPES_ProblemSolvingResolve.py`, PR #9 `openTEPES_ProblemSolvingDecompositionBenders.py`) will use to access solver tuning and persistent-solver lifecycle uniformly; the existing `openTEPES_ProblemSolvingBenders.py` driver does NOT yet consume these primitives — it uses `SolverFactory` directly to keep the minimal-driver scope (RFC PR #9 will wire up the full coupling).
- [ADDED] solver layer (Layer 5 of the RFC restructure) with `openTEPES_ProblemSolvingBenders.py` at the package root — a classical L-shaped decomposition driver for transmission expansion. Master = `vNetworkInvest` decisions for every candidate line (`mTEPES.plc`); subproblem = the full openTEPES model with each candidate `vNetworkInvest` pinned to the master decision via an explicit equality `vNetworkInvest[k] == benders_x[k]` (mutable `Param`). The dual on each fixing constraint, read through `mTEPES.dual` Suffix, gives the Benders cut coefficient; master objective is `min theta` so the investment-cost term is captured implicitly through the cut. Validates on the bundled `9n` case under the 7-day fixture: joint LP returns 252.201330 MEUR, L-shaped converges in 8 iterations to 252.201345 MEUR (relative error 5.78e-08), wall-clock ~5 s under HiGHS. Acts as a **compatibility guard** for the layered-architecture restructure: every future refactor must keep `vNetworkInvest` cleanly separable as a master decision and the rest of the model usable as an LP subproblem with valid duals on the fixing constraint. Scope deliberately minimal — single deterministic case, no multi-cut, no trust region, no binary investments. The full driver with stochastic L-shaped and sector decomposition is RFC PR #9 (`openTEPES_ProblemSolvingDecomposition*`); this PR ships the infrastructure (the `openTEPES_ProblemSolving*` solver layer + dual-extraction pattern + Suffix wiring) that PR #9 will build on. Implementation note: `Var.fix()` + `rc` Suffix is not portable (HiGHS leaves `rc` empty); always use an explicit equality constraint with a mutable `Param` and read duals via the `dual` Suffix.
- [ADDED] `InputSource` abstraction (`openTEPES_InputSource.py`) so `openTEPES_run` accepts either a CSV case directory (historical default — byte-identical behaviour) or a `.duckdb` file produced by an external ingest script. DuckDB reads stream via SQL straight into DataFrames; no tempfiles. Selection sniffs the path: a directory routes through `CSVSource`, a `.duckdb` file routes through `DuckDBSource`. DuckDB is an optional dependency; the import is lazy. A `TABLE_SPECS` catalogue (67 entries) declares each input table once with its CSV stem, DB table name, transform kind, and key columns — covering single-level wide time series, the new multi-level-header tables (`VariableTTCFrw`/`Bck`, `VariablePTDF`), entity-config, and single-row global parameters. Verified bit-identical end-to-end (total objective rel err ≤ 1e-15) across 9n, sSEP, and 9n_PTDF.
- [CHANGED] drop `pyomo.environ.DataPortal` from `InputData`. The 22 `dictSets.load(format='set')` sites collapse to `Set(initialize=df_to_set_values(source.read_dict(stem)))` — pandas is the only CSV parser in the path. `set_definitions` gains an explicit per-entry `ordered` flag (replaces a hardcoded membership check); `SPECIAL_IDX_COLS` is removed in favour of declarative `pk_cols` in `TABLE_SPECS`; the reservoir/hydrogen/heat conditional loaders are a small declarative loop with the silent-skip semantics preserved (absent tables → empty Sets / unset feature flags; malformed tables now raise instead of being swallowed). `DataConfiguration` signature becomes `DataConfiguration(mTEPES, dfs=None, par=None)` with fallback to `mTEPES.dFrame` / `mTEPES.dPar` for backward compatibility; 639 `mTEPES.dPar[...]` / `mTEPES.dFrame[...]` reach-into-model sites swept to local `par[...]` / `dfs[...]`. CSV-mode behaviour is invariant.
- [FIXED] heat investment constraint `eTotalFHeatCost` referenced an undefined variable `vTotalHeatFCost` (typo); the variable is `vTotalFHeatCost`. Dormant because no in-tree case has a candidate heat pipe (`mTEPES.hc` always empty) — the `InvestmentHeatModelFormulation` call at `openTEPES.py:207-208` is gated by `mTEPES.pIndHeat and mTEPES.hc`. Adds a self-contained regression test in `tests/test_heat_investment_typo.py` that builds the minimum Pyomo state to exercise the formulation (no case directory, no solver call).
- [ADDED] `9n_heat` test case — the first in-tree case exercising the heat-sector code path (`pIndHeat=1`). Three heat units (air-source heat pump COP 3.0, gas boiler 92 % efficiency, backpressure gas CHP power-to-heat ≈ 0.71) and two heat pipes between Node_2 / Node_3 / Node_4 overlaid on the existing `9n` electricity topology. Parameter values inspired by ECEMF / NECP / ERAA reference scenarios — not real-system calibration. Smoke-tested under the existing 7-day CI fixture pattern: HiGHS terminates optimal in 0.4 s, `total_cost = 247.19623713906074 MEUR`, heat reliability cost = 0, 10 503 constraints / 14 504 variables. Closes the most severe gap identified in the heat-sector CI coverage audit.
- [ADDED] opt-in `--gzip-large-csvs` / `--gzip-patterns` CLI flags. After writing, every `oT_Result_*.csv` whose name (after the leading `oT_Result_`) starts with one of the configured prefixes is rewritten as `.csv.gz`. Default prefix set: `Generation, Consumption, Balance, MarketResults, Network`. Pandas reads `.csv.gz` transparently; Excel does not. Sentinel JSON gains `gzip_patterns`, `gzip_files`, `gzip_mb_saved`. Default behaviour unchanged.
- [CHANGED] reorder output writers in `openTEPES_run` so small KPI/structural tables (`InvestmentResults`, `CostSummaryResults`, `OperationSummaryResults`, `ReliabilityResults`, `FlexibilityResults`) are written before bulky hourly tables (Generation, ESS, Network, Marginal, Economic). HTML map plots run last. Resilient to mid-output interruptions: headline numbers from every solved case survive a kill/timeout/disk-full. No behavioural change beyond write order.
- [CHANGED] replace the 14 hardcoded `if pIndXxxResults: XxxResults(...)` dispatch blocks in `openTEPES_run` with a single `OUTPUT_REGISTRY` tuple at module top. Each entry is `(category_key, writer_fn, extra_args_keys, guard_fn)`; the dispatch is a 5-line loop. Registry order = dispatch order, preserving the previous (headline → bulky → plots) sequence. Pure refactor — no behavioural, signature, or argument change. Sets up future pluggable-backend work.
- [CHANGED] introduction of new optional files for the operating reserve activation as an alternative to the UpReserveActivation and DwReserveActivation parameters in Data_Parameter file
- [CHANGED] modify the change of the scenario probabilities to 1.0 if there are no investment decisions
- [FIXED] control of non-existing electrolyzer output in OutputResults module
- [FIXED] control of generator investments and retirements, and line investments in openTEPES.py
- [FIXED] write voltage angle only if existing in the optimization problem.
- [FIXED] fix Big-M coefficient for AC candidate disjunctive Kirchhoff voltage law (eKirchhoff2ndLaw1/2). DC and existing AC lines are unaffected.
- [ADDED] post-solve warning when the voltage-angle bound pMaxTheta = pi/2 is (nearly) binding.
- [CHANGED] changed the simplex strategy for highs and from appsi_highs to highs
- [CHANGED] changed the penalty for hydrogen surplus to 0.5 the cost of hydrogen not served
- [FIXED] fix case with multiple independent scenarios
- [CHANGED] updated usage of appsi_gurobi and gurobi_persistent solvers
- [CHANGED] detection of generators with minimum and maximum energy constraints

## [4.18.16] - 2026-04-10

- [CHANGED] add H2 network utilization in output results
- [FIXED] fix H2 and heat network map titles
- [CHANGED] clean up ProblemSolving module
- [FIXED] fix model formulation for some lines not available until certain year
- [CHANGED] introduced appsi_gurobi as solver
- [CHANGED] changed HiGHS options
- [CHANGED] detection of lines with same initial and final nodes
- [FIXED] fix computation of SRMC for hydrogen balance equation
- [CHANGED] added excess of hydrogen production penalized as hydrogen not served in the objective function

## [4.18.15] - 2026-02-23

- [CHANGED] cleanup model formulation, input data, and output results to improve readability and avoid unnecessary computations
- [CHANGED] separate H2 and heat constraints in functions to improve readability
- [FIXED] fix error in eKirchhoff2ndLaw1 and eKirchhoff2ndLaw2 to avoid formulating for nonexistent lines in a certain year
- [FIXED] fix eReserveUpIfEnergy and eReserveDwIfEnergy constraints
- [CHANGED] cleanup model formulation and input data to improve readability

## [4.18.14] - 2026-02-06

- [CHANGED] cleanup model formulation to avoid unnecessary computations and to improve readability
- [FIXED] error in output results for case RTS24
- [CHANGED] modify the generation inventory utilization for the candidate ESS to be wrt the invested storage capacity instead of the maximum storage capacity

## [4.18.13] - 2026-02-05

- [CHANGED] extensive use of a2g and t2g in input, model formulation, and output modules to avoid unnecessary computations and to improve readability
- [FIXED] errors in eMaxOutput2ndBlock and eMinOutput2ndBlock constraints when considering generators not available in some periods
- [CHANGED] detect lines with undefined nodes or circuits
- [CHANGED] detect technologies not declared in the technology dictionary
- [CHANGED] reduce interior point method tolerance for gurobi solver

## [4.18.12] - 2026-01-28

- [CHANGED] reduce computation time in output results

## [4.18.10] - 2026-01-25

- [CHANGED] avoid formulation of superfluous eTotalOutput constraints and fix additional vTotalOutput variable
- [FIXED] errors in writing results to duckdb database
- [CHANGED] clean up eMaxOutput2ndBlock and eMinOutput2ndBlock equations
- [FIXED] errors in eMaxOutput2ndBlock and eMinOutput2ndBlock equations
- [CHANGED] clean up some output results

## [4.18.9] - 2026-01-22

- [CHANGED] increase solution time limit for some solvers
- [FIXED] errors in OutputResults module for considering generators not available in some periods
- [CHANGED] add output results to DuckDB database

## [4.18.8] - 2026-01-19

- [CHANGED] detect error of ESS unit with maximum charge and no maximum storage
- [CHANGED] create output files for ramp revenues
- [CHANGED] modify eMaxOutput2ndBlock and eMinOutput2ndBlock to consider the ramp reserve provision
- [CHANGED] create eSystemRampUp and eSystemRampDw constraints to satisfy the system ramping capability
- [CHANGED] add the optional RampReserveUp and RampReserveDown input files to introduce ramping reserves per area
- [FIXED] add domain change for fixed binary variables to avoid failures in getting the duals
- [FIXED] fix the HiGHS behavior for getting dual variables
- [CHANGED] add the GenerationCapturedSRMC and ConsumptionCapturedSRMC output files
- [FIXED] control of load levels with 0 duration in psn and fix in OutputResults module
- [CHANGED] fix pandas warning in InputData module
- [CHANGED] added MarketResultsGenerationInvestment file
- [CHANGED] added LCOE and generation in the MarketResultsTechnologyInvestment file
- [CHANGED] added MarketResultsTechnologyInvestment file
- [CHANGED] added curtailment and emissions to MarketResultsGeneration file
- [CHANGED] reduce computation time in output results
- [CHANGED] generation time reduction in model formulation moving parameters out of the sums
- [FIXED] control of candidate generators not available in some periods in some investment constraints in model formulation and output results
- [FIXED] fix computation of LCOE.
- [FIXED] upper bound of line losses only if no single node option. With single node option losses are 0.

## [4.18.7] - 2025-11-22

- [CHANGED] extension to quarter of an hour resolution for the load levels
- [FIXED] fix TechnologyEmission outfile
- [CHANGED] modify names of some output results and avoid writing empty files
- [FIXED] fix eTotalECostArea constraint
- [CHANGED] introduce conditions to avoid formulating superfluous eMaximumEnergy and eMinimumEnergy constraints
- [FIXED] fix error in MarginalEmission output results
- [FIXED] control of transmission lines not available for all the periods
- [CHANGED] remove condition for load levels with duration 0 in ReserveXXIf constraints
- [FIXED] candidate must run unit behavior (i.e., committed if installed)
- [CHANGED] penalize network losses in the objective function to avoid losses with spillage/curtailment
- [FIXED] fix the computation of MWkm in output results
- [CHANGED] detection of minimum renewable energy requirement exceeds the demand
- [CHANGED] detection of all the lines have NTC zero probably due to security factor equal to zero
- [CHANGED] avoid formulating superfluous eMaxOutput2ndBlock and eMinOutput2ndBlock constraints
- [CHANGED] fix minimum stable time variables for units that don't have minimum stable time
- [CHANGED] remove parameter pRatedConstantVarCost
- [CHANGED] avoid formulating superfluous eTotalEmissionArea and eMinOutput2ndBlock constraints
- [CHANGED] no plots for no output results

## [4.18.6] - 2025-09-21

- [FIXED] fix bugs in InputData module
- [CHANGED] InputDate module refactored to split in several functions
- [FIXED] fix bug in Output Results computation of ramp surplus
- [FIXED] fix bug in Output Results when an Area has no non-RES generators
- [CHANGED] save all the output results in the mTEPES model object
- [FIXED] fix typo in BalancePerXXX output files
- [CHANGED] if the variable TTCFrw and TTBck are both very small (e.g., 0.000001), they are set to 0 and the line is considered open
- [FIXED] fix typo in TechnologySpillage output file
- [FIXED] fix typo in BalanceEnergy and MarketResultsGeneration output files

## [4.18.5] - 2025-06-23

- [CHANGED] add MarketResultsDemand and MarketResultsGeneration output files.
- [FIXED] Fix typo in reserve equations
- [CHANGED] change ESS inventory efficiency consideration from full value at consumption to square root at both consumption and generation.
- [FIXED] fix operating reserve constraints for ESSs and hydropower plants regarding if there is enough energy/water
- [CHANGED] add the ability to choose if an ESS provides reserves as a generator or a consumer independently
- [CHANGED] avoid formulation of superfluous vHydroOutflows variables
- [FIXED] fix error when displaying network losses by transmission line
- [FIXED] fix bug when a set of mutually exclusive generators has no generators
- [FIXED] fix bug when variable TTC is used and there are lines with reactance equal to 0
- [CHANGED] introduce variable TTC forward and backward for the transmission lines
- [CHANGED] add hourly mutually exclusive generators, generators can now be part of several mutually exclusive groups, exclusivity now applies to consumption too
- [FIXED] change from titleside to title_side in output results to adapt to the latest plotly version
- [CHANGED] add logfile for GAMS solver
- [FIXED] fix error in the cost summary per area files
- [FIXED] fix some errors in the output results
- [FIXED] don't initialize some variables
- [FIXED] don't fixed or count variables that have no value
- [CHANGED] change len(xxx) to xxx

## [4.18.4] - 2025-04-08

- [CHANGED] introduction of commitment for hydro units modeled in water units
- [FIXED] allow solving periods with no investment decisions independently in a multiyear case
- [FIXED] fix GenerationCostOperatingReserve output file
- [FIXED] deactivate constraints when solving for each period and scenario
- [FIXED] avoid solving all the periods and scenarios simultaneously if not needed
- [CHANGED] added GenerationConsumptionRatio output file
- [FIXED] error in some terms of the operation costs
- [FIXED] error in CostRecovery output file

## [4.18.3] - 2025-03-18

- [FIXED] error in pumping signs of the HydroInventory constraint
- [CHANGED] introduce operation costs in CostRecovery output file
- [CHANGED] avoid the introduction of all the nodes in demand and operating reserve input files
- [FIXED] add revenues of ESS generation and consumption operating reserves
- [CHANGED] change sign of the consumption energy and operating reserve revenues
- [FIXED] typo when computing charge revenues in output results
- [CHANGED] detection of units with no energy inflows and no consumption power
- [FIXED] avoid formulation of superfluous ramp or inventory constraints for ESS with no energy inflows and no consumption power
- [FIXED] don't formulate operating reserve constraints for ESS with no energy inflows and no consumption power
- [FIXED] detection of the first time step for each period, scenario, and stage
- [FIXED] decision on the unit commitment at the initial hour done by area instead of by system
- [FIXED] contribution of the operating reserve activation of a consumption unit to eChargeDischarge and eESSTotalCharge constraints
- [CHANGED] avoid warning when updating mTEPES.na
- [FIXED] typo in output results
- [FIXED] control of duration 0 in load levels if there is no period weight or scenario probability
- [CHANGED] default values when there are no StorageType, OutflowsType, or EnergyType to 1 instead of 8736
- [FIXED] minimum up/down time constraints
- [FIXED] units of the operating reserve constraint marginals
- [CHANGED] epsilon in eRampUpState/eRampDwState constraints moved to numerator

## [4.18.2] - 2025-01-31

- [FIXED] fix condition when ignoring investment decisions
- [FIXED] typo in emission condition
- [CHANGED] fixed emission limit calculation
- [CHANGED] detect no weights in periods and stages and abort the run
- [CHANGED] define GAMS (capital letters) as a solver
- [FIXED] fix error in eRampDw constraint
- [CHANGED] add FlexibilityNetwork output file

## [4.18.1] - 2024-12-19

- [CHANGED] add area in MarginalIncrementalVariableCost, MarginalIncrementalGenerator and GenerationIncrementalEmission output files
- [FIXED] fix error in eAdequacyReserveMarginHeat
- [FIXED] some epsilon for heat were wrong
- [CHANGED] add reserve margin for heat demand (new CSV file, and modifications related to it in input data, model formulation and output results)
- [CHANGED] computing pDemandHeatPeak in InputData
- [CHANGED] refactoring the energy to heat conversion

## [4.18.0] - 2024-12-04

- [CHANGED] in this version no need to introduce all the generators as headings of the variable max/min data files
- [FIXED] all the cases have been updated to this new version
- [FIXED] to improve model robustness the first cells of the heading row of all the Data files are filled with sensible headers. These changes are mandatory for this new version.
- [FIXED] first column of Parameter and Option files dropped
- [FIXED] minor changes in output results

## [4.17.9] - 2024-11-19

- [FIXED] fix error in network map
- [FIXED] fix error in computing cost recovery
- [FIXED] fix error in computing pDemandElecPeak in InputData
- [CHANGED] keep the model in memory
- [CHANGED] default values of minimum output results
- [CHANGED] concatenation of strings

## [4.17.8] - 2024-10-30

- [FIXED] fix control of second block capacity extremely small (1e-17)
- [FIXED] fix formulation of the minimum stable time constraints
- [CHANGED] name of the solver log file
- [FIXED] fix some typos in output results
- [FIXED] writing of the GenerationSurplusHeat file
- [FIXED] computation of pMaxPowerHeat
- [FIXED] computation of net demand per node in output results
- [CHANGED] if no ending year is given in the input data, the last year is considered year 3000
- [CHANGED] control of invalid electric lines, hydrogen lines, and heat pipelines
- [CHANGED] added colum of MEUR/year in cost summary files
- [CHANGED] added information regarding detected infeasibilities
- [FIXED] lower bound only for VRE units
- [FIXED] computation of curtailment in the output results for generation candidates

## [4.17.7] - 2024-09-20

- [CHANGED] redefinition of all sets, removing the order of the elements, and the lambda function to filter the elements

-[CHANGED] enabling assert of the objective function in the test run

## [4.17.5] - 2024-09-18

- [FIXED] avoid degeneracy when ordering generating units by increasing variable costs

## [4.17.4] - 2024-09-12

- [FIXED] avoid considering the hydro units as marginal incremental generators
- [CHANGED] split generation and consumption in ESS technologies
- [FIXED] fix error when solving by stages
- [FIXED] fix error in writing investment output results
- [CHANGED] introduce outflow incompatibility column in Data_Generation file

## [4.17.3] - 2024-07-19

- [CHANGED] introduce hourly outflows
- [FIXED] control of units not available in some years
- [FIXED] change when computing pStorageTotalEnergyInflows
- [FIXED] fixed writing reserve margin dual variables
- [FIXED] fixed creation of pyomo parameters stacking original data
- [FIXED] fixed disregarding load levels for timestep > 1 for many periods
- [CHANGED] restructured source code of InputData module
- [FIXED] fixed typo in stable state equation
- [FIXED] detection of electricity, heat and H2 lines/pipelines
- [CHANGED] introduced formulation of the minimum stable time constraints
- [CHANGED] add case RTS-GMLS expansion planning for 6 years with representative weeks
- [CHANGED] add case 9n expansion planning for 7 years with representative weeks
- [FIXED] control some divisions by zero due to pDuration
- [CHANGED] declare pDuration as NonNegativeIntegers

## [4.17.2] - 2024-05-30

- [FIXED] fix some heat output files
- [CHANGED] define chp as all the heat producers
- [FIXED] fix some investment output files
- [FIXED] fix some emission output files
- [CHANGED] considering emissions from heat generators

## [4.17.1] - 2024-05-21

- [CHANGED] add the NG2030 case study
- [CHANGED] time reduction in some output results
- [FIXED] fix errors in heat generator investments
- [FIXED] fix errors and add some heat results
- [CHANGED] add some heat generation output files
- [FIXED] fix error in heat boilers
- [CHANGED] introduction of cycle equations for DC power flow
- [CHANGED] fix error in writing the duals in output results

## [4.17.0] - 2024-05-10

- [CHANGED] add period and stage in Duration file to allow different durations for each stage in each period and scenario

## [4.16.1] - 2024-05-08

- [CHANGED] add some CPLEX options

## [4.16.0] - 2024-04-30

- [FIXED] delete eTotalNCost and vTotalNCost
- [CHANGED] delete investment and commitment reduced costs files
- [CHANGED] case saved as a pickle file
- [FIXED] fix computation of incremental variable cost of generators with surplus
- [FIXED] typo in pPeriodWeight definition
- [FIXED] typo in heat network flow magnitudes
- [CHANGED] introduced StableTime in Data_Generation file for nuclear unit operation
- [FIXED] introduce boiler expansion constraint eInstallBoiCap
- [CHANGED] introduced ProductionFunctionH2ToHeat in Data_Generation file for boilers that produce heat with hydrogen
- [CHANGED] changed ProductionFunction to ProductionFunctionHydro in Data_Generation file
- [FIXED] fix binary variables to obtain dual variables only those of the corresponding period and scenario
- [FIXED] initial equal to final inventory in candidate ESS or reservoir
- [CHANGED] introduction of boilers to produce heat
- [FIXED] control of max power greater than min power
- [FIXED] delete pMacCapacity in some inventory constraints
- [FIXED] fix several errors in hydro reservoir modeling
- [FIXED] fix several errors in heat modeling
- [CHANGED] avoid some computations is converting small parameters to 0
- [CHANGED] add curtailment in summary generation file
- [CHANGED] introduction of HiGHS options and as default solver
- [CHANGED] introduction of StableTime in Data_Generation for nuclear units
- [CHANGED] introduction of MinimumPowerHeat/MaximumPowerHeat in Data_Generation for CHP units
- [CHANGED] inventories/reservoir volumes are no longer fixed to their initial value at the end of every storage type cycle

## [4.15.8] - 2024-03-12

- [FIXED] check calls of mutable parameters
- [FIXED] change sign of water/energy values
- [FIXED] fix sign of dual variable of equality constraints
- [FIXED] fix some errors in cases with no renewables
- [CHANGED] fix some future warnings in output results

## [4.15.7] - 2024-02-27

- [FIXED] fix variable fuel cost and variable emission cost
- [FIXED] fix typo en H2 and heat balance equations
- [CHANGED] tighten formulation of second charge/discharge block
- [CHANGED] added a epsilon penalty in the o.f. to ohmic losses to avoid losses with spillage/curtailment
- [FIXED] initialization of the set of load levels up to the current stage
- [CHANGED] if initial inventory is out of bounds, fix it to the closest bound
- [CHANGED] detect reserve margin feasibility
- [CHANGED] reserve margin constraint is not formulated if there are no candidate generation units
- [CHANGED] time reduction in outputting results
- [CHANGED] add a small tolerance to avoid pumping/charging with curtailment/spillage
- [FIXED] clean up output results module
- [FIXED] change in the system inertia constraint
- [FIXED] introduction of line availability in electricity, H2, and heat balance equations
- [CHANGED] split total generation in different technologies in balance results
- [FIXED] introduction of line availability in electricity, H2, and heat balance equations
- [CHANGED] not all the stages must have the same duration
- [FIXED] computation of fixed costs for several years
- [FIXED] change some performance issues in ESS operation results
- [CHANGED] flexibility to consider generating units not for all the periods
- [FIXED] introduce initial inventory as a variable for ESS candidates
- [CHANGED] clean up of dynamic sets to avoid the use of static sets
- [FIXED] typo in dual variable of reserve margin constraint
- [FIXED] include minimum reservoir volume
- [FIXED] modify the condition to delete set na
- [FIXED] don't fix the storage of ESS candidates to its initial storage in any cycle
- [FIXED] fix the initial storage of ESS candidates to its maximum storage
- [FIXED] fix error in system emission constraint
- [CHANGED] clean up of s2n in formulation
- [FIXED] consistency of heat units
- [FIXED] fix error for stages with duration 0
- [CHANGED] add minimum RES energy in Data_RESEnergy file to consider minimum RES energy production
- [CHANGED] scale eMinSystemRESEnergy to GW instead of GWh
- [CHANGED] add MarginalRESEnergy output file to consider the marginal RES energy production

## [4.15.6] - 2024-01-25

- [CHANGED] some typos

## [4.15.5] - 2024-01-25

- [FIXED] fix error in output results with multiple
- [CHANGED] add column ProductionFunctionHeat in Data_Generation file to consider heat production of generators
- [CHANGED] add column HTNSCost in Data_Parameter file to consider heat not served cost
- [CHANGED] add column IndBinNetHeatInvest in Data_Option file to consider binary or not heat network investment decisions

## [4.15.4] - 2024-01-18

- [FIXED] fix error when some scenarios have prob 0

## [4.15.3] - 2024-01-16

- [CHANGED] move the computation of storage total energy inflows to reduce computation time
- [CHANGED] avoid the use of last in computing duals

## [4.15.2] - 2024-01-15

- [FIXED] allow solving just one period out of several defined
- [CHANGED] split variable definition and bound assignment
- [CHANGED] simplify the dual variables computation

## [4.15.1] - 2023-12-27

- [CHANGED] avoid some future warnings in output results

## [4.15.0] - 2023-12-27

- [CHANGED] introduce the variable emission cost file

## [4.14.12] - 2023-12-20

- [CHANGED] allow the use of GAMS as a solver
- [CHANGED] avoid formulation of adequacy constraints if already satisfied with existing capacity

## [4.14.11] - 2023-12-09

- [FIXED] fix error associated to the period probability in the objective function
- [FIXED] fix error in considering initial and final period for investment or retirement decisions

## [4.14.10] - 2023-12-01

- [FIXED] change the name and delete some duplicated result output files

## [4.14.9] - 2023-11-24

- [FIXED] values 0 of availability not changed to 1

## [4.14.8] - 2023-11-03

- [FIXED] declare StageWeight and LoadLevelWeight as NonNegativeReals
- [FIXED] fix in eHydroInventory constraint the conversion constant 0.0036

## [4.14.7] - 2023-10-26

- [FIXED] fix the condition to solve the complete problem

## [4.14.6] - 2023-10-22

- [FIXED] fix some pandas warnings

## [4.14.5] - 2023-10-20

- [FIXED] if there are system emission constraints no stage run can be done

## [4.14.4] - 2023-10-15

- [FIXED] check that the duration of all the stages is equal
- [FIXED] cycles of ESS and hydro reservoirs can't exceed the duration of the stage

## [4.14.3] - 2023-10-05

- [FIXED] fix the reservoir volumes at the end of the period and for every water cycle
- [FIXED] change the meaning of weekly storage/reservoir type by fixing the inventory/volume at the end of the month to the initial one

## [4.14.2] - 2023-09-23

- [CHANGED] avoid the use of max in bounds definition
- [FIXED] fixed some errors associated to ESS and hydropower plants

## [4.14.1] - 2023-09-19

- [FIXED] fixed some errors associated to hydropower plants parameters/variables
- [FIXED] fixed solving of the investment decision problem and computation of dual variables when there are many scenarios
- [FIXED] fixed computation of efficiency parameter of water reservoir and ESS units
- [FIXED] fixed computation of the hydro units water cycle
- [FIXED] fixed formulation of the maximum CO2 emission constraint

## [4.14.0] - 2023-09-13

- [CHANGED] added emission file to introduce the maximum system emission
- [CHANGED] added the maximum CO2 emission constraint, eMaxSystemEmission, and the resulting MarginalEmission file
- [CHANGED] include period (year) in the adequacy reserve margin file, ReserveMargin

## [4.13.0] - 2023-08-24

- [CHANGED] added the hydrogen demand and network, DemandHydrogen and NetworkHydrogen input files
- [CHANGED] added IndBinNetH2Invest in Option file to relax hydrogen network investment decisions. This is needed to keep compatibility with previous cases
- [CHANGED] added HNSCost (hydrogen not served cost) in Parameter file. This is needed to keep compatibility with previous cases
- [CHANGED] added production function of electrolyzers in Generation file to model hydrogen production. This is needed to keep compatibility with previous cases
- [CHANGED] added eConsecutiveRsrInvest and eConsecutiveNet2Invest constraints
- [CHANGED] added eBalanceH2 constraints

## [4.12.1] - 2023-08-22

- [FIXED] fix indices of the dual variables of the adequacy constraints in output results
- [CHANGED] added writing of the dual variables of the reservoir volume constraints in output results
- [FIXED] fix error in problem solving when there are no candidate hydro reservoirs
- [FIXED] fix error in units of water values in output results

## [4.12.0] - 2023-08-08

- [CHANGED] added eMaxVolume2Comm and eMinVolume2Comm constraints
- [CHANGED] added eTrbReserveUpIfEnergy, eTrbReserveDwIfEnergy, ePmpReserveUpIfEnergy, and ePmpReserveDwIfEnergy constraints
- [CHANGED] added IndBinRsrInvest in Option file to relax reservoir investment decisions. This is needed to keep compatibility with previous cases
- [CHANGED] added production function of hydropower plants in Generation file to be modeled in water units instead of energy units. This is needed to keep compatibility with previous cases
- [CHANGED] added dictionaries of hydro basin topology in water units (Dict_Reservoir, Dict_ReservoirToHydro, Dict_HydroToReservoir, Dict_ReservoirToPumpedHydro, Dict_PumpedHydroToReservoir, Dict_ReservoirToReservoir)
- [CHANGED] added data for water hydro inflows and outflows (Data_HydroInflows, Data_HydroOutflows)
- [CHANGED] added data for reservoirs (Data_Reservoir, Data_VariableMaxVolume, oT_Data_VariableMinVolume)

## [4.11.14] - 2023-07-08

- [FIXED] simplify input data and fix division by zero in output results
- [FIXED] several fixes in input data, model formulation, problem solving, and output results modules
- [FIXED] fix output of investment results
- [FIXED] reorganize the balance equation to avoid negative dual variables
- [CHANGED] NetworkCommitment file only if needed
- [CHANGED] Computation of problem size
- [FIXED] fixed vMaxCommitment in input data
- [FIXED] fixed vLineOnState and vLineOffState in input data for all the lines
- [CHANGED] add problem size in log file

## [4.11.13] - 2023-06-18

- [FIXED] fixed error in marginals of adequacy constraints
- [FIXED] fixed error in output results

## [4.11.12] - 2023-06-12

- [FIXED] fixed error in writing technology emission file of output results

## [4.11.11] - 2023-06-08

- [CHANGED] performance issues in input data and model formulation

## [4.11.10] - 2023-06-06

- [CHANGED] performance issues in input data
- [CHANGED] clean up the scaling of the output results

## [4.11.9] - 2023-05-30

- [CHANGED] avoid the repeated computation of modulo function with n
- [FIXED] fix error in output results
- [FIXED] fix computation of MarginalIncrementalGenerator output file

## [4.11.8] - 2023-05-29

- [CHANGED] introduce some dictionaries to avoid unnecessary computations
- [CHANGED] change name mTEPES.r to mTEPES.re
- [CHANGED] simplify some set combinations to reduce computation time

## [4.11.7] - 2023-05-17

- [CHANGED] reorganizing the ifs in model formulation

## [4.11.6] - 2023-05-15

- [CHANGED] adapt figures to altair 5.0.0

## [4.11.5] - 2023-05-13

- [CHANGED] fix some typos

## [4.11.3] - 2023-04-11

- [CHANGED] change boolean to binary parameters
- [CHANGED] get dual variables for each solved problem

## [4.11.2] - 2023-04-07

- [CHANGED] avoid formulation of period/scenario not solved

## [4.11.1] - 2023-03-31

- [FIXED] reorganize the problem solving by period
- [FIXED] split formulation by period and scenario

## [4.11.0] - 2023-03-28

- [CHANGED] if no investment decisions all the scenarios with probability > 0 area solved sequentially
- [CHANGED] new VariableFuelCost input data file

## [4.10.6] - 2023-03-21

- [FIXED] fix a typo in the generation unit investment file

## [4.10.5] - 2023-03-17

- [FIXED] fix a typo in the generation unit investment file
- [FIXED] fix a typo in the name of the technology energy plot
- [FIXED] fix a typo in generation operation output results

## [4.10.4] - 2023-03-15

- [CHANGED] allow negative CO2 emission rate for biomass units

## [4.10.3] - 2023-03-10

- [CHANGED] introduce incompatibility constraint between charge and outflows use

## [4.10.2] - 2023-03-09

- [CHANGED] introduce incompatibility constraint between charge and outflows use
- [CHANGED] introduce conditions to avoid doing unnecessary computations in input data
- [CHANGED] introduce indicators to allow selecting output results

## [4.10.1] - 2023-02-27

- [FIXED] typo in writing ESS operation results
- [FIXED] typo in control of minimum energy infeasibility

## [4.10.0] - 2023-02-15

- [CHANGED] introduce control of minimum energy infeasibility
- [CHANGED] scale eMaxInventory2Comm, eMinInventory2Comm, and eInflows2Comm constraints
- [FIXED] force time step cycle for ESS inventory scheduling to be integer
- [FIXED] eliminate production and operating reserve variables if there is no pumping capability and no natural inflows
- [FIXED] fix error in determining the storage cycle of every ESS unit (as the minimum value between storage type, outflows type, and energy type) only if values of outflows and energy are provided
- [CHANGED] new VariableMaxEnergy and VariableMinEnergy input data files to determine mandatory max or min energy in time interval defined by EnergyType column in Generation file

## [4.9.1] - 2023-01-18

- [CHANGED] new TechnologyConsumptionEnergy output file
- [CHANGED] change some column headings in some output files
- [FIXED] fix error in the values of MWkm output results

## [4.9.0] - 2023-01-12

- [FIXED] fix error when writing NetworkInvestment and NetworkInvestment_MWkm output files
- [CHANGED] fix inventory to the lower bound instead of 0 to avoid warnings
- [CHANGED] print infeasibilities to a file
- [CHANGED] if investment/retirement lower and upper bounds are close to 0 or 1, make them 0 or 1
- [CHANGED] add two new network energy flow files per area and total
- [CHANGED] add two new energy balance files per area and technology
- [FIXED] fix ESS inventory constraint to include ESS candidate and existing units
- [FIXED] fix constraint of energy inflows management for the case of candidate ESS units
- [FIXED] add StorageInvestment option in Generation file to link the storage capacity and inflows to the investment decision
- [FIXED] add constraints related to the previous option

## [4.8.5] - 2022-12-06

- [CHANGED] fix some warning on input data module
- [FIXED] fix relation between generation investment and total charge
- [FIXED] change some future warnings and fix generation investment for ESS

## [4.8.4] - 2022-12-01

- [CHANGED] scenario probabilities declared as float
- [FIXED] control of inventory at the end of each stage and initial inventory fixed, but only if they are between limits
- [FIXED] error in declaring the parameter scenario probabilities
- [FIXED] avoid writing results for areas with no generation nor demand
- [FIXED] fix some errors in the use of dynamic sets in output results and other modules
- [CHANGED] extensive use of dynamic sets in several modules
- [CHANGED] modify output results to avoid the dynamic activation of the load levels depending on the stage
- [CHANGED] modify input data and output results to clean up the use of aggregated sets
- [CHANGED] modify output results to reduce printing time

## [4.8.3] - 2022-11-07

- [FIXED] fix typo in assign duration 0 to load levels not being considered
- [CHANGED] added new output files

## [4.8.2] - 2022-10-27

- [FIXED] fix computation of the demand when there are negative demands
- [CHANGED] avoid a second run of the model if no binary variables are in it
- [CHANGED] improve the computation of some double sets
- [CHANGED] change names of output files from charge to consumption
- [FIXED] protect against division by zero in output results
- [FIXED] fix computation of ESS invested capacity when the unit has no power, but charge
- [CHANGED] change computation of node and line to area sets
- [FIXED] fix an error in balance between output of the ESS and outflows
- [FIXED] fix an error fixing values of storage with outflows
- [CHANGED] fix typo in error message about input data
- [CHANGED] add file for spillage by technology TechnologySpillage
- [FIXED] fix some errors in OutputResults
- [CHANGED] avoid formulation of storage variables and equations with no generation and consumption power
- [FIXED] fix error in output results
- [CHANGED] introduction of a base year in Data_Parameter file for all the economic parameters being affected by the discount rate
- [FIXED] fix error in eTotalTCost constraint
- [FIXED] fix some errors in output results

## [4.7.1] - 2022-08-01

- [CHANGED] modify the definition of vMaxCommitment
- [CHANGED] add some KPIs, LCOE and net demand in output results
- [FIXED] fix error in operation cost
- [FIXED] fix error in vMaxCommitment
- [FIXED] fix eInstalGenCap and eUninstalGenCap
- [FIXED] fix detection of ESS units with no inflows
- [CHANGED] introduction of lower and upper bounds in investment and retirement decisions for network and generation

## [4.6.1] - 2022-06-15

- [CHANGED] addition of two new result files for percentage of spillage by generator and technology
- [FIXED] fix error in outflows equation
- [FIXED] fix some typos in input data
- [FIXED] fix error related to initial and final periods
- [CHANGED] addition of two new result files for percentage of energy curtailed by generator and technology
- [FIXED] error in the ramp up equation for the charge onf an ESS (eRampUpCharge)
- [CHANGED] introduce generation/demand balance energy result
- [FIXED] error in the generation/demand balance file

## [4.6.0] - 2022-05-19

- [CHANGED] introduce generation/demand balance output result
- [CHANGED] allow scenarios defined with 0 probability
- [CHANGED] avoid division by 0 in network utilization
- [CHANGED] avoid values of BigM = 0.0
- [CHANGED] change modeling of negative reactances
- [CHANGED] introduce maximum shifting time for DSM

## [4.5.2] - 2022-04-25

- [CHANGED] combine load level weight and duration
- [CHANGED] combine period weight and probability
- [CHANGED] fix some typos in cost summary
- [CHANGED] introduce annual discount rate to move money along the time
- [FIXED] control of non-negative values of some input data
- [CHANGED] avoid fixing voltage angle for the reference node with single node option

## [4.5.1] - 2022-03-25

- [CHANGED] split the objective function and investment constraints in two scripts

## [4.5.0] - 2022-03-20

- [CHANGED] introduce initial and final period for each generator/line. The periods must be non-negative integers
- [CHANGED] define the scenario probability of each period.
- [CHANGED] introduce changes to allow multiperiod cases.
- [CHANGED] introduce some infeasibility detection.
- [CHANGED] additional control on definition of ESS units.
- [CHANGED] exchange the order of scenario and period to do dynamic expansion planning.

## [4.4.0] - 2022-03-11

- [CHANGED] introduce options for deactivating the up/down ramp constraints and the minimum up/down time constraints.
- [CHANGED] introduce a single-node option for running a case study as a single node (no network constraints).
- [CHANGED] new option value 2 for IndBinGenInvest, IndBinGenRetirement, IndBinNetInvest for ignoring the investment/retirement decisions.
- [CHANGED] re-group the generation operation constraints by topics in separate functions.
- [CHANGED] change some names of output results to organize them by topics.

## [4.3.7] - 2022-02-28

- [CHANGED] saving new results about incremental generator '[oT_Result_IncrementalGenerator]'+CaseName+'.csv'.
- [CHANGED] saving new results about incremental emission of generators with surplus '[oT_Result_GenerationIncrementalEmission]'+CaseName+'.csv'.
- [CHANGED] saving new results about generation ramp surplus in '[oT_Result_GenerationRampUpSurplus]'+CaseName+'.csv' and '[oT_Result_GenerationRampDwSurplus]'+CaseName+'.csv'.
- [CHANGED] saving new results about generation surplus in '[oT_Result_GenerationSurplus]'+CaseName+'.csv'.
- [CHANGED] saving new results about incremental variable cost of generators with surplus in '[oT_Result_GenerationIncrementalVariableCost]'+CaseName+'.csv'.

## [4.3.6] - 2022-02-09

- [CHANGED] change of domain of some p.u. parameters to UnitInterval and others to Reals
- [CHANGED] change output of units not contributing to operating reserves
- [CHANGED] change on the assessment of the termination condition

## [4.3.5] - 2022-01-29

- [FIXED] detect ESS that only pump/charge
- [FIXED] exclude contribution to operating reserves of units with NoOperatingReserves=yes
- [FIXED] fix computation of dual variables of operating reserves

## [4.3.4] - 2022-01-27

- [FIXED] fix computation of log console option

## [4.3.3] - 2022-01-25

- [CHANGED] Permanent presence of the solver log file
- [CHANGED] LP-file writing depends of the pIndLogConsole

## [4.3.2] - 2022-01-24

- [FIXED] Append function updated to cumulate all stages before plotting the LSRMC
- [CHANGED] Condition updated in ProblemSolving to use Gurobi or Mosek

## [4.3.2] - 2022-01-24 - release candidate

- [FIXED] Legend in nodes in the network map
- [CHANGED] Use of the CBC as a recommended solver instead of GLPK
- [CHANGED] Adding pIndLogConsole in openTEPES_ProblemSolving.py

## [4.3.1] - 2022-01-19

- [CHANGED] improved network map representation in html
- [CHANGED] console log as option in input data

## [4.3.0] - 2021-12-31

- [CHANGED] improved representation of operating reserves

## [4.2.4] - 2021-12-30

- [FIXED] inertia constraints
- [FIXED] typos in output results
- [CHANGED] introduce html plots based on Altair

## [4.2.3] - 2021-12-17

- [FIXED] plots associated to ESS technologies

## [4.2.2] - 2021-12-08

- [FIXED] assessment of the locational short-run marginal costs

## [4.2.1] - 2021-12-01

- [FIXED] assessment of the locational short-run marginal costs

## [4.2.0] - 2021-11-11

- [CHANGED] introduction of a retirement cost to allow retirement decisions
- [CHANGED] elimination of line switching states

## [4.1.3] - 2021-10-31

- [FIXED] Generalization of the maximum commitment and mutually exclusive constraints

## [4.1.2] - 2021-10-28

- [FIXED] Removing option when the solver is called in ProblemSolving

## [4.1.1] - 2021-10-27

- [FIXED] adding mutually exclusive formulation for ESS, add output results of reserve margin

## [4.1.0] - 2021-10-22

- [CHANGED] introduction of mutually exclusive generator in generation file
- [CHANGED] Using TimeStep of 4 instead of 2 in Cases 9n and sSEP to speed-up the packaging tests

## [3.1.5] - 2021-10-15

- [FIXED] fix magnitude of the emission output

## [3.1.4] - 2021-09-30

- [FIXED] fix initialization of synchronous condenser and shunt candidate

## [3.1.3] - 2021-09-10

- [FIXED] fix in some equations the activation of the operating reserves

## [3.1.2] - 2021-07-12

- [FIXED] fix typo in network investment constraint to include candidate lines

## [3.1.1] - 2021-07-08

- [FIXED] change location of lea and lca computation

## [3.1.0] - 2021-07-07

- [CHANGED] definition of switching stages with dict and data files to allow less granularity in switching decisions

## [2.6.5] - 2021-07-04

- [FIXED] typos in line switching equations and redefinition of lea and lca sets

## [2.6.4] - 2021-06-23

- [FIXED] typo in equation formulating the total output of a unit
- [CHANGED] introduce binary commitment option for each unit
- [CHANGED] introduce adequacy reserve margin for each area
- [CHANGED] introduce availability for each unit

## [2.6.3] - 2021-06-20

- [FIXED] typo in investment constraint in model formulation

## [2.6.2] - 2021-06-18

- [CHANGED] updated for pyomo 6.0
- [CHANGED] if not defined length computed as geographical distance

## [2.6.1] - 2021-06-14

- [CHANGED] line length added in network input file
- [FIXED] error in output results due to stage weight

## [2.6.0] - 2021-05-27

- [CHANGED] new inertia constraint for each area
- [FIXED] change column BinarySwitching by Switching in network data meaning that line is able to switch or not

## [2.5.3] - 2021-05-14

- [FIXED] fix output results of storage utilization

## [2.5.2] - 2021-05-11

- [CHANGED] new ESS inventory utilization result file
- [FIXED] protection against stage with no load levels

## [2.5.1] - 2021-05-07

- [FIXED] introduction of stage weight in the operation variable cost

## [2.5.0] - 2021-04-29

- [CHANGED] generalize the definition of stages to allow using representative stages (weeks, days, etc.)

## [2.4.2] - 2021-04-29

- [CHANGED] initialize shutdown variable
- [FIXED] fix error in conditions to formulate the relationship between UC, startup and shutdown

## [2.4.1] - 2021-04-28

- [CHANGED] very small parameters -> 0 depending on the area
- [CHANGED] avoid use of list if not needed

## [2.4.0] - 2021-04-24

- [CHANGED] new input files VariableMaxConsumption and VariableMinConsumption and MininmumCharge column in Generation file
- [CHANGED] change names of MaximumStorage (MinimumStorage) files to VariableMaxStorage (VariableMinStorage)

## [2.3.1] - 2021-04-23

- [CHANGED] avoid superfluous equations

## [2.3.0] - 2021-04-20

- [CHANGED] separate model data and optimization model

## [2.2.5] - 2021-04-18

- [FIXED] fix commitment, startup and shutdown decisions of hydro units
- [FIXED] output results of storage units
- [FIXED] detection of storage units

## [2.2.4] - 2021-04-10

- [FIXED] fix line switch off constraint

## [2.2.3] - 2021-04-07

- [FIXED] determine the commitment and output of generating units at the beginning of each stage

## [2.2.2] - 2021-04-05

- [CHANGED] remove a warning in InputData

## [2.2.1] - 2021-04-03

- [CHANGED] added three new output files for line commitment, switch on and off
- [CHANGED] added three four output files for ESS energy outflows
- [FIXED] fix writing flexibility files for ESS

## [2.2.0] - 2021-03-31

- [CHANGED] introduction of Power-to-X in ESS. Modifies the Generation file and introduces a new EnergyOutflows file
- [CHANGED] introduction of switching decision for transmission lines. Modifies the Option file and introduces a new column BinarySwitching in Network file

## [2.1.0] - 2021-03-18

- [CHANGED] using README.rst instead of README.md
- [CHANGED] split openTEPES_ModelFormulation.py in multiple functions related to investment and operating constraints
- [CHANGED] split openTEPES_OutputResults.py in multiple functions related to investment and operating variables

## [2.0.24] - 2021-03-08

- [FIXED] changed location of the shell openTEPES to sub folder openTEPES with all modules
- [FIXED] updated \_init\_.py

## [2.0.23] - 2021-03-08

- [CHANGED] included metadata in pyproject.toml and also requirements (only pyomo, matplotlib, numpy, pandas, and psutil.)
- [CHANGED] created a README.md file
