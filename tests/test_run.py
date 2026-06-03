import os
import pytest
import pyomo.environ as pyo
import numpy as np
import pandas as pd

from openTEPES.openTEPES import openTEPES_run
from openTEPES.openTEPES_ProblemSolvingBenders import lshaped


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


# === Fixture: 7-day system with one or more Option-file overrides ===
@pytest.fixture
def case_7d_binary(request):
    """
    Like ``case_7d_system`` / ``case_multi_stage_7d_system``, but also overrides one or more columns of the
    ``oT_Data_Option_*`` file before solving (and restores them afterwards). Used to switch on a binary
    investment decision so the integer-investment (MILP) code path is exercised.

    ``request.param`` is a dict: ``{"case": <name>, "multi_stage": <bool>, "options": {<column>: <value>}}``.
    The Duration / RESEnergy / Stage truncation matches the single- or multi-stage 7-day fixture depending on
    ``multi_stage``.
    """
    cfg = request.param
    case_name = cfg["case"]
    multi = cfg.get("multi_stage", False)
    options = cfg.get("options", {})
    data = dict(
        DirName=os.path.abspath(os.path.join(os.path.dirname(__file__), "../openTEPES/cases")),
        CaseName=case_name,
        SolverName="highs",
        pIndLogConsole=0,
        pIndOutputResults=0,
    )
    case_dir = os.path.join(data["DirName"], case_name)
    duration_csv = os.path.join(case_dir, f"oT_Data_Duration_{case_name}.csv")
    RESEnergy_csv = os.path.join(case_dir, f"oT_Data_RESEnergy_{case_name}.csv")
    stage_csv = os.path.join(case_dir, f"oT_Data_Stage_{case_name}.csv")
    option_csv = os.path.join(case_dir, f"oT_Data_Option_{case_name}.csv")

    original_duration = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    original_resenergy = pd.read_csv(RESEnergy_csv, index_col=[0, 1])
    original_stage = None if multi else pd.read_csv(stage_csv, index_col=[0])
    original_option = pd.read_csv(option_csv)

    try:
        if multi:
            df = original_duration.reset_index()
            df["__rownum"] = df.groupby(["Period", "Scenario", "Stage"]).cumcount()
            df.loc[df["__rownum"] >= 168, "Duration"] = np.nan
            df.drop(columns="__rownum").set_index(["Period", "Scenario", "LoadLevel"]).to_csv(duration_csv)
        else:
            df = original_duration.copy()
            df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
            df.to_csv(duration_csv)

        df = original_resenergy.copy()
        df["RESEnergy"] = df["RESEnergy"].astype(float)
        df["RESEnergy"] = np.nan
        df.to_csv(RESEnergy_csv)

        if not multi:
            df = original_stage.copy()
            df.iloc[:, df.columns.get_loc("Weight")] = 52
            df.to_csv(stage_csv)

        df = original_option.copy()
        for col, val in options.items():
            df[col] = val
        df.to_csv(option_csv, index=False)

        yield data

    finally:
        original_duration.to_csv(duration_csv)
        original_resenergy.to_csv(RESEnergy_csv)
        if not multi:
            original_stage.to_csv(stage_csv)
        original_option.to_csv(option_csv, index=False)


# === Parametrized single-stage test ===
#
# Feature coverage matrix (single-stage block):
#
#   case        electricity   hydrogen   reservoir   heat   PTDF   UC binaries   single-node
#   9n          ✓ losses
#   sSEP        ✓             ✓ (H2 demand+network+9 H2 gens)  ✓ (7 reservoirs + pumped hydro)  ramps+min-time
#   9n_PTDF     ✓ losses                                       ✓ (multi-level headers)
#   9n_heat     ✓ losses                                              ✓ (pIndHeat=1)
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
    ("9n",        252.201329983352),
    # sSEP — small Spanish system. Exercises the hydrogen sector (DemandHydrogen + NetworkHydrogen + 9 H2-related
    # generators) AND water-reservoir hydropower (7 reservoirs, reservoir maps, inflows/outflows/MaxVolume, pumped
    # hydro). pIndHydrogen / pIndHydroSystem code paths live here.
    ("sSEP",      38581.335524272574),
    # 9n_PTDF exercises the multi-level-header tables (VariableTTCFrw/Bck, VariablePTDF).
    ("9n_PTDF",   447.3850166556059),
    # 9n_heat exercises the heat-sector code path (pIndHeat=1). Added in PR #121.
    ("9n_heat",   247.19623713906003),
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
    ("9n7y", 9019.299277297196),
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


# === Binary (MILP) investment test ===
#
# Every other case here solves the investment variables as a continuous relaxation, so no other test
# exercises an integer investment decision — the defining feature of an expansion-planning model. This
# switches on a binary network-investment decision: vNetworkInvest becomes a {0,1} build/don't-build
# variable on 9n's single candidate line (Node_1 <-> Node_4 dc1). The result differs from the continuous
# case (254.337 vs 252.201 MEUR) because the binary decision forces a full line build. It also guards the
# MIP dual recovery in ProblemSolving: a binary first solve must not ask HiGHS for duals it cannot give,
# and the fix-and-resolve LP pass must still produce the shadow prices the economic outputs need.
#
# Binary GENERATION investment (IndBinGenInvest on 9n7y, the only bundled case with generation candidates:
# CCGT_5..) is the natural companion, but 9n7y is multi-stage and the resulting MIP runs many minutes under
# HiGHS — too slow for CI. It is deferred until a small single-stage case with generation candidates exists;
# the binary network case below already covers the integer-investment code path and the MIP dual recovery.
@pytest.mark.solve
@pytest.mark.parametrize("case_7d_binary,expected_cost", [
    ({"case": "9n", "multi_stage": False, "options": {"IndBinNetInvest": 1}}, 254.3373931950719),
], indirect=["case_7d_binary"])
def test_binary_investment(case_7d_binary, expected_cost):
    """A binary (MILP) investment decision solves and matches the expected total cost."""
    print("Running binary-investment test case:", case_7d_binary["CaseName"])
    mTEPES = openTEPES_run(**case_7d_binary)

    assert mTEPES is not None, "Model instance returned is None."

    actual_cost = pyo.value(mTEPES.eTotalSCost)
    print(f"Expected cost: {expected_cost:.5f}, Actual cost: {actual_cost:.5f}")

    np.testing.assert_approx_equal(actual_cost, expected_cost)
