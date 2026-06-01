"""
openTEPES.openTEPES_InputDuckDBSource — in-process ``.duckdb`` backend.

Reads stream through SQL into DataFrames directly — no temporary CSV materialisation, no extra disk I/O round-trip.
``duckdb`` is an optional dependency; the import is lazy and the ``_HAS_DUCKDB`` flag is consulted by
``Source.open_source()`` before constructing a ``DuckDBSource``.

The DB is opened read-only. ``schema_metadata.source_case`` is consulted at connection time so the case name follows
the same rule as the CSV backend (``oT_Data_Parameter_*.csv`` filename for CSV, ``schema_metadata`` for DuckDB).
"""
from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd

from .openTEPES_InputSchema import (
    PASSTHROUGH,
    TABLE_SPECS,
    UNPIVOT_SINGLE_ROW,
    WIDE_MULTILEVEL_TO_LONG,
    WIDE_TO_LONG,
    _SPEC_BY_CSV_STEM,
)
from .openTEPES_InputSource import InputSource, _apply_index

_HAS_DUCKDB = True
try:
    import duckdb  # type: ignore
except ImportError:  # pragma: no cover
    _HAS_DUCKDB = False


class DuckDBSource(InputSource):
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._con = duckdb.connect(str(self.db_path), read_only=True)
        row = self._con.execute("SELECT Value FROM schema_metadata WHERE Key='source_case'").fetchone()
        if not row or not row[0]:
            raise ValueError(
                f"{self.db_path}: schema_metadata.source_case is missing — DB was not produced by the C2 ingest script?"
            )
        self.case_name = row[0]
        # Pre-fetch existing DB table names (cheap; speeds up the list_data_stems / table-presence checks called many
        # times).
        rows = self._con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        self._existing_tables: set[str] = {r[0] for r in rows}

    @property
    def dir_name(self) -> str:
        # openTEPES_run still uses DirName for output paths. Anchor the output to the .duckdb's parent so results
        # survive the source's close.
        return str(self.db_path.parent)

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    # ---- helpers

    def _table_for(self, csv_stem: str) -> tuple[str, str, dict] | None:
        spec = _SPEC_BY_CSV_STEM.get(csv_stem)
        return spec  # (db_table, kind, kwargs) or None

    def _table_present(self, db_table: str) -> bool:
        return db_table in self._existing_tables

    # ---- public API

    def list_data_stems(self) -> set[str]:
        stems: set[str] = set()
        for csv_prefix, db_table, kind, _ in TABLE_SPECS:
            if not csv_prefix.startswith("oT_Data_"):
                continue
            if self._table_present(db_table):
                stems.add(csv_prefix[len("oT_Data_"):])
        return stems

    def read_dict(self, stem: str) -> pd.DataFrame:
        spec = self._table_for(f"oT_Dict_{stem}")
        if spec is None or not self._table_present(spec[0]):
            return pd.DataFrame()
        return self._con.execute(f"SELECT * FROM {spec[0]}").df()

    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        spec = self._table_for(f"oT_Data_{stem}")
        if spec is None:
            raise FileNotFoundError(f"unknown oT_Data_{stem}_*.csv stem (no DB table mapped)")
        db_table, kind, kwargs = spec
        if not self._table_present(db_table):
            raise FileNotFoundError(f"oT_Data_{stem}_*.csv not present in {self.db_path}")

        if kind == PASSTHROUGH:
            df = self._con.execute(f"SELECT * FROM {db_table}").df()
            if stem in ("Option", "Parameter"):
                return df
            return _apply_index(df, stem)

        if kind == WIDE_TO_LONG:
            df = self._reconstruct_wide(db_table, **kwargs)
            return _apply_index(df, stem)

        if kind == UNPIVOT_SINGLE_ROW:
            return self._reconstruct_single_row(db_table, **kwargs)

        if kind == WIDE_MULTILEVEL_TO_LONG:
            # The reconstruction already has the multi-level column shape plus the (Period, Scenario, LoadLevel) row
            # index that the CSV reader produces — no _apply_index needed.
            return self._reconstruct_wide_multilevel(db_table, **kwargs)

        raise ValueError(f"unknown spec kind for {stem}: {kind}")

    # ---- shape reconstruction (mirror of the C2 emit logic)

    def _reconstruct_wide(self, table_name: str, *, entity: str, value: str) -> pd.DataFrame:
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        id_cols = ["Period", "Scenario", "LoadLevel"]
        wide = df.pivot_table(index=id_cols, columns=entity, values=value, dropna=False, sort=False).reset_index()
        wide.columns.name = None
        return wide

    def _reconstruct_single_row(self, table_name: str, *, value_type: str) -> pd.DataFrame:
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        header = ",".join(str(n) for n in df["Name"])
        row = ",".join("" if pd.isna(v) else str(v) for v in df["Value"])
        return pd.read_csv(StringIO(header + "\n" + row))

    def _reconstruct_wide_multilevel(self, table_name: str, *, entity_cols: list[str], value: str) -> pd.DataFrame:
        """Pivot the long DB table back to multi-level-column wide shape.

        Matches the pandas quirk where ``pd.read_csv(..., header=[0..N-1], index_col=[0,1,2])`` yields
        ``index.names = [None, None, None]`` and ``columns.names = ['Period', None, ...]``. Preserving this lets
        downstream CSV/DB consumers see identical DataFrames.
        """
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        id_cols = ["Period", "Scenario", "LoadLevel"]
        wide = df.pivot_table(index=id_cols, columns=entity_cols, values=value, dropna=False, sort=False)
        wide.index.names = [None, None, None]
        wide.columns.names = ["Period"] + [None] * (len(entity_cols) - 1)
        return wide
