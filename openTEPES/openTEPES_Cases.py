"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 17, 2026

openTEPES.openTEPES_Cases — one unit of work for the sweep runner.

A ``Case`` names one input source (a CSV directory or a ``.duckdb`` file, as
``openTEPES_run`` accepts) and where it writes results. ``overlay`` is reserved
for the Mode B sweep and rejected by the Mode A runner.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    """One sweep entry.

    ``dir_name`` / ``case_name`` are the standard openTEPES pair (``case_name``
    may be a CSV directory or a ``.duckdb`` file). ``out_path`` redirects this
    case's results — cases sharing a ``(dir_name, case_name)`` need distinct
    ``out_path`` so writers do not collide. ``label`` (default ``case_name``)
    tags the summary. ``overlay`` is reserved for Mode B.
    """

    dir_name: str
    case_name: str
    out_path: str | None = None
    label: str | None = None
    overlay: dict | None = None

    def __post_init__(self):
        if self.label is None:
            object.__setattr__(self, "label", self.case_name)
