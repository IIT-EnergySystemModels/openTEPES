"""Input-side checks for the AC optimal power flow (Phase 0-1).

These tests build the model up to DataConfiguration only — no solve — so they run in seconds. They cover:

  * a DC case is untouched by the AC code path;
  * the AC-only tables are not even read when IndACPowerFlow is 0, so carrying AC data costs a DC run nothing;
  * the derived branch model (G, B, Smax, tap factor) is what the impedance implies;
  * the two input traps that silently produce a wrong or infeasible AC model — a blank Tap column and a blank AngMin/AngMax pair.
"""
import math
import os
import shutil

import pandas as pd
import pytest
from pyomo.environ import ConcreteModel

from openTEPES.openTEPES_DataConfiguration import DataConfiguration
from openTEPES.openTEPES_InputData import InputData

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _build(dir_name, case_name):
    """Read and configure a case, returning (model, dfs, par)."""
    mTEPES = ConcreteModel(case_name)
    dfs, par = InputData(dir_name, case_name, mTEPES, 0)
    DataConfiguration(mTEPES, dfs, par)
    return mTEPES, dfs, par


def _clone(tmp_path, source_case, new_name):
    """Copy a bundled case into tmp_path under a new name and return (dir, name)."""
    case_dir = tmp_path / new_name
    shutil.copytree(os.path.join(CASES_DIR, source_case), case_dir)
    for f in os.listdir(case_dir):
        if source_case in f:
            os.rename(case_dir / f, case_dir / f.replace(source_case, new_name))
    return str(tmp_path), new_name


def _edit_csv(case_dir, case_name, stem, edit, index_col=0):
    path = os.path.join(case_dir, case_name, f"oT_Data_{stem}_{case_name}.csv")
    df = pd.read_csv(path, index_col=index_col)
    edit(df)
    df.to_csv(path)


# --------------------------------------------------------------------------------------------------------------------
# The DC path is unchanged
# --------------------------------------------------------------------------------------------------------------------

def test_dc_case_has_no_ac_data():
    mTEPES, _, _ = _build(CASES_DIR, "9n")
    assert mTEPES.pIndACPowerFlow() == 0
    assert mTEPES.pIndACModelType() == 0
    for attr in ("pLineG", "pLineB", "pLineSmax", "pLineTapFactor", "pReactiveDemand", "sh"):
        assert not hasattr(mTEPES, attr), f"{attr} must not exist on a DC run"


def test_ac_tables_not_read_when_flag_is_off(tmp_path):
    """A case can carry AC data and still be run as DC. The reactive demand is a full time series, so skipping the read matters."""
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_off")
    _edit_csv(dir_name, name, "Option", lambda df: df.__setitem__("IndACPowerFlow", 0), index_col=None)

    _, dfs, par = _build(dir_name, name)
    assert par["pIndACPowerFlow"] == 0
    assert "dfReactiveDemand" not in dfs
    assert "dfBusShunt" not in dfs


# --------------------------------------------------------------------------------------------------------------------
# The AC path
# --------------------------------------------------------------------------------------------------------------------

def test_ac_case_builds_sets_and_parameters():
    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")

    assert mTEPES.pIndACPowerFlow() == 1
    assert set(mTEPES.she) == {"Reactor_1"}
    assert set(mTEPES.shc) == {"Capacitor_1"}
    assert set(mTEPES.sh) == set(mTEPES.she) | set(mTEPES.shc)
    assert dict(mTEPES.n2sh) or list(mTEPES.n2sh)          # the node map is populated
    assert len(mTEPES.gq) > 0

    # the rated reactive limits do not vary with the load level, so they are indexed on gq, not on psn x gq
    assert len(mTEPES.pMaxReactivePower) == len(mTEPES.gq)
    assert len(mTEPES.pMinReactivePower) == len(mTEPES.gq)


def test_derived_branch_model_matches_the_impedance():
    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    for la in mTEPES.laa:
        r, x = mTEPES.pLineR[la], mTEPES.pLineX[la]
        z2 = r**2 + x**2
        assert mTEPES.pLineG[la] == pytest.approx( r / z2)
        assert mTEPES.pLineB[la] == pytest.approx(-x / z2)
        # an inductive branch has negative series susceptance and non-negative conductance
        assert mTEPES.pLineB[la] < 0.0
        assert mTEPES.pLineG[la] >= 0.0
        # the apparent power rating is the larger of the two directional ratings, security factor already applied
        assert mTEPES.pLineSmax[la] == pytest.approx(max(mTEPES.pLineNTCFrw[la], mTEPES.pLineNTCBck[la]))


def test_reactive_demand_is_averaged_like_the_active_demand():
    """The CSV is in Mvar and the model works in Gvar. On a case with TimeStep > 1 both demands must also go through the
    same rolling window, otherwise the power factor the case was built with drifts load level by load level."""
    mTEPES, dfs, par = _build(CASES_DIR, "9n_AC")
    raw = dfs["dfReactiveDemand"]
    step = par["pTimeStep"]

    for p, sc, n in list(mTEPES.psn)[:5]:
        row = raw.index.get_loc((p, sc, n))
        for nd in list(mTEPES.nd)[:3]:
            window = raw[nd].iloc[max(0, row - step + 1): row + 1]
            expected = window.mean() * 1e-3 if len(window) == step else 0.0
            assert mTEPES.pReactiveDemand[p, sc, n, nd]() == pytest.approx(expected, abs=1e-9)

    # The 9n_AC case is built at a fixed 0.30 ratio, which survives only if both series were averaged the same way.
    # The tolerance is 1 % because the reactive demand is stored rounded to 3 decimals in Mvar, so on a lightly
    # loaded node the rounding alone moves the ratio by a few parts in a thousand. Anything larger than that would
    # mean the two series went through different windows, which is what this is really checking.
    for p, sc, n in list(mTEPES.psn)[:5]:
        for nd in list(mTEPES.nd)[:3]:
            act = mTEPES.pDemandElec[p, sc, n, nd]()
            if act > 1e-3:                      # skip near-zero nodes, where rounding dominates entirely
                assert mTEPES.pReactiveDemand[p, sc, n, nd]() / act == pytest.approx(0.30, rel=1e-2)


# --------------------------------------------------------------------------------------------------------------------
# The two input traps
# --------------------------------------------------------------------------------------------------------------------

def test_blank_tap_becomes_unity(tmp_path):
    """A blank Tap column arrives as 0.0 meaning 'not a transformer'. Inverting it directly would divide by zero and
    zero out every mutual admittance term, which is what the reference implementation in openTEPES_PRO does."""
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_notap")
    _edit_csv(dir_name, name, "Network", lambda df: df.__setitem__("Tap", 0.0), index_col=[0, 1, 2])

    mTEPES, _, _ = _build(dir_name, name)
    for la in mTEPES.la:
        assert mTEPES.pLineTapFactor[la] == pytest.approx(1.0)


def test_real_tap_is_inverted_once(tmp_path):
    """A tap of 1.02 rather than 1.25: the tap now reaches the constraints, and a uniform 1.25 on every branch of a
    9-bus system genuinely cannot hold a 0.95-1.05 voltage band, so bound tightening rejects it. Real transformer
    taps are a few per cent (RTS-GMLC ships 1.015 and 1.03)."""
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_tap")
    _edit_csv(dir_name, name, "Network", lambda df: df.__setitem__("Tap", 1.02), index_col=[0, 1, 2])

    mTEPES, _, _ = _build(dir_name, name)
    for la in mTEPES.la:
        assert mTEPES.pLineTapFactor[la] == pytest.approx(1.0 / 1.02)


def _single_stage(mTEPES, p, sc, st):
    """Collapse the model to one stage and two load levels so a single (p, sc, st) formulation call can be built."""
    from pyomo.environ import Set

    mTEPES.del_component(mTEPES.st); mTEPES.del_component(mTEPES.n); mTEPES.del_component(mTEPES.n2)
    levels = [nn for nn in mTEPES.nn if (p, sc, st, nn) in mTEPES.s2n][:2]
    mTEPES.st = Set(initialize=[st]); mTEPES.n = Set(initialize=levels); mTEPES.n2 = Set(initialize=levels)
    mTEPES.na = Set(initialize=levels); mTEPES.First_st = st; mTEPES.Last_st = st; mTEPES.NoRepetition = 0
    mTEPES.nesc = []; mTEPES.necc = []; mTEPES.neso = []
    mTEPES.ngen = [(n, g) for n, g in mTEPES.n * mTEPES.g]
    return levels


def _coefficient_on(expr, var):
    """Linear coefficient of ``var`` in ``expr``, read by evaluation rather than by picking the expression apart."""
    from pyomo.core.expr.visitor import identify_variables
    from pyomo.environ import value

    for v in identify_variables(expr):
        v.set_value(0.0)
    base = value(expr)
    var.set_value(1.0)
    return value(expr) - base


@pytest.mark.parametrize("tap", [1.00, 1.05])
def test_tap_reaches_the_voltage_drop(tmp_path, tap):
    """The tap was once computed, stored, documented and tested, and then read by no constraint at all, so every
    transformer solved as 1:1 with nothing in the output saying so. The sending-end voltage in the drop equation must
    carry (1/tap)^2."""
    from openTEPES.openTEPES_ModelFormulationAC import NetworkACOperationModelFormulation
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    dir_name, name = _clone(tmp_path, "9n_AC", f"9n_tapc{str(tap).replace('.', '')}")
    _edit_csv(dir_name, name, "Network", lambda df: df.__setitem__("Tap", tap), index_col=[0, 1, 2])
    mTEPES, _, _ = _build(dir_name, name)
    SettingUpVariables(mTEPES, mTEPES)

    p, sc = list(mTEPES.ps)[0]
    st = list(mTEPES.stt)[0]
    levels = _single_stage(mTEPES, p, sc, st)
    NetworkACOperationModelFormulation(mTEPES, mTEPES, 0, p, sc, st)

    con = getattr(mTEPES, f"eVoltageDropUp_{p}_{sc}_{st}")
    n0 = levels[0]
    key = next(k for k in con if k[0] == n0)
    ni = key[1]
    coef = _coefficient_on(con[key].body, mTEPES.vW[p, sc, n0, ni])
    assert coef == pytest.approx(-(1.0 / tap) ** 2, rel=1e-9), (
        f"tap {tap}: vW[ni] carries {coef}, expected {-(1.0 / tap) ** 2}")


def test_blank_angle_limits_open_to_half_pi(tmp_path):
    """AngMin = AngMax = 0 is how a case that never filled the columns arrives. Taken literally it pins every angle
    difference to zero, which makes the AC model infeasible the moment any power flows."""
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_noang")

    def blank(df):
        df["AngMin"] = 0.0
        df["AngMax"] = 0.0

    _edit_csv(dir_name, name, "Network", blank, index_col=[0, 1, 2])

    mTEPES, _, _ = _build(dir_name, name)
    for la in mTEPES.la:
        assert mTEPES.pAngMin[la]() == pytest.approx(-math.pi / 2)
        assert mTEPES.pAngMax[la]() == pytest.approx( math.pi / 2)


def test_inverted_angle_limits_raise(tmp_path):
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_badang")

    def swap(df):
        df["AngMin"] =  30.0
        df["AngMax"] = -30.0

    _edit_csv(dir_name, name, "Network", swap, index_col=[0, 1, 2])

    with pytest.raises(ValueError, match="AngMin must be below AngMax"):
        _build(dir_name, name)


def test_inverted_voltage_band_raises(tmp_path):
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_badv")

    def swap(df):
        df["VMin"] = 1.10
        df["VMax"] = 0.90

    _edit_csv(dir_name, name, "Parameter", swap, index_col=None)

    with pytest.raises(ValueError, match="must be below VMax"):
        _build(dir_name, name)


# --------------------------------------------------------------------------------------------------------------------
# Bound tightening
# --------------------------------------------------------------------------------------------------------------------

def test_bound_tightening_never_loosens():
    """The tightened angle bound may only shrink the declared one."""
    for case in ("9n_AC", "RTS-GMLC_AC"):
        mTEPES, _, _ = _build(CASES_DIR, case)
        for la in mTEPES.laa:
            declared = min(abs(mTEPES.pAngMin[la]()), abs(mTEPES.pAngMax[la]()))
            assert 0.0 < mTEPES.pMaxAngleDiff[la] <= declared + 1e-12


def test_tightened_angle_bound_is_what_the_thermal_limit_implies():
    """|Vi||Vj| sin(theta) = xP + rQ gives |sin theta| <= |S|*z / Vmin^2. Two things have to be right in |S|, and both
    were wrong once: the rating is in GVA so it needs dividing by pSBase to meet a per-unit impedance, and the apparent
    power the model actually implies is Smax*Vmax/Vmin, not Smax, because the thermal limit is l <= (Smax/Vmin)^2 and
    the cone gives P^2+Q^2 <= vW*l. Assuming either away makes the bound a restriction that can cut off the optimum."""
    for case in ("9n_AC", "RTS-GMLC_AC"):
        mTEPES, _, par = _build(CASES_DIR, case)
        for la in list(mTEPES.laa)[:40]:
            z = math.hypot(mTEPES.pLineR[la], mTEPES.pLineX[la])
            smax = mTEPES.pLineSmax[la] / mTEPES.pSBase * par["pVMax"] / par["pVMin"]
            # the sending-end voltage the series impedance sees carries the tap, so the divisor is (Vmin/tap) * Vmin
            tapf = mTEPES.pLineTapFactor[la]
            implied = math.asin(min(1.0, smax * z / (par["pVMin"] * tapf * par["pVMin"])))
            # the two sides are carried separately: collapsing them to min(|AngMin|, |AngMax|) would cut off range the
            # case explicitly permits on a branch whose declared limits are not symmetric
            assert mTEPES.pMaxAngleDiff[la] == pytest.approx(min( abs(mTEPES.pAngMax[la]()),  implied), rel=1e-9)
            assert mTEPES.pMinAngleDiff[la] == pytest.approx(max(-abs(mTEPES.pAngMin[la]()), -implied), rel=1e-9)


def test_asymmetric_angle_limits_are_not_collapsed(tmp_path):
    """A branch whose declared limits are not symmetric must keep both sides. The tightening once took
    min(|AngMin|, |AngMax|) and imposed it symmetrically, which silently removed range the data allows.

    The declared values have to be TIGHTER than what the thermal limit implies or there is nothing to preserve: on
    9n_AC the implied bound is only 2-4 degrees, so a declared -50/+20 is clamped symmetrically and the asymmetry
    never reaches the model."""
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_asym")

    def asym(df):
        df["AngMin"] = -3.0
        df["AngMax"] = 1.0

    _edit_csv(dir_name, name, "Network", asym, index_col=[0, 1, 2])
    mTEPES, _, _ = _build(dir_name, name)
    pSeen = False
    for la in mTEPES.laa:
        hi, lo = mTEPES.pMaxAngleDiff[la], mTEPES.pMinAngleDiff[la]
        assert hi <= math.radians(1.0) + 1e-12
        assert lo >= math.radians(-3.0) - 1e-12
        if lo < -hi - 1e-9:
            pSeen = True
    assert pSeen, "no branch kept an asymmetric band, so the two sides are still being collapsed"


def test_tightening_shrinks_the_envelope_slack():
    """The angle envelope's slack is tan(t/2) - t/2 per branch, and shrinking it is the whole reason the tightening runs
    before the variables are declared.

    The thresholds here are deliberately modest, and the history is worth keeping: an earlier version of the tightening
    dropped the /pSBase conversion and so reported a bound ten times tighter than the model implies, which made the
    measured improvement look like three orders of magnitude on every case. With the valid bound the median branch on
    RTS-GMLC improves about 47x and the WORST branch only about 3.5x. A test that demanded more than the physics gives
    would have to be relaxed every time the tightening was corrected, which is the wrong way round.
    """
    import statistics
    for case, min_median, min_worst in (("9n_AC", 100.0, 50.0), ("RTS-GMLC_AC", 10.0, 2.0)):
        mTEPES, _, _ = _build(CASES_DIR, case)
        slack = lambda t: math.tan(t / 2) - t / 2
        declared  = [slack(min(abs(mTEPES.pAngMin[la]()), abs(mTEPES.pAngMax[la]()))) for la in mTEPES.laa]
        tightened = [slack(mTEPES.pMaxAngleDiff[la])                                  for la in mTEPES.laa]
        assert statistics.median(declared) / statistics.median(tightened) > min_median, f"{case}: median slack barely moved"
        assert max(declared) / max(tightened) > min_worst, f"{case}: worst-case slack barely moved"


def test_voltage_bounds_stay_inside_the_declared_band():
    for case in ("9n_AC", "RTS-GMLC_AC"):
        mTEPES, _, par = _build(CASES_DIR, case)
        for nd in mTEPES.nd:
            assert par["pVMin"] - 1e-12 <= mTEPES.pVMinBus[nd] <= mTEPES.pVMaxBus[nd] <= par["pVMax"] + 1e-12


# --------------------------------------------------------------------------------------------------------------------
# Branch-flow variables
# --------------------------------------------------------------------------------------------------------------------

def _build_with_vars(dir_name, case_name):
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables
    mTEPES, dfs, par = _build(dir_name, case_name)
    SettingUpVariables(mTEPES, mTEPES)
    return mTEPES


def test_ac_variables_exist_with_the_right_index_sets():
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    assert len(mTEPES.vW)    == len(mTEPES.psnnd)
    assert len(mTEPES.vCurr) == len(mTEPES.psnlaa)
    assert len(mTEPES.vFlowElecBck)  == len(mTEPES.psnlaa)
    assert len(mTEPES.vFlowReactFrw) == len(mTEPES.psnlaa)
    assert len(mTEPES.vFlowReactBck) == len(mTEPES.psnlaa)
    assert len(mTEPES.vReactiveTotalOutput) == len(mTEPES.psngq)
    assert len(mTEPES.vQShunt) == len(mTEPES.psnsh)
    # the bus-injection voltage products belong to a formulation this model does not use
    for gone in ("vWC", "vWS", "bp", "psnbp"):
        assert not hasattr(mTEPES, gone), f"{gone} is left over from the bus-injection formulation"


def test_voltage_variable_uses_the_tightened_per_bus_bounds():
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    for p, sc, n, nd in list(mTEPES.psnnd)[:40]:
        assert mTEPES.vW[p, sc, n, nd].lb == pytest.approx(mTEPES.pVMinBus[nd] ** 2)
        assert mTEPES.vW[p, sc, n, nd].ub == pytest.approx(mTEPES.pVMaxBus[nd] ** 2)


def test_reference_bus_voltage_is_fixed():
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    ref = mTEPES.rf.first()
    for p, sc, n in list(mTEPES.psn)[:10]:
        assert mTEPES.vW[p, sc, n, ref].fixed
        assert mTEPES.vW[p, sc, n, ref].value == pytest.approx(1.0)


def test_current_limit_uses_the_rating_at_the_lowest_voltage():
    """Chowdhury et al. (7): the squared-current limit is (Smax/Vmin)^2. Using the tightened per-bus minimum rather
    than the global one matters, because the global value makes the limit permissive by (Vmax/Vmin) in apparent power."""
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    for p, sc, n, ni, nf, cc in list(mTEPES.psnlaa)[:40]:
        expected = (mTEPES.pLineSmax[ni, nf, cc] / mTEPES.pVMinBus[ni]) ** 2
        assert mTEPES.vCurr[p, sc, n, ni, nf, cc].ub == pytest.approx(expected)


def test_dc_case_declares_no_ac_variables():
    mTEPES = _build_with_vars(CASES_DIR, "9n")
    for attr in ("vW", "vCurr", "vFlowElecBck", "vFlowReactFrw", "vQShunt", "vShuntInvest"):
        assert not hasattr(mTEPES, attr), f"{attr} must not exist on a DC run"


# --------------------------------------------------------------------------------------------------------------------
# Formulation selection
# --------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("model_type", [0, 1, 2])
def test_supported_ac_model_types_are_accepted(tmp_path, model_type):
    dir_name, name = _clone(tmp_path, "9n_AC", f"9n_mt{model_type}")
    _edit_csv(dir_name, name, "Option", lambda df: df.__setitem__("IndACModelType", model_type), index_col=None)
    mTEPES, _, _ = _build(dir_name, name)
    assert mTEPES.pIndACModelType() == model_type


def test_unsupported_ac_model_type_is_rejected(tmp_path):
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_mtbad")
    _edit_csv(dir_name, name, "Option", lambda df: df.__setitem__("IndACModelType", 7), index_col=None)
    with pytest.raises(NotImplementedError, match="IndACModelType"):
        _build(dir_name, name)


@pytest.mark.parametrize("mode", [0, 1, 2, 3])
def test_supported_ac_power_flow_models_are_accepted(tmp_path, mode):
    """0 DC, 1 branch flow, 2 bus injection in W space, 3 bus injection in rectangular coordinates.

    An earlier version of this test asserted that 2 was REJECTED, on the reasoning that Bose and Low prove the two SOC
    relaxations give the same bound so a second formulation would show nothing. That is a statement about the optimal
    value, not about conditioning or solve time, which is the question the second formulation exists to answer."""
    dir_name, name = _clone(tmp_path, "9n_AC", f"9n_pf{mode}")
    _edit_csv(dir_name, name, "Option", lambda df: df.__setitem__("IndACPowerFlow", mode), index_col=None)
    mTEPES, _, _ = _build(dir_name, name)
    assert mTEPES.pIndACPowerFlow() == mode


def test_unsupported_ac_power_flow_model_is_rejected(tmp_path):
    dir_name, name = _clone(tmp_path, "9n_AC", "9n_pfbad")
    _edit_csv(dir_name, name, "Option", lambda df: df.__setitem__("IndACPowerFlow", 4), index_col=None)
    with pytest.raises(NotImplementedError, match="IndACPowerFlow"):
        _build(dir_name, name)


@pytest.mark.parametrize("mode", [1, 3])
def test_cycle_option_is_refused_where_it_says_nothing(tmp_path, mode):
    """The loop condition is meaningful only in W space. Under branch flow the angle is an explicit node potential, so
    the sum around any cycle is identically zero; under rectangular coordinates the voltages are explicit."""
    dir_name, name = _clone(tmp_path, "9n_AC", f"9n_cyc{mode}")

    def opt(df):
        df["IndACPowerFlow"] = mode
        df["IndACCycle"] = 1

    _edit_csv(dir_name, name, "Option", opt, index_col=None)
    with pytest.raises(NotImplementedError, match="IndACCycle"):
        _build(dir_name, name)


def test_lpac_reduces_to_dc_on_a_lossless_branch():
    """The LPAC substitution vW -> 1+2phi, vWC -> cs+phi_i+phi_j, vWS -> dtheta turns the exact W-space branch equation
    into DC power flow when the branch is lossless and the voltages sit at nominal. This is the property that lets the
    same equation serve both formulations, so it is worth pinning down."""
    r, x, tap = 0.0, 0.05, 1.0
    z2 = r**2 + x**2
    pG, pB = r / z2, -x / z2

    def p_from_w(w_i, wc, ws):
        return pG * tap**2 * w_i - tap * pG * wc - tap * pB * ws

    for deg in (2, 5, 10, 20, 30):
        dth = math.radians(deg)
        assert p_from_w(1.0, 1.0, dth) == pytest.approx(dth / x)              # LPAC == DC exactly
        assert p_from_w(1.0, math.cos(dth), math.sin(dth)) == pytest.approx(math.sin(dth) / x)   # exact AC


# --------------------------------------------------------------------------------------------------------------------
# Investment decisions must cost something
# --------------------------------------------------------------------------------------------------------------------

def test_candidate_shunts_are_priced_in_the_objective():
    """A candidate shunt appears in the disjunctions that switch its reactive injection on. If it appears nowhere in
    the objective the device is free and the model builds every one that helps, which is a silent modelling error
    rather than a visible one."""
    from openTEPES.openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation
    from openTEPES.openTEPES_ModelFormulationObjective import TotalObjectiveFunction
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    SettingUpVariables(mTEPES, mTEPES)
    assert mTEPES.shc, "the 9n_AC case is expected to carry a candidate shunt"
    assert all(mTEPES.pShuntFixedCost[sh] > 0.0 for sh in mTEPES.shc)

    TotalObjectiveFunction(mTEPES, mTEPES, 0)
    InvestmentElecModelFormulation(mTEPES, mTEPES, 0)

    # every candidate shunt's investment variable must appear in the fixed-cost constraint
    body = str(mTEPES.eTotalFElecCost[mTEPES.p.first()].body)
    for p_, sh in mTEPES.pshc:
        assert "vShuntInvest" in body, "vShuntInvest is absent from eTotalFElecCost, so the device is free"


# --------------------------------------------------------------------------------------------------------------------
# AC results
# --------------------------------------------------------------------------------------------------------------------

def test_ac_output_category_is_registered_and_never_optional():
    """The relaxation diagnostic tells a user whether any other AC number can be trusted, so it must survive the
    minimal output setting rather than only appearing under --results full.

    It sits in its own category: 'acdiag' is two small files and belongs in the minimal mode, while 'acnetwork' is
    eight hourly wide tables and does not."""
    from openTEPES.openTEPES import OUTPUT_ALIASES, OUTPUT_CATEGORIES, OUTPUT_REGISTRY

    assert "acnetwork" in OUTPUT_CATEGORIES
    assert "acdiag"    in OUTPUT_CATEGORIES
    assert "acdiag"    in OUTPUT_ALIASES["min"], "the relaxation diagnostic must survive the minimal output mode"
    assert "acnetwork" not in OUTPUT_ALIASES["min"], "the hourly AC tables do not belong in the minimal output mode"

    entries = [e for e in OUTPUT_REGISTRY if e[0] in ("acnetwork", "acdiag")]
    assert len(entries) == 3, "expected the diagnostic, operation and marginal writers"
    for _key, _fn, _extra, guard in entries:
        assert guard is not None, "the AC writers must be guarded so a DC run never calls them"


def test_ac_writers_run_on_an_ac_case(tmp_path):
    """The DC test below only proves the writers return early. Nothing exercised them on an AC model, which is how a
    free name survived a refactor: splitting the relaxation diagnostic out of the operation writer left `sBranch`
    defined in one function and referenced in the other, so every AC run raised NameError after solving.

    The model is not solved — the values are filled in directly. That is enough to catch a name or key error in the
    writers, which is what this is for, and it keeps the test to seconds rather than minutes."""
    from pyomo.environ import Var

    from openTEPES.openTEPES_OutputResultsAC import (ACMarginalResults, ACNetworkOperationResults,
                                                     ACRelaxationDiagnostic)
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    SettingUpVariables(mTEPES, mTEPES)
    for var in mTEPES.component_objects(Var, active=True):
        for idx in var:
            if var[idx].value is None:
                lo, hi = var[idx].lb, var[idx].ub
                var[idx].value = 0.0 if lo is None or lo <= 0.0 <= (hi if hi is not None else 0.0) else lo

    mTEPES.pOutputPath = str(tmp_path)
    mTEPES.pOutputBackend = "csv"
    ACRelaxationDiagnostic(CASES_DIR, "9n_AC", mTEPES, mTEPES)
    ACNetworkOperationResults(CASES_DIR, "9n_AC", mTEPES, mTEPES)
    ACMarginalResults(CASES_DIR, "9n_AC", mTEPES, mTEPES)

    written = {q.name for q in tmp_path.rglob("oT_Result_*.csv")}
    assert any("ACRelaxationGap" in w for w in written), f"no relaxation gap file written, got {sorted(written)}"
    assert any("NetworkVoltageMagnitude" in w for w in written), f"no voltage file written, got {sorted(written)}"


def test_ac_writers_are_no_ops_on_a_dc_case(tmp_path):
    from openTEPES.openTEPES_OutputResultsAC import ACMarginalResults, ACNetworkOperationResults, ACRelaxationDiagnostic

    mTEPES, _, _ = _build(CASES_DIR, "9n")
    mTEPES.pOutputPath = str(tmp_path)
    mTEPES.pOutputBackend = "csv"
    ACRelaxationDiagnostic(CASES_DIR, "9n", mTEPES, mTEPES)
    ACNetworkOperationResults(CASES_DIR, "9n", mTEPES, mTEPES)
    ACMarginalResults(CASES_DIR, "9n", mTEPES, mTEPES)
    assert not list(tmp_path.glob("*.csv")), "a DC run must write no AC result files"


# --------------------------------------------------------------------------------------------------------------------
# Synchronous condensers: zero MW, positive Mvar
# --------------------------------------------------------------------------------------------------------------------

def _add_condenser(tmp_path, name, invest_cost):
    """Clone 9n_AC and add a synchronous condenser: zero active power, positive reactive capability."""
    dir_name, case = _clone(tmp_path, "9n_AC", name)
    base = os.path.join(dir_name, case)

    tech = os.path.join(base, f"oT_Dict_Technology_{case}.csv")
    tdf = pd.read_csv(tech)
    if "SynchronousCondenser" not in tdf.iloc[:, 0].values:
        tdf = pd.concat([tdf, pd.DataFrame({tdf.columns[0]: ["SynchronousCondenser"]})], ignore_index=True)
        tdf.to_csv(tech, index=False)

    gdict = os.path.join(base, f"oT_Dict_Generation_{case}.csv")
    gdf = pd.read_csv(gdict)
    gdf = pd.concat([gdf, pd.DataFrame({gdf.columns[0]: ["SynCon_1"]})], ignore_index=True)
    gdf.to_csv(gdict, index=False)

    gen_path = os.path.join(base, f"oT_Data_Generation_{case}.csv")
    gen = pd.read_csv(gen_path)
    row = gen.iloc[0].copy()
    for c in gen.select_dtypes("number").columns:
        row[c] = 0.0
    row[gen.columns[0]] = "SynCon_1"
    row["Node"] = "Node_5"
    row["Technology"] = "SynchronousCondenser"
    row["MaximumPower"] = 0.0                     # this is the whole point: no active power at all
    row["MaximumReactivePower"] = 120.0
    row["MinimumReactivePower"] = -80.0
    row["InitialPeriod"], row["FinalPeriod"] = 2020, 2050
    row["FixedInvestmentCost"], row["FixedChargeRate"] = invest_cost, 0.06
    row["Efficiency"] = 1.0
    gen = pd.concat([gen, row.to_frame().T], ignore_index=True)
    gen.to_csv(gen_path, index=False)
    return dir_name, case


def test_zero_mw_condenser_survives_into_the_reactive_sets(tmp_path):
    """A synchronous condenser has MaximumPower = 0, so it never enters mTEPES.g and therefore never enters pg. The
    reactive sets must key on the unit's own period window instead, or they come out empty for exactly the units they
    exist to hold."""
    dir_name, case = _add_condenser(tmp_path, "9n_sc", invest_cost=0.0)
    mTEPES, _, _ = _build(dir_name, case)

    assert "SynCon_1" not in set(mTEPES.g), "a zero-MW unit is not a generating unit"
    assert "SynCon_1" in set(mTEPES.gq), "but it is a reactive-capable unit"
    assert "SynCon_1" in set(mTEPES.sq), "and a synchronous condenser"
    assert ("Node_5", "SynCon_1") in mTEPES.n2gq, "it must reach the reactive balance through n2gq"
    assert any(gq == "SynCon_1" for p, gq in mTEPES.pgq), "and be available in at least one period"
    assert any(k[3] == "SynCon_1" for k in mTEPES.psngq), "so that it gets a reactive output variable"


def test_candidate_condenser_is_priced_and_switchable(tmp_path):
    from openTEPES.openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation
    from openTEPES.openTEPES_ModelFormulationObjective import TotalObjectiveFunction
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    dir_name, case = _add_condenser(tmp_path, "9n_scc", invest_cost=5.0)
    mTEPES, _, _ = _build(dir_name, case)
    assert "SynCon_1" in set(mTEPES.sqc), "a positive investment cost makes it a candidate"
    assert mTEPES.pSynchFixedCost["SynCon_1"] == pytest.approx(5.0 * 0.06)

    SettingUpVariables(mTEPES, mTEPES)
    assert hasattr(mTEPES, "vSynchInvest")
    TotalObjectiveFunction(mTEPES, mTEPES, 0)
    InvestmentElecModelFormulation(mTEPES, mTEPES, 0)
    assert "vSynchInvest" in str(mTEPES.eTotalFElecCost[mTEPES.p.first()].body), \
        "vSynchInvest is absent from eTotalFElecCost, so the condenser is free"


def test_existing_condenser_needs_no_investment_variable(tmp_path):
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    dir_name, case = _add_condenser(tmp_path, "9n_sce", invest_cost=0.0)
    mTEPES, _, _ = _build(dir_name, case)
    assert "SynCon_1" in set(mTEPES.sqe) and not mTEPES.sqc
    SettingUpVariables(mTEPES, mTEPES)
    assert not hasattr(mTEPES, "vSynchInvest"), "an existing device needs no build decision"


# --------------------------------------------------------------------------------------------------------------------
# Candidate AC lines: neither bundled case has one, so build one
# --------------------------------------------------------------------------------------------------------------------

def _with_candidate_ac_line(tmp_path, name):
    """Clone 9n_AC and turn one existing AC line into a candidate by giving it an investment cost."""
    dir_name, case = _clone(tmp_path, "9n_AC", name)
    path = os.path.join(dir_name, case, f"oT_Data_Network_{case}.csv")
    df = pd.read_csv(path)
    ac = df.index[(df["LineType"] == "AC")][0]
    df.loc[ac, "FixedInvestmentCost"] = 50.0
    df.loc[ac, "FixedChargeRate"] = 0.06
    df.to_csv(path, index=False)
    return dir_name, case, (df.loc[ac, "InitialNode"], df.loc[ac, "FinalNode"], df.loc[ac, "Circuit"])


def test_candidate_ac_line_is_recognised(tmp_path):
    dir_name, case, la = _with_candidate_ac_line(tmp_path, "9n_cand")
    mTEPES, _, _ = _build(dir_name, case)
    assert la in set(mTEPES.lc), "the line should be a candidate"
    assert la in set(mTEPES.lca), "and an AC candidate"


def test_unbuilt_candidate_ac_line_carries_nothing_and_couples_nothing(tmp_path):
    """An unbuilt candidate must not carry current and must not tie its two bus voltages together. The DC model gets
    this from pBigMFlow*(1 - vLineCommit) in eKirchhoff2ndLaw, which is skipped under AC — so the AC model has to
    supply it, and at first it did not: the line was free transmission."""
    from pyomo.environ import Constraint, Set, SolverFactory, value

    from openTEPES.openTEPES_ModelFormulationInvestment import InvestmentElecModelFormulation
    from openTEPES.openTEPES_ModelFormulationObjective import TotalObjectiveFunction
    from openTEPES.openTEPES_ProblemSolvingStageIter import FORMULATION_REGISTRY
    from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

    dir_name, case, la = _with_candidate_ac_line(tmp_path, "9n_cand2")
    mTEPES, dfs, par = _build(dir_name, case)
    SettingUpVariables(mTEPES, mTEPES)

    p, sc = list(mTEPES.ps)[0]
    st = list(mTEPES.stt)[0]
    mTEPES.del_component(mTEPES.st); mTEPES.del_component(mTEPES.n); mTEPES.del_component(mTEPES.n2)
    levels = [nn for nn in mTEPES.nn if (p, sc, st, nn) in mTEPES.s2n][:2]
    mTEPES.st = Set(initialize=[st]); mTEPES.n = Set(initialize=levels); mTEPES.n2 = Set(initialize=levels)
    mTEPES.na = Set(initialize=levels); mTEPES.First_st = st; mTEPES.Last_st = st; mTEPES.NoRepetition = 0
    mTEPES.nesc = []; mTEPES.necc = []; mTEPES.neso = []
    mTEPES.ngen = [(n, g) for n, g in mTEPES.n * mTEPES.g]

    TotalObjectiveFunction(mTEPES, mTEPES, 0)
    InvestmentElecModelFormulation(mTEPES, mTEPES, 0)
    for _lab, fn, guard in FORMULATION_REGISTRY:
        if guard is not None and not guard(mTEPES):
            continue
        fn(mTEPES, mTEPES, 0, p, sc, st)
    for c in mTEPES.component_objects(Constraint, active=True):
        if any(k in c.name for k in ("RESEnergy", "Emission")):
            c.deactivate()

    # force the line NOT to be built, then check it is electrically absent
    mTEPES.vNetworkInvest[p, la[0], la[1], la[2]].fix(0.0)
    res = SolverFactory("gurobi").solve(mTEPES)
    assert str(res.solver.termination_condition) == "optimal", "the network should still be feasible without the candidate"

    n0 = levels[0]
    assert abs(value(mTEPES.vCurr[p, sc, n0, la]))          < 1e-6, "an unbuilt line carries current"
    assert abs(value(mTEPES.vFlowElec[p, sc, n0, la]))      < 1e-4, "an unbuilt line carries active power"
    assert abs(value(mTEPES.vFlowReactFrw[p, sc, n0, la]))  < 1e-4, "an unbuilt line carries reactive power"


# --------------------------------------------------------------------------------------------------------------------
# The exact restoration pass
# --------------------------------------------------------------------------------------------------------------------

def _tiny_ac_case(tmp_path, name, hours=4, model_type=0, restore=1):
    """A few hours of 9n_AC, with the annual RES target scaled to the horizon.

    An annual energy target does not survive a truncated horizon: left at its full-year value it exceeds the demand of
    the hours that remain and the case is infeasible before any AC question is reached.
    """
    dir_name, case = _clone(tmp_path, "9n_AC", name)
    dur  = pd.read_csv(os.path.join(dir_name, case, f"oT_Data_Duration_{case}.csv"))
    keep = set(dur.loc[: hours - 1, "LoadLevel"])
    full = len(dur)
    for f in os.listdir(os.path.join(dir_name, case)):
        if not f.endswith(".csv"):
            continue
        path = os.path.join(dir_name, case, f)
        df = pd.read_csv(path)
        if "LoadLevel" in df.columns:
            df[df["LoadLevel"].isin(keep)].to_csv(path, index=False)

    res = os.path.join(dir_name, case, f"oT_Data_RESEnergy_{case}.csv")
    df  = pd.read_csv(res)
    df["RESEnergy"] = pd.to_numeric(df["RESEnergy"], errors="coerce").fillna(0.0) * hours / full
    df.to_csv(res, index=False)

    opt = os.path.join(dir_name, case, f"oT_Data_Option_{case}.csv")
    df  = pd.read_csv(opt)
    df.loc[:, "IndACModelType"] = model_type
    df["IndACRestore"] = restore
    df.to_csv(opt, index=False)
    return dir_name, case


def test_restoration_option_is_validated(tmp_path):
    """A value that is not 0 or 1 must be refused, not silently treated as off.

    The earlier version of this test only asserted the default was 0, which the validation branch is not needed to
    satisfy — it would have passed just as happily with the check deleted."""
    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    assert mTEPES.pIndACRestore() == 0, "the restoration pass must be off unless a case asks for it"

    dir_name, case = _clone(tmp_path, "9n_AC", "9n_badrestore")
    opt = os.path.join(dir_name, case, f"oT_Data_Option_{case}.csv")
    df = pd.read_csv(opt)
    df["IndACRestore"] = 2
    df.to_csv(opt, index=False)
    with pytest.raises(NotImplementedError, match="IndACRestore"):
        _build(dir_name, case)


def test_restoration_is_skipped_when_nothing_to_restore(tmp_path):
    """Type 2 is already exact, so there is no relaxation to replace and the pass must decline rather than rebuild."""
    from openTEPES.openTEPES_ModelFormulationAC import ACRestorationPass

    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    mTEPES.pIndACModelType._data[None] = 2
    assert ACRestorationPass(mTEPES, mTEPES, "ipopt", 0) is None

    mTEPES.pIndACModelType._data[None] = 0
    assert ACRestorationPass(mTEPES, mTEPES, "ipopt", 0) is None, "no recorded blocks means nothing to do"


def test_restoration_makes_the_relaxation_exact(tmp_path):
    """The whole point: after the pass the cone is closed and the cost is the cost of the plan, not below it.

    On a case whose cone is already tight the restoration should barely move the objective. It must never move it DOWN:
    the relaxed solve is a lower bound, so making the same plan physical can only cost the same or more.
    """
    from openTEPES.openTEPES import openTEPES_run

    dir_name, case = _tiny_ac_case(tmp_path, "9n_restore")
    mTEPES = openTEPES_run(str(dir_name), case, "gurobi", 0, 0)

    pSBase = mTEPES.pSBase
    pWorst = 0.0
    for k in mTEPES.psnlaa:
        p, sc, n, ni, nf, cc = k
        pNorm = max(mTEPES.pLineSmax[ni, nf, cc] ** 2, 1e-12)
        pGap = (mTEPES.vW[p, sc, n, ni]() * mTEPES.pLineTapFactor[ni, nf, cc] ** 2
                * mTEPES.vCurr[k]() * pSBase ** 2
                - mTEPES.vFlowElec[k]() ** 2 - mTEPES.vFlowReactFrw[k]() ** 2) / pNorm
        pWorst = max(pWorst, abs(pGap))

    assert pWorst < 1e-6, f"the restored solution should satisfy the exact current equality, worst gap {pWorst:.2e}"

    # and the operating point must be PHYSICAL, which the cone gap alone does not say: recompute each branch flow from
    # the bus voltages and compare. Relaxed, the same case sits about 68 MW off the series relation; restored it is
    # within a watt. A tight cone with a wrong branch equation would pass the check above and fail this one.
    import openTEPES.openTEPES_NetworkMatrices as NM
    pP = pQ = 0.0
    for p, sc, n in mTEPES.psn:
        wP, wQ = NM.branch_residuals(mTEPES, mTEPES, p, sc, n)
        pP, pQ = max(pP, wP), max(pQ, wQ)
    assert pP < 1e-3 and pQ < 1e-3, f"the restored flows do not match the bus voltages: {pP:.5f} MW, {pQ:.5f} Mvar"


def test_the_b_matrix_leaves_out_the_dc_links():
    """The susceptance matrix is a Kirchhoff object. A point-to-point DC link carries what its converters are told to
    carry, so putting it in the matrix would make the model believe power splits across it by impedance."""
    import openTEPES.openTEPES_NetworkMatrices as NM
    mTEPES, _, _ = _build(CASES_DIR, "9n")
    p = mTEPES.p.first()

    pBranches = [la for la, *_ in NM.ac_branches(mTEPES, p)]
    assert pBranches, "no AC branches were found at all"
    assert set(pBranches) <= set(mTEPES.laa), "a branch outside the model's own AC set reached the matrix"
    assert not (set(pBranches) & (set(mTEPES.cd) | set(mTEPES.ed))), "a DC link reached the susceptance matrix"

    pBbus, pBf, _, _ = NM.b_matrices(mTEPES, p)
    # every row of Bbus sums to zero: a common angle shift moves no power
    assert abs(pBbus.sum(axis=1)).max() < 1e-9
    assert abs(pBbus - pBbus.T).max() < 1e-9, "the susceptance matrix must be symmetric"
    # every row of Bf sums to zero for the same reason
    assert abs(pBf.sum(axis=1)).max() < 1e-9


def test_the_ptdf_does_not_depend_on_the_reference_node():
    """The factors change with the reference; the FLOWS a balanced injection produces must not.

    This is the property that matters, and it catches an assembly error without needing a solve. Note that PTDF rows do
    NOT sum to zero: injecting one unit at every bus and withdrawing all of it at the reference is a balanced pattern
    that genuinely moves power towards the reference.
    """
    import openTEPES.openTEPES_NetworkMatrices as NM
    mTEPES, _, _ = _build(CASES_DIR, "9n")
    p = mTEPES.p.first()
    pNodes = list(mTEPES.nd)

    pRef = mTEPES.rf.first()
    pOther = next(nd for nd in pNodes if nd != pRef)
    pA = NM.ptdf(mTEPES, p, pSlack=pRef)
    pB = NM.ptdf(mTEPES, p, pSlack=pOther)
    assert all(nd != pRef   for (_, _, _, nd) in pA), "the reference node must carry no distribution factor"
    assert all(nd != pOther for (_, _, _, nd) in pB), "the reference node must carry no distribution factor"

    # a balanced injection: one unit in at the first bus, one unit out at the last
    pInj = {nd: 0.0 for nd in pNodes}
    pInj[pNodes[0]], pInj[pNodes[-1]] = 1.0, -1.0
    for la, *_ in NM.ac_branches(mTEPES, p):
        fA = sum(pA.get((la[0], la[1], la[2], nd), 0.0) * pInj[nd] for nd in pNodes)
        fB = sum(pB.get((la[0], la[1], la[2], nd), 0.0) * pInj[nd] for nd in pNodes)
        assert abs(fA - fB) < 1e-9, f"branch {la} flow moved with the reference node: {fA} vs {fB}"


# --------------------------------------------------------------------------------------------------------------------
# HVDC converters
# --------------------------------------------------------------------------------------------------------------------

def _case_with_built_dc(tmp_path, name, converter, hours=4):
    """9n_AC with its DC candidate forced into service, so a converter actually carries power.

    Left to itself the candidate is not built and the converter terms are all multiplied by a zero flow, which would
    let a broken converter model pass a test unnoticed.
    """
    dir_name, case = _tiny_ac_case(tmp_path, name, hours=hours, model_type=0, restore=0)
    net = os.path.join(dir_name, case, f"oT_Data_Network_{case}.csv")
    df  = pd.read_csv(net)
    dc  = df["LineType"] == "DC"
    assert dc.any(), "9n_AC is expected to ship a DC candidate"
    df.loc[dc, "InvestmentLo"] = 1.0                      # force it built
    df.loc[dc, "InvestmentUp"] = 1.0
    df.to_csv(net, index=False)

    opt = os.path.join(dir_name, case, f"oT_Data_Option_{case}.csv")
    d   = pd.read_csv(opt)
    d["IndACConverter"] = converter
    d.to_csv(opt, index=False)
    return dir_name, case


def test_converter_option_is_validated(tmp_path):
    dir_name, case = _clone(tmp_path, "9n_AC", "9n_badconv")
    opt = os.path.join(dir_name, case, f"oT_Data_Option_{case}.csv")
    df = pd.read_csv(opt); df["IndACConverter"] = 3; df.to_csv(opt, index=False)
    with pytest.raises(NotImplementedError, match="IndACConverter"):
        _build(dir_name, case)


def test_lcc_converter_draws_reactive_power_at_both_ends(tmp_path):
    """An LCC station is a reactive LOAD at each terminal, tan(acos(pf)) times the active power it transfers.

    Checked against the model rather than the solution: the two halves of |P_dc| must sum to the flow's magnitude, and
    the draw must appear at both ends of the link."""
    from openTEPES.openTEPES import openTEPES_run

    dir_name, case = _case_with_built_dc(tmp_path, "9n_lcc", converter=1)
    mTEPES = openTEPES_run(str(dir_name), case, "gurobi", 0, 0)

    assert hasattr(mTEPES, "vDCFlowPos"), "the LCC model must split the DC flow to reach |P|"
    pSeen = False
    for (p, sc, n, ni, nf, cc) in mTEPES.psnlad:
        pFlow = mTEPES.vFlowElec  [p, sc, n, ni, nf, cc]()
        pPos  = mTEPES.vDCFlowPos [p, sc, n, ni, nf, cc]()
        pNeg  = mTEPES.vDCFlowNeg [p, sc, n, ni, nf, cc]()
        assert pPos - pNeg == pytest.approx(pFlow, abs=1e-7), "the split must reproduce the flow"
        # Exact, because vDCFlowDir lets only one half be non-zero. An earlier version pinned only the difference and
        # this test asserted near-minimality, which nothing enforced: the pair could be inflated, and since the draw
        # enters the reactive balance with a minus, a node with surplus reactive power actively gains by inflating it.
        # The converter became a free reactive sink and the surplus vanished from the results.
        assert pPos + pNeg == pytest.approx(abs(pFlow), abs=1e-6), (
            f"pos+neg must be exactly |P|: |P| = {abs(pFlow)} but pos+neg = {pPos + pNeg}")
        if abs(pFlow) > 1e-6:
            pSeen = True
    assert pSeen, "the DC link carried no power, so this test proved nothing about the converter"


def test_vsc_converter_can_supply_reactive_power(tmp_path):
    """A VSC station is a controllable source or sink, so it must be able to take either sign, unlike an LCC."""
    from openTEPES.openTEPES import openTEPES_run

    dir_name, case = _case_with_built_dc(tmp_path, "9n_vsc", converter=2)
    mTEPES = openTEPES_run(str(dir_name), case, "gurobi", 0, 0)

    assert hasattr(mTEPES, "vQConvFrw"), "the VSC model must give each terminal a reactive variable"
    assert not hasattr(mTEPES, "vDCFlowPos"), "the VSC model has no need of the |P| split"
    for k in mTEPES.psnlad:
        lo, up = mTEPES.vQConvFrw[k].lb, mTEPES.vQConvFrw[k].ub
        assert lo is not None and lo < 0.0 < up, f"a VSC terminal must span zero, got [{lo}, {up}]"


def test_unbuilt_hvdc_candidate_is_not_a_free_statcom(tmp_path):
    """A converter on a link that was never built must supply no reactive power.

    Left ungated, vQConvFrw/Bck are bounded only by the converter rating, so the solver takes reactive support at both
    ends of a candidate it declines to build -- and then declines to build the shunts and condensers it really needs.
    The other VSC test forces the link into service, so it cannot see this."""
    from openTEPES.openTEPES import openTEPES_run

    dir_name, case = _tiny_ac_case(tmp_path, "9n_vscoff", model_type=0, restore=0)
    net = os.path.join(dir_name, case, f"oT_Data_Network_{case}.csv")
    df  = pd.read_csv(net)
    dc  = df["LineType"] == "DC"
    df.loc[dc, "InvestmentLo"] = 0.0
    df.loc[dc, "InvestmentUp"] = 0.0                      # forbid building it
    df.to_csv(net, index=False)
    opt = os.path.join(dir_name, case, f"oT_Data_Option_{case}.csv")
    d   = pd.read_csv(opt); d["IndACConverter"] = 2; d.to_csv(opt, index=False)

    mTEPES = openTEPES_run(str(dir_name), case, "gurobi", 0, 0)
    for k in mTEPES.psnlad:
        assert abs(mTEPES.vQConvFrw[k]()) < 1e-6, f"an unbuilt converter supplied {mTEPES.vQConvFrw[k]()} Gvar"
        assert abs(mTEPES.vQConvBck[k]()) < 1e-6, f"an unbuilt converter supplied {mTEPES.vQConvBck[k]()} Gvar"


def test_a_switchable_shunt_can_open_at_an_hour(tmp_path):
    """An existing shunt marked Switchable gets an hourly on/off state and is free to open.

    Without it an existing device is wired in permanently, so the only way to model a bank that must be out at light load was to delete it from the
    case, which also removes it at peak.
    """
    case_dir, case = _clone(tmp_path, "9n_AC", "9n_SWI")
    _edit_csv(case_dir, case, "BusShunt", lambda df: df.__setitem__("Switchable", [1, 0]))
    mTEPES = _build_with_vars(case_dir, case)

    assert list(mTEPES.shw) == ["Reactor_1"], "the marked device did not reach the switchable set"
    assert hasattr(mTEPES, "vShuntSwitch"), "no hourly state was created for a switchable shunt"
    assert len(mTEPES.vShuntSwitch) == len(mTEPES.psnshw) > 0

    for k in mTEPES.psnshw:
        assert k[3] == "Reactor_1"
        # the state has to reach zero, otherwise 'switchable' means nothing
        assert mTEPES.vShuntSwitch[k].lb == 0.0 and mTEPES.vShuntSwitch[k].ub == 1.0
        # and the injection range must contain zero, the same trap the candidate devices already avoid
        assert mTEPES.vQShunt[k].lb <= 0.0 <= mTEPES.vQShunt[k].ub, "an open shunt cannot inject zero"


def test_an_unmarked_shunt_keeps_no_hourly_state(tmp_path):
    """The default is unchanged: a case written before the column existed gets no state and no extra columns."""
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    assert len(mTEPES.shw) == 0
    assert not hasattr(mTEPES, "vShuntSwitch"), "an unmarked case paid for a switching variable"


def test_a_bank_of_units_becomes_one_device_per_unit(tmp_path):
    """Units = N expands a row into N identical devices and chains them, so the decision is how many are in service.

    Follows the VAR source model of Alvarez, Paredes and Rider: a bus carries an integer count of sources of fixed susceptance, not a continuous one.
    """
    case_dir, case = _clone(tmp_path, "9n_AC", "9n_BANK")

    def edit(df):
        df["Switchable"] = [0, 1]
        df["Units"] = [1, 4]                                  # the capacitor becomes a four unit bank
    _edit_csv(case_dir, case, "BusShunt", edit)
    mTEPES = _build_with_vars(case_dir, case)

    units = [sh for sh in mTEPES.sh if sh.startswith("Capacitor_1_u")]
    assert units == ["Capacitor_1_u1", "Capacitor_1_u2", "Capacitor_1_u3", "Capacitor_1_u4"]
    assert "Capacitor_1" not in list(mTEPES.sh), "the original row survived alongside its own units"
    assert len(mTEPES.sh) == 5, "one reactor plus four capacitor units"

    # every unit carries the FULL susceptance of one unit, not a share of the bank
    for u in units:
        assert mTEPES.pBusBshb[u]() == pytest.approx(0.3)

    # consecutive pairs only, so the chain is u1 -> u2 -> u3 -> u4 and not every combination
    assert sorted(tuple(x) for x in mTEPES.shp) == [
        ("Capacitor_1_u1", "Capacitor_1_u2"),
        ("Capacitor_1_u2", "Capacitor_1_u3"),
        ("Capacitor_1_u3", "Capacitor_1_u4"),
    ]


def test_a_bank_without_units_is_a_single_device(tmp_path):
    """The default is one unit, so a case written before the column existed is untouched."""
    mTEPES = _build_with_vars(CASES_DIR, "9n_AC")
    assert sorted(mTEPES.sh) == ["Capacitor_1", "Reactor_1"]
    assert len(mTEPES.shp) == 0


@pytest.mark.parametrize("case", ["RTS-GMLC_AC", "RTS-GMLC_AC_Oper"])
def test_the_rts_cases_carry_the_three_reactors_from_the_source_data(case):
    """RTS-GMLC puts a 100 Mvar reactor on buses 106, 206 and 306 and nothing anywhere else.

    They live in RTS_Data/SourceData/bus.csv under 'MVAR Shunt B', where the value is Mvar at one per unit voltage. On these cases' 100 MVA base that
    is Bshb = -1.0. Neither case carried a shunt table before, so the systems had no reactive compensation at all and the operating points they
    reported were not RTS-GMLC's.
    """
    mTEPES, _, _ = _build(CASES_DIR, case)

    assert sorted(mTEPES.sh) == ["Reactor_106", "Reactor_206", "Reactor_306"]
    assert mTEPES.pSBase == 0.1, "the conversion below assumes a 100 MVA base expressed in GVA"
    for sh in mTEPES.sh:
        assert mTEPES.pBusBshb[sh]() == pytest.approx(-1.0), "not the -100 Mvar the source data gives"
        assert mTEPES.pBusGshb[sh]() == 0.0, "the source data gives no shunt conductance"
        # they are fixed plant, not investment candidates and not switchable
        assert sh in mTEPES.she and sh not in mTEPES.shc and sh not in mTEPES.shw

    # -1.0 p.u. on a 100 MVA base is 100 Mvar absorbed at nominal voltage
    assert mTEPES.pBusBshb["Reactor_106"]() * mTEPES.pSBase * 1e3 == pytest.approx(-100.0)


# --------------------------------------------------------------------------------------------------------------------
# Computed power transfer distribution factors
# --------------------------------------------------------------------------------------------------------------------

def _ptdf_case(tmp_path, name, **options):
    """A 9n clone with the given Option flags, operation only so two runs compare like for like."""
    case_dir, case = _clone(tmp_path, "9n", name)
    def edit(df):
        for k, v in options.items():
            df[k] = v
    _edit_csv(case_dir, case, "Option", edit, index_col=None)
    return case_dir, case


def test_computed_ptdf_reproduces_the_dc_flows(tmp_path):
    """The criterion for the whole feature: on a fixed topology the computed factors must give the SAME flows as the
    angle formulation they stand in for. Anything else means the susceptance matrix disagrees with the constraint."""
    from openTEPES.openTEPES import openTEPES_run

    pCommon = dict(IndBinNetLosses=0, IndBinNetInvest=2, IndBinGenInvest=2)
    pDirA, pCaseA = _ptdf_case(tmp_path, "9n_ptdfA", IndPTDF=0, **pCommon)
    pDirB, pCaseB = _ptdf_case(tmp_path, "9n_ptdfB", IndPTDF=2, **pCommon)

    mA = openTEPES_run(pDirA, pCaseA, "gurobi", 0, 0)
    mB = openTEPES_run(pDirB, pCaseB, "gurobi", 0, 0)

    assert mB.pIndPTDF() == 2 and hasattr(mB, "pPTDFCalc"), "the computed factors were never built"
    # not indexed by load level: the topology is fixed for a period, so an hourly index would repeat itself
    assert all(len(k) == 5 for k in mB.pland), "the computed factors should carry no load level index"

    pWorst = max(abs(mA.vFlowElec[k]() - mB.vFlowElec[k]()) for k in mA.psnla if k in mB.psnla) * 1e3
    assert pWorst < 1e-6, f"computed PTDF moved the flows by {pWorst:.6f} MW against the angle formulation"
    assert abs(mA.vTotalSCost() - mB.vTotalSCost()) < 1e-9


def test_computed_ptdf_is_refused_when_the_topology_can_change(tmp_path):
    """A PTDF matrix belongs to one topology. A candidate or switchable AC line can change it, and the factors would
    then be stale in a way nothing detects, so the combination is refused rather than approximated."""
    from openTEPES.openTEPES import openTEPES_run

    case_dir, case = _ptdf_case(tmp_path, "9n_ptdfC", IndPTDF=2, IndBinNetLosses=0)

    # Make one AC line a candidate. BOTH columns matter: the model's cost is FixedInvestmentCost * FixedChargeRate, so
    # setting the cost alone leaves it at zero and the line stays existing.
    def edit(df):
        pAC = [i for i in df.index if str(df.loc[i, "LineType"]).upper() != "DC"]
        df.loc[:, "FixedInvestmentCost"] = 0.0
        df.loc[:, "FixedChargeRate"]     = 0.0
        df.loc[pAC[0], "FixedInvestmentCost"] = 1.0
        df.loc[pAC[0], "FixedChargeRate"]     = 0.1
    _edit_csv(case_dir, case, "Network", edit, index_col=None)

    with pytest.raises(ValueError, match="one fixed topology"):
        openTEPES_run(case_dir, case, "gurobi", 0, 0)


def test_ptdf_flag_and_table_must_agree(tmp_path):
    """Asking to read factors that are not there, or to compute factors beside a table, is an error rather than a
    silent precedence rule. The old behaviour, where the table's presence alone decided, stays the default."""
    case_dir, case = _ptdf_case(tmp_path, "9n_ptdfD", IndPTDF=1, IndBinNetLosses=0)
    with pytest.raises(ValueError, match="no such table"):
        _build(case_dir, case)


# --------------------------------------------------------------------------------------------------------------------
# How the problem is solved, and how conflicting options are reported
# --------------------------------------------------------------------------------------------------------------------

def test_the_execution_flags_come_from_the_case(tmp_path):
    """These four were literals in openTEPES.py, so none of the four stage-solving strategies could be selected."""
    from openTEPES.openTEPES import openTEPES_run

    case_dir, case = _ptdf_case(tmp_path, "9n_exec", IndSequentialSolving=2, IndCompleteProblem=1)
    mTEPES = openTEPES_run(case_dir, case, "gurobi", 0, 0)
    assert mTEPES.pIndSequentialSolving() == 2, "the case's choice of stage solving did not reach the model"


def test_a_stage_solving_strategy_outside_the_four_is_refused(tmp_path):
    """The flag used to be declared Binary while its own code branched on four values."""
    case_dir, case = _ptdf_case(tmp_path, "9n_exec2", IndSequentialSolving=7)
    with pytest.raises(NotImplementedError, match="IndSequentialSolving"):
        _build(case_dir, case)


def test_incompatible_options_are_reported_together(tmp_path):
    """One conflict at a time meant fixing one and being told about the next. All of them are collected instead."""
    from openTEPES.openTEPES import openTEPES_run

    case_dir, case = _clone(tmp_path, "9n_AC", "9n_clash")
    _edit_csv(case_dir, case, "Option", lambda df: (df.__setitem__("IndBinSingleNode", 1),
                                                    df.__setitem__("IndPTDF", 2)), index_col=None)
    with pytest.raises(ValueError) as e:
        openTEPES_run(case_dir, case, "gurobi", 0, 0)

    pText = str(e.value)
    assert "IndBinSingleNode" in pText and "IndPTDF" in pText, "only one of the two conflicts was reported"
    assert "1." in pText and "2." in pText, "the conflicts were not listed"


@pytest.mark.parametrize("pf, mt, cyc, solver", [
    (1, 0, 0, "gurobi"),   # branch flow, second-order cone
    (1, 1, 0, "gurobi"),   # branch flow, piecewise linear
    (1, 2, 0, "ipopt"),    # branch flow, exact
    (2, 0, 0, "ipopt"),    # bus injection in W space
    (2, 0, 1, "ipopt"),    # bus injection in W space with the loop condition
    (3, 0, 0, "ipopt"),    # bus injection in rectangular coordinates
])
def test_every_formulation_solves_and_writes_its_results(tmp_path, pf, mt, cyc, solver):
    """Each formulation end to end, solve and output, not just built.

    Every AC solve test before this one used branch flow. That left the writers untested for the bus injection
    formulations, and one of them crashed: in W space without the loop condition vTheta is declared but constrained by
    nothing, so the solver leaves it unset and the power flow residual tried to build a phasor from None.
    """
    from openTEPES.openTEPES import openTEPES_run

    dir_name, case = _tiny_ac_case(tmp_path, f"9n_f{pf}{mt}{cyc}", hours=2, model_type=mt, restore=0)
    _edit_csv(dir_name, case, "Option", lambda df: (df.__setitem__("IndACPowerFlow", pf),
                                                    df.__setitem__("IndACCycle", cyc)), index_col=None)
    mTEPES = openTEPES_run(dir_name, case, solver, 0, 0)

    assert mTEPES.pIndACPowerFlow() == pf
    assert mTEPES.vTotalSCost() > 0.0, "the solve returned no cost"


