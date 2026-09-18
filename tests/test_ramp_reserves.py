"""A ramp reserve requirement has to be held by units that can actually ramp.

Ramp reserves are switched on by the presence of the ``RampReserveUp`` and ``RampReserveDown`` files.
sSEP ships both, which is why the switch reads as covered, but every cell in them is empty: the
requirement is zero at every hour, so ``eSystemRampUp`` and ``eSystemRampDw`` are skipped and nothing
is ever built. This writes a requirement that is not zero.

The requirement is a ramp rate in MW/h, and the held reserve is an amount, so the constraint divides
by the hours in the load level before comparing.
"""
import os

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case, rows_of

CASE = "9n"
REQUIREMENT = 10.0   # MW/h, small enough that the thermal fleet can hold it in every hour


def _solve(tmp_path, required: bool):
    case_dir, run_kwargs = week_of_case(CASE, tmp_path)

    if required:
        # The reserve files share their index with the operating reserve table, so it is borrowed here.
        index = pd.read_csv(os.path.join(case_dir, f"oT_Data_OperatingReserveUp_{CASE}.csv"), index_col=[0, 1, 2])
        for direction in ("Up", "Down"):
            requirement = pd.DataFrame(REQUIREMENT, index=index.index, columns=index.columns)
            requirement.to_csv(os.path.join(case_dir, f"oT_Data_RampReserve{direction}_{CASE}.csv"))

    return openTEPES_run(**run_kwargs)


def _ramping(mTEPES):
    """Units that count towards the system ramp: every non-storage unit, and storage that can charge."""
    return [nr for nr in mTEPES.nr
            if nr not in mTEPES.es or mTEPES.pTotalMaxCharge[nr] + mTEPES.pTotalEnergyInflows[nr]]


@pytest.mark.solve
def test_no_ramp_constraint_without_a_requirement(tmp_path):
    """The shipped state of every case, sSEP's empty files included."""
    mTEPES = _solve(tmp_path, required=False)

    assert mTEPES.pIndRampReserves() == 0
    assert rows_of(mTEPES, "eSystemRampUp") == 0
    assert rows_of(mTEPES, "eSystemRampDw") == 0


@pytest.mark.solve
def test_the_ramp_requirement_is_met_in_every_hour(tmp_path):
    """Held reserve over the hours of the load level covers the required ramp rate."""
    mTEPES = _solve(tmp_path, required=True)

    assert mTEPES.pIndRampReserves() == 1
    assert rows_of(mTEPES, "eSystemRampUp") > 0, "the up ramp constraint was not built"
    assert rows_of(mTEPES, "eSystemRampDw") > 0, "the down ramp constraint was not built"

    for p, sc, n in mTEPES.psn:
        pHours = mTEPES.pDuration[p, sc, n]()
        for var, par, name in ((mTEPES.vRampReserveUp, mTEPES.pRampReserveUp, "up"),
                               (mTEPES.vRampReserveDw, mTEPES.pRampReserveDw, "down")):
            pRequired = sum(par[p, sc, n, ar] for ar in mTEPES.ar)
            pHeld     = sum(var[p, sc, n, nr]() for nr in _ramping(mTEPES) if (p, nr) in mTEPES.pnr)
            assert pRequired == pytest.approx(REQUIREMENT * 1e-3), "the requirement did not reach the model"
            assert pHeld / pHours >= pRequired - 1e-9, (
                f"the {name} ramp held at {n} is {pHeld / pHours:.6f} GW/h against {pRequired:.6f} required")
