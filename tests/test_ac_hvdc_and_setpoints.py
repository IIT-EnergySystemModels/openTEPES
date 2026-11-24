"""AC checks for a network with an HVDC scheme, and for per-bus voltage limits.

Three things these cover, all of which a real transmission case runs into and 9n_AC as bundled does
not:

  * a node that no AC branch touches -- an HVDC pole, or a border stub reached only by a link -- has
    no voltage angle, and the residual check has to tolerate that rather than switch itself off;
  * the angle writer meets the same node and must leave a blank rather than claim it sits on the
    reference;
  * a case that records the voltage a machine holds its busbar at needs somewhere to put it.

The model is built to DataConfiguration and the variables are set by hand, so none of this needs a
solver.
"""
import os
import shutil

import pandas as pd
import pytest
from pyomo.environ import ConcreteModel, SolverFactory

from openTEPES.openTEPES_DataConfiguration import DataConfiguration, angles_available
from openTEPES.openTEPES_InputData import InputData
from openTEPES.openTEPES_ProblemSolvingTuning import apply_solver_options
from openTEPES.openTEPES_SettingUpVariables import SettingUpVariables

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def _clone(tmp_path, source_case, new_name):
    case_dir = tmp_path / new_name
    shutil.copytree(os.path.join(CASES_DIR, source_case), case_dir)
    for f in os.listdir(case_dir):
        if source_case in f:
            os.rename(case_dir / f, case_dir / f.replace(source_case, new_name))
    return str(tmp_path), new_name


def _build(dir_name, case_name, with_vars=False):
    mTEPES = ConcreteModel(case_name)
    dfs, par = InputData(dir_name, case_name, mTEPES, 0)
    DataConfiguration(mTEPES, dfs, par)
    if with_vars:
        SettingUpVariables(mTEPES, mTEPES)
    return mTEPES, dfs, par


def _write(case_dir, case_name, stem, frame):
    frame.to_csv(os.path.join(case_dir, case_name, f"oT_Data_{stem}_{case_name}.csv"), index=False)


def _with_dc_only_node(tmp_path, name, node="DCpole"):
    """9n_AC with one more node, reached by a DC branch and by nothing else.

    That is the shape every HVDC scheme puts in a case: the pole is a node of the model and carries
    no AC branch, so it has no voltage angle to report.
    """
    d, n = _clone(tmp_path, "9n_AC", name)
    case_dir = os.path.join(d, n)

    nodes = pd.read_csv(os.path.join(case_dir, f"oT_Dict_Node_{n}.csv"))
    nodes.loc[len(nodes)] = [node]
    nodes.to_csv(os.path.join(case_dir, f"oT_Dict_Node_{n}.csv"), index=False)

    zones = pd.read_csv(os.path.join(case_dir, f"oT_Dict_NodeToZone_{n}.csv"))
    zones.loc[len(zones)] = [node, zones.iloc[0, 1]]
    zones.to_csv(os.path.join(case_dir, f"oT_Dict_NodeToZone_{n}.csv"), index=False)

    loc = pd.read_csv(os.path.join(case_dir, f"oT_Data_NodeLocation_{n}.csv"))
    loc.loc[len(loc)] = [node, 0.0, 0.0]
    loc.to_csv(os.path.join(case_dir, f"oT_Data_NodeLocation_{n}.csv"), index=False)

    demand = pd.read_csv(os.path.join(case_dir, f"oT_Data_Demand_{n}.csv"))
    demand[node] = 0.0
    demand.to_csv(os.path.join(case_dir, f"oT_Data_Demand_{n}.csv"), index=False)

    reactive = os.path.join(case_dir, f"oT_Data_ReactiveDemand_{n}.csv")
    if os.path.exists(reactive):
        frame = pd.read_csv(reactive)
        frame[node] = 0.0
        frame.to_csv(reactive, index=False)

    network = pd.read_csv(os.path.join(case_dir, f"oT_Data_Network_{n}.csv"))
    link = network.iloc[0].copy()
    link["InitialNode"], link["FinalNode"], link["LineType"] = network.iloc[0]["InitialNode"], node, "DC"
    network.loc[len(network)] = link
    network.to_csv(os.path.join(case_dir, f"oT_Data_Network_{n}.csv"), index=False)
    return d, n


# --------------------------------------------------------------------------------------------------------------------
# A node with no AC branch
# --------------------------------------------------------------------------------------------------------------------

def test_angles_available_tolerates_a_node_with_no_ac_branch(tmp_path):
    """The residual check stays on when an HVDC pole carries no angle.

    vTheta is set at every node an AC branch touches and left unset at the pole, which is what a
    solver returns: the pole's angle appears in no constraint, so nothing determines it. Requiring
    one there turned the check off for any case with an HVDC scheme in it.
    """
    d, n = _with_dc_only_node(tmp_path, "9n_AC_pole")
    mTEPES, _, _ = _build(d, n, with_vars=True)

    branches = mTEPES.laa
    touched = {nd for la in branches for nd in (la[0], la[1])}
    assert "DCpole" not in touched, "the added node must carry no AC branch"

    first = next(iter(mTEPES.psn))
    for p, sc, nn, nd in mTEPES.psnnd:
        if (p, sc, nn) == first:
            mTEPES.vTheta[p, sc, nn, nd].value = 0.0 if nd in touched else None

    assert angles_available(mTEPES, mTEPES, *first)


def test_rectangular_model_fixes_an_angle_in_every_synchronous_area(tmp_path):
    """A node no AC branch reaches gets an angle reference of its own in rectangular coordinates.

    Only the reference node had one. Rotating the voltage of the pole changes no flow, so the pole's angle was a free direction
    of the NLP and Ipopt met a singular problem. The angle is fixed at zero and the magnitude stays free within the band.
    """
    d, n = _with_dc_only_node(tmp_path, "9n_AC_pole_rect")
    opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
    opt["IndACPowerFlow"] = 3
    _write(d, n, "Option", opt)
    mTEPES, _, _ = _build(d, n, with_vars=True)

    ref = mTEPES.rf.first()
    for p, sc, nn in mTEPES.psn:
        assert mTEPES.vVim[p, sc, nn, "DCpole"].fixed and mTEPES.vVim[p, sc, nn, "DCpole"].value == 0.0
        assert not mTEPES.vVre[p, sc, nn, "DCpole"].fixed
        assert mTEPES.vVre[p, sc, nn, "DCpole"].lb == pytest.approx(mTEPES.pVMinBus["DCpole"])
        # the rest of 9n_AC is one synchronous area with the reference node: no other angle is fixed
        assert {nd for nd in mTEPES.nd if mTEPES.vVim[p, sc, nn, nd].fixed} == {ref, "DCpole"}


def _with_dc_only_area(tmp_path, name):
    """9n_AC with buses 7, 8 and 9 joined to the rest only through DC: the three AC branches that cross over are made DC.

    That is the shape of an AC area behind HVDC, such as Western Denmark in a Nordic case. Inside the area 7-8 and 8-9 stay AC,
    so bus 8 has the most AC branches there and is the anchor."""
    d, n = _clone(tmp_path, "9n_AC", name)
    net = pd.read_csv(os.path.join(d, n, f"oT_Data_Network_{n}.csv"))
    cut = {("Node_6", "Node_7"), ("Node_6", "Node_8"), ("Node_4", "Node_9")}
    net.loc[[(a, b) in cut for a, b in zip(net.InitialNode, net.FinalNode)], "LineType"] = "DC"
    _write(d, n, "Network", net)
    opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
    opt["IndACPowerFlow"] = 3
    _write(d, n, "Option", opt)
    return d, n


def test_an_area_behind_hvdc_is_anchored_at_its_best_connected_bus(tmp_path):
    """One angle per area: bus 8 is fixed, buses 7 and 9 stay free, and the area is found again with the same anchor."""
    from openTEPES.openTEPES_ModelFormulationElectricity import _SynchronousAreaAnchors

    d, n = _with_dc_only_area(tmp_path, "9n_AC_area_build")
    mTEPES, _, _ = _build(d, n, with_vars=True)
    assert mTEPES.rf.first() == "Node_4"
    for p in mTEPES.p:
        assert _SynchronousAreaAnchors(mTEPES, p) == {"Node_8": ["Node_7", "Node_8", "Node_9"]}
    for p, sc, nn in mTEPES.psn:
        assert {nd for nd in mTEPES.nd if mTEPES.vVim[p, sc, nn, nd].fixed} == {"Node_4", "Node_8"}


def test_rotating_an_area_to_its_anchor_changes_no_flow(tmp_path):
    """The cone start rotates each area so that its anchor has angle zero. The magnitudes and every V_i conj(V_j), which
    is all a flow depends on, stay as they were, and the anchor angle is fixed again."""
    import cmath
    from openTEPES.openTEPES_ModelFormulationElectricity import _AnchorAreaAngles, _SynchronousAreaAnchors

    d, n = _with_dc_only_area(tmp_path, "9n_AC_area_rotate")
    mTEPES, _, _ = _build(d, n, with_vars=True)
    p, sc, _ = next(iter(mTEPES.psn))
    pAnchors = _SynchronousAreaAnchors(mTEPES, p)
    pStart = {"Node_7": cmath.rect(1.02, 0.31), "Node_8": cmath.rect(0.99, 0.42), "Node_9": cmath.rect(1.01, 0.37)}
    for nn in mTEPES.n:
        mTEPES.vVim[p, sc, nn, "Node_8"].unfix()
        for nd, v in pStart.items():
            mTEPES.vVre[p, sc, nn, nd].set_value(v.real)
            mTEPES.vVim[p, sc, nn, nd].set_value(v.imag)

    _AnchorAreaAngles(mTEPES, mTEPES, p, sc, pAnchors)

    for nn in mTEPES.n:
        V = {nd: complex(mTEPES.vVre[p, sc, nn, nd].value, mTEPES.vVim[p, sc, nn, nd].value) for nd in pStart}
        assert mTEPES.vVim[p, sc, nn, "Node_8"].fixed and mTEPES.vVim[p, sc, nn, "Node_8"].value == 0.0
        assert V["Node_8"].real == pytest.approx(0.99)
        for i in pStart:
            assert abs(V[i]) == pytest.approx(abs(pStart[i]))
            for j in pStart:
                assert V[i] * V[j].conjugate() == pytest.approx(pStart[i] * pStart[j].conjugate())


@pytest.mark.solve
def test_an_area_behind_hvdc_reaches_the_same_optimum_from_every_start(tmp_path):
    """The flat start, the cone start and the power flow start all reach one optimum on a case with an AC area behind HVDC,
    and the anchor ends the solve with angle zero. The two cone starts free the anchor angle and fix it again."""
    if not SolverFactory("ipopt").available(exception_flag=False):
        pytest.skip("ipopt is not available")
    from openTEPES.openTEPES import openTEPES_run

    pCost = {}
    for pStart in (0, 1, 2):
        d, n = _with_dc_only_area(tmp_path / f"s{pStart}", f"9n_AC_area_start{pStart}")
        _first_hours(d, n, hours=2)
        opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
        opt["IndACConeStart"] = pStart
        _write(d, n, "Option", opt)
        try:
            mTEPES = openTEPES_run(d, n, "ipopt", pIndOutputResults=0, pIndLogConsole=0)
        except Exception as e:
            if "size-limited" in str(e) or "too large" in str(e).lower():
                pytest.skip("the solver licence cannot take a model this size")
            raise
        pCost[pStart] = mTEPES.vTotalSCost()
        for p, sc, nn in mTEPES.psn:
            assert mTEPES.vVim[p, sc, nn, "Node_8"].fixed and mTEPES.vVim[p, sc, nn, "Node_8"].value == 0.0
            assert mTEPES.vVre[p, sc, nn, "Node_8"].value >= mTEPES.pVMinBus["Node_8"] - 1e-6
    for pStart in (1, 2):
        assert pCost[pStart] == pytest.approx(pCost[0], rel=1e-4), f"start {pStart} gives {pCost[pStart]}, the flat start {pCost[0]}"


def test_angles_available_still_refuses_an_unset_ac_node(tmp_path):
    """A node that an AC branch does touch must still carry an angle.

    Without this the relaxation could hand back a phasor built from a missing value, which is the
    intermittent crash the every-node rule was written to stop.
    """
    d, n = _with_dc_only_node(tmp_path, "9n_AC_pole_gap")
    mTEPES, _, _ = _build(d, n, with_vars=True)

    touched = {nd for la in mTEPES.laa for nd in (la[0], la[1])}
    first = next(iter(mTEPES.psn))
    blank = sorted(touched)[0]
    for p, sc, nn, nd in mTEPES.psnnd:
        if (p, sc, nn) == first:
            mTEPES.vTheta[p, sc, nn, nd].value = None if nd == blank else 0.0

    assert not angles_available(mTEPES, mTEPES, *first)


# --------------------------------------------------------------------------------------------------------------------
# Per-bus voltage limits
# --------------------------------------------------------------------------------------------------------------------

def test_bus_voltage_table_pins_the_named_busbars(tmp_path):
    """Equal limits hold a busbar, and the rest of the system keeps its own band."""
    d, n = _clone(tmp_path, "9n_AC", "9n_AC_setpoint")
    nodes = pd.read_csv(os.path.join(d, n, f"oT_Dict_Node_{n}.csv")).iloc[:, 0].astype(str).tolist()
    held, free = nodes[0], nodes[1]
    _write(os.path.join(d), n, "BusVoltage",
           pd.DataFrame({"Node": [held], "VMin": [1.023], "VMax": [1.023]}))

    mTEPES, _, par = _build(d, n)
    assert par["pVMinBus"][held] == pytest.approx(1.023)
    assert par["pVMaxBus"][held] == pytest.approx(1.023)
    assert par["pVMinBus"][free] < par["pVMaxBus"][free], "an unnamed busbar keeps a band"


def test_bus_voltage_table_is_ignored_on_a_dc_run(tmp_path):
    """Carrying the table costs a DC case nothing, as with the other AC-only tables."""
    d, n = _clone(tmp_path, "9n", "9n_with_bus_voltage")
    nodes = pd.read_csv(os.path.join(d, n, f"oT_Dict_Node_{n}.csv")).iloc[:, 0].astype(str).tolist()
    _write(os.path.join(d), n, "BusVoltage",
           pd.DataFrame({"Node": [nodes[0]], "VMin": [0.5], "VMax": [0.5]}))

    mTEPES, dfs, par = _build(d, n)
    assert mTEPES.pIndACPowerFlow() == 0
    assert "dfBusVoltage" not in dfs
    assert "pVMinBus" not in par


def _with_setpoint(tmp_path, name, cost, vset=1.0):
    """9n_AC with one busbar given a voltage setpoint, and a price on its distance from it."""
    d, n = _clone(tmp_path, "9n_AC", name)
    nodes = pd.read_csv(os.path.join(d, n, f"oT_Dict_Node_{n}.csv")).iloc[:, 0].astype(str).tolist()
    ref = pd.read_csv(os.path.join(d, n, f"oT_Data_Parameter_{n}.csv"))["ReferenceNode"].iloc[0]
    bus = next(nd for nd in nodes if nd != ref)
    _write(os.path.join(d), n, "BusVoltage", pd.DataFrame({"Node": [bus], "VSet": [vset]}))
    param = pd.read_csv(os.path.join(d, n, f"oT_Data_Parameter_{n}.csv"))
    param["VoltageDeviationCost"] = cost
    _write(os.path.join(d), n, "Parameter", param)
    return d, n, bus


def test_a_voltage_setpoint_is_read_with_its_price(tmp_path):
    """VSet reaches the model as a setpoint, and the price arrives in MEUR per p.u. per hour."""
    d, n, bus = _with_setpoint(tmp_path, "9n_AC_vset", cost=1000.0, vset=1.01)
    mTEPES, _, par = _build(d, n, with_vars=True)
    assert list(mTEPES.ndv) == [bus]
    assert mTEPES.pVSetBus[bus] == pytest.approx(1.01)
    assert mTEPES.pVoltageDeviationCost() == pytest.approx(1000.0 * 1e-6)
    assert hasattr(mTEPES, "vVoltageDevUp") and hasattr(mTEPES, "vTotalVPenalty")
    assert par["pVMinBus"][bus] < par["pVMaxBus"][bus], "a setpoint alone leaves the band as it was"


def test_a_setpoint_without_a_price_builds_the_same_model(tmp_path):
    """No price, no columns: a case that names setpoints but does not price them is unchanged."""
    d, n, _ = _with_setpoint(tmp_path, "9n_AC_vset_free", cost=0.0)
    mTEPES, _, _ = _build(d, n, with_vars=True)
    assert not hasattr(mTEPES, "vVoltageDevUp")
    assert not hasattr(mTEPES, "vTotalVPenalty")


def test_a_negative_voltage_price_is_refused(tmp_path):
    """The price is checked after the case's scalars are read, so the case's own value is what gets checked."""
    d, n, _ = _with_setpoint(tmp_path, "9n_AC_vset_negative", cost=-1.0)
    with pytest.raises(ValueError, match="VoltageDeviationCost"):
        _build(d, n)


@pytest.mark.solve
def test_a_priced_setpoint_holds_its_busbar(tmp_path):
    """With the price on, the busbar keeps to its setpoint; without it, the same busbar sits elsewhere in its band.

    The setpoint is 1.0 p.u., which the busbar holds. Given 1.02 instead, with the default current price, it settles at
    1.006 on average: the price is a soft target, weighed against the rest of the objective, and a setpoint it only
    partly reaches would make this test about that trade-off rather than about the term.
    """
    from openTEPES.openTEPES import openTEPES_run
    if not SolverFactory("gurobi").available(exception_flag=False):
        pytest.skip("gurobi is not available")

    def distance(cost):
        d, n, bus = _with_setpoint(tmp_path / f"c{int(cost)}", "9n_AC_vset_solve", cost=cost, vset=1.0)
        try:
            openTEPES_run(d, n, "gurobi", pIndOutputResults=1, pIndLogConsole=0)
        except Exception as e:
            if "size-limited" in str(e) or "too large" in str(e).lower():
                pytest.skip("gurobi licence cannot take a model this size")
            raise
        v = pd.read_csv(os.path.join(d, n, f"oT_Result_NetworkVoltageMagnitude_{n}.csv"))
        return float((v[bus] - 1.0).abs().mean())

    assert distance(1e6) < 1e-4, "a priced busbar should keep to its setpoint"
    assert distance(0.0) > 1e-3, "without the price the busbar should sit elsewhere, or the test says nothing"


# --------------------------------------------------------------------------------------------------------------------
# Apparent power limit at both ends of a branch
# --------------------------------------------------------------------------------------------------------------------

def _with_apparent_limit(tmp_path, name, value):
    """9n_AC with IndACApparentPowerLimit set in oT_Data_Option."""
    d, n = _clone(tmp_path, "9n_AC", name)
    opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
    opt["IndACApparentPowerLimit"] = value
    _write(d, n, "Option", opt)
    return d, n


def test_apparent_power_limit_is_off_by_default_and_validated(tmp_path):
    """Off by default; values other than 0 and 1 are refused."""
    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    assert mTEPES.pIndACApparentPowerLimit() == 0
    d, n = _with_apparent_limit(tmp_path, "9n_AC_apl_bad", 2)
    with pytest.raises(NotImplementedError, match="IndACApparentPowerLimit"):
        _build(d, n)


@pytest.mark.solve
def test_apparent_power_limit_holds_every_branch_within_its_rating(tmp_path):
    """Without the option a branch exceeds its rating; with it, none does."""
    from openTEPES.openTEPES import openTEPES_run
    if not SolverFactory("gurobi").available(exception_flag=False):
        pytest.skip("gurobi is not available")

    def largest_loading(value):
        d, n = _with_apparent_limit(tmp_path / f"v{value}", "9n_AC_apl", value)
        try:
            openTEPES_run(d, n, "gurobi", pIndOutputResults=1, pIndLogConsole=0)
        except Exception as e:
            if "size-limited" in str(e) or "too large" in str(e).lower():
                pytest.skip("gurobi licence cannot take a model this size")
            raise
        u = pd.read_csv(os.path.join(d, n, f"oT_Result_NetworkElecUtilizationAC_{n}.csv"), header=[0, 1, 2], index_col=[0, 1, 2])
        return float(u.max().max())

    assert largest_loading(0) > 101.0, "without the option a branch should exceed its rating"
    assert largest_loading(1) <= 100.0 + 1e-4


@pytest.mark.solve
def test_apparent_power_limit_survives_the_ac_recovery_step(tmp_path):
    """The recovery step swaps in the circle and keeps every branch within its rating. 12 hours: ipopt does not converge on the full year."""
    from openTEPES.openTEPES import openTEPES_run
    if not SolverFactory("gurobi").available(exception_flag=False) or not SolverFactory("ipopt").available(exception_flag=False):
        pytest.skip("gurobi and ipopt are needed")

    def largest_loading(value):
        d, n = _with_apparent_limit(tmp_path / f"v{value}", "9n_AC_apl_restore", value)
        dur = pd.read_csv(os.path.join(d, n, f"oT_Data_Duration_{n}.csv"))
        keep, full = set(dur.loc[:11, "LoadLevel"]), len(dur)
        for f in os.listdir(os.path.join(d, n)):
            path = os.path.join(d, n, f)
            if f.endswith(".csv") and "LoadLevel" in (df := pd.read_csv(path)).columns:
                df[df["LoadLevel"].isin(keep)].to_csv(path, index=False)
        res = pd.read_csv(os.path.join(d, n, f"oT_Data_RESEnergy_{n}.csv"))
        res["RESEnergy"] = pd.to_numeric(res["RESEnergy"], errors="coerce").fillna(0.0) * 12 / full
        _write(d, n, "RESEnergy", res)
        opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
        opt["IndACRestore"] = 1
        _write(d, n, "Option", opt)
        try:
            model = openTEPES_run(d, n, "gurobi", pIndOutputResults=1, pIndLogConsole=0)
        except Exception as e:
            if "size-limited" in str(e) or "too large" in str(e).lower():
                pytest.skip("gurobi licence cannot take a model this size")
            raise
        assert any(c.name.startswith("eApparentRestoredFrw") for c in model.component_objects()) == bool(value)
        u = pd.read_csv(os.path.join(d, n, f"oT_Result_NetworkElecUtilizationAC_{n}.csv"), header=[0, 1, 2], index_col=[0, 1, 2])
        return float(u.max().max())

    assert largest_loading(0) > 101.0, "without the option a branch should exceed its rating"
    assert largest_loading(1) <= 100.0 + 1e-3


def _first_hours(d, n, hours=12):
    """Keep the first hours of a case and scale the RES energy target to them."""
    dur = pd.read_csv(os.path.join(d, n, f"oT_Data_Duration_{n}.csv"))
    keep, full = set(dur.loc[:hours - 1, "LoadLevel"]), len(dur)
    for f in os.listdir(os.path.join(d, n)):
        path = os.path.join(d, n, f)
        if f.endswith(".csv") and "LoadLevel" in (df := pd.read_csv(path)).columns:
            df[df["LoadLevel"].isin(keep)].to_csv(path, index=False)
    res = pd.read_csv(os.path.join(d, n, f"oT_Data_RESEnergy_{n}.csv"))
    res["RESEnergy"] = pd.to_numeric(res["RESEnergy"], errors="coerce").fillna(0.0) * hours / full
    _write(d, n, "RESEnergy", res)


@pytest.mark.solve
@pytest.mark.parametrize("mode, cycle", [(3, 0), (2, 1)])
def test_apparent_power_limit_holds_in_bus_injection(tmp_path, mode, cycle):
    """The option limits both ends in bus injection solved as a non-linear program: rectangular coordinates, and W space with
    the loop condition. Before, it was applied in branch flow only, and a bus-injection branch could exceed its rating.
    12 hours: ipopt does not converge on the full year."""
    solver = "ipopt"
    from openTEPES.openTEPES import openTEPES_run
    if not SolverFactory(solver).available(exception_flag=False):
        pytest.skip(f"{solver} is not available")

    def largest_loading(value):
        d, n = _with_apparent_limit(tmp_path / f"m{mode}c{cycle}v{value}", f"9n_AC_apl_bim{mode}", value)
        _first_hours(d, n)
        opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
        opt["IndACPowerFlow"] = mode
        opt["IndACCycle"] = cycle
        _write(d, n, "Option", opt)
        try:
            model = openTEPES_run(d, n, solver, pIndOutputResults=1, pIndLogConsole=0)
        except Exception as e:
            if "size-limited" in str(e) or "too large" in str(e).lower():
                pytest.skip(f"{solver} licence cannot take a model this size")
            raise
        assert any(c.name.startswith("eApparentLimitBck") for c in model.component_objects()) == bool(value)
        u = pd.read_csv(os.path.join(d, n, f"oT_Result_NetworkElecUtilizationAC_{n}.csv"), header=[0, 1, 2], index_col=[0, 1, 2])
        return float(u.max().max())

    assert largest_loading(0) > 101.0, "without the option a branch should exceed its rating"
    assert largest_loading(1) <= 100.0 + 1e-3


@pytest.mark.solve
def test_apparent_power_limit_is_not_applied_in_the_w_space_cone(tmp_path, capsys):
    """In the W-space cone the option is reported as not applied, not silently ignored."""
    from openTEPES.openTEPES import openTEPES_run
    if not SolverFactory("gurobi").available(exception_flag=False):
        pytest.skip("gurobi is not available")
    d, n = _with_apparent_limit(tmp_path, "9n_AC_apl_cone", 1)
    _first_hours(d, n)
    opt = pd.read_csv(os.path.join(d, n, f"oT_Data_Option_{n}.csv"))
    opt["IndACPowerFlow"] = 2
    _write(d, n, "Option", opt)
    try:
        model = openTEPES_run(d, n, "gurobi", pIndOutputResults=0, pIndLogConsole=0)
    except Exception as e:
        if "size-limited" in str(e) or "too large" in str(e).lower():
            pytest.skip("gurobi licence cannot take a model this size")
        raise
    assert "not applied in the W-space cone" in capsys.readouterr().out
    assert not any(c.name.startswith("eApparentLimit") for c in model.component_objects())


# --------------------------------------------------------------------------------------------------------------------
# Duals on a quadratically constrained model
# --------------------------------------------------------------------------------------------------------------------

def test_gurobi_is_asked_for_duals_on_an_ac_run():
    """An AC model is quadratically constrained, and Gurobi withholds duals unless asked.

    Without this a case with no integer variable attaches the dual suffix, solves to optimality and
    then fails retrieving Pi, with the solver log still reporting success. The locational prices an
    AC case exists to produce come from those duals.
    """
    mTEPES, _, _ = _build(CASES_DIR, "9n_AC")
    solver = SolverFactory("gurobi")
    apply_solver_options(solver, "gurobi", "unused.log", 1, mTEPES)
    assert solver.options.get("QCPDual") == 1


def test_gurobi_is_not_asked_for_duals_on_a_dc_run():
    mTEPES, _, _ = _build(CASES_DIR, "9n")
    solver = SolverFactory("gurobi")
    apply_solver_options(solver, "gurobi", "unused.log", 1, mTEPES)
    assert solver.options.get("QCPDual") is None
