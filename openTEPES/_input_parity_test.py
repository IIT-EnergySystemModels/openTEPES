"""Parity probe for the InputData refactor.

Loads a case via ``InputData`` and snapshots every model-visible piece of
state: each Pyomo ``Set`` (as a sorted list), every ``mTEPES.dFrame[k]``
DataFrame, and every ``mTEPES.dPar[k]`` value. Snapshots are picklable.

Two snapshots can be diff'd with ``compare_snapshots(a, b)``; the diff
result is a list of human-readable strings describing every key whose
value disagrees.

Used like:

    python -m openTEPES._input_parity_test snapshot <case_dir_or_db> <out.pkl>
    python -m openTEPES._input_parity_test diff <a.pkl> <b.pkl>
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyomo.environ import ConcreteModel, Set


def _serialise_pyomo_set(s) -> dict:
    members = list(s)
    return {
        "ordered": s.isordered(),
        "len":     len(members),
        "head":    members[:5],
        "tail":    members[-5:],
        # Full membership for compact sets; sample for huge ones.
        "members": members if len(members) <= 10_000 else None,
        "doc":     s.doc,
    }


def _serialise_value(v: Any) -> Any:
    if isinstance(v, pd.DataFrame):
        return {"__df__": True, "shape": v.shape,
                "cols": list(map(str, v.columns)),
                "values": v.to_numpy()}
    if isinstance(v, pd.Series):
        return {"__series__": True, "shape": v.shape,
                "name": str(v.name) if v.name is not None else None,
                "index": list(v.index),
                "values": v.to_numpy()}
    return v


def snapshot(case_path: str) -> dict:
    """Build a fresh mTEPES via InputData on the given path and return a
    serialisable dict of its model-visible state.

    Handles both directory cases (CSV) and ``.duckdb`` file cases — the
    same sniff logic as ``openTEPES_run`` would apply.
    """
    # Late imports so a parity probe in a freshly-cloned tree doesn't
    # error if optional deps are missing at import time.
    from openTEPES.openTEPES_InputData import InputData
    from openTEPES.src import open_source

    mTEPES = ConcreteModel("parity_probe")
    p = Path(case_path)
    if p.is_file() and p.suffix == ".duckdb":
        source = open_source(p)
        mTEPES.pInputSource = source
        # InputData reads from pInputSource; DirName/CaseName are only
        # used for log path strings.
        InputData(str(p.parent), source.case_name, mTEPES, "No")
        source.close()
    else:
        InputData(str(p.parent), p.name, mTEPES, "No")

    out: dict[str, Any] = {"sets": {}, "dFrame": {}, "dPar": {}}

    for name in dir(mTEPES):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(mTEPES, name)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, Set):
            out["sets"][name] = _serialise_pyomo_set(obj)

    if hasattr(mTEPES, "dFrame"):
        for k, df in mTEPES.dFrame.items():
            out["dFrame"][k] = _serialise_value(df)

    if hasattr(mTEPES, "dPar"):
        for k, v in mTEPES.dPar.items():
            out["dPar"][k] = _serialise_value(v)

    return out


def _values_equal(a: Any, b: Any) -> tuple[bool, str]:
    if isinstance(a, dict) and a.get("__df__") and isinstance(b, dict) and b.get("__df__"):
        if a["shape"] != b["shape"]:
            return False, f"df shape {a['shape']} vs {b['shape']}"
        if a["cols"] != b["cols"]:
            return False, f"df cols differ: {a['cols'][:3]}... vs {b['cols'][:3]}..."
        ax, bx = a["values"], b["values"]
        try:
            if ax.dtype.kind in "fc" or bx.dtype.kind in "fc":
                if np.allclose(np.nan_to_num(ax.astype(float)),
                               np.nan_to_num(bx.astype(float)),
                               rtol=0, atol=1e-12, equal_nan=True):
                    return True, ""
            elif np.array_equal(ax, bx):
                return True, ""
        except Exception as e:
            return False, f"df compare err: {e}"
        return False, "df values differ"
    if isinstance(a, dict) and a.get("__series__") and isinstance(b, dict) and b.get("__series__"):
        if a["shape"] != b["shape"]:
            return False, f"series shape {a['shape']} vs {b['shape']}"
        if a["index"] != b["index"]:
            return False, "series index differs"
        ax, bx = a["values"], b["values"]
        if ax.dtype.kind in "fc" or bx.dtype.kind in "fc":
            if np.allclose(np.nan_to_num(ax.astype(float)),
                           np.nan_to_num(bx.astype(float)),
                           rtol=0, atol=1e-12, equal_nan=True):
                return True, ""
            return False, "series values differ"
        if np.array_equal(ax, bx):
            return True, ""
        return False, "series values differ"
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return False, f"dict keys {sorted(a)[:5]} vs {sorted(b)[:5]}"
        for k in a:
            ok, why = _values_equal(a[k], b[k])
            if not ok:
                return False, f"dict[{k!r}]: {why}"
        return True, ""
    if isinstance(a, list) and isinstance(b, list):
        if a == b:
            return True, ""
        return False, f"list len {len(a)} vs {len(b)}"
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        try:
            if np.array_equal(a, b):
                return True, ""
            if a.dtype.kind in "fc" or b.dtype.kind in "fc":
                if np.allclose(a, b, rtol=0, atol=1e-12, equal_nan=True):
                    return True, ""
        except Exception as e:
            return False, f"ndarray compare err: {e}"
        return False, "ndarray values differ"
    if a == b:
        return True, ""
    return False, f"value {a!r} vs {b!r}"


def compare_snapshots(a: dict, b: dict) -> list[str]:
    diffs: list[str] = []

    for section in ("sets", "dFrame", "dPar"):
        ak, bk = set(a[section]), set(b[section])
        if ak - bk:
            diffs.append(f"{section}: only-in-A keys: {sorted(ak - bk)[:5]}")
        if bk - ak:
            diffs.append(f"{section}: only-in-B keys: {sorted(bk - ak)[:5]}")
        for k in sorted(ak & bk):
            ok, why = _values_equal(a[section][k], b[section][k])
            if not ok:
                diffs.append(f"{section}[{k!r}]: {why}")
    return diffs


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "snapshot":
        case_path, out_pkl = sys.argv[2], sys.argv[3]
        snap = snapshot(case_path)
        Path(out_pkl).write_bytes(pickle.dumps(snap))
        print(f"snapshot: {len(snap['sets'])} sets, "
              f"{len(snap['dFrame'])} dFrame keys, "
              f"{len(snap['dPar'])} dPar keys -> {out_pkl}")
        return 0
    if cmd == "diff":
        a = pickle.loads(Path(sys.argv[2]).read_bytes())
        b = pickle.loads(Path(sys.argv[3]).read_bytes())
        diffs = compare_snapshots(a, b)
        if not diffs:
            print("OK — snapshots identical (sets, dFrame, dPar).")
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
