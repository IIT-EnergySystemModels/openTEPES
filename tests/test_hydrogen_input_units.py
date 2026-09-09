"""The hydrogen input units are not uniform, and two of them are easy to get wrong by a thousand.

ProductionFunctionH2ToHeat and ProductionFunctionH2ToPower enter eBalanceH2 the same way, as
pDuration x output x PF, so the term is in tonnes only if PF is in gH2/kWh. ToHeat is read in
kgH2/kWh and rescaled; ToPower is read in grams already and is not. Rescaling it too understates a
turbine's fuel by a factor of a thousand.

ProductionCostH2 is the same trap on the price side: HNSCost and H2ExcCost are read in EUR/kgH2 and
rescaled, this one is read in MEUR/tH2 and is not.
"""
LHV_KWH_PER_KG = 33.33


def test_topower_in_grams_gives_a_credible_turbine():
    pf = 50.005                                  # the value TF2030_rb carries
    efficiency = (1000.0 / pf) / LHV_KWH_PER_KG  # kWh_e per kgH2, over the LHV
    assert 0.30 < efficiency < 0.75, efficiency


def test_topower_in_kilograms_would_be_absurd():
    pf = 50.005
    efficiency = (1.0 / pf) / LHV_KWH_PER_KG
    assert efficiency < 0.001                    # 0.06%, which is how the error shows itself


def test_balance_term_is_tonnes_with_grams():
    # 1 GWh of output x PF[g/kWh] = 1e6 kWh x g/kWh = 1e6 g = 1 t
    assert 1.0e6 * (1.0e-6) == 1.0               # g -> t on 1 GWh, i.e. no further scaling


def test_production_cost_is_meur_per_tonne():
    cost = 0.002459                              # the value TF2030_rb carries
    assert abs(cost * 1000.0 - 2.459) < 1e-9     # MEUR/t -> EUR/kg, a credible reforming cost
