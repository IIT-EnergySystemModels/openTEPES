"""
Tool_openTEPES_CSV_to_DuckDB — command-line wrapper to write a CSV case to a ``.duckdb`` input file.

    python scripts/openTEPES_CSV_to_DuckDB/Tool_openTEPES_CSV_to_DuckDB.py cases/9n
    python scripts/openTEPES_CSV_to_DuckDB/Tool_openTEPES_CSV_to_DuckDB.py cases/9n --db out/9n.duckdb

The resulting file is read back by openTEPES_run when the case name ends in ``.duckdb``. See openTEPES_InputDuckDBWriter.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openTEPES_InputDuckDBWriter import write_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Write an openTEPES CSV case to a .duckdb input file.")
    parser.add_argument("case_dir", type=Path, help="Case directory with oT_Data_*.csv and oT_Dict_*.csv files.")
    parser.add_argument("--case-name", default=None, help="Case name (default: detected from oT_Data_Parameter_*.csv).")
    parser.add_argument("--db", type=Path, default=None, help="Output .duckdb path (default: <case_dir>/../<case>.duckdb).")
    args = parser.parse_args()

    db_path = write_case(args.case_dir, args.db, args.case_name)
    print(f"wrote {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
