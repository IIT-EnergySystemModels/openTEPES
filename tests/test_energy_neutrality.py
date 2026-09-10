"""Energy neutrality has to account for the round-trip losses.

A storage unit marked neutral must exchange no net electricity with the system over its EnergyType
period. eESSInventory stores sqrt(eff) of what the unit takes and drains output/sqrt(eff) to deliver,
so a closed cycle gives output = eff x charge. Asking instead for output = charge is a second and
contradictory condition, and for any unit below 100 % efficiency the only point satisfying both is
zero: the unit is pinned idle and the cost rises, with nothing to say why.

No shipped case sets EnergyNeutrality, so nothing exercised this.
"""
import os
import shutil

import numpy as np
import pandas as pd
import pyomo.environ as pyo
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))
_pCopies = [0]


def _solve(tmp_path, neutral: bool, efficiency: float):
    """Solve a week of 9n with its storage unit at the given efficiency, neutral or not."""
    _pCopies[0] += 1
    root = tmp_path / f"c{_pCopies[0]}"
    root.mkdir()
    case_dir = root / "9n"
    shutil.copytree(os.path.join(CASES_DIR, "9n"), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))

    pDur = case_dir / "oT_Data_Duration_9n.csv"
    df = pd.read_csv(pDur, index_col=[0, 1, 2])
    df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
    df.to_csv(pDur)

    pRes = case_dir / "oT_Data_RESEnergy_9n.csv"
    df = pd.read_csv(pRes, index_col=[0, 1])
    df["RESEnergy"] = np.nan
    df.to_csv(pRes)

    pGen = case_dir / "oT_Data_Generation_9n.csv"
    gen = pd.read_csv(pGen)
    pEss = gen.index[pd.to_numeric(gen["MaximumCharge"], errors="coerce").fillna(0) > 0]
    gen["EnergyNeutrality"] = 0
    if neutral:
        gen.loc[pEss, "EnergyNeutrality"] = 1
    gen.loc[pEss, "Efficiency"] = efficiency
    gen["EnergyType"] = gen["EnergyType"].astype(object)   # empty columns read as float; pandas 3 refuses a string
    gen.loc[pEss, "EnergyType"] = "Daily"
    gen.to_csv(pGen, index=False)

    return openTEPES_run(str(root), "9n", "highs", 0, 0)


def _totals(mTEPES, es):
    pDur = lambda p, sc, n: mTEPES.pDuration[p, sc, n]()
    pOut = sum(pDur(p, sc, n) * mTEPES.vTotalOutput   [p, sc, n, es]() for p, sc, n in mTEPES.psn)
    pIn  = sum(pDur(p, sc, n) * mTEPES.vESSTotalCharge[p, sc, n, es]() for p, sc, n in mTEPES.psn)
    return pOut, pIn


@pytest.mark.solve
def test_a_lossy_unit_still_cycles_under_neutrality(tmp_path):
    """The defect this closes: a 90 % efficient unit was pinned idle by its own constraint.

    Before the losses were carried, charge and discharge both came out at 0.0000 against 0.0629 and
    0.0566 without the constraint, and the cost rose because the system lost the arbitrage.
    """
    mTEPES = _solve(tmp_path, neutral=True, efficiency=0.9)

    for es in mTEPES.es:
        pOut, pIn = _totals(mTEPES, es)
        assert pIn  > 0.0, f"{es} charges nothing; the neutrality constraint has pinned it idle"
        assert pOut > 0.0, f"{es} discharges nothing; the neutrality constraint has pinned it idle"


@pytest.mark.solve
def test_neutrality_balances_after_losses(tmp_path):
    """Delivering E takes E/eff from the system, so a neutral unit satisfies output = eff x charge."""
    mTEPES = _solve(tmp_path, neutral=True, efficiency=0.9)

    for es in mTEPES.es:
        pOut, pIn = _totals(mTEPES, es)
        assert pIn > 0.0, f"{es} is idle, which satisfies the ratio below for the wrong reason"
        assert pOut == pytest.approx(0.9 * pIn, rel=1e-6), (
            f"{es} returns {pOut:.4f} for {pIn:.4f} taken, which is not neutral after 90 % losses")


@pytest.mark.solve
def test_a_lossless_unit_balances_one_for_one(tmp_path):
    """At 100 % efficiency the constraint is output = charge, which is where it started."""
    mTEPES = _solve(tmp_path, neutral=True, efficiency=1.0)

    for es in mTEPES.es:
        pOut, pIn = _totals(mTEPES, es)
        assert pIn > 0.0
        assert pOut == pytest.approx(pIn, rel=1e-6)


@pytest.mark.solve
def test_the_requirement_is_built_only_when_asked_for(tmp_path):
    """A case that sets no EnergyNeutrality carries no such constraint, which is every shipped case."""
    mTEPES = _solve(tmp_path, neutral=False, efficiency=0.9)

    pRows = sum(len(c) for c in mTEPES.component_objects(pyo.Constraint)
                if c.name.startswith("eEnergyNeutrality"))
    assert pRows == 0
