"""The CSV <-> DuckDB converters must round-trip a case input-identically.

Forward: ``write_case`` (Tool_CSV_to_DuckDB) writes a ``.duckdb``; the DuckDB backend must read it back with the same
sets and parameters as the original CSV case. Inverse: ``export_case`` (Tool_DuckDB_to_CSV) writes that ``.duckdb``
back out to CSV; a model built from the exported CSVs must again match the original. Both hops are compared with the
same snapshot the CSV/DuckDB input-parity probe uses. Covers all four transform kinds: passthrough, wide-to-long,
single-row unpivot (9n) and multi-level-header (9n_PTDF). No model is solved, so this runs in the fast CI job.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "openTEPES_DuckDB"))
from Tool_CSV_to_DuckDB import write_case
from Tool_DuckDB_to_CSV import export_case
from openTEPES._input_parity_test import compare_snapshots, snapshot

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


@pytest.mark.parametrize("case_name", ["9n", "9n_PTDF", "sSEP"])
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
