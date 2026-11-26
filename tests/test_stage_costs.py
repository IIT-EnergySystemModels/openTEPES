"""Cost of every period in the cost summary and the run status, for a joint solve and for one solve per period.

With the investment decisions ignored and no RES or emission target, openTEPES solves each period separately. Its constraints are then
deactivated; however, its operation cost variables remain in the total system cost, and each subsequent solve sets them to zero. The cost of
each solve is therefore stored and restored once all solves are complete.
"""
import json
import os
import re
import shutil

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _day_per_period(dest_root, pPerPeriod, pTwoScenarios=False):
    """Case 9n7y with each of its seven periods reduced to the first 24 load levels, in one stage weighted to a year."""
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
        # with the investment decisions and the RES target ignored, the case is an operation model solved one period at a time
        option_csv = os.path.join(case_dir, 'oT_Data_Option_9n7y.csv')
        df = pd.read_csv(option_csv)
        for c in ('IndBinGenInvest', 'IndBinGenRetirement', 'IndBinRsrInvest', 'IndBinNetInvest', 'IndBinNetH2Invest', 'IndBinNetHeatInvest'):
            df[c] = 2
        df.to_csv(option_csv, index=False)
        res_csv = os.path.join(case_dir, 'oT_Data_RESEnergy_9n7y.csv')
        df = pd.read_csv(res_csv)
        df['RESEnergy'] = 0
        df.to_csv(res_csv, index=False)
    if pTwoScenarios:
        # a second scenario with 10 % more demand; each scenario has probability 0.5
        for f in sorted(os.listdir(case_dir)):
            if not f.startswith('oT_Data_'):
                continue
            df = pd.read_csv(os.path.join(case_dir, f), encoding='utf-8-sig')
            if 'Scenario' not in df.columns:
                continue
            sc2 = df.copy()
            sc2['Scenario'] = 'sc02'
            if f.startswith('oT_Data_Demand'):
                sc2[sc2.columns[3:]] *= 1.1
            if f.startswith('oT_Data_Scenario'):
                df['Probability']  = 0.5
                sc2['Probability'] = 0.5
            pd.concat([df, sc2]).to_csv(os.path.join(case_dir, f), index=False)
        pd.DataFrame({'Scenario': ['sc01', 'sc02']}).to_csv(os.path.join(case_dir, 'oT_Dict_Scenario_9n7y.csv'), index=False)
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

    # every period carries its generation cost, not only the last period solved
    pGeneration = pSummary[pSummary['Cost'] == 'Operation Cost Generation'].set_index('Period')['MEUR']
    assert (pGeneration > 0.0).all(), pGeneration.to_dict()

    # the cost summary, the run status and the model all equal the sum of the separate solves
    pTotal = pSummary[~pSummary['Cost'].str.contains('not in total')]['MEUR'].sum()
    assert pTotal                     == pytest.approx(sum(pSolveCosts), rel=1e-9)
    assert pStatus['total_cost_meur'] == pytest.approx(sum(pSolveCosts), rel=1e-9)
    assert mTEPES.vTotalSCost()       == pytest.approx(sum(pSolveCosts), rel=1e-9)


@pytest.mark.solve
def test_a_joint_solve_is_reported_as_before(tmp_path):
    mTEPES, pSummary, pStatus = _day_per_period(tmp_path, pPerPeriod=False)
    pTotal = pSummary[~pSummary['Cost'].str.contains('not in total')]['MEUR'].sum()
    assert pTotal                     == pytest.approx(mTEPES.vTotalSCost(), rel=1e-9)
    assert pStatus['total_cost_meur'] == pytest.approx(mTEPES.vTotalSCost(), rel=1e-12)


@pytest.mark.solve
def test_scenarios_solved_separately_are_weighted_by_their_probability(tmp_path, capsys):
    mTEPES, pSummary, pStatus = _day_per_period(tmp_path, pPerPeriod=True, pTwoScenarios=True)
    pSolveCosts = [float(x) for x in re.findall(r'Total system\s+cost \[MEUR\]\s+([0-9.eE+-]+)', capsys.readouterr().out)]
    assert len(pSolveCosts) == 2 * len(mTEPES.p)

    # each solve is weighted by the probability of its scenario, as the objective is, so the summary reports the expected cost, not the sum
    pTotal = pSummary[~pSummary['Cost'].str.contains('not in total')]['MEUR'].sum()
    assert all(mTEPES.pScenProb[p,sc]() == 0.5 for p,sc in mTEPES.ps)
    assert pTotal                     == pytest.approx(sum(pSolveCosts), rel=1e-9)
    assert pStatus['total_cost_meur'] == pytest.approx(sum(pSolveCosts), rel=1e-9)
