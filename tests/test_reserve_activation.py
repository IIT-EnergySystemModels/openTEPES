"""Activated operating reserve has to be delivered, and only by units that hold the reserve.

Reserve activation is switched on by the presence of the ``OperatingReserveUpEnergy`` and
``OperatingReserveDownEnergy`` files. No shipped case has them, so ``eOperReserveUpEnergy`` and
``eOperReserveDwEnergy`` were built by no solve, and neither were the constraints tying the activated
energy to the reserve held.

The two files are written here from the case's own reserve requirement, at half of it, so the
requested activation is always something the held reserve can cover.
"""
import os

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case, rows_of

CASE = "9n"
SHARE = 0.5


def _solve(tmp_path, activated: bool):
    case_dir, run_kwargs = week_of_case(CASE, tmp_path)

    if activated:
        for direction in ("Up", "Down"):
            reserve = pd.read_csv(os.path.join(case_dir, f"oT_Data_OperatingReserve{direction}_{CASE}.csv"),
                                  index_col=[0, 1, 2])
            (reserve * SHARE).to_csv(os.path.join(case_dir, f"oT_Data_OperatingReserve{direction}Energy_{CASE}.csv"))

    return openTEPES_run(**run_kwargs)


def _activated(mTEPES, p, sc, n, up: bool):
    """Energy activated at one hour, over the generators and the storage units together [GW]."""
    pGen = mTEPES.vReserveUpEnergy if up else mTEPES.vReserveDownEnergy
    pEss = mTEPES.vESSReserveUpEnergy if up else mTEPES.vESSReserveDownEnergy
    return (sum(pGen[p, sc, n, nr]() for nr in mTEPES.nr if (p, nr) in mTEPES.pnr and mTEPES.pIndOperReserveGen[nr] == 0)
            + sum(pEss[p, sc, n, eh]() for eh in mTEPES.eh if (p, eh) in mTEPES.peh and mTEPES.pIndOperReserveCon[eh] == 0))


@pytest.mark.solve
def test_no_activation_constraint_without_the_files(tmp_path):
    """Which is every shipped case."""
    mTEPES = _solve(tmp_path, activated=False)

    assert mTEPES.pIndReserveActivation() == 0
    assert rows_of(mTEPES, "eOperReserveUpEnergy") == 0
    assert rows_of(mTEPES, "eOperReserveDwEnergy") == 0


@pytest.mark.solve
def test_the_activation_asked_for_is_delivered(tmp_path):
    """Every hour, the reserve activated across the system equals the requirement of that hour."""
    mTEPES = _solve(tmp_path, activated=True)

    assert mTEPES.pIndReserveActivation() == 1
    assert rows_of(mTEPES, "eOperReserveUpEnergy") > 0, "the up activation constraint was not built"
    assert rows_of(mTEPES, "eOperReserveDwEnergy") > 0, "the down activation constraint was not built"

    for p, sc, n in mTEPES.psn:
        for up, name in ((True, "up"), (False, "down")):
            pReq = sum(mTEPES.pOperReserveUpEnergy[p, sc, n, ar] if up else mTEPES.pOperReserveDwEnergy[p, sc, n, ar]
                       for ar in mTEPES.ar)
            assert pReq > 0.0, f"the {name} requirement at {n} is zero, so the constraint is skipped there"
            assert _activated(mTEPES, p, sc, n, up) == pytest.approx(pReq, rel=1e-6, abs=1e-9), (
                f"the {name} activation at {n} does not meet its {pReq:.6f} GW requirement")


@pytest.mark.solve
def test_a_unit_can_activate_only_the_reserve_it_holds(tmp_path):
    """Activated energy is capped by the reserve the same unit is holding at the same hour."""
    mTEPES = _solve(tmp_path, activated=True)

    for p, sc, n in mTEPES.psn:
        for nr in mTEPES.nr:
            if (p, nr) not in mTEPES.pnr or mTEPES.pIndOperReserveGen[nr] != 0:
                continue
            assert mTEPES.vReserveUpEnergy[p, sc, n, nr]() <= mTEPES.vReserveUp[p, sc, n, nr]() + 1e-9, (
                f"{nr} at {n} activates more upward energy than the reserve it holds")
            assert mTEPES.vReserveDownEnergy[p, sc, n, nr]() <= mTEPES.vReserveDown[p, sc, n, nr]() + 1e-9, (
                f"{nr} at {n} activates more downward energy than the reserve it holds")
