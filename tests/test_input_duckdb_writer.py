"""The CSV -> DuckDB writer must produce a case the DuckDB backend reads back input-identically.

``write_case`` (scripts/openTEPES_CSV_to_DuckDB/openTEPES_InputDuckDBWriter) is the inverse of the DuckDB input
backend. For each bundled case this test writes a ``.duckdb`` into a temp dir and asserts that a model built from it
(via ``InputData``) has the same sets and parameters as one built from the CSV case — the same snapshot compare the
CSV/DuckDB input-parity probe uses. Covers all four transform kinds: passthrough, wide-to-long, single-row unpivot
(9n), and multi-level-header (9n_PTDF). No model is solved, so this runs in the fast CI job.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "openTEPES_CSV_to_DuckDB"))
from openTEPES_InputDuckDBWriter import write_case
from openTEPES._input_parity_test import compare_snapshots, snapshot

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


@pytest.mark.parametrize("case_name", ["9n", "9n_PTDF", "sSEP"])
def test_written_duckdb_matches_csv(case_name, tmp_path):
    case_dir = os.path.join(CASES_DIR, case_name)
    db_path = write_case(case_dir, tmp_path / f"{case_name}.duckdb")

    diffs = compare_snapshots(snapshot(case_dir), snapshot(str(db_path)))
    assert not diffs, f"{case_name}: CSV vs written DuckDB differ:\n" + "\n".join(diffs[:10])
