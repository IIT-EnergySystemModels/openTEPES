"""The hydrogen reliability cost has to be annualised, and by the weight alone.

Every cost in the objective is written per load level and scaled up to a year. eTotalRH2Cost was
the one term with no scaling at all, so unserved hydrogen was priced at a fraction of everything
it competes with: on a week weighted by 52, a fifty-second of its real cost. Nothing about that
looks wrong from outside. The model still solves and the balance still holds; what changes is the
trade-off, because an electrolyser is priced against a full-weight investment while the shortfall
it would avoid is discounted.

The scaling is pLoadLevelWeight, not pLoadLevelDuration. Those differ by pDuration, and the hours
are already inside vH2NS: the balance reads ... + vH2NS == pDemandH2*pDuration, so vH2NS is tonnes
over the load level, not a rate. Using pLoadLevelDuration counts the hours twice, which is invisible
on any case with a one-hour step and wrong by a factor of four on sSEP.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "openTEPES" / "openTEPES_ModelFormulationHydrogen.py"


def _body(name, code_only=False):
    src = SRC.read_text()
    i = src.index(f"def {name}(")
    body = src[i:src.index("setattr", i)]
    if code_only:  # the comments discuss the wrong parameter on purpose; test the code
        body = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    return body


def test_h2_reliability_cost_is_annualised():
    body = _body("eTotalRH2Cost")
    assert re.search(r"pLoadLevelWeight\[p,sc,n\]\(\)\s*\*\s*sum\(", body), (
        "eTotalRH2Cost must scale the whole sum by pLoadLevelWeight; without it unserved "
        "hydrogen is under-priced by the stage weight against every other cost"
    )


def test_h2_reliability_does_not_count_the_hours_twice():
    body = _body("eTotalRH2Cost", code_only=True)
    assert "pLoadLevelDuration" not in body, (
        "vH2NS is tonnes over the load level, so it already carries pDuration; scaling by "
        "pLoadLevelDuration (= weight x duration) charges the hours a second time"
    )


def test_electricity_term_does_use_the_duration():
    # the contrast is the point: vENS is a power, so it needs the hours as well as the weight
    obj = (SRC.parent / "openTEPES_ModelFormulationObjective.py").read_text()
    i = obj.index("vTotalRElecCost[p,sc,n] ==")
    assert "pLoadLevelDuration" in obj[i:obj.index("\n", i)], (
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
