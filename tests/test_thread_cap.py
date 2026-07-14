"""The solver thread count can be capped, and is unchanged when it is not.

The fallback is the test that matters: with nothing set, or with a value that is not a positive
integer, ``_threads()`` must return what it always did, so existing runs do not move.
"""
import os

import psutil
import pytest

from openTEPES.openTEPES_Main import parser
from openTEPES.openTEPES_ProblemSolvingTuning import _threads
from openTEPES.openTEPES_Runner import _worker_thread_budget


def _default() -> int:
    return int((psutil.cpu_count(logical=True) + psutil.cpu_count(logical=False)) / 2)


def test_default_when_nothing_is_set(monkeypatch):
    monkeypatch.delenv("OTEPES_THREADS", raising=False)
    assert _threads() == _default()


def test_environment_variable_caps_the_count(monkeypatch):
    monkeypatch.setenv("OTEPES_THREADS", "3")
    assert _threads() == 3


@pytest.mark.parametrize("value", ["", "junk", "0", "-2", "2.5"])
def test_unusable_value_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("OTEPES_THREADS", value)
    assert _threads() == _default()


def test_flag_is_parsed():
    assert parser.parse_args(["--threads", "4"]).threads == 4


@pytest.mark.parametrize("value", ["0", "-1", "junk"])
def test_flag_rejects_a_count_below_one(value):
    with pytest.raises(SystemExit):
        parser.parse_args(["--threads", value])


def test_flag_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv("OTEPES_THREADS", "9")
    args = parser.parse_args(["--threads", "2"])
    monkeypatch.setenv("OTEPES_THREADS", str(args.threads))   # what openTEPES_Main.main() does
    assert _threads() == 2


def test_a_parallel_sweep_splits_the_budget_and_restores_it(monkeypatch):
    monkeypatch.delenv("OTEPES_THREADS", raising=False)
    with _worker_thread_budget("multiprocessing", 4):
        assert _threads() == max(1, _default() // 4)
    assert "OTEPES_THREADS" not in os.environ


def test_a_count_the_user_set_survives_the_sweep(monkeypatch):
    monkeypatch.setenv("OTEPES_THREADS", "3")
    with _worker_thread_budget("multiprocessing", 4):
        assert _threads() == 3


@pytest.mark.parametrize("backend,n_workers", [("serial", 1), ("serial", 4), ("multiprocessing", 1)])
def test_one_case_at_a_time_keeps_the_default(monkeypatch, backend, n_workers):
    monkeypatch.delenv("OTEPES_THREADS", raising=False)
    with _worker_thread_budget(backend, n_workers):
        assert _threads() == _default()
