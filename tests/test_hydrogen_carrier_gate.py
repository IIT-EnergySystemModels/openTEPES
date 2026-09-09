"""The hydrogen carrier is switched on by two data files, and that was not enough.

oT_Data_DemandHydrogen and oT_Data_NetworkHydrogen each set pIndHydrogen. With neither present the
carrier is off, eBalanceH2 is never built, and a hydrogen-fired generator then produces electricity
without its fuel being charged anywhere: the term that charges it lives inside that balance.

An electrolyser is a different matter. Without the carrier it is a flexible load whose hydrogen
leaves the model boundary, which cases/9nH2 relies on, so it must not switch the carrier on.
"""
import pandas as pd


def _gen(**cols):
    return pd.DataFrame(cols, index=['g1', 'g2'])


def _turbines(gen):
    """The rule InputData applies: hydrogen-fired generation enables the carrier."""
    if 'ProductionFunctionH2ToPower' not in gen.columns:
        return 0
    return int((gen['ProductionFunctionH2ToPower'] > 0.0).sum())


def test_turbine_enables_the_carrier():
    gen = _gen(ProductionFunctionH2ToPower=[0.0, 0.05])
    assert _turbines(gen) == 1


def test_electrolyser_alone_does_not():
    gen = _gen(ProductionFunctionH2=[0.05, 0.05])
    assert _turbines(gen) == 0


def test_no_hydrogen_columns_at_all():
    gen = _gen(MaximumPower=[100.0, 50.0])
    assert _turbines(gen) == 0


def test_zero_valued_column_is_not_a_turbine():
    # a column present but all zero is how a case says "no hydrogen-fired unit here"
    gen = _gen(ProductionFunctionH2ToPower=[0.0, 0.0])
    assert _turbines(gen) == 0
