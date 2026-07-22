import os
import shutil
import pytest
import pyomo.environ as pyo
import numpy as np
import pandas as pd

from openTEPES.openTEPES import openTEPES_run
from openTEPES.openTEPES_ProblemSolvingBenders import lshaped
from openTEPES.openTEPES_ProblemSolvingResolve import resolve, overlay_scaled
from openTEPES import openTEPES_Runner, openTEPES_Cases
from openTEPES.openTEPES_ResultAggregate import aggregate
from openTEPES.openTEPES_OutputResultsSink import ResultSink, set_active_sink, clear_active_sink, get_active_sink


# === Fixture: single-stage 7-day system ===
@pytest.fixture
def case_7d_system(request):
    """
    Temporarily modify the input files of a single-stage case to simulate a 7-day system, then restore the originals
    afterwards. Duration is truncated globally to the first 168 hours; StageWeight is forced to 52 (one stage stands
    in for the full year); RESEnergy is wiped to disable the annual RES-energy constraint.

    Use ``case_multi_stage_7d_system`` for cases with multiple stages (the global Duration truncation here zeroes out
    stages 2..N, which causes ``pStorageTimeStep`` to fail against ``PositiveIntegers``).
    """
    case_name = request.param
    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES/cases")
        ),
        CaseName=case_name,
        SolverName="highs",  # or "gurobi" or "glpk"
        pIndLogConsole=0,
        pIndOutputResults=0,
    )

    # File paths
    duration_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_Duration_{case_name}.csv"
    )
    RESEnergy_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_RESEnergy_{case_name}.csv"
    )
    stage_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_Stage_{case_name}.csv"
    )

    # Backup original data
    original_duration_df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    original_resenergy_df = pd.read_csv(RESEnergy_csv, index_col=[0, 1])
    original_stage_df = pd.read_csv(stage_csv, index_col=[0])

    try:
        # Modify Duration: keep only first 168 hours (1 week)
        df = original_duration_df.copy()
        df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
        df.to_csv(duration_csv)

        # Modify RESEnergy: set all to NaN
        df = original_resenergy_df.copy()
        col = "RESEnergy"
        df[col] = df[col].astype(float)  # ✅ Ensure float dtype
        df[col] = np.nan                 # ✅ Now safe to set NaN
        df.to_csv(RESEnergy_csv)

        # Modify Stage Weight: force all weights to 52 (weeks)
        df = original_stage_df.copy()
        df.iloc[:, df.columns.get_loc("Weight")] = 52
        df.to_csv(stage_csv)

        yield data

    finally:
        # Restore original files
        original_duration_df.to_csv(duration_csv)
        original_resenergy_df.to_csv(RESEnergy_csv)
        original_stage_df.to_csv(stage_csv)


# === Fixture: multi-stage 7-day-per-stage system ===
@pytest.fixture
def case_multi_stage_7d_system(request):
    """
    Multi-stage variant of ``case_7d_system``. Keeps the first 168 hours of each ``(Period, Scenario, Stage)`` group
    in the Duration table — i.e. one representative week per stage — and leaves ``StageWeight`` as authored (so the
    stages still cover the full year via their per-stage weights). RESEnergy is wiped to disable the annual constraint.

    Required for cases with multi-stage rolling layouts such as ``9n7y`` (13 stages × 672 h) and ``RTS-GMLC_6y`` —
    the single-stage fixture's global Duration truncation zeroes out stages 2..N and crashes them at
    ``pStorageTimeStep``.
    """
    case_name = request.param
    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES/cases")
        ),
        CaseName=case_name,
        SolverName="highs",
        pIndLogConsole=0,
        pIndOutputResults=0,
    )

    duration_csv = os.path.join(data["DirName"], data["CaseName"], f"oT_Data_Duration_{case_name}.csv")
    RESEnergy_csv = os.path.join(data["DirName"], data["CaseName"], f"oT_Data_RESEnergy_{case_name}.csv")

    original_duration_df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    original_resenergy_df = pd.read_csv(RESEnergy_csv, index_col=[0, 1])

    try:
        # Per-stage truncation: keep first 168 rows of each (Period, Scenario, Stage) group; NaN the rest.
        df = original_duration_df.reset_index()
        df["__rownum"] = df.groupby(["Period", "Scenario", "Stage"]).cumcount()
        df.loc[df["__rownum"] >= 168, "Duration"] = np.nan
        df.drop(columns="__rownum").set_index(["Period", "Scenario", "LoadLevel"]).to_csv(duration_csv)

        # Wipe RESEnergy (same as the single-stage fixture).
        df = original_resenergy_df.copy()
        df["RESEnergy"] = df["RESEnergy"].astype(float)
        df["RESEnergy"] = np.nan
        df.to_csv(RESEnergy_csv)

        yield data

    finally:
        original_duration_df.to_csv(duration_csv)
        original_resenergy_df.to_csv(RESEnergy_csv)


# === Fixture: 7-day system on a private copy, with one or more Option-file overrides ===
@pytest.fixture
def case_7d_binary(request, tmp_path):
    """
    Like ``case_7d_system`` / ``case_multi_stage_7d_system``, but runs on a private copy of the case in a
    temporary folder and also overrides one or more columns of the ``oT_Data_Option_*`` file. Used to switch
    on a binary investment decision so the integer-investment (MILP) code path is exercised.

    Running on a copy (instead of editing the case in place) gives this test its own folder for the solver
    log files. On Windows the solver can still hold a log file open after a solve, so when several 9n tests
    reuse the shared case folder one of them fails trying to delete the stale log ("file in use"); a private
    folder per test avoids that. The copy is removed automatically with ``tmp_path``, so there is no restore.

    ``request.param`` is a dict: ``{"case": <name>, "multi_stage": <bool>, "options": {<column>: <value>}}``.
    The Duration / RESEnergy / Stage truncation matches the single- or multi-stage 7-day fixture depending on
    ``multi_stage``.
    """
    cfg = request.param
    case_name = cfg["case"]
    multi = cfg.get("multi_stage", False)
    options = cfg.get("options", {})

    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../openTEPES/cases", case_name))
    case_dir = os.path.join(str(tmp_path), case_name)
    # Copy only the input data; skip any run artifacts (logs, results, plots) left in the source folder.
    shutil.copytree(src_dir, case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))

    duration_csv = os.path.join(case_dir, f"oT_Data_Duration_{case_name}.csv")
    RESEnergy_csv = os.path.join(case_dir, f"oT_Data_RESEnergy_{case_name}.csv")
    stage_csv = os.path.join(case_dir, f"oT_Data_Stage_{case_name}.csv")
    option_csv = os.path.join(case_dir, f"oT_Data_Option_{case_name}.csv")

    if multi:
        df = pd.read_csv(duration_csv, index_col=[0, 1, 2]).reset_index()
        df["__rownum"] = df.groupby(["Period", "Scenario", "Stage"]).cumcount()
        df.loc[df["__rownum"] >= 168, "Duration"] = np.nan
        df.drop(columns="__rownum").set_index(["Period", "Scenario", "LoadLevel"]).to_csv(duration_csv)
    else:
        df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
        df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
        df.to_csv(duration_csv)

    df = pd.read_csv(RESEnergy_csv, index_col=[0, 1])
    df["RESEnergy"] = df["RESEnergy"].astype(float)
    df["RESEnergy"] = np.nan
    df.to_csv(RESEnergy_csv)

    if not multi:
        df = pd.read_csv(stage_csv, index_col=[0])
        df.iloc[:, df.columns.get_loc("Weight")] = 52
        df.to_csv(stage_csv)

    df = pd.read_csv(option_csv)
    for col, val in options.items():
        df[col] = val
    df.to_csv(option_csv, index=False)

    yield dict(
        DirName=str(tmp_path),
        CaseName=case_name,
        SolverName="highs",
        pIndLogConsole=0,
        pIndOutputResults=0,
    )


# === Parametrized single-stage test ===
#
# Feature coverage matrix (single-stage block):
#
#   case        electricity   hydrogen   reservoir   heat   PTDF   UC binaries   single-node
#   9n          ✓ losses
#   sSEP        ✓             ✓ (H2 demand+network+9 H2 gens)  ✓ (7 reservoirs + pumped hydro)  ramps+min-time
#   9n_PTDF     ✓ losses                                       ✓ (multi-level headers)
#   9n_heat     ✓ losses                                              ✓ (pIndHeat=1)
#   9n_H2       ✓ losses     ✓ (2 electrolyzers + H2 demand + H2 pipes; pIndHydrogen=1)
#   NG2030      ✓ losses                                                                                ✓
#   RTS-GMLC    ✓                                                                  ramps+min-time
#
# All single-stage cases use TimeStep ≥ 2 (rolling-mean time aggregation; openTEPES's representative-time-block
# mechanism). The 7-day fixture truncates Duration globally to the first 168 h and forces StageWeight=52 so one
# representative week stands in for the full year. For multi-stage rolling (representative weeks per stage), see
# the test_openTEPES_run_multi_stage block below.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system,expected_cost", [
    # 9n — minimal 9-node electricity case; reference for new cases per the openTEPES QA page.
    ("9n",        238.5141906543151),
    # sSEP — small Spanish system. Exercises the hydrogen sector (DemandHydrogen + NetworkHydrogen + 9 H2-related
    # generators) AND water-reservoir hydropower (7 reservoirs, reservoir maps, inflows/outflows/MaxVolume, pumped
    # hydro). pIndHydrogen / pIndHydroSystem code paths live here.
    ("sSEP",      38581.335524272574),
    # 9n_PTDF exercises the multi-level-header tables (VariableTTCFrw/Bck, VariablePTDF).
    ("9n_PTDF",   500.1114692260149),
    # 9n_heat exercises the heat-sector code path (pIndHeat=1). Added in PR #121.
    ("9n_heat",   234.5040485349081),
    # 9n_H2 exercises the hydrogen-sector code path (pIndHydrogen=1) on the minimal 9-node system: 2 electrolyzers,
    # hydrogen demand at three nodes, and a hydrogen pipe network. The H2 counterpart of 9n_heat. Added in PR #128.
    ("9n_H2",     245.02388843520743),
    # NG2030 — Nigeria 2030 baseline, multi-area state-level network (~37 nodes). Single-node mode active.
    ("NG2030",    1041.3415582681946),
    # RTS-GMLC — single-stage variant of the GMLC reference system; exercises ramp and min-up/down-time binaries.
    ("RTS-GMLC",  1091.0943444941825),
    # RTS24 (single area of RTS-GMLC) shows HiGHS non-determinism — three identical runs returned 1107.185,
    # 1107.400, and 1110.174. Covered indirectly by RTS-GMLC; not parametrised here.
], indirect=["case_7d_system"])
def test_openTEPES_run(case_7d_system, expected_cost):
    """
    Parametrized test for running openTEPES with 7-day modification.
    Asserts that total system cost matches expected value.
    """
    print("Running test case:", case_7d_system["CaseName"])
    mTEPES = openTEPES_run(**case_7d_system)

    assert mTEPES is not None, "Model instance returned is None."

    actual_cost = pyo.value(mTEPES.eTotalSCost)
    print(f"Expected cost: {expected_cost:.5f}, Actual cost: {actual_cost:.5f}")

    np.testing.assert_approx_equal(actual_cost, expected_cost)


# === Solve from a DuckDB input ===
#
# The DuckDB input backend is only tested at read time (input parity) elsewhere; no other test solves a model
# from a .duckdb. This writes the 7-day-trimmed 9n case to a .duckdb and solves straight from it, asserting the
# same total cost as the CSV run above, so the whole input -> model -> solve path through the DuckDB backend is
# covered. It reuses the case_7d_system fixture (which trims the CSV case and restores it afterwards); the .duckdb
# is written into the test's tmp dir, so the tracked example case is untouched.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_openTEPES_run_from_duckdb(case_7d_system, tmp_path):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "openTEPES_DuckDB"))
    from Tool_CSV_to_DuckDB import write_case

    case_dir = os.path.join(case_7d_system["DirName"], case_7d_system["CaseName"])
    db_path = write_case(case_dir, tmp_path / "9n.duckdb")

    mTEPES = openTEPES_run(str(tmp_path), db_path.name, case_7d_system["SolverName"], 0, 0)

    assert mTEPES is not None, "Model instance returned is None."
    actual_cost = pyo.value(mTEPES.eTotalSCost)
    np.testing.assert_approx_equal(actual_cost, 238.5141906543151)  # same reference as the CSV 9n run above


# === Parametrized multi-stage test (one representative week per stage) ===
#
# Covers the "representative stages" temporal-reduction pattern that the openTEPES QA page documents — i.e. each
# period is decomposed into N stages of K weeks each, with per-stage weight in the Stage table scaling the
# stage's costs back up to a full year. 9n7y is the canonical example named in QA.html.
#
# Feature coverage matrix (multi-stage block):
#
#   case        electricity   multi-year (dynamic)   multi-stage rolling   representative weeks
#   9n7y        ✓ losses      ✓ (7 periods 2020-2050) ✓ (13 stages × 4w)    ✓ (one week per stage)
#
@pytest.mark.solve
@pytest.mark.parametrize("case_multi_stage_7d_system,expected_cost", [
    # 9n7y exercises the multi-stage rolling layout (13 stages × 4-week weight each = 52 weeks / period × 7 periods).
    # Cost reproducible to 13 significant figures across reruns under HiGHS.
    ("9n7y", 9047.829359499794),
    # RTS-GMLC_6y is a candidate (6 periods × 13 stages); deferred until its full multi-stage solve time under HiGHS
    # is characterised on CI hardware — the multi-stage fixture itself is verified correct via 9n7y.
], indirect=["case_multi_stage_7d_system"])
def test_openTEPES_run_multi_stage(case_multi_stage_7d_system, expected_cost):
    """
    Parametrized test for multi-stage cases under the per-stage 7-day fixture.
    Asserts that total system cost matches expected value.
    """
    print("Running multi-stage test case:", case_multi_stage_7d_system["CaseName"])
    mTEPES = openTEPES_run(**case_multi_stage_7d_system)

    assert mTEPES is not None, "Model instance returned is None."

    actual_cost = pyo.value(mTEPES.eTotalSCost)
    print(f"Expected cost: {expected_cost:.5f}, Actual cost: {actual_cost:.5f}")

    np.testing.assert_approx_equal(actual_cost, expected_cost)


# === Classical L-shaped Benders compatibility test ===
#
# Reuses the single-stage 7-day fixture, parametrised on the 9n case (the only bundled case with a single
# candidate transmission line: Node_1 ↔ Node_4 dc1, FixedInvestmentCost=100). Solves the case as the joint
# LP via openTEPES_run, then runs L-shaped Benders on the same model and asserts both total costs match.
#
# This is a compatibility guard for the layered-architecture restructure: every future refactor must keep
# vNetworkInvest cleanly separable as a master decision and the rest of the model usable as an LP
# subproblem with valid duals on the fixing constraint. If a refactor breaks this, the test fails.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_benders_lshaped_matches_joint_lp(case_7d_system):
    """L-shaped Benders on 9n must converge to the joint-LP total cost within 1e-4 relative tolerance."""
    mTEPES = openTEPES_run(**case_7d_system)
    joint_cost = float(pyo.value(mTEPES.eTotalSCost))

    result = lshaped(mTEPES, solver_name="highs", max_iter=20, tol=1e-4, verbose=False)

    print(f"Joint LP cost : {joint_cost:.6f} MEUR")
    print(f"Benders cost  : {result['total_cost']:.6f} MEUR  ({result['num_iterations']} iters, "
          f"{result['wall_clock_s']:.1f} s)")

    assert result["converged"], (
        f"Benders failed to converge within {result['num_iterations']} iterations "
        f"(history: {result['history']})"
    )
    rel_err = abs(result["total_cost"] - joint_cost) / max(abs(joint_cost), 1.0)
    assert rel_err < 1e-4, (
        f"Benders total cost diverges from joint LP by {rel_err:.2e} "
        f"(Benders={result['total_cost']:.6f}, joint={joint_cost:.6f})"
    )


# === Mode C hot-swap re-solve test ===
#
# Builds 9n once via openTEPES_run, then re-solves it under parameter overlays without rebuilding
# (openTEPES_ProblemSolvingResolve.resolve). An identity overlay must reproduce the from-build
# objective exactly: this is the Mode C parity guarantee, since the hot-swap path feeds the same
# mutable Param into the same constraint expressions as the build path — there is no separate
# "baked-in" code path. A +10% demand overlay must raise total cost, and restoring the baseline
# must return the objective to its original value (store_values reversibility).
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_c_resolve_demand_hot_swap(case_7d_system):
    """Mode C: re-solve 9n under demand overlays without rebuilding; identity == build, +10% > build."""
    mTEPES = openTEPES_run(**case_7d_system)
    base = mTEPES.vTotalSCost()

    identity = resolve(mTEPES, "highs", [{}])
    assert identity[0]["status"] == "optimal"
    assert identity[0]["total_cost_meur"] == pytest.approx(base, rel=1e-7)

    # Two overlays in one sweep: overlays must be independent (each applied relative to the
    # baseline, not to the previous overlay), so the empty second overlay must reproduce the
    # baseline cost even though the first overlay raised demand.
    sweep = resolve(mTEPES, "highs", [overlay_scaled(mTEPES, "pDemandElec", 1.10), {}], restore=True)
    assert sweep[0]["status"] == "optimal"
    assert sweep[0]["total_cost_meur"] > base
    assert sweep[1]["total_cost_meur"] == pytest.approx(base, rel=1e-7)

    restored = resolve(mTEPES, "highs", [{}])
    assert restored[0]["total_cost_meur"] == pytest.approx(base, rel=1e-7)


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_c_resolve_reoptimises_investment(case_7d_system):
    """A demand rise in a Mode C sweep must move the investment plan, not just add unserved energy.

    The solve fixes the plan to read the duals; resolve releases it first. Without that release the line
    investment stays at its baseline value and the reported cost is too high (issue #148).
    """
    mTEPES = openTEPES_run(**case_7d_system)
    line = next(iter(mTEPES.vNetworkInvest))
    base_invest = mTEPES.vNetworkInvest[line]()

    resolve(mTEPES, "highs", [overlay_scaled(mTEPES, "pDemandElec", 1.5)], restore=False)
    assert mTEPES.vNetworkInvest[line]() > base_invest + 1e-3
    assert not any(mTEPES.vNetworkInvest[i].fixed for i in mTEPES.vNetworkInvest)


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_c_resolve_rejects_unreachable_overlay(case_7d_system):
    """resolve refuses an overlay the built model does not read live, instead of swapping it silently.

    ``pEFOR`` is mutable but 9n has no generation candidates, so the adequacy constraint that reads it is
    skipped and no live constraint references it; a misspelt name is unreachable too. Both must raise rather
    than return an unchanged cost.
    """
    mTEPES = openTEPES_run(**case_7d_system)
    with pytest.raises(ValueError, match="does not read them live"):
        resolve(mTEPES, "highs", [{"pEFOR": mTEPES.pEFOR.extract_values()}])
    with pytest.raises(ValueError, match="does not read them live"):
        resolve(mTEPES, "highs", [{"pDemandElecc": {}}])


# === Binary (MILP) investment test ===
#
# Every other case here solves the investment variables as a continuous relaxation, so no other test
# exercises an integer investment decision — the defining feature of an expansion-planning model. This
# switches on a binary network-investment decision: vNetworkInvest becomes a {0,1} build/don't-build
# variable on 9n's single candidate line (Node_1 <-> Node_4 dc1). The result differs from the continuous
# case (238.823 vs 238.514 MEUR) because the binary decision forces a full line build. It also guards the
# MIP dual recovery in ProblemSolving: a binary first solve must not ask HiGHS for duals it cannot give,
# and the fix-and-resolve LP pass must still produce the shadow prices the economic outputs need.
#
# Binary GENERATION investment (IndBinGenInvest on 9n7y, the only bundled case with generation candidates:
# CCGT_5..) is the natural companion, but 9n7y is multi-stage and the resulting MIP runs many minutes under
# HiGHS — too slow for CI. It is deferred until a small single-stage case with generation candidates exists;
# the binary network case below already covers the integer-investment code path and the MIP dual recovery.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_binary,expected_cost", [
    ({"case": "9n", "multi_stage": False, "options": {"IndBinNetInvest": 1}}, 238.82295305023092),
], indirect=["case_7d_binary"])
def test_binary_investment(case_7d_binary, expected_cost):
    """A binary (MILP) investment decision solves and matches the expected total cost."""
    print("Running binary-investment test case:", case_7d_binary["CaseName"])
    mTEPES = openTEPES_run(**case_7d_binary)

    assert mTEPES is not None, "Model instance returned is None."

    actual_cost = pyo.value(mTEPES.eTotalSCost)
    print(f"Expected cost: {expected_cost:.5f}, Actual cost: {actual_cost:.5f}")

    np.testing.assert_approx_equal(actual_cost, expected_cost)


# === Mode A sweep-runner tests ===
#
# openTEPES_Runner.run drives many cases through openTEPES_run with a chosen backend (Mode A,
# RFC §4.1: each worker loads its own source, builds, solves, writes). The runner never returns
# the Pyomo model — that cannot cross a process boundary — so it reads back the per-case
# openTEPES_run_status_*.json and returns one summary dict per case, in input order, regardless of
# backend. A case that raises is captured as status="error" so one bad pathway does not lose the
# rest of the sweep.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_a_runner_serial_parity(case_7d_system, tmp_path):
    """A single-case serial sweep reproduces a direct openTEPES_run cost and echoes the label."""
    d = case_7d_system
    base_model = openTEPES_run(d["DirName"], d["CaseName"], d["SolverName"], 0, 0)
    base_cost  = base_model.vTotalSCost()

    records = openTEPES_Runner.run(
        [openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "c1"), label="first")],
        d["SolverName"], mode="pre-build", backend="serial",
        pIndOutputResults=0, pIndLogConsole=0,
    )
    assert len(records) == 1
    assert records[0]["status"] == "optimal"
    assert records[0]["label"] == "first"
    assert records[0]["total_cost_meur"] == pytest.approx(base_cost, rel=1e-6)


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_a_runner_multi_case_and_error(case_7d_system, tmp_path):
    """A multi-case serial sweep preserves input order, isolates outputs, and captures a bad case."""
    d = case_7d_system
    cases = [
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "good1"), label="good1"),
        openTEPES_Cases.Case(str(tmp_path), "DOES_NOT_EXIST", out_path=str(tmp_path / "broken"), label="broken"),
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "good2"), label="good2"),
    ]
    records = openTEPES_Runner.run(cases, d["SolverName"], mode="pre-build", backend="serial",
                                   pIndOutputResults=0, pIndLogConsole=0)

    assert [r["label"] for r in records] == ["good1", "broken", "good2"]
    assert records[0]["status"] == "optimal"
    assert records[2]["status"] == "optimal"
    assert records[1]["status"] == "error"
    assert "error" in records[1]
    # The two good cases solved to the same cost from independent output directories.
    assert records[0]["total_cost_meur"] == pytest.approx(records[2]["total_cost_meur"], rel=1e-9)


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_a_runner_multiprocessing(case_7d_system, tmp_path):
    """The multiprocessing backend returns the same per-case summaries, in input order."""
    d = case_7d_system
    cases = [
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "w1"), label="w1"),
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "w2"), label="w2"),
    ]
    records = openTEPES_Runner.run(cases, d["SolverName"], mode="pre-build",
                                   backend="multiprocessing", n_workers=2,
                                   pIndOutputResults=0, pIndLogConsole=0)
    assert [r["label"] for r in records] == ["w1", "w2"]
    assert all(r["status"] == "optimal" for r in records)
    assert records[0]["total_cost_meur"] == pytest.approx(records[1]["total_cost_meur"], rel=1e-9)


# === Mode B — in-memory overlay sweep (RFC §4.2) ===
# openTEPES_Runner.run(mode="in-memory") reads the baseline case once into an InMemorySource, then
# runs every case from it through openTEPES_run(input_source=...). An empty (identity) overlay must
# reproduce the direct-build cost — it reads exactly the same baseline frames — proving the in-memory
# path is faithful to reading from disk. A +10% demand overlay must strictly raise total system cost.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_mode_b_runner_overlay_parity(case_7d_system, tmp_path):
    """Mode B: identity overlay == direct build cost; a +10% demand overlay raises it."""
    d = case_7d_system
    base_model = openTEPES_run(d["DirName"], d["CaseName"], d["SolverName"], 0, 0)
    base_cost = base_model.vTotalSCost()

    cases = [
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "identity"), label="identity"),
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "demand_110"),
                             label="demand_110", overlay={"Demand": 1.10}),
    ]
    records = openTEPES_Runner.run(cases, d["SolverName"], mode="in-memory", backend="serial",
                                   pIndOutputResults=0, pIndLogConsole=0)

    assert [r["label"] for r in records] == ["identity", "demand_110"]
    assert all(r["status"] == "optimal" for r in records)
    # The identity overlay reads the same baseline frames as a direct build → same cost.
    assert records[0]["total_cost_meur"] == pytest.approx(base_cost, rel=1e-6)
    # Scaling every demand value up by 10% strictly raises the total system cost.
    assert records[1]["total_cost_meur"] > records[0]["total_cost_meur"]


def test_runner_guards():
    """Unsupported modes/backends, a Mode-A overlay, and a Mode-B case without out_path are rejected before solving."""
    case = openTEPES_Cases.Case("dir", "case")
    # Mode A (pre-build) rejects an overlay — that is Mode B's input.
    with pytest.raises(NotImplementedError):
        openTEPES_Runner.run([openTEPES_Cases.Case("dir", "case", overlay={"Demand": 1.1})], "highs")
    # Unknown mode and unknown backend are rejected.
    with pytest.raises(ValueError):
        openTEPES_Runner.run([case], "highs", mode="hot-swap")
    with pytest.raises(ValueError):
        openTEPES_Runner.run([case], "highs", backend="dask")
    # Mode B needs a distinct out_path per case so results do not collide on the shared baseline dir.
    with pytest.raises(ValueError):
        openTEPES_Runner.run([case], "highs", mode="in-memory")


# === Result sink (DuckDB output) and sweep aggregate ===
# The .oT accessor on a DataFrame/Series routes a write through the process-active ResultSink
# (openTEPES_OutputResultsSink). With no active sink it is plain to_csv; with a "both" sink it
# also stores the same in-memory frame as one table in oT_Results_<case>.duckdb. aggregate()
# then stacks the cases of a sweep into one long table per result with a leading "case" column.

def test_sink_csv_only_matches_plain_to_csv(tmp_path):
    """With no active sink, frame.oT.write writes the same bytes as frame.to_csv."""
    assert get_active_sink() is None
    df = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.5]})
    df.oT.write(str(tmp_path / "oT_Result_Foo_9n.csv"), sep=",")
    df.to_csv(str(tmp_path / "plain.csv"), sep=",")
    assert (tmp_path / "oT_Result_Foo_9n.csv").read_text() == (tmp_path / "plain.csv").read_text()


def test_sink_writes_duckdb_tables(tmp_path):
    """A 'both' sink writes the CSV and a per-case DuckDB whose tables match the CSVs."""
    import duckdb
    sink = ResultSink(str(tmp_path), "9n", fmt="both")
    set_active_sink(sink)
    try:
        df = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.5]})
        df.oT.write(str(tmp_path / "oT_Result_Frame_9n.csv"), index=False, sep=",")
        pd.Series([5.0, 6.0], name="v").oT.write(str(tmp_path / "oT_Result_Ser_9n.csv"), sep=",")
    finally:
        sink.close()
        clear_active_sink()
    assert get_active_sink() is None
    assert (tmp_path / "oT_Result_Frame_9n.csv").exists()         # CSV still written
    con = duckdb.connect(sink.db_path, read_only=True)
    try:
        tables = sorted(t[0] for t in con.execute("SHOW TABLES").fetchall())
        assert tables == ["Frame", "Ser"]                         # case suffix stripped
        assert con.execute("SELECT count(*) FROM Frame").fetchone()[0] == 2
        assert [c[0] for c in con.execute("DESCRIBE Frame").fetchall()] == ["a", "b"]
    finally:
        con.close()


def _write_fake_case(dir_path, case, tables):
    dir_path.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(dir_path / f"oT_Result_{name}_{case}.csv", index=False)


def test_aggregate_stacks_csv_dirs(tmp_path):
    """aggregate over two CSV case dirs stacks each table with a leading case column."""
    _write_fake_case(tmp_path / "A", "caseA", {
        "CostSummary": pd.DataFrame({"Item": ["total"], "MEUR": [100.0]}),
        "GenInvest":   pd.DataFrame({"Gen": ["g1", "g2"], "MW": [10.0, 20.0]}),
    })
    _write_fake_case(tmp_path / "B", "caseB", {
        "CostSummary": pd.DataFrame({"Item": ["total"], "MEUR": [200.0]}),
        "GenInvest":   pd.DataFrame({"Gen": ["g1", "g2"], "MW": [11.0, 22.0]}),
    })
    out = tmp_path / "merged"
    merged = aggregate([str(tmp_path / "A"), str(tmp_path / "B")], out_path=str(out),
                       to="csv", labels=["caseA", "caseB"])

    assert set(merged) == {"CostSummary", "GenInvest"}
    cs = merged["CostSummary"]
    assert list(cs.columns)[0] == "case"
    assert sorted(cs["case"].unique()) == ["caseA", "caseB"]
    assert len(merged["GenInvest"]) == 4                          # 2 cases x 2 rows
    # Files on disk match the returned tables.
    assert (out / "oT_Sweep_CostSummary.csv").exists()
    assert len(pd.read_csv(out / "oT_Sweep_GenInvest.csv")) == 4


def test_aggregate_from_duckdb_union(tmp_path):
    """aggregate reads per-case DuckDB files (preferred over CSVs) and unions them."""
    import duckdb
    for case, mw in (("caseA", 10.0), ("caseB", 20.0)):
        d = tmp_path / case
        d.mkdir()
        sink = ResultSink(str(d), case, fmt="duckdb")
        set_active_sink(sink)
        try:
            pd.DataFrame({"Gen": ["g1"], "MW": [mw]}).oT.write(str(d / f"oT_Result_GenInvest_{case}.csv"), index=False)
        finally:
            sink.close()
            clear_active_sink()
        assert not (d / f"oT_Result_GenInvest_{case}.csv").exists()   # duckdb-only: no CSV

    out = tmp_path / "merged"
    merged = aggregate([str(tmp_path / "caseA"), str(tmp_path / "caseB")], out_path=str(out),
                       to="duckdb", labels=["caseA", "caseB"])
    gi = merged["GenInvest"]
    assert sorted(gi["case"].unique()) == ["caseA", "caseB"]
    assert sorted(gi["MW"]) == [10.0, 20.0]
    con = duckdb.connect(str(out / "oT_Sweep.duckdb"), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM GenInvest").fetchone()[0] == 2
    finally:
        con.close()


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_output_format_both_csv_parity(case_7d_system, tmp_path):
    """output_format='both' writes CSVs identical to a 'csv' run, plus a matching DuckDB."""
    import duckdb
    from openTEPES._output_parity_test import snapshot, compare_snapshots
    d = case_7d_system
    a = str(tmp_path / "csv")
    b = str(tmp_path / "both")
    openTEPES_run(d["DirName"], d["CaseName"], d["SolverName"], "Yes", "No", out_path=a, output_format="csv")
    openTEPES_run(d["DirName"], d["CaseName"], d["SolverName"], "Yes", "No", out_path=b, output_format="both")

    assert compare_snapshots(snapshot(a), snapshot(b)) == []      # CSVs byte-equal within tolerance

    db = os.path.join(b, f"oT_Results_{d['CaseName']}.duckdb")
    assert os.path.exists(db)
    con = duckdb.connect(db, read_only=True)
    try:
        n_tables = len(con.execute("SHOW TABLES").fetchall())
    finally:
        con.close()
    n_csv = len([f for f in os.listdir(b) if f.startswith("oT_Result_") and f.endswith(".csv")])
    assert n_tables == n_csv and n_tables > 10                    # one DuckDB table per result CSV


@pytest.mark.solve
@pytest.mark.parametrize("case_7d_system", ["9n"], indirect=["case_7d_system"])
def test_runner_output_format_and_aggregate(case_7d_system, tmp_path):
    """The runner solves two cases to DuckDB and merges them into one oT_Sweep set."""
    import duckdb
    d = case_7d_system
    cases = [
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "c1"), label="c1"),
        openTEPES_Cases.Case(d["DirName"], d["CaseName"], out_path=str(tmp_path / "c2"), label="c2"),
    ]
    merged_dir = str(tmp_path / "sweep")
    records = openTEPES_Runner.run(cases, d["SolverName"], mode="pre-build", backend="serial",
                                   pIndOutputResults=0, pIndLogConsole=0,
                                   output_format="both", aggregate_to=merged_dir)
    assert [r["status"] for r in records] == ["optimal", "optimal"]
    assert all(r["backend"] == "both" for r in records)          # status JSON records the format
    assert os.path.exists(os.path.join(str(tmp_path / "c1"), f"oT_Results_{d['CaseName']}.duckdb"))

    con = duckdb.connect(os.path.join(merged_dir, "oT_Sweep.duckdb"), read_only=True)
    try:
        # CostSummary is always written (min output suite); both cases must appear.
        labels = sorted(r[0] for r in con.execute('SELECT DISTINCT "case" FROM "CostSummary"').fetchall())
    finally:
        con.close()
    assert labels == ["c1", "c2"]
