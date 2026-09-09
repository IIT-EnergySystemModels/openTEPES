"""The hydrogen excess price is its own input, and defaults to half the not-served price.

pH2ExcCost prices vH2Exc, the hydrogen a node cannot place. It was a literal half of HNSCost with
no input behind it, so a case could not price surplus hydrogen apart from scarcity: an export at a
low price and a shortage at the value of lost load had to share one number.

H2ExcCost in oT_Data_Parameter now sets it. Cases without the column keep the half, so their results
do not move.
"""


def _exc_cost(par):
    """The rule DataConfiguration applies."""
    v = par.get('pH2ExcCost')
    if v is None or v != v:                 # absent, or the column present and the cell blank
        v = par['pHNSCost'] * 0.5
    return v


def test_absent_column_keeps_the_half():
    assert _exc_cost({'pHNSCost': 10.0}) == 5.0


def test_given_column_wins():
    assert _exc_cost({'pHNSCost': 10.0, 'pH2ExcCost': 0.2}) == 0.2


def test_zero_is_honoured_not_treated_as_missing():
    # a free export is a real case, and 0.0 must not fall back to half of HNSCost
    assert _exc_cost({'pHNSCost': 10.0, 'pH2ExcCost': 0.0}) == 0.0


def test_excess_may_exceed_not_served():
    # nothing orders the two: a system penalised for venting more than for shedding is allowed
    assert _exc_cost({'pHNSCost': 10.0, 'pH2ExcCost': 25.0}) == 25.0


def test_blank_cell_falls_back():
    # the header is there and the cell empty, which arrives as NaN and means "not given"
    assert _exc_cost({'pHNSCost': 10.0, 'pH2ExcCost': float('nan')}) == 5.0
