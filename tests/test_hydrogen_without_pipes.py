"""A hydrogen system with no pipes must still report itself.

Hydrogen can exist without a network: electrolysers, reformers, caverns and a balance at every
node, with each node supplied locally. The results code assumed otherwise in two places, and the
combination was quiet in the worst way. The writer was gated on the pipe set being non-empty, so
no hydrogen output was produced at all; and inside it, the pipe flow tables name six index levels
on a series built from an empty set, which raises rather than writing an empty table.

Together that meant a case with 93 GW of electrolysers and 33 GW of reformers wrote no hydrogen
results, and the run reported an error only after every other table had been written.
"""
import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "openTEPES"


def test_h2_output_is_gated_on_hydrogen_not_on_pipes():
    src = (PKG / "openTEPES.py").read_text()
    row = next(l for l in src.splitlines() if "NetworkH2OperationResults," in l and "lambda" in l)
    gate = row[row.index("lambda"):]
    assert "pIndHydrogen" in gate, "the gate must require the hydrogen carrier"
    assert re.search(r"m\.el|m\.sr|m\.hs", gate), (
        "the gate must let a pipeless hydrogen system through; keying it on m.pa alone writes "
        "no hydrogen results for a system that has sources and demand but no network"
    )


def test_pipe_only_output_blocks_are_guarded():
    src = (PKG / "openTEPES_OutputResultsHydrogen.py").read_text()
    for marker in ("oT_Result_NetworkFlowH2PerNode_", "oT_Result_NetworkH2Utilization_",
                   "oT_Plot_MapNetworkH2_"):
        i = src.index(marker)
        before = src[:i]
        assert "if mTEPES.pa:" in before or "if not mTEPES.pa:" in before, (
            f"{marker} is built from the pipe set and must sit behind a check that pipes exist"
        )


def test_node_guards_include_the_source_set():
    """Every node filter must count reformers, or a reformer-only node vanishes from the report."""
    src = (PKG / "openTEPES_OutputResultsHydrogen.py").read_text()
    guards = re.findall(r"len\(l2n\[nd\]\)(?:\s*\+\s*len\(\w+\[nd\]\))+", src)
    assert guards, "expected at least one node guard"
    for g in guards:
        assert "r2n" in g, f"guard omits the hydrogen source set: {g}"
