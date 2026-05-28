"""
openTEPES.oT_IO — Layer 2 of the layered-architecture restructure (pure pandas, no Pyomo).

Three concerns split into four modules:

  * ``Schema``        — ``TABLE_SPECS`` catalogue + transform-kind constants + ``DEFAULT_IDX_COLS``. Single source of
                        truth used by every backend, by the NESP-side ``ingest_csv_to_duckdb`` migrator, and by the
                        case-management CLI. No Pyomo, no I/O.
  * ``Source``        — ``InputSource`` ABC + ``open_source()`` factory + post-read shape helpers (``_apply_index``,
                        ``df_to_set_values``).
  * ``CSVSource``     — file-system CSV backend.
  * ``DuckDBSource``  — in-process ``.duckdb`` backend. ``duckdb`` is an optional dependency, lazily imported by
                        ``open_source()`` only when a ``.duckdb`` path is opened.

Subfolder per RFC layer (``Docs/architecture/opentepes_architecture_proposal.md`` §3). File names use CamelCase to
mirror the existing ``openTEPES_<Concern>.py`` style; the subfolder already disambiguates so the package prefix is
dropped inside the layer.

Back-compat: the top-level ``openTEPES.openTEPES_InputSource`` import path keeps working via a thin shim module that
re-exports every public name from this subpackage. External tooling does not need to change.
"""
from __future__ import annotations

from .Schema import (
    PASSTHROUGH,
    WIDE_TO_LONG,
    WIDE_MULTILEVEL_TO_LONG,
    UNPIVOT_SINGLE_ROW,
    TABLE_SPECS,
    DEFAULT_IDX_COLS,
    _SPEC_BY_CSV_STEM,
)
from .Source import InputSource, open_source, _apply_index, df_to_set_values
from .CSVSource import CSVSource
from .DuckDBSource import DuckDBSource

__all__ = [
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
    # Leading-underscore names re-exported because external tooling (NESP migrator, case CLI) imports them today.
    "_apply_index",
    "_SPEC_BY_CSV_STEM",
]
