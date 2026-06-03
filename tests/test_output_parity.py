"""Tests for the result-file comparison tool (_output_parity_test).

These tests build small fake ``oT_Result_*.csv`` files and check that the
snapshot/compare logic behaves correctly. No model is solved, so they run in
milliseconds. The real use of the tool (snapshot the results before and after
a change to the output code and check they are identical) is described in the
tool's own docstring.
"""
import numpy as np
import pandas as pd

from openTEPES._output_parity_test import snapshot, compare_snapshots


def _write_case(dir_path, tables):
    """Write {table_name: DataFrame} as oT_Result_<name>_<case>.csv files."""
    dir_path.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(dir_path / f"oT_Result_{name}_TESTCASE.csv", index=False)


def _sample_tables():
    return {
        "GenerationInvestment": pd.DataFrame(
            {"Period": ["p1", "p1"], "Generator": ["G1", "G2"], "MW": [100.0, 250.5]}
        ),
        "CostSummary": pd.DataFrame({"Item": ["total"], "MEUR": [252.201329983352]}),
    }


def test_identical_snapshots_have_empty_diff(tmp_path):
    _write_case(tmp_path / "A", _sample_tables())
    _write_case(tmp_path / "B", _sample_tables())
    a = snapshot(str(tmp_path / "A"))
    b = snapshot(str(tmp_path / "B"))
    assert a["n_tables"] == 2
    assert compare_snapshots(a, b) == []


def test_numeric_difference_is_detected(tmp_path):
    _write_case(tmp_path / "A", _sample_tables())
    perturbed = _sample_tables()
    perturbed["CostSummary"].loc[0, "MEUR"] += 1.0  # 1 MEUR off
    _write_case(tmp_path / "B", perturbed)
    diffs = compare_snapshots(snapshot(str(tmp_path / "A")), snapshot(str(tmp_path / "B")))
    assert any("CostSummary" in d for d in diffs)


def test_tolerance_absorbs_float_repr_noise(tmp_path):
    _write_case(tmp_path / "A", _sample_tables())
    noisy = _sample_tables()
    noisy["CostSummary"].loc[0, "MEUR"] += 1e-12  # below atol/rtol
    _write_case(tmp_path / "B", noisy)
    assert compare_snapshots(snapshot(str(tmp_path / "A")), snapshot(str(tmp_path / "B"))) == []


def test_missing_table_is_reported(tmp_path):
    _write_case(tmp_path / "A", _sample_tables())
    one = {"CostSummary": _sample_tables()["CostSummary"]}
    _write_case(tmp_path / "B", one)
    diffs = compare_snapshots(snapshot(str(tmp_path / "A")), snapshot(str(tmp_path / "B")))
    assert any("only-in-A" in d and "GenerationInvestment" in d for d in diffs)


def test_categorical_difference_is_detected(tmp_path):
    _write_case(tmp_path / "A", _sample_tables())
    relabel = _sample_tables()
    relabel["GenerationInvestment"].loc[1, "Generator"] = "G9"  # label change, same shape
    _write_case(tmp_path / "B", relabel)
    diffs = compare_snapshots(snapshot(str(tmp_path / "A")), snapshot(str(tmp_path / "B")))
    assert any("GenerationInvestment" in d for d in diffs)


def test_case_suffix_with_underscores_is_normalised(tmp_path):
    """Case names containing underscores (SE2035_EP_G0) are stripped correctly,
    so snapshots of the same case under different case names still match."""
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    df = pd.DataFrame({"x": [1.0, 2.0]})
    # Two tables per dir so the common-trailing-token inference can fire.
    for tbl in ("Foo", "BarResults"):
        df.to_csv(tmp_path / "A" / f"oT_Result_{tbl}_9n.csv", index=False)
        df.to_csv(tmp_path / "B" / f"oT_Result_{tbl}_SE2035_EP_G0.csv", index=False)
    a, b = snapshot(str(tmp_path / "A")), snapshot(str(tmp_path / "B"))
    assert set(a["tables"]) == {"Foo", "BarResults"} == set(b["tables"])
    assert compare_snapshots(a, b) == []
