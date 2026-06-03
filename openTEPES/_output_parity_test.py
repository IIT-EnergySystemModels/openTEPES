"""Check that two runs produce the same result files.

This is the output-side version of ``_input_parity_test.py``. It takes a
"snapshot" of every ``oT_Result_*.csv`` (and ``.csv.gz``) file a run writes
to a case folder, saving each table's size, column names and values. Two
snapshots can then be compared: numbers are compared with a small tolerance,
text labels exactly.

It is meant for safely changing the output code. If you reorganise the
``openTEPES_OutputResults*.py`` modules, the result files should stay the
same. To check that, take a snapshot before and after the change and compare:

    # before the change
    python -m openTEPES._output_parity_test snapshot <case_output_folder> before.pkl
    # after the change, having run the same case again
    python -m openTEPES._output_parity_test snapshot <case_output_folder> after.pkl
    python -m openTEPES._output_parity_test diff before.pkl after.pkl

``diff`` exits with code 0 if the two snapshots match (same files, sizes,
columns and numbers within tolerance) and 1 if they differ. The tool only
reads the CSV files on disk, so the two snapshots can come from two
different versions of the code.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# How close two numbers must be to count as equal. The same case solved
# twice should match much more tightly than this; the small margin just
# absorbs rounding from writing numbers out to CSV and reading them back.
RTOL = 1e-9
ATOL = 1e-9


def _result_files(out_dir: Path) -> list[Path]:
    """Every oT_Result_*.csv / .csv.gz in a case output directory, sorted."""
    files = list(out_dir.glob("oT_Result_*.csv")) + list(out_dir.glob("oT_Result_*.csv.gz"))
    return sorted(files, key=lambda p: p.name)


def _result_stem(name: str) -> str:
    """``oT_Result_GenerationInvestment_9n.csv`` -> ``GenerationInvestment_9n``."""
    stem = name[: -len(".csv.gz")] if name.endswith(".csv.gz") else name[: -len(".csv")]
    return stem[len("oT_Result_"):] if stem.startswith("oT_Result_") else stem


def _infer_case_tokens(stems: list[str]) -> list[str]:
    """Find the case name shared by all result file names.

    Result files are named ``oT_Result_<Table>_<CaseName>``. The table part
    is different in every file, but the case name at the end is the same. So
    the words (split on ``_``) that all the names share at the end are the
    case name. This works even when the case name has underscores in it, such
    as ``SE2035_EP_G0``. Returns [] if there is nothing shared (only one
    file), in which case the names are left as they are.
    """
    if len(stems) < 2:
        return []
    token_lists = [s.split("_") for s in stems]
    common: list[str] = []
    for tail in zip(*(reversed(t) for t in token_lists)):
        if len(set(tail)) == 1:
            common.append(tail[0])
        else:
            break
    # Keep at least the first word of each name, so a table whose name happens
    # to match the case name is not erased completely.
    if common and len(common) >= min(len(t) for t in token_lists):
        common = common[: -1]
    return list(reversed(common))


def _strip_case_suffix(stem: str, case_tokens: list[str]) -> str:
    if not case_tokens:
        return stem
    suffix = "_" + "_".join(case_tokens)
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def _serialise_csv(path: Path) -> dict[str, Any]:
    """Read one result CSV into a record we can compare later.

    Number columns and text columns are kept apart, so that numbers can be
    compared with a tolerance and text labels can be compared exactly.
    """
    df = pd.read_csv(path)
    num = df.select_dtypes(include=[np.number])
    obj = df.drop(columns=num.columns)
    return {
        "shape": tuple(df.shape),
        "cols": list(map(str, df.columns)),
        "num_cols": list(map(str, num.columns)),
        "num": num.to_numpy(dtype=float) if num.shape[1] else np.empty((len(df), 0)),
        "obj_cols": list(map(str, obj.columns)),
        "obj": obj.astype(str).to_numpy() if obj.shape[1] else np.empty((len(df), 0), dtype=object),
    }


def snapshot(out_dir: str) -> dict[str, Any]:
    """Snapshot every result CSV in ``out_dir``, keyed by table name (the
    case name is removed so snapshots of the same case under different names
    still match)."""
    p = Path(out_dir)
    if not p.is_dir():
        raise NotADirectoryError(f"{out_dir} is not a directory")
    files = _result_files(p)
    case_tokens = _infer_case_tokens([_result_stem(f.name) for f in files])
    tables: dict[str, Any] = {}
    for f in files:
        key = _strip_case_suffix(_result_stem(f.name), case_tokens)
        tables[key] = _serialise_csv(f)
    return {"out_dir": str(p), "n_tables": len(tables), "tables": tables}


def _compare_table(a: dict, b: dict, rtol: float, atol: float) -> str | None:
    if a["shape"] != b["shape"]:
        return f"shape {a['shape']} vs {b['shape']}"
    if a["cols"] != b["cols"]:
        return f"columns differ: {a['cols'][:4]}... vs {b['cols'][:4]}..."
    # Text columns: must match exactly.
    if a["obj_cols"] != b["obj_cols"]:
        return f"text columns differ: {a['obj_cols']} vs {b['obj_cols']}"
    if a["obj"].shape and not np.array_equal(a["obj"], b["obj"]):
        return "text/label values differ"
    # Number columns: compared with a tolerance.
    if a["num_cols"] != b["num_cols"]:
        return f"numeric columns differ: {a['num_cols']} vs {b['num_cols']}"
    ax, bx = a["num"], b["num"]
    if ax.size:
        close = np.isclose(ax, bx, rtol=rtol, atol=atol, equal_nan=True)
        if not close.all():
            bad = np.argwhere(~close)
            i, j = bad[0]
            col = a["num_cols"][j]
            return (f"{int((~close).sum())} numeric cell(s) differ; "
                    f"first at row {int(i)} col {col!r}: "
                    f"{ax[i, j]!r} vs {bx[i, j]!r}")
    return None


def compare_snapshots(a: dict, b: dict, rtol: float = RTOL, atol: float = ATOL) -> list[str]:
    diffs: list[str] = []
    at, bt = a["tables"], b["tables"]
    ak, bk = set(at), set(bt)
    if ak - bk:
        diffs.append(f"only-in-A tables: {sorted(ak - bk)}")
    if bk - ak:
        diffs.append(f"only-in-B tables: {sorted(bk - ak)}")
    for k in sorted(ak & bk):
        why = _compare_table(at[k], bt[k], rtol, atol)
        if why:
            diffs.append(f"{k}: {why}")
    return diffs


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "snapshot":
        out_dir, out_pkl = sys.argv[2], sys.argv[3]
        snap = snapshot(out_dir)
        Path(out_pkl).write_bytes(pickle.dumps(snap))
        print(f"snapshot: {snap['n_tables']} result tables -> {out_pkl}")
        return 0
    if cmd == "diff":
        a = pickle.loads(Path(sys.argv[2]).read_bytes())
        b = pickle.loads(Path(sys.argv[3]).read_bytes())
        diffs = compare_snapshots(a, b)
        if not diffs:
            print(f"OK — snapshots identical ({a['n_tables']} vs {b['n_tables']} result tables).")
            return 0
        for d in diffs[:50]:
            print(f"DIFF  {d}")
        if len(diffs) > 50:
            print(f"  ...and {len(diffs) - 50} more")
        return 1
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
