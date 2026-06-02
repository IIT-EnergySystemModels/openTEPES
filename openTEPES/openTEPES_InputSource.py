"""
openTEPES.openTEPES_InputSource — ``InputSource`` ABC, ``open_source()`` factory, and post-read shape helpers shared by every
backend.

Selection rules of ``open_source(path)``:

  * directory                → ``CSVSource(path)`` (historical behaviour).
  * file with ``.duckdb``    → ``DuckDBSource(path)``.
  * anything else            → ``ValueError``.

Backends are imported lazily so a parity probe in a freshly-cloned tree without ``duckdb`` installed still resolves
``InputSource`` and ``open_source`` for the CSV path.
"""
from __future__ import annotations

import abc
import os
from pathlib import Path

import pandas as pd

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative import below has no parent package; fall back to an absolute package import in that case.
try:
    from .openTEPES_InputSchema import (
        DEFAULT_IDX_COLS,
        UNPIVOT_SINGLE_ROW,
        WIDE_TO_LONG,
        _SPEC_BY_CSV_STEM,
    )
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSchema import (
        DEFAULT_IDX_COLS,
        UNPIVOT_SINGLE_ROW,
        WIDE_TO_LONG,
        _SPEC_BY_CSV_STEM,
    )


class InputSource(abc.ABC):
    """Abstract input source. Implementations: ``CSVSource``, ``DuckDBSource``."""

    case_name: str

    @abc.abstractmethod
    def list_data_stems(self) -> set[str]:
        """Stems of data tables present in the source (without the ``oT_Data_`` prefix or the ``_<casename>.csv``
        suffix)."""

    @abc.abstractmethod
    def read_dict(self, stem: str) -> pd.DataFrame:
        """Return the dimension dict for ``stem`` as a DataFrame (no index set). Returns an empty DataFrame if absent."""

    @abc.abstractmethod
    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        """Return a data table in the wide-format-indexed shape that ``InputData`` expects.

        For Pattern-3 tables, the value column is pivoted out and the entity becomes columns. For multi-row tables
        with key columns, those are set as the index. For single-row tables (``Option`` / ``Parameter``), no index
        is set.

        ``header_levels`` mirrors ``pd.read_csv(header=...)`` for the few files that use multi-level column headers
        (``VariableTTC*``, ``VariablePTDF``). Raises ``FileNotFoundError`` if the stem is absent.
        """

    def close(self) -> None:  # default no-op
        pass

    def __enter__(self) -> "InputSource":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open_source(path: str | os.PathLike) -> InputSource:
    """Sniff ``path`` and return a ``CSVSource`` or ``DuckDBSource``.

    Backends are imported lazily so the ``duckdb`` dependency is only required when a ``.duckdb`` path is opened.
    """
    p = Path(path).expanduser()
    if p.is_dir():
        from .openTEPES_InputCSVSource import CSVSource  # local import keeps duckdb-free environments importing Source.py cleanly
        return CSVSource(p)
    if p.is_file() and p.suffix == ".duckdb":
        from .openTEPES_InputDuckDBSource import DuckDBSource, _HAS_DUCKDB
        if not _HAS_DUCKDB:
            raise ImportError("duckdb is required to read .duckdb input sources; install it with `pip install duckdb`")
        return DuckDBSource(p)
    raise ValueError(f"{p}: not a CSV case directory or a .duckdb file")


def _apply_index(df: pd.DataFrame, stem: str) -> pd.DataFrame:
    """Set the multi-index that ``InputData`` expects on a wide-format table.

    Priority for choosing the index columns:
      1. ``pk_cols`` from the table's TABLE_SPECS entry (preferred — explicit).
      2. Auto-detection from DEFAULT_IDX_COLS (fallback for stems not in the spec, e.g. optional hydropower / heat /
         H2 tables).

    Wide-format tables (post-pivot) always end up keyed on ``[Period, Scenario, LoadLevel]`` and are handled by the
    WIDE_TO_LONG spec path before this function is called.
    """
    spec = _SPEC_BY_CSV_STEM.get(f"oT_Data_{stem}")
    if spec is not None:
        _, kind, kwargs = spec
        if kind == WIDE_TO_LONG:
            idx_cols = ["Period", "Scenario", "LoadLevel"]
        elif kind == UNPIVOT_SINGLE_ROW:
            return df  # single-row tables carry no index
        else:  # PASSTHROUGH
            idx_cols = kwargs.get("pk_cols") or [c for c in df.columns if c in DEFAULT_IDX_COLS]
    else:
        idx_cols = [c for c in df.columns if c in DEFAULT_IDX_COLS]

    if idx_cols:
        df = df.set_index(idx_cols, drop=True)
    return df


def df_to_set_values(df: pd.DataFrame) -> list:
    """Convert a dict-table DataFrame into the values an init-time Pyomo ``Set(initialize=...)`` accepts.

      * 1-col DataFrame  -> ``[v1, v2, ...]``
      * 2-col+ DataFrame -> ``[(a, b, ...), ...]`` (relation / membership).
    """
    if df.shape[1] == 1:
        return df.iloc[:, 0].tolist()
    return [tuple(row) for row in df.itertuples(index=False, name=None)]
