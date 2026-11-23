"""The CSV <-> DuckDB converters must round-trip a case input-identically.

Forward: ``write_case`` (Tool_CSV_to_DuckDB) writes a ``.duckdb``; the DuckDB backend must read it back with the same
sets and parameters as the original CSV case. Inverse: ``export_case`` (Tool_DuckDB_to_CSV) writes that ``.duckdb``
back out to CSV; a model built from the exported CSVs must again match the original. Both hops are compared with the
same snapshot the CSV/DuckDB input-parity probe uses. Covers all four transform kinds: passthrough, wide-to-long,
single-row unpivot (9n) and multi-level-header (9n_PTDF). No model is solved, so this runs in the fast CI job.

The converter stores each table with the columns of its CSV file (schema version 2). The tests at the end check that a
file in the earlier layout (schema version 1, every time series one row per value) still reads, that a time series with
two column names differing only in case is stored one row per value, and that the ``<table>_long`` views hold every value.
"""
import os
import shutil
import sys

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "openTEPES_DuckDB"))
from Tool_CSV_to_DuckDB import _unpivot_single_row, _wide_to_long, write_case
from Tool_DuckDB_to_CSV import export_case
from openTEPES._input_parity_test import compare_snapshots, snapshot
from openTEPES.openTEPES_InputSchema import TABLE_SPECS, WIDE_TO_LONG
from openTEPES.openTEPES_InputSource import open_source

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


@pytest.mark.parametrize("case_name", ["9n", "9n_PTDF", "sSEP", "9n_AC"])
def test_csv_duckdb_csv_roundtrip(case_name, tmp_path):
    case_dir = os.path.join(CASES_DIR, case_name)
    base = snapshot(case_dir)

    # forward: CSV -> DuckDB reads back identically
    db_path = write_case(case_dir, tmp_path / f"{case_name}.duckdb")
    diffs = compare_snapshots(base, snapshot(str(db_path)))
    assert not diffs, f"{case_name}: CSV vs written DuckDB differ:\n" + "\n".join(diffs[:10])

    # inverse: DuckDB -> CSV reads back identically
    out_dir = export_case(db_path, tmp_path / f"{case_name}_from_db")
    diffs = compare_snapshots(base, snapshot(str(out_dir)))
    assert not diffs, f"{case_name}: CSV vs exported CSV differ:\n" + "\n".join(diffs[:10])


def test_shipped_example_duckdb_matches_9n_csv():
    """The tracked example openTEPES/cases/9n_duckdb/9n.duckdb must stay in sync with the 9n CSV case.

    It is the one .duckdb committed to the repo; it is generated from the 9n CSV case. If someone edits that CSV
    case and forgets to regenerate the .duckdb, the example goes stale. This compares the two the same way the
    round-trip test does, catching that drift.
    """
    csv_case = os.path.join(CASES_DIR, "9n")
    example_db = os.path.join(CASES_DIR, "9n_duckdb", "9n.duckdb")
    diffs = compare_snapshots(snapshot(csv_case), snapshot(example_db))
    assert not diffs, (
        "openTEPES/cases/9n_duckdb/9n.duckdb is stale vs the 9n CSV case — regenerate it with\n"
        "  python scripts/openTEPES_DuckDB/Tool_CSV_to_DuckDB.py openTEPES/cases/9n "
        "--db openTEPES/cases/9n_duckdb/9n.duckdb\n" + "\n".join(diffs[:10])
    )


_SPEC_BY_DB_TABLE = {table: (kind, kwargs) for _stem, table, kind, kwargs in TABLE_SPECS}


def _to_schema_version_1(db_path):
    """Rewrite a converted file in the layout of schema version 1: every time series one row per value, the single-row
    tables as (Name, Value) rows, and no table_layout table or views. Uses the converter's own long-layout helpers."""
    con = duckdb.connect(str(db_path))
    try:
        for table, _layout in con.execute("SELECT * FROM table_layout WHERE Layout = 'wide'").fetchall():
            kind, kwargs = _SPEC_BY_DB_TABLE[table]
            df = con.execute(f"SELECT * FROM {table}").df()
            if kind == WIDE_TO_LONG:
                con.execute(f"DROP VIEW {table}_long")
                df = _wide_to_long(df, **kwargs)
            else:
                df = _unpivot_single_row(df, **kwargs)
            con.register("__df", df)
            con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM __df")
            con.unregister("__df")
        con.execute("DROP TABLE table_layout")
        con.execute("UPDATE schema_metadata SET Value = '1' WHERE Key = 'schema_version'")
    finally:
        con.close()


def test_a_file_in_the_earlier_long_layout_still_reads(tmp_path):
    case_dir = os.path.join(CASES_DIR, "9n")
    db_path = write_case(case_dir, tmp_path / "9n.duckdb")
    _to_schema_version_1(db_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        columns = [r[0] for r in con.execute("DESCRIBE demand").fetchall()]
    assert columns == ["Period", "Scenario", "LoadLevel", "Node", "Demand"]  # one row per node and hour

    diffs = compare_snapshots(snapshot(case_dir), snapshot(str(db_path)))
    assert not diffs, "9n: CSV vs schema-version-1 DuckDB differ:\n" + "\n".join(diffs[:10])


def test_column_names_differing_only_in_case_keep_the_table_long(tmp_path):
    case_dir = tmp_path / "9n"
    shutil.copytree(os.path.join(CASES_DIR, "9n"), case_dir)
    csv_path = case_dir / "oT_Data_VariableMaxGeneration_9n.csv"
    df = pd.read_csv(csv_path)
    df[df.columns[3].lower()] = df[df.columns[3]] * 0.5
    df.to_csv(csv_path, index=False)

    db_path = write_case(case_dir, tmp_path / "9n.duckdb")
    with duckdb.connect(str(db_path), read_only=True) as con:
        layout = dict(con.execute("SELECT * FROM table_layout").fetchall())
    assert layout["variable_max_generation"] == "long"
    assert layout["demand"] == "wide"

    with open_source(case_dir) as csv_src, open_source(db_path) as db_src:
        expected = csv_src.read_data("VariableMaxGeneration")
        actual = db_src.read_data("VariableMaxGeneration")
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)


def test_the_long_views_hold_every_value_of_the_wide_tables(tmp_path):
    db_path = write_case(os.path.join(CASES_DIR, "9n"), tmp_path / "9n.duckdb")
    with duckdb.connect(str(db_path), read_only=True) as con:
        wide = [t for t, layout in con.execute("SELECT * FROM table_layout").fetchall()
                if layout == "wide" and _SPEC_BY_DB_TABLE[t][0] == WIDE_TO_LONG]
        assert "demand" in wide
        for table in wide:
            df = con.execute(f"SELECT * FROM {table}").df()
            values = df.iloc[:, 3:].notna().sum().sum()
            assert con.execute(f"SELECT count(*) FROM {table}_long").fetchone()[0] == values, table
        node = con.execute("SELECT * FROM demand").df().columns[3]
        first = con.execute(f'SELECT "{node}" FROM demand LIMIT 1').fetchone()[0]
        assert con.execute(f"SELECT Demand FROM demand_long WHERE Node = '{node}' LIMIT 1").fetchone()[0] == first
