"""Each package module must import cleanly when run as a script.

When a file is run directly (VS Code "Run Python File", ``python path/to/file.py``) it executes as ``__main__``
with an empty ``__package__``, so a top-level ``from .openTEPES_X import ...`` relative import fails. The modules
that import sibling modules at load time guard against this with a ``try``/``except ImportError`` fallback that
puts the repository root on ``sys.path`` and retries the import absolutely.

Nothing else in the test suite exercises that fallback: a normal ``import openTEPES`` only ever takes the
relative-import path. This test runs every ``openTEPES_*.py`` module as ``__main__`` (via ``runpy``) so the
fallback path is checked on every CI run, catching a broken guard, a missing import, or a circular import before
a user hits it in an editor. No model is solved, so it runs in the fast (non-solve) CI job.

``openTEPES_Main.py`` is excluded because it has an active ``if __name__ == "__main__"`` block that would launch
the command-line interface rather than just import.
"""
import runpy
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parent.parent / "openTEPES"

# Modules with an active __main__ block that does real work (not just imports) — running them as __main__ would
# execute that work, not test the import guard.
EXCLUDE = {"openTEPES_Main.py"}

MODULES = sorted(p.name for p in PKG_DIR.glob("openTEPES_*.py") if p.name not in EXCLUDE)


def test_modules_discovered():
    """Guard against the glob silently matching nothing (e.g. a path change)."""
    assert MODULES, f"no openTEPES_*.py modules found under {PKG_DIR}"


@pytest.mark.parametrize("module", MODULES)
def test_module_runs_as_main(module):
    """Running the module as a script must not raise (the relative-import guard's fallback works)."""
    runpy.run_path(str(PKG_DIR / module), run_name="__main__")
