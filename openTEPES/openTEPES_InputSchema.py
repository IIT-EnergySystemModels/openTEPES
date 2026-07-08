"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026
openTEPES.openTEPES_InputSchema — declarative catalogue of every input table.

Each ``TABLE_SPECS`` entry is the tuple ``(csv_stem_prefix, db_table, kind, kwargs)``. Backends consume this single
catalogue to know (i) which stems exist, (ii) the DuckDB table name they correspond to, (iii) the read-side transform
required to recover the CSV-shaped DataFrame, and (iv) extra metadata such as primary-key columns or entity/value
names for long↔wide pivots.

The four transform kinds:

  * ``PASSTHROUGH``                table is stored long in DB and consumed long by ``InputData``; ``pk_cols`` declares
                                   the primary key (auto-detection via ``DEFAULT_IDX_COLS`` is the fallback).
  * ``WIDE_TO_LONG``               table is stored long in DB; on read, the value column is pivoted across the
                                   ``entity`` column to recover the wide CSV shape keyed on ``(Period, Scenario,
                                   LoadLevel)``.
  * ``WIDE_MULTILEVEL_TO_LONG``    same as ``WIDE_TO_LONG`` but ``entity_cols`` carries 3 or 4 column names that
                                   together form a multi-level column header (used by ``VariableTTC*`` and
                                   ``VariablePTDF``).
  * ``UNPIVOT_SINGLE_ROW``         table is stored as ``(Name, Value)`` rows in DB; on read, it is pivoted to the
                                   single-row, many-column CSV shape used by ``oT_Data_Parameter`` and ``oT_Data_Option``.

Adding a new input table is two lines: extend ``TABLE_SPECS`` with the entry, optionally extend ``DEFAULT_IDX_COLS``
if the primary key uses an index column the catalogue has not seen before. No Pyomo dependency, no I/O dependency.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Transform-kind constants. Kept as bare module-level strings (not an Enum) so that ``TABLE_SPECS`` stays grep-friendly
# from any editor and so external tooling reading the catalogue does not have to import the Enum class.
# ---------------------------------------------------------------------------

PASSTHROUGH = "passthrough"
WIDE_TO_LONG = "wide_to_long"
WIDE_MULTILEVEL_TO_LONG = "wide_multilevel_to_long"
UNPIVOT_SINGLE_ROW = "unpivot_single_row"


# ---------------------------------------------------------------------------
# Spec catalogue. Single source of truth across backends, the C2 migrator, and the case-management CLI.
# Entry shape: ``(csv_stem_prefix, db_table, kind, kwargs)``.
# ---------------------------------------------------------------------------

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
    # pk_cols: explicit primary key. Replaces the SPECIAL_IDX_COLS map InputData used to keep — declaring it next to
    # the table avoids two places of truth.
    ("oT_Data_Generation",      "generation_config",     PASSTHROUGH, dict(pk_cols=["Generator"])),
    ("oT_Data_Network",         "network_config",        PASSTHROUGH, dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_NodeLocation",    "node_location",         PASSTHROUGH, dict(pk_cols=["Node"])),

    # --- Scalar / probability tables ---
    # pk_cols: same explicit declaration; auto-detect via DEFAULT_IDX_COLS would also work but the explicit form is
    # grep-friendly.
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
    # Hydropower topology (sSEP and similar cases). The optional reservoir-mapping dicts can be empty (header-only).
    # The entity-config carries reservoir attributes; the wide time-series key entity columns on reservoir name.
    # =====================================================================
    ("oT_Dict_Reservoir",               "reservoir",                    PASSTHROUGH, {}),
    ("oT_Dict_HydroToReservoir",        "hydro_to_reservoir",           PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToHydro",        "reservoir_to_hydro",           PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToReservoir",    "reservoir_to_reservoir",       PASSTHROUGH, {}),
    ("oT_Dict_PumpedHydroToReservoir",  "pumped_hydro_to_reservoir",    PASSTHROUGH, {}),
    ("oT_Dict_ReservoirToPumpedHydro",  "reservoir_to_pumped_hydro",    PASSTHROUGH, {}),

    ("oT_Data_Reservoir",       "reservoir_config",     PASSTHROUGH, dict(pk_cols=["Reservoir"])),

    ("oT_Data_HydroInflows",      "hydro_inflows",        WIDE_TO_LONG, dict(entity="Reservoir", value="Inflows")),
    ("oT_Data_HydroOutflows",     "hydro_outflows",       WIDE_TO_LONG, dict(entity="Reservoir", value="Outflows")),
    ("oT_Data_VariableMaxVolume", "variable_max_volume",  WIDE_TO_LONG, dict(entity="Reservoir", value="MaxVolume")),
    ("oT_Data_VariableMinVolume", "variable_min_volume",  WIDE_TO_LONG, dict(entity="Reservoir", value="MinVolume")),

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
    # Hydrogen sector (sSEP). NetworkHydrogen mirrors Network (3-col composite PK). DemandHydrogen mirrors Demand
    # (Node-keyed wide).
    # =====================================================================
    ("oT_Data_NetworkHydrogen", "network_hydrogen_config", PASSTHROUGH,  dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_DemandHydrogen",  "demand_hydrogen",         WIDE_TO_LONG, dict(entity="Node", value="Demand")),

    # =====================================================================
    # Heat sector. Structurally identical to the hydrogen counterparts; included here so heat-bearing cases load via
    # DuckDB mode without further spec changes. Schema is inferred from FLAG_MAPPING — verify column names against a
    # real heat-bearing case before relying on these.
    # =====================================================================
    ("oT_Data_NetworkHeat",       "network_heat_config",  PASSTHROUGH,  dict(pk_cols=["InitialNode", "FinalNode", "Circuit"])),
    ("oT_Data_DemandHeat",        "demand_heat",          WIDE_TO_LONG, dict(entity="Node", value="Demand")),
    ("oT_Data_ReserveMarginHeat", "reserve_margin_heat",  PASSTHROUGH,  dict(pk_cols=["Period", "Area"])),

    # =====================================================================
    # Multi-level-header wide tables (9n_PTDF).
    #   VariableTTCFrw/Bck  -> (InitialNode, FinalNode, Circuit)        N=3
    #   VariablePTDF        -> (InitialNode, FinalNode, Circuit, Node)  N=4
    # DB long shape: (Period, Scenario, LoadLevel, *entity_cols, <value>).
    # Read-side reconstruction (CSV mode and DuckDB mode) preserves the pandas quirky multi-level index naming so
    # downstream consumers see identical DataFrames.
    # =====================================================================
    ("oT_Data_VariableTTCFrw",  "variable_ttc_frw",  WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit"], value="TTC")),
    ("oT_Data_VariableTTCBck",  "variable_ttc_bck",  WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit"], value="TTC")),
    ("oT_Data_VariablePTDF",    "variable_ptdf",     WIDE_MULTILEVEL_TO_LONG,
        dict(entity_cols=["InitialNode", "FinalNode", "Circuit", "Node"], value="PTDF")),
]

# csv_stem_prefix -> (db_table, kind, kwargs). Derived lookup so backends can find a spec in O(1) without scanning.
_SPEC_BY_CSV_STEM: dict[str, tuple[str, str, dict]] = {s[0]: (s[1], s[2], s[3]) for s in TABLE_SPECS}


# ---------------------------------------------------------------------------
# Columns to scan for index when a stem is not declared in TABLE_SPECS (e.g. hydropower / heat / H2 tables that
# aren't yet in the C2 spec). Kept here so backend code does not duplicate the list.
# ---------------------------------------------------------------------------

DEFAULT_IDX_COLS: list[str] = [
    "Period", "Scenario", "LoadLevel", "Area", "Generator",
    "InitialNode", "FinalNode", "Circuit", "Node", "Stage",
    "Reservoir",  # Optional hydro tables key on this.
]
