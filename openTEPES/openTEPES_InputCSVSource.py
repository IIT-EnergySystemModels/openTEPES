"""
openTEPES.openTEPES_InputCSVSource — file-system CSV backend.

Preserves today's behaviour bit-for-bit: every read uses ``pd.read_csv`` with ``encoding="utf-8-sig"`` so the
optional BOM emitted by Excel is stripped silently.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_InputSchema import WIDE_MULTILEVEL_TO_LONG, _SPEC_BY_CSV_STEM
    from .openTEPES_InputSource import InputSource, _apply_index
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSchema import WIDE_MULTILEVEL_TO_LONG, _SPEC_BY_CSV_STEM
    from openTEPES.openTEPES_InputSource import InputSource, _apply_index


class CSVSource(InputSource):
    def __init__(self, case_dir: Path) -> None:
        self.case_dir = Path(case_dir)
        cn = self._detect_case_name(self.case_dir)
        if cn is None:
            raise ValueError(f"{self.case_dir}: cannot detect case name (no oT_Data_Parameter_*.csv found)")
        self.case_name = cn

    # DirName/CaseName the rest of openTEPES expects.
    @property
    def dir_name(self) -> str:
        return str(self.case_dir.parent)

    @staticmethod
    def _detect_case_name(case_dir: Path) -> str | None:
        for p in case_dir.glob("oT_Data_Parameter_*.csv"):
            return p.stem[len("oT_Data_Parameter_"):]
        return None

    def list_data_stems(self) -> set[str]:
        stems: set[str] = set()
        suffix = f"_{self.case_name}.csv"
        for p in self.case_dir.glob("oT_Data_*.csv"):
            name = p.name
            if name.endswith(suffix):
                # 'oT_Data_<stem>_<case>.csv'
                inner = name[len("oT_Data_"):-len(suffix)]
                if inner:
                    stems.add(inner)
        return stems

    def list_dict_stems(self) -> set[str]:
        stems: set[str] = set()
        suffix = f"_{self.case_name}.csv"
        for p in self.case_dir.glob("oT_Dict_*.csv"):
            name = p.name
            if name.endswith(suffix):
                # 'oT_Dict_<stem>_<case>.csv'
                inner = name[len("oT_Dict_"):-len(suffix)]
                if inner:
                    stems.add(inner)
        return stems

    def read_dict(self, stem: str) -> pd.DataFrame:
        path = self.case_dir / f"oT_Dict_{stem}_{self.case_name}.csv"
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, encoding="utf-8-sig")

    def read_data(self, stem: str, header_levels: list[int] | None = None) -> pd.DataFrame:
        path = self.case_dir / f"oT_Data_{stem}_{self.case_name}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        # Multi-level header tables: derive level count from the spec if the caller didn't pass header_levels, so the
        # source is self-sufficient.
        spec = _SPEC_BY_CSV_STEM.get(f"oT_Data_{stem}")
        if header_levels is None and spec and spec[1] == WIDE_MULTILEVEL_TO_LONG:
            header_levels = list(range(len(spec[2]["entity_cols"])))
        if header_levels:
            return pd.read_csv(path, encoding="utf-8-sig", header=header_levels, index_col=[0, 1, 2])
        df = pd.read_csv(path, encoding="utf-8-sig")
        # Option / Parameter are single-row, leave as-is (no index).
        if stem in ("Option", "Parameter"):
            return df
        return _apply_index(df, stem)
