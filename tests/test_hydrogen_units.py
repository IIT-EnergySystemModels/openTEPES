"""The hydrogen balance is in tonnes. Check the two production functions agree with that.

eBalanceH2 sums terms in tH2 while vTotalOutput and vESSTotalCharge are in GW, so the scaling
applied when each production function is read decides whether its term lands in tonnes. The
electrolyser divides and needs a 1e-3; the hydrogen-fired generator multiplies and must not have one.
Copying the scaling from one to the other understates a turbine's fuel by a factor of a thousand,
and the model still balances, so nothing looks wrong.
"""
import math


LHV_MWH_PER_T = 33.33


def test_electrolyser_term_is_tonnes():
    # PF is kWh per gH2 after the 1e-3 applied on read
    eta = 0.622
    pf_kwh_per_kg = LHV_MWH_PER_T / eta          # kWh per kgH2
    pf_model = pf_kwh_per_kg * 1e-3              # kWh per gH2, as InputData stores it
    tonnes = 1.0e6 / pf_model / 1.0e6            # 1 GWh = 1e6 kWh, divide, g -> t
    # kWh/kg and MWh/t are numerically equal, so 1 GWh = 1000 MWh divided by the same number
    expected = 1.0e3 / pf_kwh_per_kg
    assert math.isclose(tonnes, expected, rel_tol=1e-9)


def test_turbine_term_is_tonnes_and_carries_no_milli_scaling():
    eta = 0.60
    pf_g_per_kwh = 1000.0 / (eta * LHV_MWH_PER_T)   # gH2 per kWh
    # the term openTEPES forms: vTotalOutput [GWh] * PF, with PF stored unscaled
    tonnes_model = 1.0e6 * pf_g_per_kwh / 1.0e6     # 1e6 kWh * g/kWh = g, /1e6 = t
    tonnes_true = (1.0e3 / eta) / LHV_MWH_PER_T     # 1 GWh = 1e3 MWh of output, / eta, / LHV
    assert math.isclose(tonnes_model, tonnes_true, rel_tol=1e-9)
    # and the failure this guards against: a 1e-3 would make it kilograms
    assert not math.isclose(tonnes_model * 1e-3, tonnes_true, rel_tol=1e-6)
