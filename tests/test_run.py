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
    ("9n", 252.201329983352),
    ("sSEP", 38581.335524272574),
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


# === Regression test: InvestmentUp=0 must enforce zero investment ===
@pytest.fixture
def case_9n_with_net_invest_up_zero(request):
    """
    Prepare case 9n with InvestmentUp=0 set on the single network candidate
    (Node_1, Node_4, dc1). 7-day truncation matches the case_7d_system fixture.
    Restores all touched files in finally.

    Exercises the pNetUpInvest fillna fix at openTEPES_InputData.py:447.
    The same code change (.fillna(1.0) instead of .where(par > 0.0, 1.0))
    is applied identically to pGenUpInvest (line 445) and pGenUpRetire
    (line 446); a single regression test for one of the three is enough
    to pin the corrected semantics.
    """
    case_name = "9n"
    forbid_line = ("Node_1", "Node_4", "dc1")

    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES")
        ),
        CaseName=case_name,
        SolverName="glpk",
        pIndLogConsole=0,
        pIndOutputResults=0,
    )

    case_dir = os.path.join(data["DirName"], data["CaseName"])
    duration_csv  = os.path.join(case_dir, f"oT_Data_Duration_{case_name}.csv")
    resenergy_csv = os.path.join(case_dir, f"oT_Data_RESEnergy_{case_name}.csv")
    stage_csv     = os.path.join(case_dir, f"oT_Data_Stage_{case_name}.csv")
    network_csv   = os.path.join(case_dir, f"oT_Data_Network_{case_name}.csv")

    original_duration  = pd.read_csv(duration_csv,  index_col=[0, 1, 2])
    original_resenergy = pd.read_csv(resenergy_csv, index_col=[0, 1])
    original_stage     = pd.read_csv(stage_csv,     index_col=[0])
    original_network   = pd.read_csv(network_csv)

    try:
        df = original_duration.copy()
        df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
        df.to_csv(duration_csv)

        df = original_resenergy.copy()
        df["RESEnergy"] = df["RESEnergy"].astype(float)
        df["RESEnergy"] = np.nan
        df.to_csv(resenergy_csv)

        df = original_stage.copy()
        df.iloc[:, df.columns.get_loc("Weight")] = 52
        df.to_csv(stage_csv)

        df = original_network.copy()
        ni, nf, cc = forbid_line
        mask = (df["InitialNode"] == ni) & (df["FinalNode"] == nf) & (df["Circuit"] == cc)
        assert mask.any(), f"Test setup error: {forbid_line} not in 9n network."
        df.loc[mask, "InvestmentLo"] = 0.0
        df.loc[mask, "InvestmentUp"] = 0.0
        df.to_csv(network_csv, index=False)

        yield {**data, "forbid_line": forbid_line}

    finally:
        original_duration.to_csv(duration_csv)
        original_resenergy.to_csv(resenergy_csv)
        original_stage.to_csv(stage_csv)
        original_network.to_csv(network_csv, index=False)


def test_invest_up_zero_enforces_no_investment(case_9n_with_net_invest_up_zero):
    """
    Regression test for the InvestmentUp=0 semantics.

    Before the fix at openTEPES_InputData.py:444-447, an explicit 0 in
    InvestmentUp was silently overridden to 1.0 (`.where(par > 0.0, 1.0)`),
    which let the solver freely build the candidate up to MaximumPower / TTC.
    After the fix (`.fillna(1.0)`), only blank/NaN cells default to 1.0;
    an explicit 0 enforces "no investment", per the column's documented
    [p.u.] semantics.
    """
    data = case_9n_with_net_invest_up_zero
    forbid_line = data.pop("forbid_line")
    mTEPES = openTEPES_run(**data)

    assert mTEPES is not None, "Model instance returned is None."

    ni, nf, cc = forbid_line
    invest_levels = [
        pyo.value(var) for (p, i, j, c), var in mTEPES.vNetworkInvest.items()
        if (i, j, c) == (ni, nf, cc)
    ]
    assert invest_levels, (
        f"{forbid_line} is not in the candidate-line set — test case "
        "configuration drifted."
    )
    total_invest = sum(invest_levels)
    assert total_invest == pytest.approx(0.0, abs=1e-6), (
        f"InvestmentUp=0 did not enforce zero investment on {forbid_line}: "
        f"got vNetworkInvest sum = {total_invest}"
    )
