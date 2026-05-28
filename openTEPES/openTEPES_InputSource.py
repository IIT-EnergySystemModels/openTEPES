"""
openTEPES — Input source abstraction.

Lets ``InputData`` read each input table from either a per-case CSV
directory (the historical contract) or a ``.duckdb`` file produced by an
ingest script, through a uniform interface:

    source = open_source(path)
    df = source.read_data("Demand")          # wide-format, multi-indexed
    rows = source.read_dict("Node")          # list of values or tuples
    stems = source.list_data_stems()         # {"Demand", "Generation", ...}

The two backends (``CSVSource``, ``DuckDBSource``) return identical pandas
shapes for every call, so ``InputData`` does not branch on source type.
DuckDB reads stream through SQL into DataFrames directly — no temporary
CSV materialisation, no extra disk I/O round-trip.

Selection
---------
``open_source(path)`` sniffs the path:

  * directory                → ``CSVSource(path)`` (historical behaviour).
  * file with ``.duckdb``    → ``DuckDBSource(path)``.
  * anything else            → ``ValueError``.

The case name is read from the directory contents (CSV) or from
``schema_metadata.source_case`` (DuckDB).
"""
from __future__ import annotations

import abc
import os
from pathlib import Path
from typing import Iterable

import pandas as pd

_HAS_DUCKDB = True
try:
    import duckdb  # type: ignore
except ImportError:  # pragma: no cover
    _HAS_DUCKDB = False


# ---------------------------------------------------------------------------
# Spec: the same declarative table catalogue used by the C2 migrator and the
# C2.5 case CLI. Each entry: (csv_stem_prefix, db_table, kind, kwargs).
# Kept inline here so this module has no cross-repo import surface.
# ---------------------------------------------------------------------------

PASSTHROUGH = "passthrough"
WIDE_TO_LONG = "wide_to_long"
WIDE_MULTILEVEL_TO_LONG = "wide_multilevel_to_long"
UNPIVOT_SINGLE_ROW = "unpivot_single_row"

TABLE_SPECS: list[tuple[str, str, str, dict]] = [
    # --- Dimension dicts ---
    ("oT_Dict_Node",            "node",             PASSTHROUGH, {}),
    ("oT_Dict_Generation",      "generator",        PASSTHROUGH, {}),
    ("oT_Dict_Technology",      "technology",       PASSTHROUGH, {}),
    ("oT_Dict_Storage",         "storage",          PASSTHROUGH, {}),
    ("oT_Dict_Zone",            "zone",             PASSTHROUGH, {}),
    ("oT_Dict_Area",            "area",             PASSTHROUGH, {}),
    ("oT_Dict_Region",          "region",           PASSTHROUGH, {}),
    ("oT_Dict_Period",          "period",           PASSTHROUGH, {}),
    ("oT_Dict_Stage",           "stage",            PASSTHROUGH, {}),
    ("oT_Dict_Scenario",        "scenario",         PASSTHROUGH, {}),
    ("oT_Dict_LoadLevel",       "loadlevel",        PASSTHROUGH, {}),
    ("oT_Dict_Circuit",         "circuit",          PASSTHROUGH, {}),
    ("oT_Dict_Line",            "line",             PASSTHROUGH, {}),
    ("oT_Dict_NodeToZone",      "node_to_zone",     PASSTHROUGH, {}),
    ("oT_Dict_ZoneToArea",      "zone_to_area",     PASSTHROUGH, {}),
    ("oT_Dict_AreaToRegion",    "area_to_region",   PASSTHROUGH, {}),

    # --- Entity config (long-format already) ---
    # pk_cols: explicit primary key. Replaces the SPECIAL_IDX_COLS map
    # InputData used to keep — declaring it next to the table avoids two
    # places of truth.
    ("oT_Data_Generation",      "generation_config",     PASSTHROUGH, dict(pk_cols=["Generator"])),
    ("oT_Data_Network",         "network_config",        PASSTHROUGH, dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_NodeLocation",    "node_location",         PASSTHROUGH, dict(pk_cols=["Node"])),

    # --- Scalar / probability tables ---
    # pk_cols: same explicit declaration; auto-detect via DEFAULT_IDX_COLS
    # would also work but the explicit form is grep-friendly.
    ("oT_Data_Scenario",        "scenario_probability",  PASSTHROUGH, dict(pk_cols=["Period", "Scenario"])),
    ("oT_Data_Period",          "period_weight",         PASSTHROUGH, dict(pk_cols=["Period"])),
    ("oT_Data_Stage",           "stage_weight",          PASSTHROUGH, dict(pk_cols=["Stage"])),
    ("oT_Data_Duration",        "duration",              PASSTHROUGH, dict(pk_cols=["Period", "Scenario", "LoadLevel"])),
    ("oT_Data_RESEnergy",       "res_energy",            PASSTHROUGH, dict(pk_cols=["Period", "Area"])),
    ("oT_Data_ReserveMargin",   "reserve_margin",        PASSTHROUGH, dict(pk_cols=["Period", "Area"])),
    ("oT_Data_Emission",        "emission",              PASSTHROUGH, dict(pk_cols=["Period", "Area"])),

    # --- Time series, stored long in DB / wide in CSV ---
    ("oT_Data_Demand",                  "demand",                   WIDE_TO_LONG, dict(entity="Node",      value="Demand")),
    ("oT_Data_VariableMaxGeneration",   "variable_max_generation",  WIDE_TO_LONG, dict(entity="Generator", value="MaxPower")),
    ("oT_Data_VariableMinGeneration",   "variable_min_generation",  WIDE_TO_LONG, dict(entity="Generator", value="MinPower")),
    ("oT_Data_VariableMaxConsumption",  "variable_max_consumption", WIDE_TO_LONG, dict(entity="Generator", value="MaxCharge")),
    ("oT_Data_VariableMinConsumption",  "variable_min_consumption", WIDE_TO_LONG, dict(entity="Generator", value="MinCharge")),
    ("oT_Data_VariableMaxEnergy",       "variable_max_energy",      WIDE_TO_LONG, dict(entity="Generator", value="MaxEnergy")),
    ("oT_Data_VariableMinEnergy",       "variable_min_energy",      WIDE_TO_LONG, dict(entity="Generator", value="MinEnergy")),
    ("oT_Data_VariableMaxStorage",      "variable_max_storage",     WIDE_TO_LONG, dict(entity="Generator", value="MaxStorage")),
    ("oT_Data_VariableMinStorage",      "variable_min_storage",     WIDE_TO_LONG, dict(entity="Generator", value="MinStorage")),
    ("oT_Data_EnergyInflows",           "energy_inflows",           WIDE_TO_LONG, dict(entity="Generator", value="Inflows")),
    ("oT_Data_EnergyOutflows",          "energy_outflows",          WIDE_TO_LONG, dict(entity="Generator", value="Outflows")),
    ("oT_Data_OperatingReserveUp",      "operating_reserve_up",     WIDE_TO_LONG, dict(entity="Area",      value="Reserve")),
    ("oT_Data_OperatingReserveDown",    "operating_reserve_down",   WIDE_TO_LONG, dict(entity="Area",      value="Reserve")),
    ("oT_Data_VariableFuelCost",        "variable_fuel_cost",       WIDE_TO_LONG, dict(entity="Generator", value="FuelCost")),
    ("oT_Data_VariableEmissionCost",    "variable_emission_cost",   WIDE_TO_LONG, dict(entity="Generator", value="EmissionCost")),
    ("oT_Data_Inertia",                 "inertia",                  WIDE_TO_LONG, dict(entity="Area",      value="Inertia")),

    # --- Single-row global parameter tables ---
    ("oT_Data_Parameter",       "parameter",    UNPIVOT_SINGLE_ROW, dict(value_type="VARCHAR")),
    ("oT_Data_Option",          "option_flag",  UNPIVOT_SINGLE_ROW, dict(value_type="INTEGER")),

    # =====================================================================
    # Hydropower topology (sSEP and similar cases).
    # The optional reservoir-mapping dicts can be empty (header-only). The
    # entity-config carries reservoir attributes; the wide time-series key
    # entity columns on reservoir name.
    # =====================================================================
    ("oT_Dict_Reservoir",               "reservoir",                    PASSTHROUGH, {}),
    ("oT_Dict_HydroToReservoir",        "hydro_to_reservoir",           PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToHydro",        "reservoir_to_hydro",           PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToReservoir",    "reservoir_to_reservoir",       PASSTHROUGH, {}),
    ("oT_Dict_PumpedHydroToReservoir",  "pumped_hydro_to_reservoir",    PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToPumpedHydro",  "reservoir_to_pumped_hydro",    PASSTHROUGH, {}),

    ("oT_Data_Reservoir",       "reservoir_config",     PASSTHROUGH, dict(pk_cols=["Reservoir"])),

    ("oT_Data_HydroInflows",    "hydro_inflows",        WIDE_TO_LONG, dict(entity="Reservoir", value="Inflows")),
    ("oT_Data_HydroOutflows",   "hydro_outflows",       WIDE_TO_LONG, dict(entity="Reservoir", value="Outflows")),
    ("oT_Data_VariableMaxVolume", "variable_max_volume", WIDE_TO_LONG, dict(entity="Reservoir", value="MaxVolume")),
    ("oT_Data_VariableMinVolume", "variable_min_volume", WIDE_TO_LONG, dict(entity="Reservoir", value="MinVolume")),

    # =====================================================================
    # Ramp reserves (Area-keyed, mirrors OperatingReserve*).
    # =====================================================================
    ("oT_Data_RampReserveUp",   "ramp_reserve_up",      WIDE_TO_LONG, dict(entity="Area", value="Reserve")),
    ("oT_Data_RampReserveDown", "ramp_reserve_down",    WIDE_TO_LONG, dict(entity="Area", value="Reserve")),

    # =====================================================================
    # Operating-reserve activation (Area-keyed, paired with OperatingReserve*).
    # Optional; only present when pIndReserveActivation is on.
    # =====================================================================
    ("oT_Data_OperatingReserveUpEnergy",   "operating_reserve_up_energy",   WIDE_TO_LONG, dict(entity="Area", value="Reserve")),
    ("oT_Data_OperatingReserveDownEnergy", "operating_reserve_down_energy", WIDE_TO_LONG, dict(entity="Area", value="Reserve")),

    # =====================================================================
    # Hydrogen sector (sSEP).
    # NetworkHydrogen mirrors Network (3-col composite PK). DemandHydrogen
    # mirrors Demand (Node-keyed wide).
    # =====================================================================
    ("oT_Data_NetworkHydrogen", "network_hydrogen_config", PASSTHROUGH,  dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_DemandHydrogen",  "demand_hydrogen",         WIDE_TO_LONG, dict(entity="Node", value="Demand")),

    # =====================================================================
    # Heat sector. Structurally identical to the hydrogen counterparts;
    # included here so heat-bearing cases load via DuckDB mode without
    # further spec changes. Schema is inferred from FLAG_MAPPING — verify
    # column names against a real heat-bearing case before relying on these.
    # =====================================================================
    ("oT_Data_NetworkHeat",     "network_heat_config",  PASSTHROUGH,  dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_DemandHeat",      "demand_heat",          WIDE_TO_LONG, dict(entity="Node", value="Demand")),
    ("oT_Data_ReserveMarginHeat", "reserve_margin_heat", PASSTHROUGH, dict(pk_cols=["Period", "Area"])),

    # =====================================================================
    # Multi-level-header wide tables (9n_PTDF).
    #   VariableTTCFrw/Bck  -> (InitialNode, FinalNode, Circuit)        N=3
    #   VariablePTDF        -> (InitialNode, FinalNode, Circuit, Node)  N=4
    # DB long shape: (Period, Scenario, LoadLevel, *entity_cols, <value>).
    # Read-side reconstruction (CSV mode and DuckDB mode) preserves the
    # pandas quirky multi-level index naming so downstream consumers see
    # identical DataFrames.
    # =====================================================================
    ("oT_Data_VariableTTCFrw",  "variable_ttc_frw",  WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit"], value="TTC")),
    ("oT_Data_VariableTTCBck",  "variable_ttc_bck",  WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit"], value="TTC")),
    ("oT_Data_VariablePTDF",    "variable_ptdf",     WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit", "Node"], value="PTDF")),
]

# csv_stem_prefix -> (db_table, kind, kwargs).
_SPEC_BY_CSV_STEM = {s[0]: (s[1], s[2], s[3]) for s in TABLE_SPECS}


# ---------------------------------------------------------------------------
# InputData helpers — kept here so source backends can share the post-read
# shaping that load_csv_with_index used to do for CSV.
# ---------------------------------------------------------------------------

# Columns to scan for index when a stem is not declared in TABLE_SPECS
# (e.g. hydropower / heat / H2 tables that aren't yet in the C2 spec).
DEFAULT_IDX_COLS = [
    "Period", "Scenario", "LoadLevel", "Area", "Generator",
    "InitialNode", "FinalNode", "Circuit", "Node", "Stage",
    "Reservoir",  # Optional hydro tables key on this.
]


def _apply_index(df: pd.DataFrame, stem: str) -> pd.DataFrame:
    """Set the multi-index that InputData expects on a wide-format table.

    Priority for choosing the index columns:
      1. ``pk_cols`` from the table's TABLE_SPECS entry (preferred — explicit).
      2. Auto-detection from DEFAULT_IDX_COLS (fallback for stems not in the spec,
         e.g. optional hydropower / heat / H2 tables).

    Wide-format tables (post-pivot) always end up keyed on
    ``[Period, Scenario, LoadLevel]`` and are handled by the WIDE_TO_LONG
    spec path before this function is called.
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
    """Convert a dict-table DataFrame into the values an init-time Pyomo
    ``Set(initialize=...)`` accepts.

    * 1-col DataFrame -> ``[v1, v2, ...]``
    * 2-col+ DataFrame -> ``[(a, b, ...), ...]`` (relation / membership).
    """
    if df.shape[1] == 1:
        return df.iloc[:, 0].tolist()
    return [tuple(row) for row in df.itertuples(index=False, name=None)]


# ---------------------------------------------------------------------------
# Source backends.
# ---------------------------------------------------------------------------

class InputSource(abc.ABC):
    """Abstract input source. Implementations: CSVSource, DuckDBSource."""

    case_name: str

    @abc.abstractmethod
    def list_data_stems(self) -> set[str]:
        """Stems of data tables present in the source (without the
        ``oT_Data_`` prefix or the ``_<casename>.csv`` suffix)."""

    @abc.abstractmethod
    def read_dict(self, stem: str) -> pd.DataFrame:
        """Return the dimension dict for ``stem`` as a DataFrame
        (no index set). Returns an empty DataFrame if absent."""

    @abc.abstractmethod
    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        """Return a data table in the *wide-format-indexed shape that
        InputData expects*. For Pattern-3 tables, the value column is
        pivoted out and the entity becomes columns. For multi-row tables
        with key columns, those are set as the index. For single-row
        tables (Option/Parameter), no index is set.

        ``header_levels`` mirrors ``pd.read_csv(header=...)`` for the few
        files that use multi-level column headers (VariableTTC*, VariablePTDF).
        Raises ``FileNotFoundError`` if the stem is absent.
        """

    def close(self) -> None:  # default no-op
        pass

    def __enter__(self) -> "InputSource":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open_source(path: str | os.PathLike) -> InputSource:
    """Sniff ``path`` and return a CSVSource or DuckDBSource."""
    p = Path(path).expanduser()
    if p.is_dir():
        return CSVSource(p)
    if p.is_file() and p.suffix == ".duckdb":
        if not _HAS_DUCKDB:
            raise ImportError(
                "duckdb is required to read .duckdb input sources; "
                "install it with `pip install duckdb`"
            )
        return DuckDBSource(p)
    raise ValueError(f"{p}: not a CSV case directory or a .duckdb file")


# ---------------------------------------------------------------------------
# CSV backend — preserves today's behaviour bit-for-bit.
# ---------------------------------------------------------------------------

class CSVSource(InputSource):
    def __init__(self, case_dir: Path) -> None:
        self.case_dir = Path(case_dir)
        cn = self._detect_case_name(self.case_dir)
        if cn is None:
            raise ValueError(
                f"{self.case_dir}: cannot detect case name "
                "(no oT_Data_Parameter_*.csv found)"
            )
        self.case_name = cn

    # DirName/CaseName the rest of openTEPES expects.
    @property
    def dir_name(self) -> str:
        return str(self.case_dir.parent)

    @staticmethod
    def _detect_case_name(case_dir: Path) -> str | None:
        for p in case_dir.glob("oT_Data_Parameter_*.csv"):
            return p.stem[len("oT_Data_Parameter_"):]
        return None

    def list_data_stems(self) -> set[str]:
        stems: set[str] = set()
        suffix = f"_{self.case_name}.csv"
        for p in self.case_dir.glob("oT_Data_*.csv"):
            name = p.name
            if name.endswith(suffix):
                # 'oT_Data_<stem>_<case>.csv'
                inner = name[len("oT_Data_"):-len(suffix)]
                if inner:
                    stems.add(inner)
        return stems

    def read_dict(self, stem: str) -> pd.DataFrame:
        path = self.case_dir / f"oT_Dict_{stem}_{self.case_name}.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, encoding="utf-8-sig")

    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        path = self.case_dir / f"oT_Data_{stem}_{self.case_name}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        # Multi-level header tables: derive level count from the spec if the
        # caller didn't pass header_levels, so the source is self-sufficient.
        spec = _SPEC_BY_CSV_STEM.get(f"oT_Data_{stem}")
        if header_levels is None and spec and spec[1] == WIDE_MULTILEVEL_TO_LONG:
            header_levels = list(range(len(spec[2]["entity_cols"])))
        if header_levels:
            return pd.read_csv(path, encoding="utf-8-sig",
                               header=header_levels, index_col=[0, 1, 2])
        df = pd.read_csv(path, encoding="utf-8-sig")
        # Option / Parameter are single-row, leave as-is (no index).
        if stem in ("Option", "Parameter"):
            return df
        return _apply_index(df, stem)


# ---------------------------------------------------------------------------
# DuckDB backend — reads in-memory via SQL, materialises nothing to disk.
# ---------------------------------------------------------------------------

class DuckDBSource(InputSource):
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._con = duckdb.connect(str(self.db_path), read_only=True)
        row = self._con.execute(
            "SELECT Value FROM schema_metadata WHERE Key='source_case'"
        ).fetchone()
        if not row or not row[0]:
            raise ValueError(
                f"{self.db_path}: schema_metadata.source_case is missing — "
                "DB was not produced by the C2 ingest script?"
            )
        self.case_name = row[0]
        # Pre-fetch existing DB table names (cheap; speeds up the
        # list_data_stems / table-presence checks called many times).
        rows = self._con.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
        self._existing_tables: set[str] = {r[0] for r in rows}

    @property
    def dir_name(self) -> str:
        # openTEPES_run still uses DirName for output paths. Anchor the
        # output to the .duckdb's parent so results survive the source's
        # close.
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
            raise FileNotFoundError(
                f"unknown oT_Data_{stem}_*.csv stem (no DB table mapped)"
            )
        db_table, kind, kwargs = spec
        if not self._table_present(db_table):
            raise FileNotFoundError(
                f"oT_Data_{stem}_*.csv not present in {self.db_path}"
            )

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
            # The reconstruction already has the multi-level column shape
            # plus the (Period, Scenario, LoadLevel) row index that the
            # CSV reader produces — no _apply_index needed.
            return self._reconstruct_wide_multilevel(db_table, **kwargs)

        raise ValueError(f"unknown spec kind for {stem}: {kind}")

    # ---- shape reconstruction (mirror of the C2 emit logic)

    def _reconstruct_wide(self, table_name: str, *, entity: str, value: str) -> pd.DataFrame:
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        id_cols = ["Period", "Scenario", "LoadLevel"]
        wide = df.pivot_table(
            index=id_cols, columns=entity, values=value, dropna=False, sort=False,
        ).reset_index()
        wide.columns.name = None
        return wide

    def _reconstruct_single_row(self, table_name: str, *, value_type: str) -> pd.DataFrame:
        import io
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        header = ",".join(str(n) for n in df["Name"])
        row = ",".join("" if pd.isna(v) else str(v) for v in df["Value"])
        return pd.read_csv(io.StringIO(header + "\n" + row))

    def _reconstruct_wide_multilevel(
        self, table_name: str, *, entity_cols: list[str], value: str
    ) -> pd.DataFrame:
        """Pivot the long DB table back to multi-level-column wide shape.

        Matches the pandas quirk where ``pd.read_csv(..., header=[0..N-1],
        index_col=[0,1,2])`` yields ``index.names = [None, None, None]`` and
        ``columns.names = ['Period', None, ...]``. Preserving this lets
        downstream CSV/DB consumers see identical DataFrames.
        """
        df = self._con.execute(f"SELECT * FROM {table_name}").df()
        id_cols = ["Period", "Scenario", "LoadLevel"]
        wide = df.pivot_table(
            index=id_cols, columns=entity_cols, values=value,
            dropna=False, sort=False,
        )
        wide.index.names = [None, None, None]
        wide.columns.names = ["Period"] + [None] * (len(entity_cols) - 1)
        return wide


