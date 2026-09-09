"""The hydrogen carrier is switched on by two data files, and that was not enough.

oT_Data_DemandHydrogen and oT_Data_NetworkHydrogen each set pIndHydrogen. With neither present the
carrier is off, eBalanceH2 is never built, and a hydrogen-fired generator then produces electricity
without its fuel being charged anywhere: the term that charges it lives inside that balance.

An electrolyser is a different matter. Without the carrier it is a flexible load whose hydrogen
leaves the model boundary, as cases/9n_ELZ and cases/RTS24 rely on, so it must not bring the
carrier in.
"""
import pandas as pd


def _gen(**cols):
    return pd.DataFrame(cols, index=['g1', 'g2'])


def _consumers(gen):
    """The rule InputData applies: a hydrogen consumer enables the carrier.

    Two unit types consume hydrogen, and each is charged for it only in eBalanceH2.
    """
    def n(col):
        return int((gen[col] > 0.0).sum()) if col in gen.columns else 0
    return n('ProductionFunctionH2ToPower') + n('ProductionFunctionH2ToHeat')


def _turbines(gen):
    return _consumers(gen)


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


def test_hydrogen_boiler_enables_the_carrier_too():
    # a boiler burning hydrogen for heat is charged in eBalanceH2 exactly as a turbine is
    gen = _gen(ProductionFunctionH2ToHeat=[0.0, 0.02])
    assert _consumers(gen) == 1


def test_a_producer_only_case_stays_off():
    # electrolysers and a store make and hold hydrogen; neither consumes it
    gen = _gen(ProductionFunctionH2=[0.05, 0.05], MaximumStorageH2=[10.0, 0.0])
    assert _consumers(gen) == 0
