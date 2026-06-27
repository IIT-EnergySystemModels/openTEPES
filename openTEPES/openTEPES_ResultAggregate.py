"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 23, 2026

Sweep merger: stack each result table across the cases of a sweep.

``aggregate(sources, out_path, to=...)`` reads each case's results -- a per-case
``oT_Results_<case>.duckdb`` if present, else its ``oT_Result_*.csv`` folder -- and
stacks them into one long table per result with a leading ``case`` column. It returns
the merged tables and can write ``oT_Sweep_<Table>.csv`` and/or one ``oT_Sweep.duckdb``.
Cases with a slightly different column set are aligned by column union.
"""
from __future__ import annotations

import glob
import os
import pandas as pd

try:
    from ._output_parity_test import _result_files, _result_stem, _infer_case_tokens, _strip_case_suffix
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES._output_parity_test import _result_files, _result_stem, _infer_case_tokens, _strip_case_suffix

from pathlib import Path

VALID_TO = ("csv", "duckdb", "both", "none")


def _read_case_duckdb(db_path):
    """Return {table_name: DataFrame} for every table in a per-case DuckDB file."""
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    try:
        names = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        return {name: con.execute(f'SELECT * FROM "{name}"').df() for name in names}
    finally:
        con.close()


def _read_case_csv_dir(dir_path):
    """Return {table_name: DataFrame} for the ``oT_Result_*.csv[.gz]`` files in a dir."""
    files = _result_files(Path(dir_path))
    case_tokens = _infer_case_tokens([_result_stem(f.name) for f in files])
    tables = {}
    for f in files:
        name = _strip_case_suffix(_result_stem(f.name), case_tokens)
        tables[name] = pd.read_csv(f)
    return tables


def _label_for(source):
    """Infer a case label from a source path (DuckDB stem or directory name)."""
    base = os.path.basename(os.path.normpath(source))
    if base.endswith(".duckdb"):
        stem = base[: -len(".duckdb")]
        return stem[len("oT_Results_"):] if stem.startswith("oT_Results_") else stem
    return base


def _read_source(source):
    """Return {table_name: DataFrame} for one source (dir or .duckdb file)."""
    if os.path.isfile(source) and source.endswith(".duckdb"):
        return _read_case_duckdb(source)
    if os.path.isdir(source):
        db = glob.glob(os.path.join(source, "oT_Results_*.duckdb"))
        if db:
            return _read_case_duckdb(sorted(db)[0])
        return _read_case_csv_dir(source)
    raise FileNotFoundError(f"aggregate source not found (need a case dir or .duckdb file): {source!r}")


def aggregate(sources, out_path=None, to="csv", case_col="case", labels=None):
    """Merge the results of several cases into one long table per result type.

    Parameters
    ----------
    sources : iterable of str
        Case output directories and/or per-case ``.duckdb`` files.
    out_path : str | None
        Directory to write merged tables to. Required unless ``to='none'``;
        created if missing.
    to : {'csv', 'duckdb', 'both', 'none'}
        ``'csv'`` writes one ``oT_Sweep_<Table>.csv`` per table; ``'duckdb'``
        writes one ``oT_Sweep.duckdb`` with one table per result; ``'both'``
        writes both; ``'none'`` writes nothing and only returns the tables.
    case_col : str
        Name of the leading column that tags each row with its case label.
    labels : list[str] | None
        Case labels, one per source, in order. Defaults to a label inferred
        from each source path (the ``.duckdb`` stem or the directory name).

    Returns
    -------
    dict[str, pandas.DataFrame]
        Merged table per result name, each with ``case_col`` as its first column.
    """
    if to not in VALID_TO:
        raise ValueError(f"to must be one of {VALID_TO}; got {to!r}.")
    sources = list(sources)
    if labels is None:
        labels = [_label_for(s) for s in sources]
    if len(labels) != len(sources):
        raise ValueError(f"labels ({len(labels)}) must match sources ({len(sources)}).")

    # Collect, per table name, the per-case frames in source order.
    per_table = {}
    for source, label in zip(sources, labels):
        for name, df in _read_source(source).items():
            per_table.setdefault(name, []).append((label, df))

    merged = {}
    for name, items in per_table.items():
        stacked = pd.concat([df.assign(**{case_col: label}) for label, df in items], ignore_index=True)
        cols = [case_col] + [c for c in stacked.columns if c != case_col]
        merged[name] = stacked[cols]

    if to != "none":
        if not out_path:
            raise ValueError("out_path is required unless to='none'.")
        os.makedirs(out_path, exist_ok=True)
        if to in ("csv", "both"):
            for name, df in merged.items():
                df.to_csv(os.path.join(out_path, f"oT_Sweep_{name}.csv"), index=False)
        if to in ("duckdb", "both"):
            import duckdb
            db_path = os.path.join(out_path, "oT_Sweep.duckdb")
            if os.path.exists(db_path):
                os.remove(db_path)
            con = duckdb.connect(db_path)
            try:
                for name, df in merged.items():
                    con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM df')
            finally:
                con.close()

    return merged
