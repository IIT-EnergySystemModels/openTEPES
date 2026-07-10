"""Input-validation checks for the heat sector in openTEPES_DataConfiguration.

A non-boiler CHP needs a positive electric and heat power range, otherwise the
power-to-heat ratio (pRatedMaxPowerElec - pRatedMinPowerElec) / (pRatedMaxPowerHeat
- pRatedMinPowerHeat) is zero or divides by zero, which used to crash later with an
opaque ZeroDivisionError. The guard now raises a clear error naming the unit.

These tests take the bundled 9n_heat case (pIndHeat=1, one CHP: CHP_4), copy it,
break one range, and assert the guard fires.
"""
import os
import shutil

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _prepare_case(tmp_path, edit):
    """Copy 9n_heat into tmp_path under a new name, apply `edit` to the generation frame, return (dir, name)."""
    name = "9n_bad"
    case_dir = tmp_path / name
    shutil.copytree(os.path.join(CASES_DIR, "9n_heat"), case_dir)
    for f in os.listdir(case_dir):
        if "9n_heat" in f:
            os.rename(case_dir / f, case_dir / f.replace("9n_heat", name))

    gen_file = case_dir / f"oT_Data_Generation_{name}.csv"
    df = pd.read_csv(gen_file, index_col=0)
    edit(df)
    df.to_csv(gen_file)
    return str(tmp_path), name


def test_chp_zero_heat_range_raises(tmp_path):
    def edit(df):
        df.loc["CHP_4", "MaximumPowerHeat"] = df.loc["CHP_4", "MinimumPowerHeat"]

    DirName, CaseName = _prepare_case(tmp_path, edit)
    with pytest.raises(ValueError, match=r"### CHP CHP_4 has a non-positive heat"):
        openTEPES_run(DirName, CaseName, "gurobi", 0, 0)


def test_chp_zero_electric_range_raises(tmp_path):
    def edit(df):
        df.loc["CHP_4", "MaximumPower"] = df.loc["CHP_4", "MinimumPower"]

    DirName, CaseName = _prepare_case(tmp_path, edit)
    with pytest.raises(ValueError, match=r"### CHP CHP_4 has a non-positive electric"):
        openTEPES_run(DirName, CaseName, "gurobi", 0, 0)
