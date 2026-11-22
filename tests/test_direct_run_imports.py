"""A module run directly, without its package, imports the other modules from the package, so no module is loaded twice."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

CODE = """
import glob, os, runpy, sys
loose = {}
for f in sorted(glob.glob('openTEPES/openTEPES*.py')):
    before = set(sys.modules)
    runpy.run_path(f, run_name='__direct__')
    new = sorted(k for k in set(sys.modules) - before if k.startswith('openTEPES_'))
    if new:
        loose[os.path.basename(f)] = new
print(loose)
"""


def test_no_module_is_imported_outside_the_package():
    out = subprocess.run([sys.executable, "-c", CODE], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    assert out == "{}"
