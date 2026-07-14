"""The solver thread count can be capped, and is unchanged when it is not.

The fallback is the test that matters: with nothing set, or with a value that is not a positive
integer, ``_threads()`` must return what it always did, so existing runs do not move.
"""
import psutil
import pytest

from openTEPES.openTEPES_Main import parser
from openTEPES.openTEPES_ProblemSolvingTuning import _threads


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
