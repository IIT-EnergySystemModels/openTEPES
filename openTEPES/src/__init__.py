"""
openTEPES.src — split-out source modules for the layered-architecture restructure.

Rather than one folder per RFC layer, the split modules live together in this single ``src`` package and the
layer is encoded in the file name: ``openTEPES_IO_*`` for the I/O layer (Layer 2, pure pandas, no Pyomo) and
``openTEPES_Solver_*`` for the solver layer (Layer 5). File basenames keep the ``openTEPES_<Layer>_<Concern>``
convention of the rest of the package so the import path is self-describing without a nested folder tree.

I/O layer (``openTEPES_IO_*``)
------------------------------
  * ``openTEPES_IO_Schema``     — ``TABLE_SPECS`` catalogue + transform-kind constants + ``DEFAULT_IDX_COLS``.
                                  Single source of truth used by every backend, the NESP-side ingest migrator,
                                  and the case-management CLI. No Pyomo, no I/O.
  * ``openTEPES_IO_Source``     — ``InputSource`` ABC + ``open_source()`` factory + post-read shape helpers
                                  (``_apply_index``, ``df_to_set_values``).
  * ``openTEPES_IO_CSVSource``  — file-system CSV backend.
  * ``openTEPES_IO_DuckDBSource`` — in-process ``.duckdb`` backend. ``duckdb`` is an optional dependency, lazily
                                  imported by ``open_source()`` only when a ``.duckdb`` path is opened.

Solver layer (``openTEPES_Solver_*``)
-------------------------------------
  Single-solve primitives (5.a): ``openTEPES_Solver_Persistent`` (``appsi_gurobi`` / ``gurobi_persistent``
  lifecycle), ``openTEPES_Solver_Tuning`` (per-solver option presets), ``openTEPES_Solver_DualExtraction``
  (fix-integers + investments → re-solve as LP → collect duals into ``mTEPES.pDuals``).
  Orchestration drivers (5.b): ``openTEPES_Solver_ProblemSolving`` (per-stage solve orchestrator that composes
  the three primitives) and ``openTEPES_Solver_Benders.lshaped`` (classical L-shaped decomposition for
  transmission expansion).

Every public name is re-exported here so consumers import from a single surface,
e.g. ``from openTEPES.src import open_source, ProblemSolving, lshaped``.
"""
from __future__ import annotations

from .openTEPES_IO_Schema import (
    PASSTHROUGH,
    WIDE_TO_LONG,
    WIDE_MULTILEVEL_TO_LONG,
    UNPIVOT_SINGLE_ROW,
    TABLE_SPECS,
    DEFAULT_IDX_COLS,
    _SPEC_BY_CSV_STEM,
)
from .openTEPES_IO_Source import InputSource, open_source, _apply_index, df_to_set_values
from .openTEPES_IO_CSVSource import CSVSource
from .openTEPES_IO_DuckDBSource import DuckDBSource
from .openTEPES_Solver_Benders import lshaped
from .openTEPES_Solver_ProblemSolving import ProblemSolving

__all__ = [
    # I/O layer
    "PASSTHROUGH",
    "WIDE_TO_LONG",
    "WIDE_MULTILEVEL_TO_LONG",
    "UNPIVOT_SINGLE_ROW",
    "TABLE_SPECS",
    "DEFAULT_IDX_COLS",
    "InputSource",
    "open_source",
    "df_to_set_values",
    "CSVSource",
    "DuckDBSource",
    # Solver layer
    "lshaped",
    "ProblemSolving",
    # Leading-underscore names re-exported because external tooling (NESP migrator, case CLI) imports them today.
    "_apply_index",
    "_SPEC_BY_CSV_STEM",
]
