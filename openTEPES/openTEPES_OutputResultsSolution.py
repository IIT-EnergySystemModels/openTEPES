"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - November 28, 2026

Solution file.

This module writes the solution of a solved case to one Parquet file, ``oT_Solution_<CaseName>.parquet``: every variable value with its fixed indicator,
every stored dual, and every stored stage cost, one row per value. The file holds what the result writers read, so a case solved on one computer can
produce its results on another without the solver. It is written with DuckDB, compressed with zstd, and carries its metadata (openTEPES version and
commit, case, solver, termination conditions, solve time, date, a hash of the inputs and the OTEPES_* settings) in the Parquet footer.

It also reads the file back for a reload (``--from-solution``): the metadata are checked against the case, and the stored values are loaded into the
model in place of each solve.

Columns: ``kind`` (var, dual or stagecost), ``component``, ``p``, ``sc``, ``n``, ``rest``, ``value`` and ``fixed``. An index that starts with a period, a
scenario and a third position (the load level for an operation variable) is split into ``p``, ``sc`` and ``n``, and its remainder is kept as text in
``rest``; any other index is kept as text in ``rest`` alone. A remainder of one text element (a unit, a node) is stored as that text, e.g., ``CCGT_1``;
any other remainder is stored as the text of its tuple, e.g., ``('Node_1', 'Node_2', 'eac1')``. The key of a dual is its constraint name followed by its index, as in ``mTEPES.pDuals``; the
constraint name goes in ``component`` and the index in ``rest``.
"""

import datetime
import hashlib
import json
import os

import duckdb
import pandas        as     pd
import pyomo.environ as     pyo

try:
    from .                    import __version__
    from .openTEPES_gitinfo   import ROOT_DIR, last_commit_id
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES                   import __version__
    from openTEPES.openTEPES_gitinfo import ROOT_DIR, last_commit_id

# Version of the layout above. A reader refuses a file whose layout version it does not know.
SOLUTION_FORMAT_VERSION = 1
# About one million rows per row group, as measured on RTS-GMLC_6y: smaller groups gave the same query time and a larger file.
ROW_GROUP_SIZE          = 1 << 20
# Settings read from the environment. The first two change the model, so a solution obtained with other values of them is refused on reload; the others
# change only how the solver works, and a difference in them is ignored.
MODEL_SETTINGS          = ('OTEPES_MAX_THETA', 'OTEPES_ZERO_ENS')
SOLVER_SETTINGS         = ('OTEPES_THREADS', 'OTEPES_CROSSOVER', 'OTEPES_HIGHS_SOLVER', 'OTEPES_WARM_RESOLVE', 'OTEPES_WARM_RESOLVE_CAP',
                           'OTEPES_WARM_RESOLVE_SIMPLEX')


def input_hash(dfs, option_overrides=None):
    """SHA-256 of the input tables after reading, together with the option overrides.

    The hash is computed over the frames returned by InputData, not over the files, so a case gives the same hash whether it is read from CSV files or from
    a DuckDB file. A reload compares it with the hash stored in the solution file, to refuse a solution that belongs to other inputs.
    """
    h = hashlib.sha256()
    for pName in sorted(dfs):
        df = dfs[pName]
        h.update(pName.encode())
        if isinstance(df, (pd.DataFrame, pd.Series)):
            if isinstance(df, pd.DataFrame):
                h.update(repr(list(df.columns)).encode())
            h.update(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes())
        else:
            h.update(repr(df).encode())
    h.update(json.dumps(option_overrides or {}, sort_keys=True, default=str).encode())
    return h.hexdigest()


def _code_commit():
    """Commit of the code that ran, or an empty string if openTEPES does not run from a git checkout.

    The check for .git keeps an installed package from reporting the commit of an unrelated repository that happens to contain the Python environment.
    """
    if not os.path.exists(os.path.join(ROOT_DIR, '.git')):
        return ''
    return last_commit_id()


def _index_text(t):
    """The text of an index remainder: one text element as itself, anything else as the text of its tuple."""
    if len(t) == 1 and isinstance(t[0], str):
        return t[0]
    return repr(t)


def _splits(pKeys):
    """True if every index of a component starts with a period, a scenario and a third position, so that the file splits it into p, sc and n.

    The test is made on every key, so that a component indexed by a union set cannot mislead it. The writer and the reader both decide by this test, per
    component, so they always agree on the key of a value.
    """
    return len(pKeys) > 0 and all(isinstance(k, tuple) and len(k) >= 3 and isinstance(k[0], int) and isinstance(k[1], str) for k in pKeys)


def _index_key(k, pSplit):
    """The (p, sc, n, rest) key of one variable index, as stored in the file."""
    if pSplit:
        return k[0], k[1], k[2], (_index_text(k[3:]) if len(k) > 3 else None)
    return None, None, None, _index_text(k if isinstance(k, tuple) else (k,))


def _environment():
    """The OTEPES_* settings of this run."""
    return {k: os.environ[k] for k in MODEL_SETTINGS + SOLVER_SETTINGS if k in os.environ}


def _var_columns(pVar, cols):
    """Append the rows of one variable component to the column lists in cols."""
    pKeys  = list(pVar.keys())
    pDatas = list(pVar.values())
    pName  = pVar.name
    nRows  = len(pKeys)
    pSplit = _splits(pKeys)
    cols['kind'     ].extend(['var'] * nRows)
    cols['component'].extend([pName] * nRows)
    if pSplit:
        cols['p'   ].extend(k[0] for k in pKeys)
        cols['sc'  ].extend(k[1] for k in pKeys)
        cols['n'   ].extend(k[2] for k in pKeys)
        cols['rest'].extend(_index_text(k[3:]) if len(k) > 3 else None for k in pKeys)
    else:
        cols['p'   ].extend([None] * nRows)
        cols['sc'  ].extend([None] * nRows)
        cols['n'   ].extend([None] * nRows)
        cols['rest'].extend(_index_text(k if isinstance(k, tuple) else (k,)) for k in pKeys)
    cols['value'].extend(d.value for d in pDatas)
    cols['fixed'].extend(d.fixed for d in pDatas)


def solution_frame(OptModel, mTEPES):
    """The solution of the model as one long frame, in the layout described in the module docstring."""
    cols = {c: [] for c in ('kind', 'component', 'p', 'sc', 'n', 'rest', 'value', 'fixed')}
    for pVar in sorted(OptModel.component_objects(pyo.Var, descend_into=True), key=lambda v: v.name):
        _var_columns(pVar, cols)

    for pKey, pValue in getattr(mTEPES, 'pDuals', {}).items():
        pName, pSep, pIndex = pKey.partition('(')
        cols['kind'     ].append('dual')
        cols['component'].append(pName if pSep else pKey)
        cols['p'        ].append(None)
        cols['sc'       ].append(None)
        cols['n'        ].append(None)
        cols['rest'     ].append(pSep + pIndex if pSep else None)
        cols['value'    ].append(pValue)
        cols['fixed'    ].append(False)

    for (pName, p, sc, n), pValue in sorted(getattr(mTEPES, 'pStageCostValues', {}).items()):
        cols['kind'     ].append('stagecost')
        cols['component'].append(pName)
        cols['p'        ].append(p)
        cols['sc'       ].append(sc)
        cols['n'        ].append(n)
        cols['rest'     ].append(None)
        cols['value'    ].append(pValue)
        cols['fixed'    ].append(False)

    df = pd.DataFrame(cols)
    df['p']     = df['p'].astype('Int16')
    df['value'] = df['value'].astype('float64')
    df['fixed'] = df['fixed'].astype('bool')
    return df


def _sql_text(s):
    return "'" + str(s).replace("'", "''") + "'"


def write_solution(OptModel, mTEPES, CaseName, SolverName, pInputHash):
    """Write oT_Solution_<CaseName>.parquet to the output directory and return its path.

    The file is written to a temporary name and then renamed, so an interrupted write never leaves a partial file under the final name.
    """
    pPath = os.path.join(mTEPES.pOutputPath, f'oT_Solution_{CaseName}.parquet')
    pTemp = pPath + '.tmp'
    df    = solution_frame(OptModel, mTEPES)
    pMeta = {
        'format_version':         str(SOLUTION_FORMAT_VERSION),
        'opentepes_version':      __version__,
        'opentepes_commit':       _code_commit(),
        'case':                   CaseName,
        'solver':                 SolverName,
        'termination_conditions': json.dumps(getattr(mTEPES, 'pTerminationConditions', [])),
        'solve_seconds':          f'{getattr(mTEPES, "pSolveSeconds", 0.0):.2f}',
        'written_utc':            datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds') + 'Z',
        'input_hash':             pInputHash,
        'environment':            json.dumps(_environment(), sort_keys=True),
    }
    pKV = ', '.join(f'{_sql_text(k)}: {_sql_text(v)}' for k, v in pMeta.items())
    with duckdb.connect() as con:
        con.register('solution', df)
        con.execute(f"COPY solution TO {_sql_text(pTemp)} (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {ROW_GROUP_SIZE}, KV_METADATA {{{pKV}}})")
    os.replace(pTemp, pPath)
    return pPath


def read_solution_metadata(pPath):
    """The metadata of a solution file as a dict of text values."""
    with duckdb.connect() as con:
        pRows = con.execute('SELECT key, value FROM parquet_kv_metadata(?)', [pPath]).fetchall()
    return {(k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v) for k, v in pRows}


class SolutionMismatch(ValueError):
    """A solution file that does not belong to the case being reloaded."""


def check_solution_metadata(pMeta, pInputHash, CaseName):
    """Refuse a solution file whose layout, inputs or model settings differ from those of the case; warn on a different openTEPES version or case name.

    The structure of the model, not its version number, decides whether a stored solution fits: a variable with no stored value, or a stored value with no
    variable, is found by load_solution. A different version of openTEPES therefore gives a warning only.
    """
    if pMeta.get('format_version') != str(SOLUTION_FORMAT_VERSION):
        raise SolutionMismatch(f"### The solution file has layout version {pMeta.get('format_version')!r}; this openTEPES reads version "
                               f"{SOLUTION_FORMAT_VERSION}.")
    if pMeta.get('input_hash') != pInputHash:
        raise SolutionMismatch('### The solution file belongs to other input data: the hash of the inputs differs. Solve the case again, or reload it '
                               'with the inputs and option overrides it was solved with.')
    pStored = json.loads(pMeta.get('environment') or '{}')
    pNow    = _environment()
    pModel  = [k for k in MODEL_SETTINGS if pStored.get(k) != pNow.get(k)]
    if pModel:
        raise SolutionMismatch('### The solution file was obtained with other model settings: ' +
                               ', '.join(f'{k} {pStored.get(k)!r} in the file, {pNow.get(k)!r} now' for k in pModel) + '.')
    if pMeta.get('opentepes_version') != __version__:
        print(f"### WARNING: the solution file was written by openTEPES {pMeta.get('opentepes_version')}; this is {__version__}. The model is "
              f"checked variable by variable before any result is written.")
    if pMeta.get('case') != CaseName:
        print(f"### WARNING: the solution file was written for case {pMeta.get('case')!r}; the case reloaded is {CaseName!r}. Its inputs are the same.")


def read_solution(pPath):
    """The stored values of a solution file, ready for load_solution.

    Returns a dict with the variable values and fixed indicators by component and key, the duals by key, the stage costs by key, the termination
    conditions, and the metadata.
    """
    pMeta = read_solution_metadata(pPath)
    with duckdb.connect() as con:
        df = con.execute("SELECT kind, component, p, sc, n, rest, value, fixed FROM read_parquet(?)", [pPath]).df()
    df['p'] = df['p'].astype(object).where(df['p'].notna(), None)
    # converted to object first: under pandas 3, a text column keeps its missing values as NaN even when they are replaced by None
    for c in ('sc', 'n', 'rest'):
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    df['value'] = df['value'].astype(object).where(df['value'].notna(), None)

    pVars = {}
    v = df[df['kind'] == 'var']
    for pName, pGroup in v.groupby('component', sort=False):
        pVars[pName] = dict(zip(zip([None if x is None else int(x) for x in pGroup['p']], pGroup['sc'], pGroup['n'], pGroup['rest']),
                                zip(pGroup['value'], pGroup['fixed'])))
    d = df[df['kind'] == 'dual']
    pDuals = {c + (r or ''): x for c, r, x in zip(d['component'], d['rest'], d['value'])}
    s = df[df['kind'] == 'stagecost']
    pStage = {(c, int(p), sc, n): x for c, p, sc, n, x in zip(s['component'], s['p'], s['sc'], s['n'], s['value'])}
    return {'vars': pVars, 'duals': pDuals, 'stagecosts': pStage, 'termination_conditions': json.loads(pMeta.get('termination_conditions') or '[]'),
            'metadata': pMeta}


def load_solution(OptModel, mTEPES, pSolution):
    """Load the stored values into the model in place of the solves.

    Every variable gets its stored value and fixed indicator, and the duals, the stage costs and the termination conditions are restored. The values are
    the final values of the run, so they are loaded once, at the first call; the fixing between stages then holds them at the same values. A variable
    with no stored value, or a stored variable that the model does not have, refuses the reload, since its results would be wrong.
    """
    pMissing = []
    pSeen    = set()
    for pVar in OptModel.component_objects(pyo.Var, descend_into=True):
        pStored = pSolution['vars'].get(pVar.name)
        pSeen.add(pVar.name)
        pSplit  = _splits(list(pVar.keys()))
        for k, pData in pVar.items():
            pValue = None if pStored is None else pStored.get(_index_key(k, pSplit))
            if pValue is None:
                pMissing.append(pData.name)
                continue
            pData.set_value(pValue[0], skip_validation=True)
            if pValue[1]:
                pData.fix()
    pExtra = sorted(set(pSolution['vars']) - pSeen)
    if pMissing or pExtra:
        raise SolutionMismatch(f'### The solution file does not fit the model: {len(pMissing)} variables have no stored value '
                               f'(e.g., {pMissing[:3]}), and {len(pExtra)} stored variables are not in the model (e.g., {pExtra[:3]}).')
    mTEPES.pDuals.update(pSolution['duals'])
    mTEPES.pStageCostValues = dict(pSolution['stagecosts'])
    if not hasattr(mTEPES, 'pTerminationConditions'):
        mTEPES.pTerminationConditions = []
    mTEPES.pTerminationConditions.extend(pSolution['termination_conditions'])
