import os
import pytest
import pyomo.environ as pyo
import numpy as np
import pandas as pd

from openTEPES.openTEPES import openTEPES_run

CASE_NAMES     = ["9n", "sSEP"]  # Add more case names as needed
EXPECTED_COSTS = {"9n": 249.5625364481767, "sSEP": 38623.89741870424}

@pytest.fixture
def case_7d_system(case_name):
    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES")
        ),
        CaseName=case_name,
        # SolverName="appsi_highs",
        SolverName="glpk",
        pIndLogConsole=0,
        pIndOutputResults=0,
    )
    duration_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_Duration_{data['CaseName']}.csv"
    )
    RESEnergy_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_RESEnergy_{data['CaseName']}.csv"
    )
    stage_csv = os.path.join(
        data["DirName"], data["CaseName"], f"oT_Data_Stage_{data['CaseName']}.csv"
    )
    original_duration_df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    original_resenergy_df = pd.read_csv(RESEnergy_csv, index_col=[0, 1])
    original_stage_df = pd.read_csv(stage_csv, index_col=[0])
    try:
        df = original_duration_df.copy()
        df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
        df.to_csv(duration_csv)

        df = original_resenergy_df.copy()
        df.iloc[0:, df.columns.get_loc("RESEnergy")] = np.nan
        df.to_csv(RESEnergy_csv)

        df = original_stage_df.copy()
        df.iloc[0:, df.columns.get_loc("Weight")] = 52
        df.to_csv(stage_csv)

        yield data
    finally:
        original_duration_df.to_csv(duration_csv)
        original_resenergy_df.to_csv(RESEnergy_csv)
        original_stage_df.to_csv(stage_csv)


def test_openTEPES_run(CASE_NAMES, EXPECTED_COSTS):
    for case_name in CASE_NAMES:
        mTEPES = openTEPES_run(**case_7d_system(case_name))
        assert mTEPES is not None
        np.testing.assert_approx_equal(pyo.value(mTEPES.eTotalSCost), EXPECTED_COSTS[case_name])
