"""Hydrogen source cost in the cost summary.

The cost of hydrogen from reforming or imports enters the total system cost through vTotalH2SrcCost. The cost summary reports it in its own row,
so that the rows add up to the total system cost. A case without a hydrogen source writes the same rows as before.
"""
import os
import shutil

import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))
ROW       = 'Operation Cost Hydrogen Sources'


def _day_of_9nH2(dest_root, pWithSource):
    """Case 9nH2 reduced to its first 24 load levels without its RES target, optionally with a reformer of 0.5 tH2/h at 2000 EUR/tH2 on Node_1."""
    case_dir = os.path.join(str(dest_root), '9nH2')
    shutil.copytree(os.path.join(CASES_DIR, '9nH2'), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))
    duration_csv = os.path.join(case_dir, 'oT_Data_Duration_9nH2.csv')
    df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    df.loc[df.groupby(level=[0, 1]).cumcount().to_numpy() >= 24, 'Duration'] = float('nan')
    df.to_csv(duration_csv)
    # the yearly RES target cannot be met in one day
    res_csv = os.path.join(case_dir, 'oT_Data_RESEnergy_9nH2.csv')
    if os.path.exists(res_csv):
        df = pd.read_csv(res_csv, encoding='utf-8-sig')
        df['RESEnergy'] = 0
        df.to_csv(res_csv, index=False)
    if pWithSource:
        generation_csv = os.path.join(case_dir, 'oT_Data_Generation_9nH2.csv')
        df  = pd.read_csv(generation_csv, encoding='utf-8-sig')
        row = df[df['Generator'] == 'CCGT_4'].copy()
        row['Generator'] = 'SMR_1'
        for c in ('MaximumPower', 'MinimumPower', 'FixedInvestmentCost'):
            row[c] = 0.0
        row['MaximumProductionH2'] = 0.5
        row['ProductionCostH2']    = 0.002
        pd.concat([df, row]).to_csv(generation_csv, index=False)
        dict_csv = os.path.join(case_dir, 'oT_Dict_Generation_9nH2.csv')
        df = pd.read_csv(dict_csv, encoding='utf-8-sig')
        pd.concat([df, pd.DataFrame({df.columns[0]: ['SMR_1']})]).to_csv(dict_csv, index=False)
    mTEPES   = openTEPES_run(str(dest_root), '9nH2', 'highs', 0, 0)
    pSummary = pd.read_csv(os.path.join(case_dir, 'oT_Result_CostSummary_9nH2.csv'))
    return mTEPES, pSummary[~pSummary['Cost'].str.contains('not in total')]


@pytest.mark.solve
def test_the_cost_summary_includes_the_hydrogen_source_cost(tmp_path):
    mTEPES, pSummary = _day_of_9nH2(tmp_path, pWithSource=True)
    pScenFactor = {(p,sc): mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() for p,sc in mTEPES.ps}
    pSourceCost = sum(pScenFactor[p,sc] * mTEPES.vTotalH2SrcCost[p,sc,n]() for p,sc,n in mTEPES.psn)
    assert pSourceCost > 0.0
    assert pSummary[pSummary['Cost'] == ROW]['MEUR'].sum() == pytest.approx(pSourceCost, rel=1e-9)
    assert pSummary['MEUR'].sum()                          == pytest.approx(mTEPES.vTotalSCost(), rel=1e-9)


@pytest.mark.solve
def test_a_case_without_a_hydrogen_source_has_no_such_row(tmp_path):
    mTEPES, pSummary = _day_of_9nH2(tmp_path, pWithSource=False)
    assert not mTEPES.sr
    assert ROW not in set(pSummary['Cost'])
    assert pSummary['MEUR'].sum() == pytest.approx(mTEPES.vTotalSCost(), rel=1e-9)
