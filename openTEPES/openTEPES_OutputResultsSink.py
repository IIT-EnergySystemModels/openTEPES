"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 23, 2026

Result sink: write each result table to CSV and/or one per-case DuckDB file.

The output-side mirror of ``openTEPES_InputSource``. Every result writer ends in
``<frame>.oT.write(path, ...)``; the ``oT`` accessor (registered here on DataFrame
and Series) routes the write through the process-active ``ResultSink``. With no
sink it is plain ``to_csv`` -- so a CSV run and "Run Python File" are unchanged;
with a sink it writes the CSV and/or stores the same in-memory frame as one table
in ``oT_Results_<case>.duckdb`` (not re-read from the CSV).

``openTEPES_run`` sets the active sink around the output loop. One DuckDB per case
keeps a parallel sweep single-writer-safe; the sink is opened in the worker after
any fork, never carried across one.
"""
from __future__ import annotations

import os
import pandas as pd

VALID_FORMATS = ("csv", "duckdb", "both")

# Per-process active sink. Set by openTEPES_run before the output loop and
# cleared after; None means "plain to_csv" (historical behaviour).
_ACTIVE_SINK = None


def set_active_sink(sink):
    """Install the sink the ``oT`` accessor routes writes to (per process)."""
    global _ACTIVE_SINK
    _ACTIVE_SINK = sink


def clear_active_sink():
    """Remove the active sink so the ``oT`` accessor falls back to ``to_csv``."""
    global _ACTIVE_SINK
    _ACTIVE_SINK = None


def get_active_sink():
    """Return the active sink, or None when writes go straight to CSV."""
    return _ACTIVE_SINK


def _table_name(path, case_name):
    """``.../oT_Result_GenerationInvestment_9n.csv`` -> ``GenerationInvestment``.

    Strips the directory, the ``.csv`` / ``.csv.gz`` extension, the
    ``oT_Result_`` prefix, and the trailing ``_<case_name>`` so the DuckDB
    table name matches the CSV table name without the case suffix.
    """
    name = os.path.basename(path)
    for ext in (".csv.gz", ".csv"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    if name.startswith("oT_Result_"):
        name = name[len("oT_Result_"):]
    suffix = f"_{case_name}"
    if case_name and name.endswith(suffix):
        name = name[: -len(suffix)]
    return name


class ResultSink:
    """Write result tables to CSV, to a per-case DuckDB file, or to both.

    Parameters
    ----------
    out_path : str
        Directory the case writes its results to (same as ``mTEPES.pOutputPath``).
    case_name : str
        Case name; names the DuckDB file ``oT_Results_<case_name>.duckdb`` and is
        stripped from each table name.
    fmt : {'csv', 'duckdb', 'both'}
        ``'csv'`` keeps the historical CSV-only behaviour. ``'duckdb'`` writes
        only the DuckDB file. ``'both'`` writes both.
    """

    def __init__(self, out_path, case_name, fmt="both"):
        if fmt not in VALID_FORMATS:
            raise ValueError(f"fmt must be one of {VALID_FORMATS}; got {fmt!r}.")
        self.out_path = out_path
        self.case_name = case_name
        self.fmt = fmt
        self._con = None
        self.db_path = None
        if fmt in ("duckdb", "both"):
            import duckdb
            self.db_path = os.path.join(out_path, f"oT_Results_{case_name}.duckdb")
            # Start from a clean file so a re-run does not stack stale tables.
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            self._con = duckdb.connect(self.db_path)

    @property
    def writes_csv(self):
        return self.fmt in ("csv", "both")

    def write(self, obj, path, **csv_kwargs):
        """Write one result table. ``obj`` is a DataFrame or Series; ``path`` is
        the ``oT_Result_*.csv`` path the writer would have used; ``csv_kwargs``
        are its ``to_csv`` keywords (``sep``, ``index`` ...)."""
        if self.writes_csv:
            obj.to_csv(path, **csv_kwargs)
        if self._con is not None:
            df = obj.to_frame() if isinstance(obj, pd.Series) else obj
            # The CSV writes the index unless index=False; mirror that so the
            # DuckDB table has the same columns the CSV reader would see.
            if csv_kwargs.get("index", True):
                df = df.reset_index()
            table = _table_name(path, self.case_name)
            self._con.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM df')
        return None

    def close(self):
        if self._con is not None:
            self._con.close()
            self._con = None


def _dispatch_write(obj, path, **csv_kwargs):
    """Route a write through the active sink, or fall back to plain ``to_csv``."""
    sink = _ACTIVE_SINK
    if sink is None:
        return obj.to_csv(path, **csv_kwargs)
    return sink.write(obj, path, **csv_kwargs)


class _OTWriter:
    """Backing object for the ``.oT`` accessor on DataFrame and Series."""

    def __init__(self, obj):
        self._obj = obj

    def write(self, path, **csv_kwargs):
        return _dispatch_write(self._obj, path, **csv_kwargs)


def _register_accessor():
    """Register the ``oT`` accessor once on DataFrame and Series."""
    from pandas.api.extensions import register_dataframe_accessor, register_series_accessor
    import warnings
    if not getattr(pd.DataFrame, "_oT_accessor_registered", False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            register_dataframe_accessor("oT")(_OTWriter)
            register_series_accessor("oT")(_OTWriter)
        pd.DataFrame._oT_accessor_registered = True


_register_accessor()
