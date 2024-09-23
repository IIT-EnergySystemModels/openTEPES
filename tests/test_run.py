import os
import pytest
import pyomo.environ as pyo
import numpy as np
import pandas as pd

from openTEPES.openTEPES import openTEPES_run


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_test_case():
    """
    Set up the test case by modifying the necessary CSV files and preparing input data.
    Returns the data required for running openTEPES.
    """
    data = dict(
        DirName=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../openTEPES")
        ),
        CaseName="9n",
        SolverName="gurobi",  # You can change the solver here
        pIndLogConsole=0,
        pIndOutputResults=0,
    )

    print("Setting up test case...")  # Added print for console feedback
    duration_csv = os.path.join(data["DirName"], data["CaseName"], f"oT_Data_Duration_{data['CaseName']}.csv")
    RESEnergy_csv = os.path.join(data["DirName"], data["CaseName"], f"oT_Data_RESEnergy_{data['CaseName']}.csv")
    stage_csv = os.path.join(data["DirName"], data["CaseName"], f"oT_Data_Stage_{data['CaseName']}.csv")

    # Read original data
    original_duration_df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    original_resenergy_df = pd.read_csv(RESEnergy_csv, index_col=[0, 1])
    original_stage_df = pd.read_csv(stage_csv, index_col=[0])

    try:
        print("Modifying CSV files...")  # Added print for console feedback
        # Modify and save the modified DataFrames
        modify_and_save_csv(original_duration_df, "Duration", 169, duration_csv, 0)
        modify_and_save_csv(original_resenergy_df, "RESEnergy", 0, RESEnergy_csv, 0)
        modify_and_save_csv(original_stage_df, "Weight", 0, stage_csv, 1)

        yield data  # Yielding allows cleanup even if there's an early return or exception

    except Exception as e:
        logger.error(f"Error occurred during test setup: {e}")
        raise

    finally:
        print("Restoring original CSV files...")  # Added print for console feedback
        # Restore original data
        logger.info("Restoring original CSV files.")
        original_duration_df.to_csv(duration_csv)
        original_resenergy_df.to_csv(RESEnergy_csv)
        original_stage_df.to_csv(stage_csv)


def modify_and_save_csv(df, column_name, start_row, file_path, idx):
    """
    Modify the specified column starting from the given row, setting values to NaN, and save to the file.
    """
    df_copy = df.copy()
    if idx == 0:
        df_copy.iloc[start_row:, df_copy.columns.get_loc(column_name)] = np.nan
    elif idx == 1:
        df_copy.iloc[start_row:, df_copy.columns.get_loc(column_name)] = 52
    df_copy.to_csv(file_path)
    print(f"Modified {file_path} and saved.")  # Added print for console feedback


def test_openTEPES_run():
    """
    Test function for running openTEPES with the modified test case.
    Asserts the run was successful.
    """
    print("Starting the openTEPES run...")  # Added print for console feedback
    for case_data in setup_test_case():
        mTEPES = openTEPES_run(**case_data)

        assert mTEPES is not None, "openTEPES run failed, mTEPES object is None."
        logger.info(f"Test passed. Total system cost: {mTEPES.eTotalSCost}")
        print(f"Total system cost: {mTEPES.eTotalSCost}")  # Added print for console feedback
        np.testing.assert_approx_equal(pyo.value(mTEPES.eTotalSCost), 248.433199803524)

