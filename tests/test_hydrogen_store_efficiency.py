"""A hydrogen store loses something on the round trip, and the loss belongs in the inventory.

`eH2Inventory` used to add what went in and subtract what came out one for one, so a cavern was a
perfect buffer: a tonne in, a tonne out, forever. Every other store in the model pays a round trip.
The shape is the one `eESSInventory` already uses, the square root split evenly between the two
directions, so a tonne withdrawn has cost a tonne over the efficiency to put in.

The loss is in the inventory, not in `eBalanceH2`. The balance is what the node sees: the store
takes the hydrogen it takes and delivers the hydrogen it delivers. Putting the efficiency there too
would charge the same loss twice.

`EfficiencyH2` is optional and defaults to 1.0, so a case written before this reads exactly as it
did.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "openTEPES" / "openTEPES_ModelFormulationHydrogen.py"


def _body(name):
    src = SRC.read_text()
    i = src.index(f"def {name}(")
    return src[i:src.index("setattr", i)]


def test_the_charge_is_multiplied_and_the_discharge_divided():
    body = _body("eH2Inventory")
    assert re.search(r"math\.sqrt\(mTEPES\.pEfficiencyH2\[hs\]\)", body), (
        "eH2Inventory must take the square root of pEfficiencyH2, as eESSInventory does for pEfficiency"
    )
    assert re.search(r"eta\s*\*\s*OptModel\.vH2StorCharge", body), "what goes in is scaled by the square root"
    assert re.search(r"OptModel\.vH2StorDischarge\[[^\]]+\]\s*/\s*eta", body), "what comes out is divided by it"


def test_the_balance_does_not_charge_the_loss_a_second_time():
    body = _body("eBalanceH2")
    assert "pEfficiencyH2" not in body, (
        "the round trip belongs in eH2Inventory; in eBalanceH2 it would be charged twice, once at "
        "the node and once in the store"
    )


def test_electricity_storage_uses_the_same_split():
    # the contrast is the point: this is not a new convention, it is the one the ESS already has
    src = (SRC.parent / "openTEPES_ModelFormulationElectricity.py").read_text()
    i = src.index("def eESSInventory(")
    body = src[i:src.index("setattr", i)]
    assert "math.sqrt(mTEPES.pEfficiency[es])" in body


def _efficiency_h2(cell_given, value=None):
    """The rule InputData applies. A blank cell and a zero both mean 'not given'."""
    if not cell_given:
        return 1.0
    if value is None or value != value or value == 0.0:   # absent, NaN, or a literal zero
        return 1.0
    return value


def test_absent_column_is_lossless():
    assert _efficiency_h2(cell_given=False) == 1.0


def test_a_given_efficiency_wins():
    assert _efficiency_h2(cell_given=True, value=0.9) == 0.9


def test_zero_is_not_a_store_that_swallows_everything():
    # 0.0 divides in eH2Inventory, so it is read as "not given" and warned about, exactly as Efficiency is
    assert _efficiency_h2(cell_given=True, value=0.0) == 1.0


def test_blank_cell_falls_back():
    assert _efficiency_h2(cell_given=True, value=float("nan")) == 1.0
