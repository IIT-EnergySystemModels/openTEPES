"""
Tool_DuckDB_to_CSV — export a ``.duckdb`` input file back to an openTEPES CSV case.

Offline utility (not part of the core model), the inverse of ``Tool_CSV_to_DuckDB``. openTEPES can already read a
``.duckdb`` input directly at solve time; this tool is for inspecting, diffing or hand-editing a ``.duckdb`` case as
plain CSVs, and for round-trip checks.

It does no shape work of its own. The in-package ``openTEPES_InputDuckDBSource`` reader already reconstructs every
table back to its wide CSV shape (all driven by ``openTEPES_InputSchema.TABLE_SPECS``); this tool reads each table
through that reader and writes it out as ``oT_Data_*`` / ``oT_Dict_*`` CSVs. Reusing the reader is deliberate — a
hand-written inverse transform here would drift from the reader.

The result is input-identical, not byte-identical: a re-read of the exported CSVs yields the same frames as the
``.duckdb`` (float and NaN formatting or column order may differ on disk).

Needs openTEPES installed. Run it as a script:

    python scripts/openTEPES_DuckDB/Tool_DuckDB_to_CSV.py cases/9n.duckdb
    python scripts/openTEPES_DuckDB/Tool_DuckDB_to_CSV.py cases/9n.duckdb --out cases/9n_from_db
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from openTEPES.openTEPES_InputSchema import TABLE_SPECS, WIDE_MULTILEVEL_TO_LONG
from openTEPES.openTEPES_InputSource import open_source

# Transform kind per CSV stem prefix, so we know how each reconstructed frame maps back onto disk.
_KIND_BY_STEM = {stem_prefix: kind for stem_prefix, _table, kind, _kwargs in TABLE_SPECS}


def _write_flat_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a single-header frame. ``read_data``/``read_dict`` may return the primary keys as the index; move them
    back to columns so the CSV reader sees the original wide layout. A frame with no real index is written as-is."""
    if any(name is not None for name in df.index.names):
        df = df.reset_index()
    df.to_csv(path, index=False, encoding="utf-8-sig")


def export_case(db_path, out_dir=None, case_name: str | None = None) -> Path:
    """Export every table in ``db_path`` to CSV. ``case_name`` defaults to the DB's ``schema_metadata.source_case``.
    ``out_dir`` defaults to ``<db_path parent>/<case_name>``. Returns the output directory."""
    src = open_source(db_path)
    try:
        case = case_name or src.case_name
        out = Path(out_dir) if out_dir is not None else Path(db_path).parent / case
        out.mkdir(parents=True, exist_ok=True)

        for stem in sorted(src.list_data_stems()):
            df = src.read_data(stem)
            path = out / f"oT_Data_{stem}_{case}.csv"
            if _KIND_BY_STEM.get(f"oT_Data_{stem}") == WIDE_MULTILEVEL_TO_LONG:
                # keep the 3-column row index and the multi-level header (read back with header=[...], index_col=[0,1,2])
                df.to_csv(path, encoding="utf-8-sig")
            else:
                _write_flat_csv(df, path)

        for stem in sorted(src.list_dict_stems()):
            src.read_dict(stem).to_csv(out / f"oT_Dict_{stem}_{case}.csv", index=False, encoding="utf-8-sig")
    finally:
        src.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a .duckdb openTEPES input file back to a CSV case.")
    parser.add_argument("db_path", type=Path, help="Input .duckdb file.")
    parser.add_argument("--case-name", default=None, help="Case name for the output filenames (default: from the DB).")
    parser.add_argument("--out", type=Path, default=None, help="Output directory (default: <db parent>/<case>).")
    args = parser.parse_args()

    out = export_case(args.db_path, args.out, args.case_name)
    n = len(list(out.glob("oT_*.csv")))
    print(f"wrote {n} CSV files to {out}")


if __name__ == "__main__":
    main()
