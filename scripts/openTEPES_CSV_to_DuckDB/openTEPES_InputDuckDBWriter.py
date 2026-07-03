"""
openTEPES_InputDuckDBWriter — write a CSV case to a ``.duckdb`` input file.

Offline case-prep utility (not part of the core model). The inverse of ``openTEPES_InputDuckDBSource``: read every
``oT_Data_*`` / ``oT_Dict_*`` CSV of a case and store it in the long / key-value / passthrough shape the DuckDB
backend reads back. Both sides are driven by the same ``openTEPES_InputSchema.TABLE_SPECS``, so the writer and the
reader cannot drift. A ``schema_metadata`` table records the case name, which ``DuckDBSource`` requires.

The metadata is deliberately limited to the case name and schema version — no timestamp or absolute path — so the
same CSV case always produces the same tables (a regenerated DB compares equal to a committed one, input for input).

Needs openTEPES installed (it imports ``openTEPES_InputSchema``). Run it through the CLI wrapper:

    python scripts/openTEPES_CSV_to_DuckDB/Tool_openTEPES_CSV_to_DuckDB.py cases/9n
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from openTEPES.openTEPES_InputSchema import (
    PASSTHROUGH,
    TABLE_SPECS,
    UNPIVOT_SINGLE_ROW,
    WIDE_MULTILEVEL_TO_LONG,
    WIDE_TO_LONG,
)

__all__ = ["write_case"]


# ---- CSV -> DB-table transforms (the exact inverse of DuckDBSource's _reconstruct_* helpers)

def _wide_to_long(df: pd.DataFrame, entity: str, value: str) -> pd.DataFrame:
    """Melt a wide time series (one column per entity) to long, keeping NaN cells so the read side can rebuild the
    full entity-column set without a separate entity-universe table."""
    return df.melt(id_vars=["Period", "Scenario", "LoadLevel"], var_name=entity, value_name=value)


def _unpivot_single_row(df: pd.DataFrame, value_type: str) -> pd.DataFrame:
    """Turn a single-row wide table (``oT_Data_Option`` / ``oT_Data_Parameter``) into ``(Name, Value)`` rows."""
    if len(df) != 1:
        raise ValueError(f"expected a single-row table, got {len(df)} rows")
    row = df.iloc[0]
    out = pd.DataFrame({"Name": row.index, "Value": row.values})
    if value_type == "INTEGER":
        out["Value"] = pd.to_numeric(out["Value"], errors="coerce").astype("Int64")
    return out


def _wide_multilevel_to_long(df: pd.DataFrame, entity_cols: list[str], value: str) -> pd.DataFrame:
    """Stack a multi-level-column wide table (``VariableTTC*`` / ``VariablePTDF``) to long.

    ``df`` is ``pd.read_csv(..., header=[0..N-1], index_col=[0, 1, 2])`` — an N-level column MultiIndex over
    ``entity_cols`` and a 3-level row MultiIndex ``(Period, Scenario, LoadLevel)``. Output columns:
    ``["Period", "Scenario", "LoadLevel", *entity_cols, value]``.
    """
    n = len(entity_cols)
    long_df = df.stack(level=list(range(n)), future_stack=True).reset_index()
    if len(long_df.columns) != 3 + n + 1:
        raise ValueError(f"wide_multilevel_to_long: expected {3 + n + 1} columns, got {len(long_df.columns)}")
    long_df.columns = ["Period", "Scenario", "LoadLevel"] + entity_cols + [value]
    return long_df


def _detect_case_name(case_dir: Path) -> str | None:
    """The case name is the ``X`` in ``oT_Data_Parameter_X.csv`` (same rule as CSVSource)."""
    for p in case_dir.glob("oT_Data_Parameter_*.csv"):
        return p.stem[len("oT_Data_Parameter_"):]
    return None


def write_case(case_dir, db_path=None, case_name: str | None = None) -> Path:
    """Write a CSV case directory to a ``.duckdb`` file the DuckDB backend can read.

    ``case_dir`` is the folder holding ``oT_Data_*`` / ``oT_Dict_*`` CSVs. ``case_name`` defaults to the name detected
    from ``oT_Data_Parameter_*.csv``. ``db_path`` defaults to ``<case_dir>/../<case_name>.duckdb``. Absent input files
    are skipped (a case need not populate every table). Returns the DB path.
    """
    import duckdb

    case_dir = Path(case_dir)
    if case_name is None:
        case_name = _detect_case_name(case_dir)
        if case_name is None:
            raise ValueError(f"{case_dir}: cannot detect case name (no oT_Data_Parameter_*.csv found)")
    db_path = Path(db_path) if db_path is not None else case_dir.parent / f"{case_name}.duckdb"
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    try:
        for stem_prefix, table_name, kind, kwargs in TABLE_SPECS:
            csv_path = case_dir / f"{stem_prefix}_{case_name}.csv"
            if not csv_path.exists():
                continue
            if kind == WIDE_MULTILEVEL_TO_LONG:
                n = len(kwargs["entity_cols"])
                raw = pd.read_csv(csv_path, encoding="utf-8-sig", header=list(range(n)), index_col=[0, 1, 2])
                df = _wide_multilevel_to_long(raw, **kwargs)
            else:
                raw = pd.read_csv(csv_path, encoding="utf-8-sig")
                if kind == PASSTHROUGH:
                    df = raw
                elif kind == WIDE_TO_LONG:
                    df = _wide_to_long(raw, **kwargs)
                elif kind == UNPIVOT_SINGLE_ROW:
                    df = _unpivot_single_row(raw, **kwargs)
                else:
                    raise ValueError(f"unknown spec kind for {stem_prefix}: {kind}")
            con.register("__df", df)
            con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM __df")
            con.unregister("__df")

        con.execute("CREATE OR REPLACE TABLE schema_metadata (Key VARCHAR, Value VARCHAR)")
        for k, v in (("schema_version", "1"), ("source_case", case_name)):
            con.execute("INSERT INTO schema_metadata VALUES (?, ?)", (k, v))
    finally:
        con.close()
    return db_path
