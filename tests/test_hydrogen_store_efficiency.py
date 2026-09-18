"""A hydrogen store loses something on the round trip, and the loss belongs in the inventory.

`eH2Inventory` used to add what went in and subtract what came out one for one, so a cavern was a
perfect buffer: a tonne in, a tonne out, forever. Every other store in the model pays a round trip.
The shape is the one `eESSInventory` already uses, the square root split evenly between the two
directions, so a tonne withdrawn has cost a tonne over the efficiency to put in.

The loss is in the inventory, not in `eBalanceH2`. The balance is what the node sees: the store
takes the hydrogen it takes and delivers the hydrogen it delivers. Putting the efficiency there too
would charge the same loss twice.

`EfficiencyH2` is optional and defaults to 1.0, so a case written before this reads exactly as it
did.
"""
import os
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

SRC = Path(__file__).resolve().parents[1] / "openTEPES" / "openTEPES_ModelFormulationHydrogen.py"


def _body(name):
    src = SRC.read_text()
    i = src.index(f"def {name}(")
    return src[i:src.index("setattr", i)]


def test_the_charge_is_multiplied_and_the_discharge_divided():
    body = _body("eH2Inventory")
    assert re.search(r"math\.sqrt\(mTEPES\.pEfficiencyH2\[hs\]\)", body), (
        "eH2Inventory must take the square root of pEfficiencyH2, as eESSInventory does for pEfficiency"
    )
    assert re.search(r"eta\s*\*\s*OptModel\.vH2StorCharge", body), "what goes in is scaled by the square root"
    assert re.search(r"OptModel\.vH2StorDischarge\[[^\]]+\]\s*/\s*eta", body), "what comes out is divided by it"


def test_the_balance_does_not_charge_the_loss_a_second_time():
    body = _body("eBalanceH2")
    assert "pEfficiencyH2" not in body, (
        "the round trip belongs in eH2Inventory; in eBalanceH2 it would be charged twice, once at "
        "the node and once in the store"
    )


def test_electricity_storage_uses_the_same_split():
    # the contrast is the point: this is not a new convention, it is the one the ESS already has
    src = (SRC.parent / "openTEPES_ModelFormulationElectricity.py").read_text()
    i = src.index("def eESSInventory(")
    body = src[i:src.index("setattr", i)]
    assert "math.sqrt(mTEPES.pEfficiency[es])" in body


def _efficiency_h2(cell_given, value=None):
    """The rule InputData applies. A blank cell and a zero both mean 'not given'."""
    if not cell_given:
        return 1.0
    if value is None or value != value or value == 0.0:   # absent, NaN, or a literal zero
        return 1.0
    return value


def test_absent_column_is_lossless():
    assert _efficiency_h2(cell_given=False) == 1.0


def test_a_given_efficiency_wins():
    assert _efficiency_h2(cell_given=True, value=0.9) == 0.9


def test_zero_is_not_a_store_that_swallows_everything():
    # 0.0 divides in eH2Inventory, so it is read as "not given" and warned about, exactly as Efficiency is
    assert _efficiency_h2(cell_given=True, value=0.0) == 1.0


def test_blank_cell_falls_back():
    assert _efficiency_h2(cell_given=True, value=float("nan")) == 1.0


@pytest.fixture
def case_9nH2_lossy_store(tmp_path):
    """9nH2 over a week, with a round trip of 0.9 on its cavern.

    None of the bundled cases carries EfficiencyH2, so a solved check needs one written here. The
    week is the truncation the other solve fixtures use, and the cavern cycles on it.
    """
    case = "9nH2"
    src = Path(__file__).resolve().parents[1] / "openTEPES" / "cases" / case
    dst = os.path.join(str(tmp_path), case)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))

    duration = os.path.join(dst, f"oT_Data_Duration_{case}.csv")
    df = pd.read_csv(duration, index_col=[0, 1, 2])
    df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
    df.to_csv(duration)

    # the annual RES-energy requirement is written for a year and a week cannot meet it, as the other 7-day fixtures also find
    res_energy = os.path.join(dst, f"oT_Data_RESEnergy_{case}.csv")
    df = pd.read_csv(res_energy, index_col=[0, 1])
    df["RESEnergy"] = np.nan
    df.to_csv(res_energy)

    generation = os.path.join(dst, f"oT_Data_Generation_{case}.csv")
    df = pd.read_csv(generation, index_col=0)
    df["EfficiencyH2"] = 1.0
    df.loc[df["MaximumStorageH2"].fillna(0.0) > 0.0, "EfficiencyH2"] = 0.9
    df.to_csv(generation)

    return dict(DirName=str(tmp_path), CaseName=case, SolverName="highs", pIndLogConsole=0, pIndOutputResults=0)


@pytest.mark.solve
def test_a_lossy_store_gives_back_its_round_trip(case_9nH2_lossy_store):
    """The round trip is the one the case asked for, measured on the solved model.

    Without the efficiency the store gives back every tonne, and the ratio below is 1.0 whatever
    EfficiencyH2 says.
    """
    mTEPES = openTEPES_run(**case_9nH2_lossy_store)

    pDur = lambda p, sc, n: mTEPES.pDuration[p, sc, n]()
    pIn = sum(pDur(p, sc, n) * (mTEPES.vH2StorCharge[p, sc, n, hs]() or 0.0)
              for p, sc, n in mTEPES.psn for hs in mTEPES.hs)
    pOut = sum(pDur(p, sc, n) * (mTEPES.vH2StorDischarge[p, sc, n, hs]() or 0.0)
               for p, sc, n in mTEPES.psn for hs in mTEPES.hs)

    assert all(mTEPES.pEfficiencyH2[hs] == 0.9 for hs in mTEPES.hs), "the case did not carry the efficiency"
    assert pIn > 1.0, "the store never charged, so the round trip is not exercised"
    assert pOut / pIn == pytest.approx(0.9, abs=1e-6), (
        f"the store gave back {pOut / pIn:.4f} of what it took, against the 0.9 round trip asked for")
