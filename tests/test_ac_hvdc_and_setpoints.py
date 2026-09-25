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
