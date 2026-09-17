"""The hydrogen cost terms have to be annualised, and by the weight times the hours.

Every cost in the objective is written per load level and scaled up to a year. eTotalRH2Cost and
eTotalH2SrcCost were the two terms with no scaling at all, so unserved hydrogen, and hydrogen
bought from a source, were priced at a fifty-second of their real cost on a week weighted by 52. Nothing about that
looks wrong from outside. The model still solves and the balance still holds; what changes is the
trade-off, because an electrolyser is priced against a full-weight investment while the shortfall
it would avoid is discounted.

The scaling is pLoadLevelDuration, which is pLoadLevelWeight times pDuration. The hydrogen
variables are rates in tH2/h, the same way vENS is a power, so the cost needs the hours as well as
the weight. Scaling by the weight alone would charge one hour of shortfall on a load level that
lasts four.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "openTEPES" / "openTEPES_ModelFormulationHydrogen.py"


def _body(name, code_only=False):
    src = SRC.read_text()
    i = src.index(f"def {name}(")
    body = src[i:src.index("setattr", i)]
    if code_only:  # the comments discuss the other parameter on purpose; test the code
        body = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    return body


def test_h2_reliability_cost_is_annualised():
    body = _body("eTotalRH2Cost")
    assert re.search(r"pLoadLevelDuration\[p,sc,n\]\(\)\s*\*\s*sum\(", body), (
        "eTotalRH2Cost must scale the whole sum by pLoadLevelDuration; without it unserved "
        "hydrogen is under-priced by the stage weight against every other cost"
    )


def test_h2_reliability_carries_the_hours():
    body = _body("eTotalRH2Cost", code_only=True)
    assert "pLoadLevelWeight" not in body, (
        "vH2NS is a rate in tH2/h, so the stage weight alone leaves out the hours of the load "
        "level and prices a four-hour shortfall as one hour"
    )


def test_electricity_term_does_use_the_duration():
    # the same shape on the electricity side: vENS is a power, so it needs the hours as well as the weight
    obj = (SRC.parent / "openTEPES_ModelFormulationObjective.py").read_text()
    i = obj.index("def eTotalRElecCost(")
    body = obj[i:obj.index("setattr", i)]
    assert "pLoadLevelDuration" in body, (
        "vENS is in MW, so the electricity reliability cost must carry pLoadLevelDuration"
    )


def test_balance_and_cost_cover_the_same_nodes():
    """A node the balance covers but the cost sum skips gets free unserved hydrogen.

    Both guards decide which nodes have a hydrogen balance at all. If eBalanceH2 builds a
    constraint at a node that eTotalRH2Cost leaves out of its sum, that node's vH2NS carries no
    price, and the cheapest way to meet its demand is to declare all of it unserved. The bug is
    silent: the model solves, the balance holds, and the demand simply disappears.
    """
    src = SRC.read_text()
    guards = re.findall(r"len\(l2n\[nd\]\)(?:\s*\+\s*len\(\w+\[nd\]\))+", src)
    assert len(guards) >= 2, "expected a guard on both eBalanceH2 and eTotalRH2Cost"
    sets = [frozenset(re.findall(r"len\((\w+)\[nd\]\)", g)) for g in guards]
    assert len(set(sets)) == 1, (
        f"the hydrogen node guards disagree: {[sorted(s) for s in sets]}; every set that can "
        f"supply or move hydrogen must appear in both"
    )


def test_h2_source_cost_is_annualised():
    body = _body("eTotalH2SrcCost")
    assert re.search(r"pLoadLevelDuration\[p,sc,n\]\(\)\s*\*\s*sum\(", body), (
        "eTotalH2SrcCost must scale the sum by pLoadLevelDuration; without it a reformed tonne "
        "costs a stage weight less than the electricity to electrolyse the same tonne"
    )


def test_h2_source_cost_carries_the_hours():
    body = _body("eTotalH2SrcCost", code_only=True)
    assert "pLoadLevelWeight" not in body, (
        "vH2Production is a rate in tH2/h, so the hours of the load level have to be in the cost"
    )


def test_the_balance_is_a_rate_balance():
    """No term of eBalanceH2 may carry pDuration.

    The whole hydrogen module is written in tH2/h, as the electricity module is written in GW. A
    pDuration anywhere in the balance means one term is a quantity while the rest are rates, which
    is the mistake the rate convention exists to make impossible.
    """
    body = _body("eBalanceH2", code_only=True)
    assert "pDuration" not in body, (
        "eBalanceH2 is a rate balance in tH2/h; a pDuration factor turns one of its terms into "
        "tonnes and silently rescales that term by the length of the load level"
    )
