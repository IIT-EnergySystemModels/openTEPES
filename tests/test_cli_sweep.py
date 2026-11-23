"""Command-line options for the result format and for a sweep.

``openTEPES_Main --output-format`` passes the result format to ``openTEPES_run``. ``python -m openTEPES.openTEPES_Runner``
solves several cases (Mode A): these tests replace the solve with a stand-in to check the cases it builds and its exit
code. ``test_run.py`` solves the trimmed 9n case from the command line, next to the other sweep tests.
"""
import os

import pytest

from openTEPES import openTEPES_Runner
from openTEPES.openTEPES_Main import parser


def test_output_format_defaults_to_csv_and_accepts_only_the_three_formats():
    assert parser.parse_args([]).output_format == "csv"
    assert parser.parse_args(["--output-format", "duckdb"]).output_format == "duckdb"
    with pytest.raises(SystemExit):
        parser.parse_args(["--output-format", "parquet"])


def test_the_sweep_command_builds_one_case_per_name_and_fails_if_any_case_fails(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_run(cases, solver_name, **kwargs):
        seen.update(cases=cases, solver=solver_name, **kwargs)
        return [{"label": "a", "status": "optimal", "total_cost_meur": 12.5, "total_seconds": 3.0},
                {"label": "b", "status": "error", "error": "ValueError: no case"}]

    monkeypatch.setattr(openTEPES_Runner, "run", fake_run)
    code = openTEPES_Runner.main(["a", "b.duckdb", "--dir", "cases", "--out", str(tmp_path), "--solver", "gurobi",
                                  "--backend", "multiprocessing", "--workers", "2", "--output-format", "duckdb",
                                  "--aggregate-to", str(tmp_path / "sweep")])

    assert code == 1
    assert [(c.dir_name, c.case_name, c.label, c.out_path) for c in seen["cases"]] == [
        ("cases", "a", "a", os.path.join(str(tmp_path), "a")),
        ("cases", "b.duckdb", "b", os.path.join(str(tmp_path), "b")),
    ]
    assert seen["solver"] == "gurobi"
    assert (seen["backend"], seen["n_workers"], seen["output_format"]) == ("multiprocessing", 2, "duckdb")
    assert seen["aggregate_to"] == str(tmp_path / "sweep")
    assert capsys.readouterr().out.splitlines() == ["a: optimal, 12.5 MEUR, 3.0 s", "b: error, ValueError: no case"]


def test_the_sweep_command_returns_0_when_every_case_solves(monkeypatch):
    monkeypatch.setattr(openTEPES_Runner, "run", lambda cases, solver_name, **kw: [{"label": "a", "status": "optimal"}])
    assert openTEPES_Runner.main(["a"]) == 0

