"""Reload of a solution file (from_solution).

A case reloaded from its solution file writes the same result files as the solve, without the solver. A solution that belongs to other inputs, to
other model settings, or to a model with other variables is refused before any result is written.
"""
import filecmp
import json
import os
import shutil

import pandas as pd
import pytest

import openTEPES.openTEPES as oT
from openTEPES.openTEPES import openTEPES_run
from openTEPES.openTEPES_OutputResultsSolution import SolutionMismatch, read_solution

from test_solution_file import _day_of_9n

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))
SPEC      = {'plots': False}


def _results(pDir):
    return sorted(f for f in os.listdir(pDir) if f.startswith('oT_Result_'))


def _same_results(pSolve, pReload):
    """The result files of the solve and of the reload, and those that differ byte for byte."""
    pA, pB = _results(pSolve), _results(pReload)
    return pA, pB, [f for f in pA if f in pB and not filecmp.cmp(os.path.join(pSolve, f), os.path.join(pReload, f), shallow=False)]


@pytest.fixture(scope='module')
def solved_9n(tmp_path_factory):
    """Case 9n reduced to 24 load levels, solved once with every result file and its solution file."""
    pRoot = tmp_path_factory.mktemp('reload')
    _day_of_9n(pRoot)
    openTEPES_run(str(pRoot), '9n', 'highs', 1, 0, output_spec=SPEC, out_path=str(pRoot / 'solve'), save_solution=True)
    return pRoot, str(pRoot / 'solve' / 'oT_Solution_9n.parquet')


@pytest.mark.solve
def test_a_reloaded_case_writes_the_same_result_files(solved_9n):
    pRoot, pFile = solved_9n
    openTEPES_run(str(pRoot), '9n', 'highs', 1, 0, output_spec=SPEC, out_path=str(pRoot / 'reload'), from_solution=pFile)
    pA, pB, pDiffer = _same_results(str(pRoot / 'solve'), str(pRoot / 'reload'))
    assert len(pA) > 50
    assert pA == pB
    assert pDiffer == []
    with open(pRoot / 'reload' / 'openTEPES_run_status_9n.json') as f:
        pStatus = json.load(f)
    assert pStatus['from_solution'] == pFile
    assert pStatus['status']        == 'optimal'
    assert not any(f.startswith('openTEPES_highs_') for f in os.listdir(pRoot / 'reload'))


@pytest.mark.solve
def test_a_solution_of_other_inputs_is_refused(solved_9n, tmp_path):
    pRoot, pFile = solved_9n
    shutil.copytree(pRoot / '9n', tmp_path / '9n')
    pDemand = tmp_path / '9n' / 'oT_Data_Demand_9n.csv'
    df = pd.read_csv(pDemand, index_col=[0, 1, 2])
    df.iloc[0, 0] *= 1.01
    df.to_csv(pDemand)
    with pytest.raises(SolutionMismatch, match='other input data'):
        openTEPES_run(str(tmp_path), '9n', 'highs', 1, 0, output_spec=SPEC, out_path=str(tmp_path / 'reload'), from_solution=pFile)
    assert _results(tmp_path / 'reload') == []


@pytest.mark.solve
def test_a_solution_of_other_model_settings_is_refused(solved_9n, tmp_path, monkeypatch):
    pRoot, pFile = solved_9n
    monkeypatch.setenv('OTEPES_ZERO_ENS', '1')
    with pytest.raises(SolutionMismatch, match='OTEPES_ZERO_ENS'):
        openTEPES_run(str(pRoot), '9n', 'highs', 1, 0, output_spec=SPEC, out_path=str(tmp_path / 'reload'), from_solution=pFile)
    assert _results(tmp_path / 'reload') == []


@pytest.mark.solve
def test_a_variable_with_no_stored_value_refuses_the_reload(solved_9n, tmp_path, monkeypatch):
    pRoot, pFile = solved_9n

    def _without_output(pPath):
        pSolution = read_solution(pPath)
        del pSolution['vars']['vTotalOutput']
        return pSolution
    monkeypatch.setattr(oT, 'read_solution', _without_output)
    with pytest.raises(SolutionMismatch, match='no stored value'):
        openTEPES_run(str(pRoot), '9n', 'highs', 1, 0, output_spec=SPEC, out_path=str(tmp_path / 'reload'), from_solution=pFile)
    assert _results(tmp_path / 'reload') == []


@pytest.mark.solve
def test_a_case_solved_one_stage_at_a_time_is_reloaded_exactly(tmp_path):
    """Case 9n7y as an operation model, solved in seven separate solves, one per period."""
    case_dir = tmp_path / '9n7y'
    shutil.copytree(os.path.join(CASES_DIR, '9n7y'), case_dir, ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))
    pFile = case_dir / 'oT_Data_Duration_9n7y.csv'
    df = pd.read_csv(pFile, index_col=[0, 1, 2])
    df.loc[df.groupby(level=[0, 1]).cumcount().to_numpy() >= 24, 'Duration'] = float('nan')
    df.to_csv(pFile)
    pFile = case_dir / 'oT_Data_Stage_9n7y.csv'
    df = pd.read_csv(pFile, index_col=[0])
    df['Weight'] = 0.0
    df.iloc[0, 0] = 365.0
    df.to_csv(pFile)
    pFile = case_dir / 'oT_Data_Option_9n7y.csv'
    df = pd.read_csv(pFile)
    for c in ('IndBinGenInvest', 'IndBinGenRetirement', 'IndBinRsrInvest', 'IndBinNetInvest', 'IndBinNetH2Invest', 'IndBinNetHeatInvest'):
        df[c] = 2
    df.to_csv(pFile, index=False)
    pFile = case_dir / 'oT_Data_RESEnergy_9n7y.csv'
    df = pd.read_csv(pFile)
    df['RESEnergy'] = 0
    df.to_csv(pFile, index=False)

    mSolve  = openTEPES_run(str(tmp_path), '9n7y', 'highs', 1, 0, output_spec=SPEC, out_path=str(tmp_path / 'solve'), save_solution=True)
    assert len(mSolve.pTerminationConditions) == 7
    mReload = openTEPES_run(str(tmp_path), '9n7y', 'highs', 1, 0, output_spec=SPEC, out_path=str(tmp_path / 'reload'),
                            from_solution=str(tmp_path / 'solve' / 'oT_Solution_9n7y.parquet'))
    assert mReload.pTerminationConditions == mSolve.pTerminationConditions
    assert mReload.vTotalSCost() == mSolve.vTotalSCost()
    pA, pB, pDiffer = _same_results(str(tmp_path / 'solve'), str(tmp_path / 'reload'))
    assert pA == pB
    assert pDiffer == []
