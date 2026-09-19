"""A storage unit told its outflows and its charging are incompatible must not do both at once.

``OutflowsIncompatibility`` puts the energy outflows and the charge second block of one unit under a
single capacity limit, so the unit cannot draw a full charge while it is also delivering its outflow.
No shipped case sets the column, so ``eChargeOutflows`` was never built in a solve.

9n_ELZ is the case for it: its two electrolyzers charge up to 200 MW and carry a 9 MW energy outflow,
which is the documented archetype the constraint is written for. Solved without the column, seven
hours of the week put outflows and charging together at up to twice the block. With it, none do, and
the cost is unchanged at 242.89492215 MEUR -- the electrolyzer moves its charging rather than pay
more for it.
"""
import os

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case, rows_of

CASE = "9n_ELZ"


def _solve(tmp_path, incompatible: bool):
    case_dir, run_kwargs = week_of_case(CASE, tmp_path)

    gen_csv = os.path.join(case_dir, f"oT_Data_Generation_{CASE}.csv")
    gen = pd.read_csv(gen_csv)
    elz = gen.index[gen["Generator"].str.startswith("Electrolyzer")]
    gen["OutflowsIncompatibility"] = 0
    if incompatible:
        gen.loc[elz, "OutflowsIncompatibility"] = 1
    gen.to_csv(gen_csv, index=False)

    return openTEPES_run(**run_kwargs)


def _utilisation(mTEPES):
    """Outflows plus charge second block over the block itself, for every unit and hour that has one."""
    for p, sc, n in mTEPES.psn:
        for eh in mTEPES.eh:
            if (p, sc, eh) not in mTEPES.eo:
                continue
            pMax = mTEPES.pMaxCharge2ndBlock[p, sc, n, eh]
            if pMax == 0.0:
                continue
            pUsed = mTEPES.vEnergyOutflows[p, sc, n, eh]() + mTEPES.vCharge2ndBlock[p, sc, n, eh]()
            yield eh, n, pUsed / pMax


@pytest.mark.solve
def test_the_constraint_is_built_only_when_the_column_asks_for_it(tmp_path):
    """Which is what every shipped case leaves unasked."""
    assert rows_of(_solve(tmp_path, incompatible=False), "eChargeOutflows") == 0


@pytest.mark.solve
def test_charge_and_outflows_share_one_capacity(tmp_path):
    """Together they may not exceed the charge second block, which is the whole of the constraint."""
    mTEPES = _solve(tmp_path, incompatible=True)

    assert rows_of(mTEPES, "eChargeOutflows") > 0, "the constraint was not built"

    pRatios = {}
    for eh, n, pRatio in _utilisation(mTEPES):
        if mTEPES.pIndOutflowIncomp[eh] == 0:
            continue
        assert pRatio <= 1 + 1e-6, f"{eh} at {n} uses {pRatio:.4f} of its block for outflows and charging together"
        pRatios[(eh, n)] = pRatio

    assert pRatios, "no unit carried both outflows and a charge block, so nothing was tested"
    assert max(pRatios.values()) > 1 - 1e-6, (
        "no hour reaches the shared limit, so the run says nothing about a constraint that binds")
