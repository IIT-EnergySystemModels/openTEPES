"""Parity probe for the OutputResults refactor.

Snapshots every ``oT_Result_*.csv`` (and ``.csv.gz``) that a solve writes
into a case output directory, capturing each table's shape, columns, and
values so two snapshots can be diff'd with a float tolerance. Used to prove
that splitting ``openTEPES_OutputResults.py`` into flat per-concern modules
leaves the written results bit-for-bit (within tolerance) unchanged:

    # on master
    python -m openTEPES._output_parity_test snapshot <case_out_dir> before.pkl
    # on the split branch, after re-solving the same case
    python -m openTEPES._output_parity_test snapshot <case_out_dir> after.pkl
    python -m openTEPES._output_parity_test diff before.pkl after.pkl

``diff`` exits 0 when the two snapshots agree (same files, shapes, columns,
and numeric values within ``rtol``/``atol``), 1 otherwise. The harness is
intentionally code-version-agnostic: it reads only the CSVs on disk, so the
two snapshots may come from different checkouts of the package.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Default float tolerance for value comparison. Solves are deterministic for
# a given solver/seed, so outputs should agree far tighter than this; the
# slack absorbs CSV round-tripping (float repr) and harmless reorderings.
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
    """Longest common trailing ``_``-token run shared by every stem.

    Result files are ``oT_Result_<Table>_<CaseName>``; table names differ
    between files while the ``<CaseName>`` suffix (which may itself contain
    underscores, e.g. ``SE2035_EP_G0``) is shared. The common trailing tokens
    are therefore exactly the case name — robust to underscores in either the
    table name or the case name. Returns [] when nothing is shared (single
    file, or all distinct), leaving stems unstripped.
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
    # Never strip the whole stem away (would happen if a table name equals the
    # case name); keep at least one leading token.
    if common and len(common) >= min(len(t) for t in token_lists):
        common = common[: -1]
    return list(reversed(common))


def _strip_case_suffix(stem: str, case_tokens: list[str]) -> str:
    if not case_tokens:
        return stem
    suffix = "_" + "_".join(case_tokens)
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def _serialise_csv(path: Path) -> dict[str, Any]:
    """Read one result CSV into a comparable snapshot record.

    Numeric columns are stored as a float ndarray (NaN-preserving); the
    object/string block is stored separately so categorical labels are
    compared exactly while numbers get tolerance.
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
    """Snapshot every result CSV in ``out_dir`` keyed by case-agnostic name."""
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
    # Object/categorical block: exact match.
    if a["obj_cols"] != b["obj_cols"]:
        return f"object columns differ: {a['obj_cols']} vs {b['obj_cols']}"
    if a["obj"].shape and not np.array_equal(a["obj"], b["obj"]):
        return "categorical/label values differ"
    # Numeric block: tolerance.
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
