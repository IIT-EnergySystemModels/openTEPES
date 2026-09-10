"""A cycle longer than the stage it must close inside is refused, not dropped.

When no load level qualifies the constraint is built with no rows and the model solves without it,
reporting a cost below the truth: issue #159 measured 10.4 per cent low on an energy limit. Nothing
says so, which is why this raises rather than warns.
"""
import os
import shutil

import numpy as np
import pandas as pd
import pytest
from pyomo.environ import ConcreteModel

from openTEPES.openTEPES_DataConfiguration import DataConfiguration
from openTEPES.openTEPES_InputData import InputData

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


_pCopies = [0]


def _case(tmp_path, hours, **columns):
    """Copy 9n, truncate it to `hours`, and set generation columns on its storage unit.

    Each call gets its own directory, so one test can configure the case more than once.
    """
    _pCopies[0] += 1
    root = tmp_path / f"c{_pCopies[0]}"
    root.mkdir()
    case_dir = root / "9n"
    shutil.copytree(os.path.join(CASES_DIR, "9n"), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))

    pDur = case_dir / "oT_Data_Duration_9n.csv"
    df = pd.read_csv(pDur, index_col=[0, 1, 2])
    df.iloc[hours:, df.columns.get_loc("Duration")] = np.nan
    df.to_csv(pDur)

    if columns:
        pGen = case_dir / "oT_Data_Generation_9n.csv"
        gen = pd.read_csv(pGen)
        pEss = gen.index[pd.to_numeric(gen["MaximumCharge"], errors="coerce").fillna(0) > 0]
        for col, val in columns.items():
            # A column nobody filled in is read as all-NaN and typed as a float, and pandas 3 refuses
            # to put a string into it. 9n leaves EnergyType empty, so the cast is what makes this work.
            gen[col] = gen[col].astype(object) if col in gen.columns else pd.Series(dtype=object)
            gen.loc[pEss, col] = val
        gen.to_csv(pGen, index=False)

    return str(root), "9n"


def _configure(tmp_path, hours, **columns):
    pDir, pCase = _case(tmp_path, hours, **columns)
    mTEPES = ConcreteModel(pCase)
    dfs, par = InputData(pDir, pCase, mTEPES, 0)
    DataConfiguration(mTEPES, dfs, par)
    return mTEPES


def test_a_case_whose_cycles_fit_is_untouched(tmp_path):
    """The shipped case at its own horizon has to keep working."""
    assert _configure(tmp_path, 8736) is not None


def test_the_seven_day_fixture_still_works(tmp_path):
    """The horizon every regression test uses. Refusing it would fail the suite, not protect it."""
    assert _configure(tmp_path, 168) is not None


@pytest.mark.parametrize("hours, columns, expected", [
    (168, {"EnergyType":  "Monthly"}, "EnergyType"),      # issue #159, the energy limit
    (24,  {"EnergyType":  "Weekly"},  "EnergyType"),      # the same, reaching energy neutrality
    (168, {"StorageType": "Yearly"},  "StorageType"),     # the inventory tracking step
])
def test_a_cycle_longer_than_the_stage_is_refused(tmp_path, hours, columns, expected):
    with pytest.raises(ValueError, match=expected):
        _configure(tmp_path, hours, **columns)


def test_the_message_says_what_to_change(tmp_path):
    """An error a user cannot act on barely improves on the silence it replaced."""
    with pytest.raises(ValueError) as pErr:
        _configure(tmp_path, 168, EnergyType="Monthly")
    pText = str(pErr.value)
    assert "84 load levels" in pText,  "the message should say what the stage holds"
    assert "ESS1" in pText,            "the message should name the unit"
    assert "Monthly" in pText,         "the message should name the period asked for"
    assert "longer stage" in pText,    "the message should say what to change"


def test_storage_tracking_is_measured_on_its_own_scale(tmp_path):
    """StorageType maps one period shorter than the other columns, deliberately.

    It sets how often the inventory is written down rather than the cycle itself, and a slow store
    needs that less often. Monthly storage is 168 hours of tracking and fits a week exactly; Monthly
    energy is 672 and does not. Pinned so the two scales are not "corrected" into one.
    """
    assert _configure(tmp_path, 168, StorageType="Monthly") is not None
    with pytest.raises(ValueError):
        _configure(tmp_path, 168, EnergyType="Monthly")


def test_hydrogen_cycles_are_checked_only_where_there_is_hydrogen(tmp_path):
    """StorageTypeH2 is filled in for every generator, coal and nuclear included.

    Checking it unconditionally refused every case with no hydrogen, which is all but three of those
    that ship. The check applies only to units carrying hydrogen storage.
    """
    assert _configure(tmp_path, 168, StorageTypeH2="Yearly") is not None


def test_a_shortened_storage_cycle_is_reported(tmp_path, capsys):
    """The storage cycle is the shortest of its three periods, so a setting made for outflows or an
    energy bound moves the inventory cycle too.

    Intended, and invisible until now. On 9n every unit comes out at one load level whatever
    StorageType says, because that case has neither outflows nor energy bounds and both default to
    one, and the results give no sign the declared period was not the one used.
    """
    _configure(tmp_path, 168, StorageType="Monthly")
    pOut = capsys.readouterr().out
    assert "storage cycle shortened from 84 to 1" in pOut, (
        "the run should say the declared cycle was not the one used")
