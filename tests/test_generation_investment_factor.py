"""oT_Data_GenerationInvestmentFactor scales the investment cost of a candidate by the period it is installed in.

vGenerationInvest is cumulative and its cost is paid in every period, so each increment must keep the factor of the
period it was built in. Multiplying the cumulative variable by the current factor would reprice the old capacity.
"""
import os
import shutil

import pandas as pd
import pyomo.environ as pyo
import pytest

from openTEPES.openTEPES import openTEPES_run
from openTEPES.openTEPES_ModelFormulationInvestment import GenInvestCost

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _vintage_model(pFactor):
    """One candidate over three periods, with half the unit built in 2030 and the other half in 2035."""
    m = pyo.ConcreteModel()
    m.p   = pyo.Set(initialize=[2030, 2035, 2040], ordered=True)
    m.peb = pyo.Set(initialize=[(p, 'g') for p in m.p], dimen=2)
    m.pGenInvestCost   = pyo.Param(['g'], initialize={'g': 100.0})
    m.pGenInvestFactor = pyo.Param(m.peb, initialize=pFactor, default=1.0)
    m.vGenerationInvest = pyo.Var(m.peb)
    for p, v in zip(m.p, [0.5, 1.0, 1.0]):
        m.vGenerationInvest[p, 'g'].fix(v)
    return m


def test_each_vintage_keeps_the_factor_of_its_period():
    m = _vintage_model({(2030, 'g'): 1.0, (2035, 'g'): 0.8, (2040, 'g'): 0.6})
    pCost = {p: pyo.value(GenInvestCost(m, m, p, 'g')) for p in m.p}
    # 100 x (0.5 x 1.0 + 0.5 x 0.8); nothing built in 2040, so its factor scales nothing
    assert pCost == pytest.approx({2030: 50.0, 2035: 90.0, 2040: 90.0})


def test_without_factors_the_cost_is_unchanged():
    m = _vintage_model({})
    for p in m.p:
        assert pyo.value(GenInvestCost(m, m, p, 'g')) == pytest.approx(100.0 * m.vGenerationInvest[p, 'g'].value)


def _day_per_period(dest_root, pFactorRows=None):
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
    if pFactorRows is not None:
        pd.DataFrame(pFactorRows, columns=['Period', 'Generator', 'Factor']).to_csv(
            os.path.join(case_dir, 'oT_Data_GenerationInvestmentFactor_9n7y.csv'), index=False)
    return openTEPES_run(str(dest_root), '9n7y', 'highs', 0, 0)


@pytest.mark.solve
def test_factors_of_one_leave_the_case_as_it_was(tmp_path):
    pBase = _day_per_period(tmp_path / 'base')
    pOnes = _day_per_period(tmp_path / 'ones', [(p, 'SolarPV_2', 1.0) for p in pBase.p])
    assert pOnes.vTotalSCost() == pytest.approx(pBase.vTotalSCost(), rel=1e-9)


@pytest.mark.solve
def test_a_learning_curve_is_paid_per_vintage(tmp_path, capsys):
    pFactor = dict(zip([2020, 2025, 2030, 2035, 2040, 2045, 2050], [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]))
    m = _day_per_period(tmp_path, [(p, 'SolarPV_2', f) for p, f in pFactor.items()] + [(2030, 'NoSuchUnit', 0.5)])
    assert 'NoSuchUnit' in capsys.readouterr().out

    # the cost of each period, rebuilt by hand from the solved investment
    pInvest = [m.vGenerationInvest[p, 'SolarPV_2']() for p in m.p]
    pBuilt  = [pInvest[0]] + [b - a for a, b in zip(pInvest, pInvest[1:])]
    pCost   = [m.pGenInvestCost['SolarPV_2'] * sum(pFactor[pp] * d for pp, d in zip(list(m.p)[:i+1], pBuilt[:i+1])) for i in range(len(pBuilt))]
    assert [pyo.value(GenInvestCost(m, m, p, 'SolarPV_2')) for p in m.p] == pytest.approx(pCost)
    assert sum(pInvest) > 0.0
