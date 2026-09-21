"""A unit writes its inventory as its own StorageType asks, unless something else reads it.

StorageType sets how often the state of charge is written down, OutflowsType the window for
delivering energy out, EnergyType the window for the energy bounds. The last two shorten the first,
which an EV fleet needs and a unit with neither does not. Every storage unit of every case used to
come out at one load level. Issue #194.
"""
import collections
import os
import pathlib
import shutil
import tempfile

import numpy as np
import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case


def _intervals(case, tmp_path):
    """Solve a week of a case and return the inventory interval of every storage unit."""
    _, run_kwargs = week_of_case(case, tmp_path)
    mTEPES = openTEPES_run(**run_kwargs)
    return mTEPES, {es: mTEPES.pStorageTimeStep[es] for es in mTEPES.es}


@pytest.mark.solve
def test_a_weekly_unit_with_nothing_reading_it_keeps_its_own_interval(tmp_path):
    """sSEP declares four, none with outflows or energy bounds."""
    mTEPES, pIntervals = _intervals("sSEP", tmp_path)

    pDeclared = {es: mTEPES.pStorageType[es] for es in mTEPES.es}
    pWeekly = [es for es, pType in pDeclared.items() if str(pType) == "Weekly"]
    assert pWeekly, "sSEP no longer declares a weekly storage unit"

    for es in pWeekly:
        assert pIntervals[es] > 1, (
            f"{es} is declared {pDeclared[es]} and writes its inventory every {pIntervals[es]} load "
            "level, so its column is governing nothing")


@pytest.mark.solve
def test_a_unit_delivering_outflows_is_still_shortened(tmp_path):
    """The 9n_ELZ electrolyzers owe a weekly outflow, the shape an EV fleet has. The outflow wins."""
    mTEPES, pIntervals = _intervals("9n_ELZ", tmp_path)

    pWithOutflows = [es for es in mTEPES.es if (list(mTEPES.p)[0], list(mTEPES.sc)[0], es) in mTEPES.eo]
    assert pWithOutflows, "9n_ELZ no longer carries a unit with energy outflows"

    for es in pWithOutflows:
        pOutflow = mTEPES.pOutflowsTimeStep[es]
        assert pIntervals[es] <= pOutflow, (
            f"{es} owes an outflow every {pOutflow} load levels and writes its inventory every "
            f"{pIntervals[es]}, so the delivery has no state of charge to be read against")


@pytest.mark.solve
def test_the_inventory_balance_reaches_back_over_the_interval(tmp_path):
    """An interval above one has to fit the stage it closes in."""
    mTEPES, pIntervals = _intervals("sSEP", tmp_path)

    pSpans = collections.Counter(pIntervals.values())
    assert max(pSpans) > 1, "no unit writes its inventory over more than one load level"

    for es, pInterval in pIntervals.items():
        if pInterval == 1:
            continue
        pLevels = [n for p, sc, n in mTEPES.psn]
        assert len(pLevels) >= pInterval, (
            f"{es} asks for {pInterval} load levels and the stage holds {len(pLevels)}")
