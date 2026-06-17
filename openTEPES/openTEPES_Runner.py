"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 17, 2026

openTEPES.openTEPES_Runner — Mode A pre-build sweep runner.

Run many cases through ``openTEPES_run`` with a chosen backend: each case loads
its own source, builds, solves, and writes its own results (RFC §4.1). Mode B
(in-memory overlay) and Mode C (``openTEPES_ProblemSolvingResolve``) are separate.
"""
from __future__ import annotations

import glob
import json
import os

try:
    from .openTEPES import openTEPES_run
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES import openTEPES_run


def _status_dir(case):
    """Directory ``openTEPES_run`` writes this case's status JSON to (its own rule)."""
    if case.out_path:
        return case.out_path
    if case.case_name.endswith(".duckdb"):
        return os.path.dirname(os.path.abspath(os.path.join(case.dir_name, case.case_name)))
    return os.path.join(case.dir_name, case.case_name)


def _read_status(case):
    """Return the case's ``openTEPES_run_status_*.json``: a summary dict, not the model.

    The model cannot cross a worker process boundary, so every backend returns
    the JSON ``openTEPES_run`` already persists. CSV cases name it after the
    case; DuckDB inputs use the embedded name, hence the glob fallback.
    """
    out_dir = _status_dir(case)
    candidate = os.path.join(out_dir, f"openTEPES_run_status_{case.case_name}.json")
    if not os.path.exists(candidate):
        matches = sorted(glob.glob(os.path.join(out_dir, "openTEPES_run_status_*.json")),
                         key=os.path.getmtime)
        candidate = matches[-1] if matches else None
    if candidate and os.path.exists(candidate):
        with open(candidate) as handle:
            return json.load(handle)
    return {"case": case.case_name, "dir": case.dir_name, "status": "unknown",
            "error": "status JSON not found after run"}


def _run_one(case, solver_name, output_spec, gzip_patterns, pIndOutputResults, pIndLogConsole):
    """Solve one case; capture a raise as ``status="error"`` so the sweep survives it.

    Module-level so it pickles for the multiprocessing and joblib backends.
    """
    try:
        openTEPES_run(
            case.dir_name, case.case_name, solver_name,
            pIndOutputResults, pIndLogConsole,
            output_spec=output_spec, out_path=case.out_path, gzip_patterns=gzip_patterns,
        )
    except Exception as exc:
        return {
            "label":  case.label,
            "case":   case.case_name,
            "dir":    case.dir_name,
            "status": "error",
            "error":  f"{type(exc).__name__}: {exc}",
        }
    summary = _read_status(case)
    summary.setdefault("label", case.label)
    return summary


def run(cases, solver_name, *, mode="pre-build", backend="serial", n_workers=1,
        output_spec=None, gzip_patterns=None, pIndOutputResults=1, pIndLogConsole=0):
    """Run ``Case`` objects through ``openTEPES_run`` and return one summary per case.

    ``mode`` must be ``"pre-build"`` (Mode A); ``backend`` is ``"serial"`` (default,
    no extra dependency), ``"multiprocessing"`` (stdlib ``Pool``), or ``"joblib"``.
    ``output_spec``, ``gzip_patterns``, ``pIndOutputResults`` and ``pIndLogConsole``
    pass through to ``openTEPES_run``. Summaries keep input order on every backend;
    a failed case carries ``status="error"``.
    """
    if mode != "pre-build":
        raise NotImplementedError(
            f"openTEPES_Runner.run supports mode='pre-build' (Mode A) only; got mode={mode!r}. "
            "Mode B (in-memory overlay) is a later PR; Mode C (hot-swap) lives in "
            "openTEPES_ProblemSolvingResolve.resolve."
        )

    cases = list(cases)
    for case in cases:
        if case.overlay is not None:
            raise NotImplementedError(
                f"Case.overlay is reserved for Mode B (in-memory overlay) and is not supported "
                f"in Mode A; case label={case.label!r} set an overlay."
            )

    work = [(case, solver_name, output_spec, gzip_patterns, pIndOutputResults, pIndLogConsole)
            for case in cases]

    if backend == "serial":
        return [_run_one(*args) for args in work]

    if backend == "multiprocessing":
        import multiprocessing as mp
        with mp.Pool(processes=n_workers) as pool:
            return pool.starmap(_run_one, work)

    if backend == "joblib":
        try:
            from joblib import Parallel, delayed
        except ImportError as exc:
            raise ImportError("backend='joblib' requires joblib (pip install joblib).") from exc
        return Parallel(n_jobs=n_workers)(delayed(_run_one)(*args) for args in work)

    raise ValueError(f"unknown backend {backend!r}; expected 'serial', 'multiprocessing', or 'joblib'.")
