"""Solution file and raw dump options of openTEPES_run.

With save_solution, a solved case writes oT_Solution_<case>.parquet: every variable value with its fixed indicator, every dual and every stored stage
cost, with the metadata a reload checks. With dump_raw, it writes the raw DuckDB dump. Both are off by default.
"""
import json
import os
import shutil

import duckdb
import pandas as pd
import pytest
from pyomo.environ import ConcreteModel, Var

from openTEPES.openTEPES import openTEPES_run
from openTEPES.openTEPES_InputData import InputData
from openTEPES.openTEPES_InputSource import open_source
from openTEPES.openTEPES_OutputResultsSolution import input_hash, read_solution_metadata

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _day_of_9n(dest_root):
    """Case 9n reduced to its first 24 load levels, without its RES target."""
    case_dir = os.path.join(str(dest_root), '9n')
    shutil.copytree(os.path.join(CASES_DIR, '9n'), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))
    duration_csv = os.path.join(case_dir, 'oT_Data_Duration_9n.csv')
    df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    df.loc[df.groupby(level=[0, 1]).cumcount().to_numpy() >= 24, 'Duration'] = float('nan')
    df.to_csv(duration_csv)
    # the yearly RES target cannot be met in one day
    res_csv = os.path.join(case_dir, 'oT_Data_RESEnergy_9n.csv')
    if os.path.exists(res_csv):
        df = pd.read_csv(res_csv)
        df['RESEnergy'] = 0
        df.to_csv(res_csv, index=False)
    return case_dir


def _status(case_dir):
    with open(os.path.join(case_dir, 'openTEPES_run_status_9n.json')) as f:
        return json.load(f)


@pytest.mark.solve
def test_the_solution_file_holds_every_value_of_the_solved_case(tmp_path):
    case_dir = _day_of_9n(tmp_path)
    mTEPES   = openTEPES_run(str(tmp_path), '9n', 'highs', 0, 0, save_solution=True)
    pPath    = os.path.join(case_dir, 'oT_Solution_9n.parquet')
    assert _status(case_dir)['solution_file'] == pPath
    assert not os.path.exists(pPath + '.tmp')

    pSol = duckdb.sql(f"SELECT * FROM read_parquet('{pPath}')").df()
    pVarData = list(mTEPES.component_data_objects(Var, descend_into=True))
    assert (pSol['kind'] == 'var'      ).sum() == len(pVarData)
    assert (pSol['kind'] == 'dual'     ).sum() == len(mTEPES.pDuals) > 0
    assert (pSol['kind'] == 'stagecost').sum() == len(mTEPES.pStageCostValues) > 0

    # every value and fixed indicator of the output of the units, by its typed index
    pOut = pSol[(pSol['kind'] == 'var') & (pSol['component'] == 'vTotalOutput')].set_index(['p', 'sc', 'n', 'rest'])
    assert len(pOut) == len(mTEPES.vTotalOutput)
    for (p, sc, n, g), v in mTEPES.vTotalOutput.items():
        assert pOut.loc[(p, sc, n, g), 'value'] == pytest.approx(v.value, abs=1e-12)
        assert pOut.loc[(p, sc, n, g), 'fixed'] == v.fixed

    # each dual is found again under its key, i.e., its constraint name followed by its index
    pDual = pSol[pSol['kind'] == 'dual']
    pKeys = pDual['component'] + pDual['rest'].fillna('')
    assert dict(zip(pKeys, pDual['value'])) == pytest.approx(mTEPES.pDuals)

    pMeta = read_solution_metadata(pPath)
    assert pMeta['format_version'] == '1'
    assert pMeta['case']           == '9n'
    assert pMeta['solver']         == 'highs'
    assert json.loads(pMeta['termination_conditions']) == mTEPES.pTerminationConditions
    assert len(pMeta['input_hash']) == 64


@pytest.mark.solve
def test_the_raw_dump_is_written_on_request_and_no_solution_file_by_default(tmp_path):
    case_dir = _day_of_9n(tmp_path)
    openTEPES_run(str(tmp_path), '9n', 'highs', 0, 0, dump_raw=True)
    assert not os.path.exists(os.path.join(case_dir, 'oT_Solution_9n.parquet'))
    assert _status(case_dir)['solution_file'] is None
    pDumps = [d for d in os.listdir(case_dir) if d.startswith('CaseDumpFolder_9n_')]
    assert len(pDumps) == 1
    assert os.path.exists(os.path.join(case_dir, pDumps[0], 'oT_Case_9n.duckdb'))


def _hash_of(DirName, CaseName, pSource=None):
    mTEPES = ConcreteModel()
    if pSource is not None:
        mTEPES.pInputSource = pSource
    dfs, _ = InputData(DirName, CaseName, mTEPES, 0)
    return input_hash(dfs)


def test_the_input_hash_is_the_same_for_a_case_in_csv_and_in_duckdb_form():
    pSource = open_source(os.path.join(CASES_DIR, '9n_duckdb', '9n.duckdb'))
    try:
        pDuckDB = _hash_of(os.path.join(CASES_DIR, '9n_duckdb'), pSource.case_name, pSource)
    finally:
        pSource.close()
    assert _hash_of(CASES_DIR, '9n') == pDuckDB


def test_the_input_hash_changes_with_an_option_override():
    mTEPES = ConcreteModel()
    dfs, _ = InputData(CASES_DIR, '9n', mTEPES, 0)
    assert input_hash(dfs) != input_hash(dfs, {'IndBinGenInvest': '2'})
