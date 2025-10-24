import os
import pytest
import pyomo.environ as pyo
import numpy as np
import pandas as pd

from openTEPES.openTEPES import openTEPES_run


# === Fixture definition ===
@pytest.fixture
def case_7d_system(request):
    """
    Fixture to temporarily modify the input files of a given case
    to simulate a 7-day system and restore the originals afterward.
    """
    case_name = request.param
    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES")
        ),
        CaseName=case_name,
        SolverName="glpk",  # or "gurobi" or "appsi_highs"
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


# === Parametrized Test ===
@pytest.mark.parametrize("case_7d_system,expected_cost", [
    ("9n", 248.434726565058),
    ("sSEP", 38581.3355242721),
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
