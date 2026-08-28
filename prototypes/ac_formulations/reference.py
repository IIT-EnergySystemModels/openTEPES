"""Ground truth for the formulation study, via pandapower.

Two references, and they answer different questions:

  * ``true_acopf(snap)`` solves the exact non-convex AC OPF with pandapower's interior-point solver.
    This is the answer every prototype is trying to approximate: it gives the true optimal cost, the
    true dispatch, and the true voltage profile.

  * ``ac_powerflow(snap, dispatch)`` fixes the generator active powers to what a prototype decided and
    solves an exact Newton-Raphson AC power flow. This answers the question that matters for a planning
    model: *given the decision this formulation made, what does the network actually do?* The gap
    between what the prototype predicted and what the power flow returns is the physical error the
    formulation introduces, and it is not the same thing as the optimality gap.

The per-unit to engineering-unit conversion follows the case: Zbase = kV^2 / SBase per branch, and the
total charging susceptance b_pu is split into the pi model's two ends by pandapower itself.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
import pandapower as pp

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


def build_net(snap, *, with_costs: bool = True):
    """Translate a Snapshot into a pandapower network. Returns (net, bus_index_by_name)."""
    net = pp.create_empty_network(sn_mva=snap.sbase_mva, f_hz=50.0)

    # One nominal voltage for the whole network, and therefore one impedance base. The study compares network
    # formulations in per unit, where the physical kV never enters: impedances are already per unit and thermal
    # limits are expressed in MVA. Carrying two voltage levels would force transformers to be modelled as
    # transformers rather than branches, which is a separate question from the one being asked here. The cost is
    # that off-nominal taps are dropped — for every formulation equally.
    kv = float(snap.branches["kv"].mode().iloc[0])

    bx = {}
    for b in snap.buses:
        bx[b] = pp.create_bus(net, vn_kv=kv, name=b, min_vm_pu=snap.vmin, max_vm_pu=snap.vmax)

    for (ni, nf, cc), row in snap.branches.iterrows():
        zbase = (kv ** 2) / snap.sbase_mva
        # b_pu is the TOTAL pi-model charging susceptance; C = B / (Zbase * 2*pi*f)
        c_nf = row.b_pu / (zbase * 2 * math.pi * net.f_hz) * 1e9
        imax_ka = row.s_mva / (math.sqrt(3) * kv)
        li = pp.create_line_from_parameters(
            net, from_bus=bx[ni], to_bus=bx[nf], length_km=1.0,
            r_ohm_per_km=row.r_pu * zbase, x_ohm_per_km=row.x_pu * zbase,
            c_nf_per_km=max(c_nf, 0.0), max_i_ka=imax_ka, name=f"{ni}-{nf}-{cc}")
        # pandapower's OPF ignores the current rating unless max_loading_percent is set. Without this the
        # reference would be solving an unconstrained network while every prototype respects the ratings,
        # and the comparison would be meaningless.
        net.line.at[li, "max_loading_percent"] = 100.0

    for b in snap.buses:
        if abs(snap.pd_mw[b]) > 1e-9 or abs(snap.qd_mvar[b]) > 1e-9:
            pp.create_load(net, bus=bx[b], p_mw=snap.pd_mw[b], q_mvar=snap.qd_mvar[b], name=f"load_{b}")

    if not snap.shunts.empty:
        for name, row in snap.shunts.iterrows():
            if row["Node"] in bx:
                # q_mvar sign convention in pandapower: positive consumes. Bshb > 0 is a capacitor, so it injects.
                pp.create_shunt(net, bus=bx[row["Node"]], q_mvar=-float(row["Bshb"]) * snap.sbase_mva,
                                p_mw=float(row.get("Gshb", 0.0)) * snap.sbase_mva, name=str(name))

    # The reference bus carries the slack. Its generator, if any, is folded into the external grid so the
    # power balance always closes; every other unit becomes a controllable generator.
    gx = {}
    slack_created = False
    for g, row in snap.gens.iterrows():
        if row.bus == snap.ref_bus and not slack_created:
            idx = pp.create_ext_grid(net, bus=bx[row.bus], vm_pu=1.0, name=g,
                                     min_p_mw=row.pmin, max_p_mw=row.pmax,
                                     min_q_mvar=row.qmin, max_q_mvar=row.qmax)
            if with_costs:
                pp.create_poly_cost(net, element=idx, et="ext_grid", cp1_eur_per_mw=float(row.cost))
            gx[g] = ("ext_grid", idx)
            slack_created = True
        else:
            idx = pp.create_gen(net, bus=bx[row.bus], p_mw=max(row.pmin, 0.0), vm_pu=1.0, name=g,
                                min_p_mw=row.pmin, max_p_mw=row.pmax,
                                min_q_mvar=row.qmin, max_q_mvar=row.qmax, controllable=True)
            if with_costs:
                pp.create_poly_cost(net, element=idx, et="gen", cp1_eur_per_mw=float(row.cost))
            gx[g] = ("gen", idx)

    if not slack_created:
        raise ValueError(f"no generator at the reference bus {snap.ref_bus}; cannot place the slack")

    return net, bx, gx


def true_acopf(snap) -> dict:
    """Exact non-convex AC OPF. Returns cost, dispatch, voltages and branch flows, or {'ok': False}."""
    net, bx, gx = build_net(snap, with_costs=True)
    try:
        pp.runopp(net, calculate_voltage_angles=True, init="flat")
    except Exception as e:                                    # pandapower raises OPFNotConverged and friends
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return _harvest(net, snap, bx, gx, cost=float(net.res_cost))


def ac_powerflow(snap, p_dispatch: dict[str, float], v_setpoint: dict[str, float] | None = None) -> dict:
    """Exact AC power flow with the generator active powers fixed to ``p_dispatch``.

    ``v_setpoint`` optionally pins each generator bus voltage to what the prototype predicted; without it
    every unit holds 1.0 p.u., which would flatter formulations that ignore voltage.
    """
    net, bx, gx = build_net(snap, with_costs=False)
    for g, (et, idx) in gx.items():
        if g not in p_dispatch:
            continue
        if et == "gen":
            net.gen.at[idx, "p_mw"] = float(p_dispatch[g])
            if v_setpoint and g in v_setpoint:
                net.gen.at[idx, "vm_pu"] = float(np.clip(v_setpoint[g], snap.vmin, snap.vmax))
        elif v_setpoint and g in v_setpoint:
            net.ext_grid.at[idx, "vm_pu"] = float(np.clip(v_setpoint[g], snap.vmin, snap.vmax))
    try:
        pp.runpp(net, calculate_voltage_angles=True, init="flat", enforce_q_lims=True)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return _harvest(net, snap, bx, gx, cost=None)


def _harvest(net, snap, bx, gx, cost) -> dict:
    inv = {v: k for k, v in bx.items()}
    vm = {inv[i]: float(net.res_bus.vm_pu[i])      for i in net.res_bus.index}
    va = {inv[i]: math.radians(float(net.res_bus.va_degree[i])) for i in net.res_bus.index}

    pg, qg = {}, {}
    for g, (et, idx) in gx.items():
        res = net.res_gen if et == "gen" else net.res_ext_grid
        pg[g] = float(res.p_mw[idx])
        qg[g] = float(res.q_mvar[idx])

    flow_p, flow_q, loss = {}, {}, {}
    for i, row in net.line.iterrows():
        key = tuple(net.line.name[i].split("-"))
        flow_p[key] = float(net.res_line.p_from_mw[i])
        flow_q[key] = float(net.res_line.q_from_mvar[i])
        loss[key]   = float(net.res_line.pl_mw[i])

    return {"ok": True, "cost": cost, "vm": vm, "va": va, "pg": pg, "qg": qg,
            "flow_p": flow_p, "flow_q": flow_q, "loss": loss,
            "total_loss_mw": float(sum(loss.values())),
            "vm_min": min(vm.values()), "vm_max": max(vm.values())}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__.rsplit("/", 1)[0]))
    from case import load_snapshot, summarise

    d = sys.argv[1] if len(sys.argv) > 1 else "openTEPES/cases/9n_AC"
    c = sys.argv[2] if len(sys.argv) > 2 else "9n_AC"
    snap = load_snapshot(d, c)
    print(summarise(snap))

    ref = true_acopf(snap)
    if not ref["ok"]:
        print("true AC OPF failed:", ref["error"])
        raise SystemExit(1)
    print(f"\ntrue AC OPF   cost {ref['cost']:.2f} EUR/h   losses {ref['total_loss_mw']:.2f} MW   "
          f"V in [{ref['vm_min']:.4f}, {ref['vm_max']:.4f}]")
    print("dispatch:", {g: round(p, 1) for g, p in ref["pg"].items() if abs(p) > 1e-3})

    pf = ac_powerflow(snap, ref["pg"], ref["vm"] and {g: ref["vm"][snap.gens.bus[g]] for g in ref["pg"]})
    print(f"\nreplay power flow  losses {pf['total_loss_mw']:.2f} MW   "
          f"V in [{pf['vm_min']:.4f}, {pf['vm_max']:.4f}]" if pf["ok"] else f"replay failed: {pf.get('error')}")
