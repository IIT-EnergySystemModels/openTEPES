"""The cost summary and the run status report the cost of every period, whether the periods are solved together or one at a time.

With the investment decisions ignored and no RES or emission target, openTEPES solves each period alone. Its constraints are then deactivated,
but its cost variables stay in the total system cost, so every later solve sets them to zero. The cost of each solve is kept and put back at the end.
"""
import json
import os
import re
import shutil

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _day_per_period(dest_root, pPerPeriod):
    """9n7y, its seven periods cut to the first 24 load levels each, in one stage weighted to a year."""
    case_dir = os.path.join(str(dest_root), '9n7y')
    shutil.copytree(os.path.join(CASES_DIR, '9n7y'), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))
    duration_csv = os.path.join(case_dir, 'oT_Data_Duration_9n7y.csv')
    df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    df.loc[df.groupby(level=[0, 1]).cumcount().to_numpy() >= 24, 'Duration'] = float('nan')
    df.to_csv(duration_csv)
    stage_csv = os.path.join(case_dir, 'oT_Data_Stage_9n7y.csv')
    df = pd.read_csv(stage_csv, index_col=[0])
    df['Weight'] = 0.0
    df.iloc[0, 0] = 365.0
    df.to_csv(stage_csv)
    if pPerPeriod:
        # ignoring the investment decisions and the RES target makes it an operation model solved one period at a time
        option_csv = os.path.join(case_dir, 'oT_Data_Option_9n7y.csv')
        df = pd.read_csv(option_csv)
        for c in ('IndBinGenInvest', 'IndBinGenRetirement', 'IndBinRsrInvest', 'IndBinNetInvest', 'IndBinNetH2Invest', 'IndBinNetHeatInvest'):
            df[c] = 2
        df.to_csv(option_csv, index=False)
        res_csv = os.path.join(case_dir, 'oT_Data_RESEnergy_9n7y.csv')
        df = pd.read_csv(res_csv)
        df['RESEnergy'] = 0
        df.to_csv(res_csv, index=False)
    mTEPES = openTEPES_run(str(dest_root), '9n7y', 'highs', 0, 0)
    pSummary = pd.read_csv(os.path.join(case_dir, 'oT_Result_CostSummary_9n7y.csv'))
    with open(os.path.join(case_dir, 'openTEPES_run_status_9n7y.json')) as f:
        pStatus = json.load(f)
    return mTEPES, pSummary, pStatus


@pytest.mark.solve
def test_a_period_solved_alone_keeps_its_cost(tmp_path, capsys):
    mTEPES, pSummary, pStatus = _day_per_period(tmp_path, pPerPeriod=True)
    pSolveCosts = [float(x) for x in re.findall(r'Total system\s+cost \[MEUR\]\s+([0-9.eE+-]+)', capsys.readouterr().out)]
    assert len(pSolveCosts) == len(mTEPES.p)

    # every period has its generation cost, not only the last one solved
    pGeneration = pSummary[pSummary['Cost'] == 'Operation Cost Generation'].set_index('Period')['MEUR']
    assert (pGeneration > 0.0).all(), pGeneration.to_dict()

    # the summary, the run status and the model add up to the sum of the separate solves
    pTotal = pSummary[~pSummary['Cost'].str.contains('not in total')]['MEUR'].sum()
    assert pTotal                     == pytest.approx(sum(pSolveCosts), rel=1e-9)
    assert pStatus['total_cost_meur'] == pytest.approx(sum(pSolveCosts), rel=1e-9)
    assert mTEPES.vTotalSCost()       == pytest.approx(sum(pSolveCosts), rel=1e-9)


@pytest.mark.solve
def test_a_joint_solve_keeps_the_cost_of_every_period(tmp_path):
    mTEPES, pSummary, pStatus = _day_per_period(tmp_path, pPerPeriod=False)
    pKept = {(p,sc,n) for pName,p,sc,n in mTEPES.pStageCostValues if pName == 'vTotalGCost'}
    assert pKept == set(mTEPES.psn)
    assert all(mTEPES.pStageCostValues['vTotalGCost',p,sc,n] == mTEPES.vTotalGCost[p,sc,n]() for p,sc,n in mTEPES.psn)
    assert pStatus['total_cost_meur'] == pytest.approx(mTEPES.vTotalSCost(), rel=1e-12)
