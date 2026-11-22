"""The version and its date are set once, in openTEPES/__init__.py, and every other place reads them from there."""
import pathlib
import runpy

import openTEPES
from openTEPES.openTEPES import BANNER

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_banner_carries_the_version_and_its_date():
    assert f"Version {openTEPES.__version__} - {openTEPES.__version_date__}" in BANNER


def test_the_version_is_typed_only_in_init():
    files = [*(ROOT / "openTEPES").glob("*.py"), ROOT / "doc" / "md" / "conf.py"]
    typed = [f.name for f in files if f.name != "__init__.py" and openTEPES.__version__ in f.read_text(encoding="utf-8")]
    assert typed == []


def test_the_documentation_reads_the_same_version():
    conf = runpy.run_path(str(ROOT / "doc" / "md" / "conf.py"))
    assert conf["version"] == f"version {openTEPES.__version__}"
    assert conf["html_title"] == conf["version"]
