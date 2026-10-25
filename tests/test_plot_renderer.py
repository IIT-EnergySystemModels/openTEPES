"""Writing the network maps must not import kaleido.

The maps are written with ``fig.write_html``, which needs no image export. Setting ``pio.renderers.default``
loads plotly's renderers, which import kaleido, then choreographer, then logistro. logistro reads the command
line when it is imported, with abbreviations allowed, so the ``--log`` option of ``openTEPES_Main`` matches its
own ``--logistro-*`` options and it ends the run with exit code 2. The network map of every case was lost that
way, and for a case with hydrogen or heat the run ended before the network, marginal and economic results.

Each case is solved in a fresh interpreter, because an earlier import of kaleido in the test session would hide
the problem. kaleido, choreographer and logistro are blocked there, so the test does not depend on whether
kaleido is installed.
"""
import os
import subprocess
import sys
import textwrap

import pytest

import openTEPES

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
# The child must import the same openTEPES as this session, not whichever one is installed.
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(openTEPES.__file__)))

SCRIPT = textwrap.dedent("""
    import importlib.abc
    import sys

    class _Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in ("kaleido", "choreographer", "logistro"):
                sys.stderr.write(f"blocked import of {{name}}\\n")
                raise SystemExit(3)
            return None

    sys.meta_path.insert(0, _Block())
    sys.argv = ["openTEPES_Main.py", "--log", "No"]
    sys.path.insert(0, {tests!r})

    from case_week import week_of_case
    from openTEPES.openTEPES import openTEPES_run

    case_dir, run_kwargs = week_of_case({case!r}, {dest!r})
    openTEPES_run(**run_kwargs, output_spec={{"h2": True, "heat": True, "map": True}})
""")


@pytest.mark.solve
@pytest.mark.parametrize("case, maps", [
    ("9n",      ["MapNetwork"]),
    ("sSEP",    ["MapNetworkH2", "MapNetwork"]),
    ("9n_heat", ["MapNetworkHeat", "MapNetwork"]),
])
def test_maps_written_without_kaleido(tmp_path, case, maps):
    script = SCRIPT.format(tests=TESTS_DIR, case=case, dest=str(tmp_path))
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [PACKAGE_ROOT, os.environ.get("PYTHONPATH")])))
    run = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=900, env=env)
    assert run.returncode == 0, run.stderr[-2000:]
    for name in maps:
        assert os.path.isfile(os.path.join(tmp_path, case, f"oT_Plot_{name}_{case}.html")), name
