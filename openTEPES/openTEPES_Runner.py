"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 29, 2026

openTEPES.openTEPES_Runner — Mode A and Mode B sweep runner.

Run many cases through ``openTEPES_run`` with a chosen backend. Mode A (``mode="pre-build"``,
RFC §4.1): each case loads its own source, builds, solves, and writes its own results. Mode B
(``mode="in-memory"``, RFC §4.2): the baseline case is read once into RAM and every case re-uses
it through an ``InMemorySource`` plus an overlay, so the sweep pays the I/O once and only rebuilds
+ solves per worker (forked workers share the baseline frames copy-on-write). Mode C (post-build
hot-swap) lives in ``openTEPES_ProblemSolvingResolve``.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from contextlib import contextmanager

try:
    from .openTEPES import openTEPES_run
    from .openTEPES_ResultAggregate import aggregate
    from .openTEPES_ProblemSolvingTuning import _threads
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES import openTEPES_run
    from openTEPES.openTEPES_ResultAggregate import aggregate
    from openTEPES.openTEPES_ProblemSolvingTuning import _threads


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


def _run_one(case, solver_name, output_spec, gzip_patterns, pIndOutputResults, pIndLogConsole, output_format):
    """Solve one case; capture a raise as ``status="error"`` so the sweep survives it.

    Module-level so it pickles for the multiprocessing and joblib backends.
    """
    try:
        openTEPES_run(
            case.dir_name, case.case_name, solver_name,
            pIndOutputResults, pIndLogConsole,
            output_spec=output_spec, out_path=case.out_path, gzip_patterns=gzip_patterns,
            output_format=output_format,
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


def _run_one_in_memory(case, baseline, solver_name, output_spec, gzip_patterns,
                       pIndOutputResults, pIndLogConsole, output_format):
    """Mode B worker: build from the shared in-memory baseline plus this case's overlay, then solve.

    ``baseline`` is an ``InMemorySource`` materialised once by the master; ``with_overlay`` shares its
    frames, so a forked worker perturbs only a few tables and rebuilds — no CSV re-read. Module-level so
    it pickles for the multiprocessing and joblib backends.
    """
    try:
        source = baseline.with_overlay(case.overlay) if case.overlay else baseline
        openTEPES_run(
            case.dir_name, case.case_name, solver_name,
            pIndOutputResults, pIndLogConsole,
            output_spec=output_spec, out_path=case.out_path, gzip_patterns=gzip_patterns,
            output_format=output_format, input_source=source,
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


@contextmanager
def _worker_thread_budget(backend, n_workers):
    """Give each worker its slice of the thread budget for the duration of the sweep.

    Workers call ``_threads()`` in their own process, so each would otherwise take the full default
    and the sweep would ask for ``n_workers`` machines. A count the user set is left alone.
    """
    chosen = os.environ.get("OTEPES_THREADS", "").strip()
    if backend == "serial" or n_workers <= 1 or chosen:
        yield
        return
    previous = os.environ.get("OTEPES_THREADS")
    os.environ["OTEPES_THREADS"] = str(max(1, _threads() // n_workers))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("OTEPES_THREADS", None)
        else:
            os.environ["OTEPES_THREADS"] = previous


def _run_in_memory(cases, solver_name, *, backend, n_workers, output_spec, gzip_patterns,
                   pIndOutputResults, pIndLogConsole, output_format):
    """Mode B dispatch: read each distinct baseline once, then run every case from it. Returns one summary per case."""
    try:
        from .openTEPES_InputSource import open_source
        from .openTEPES_InMemorySource import InMemorySource
    except ImportError:
        from openTEPES.openTEPES_InputSource import open_source
        from openTEPES.openTEPES_InMemorySource import InMemorySource

    for case in cases:
        if not case.out_path:
            raise ValueError(
                f"Mode B (in-memory) needs a distinct out_path per case so results do not collide on the shared "
                f"baseline directory; case label={case.label!r} has none."
            )

    # Read each distinct (dir_name, case_name) baseline once; cases re-use it (copy-on-write under fork).
    baselines = {}
    for case in cases:
        key = (case.dir_name, case.case_name)
        if key not in baselines:
            baselines[key] = InMemorySource.materialize(open_source(os.path.join(case.dir_name, case.case_name)))

    work = [(case, baselines[(case.dir_name, case.case_name)], solver_name, output_spec,
             gzip_patterns, pIndOutputResults, pIndLogConsole, output_format) for case in cases]

    if backend == "serial":
        return [_run_one_in_memory(*args) for args in work]
    if backend == "multiprocessing":
        import multiprocessing as mp
        # fork shares the baseline frames copy-on-write (the Mode B win); on Windows fall back to the default
        # start method, which pickles the baseline once per task — still no CSV re-read, just without COW.
        ctx = mp.get_context("fork") if sys.platform != "win32" else mp.get_context()
        with ctx.Pool(processes=n_workers) as pool:
            return pool.starmap(_run_one_in_memory, work)
    if backend == "joblib":
        try:
            from joblib import Parallel, delayed
        except ImportError as exc:
            raise ImportError("backend='joblib' requires joblib (pip install joblib).") from exc
        return Parallel(n_jobs=n_workers)(delayed(_run_one_in_memory)(*args) for args in work)
    raise ValueError(f"unknown backend {backend!r}; expected 'serial', 'multiprocessing', or 'joblib'.")


def run(cases, solver_name, *, mode="pre-build", backend="serial", n_workers=1,
        output_spec=None, gzip_patterns=None, pIndOutputResults=1, pIndLogConsole=0,
        output_format="csv", aggregate_to=None):
    """Run ``Case`` objects through ``openTEPES_run`` and return one summary per case.

    ``mode`` is ``"pre-build"`` (Mode A, each case reads its own source) or
    ``"in-memory"`` (Mode B, the baseline is read once and re-used through an
    overlay). ``backend`` is ``"serial"`` (default, no extra dependency),
    ``"multiprocessing"`` (stdlib ``Pool``), or ``"joblib"``. ``output_spec``,
    ``gzip_patterns``, ``pIndOutputResults`` and ``pIndLogConsole`` pass through to
    ``openTEPES_run``. Summaries keep input order on every backend; a failed case
    carries ``status="error"``.

    Mode A rejects ``Case.overlay``; Mode B uses it (a dict mapping a data-table
    stem to a number / callable / DataFrame, see ``InMemorySource``) and requires a
    distinct ``out_path`` per case.

    A parallel sweep splits the solver thread budget across its ``n_workers``, so they ask for one
    machine between them, not one each. ``--threads`` / ``OTEPES_THREADS`` overrides that.

    ``output_format`` (``"csv"`` / ``"duckdb"`` / ``"both"``) selects each case's
    result format (see ``openTEPES_run``); each worker writes its own per-case
    DuckDB so a parallel sweep stays single-writer-safe. ``aggregate_to``, if set
    to a directory, merges the solved cases after the sweep into one long table per
    result type (``oT_Sweep_*``) tagged by case label, via
    ``openTEPES_ResultAggregate.aggregate``; failed cases are skipped.
    """
    cases = list(cases)

    with _worker_thread_budget(backend, n_workers):
        if mode == "in-memory":
            records = _run_in_memory(
                cases, solver_name, backend=backend, n_workers=n_workers, output_spec=output_spec,
                gzip_patterns=gzip_patterns, pIndOutputResults=pIndOutputResults,
                pIndLogConsole=pIndLogConsole, output_format=output_format,
            )
        elif mode == "pre-build":
            for case in cases:
                if case.overlay is not None:
                    raise NotImplementedError(
                        f"Case.overlay is for Mode B (in-memory overlay) and is not supported in Mode A "
                        f"(mode='pre-build'); case label={case.label!r} set an overlay. Use mode='in-memory'."
                    )

            work = [(case, solver_name, output_spec, gzip_patterns, pIndOutputResults, pIndLogConsole, output_format)
                    for case in cases]

            if backend == "serial":
                records = [_run_one(*args) for args in work]
            elif backend == "multiprocessing":
                import multiprocessing as mp
                with mp.Pool(processes=n_workers) as pool:
                    records = pool.starmap(_run_one, work)
            elif backend == "joblib":
                try:
                    from joblib import Parallel, delayed
                except ImportError as exc:
                    raise ImportError("backend='joblib' requires joblib (pip install joblib).") from exc
                records = Parallel(n_jobs=n_workers)(delayed(_run_one)(*args) for args in work)
            else:
                raise ValueError(f"unknown backend {backend!r}; expected 'serial', 'multiprocessing', or 'joblib'.")
        else:
            raise ValueError(
                f"unknown mode {mode!r}; expected 'pre-build' (Mode A) or 'in-memory' (Mode B). "
                "Mode C (post-build hot-swap) lives in openTEPES_ProblemSolvingResolve.resolve."
            )

    if aggregate_to:
        solved = [(case, rec) for case, rec in zip(cases, records) if rec.get("status") != "error"]
        if solved:
            sources = [_status_dir(case) for case, _ in solved]
            labels  = [rec.get("label") or case.label or case.case_name for case, rec in solved]
            aggregate(sources, out_path=aggregate_to, to=output_format, labels=labels)

    return records
