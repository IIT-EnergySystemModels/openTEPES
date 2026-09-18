"""A line marked switchable can be taken out of service, and carries nothing while it is out.

The ``Switching`` column of the network table frees the commitment of a line that would otherwise be
fixed in service, and brings in the on/off state constraints and the minimum switch-on and
switch-off times. No shipped case sets it, in any of its sixteen network tables, so none of that was
built in a solve.

Here one existing AC line of 9n is made switchable, with a binary commitment and a four-hour minimum
switch-on and switch-off time. Measured on that run: the line is out of service in 72 of the 84 load
levels, and the cost is 239.275 MEUR against 238.514 with the line fixed in. A higher cost with more
freedom is the 1 % relative MIP gap openTEPES asks HiGHS for, not a defect -- 0.3 % sits inside it --
so neither the cost nor the number of hours out is asserted below. What is asserted holds at any
gap: the line is read as switchable, the state constraints are built, and an open line carries no
flow. Commitment variables are not checked for being free, because openTEPES fixes every binary and
re-solves the linear problem to recover the marginal prices, so they are all fixed once a run ends.
"""
import os

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case, rows_of

CASE = "9n"
LINE = ("Node_4", "Node_9", "ac1")
OTHER_LINE = ("Node_3", "Node_4", "ac1")


def _solve(tmp_path, switchable: bool):
    case_dir, run_kwargs = week_of_case(CASE, tmp_path)

    if switchable:
        network_csv = os.path.join(case_dir, f"oT_Data_Network_{CASE}.csv")
        network = pd.read_csv(network_csv)
        row = ((network["InitialNode"] == LINE[0]) & (network["FinalNode"] == LINE[1])
               & (network["Circuit"] == LINE[2]))
        assert row.sum() == 1, f"{LINE} is not one line of the shipped network table"
        network.loc[row, "Switching"] = 1
        # Four hours, which is two load levels at the 2-hour time step of 9n. The switching times have
        # to exceed one load level or the state constraints are skipped as trivial.
        network.loc[row, ["SwOnTime", "SwOffTime"]] = 4
        network.to_csv(network_csv, index=False)

        option_csv = os.path.join(case_dir, f"oT_Data_Option_{CASE}.csv")
        option = pd.read_csv(option_csv)
        option["IndBinLineCommit"] = 1
        option.to_csv(option_csv, index=False)

    return openTEPES_run(**run_kwargs)


@pytest.mark.solve
def test_a_line_that_is_not_switchable_stays_in_service(tmp_path):
    """The shipped state of every case: no switchable line, and no switching constraint."""
    mTEPES = _solve(tmp_path, switchable=False)

    assert len(mTEPES.ls) == 0, "9n has no switchable line, so the set should be empty"
    assert rows_of(mTEPES, "eSWOnOff") == 0
    assert rows_of(mTEPES, "eMinSwOnState") == 0
    assert rows_of(mTEPES, "eMinSwOffState") == 0

    for p, sc, n in mTEPES.psn:
        assert mTEPES.vLineCommit[(p, sc, n) + LINE]() == 1.0


@pytest.mark.solve
def test_a_switchable_line_carries_nothing_while_it_is_out(tmp_path):
    """The commitment is free, the switching constraints are built, and the flow follows the state."""
    mTEPES = _solve(tmp_path, switchable=True)

    assert LINE in mTEPES.ls, "the line was not read as switchable"
    assert rows_of(mTEPES, "eSWOnOff") > 0, "the on/off state constraint was not built"
    assert rows_of(mTEPES, "eMinSwOnState") > 0, "the minimum switch-on time was not built"
    assert rows_of(mTEPES, "eMinSwOffState") > 0, "the minimum switch-off time was not built"

    for p, sc, n in mTEPES.psn:
        pCommit = mTEPES.vLineCommit[(p, sc, n) + LINE]
        assert mTEPES.vLineCommit[(p, sc, n) + OTHER_LINE]() == 1.0, (
            "a line that was not marked switchable should stay in service")

        assert min(abs(pCommit() - 0.0), abs(pCommit() - 1.0)) < 1e-5, (
            f"the commitment at {n} is {pCommit():.6f}, which is neither in nor out of service")
        if pCommit() < 0.5:
            assert abs(mTEPES.vFlowElec[(p, sc, n) + LINE]()) < 1e-5, (
                f"the line carries {mTEPES.vFlowElec[(p, sc, n) + LINE]():.6f} GW at {n} while it is switched out")
