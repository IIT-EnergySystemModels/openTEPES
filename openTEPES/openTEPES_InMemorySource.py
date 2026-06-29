"""
openTEPES.openTEPES_InMemorySource — in-memory input backend for the Mode B sweep (RFC §4.2).

A ``CSVSource`` or ``DuckDBSource`` reads the case from disk on every build. Mode B reads the baseline once into RAM and
re-uses it: ``InMemorySource.materialize(open_source(path))`` captures every dimension dict and data table as a DataFrame,
and ``baseline.with_overlay({...})`` returns a cheap clone that perturbs a few tables. Forked workers share the baseline
frames copy-on-write, so a parameter sweep pays the I/O once and only rebuilds + solves per worker.

The overlay maps a data-table stem (e.g. ``"Demand"``) to one of:

  * a number              → multiply every numeric value of that table by it (a uniform scale, e.g. ``1.10`` for +10 %),
  * a callable ``df->df`` → replace the table with the function applied to a copy of the baseline frame,
  * a DataFrame           → replace the table outright (must already be in the wide, indexed shape ``read_data`` returns).

Overlays target ``oT_Data_*`` tables (the wide frames the model reads); dimension dicts are passed through unchanged.
"""
from __future__ import annotations

import pandas as pd

try:
    from .openTEPES_InputSource import InputSource
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSource import InputSource


def _apply_overlay(df: pd.DataFrame, transform) -> pd.DataFrame:
    """Return ``df`` perturbed by ``transform`` (number, callable, or replacement DataFrame). ``df`` is a private copy."""
    if isinstance(transform, pd.DataFrame):
        return transform
    if callable(transform):
        return transform(df)
    if isinstance(transform, (int, float)) and not isinstance(transform, bool):
        num_cols = df.select_dtypes(include="number").columns
        df[num_cols] = df[num_cols] * transform
        return df
    raise TypeError(
        f"overlay value must be a number, a callable df->df, or a DataFrame; got {type(transform).__name__}"
    )


class InMemorySource(InputSource):
    """Baseline case held in RAM, optionally perturbed by an overlay. Built via ``materialize`` / ``with_overlay``."""

    def __init__(self, case_name: str, dir_name: str, dict_frames: dict, data_frames: dict, overlay: dict | None = None):
        self.case_name = case_name
        self.dir_name = dir_name           # anchors openTEPES_run's log/output filename conventions
        self._dict_frames = dict_frames    # stem -> DataFrame (shared, treated read-only)
        self._data_frames = data_frames    # stem -> DataFrame (shared, treated read-only)
        self._overlay = overlay or {}

    @classmethod
    def materialize(cls, source: InputSource) -> "InMemorySource":
        """Read every dict and data table from ``source`` once and hold them in memory.

        ``read_data`` is called without ``header_levels`` so each backend self-derives the multi-level-header shape
        (``CSVSource`` and ``DuckDBSource`` both do this from the schema), giving the same frame ``InputData`` would read.
        """
        data_frames: dict[str, pd.DataFrame] = {}
        for stem in source.list_data_stems():
            try:
                data_frames[stem] = source.read_data(stem)
            except FileNotFoundError:
                continue
        dict_frames = {stem: source.read_dict(stem) for stem in source.list_dict_stems()}
        dir_name = getattr(source, "dir_name", "")
        return cls(source.case_name, dir_name, dict_frames, data_frames)

    def with_overlay(self, overlay: dict | None) -> "InMemorySource":
        """Return a clone sharing the baseline frames but reading ``overlay``-perturbed data tables."""
        return InMemorySource(self.case_name, self.dir_name, self._dict_frames, self._data_frames, overlay)

    def list_data_stems(self) -> set[str]:
        return set(self._data_frames)

    def list_dict_stems(self) -> set[str]:
        return set(self._dict_frames)

    def read_dict(self, stem: str) -> pd.DataFrame:
        df = self._dict_frames.get(stem)
        return df.copy() if df is not None else pd.DataFrame()

    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        if stem not in self._data_frames:
            raise FileNotFoundError(f"oT_Data_{stem}: not in the in-memory source")
        df = self._data_frames[stem].copy()
        if stem in self._overlay:
            df = _apply_overlay(df, self._overlay[stem])
        return df
