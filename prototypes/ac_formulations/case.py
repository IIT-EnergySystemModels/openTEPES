"""Read one load level of an openTEPES case into a compact snapshot for the formulation study.

Deliberately independent of the openTEPES package: it reads the case CSVs with pandas only, so the
prototypes can run in any environment and cannot be perturbed by changes to the model code while the
study is running.

Per-unit convention follows the case: impedances are already per unit on ``SBase`` (MVA) and the line
voltage given in the network table. Powers are converted to MW / Mvar, which is what pandapower wants.

DC lines are excluded. The study compares AC network formulations, and a point-to-point DC link is
modelled identically by all of them, so including it would only add noise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class Snapshot:
    """One load level of a case, in engineering units (MW, Mvar, ohm, p.u.)."""
    name:       str
    sbase_mva:  float
    ref_bus:    str
    buses:      list[str]
    vmin:       float
    vmax:       float
    # branch table, indexed by (ni, nf, cc)
    branches:   pd.DataFrame
    # generator table, indexed by generator name
    gens:       pd.DataFrame
    # per-bus demand
    pd_mw:      dict[str, float]
    qd_mvar:    dict[str, float]
    # shunt devices, indexed by name; empty frame when the case has none
    shunts:     pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def zbase(self) -> dict[tuple, float]:
        """Impedance base per branch, from its own voltage level."""
        return {k: (row.kv ** 2) / self.sbase_mva for k, row in self.branches.iterrows()}


def _read(case_dir: Path, stem: str, case: str, **kw) -> pd.DataFrame:
    return pd.read_csv(case_dir / f"oT_Data_{stem}_{case}.csv", encoding="utf-8-sig", **kw)


def load_snapshot(case_dir: str | Path, case: str, hour: int | str = "peak") -> Snapshot:
    """Build a Snapshot from an openTEPES case directory.

    ``hour`` is either an integer row index into the demand table or ``"peak"`` for the load level with
    the highest total active demand.
    """
    case_dir = Path(case_dir)

    par = _read(case_dir, "Parameter", case)
    sbase = float(par["SBase"].iloc[0])
    ref_bus = str(par["ReferenceNode"].iloc[0])
    vmin = float(par["VMin"].iloc[0]) if "VMin" in par.columns else 0.95
    vmax = float(par["VMax"].iloc[0]) if "VMax" in par.columns else 1.05

    net = _read(case_dir, "Network", case).fillna(0.0)
    net = net[net["LineType"] != "DC"].copy()
    net["cc"] = net["Circuit"]
    branches = net.set_index(["InitialNode", "FinalNode", "Circuit"])
    branches = pd.DataFrame({
        "r_pu":   branches["Resistance"].astype(float),
        "x_pu":   branches["Reactance"].astype(float),
        "b_pu":   branches["Susceptance"].astype(float),      # TOTAL charging susceptance of the pi model
        "tap":    branches["Tap"].astype(float).where(branches["Tap"].astype(float) > 0.0, 1.0),
        "kv":     branches["Voltage"].astype(float),
        "s_mva":  branches["TTC"].astype(float) * branches["SecurityFactor"].astype(float),
        "angmin": branches["AngMin"].astype(float) * math.pi / 180.0,
        "angmax": branches["AngMax"].astype(float) * math.pi / 180.0,
    })
    # an unset angle band means "not given", not "pinned to zero"
    unset = (branches["angmin"] == 0.0) & (branches["angmax"] == 0.0)
    branches.loc[unset, "angmin"] = -math.pi / 2
    branches.loc[unset, "angmax"] = +math.pi / 2

    gen = _read(case_dir, "Generation", case).set_index(gen_index_col(case_dir, case))
    gen = gen.fillna({c: 0.0 for c in gen.select_dtypes("number").columns})
    gens = pd.DataFrame({
        "bus":    gen["Node"],
        "pmax":   gen["MaximumPower"].astype(float),
        "pmin":   gen["MinimumPower"].astype(float),
        "qmax":   gen["MaximumReactivePower"].astype(float),
        "qmin":   gen["MinimumReactivePower"].astype(float),
        # linear operating cost proxy: fuel cost * linear term, the same product openTEPES prices energy with
        "cost":   (gen["FuelCost"].astype(float) * gen["LinearTerm"].astype(float)
                   + gen["OMVariableCost"].astype(float)),
    })
    # Storage is excluded: a single snapshot has no inter-temporal energy balance, so an ESS would appear as free
    # generation. Identified by a positive charging capacity, the same test openTEPES uses to build mTEPES.eh.
    gens = gens[gens["pmax"] > 0.0]
    gens = gens[gen["MaximumCharge"].astype(float).reindex(gens.index).fillna(0.0) <= 0.0]
    gens = gens[gens["bus"].isin(set(branches.index.get_level_values(0)) | set(branches.index.get_level_values(1)))]
    # Zero marginal cost is correct for RES, but an exactly-free unit leaves the merit order degenerate at the top.
    # A token cost keeps RES cheapest without making the LP indifferent between identical free units.
    gens.loc[gens["cost"] <= 0.0, "cost"] = 0.01

    # Minimum outputs are released. In openTEPES a pmin binds only on a committed unit; in a single snapshot with no
    # unit commitment every pmin would bind at once, and on this case they sum to 1659 MW against 1531 MW of demand,
    # which is simply infeasible. Every formulation sees the same relaxation, and the study is about network physics,
    # not commitment. This also matches how the reference papers test: pure OPF, no UC.
    gens["pmin"] = 0.0

    dem = _read(case_dir, "Demand", case, index_col=[0, 1, 2]).fillna(0.0)
    if hour == "peak":
        row = dem.sum(axis=1).idxmax()
    else:
        row = dem.index[int(hour)]
    pd_mw = dem.loc[row].astype(float).to_dict()

    qpath = case_dir / f"oT_Data_ReactiveDemand_{case}.csv"
    if qpath.exists():
        qdem = pd.read_csv(qpath, encoding="utf-8-sig", index_col=[0, 1, 2]).fillna(0.0)
        qd_mvar = qdem.loc[row].astype(float).to_dict()
    else:
        qd_mvar = {b: 0.0 for b in pd_mw}

    spath = case_dir / f"oT_Data_BusShunt_{case}.csv"
    shunts = pd.read_csv(spath, encoding="utf-8-sig", index_col=0).fillna(0.0) if spath.exists() else pd.DataFrame()

    buses = sorted(set(branches.index.get_level_values(0)) | set(branches.index.get_level_values(1)))
    pd_mw   = {b: float(pd_mw.get(b, 0.0))   for b in buses}
    qd_mvar = {b: float(qd_mvar.get(b, 0.0)) for b in buses}

    return Snapshot(name=f"{case}@{row[-1]}", sbase_mva=sbase, ref_bus=ref_bus, buses=buses,
                    vmin=vmin, vmax=vmax, branches=branches, gens=gens,
                    pd_mw=pd_mw, qd_mvar=qd_mvar, shunts=shunts)


def gen_index_col(case_dir: Path, case: str) -> str:
    return pd.read_csv(case_dir / f"oT_Data_Generation_{case}.csv", encoding="utf-8-sig", nrows=1).columns[0]


def summarise(s: Snapshot) -> str:
    n_mesh = len(s.branches) - len(s.buses) + 1
    return (f"{s.name}: {len(s.buses)} buses, {len(s.branches)} AC branches, "
            f"{len(s.gens)} units, {n_mesh} independent cycles, "
            f"demand {sum(s.pd_mw.values()):.0f} MW / {sum(s.qd_mvar.values()):.0f} Mvar, "
            f"SBase {s.sbase_mva} MVA, V in [{s.vmin}, {s.vmax}]")


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "openTEPES/cases/9n_AC"
    c = sys.argv[2] if len(sys.argv) > 2 else "9n_AC"
    print(summarise(load_snapshot(d, c)))
