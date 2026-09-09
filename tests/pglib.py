"""Turn a MATPOWER case into a single-hour openTEPES AC case.

Written for the pglib-opf benchmark library, which publishes a reference AC OPF objective and a SOC relaxation gap for
every case. That gives the one thing our own cases cannot: a number computed by other people, on a problem everybody
agrees on, so a gap we measure can be compared with a gap somebody else measured.

Two unit traps live in the MATPOWER format and both cost a factor of 100 if missed.

  * bus ``GS`` and ``BS`` are MW and Mvar drawn or injected AT V = 1.0 p.u., NOT per unit. openTEPES wants per unit on
    SBase, so the conversion is ``Bshb = BS / baseMVA``. Bus 5 of case118 carries ``BS = -40``, a 40 Mvar reactor,
    which is ``Bshb = -0.40``.
  * branch ``r``, ``x`` and ``b`` ARE per unit on baseMVA already, so they copy across untouched. ``b`` is the total
    line charging of the pi model, which is the convention openTEPES_InputDataAC documents for ``Susceptance``.

The case this writes is deliberately a bare AC OPF and nothing else: one hour, no commitment, no reserves, no storage,
no emissions, no investment. Everything openTEPES can add on top of the network is switched off or zeroed, because any
of it would appear in the objective and make the comparison with the published number meaningless.
"""
from __future__ import annotations

import math
import os
import re

import pandas as pd

# MATPOWER column positions, zero based
BUS_I, BUS_TYPE, BUS_PD, BUS_QD, BUS_GS, BUS_BS, BUS_AREA, BUS_VM, BUS_VA, BUS_KV, BUS_ZONE, BUS_VMAX, BUS_VMIN = range(13)
GEN_BUS, GEN_PG, GEN_QG, GEN_QMAX, GEN_QMIN, GEN_VG, GEN_MBASE, GEN_STATUS, GEN_PMAX, GEN_PMIN = range(10)
BR_F, BR_T, BR_R, BR_X, BR_B, BR_RATEA, BR_RATEB, BR_RATEC, BR_TAP, BR_SHIFT, BR_STATUS, BR_ANGMIN, BR_ANGMAX = range(13)

LOAD_LEVEL = '01-01 00:00:00+01:00'
PERIOD, SCENARIO, STAGE = 2030, 'sc01', 'st1'


def read_matpower(path):
    """Parse the handful of mpc blocks we need. Returns a dict of lists of floats plus baseMVA."""
    text = open(path, encoding='utf-8').read()

    def block(name):
        m = re.search(r'mpc\.' + name + r'\s*=\s*\[(.*?)\n\s*\];', text, re.S)
        if m is None:
            return []
        rows = []
        for line in m.group(1).strip().splitlines():
            line = line.split('%')[0].strip().rstrip(';').strip()
            if line:
                rows.append([float(x) for x in line.split()])
        return rows

    base = float(re.search(r'mpc\.baseMVA\s*=\s*([0-9.eE+-]+)\s*;', text).group(1))
    return {'baseMVA': base, 'bus': block('bus'), 'gen': block('gen'), 'branch': block('branch'), 'gencost': block('gencost')}


def _write(out_dir, case, stem, df, index=False):
    df.to_csv(os.path.join(out_dir, case, f'oT_{stem}_{case}.csv'), index=index)


def write_case(mpc, out_dir, case, ind_ac_power_flow=1, ind_ac_model_type=0):
    """Write the openTEPES CSVs for a one hour AC OPF of ``mpc`` into ``out_dir/case``."""
    os.makedirs(os.path.join(out_dir, case), exist_ok=True)
    base = mpc['baseMVA']
    bus, gen, branch, gencost = mpc['bus'], mpc['gen'], mpc['branch'], mpc['gencost']

    nd = {int(b[BUS_I]): f'N_{int(b[BUS_I])}' for b in bus}
    nodes = [nd[int(b[BUS_I])] for b in bus]
    slack = [nd[int(b[BUS_I])] for b in bus if b[BUS_TYPE] == 3][0]
    vmin = min(b[BUS_VMIN] for b in bus)
    vmax = max(b[BUS_VMAX] for b in bus)

    idx = pd.DataFrame({'Period': [PERIOD], 'Scenario': [SCENARIO], 'LoadLevel': [LOAD_LEVEL]})

    # ---- scalars, dictionaries and the single load level -------------------------------------------------------
    # CapacitivePF and InductivePF are pushed to 0.01 on purpose. openTEPES also limits generator reactive output to
    # tan(acos(pf)) times the ACTIVE output, which MATPOWER does not do: there Qmin <= Qg <= Qmax is a box, independent
    # of Pg. tan(acos(0.01)) is about 100, so the box is what binds and the model is the one pglib solved.
    _write(out_dir, case, 'Data_Parameter', pd.DataFrame([{
        'ENSCost': 10000, 'HNSCost': 10000, 'HTNSCost': 10000, 'CO2Cost': 0,
        'UpReserveActivation': 0, 'DwReserveActivation': 0, 'MinRatioDwUp': 0, 'MaxRatioDwUp': 1,
        'SBase': base, 'ReferenceNode': slack, 'TimeStep': 1, 'EconomicBaseYear': PERIOD, 'AnnualDiscountRate': 0,
        'VMin': vmin, 'VNom': 1.0, 'VMax': vmax, 'CapacitivePF': 0.01, 'InductivePF': 0.01,
    }]))
    # The AC flags belong in oT_Data_Option, NOT oT_Data_Parameter. InputData peeks at Option before the main read loop to
    # decide whether to read ReactiveDemand and BusShunt at all; put them in Parameter and the model is still built as AC
    # but with zero reactive demand and no shunts, which looks like a solved case and is not one.
    _write(out_dir, case, 'Data_Option', pd.DataFrame([{
        'IndBinGenInvest': 2, 'IndBinGenRetirement': 2, 'IndBinRsrInvest': 2, 'IndBinNetInvest': 2,
        'IndBinNetH2Invest': 2, 'IndBinNetHeatInvest': 2, 'IndBinGenOperat': 0, 'IndBinNetLosses': 0,
        'IndBinLineCommit': 0, 'IndBinSingleNode': 0, 'IndBinGenRamps': 0, 'IndBinGenMinTime': 0,
        'IndACPowerFlow': ind_ac_power_flow, 'IndACModelType': ind_ac_model_type, 'IndACRestore': 0, 'IndACCycle': 0,
    }]))
    _write(out_dir, case, 'Data_Period',   pd.DataFrame({'Period': [PERIOD], 'Weight': [1]}))
    _write(out_dir, case, 'Data_Scenario', pd.DataFrame({'Period': [PERIOD], 'Scenario': [SCENARIO], 'Probability': [1]}))
    _write(out_dir, case, 'Data_Stage',    pd.DataFrame({'Stage': [STAGE], 'Weight': [1]}))
    _write(out_dir, case, 'Data_Duration', idx.assign(Duration=1, Stage=STAGE))

    for stem, col, vals in (('Dict_Node', 'Node', nodes), ('Dict_Period', 'Period', [PERIOD]),
                            ('Dict_Scenario', 'Scenario', [SCENARIO]), ('Dict_Stage', 'Stage', [STAGE]),
                            ('Dict_LoadLevel', 'LoadLevel', [LOAD_LEVEL]), ('Dict_Circuit', 'Circuit', ['ac1']),
                            ('Dict_Line', 'LineType', ['AC', 'DC']), ('Dict_Storage', 'StorageType', ['Daily']),
                            ('Dict_Zone', 'Zone', ['Zone1']), ('Dict_Area', 'Area', ['Area1']),
                            ('Dict_Region', 'Region', ['Reg1'])):
        _write(out_dir, case, stem, pd.DataFrame({col: vals}))
    _write(out_dir, case, 'Dict_NodeToZone',   pd.DataFrame({'Node': nodes, 'Zone': 'Zone1'}))
    _write(out_dir, case, 'Dict_ZoneToArea',   pd.DataFrame({'Zone': ['Zone1'], 'Area': ['Area1']}))
    _write(out_dir, case, 'Dict_AreaToRegion', pd.DataFrame({'Area': ['Area1'], 'Region': ['Reg1']}))
    _write(out_dir, case, 'Data_NodeLocation', pd.DataFrame({'Node': nodes, 'Latitude': 0.0, 'Longitude': 0.0}))

    # ---- demand ------------------------------------------------------------------------------------------------
    pd_mw = {nd[int(b[BUS_I])]: b[BUS_PD] for b in bus}
    qd_mvar = {nd[int(b[BUS_I])]: b[BUS_QD] for b in bus}
    _write(out_dir, case, 'Data_Demand',         pd.concat([idx, pd.DataFrame([pd_mw])],   axis=1))
    _write(out_dir, case, 'Data_ReactiveDemand', pd.concat([idx, pd.DataFrame([qd_mvar])], axis=1))

    # ---- shunts: MW / Mvar at V = 1.0 p.u. in MATPOWER, per unit on SBase in openTEPES ---------------------------
    sh = [(f'Sh_{int(b[BUS_I])}', nd[int(b[BUS_I])], b[BUS_GS] / base, b[BUS_BS] / base)
          for b in bus if b[BUS_GS] != 0.0 or b[BUS_BS] != 0.0]
    _write(out_dir, case, 'Data_BusShunt', pd.DataFrame(
        [{'Shunt': s, 'Node': n, 'InitialPeriod': PERIOD, 'FinalPeriod': 3000, 'Gshb': g, 'Bshb': b,
          'FixedInvestmentCost': 0.0, 'FixedChargeRate': 0.0, 'BinaryInvestment': 0,
          'InvestmentLo': 0.0, 'InvestmentUp': 0.0, 'Switchable': 0} for s, n, g, b in sh]))

    # ---- branches ----------------------------------------------------------------------------------------------
    seen, rows = {}, []
    for br in branch:
        if br[BR_STATUS] == 0:
            continue
        ni, nf = nd[int(br[BR_F])], nd[int(br[BR_T])]
        seen[(ni, nf)] = seen.get((ni, nf), 0) + 1
        rating = br[BR_RATEA] if br[BR_RATEA] > 0 else 9999.0
        rows.append({
            'InitialNode': ni, 'FinalNode': nf, 'Circuit': f'ac{seen[(ni, nf)]}', 'LineType': 'AC', 'Switching': '',
            'InitialPeriod': PERIOD, 'FinalPeriod': 3000,
            'Voltage': [b[BUS_KV] for b in bus if int(b[BUS_I]) == int(br[BR_F])][0], 'Length': '',
            'LossFactor': 0.0, 'Reactance': br[BR_X], 'TTC': rating, 'TTCBck': rating, 'SecurityFactor': 1.0,
            'FixedInvestmentCost': '', 'FixedChargeRate': '', 'BinaryInvestment': '', 'SwOnTime': '', 'SwOffTime': '',
            'Resistance': br[BR_R], 'Susceptance': br[BR_B],
            'Tap': br[BR_TAP] if br[BR_TAP] != 0.0 else 1.0,
            'AngMin': br[BR_ANGMIN], 'AngMax': br[BR_ANGMAX], 'InvestmentLo': '', 'InvestmentUp': '',
        })
    _write(out_dir, case, 'Data_Network', pd.DataFrame(rows))
    _write(out_dir, case, 'Dict_Circuit', pd.DataFrame({'Circuit': sorted({r['Circuit'] for r in rows})}))

    # ---- generators --------------------------------------------------------------------------------------------
    # A unit with no active capability but some reactive capability is a synchronous condenser, which is exactly what
    # openTEPES_DataConfiguration:110 looks for. pglib labels 35 of case118's 54 units SYNC and gives them Pmax = 0.
    grows = []
    for i, g in enumerate(gen):
        if g[GEN_STATUS] == 0:
            continue
        c = gencost[i] if i < len(gencost) else [2, 0, 0, 3, 0.0, 0.0, 0.0]
        c1 = c[5] if len(c) > 5 else 0.0                      # $/MWh, linear; pglib TYP cases have c2 = 0
        cond = g[GEN_PMAX] == 0.0 and g[GEN_QMAX] > 0.0
        if g[GEN_PMAX] == 0.0 and g[GEN_QMAX] <= 0.0:
            continue                                          # neither active nor reactive capability: not a device
        name = f'{"SC" if cond else "G"}_{i + 1:02d}_{int(g[GEN_BUS])}'
        grows.append({
            'Generator': name, 'Node': nd[int(g[GEN_BUS])],
            'Technology': 'SynchronousCondenser' if cond else 'Thermal',
            'MutuallyExclusive': '', 'StorageType': '', 'OutflowsType': '', 'EnergyType': '', 'MustRun': '',
            'OutflowsIncompatibility': '', 'NoOperatingReserve': 'Yes', 'BinaryInvestment': '',
            'BinaryRetirement': '', 'BinaryCommitment': '', 'InitialPeriod': PERIOD, 'FinalPeriod': 3000,
            'MaximumPower': g[GEN_PMAX], 'MinimumPower': g[GEN_PMIN],
            'MaximumPowerHeat': '', 'MinimumPowerHeat': '', 'MaximumCharge': '', 'MinimumCharge': '',
            'InitialStorage': '', 'MaximumStorage': '', 'MinimumStorage': '', 'Efficiency': '', 'ShiftTime': '',
            'EFOR': 0.0, 'RampUp': '', 'RampDown': '', 'UpTime': '', 'DownTime': '', 'StableTime': '',
            'FuelCost': 1.0, 'LinearTerm': c1, 'ConstantTerm': 0.0, 'OMVariableCost': 0.0, 'OperReserveCost': 0.0,
            'StartUpCost': 0.0, 'ShutDownCost': 0.0, 'CO2EmissionRate': 0.0, 'Availability': '',
            'FixedInvestmentCost': '', 'FixedRetirementCost': '', 'FixedChargeRate': '', 'StorageInvestment': '',
            'Inertia': '', 'MaximumReactivePower': g[GEN_QMAX], 'MinimumReactivePower': g[GEN_QMIN],
            'InvestmentLo': '', 'InvestmentUp': '', 'RetirementLo': '', 'RetirementUp': '',
            'ProductionFunctionHydro': '', 'ProductionFunctionH2': '', 'ProductionFunctionHeat': '',
            'ProductionFunctionH2ToHeat': '',
        })
    gdf = pd.DataFrame(grows)
    _write(out_dir, case, 'Data_Generation', gdf)
    _write(out_dir, case, 'Dict_Generation', pd.DataFrame({'Generator': gdf['Generator']}))
    _write(out_dir, case, 'Dict_Technology', pd.DataFrame({'Technology': sorted(set(gdf['Technology']))}))

    # ---- everything openTEPES can add on top of the network, switched off ---------------------------------------
    names = list(gdf['Generator'])
    for stem in ('VariableMaxGeneration', 'VariableMinGeneration', 'VariableMaxConsumption', 'VariableMinConsumption',
                 'VariableMaxStorage', 'VariableMinStorage', 'VariableMaxEnergy', 'VariableMinEnergy',
                 'VariableFuelCost', 'VariableEmissionCost', 'EnergyInflows', 'EnergyOutflows'):
        _write(out_dir, case, f'Data_{stem}', pd.concat([idx, pd.DataFrame([{n: '' for n in names}])], axis=1))
    for stem in ('OperatingReserveUp', 'OperatingReserveDown', 'Inertia'):
        _write(out_dir, case, f'Data_{stem}', idx.assign(Area1=0.0))
    _write(out_dir, case, 'Data_Emission',      pd.DataFrame({'Period': [PERIOD], 'Area': ['Area1'], 'CO2Emission': ['']}))
    _write(out_dir, case, 'Data_RESEnergy',     pd.DataFrame({'Period': [PERIOD], 'Area': ['Area1'], 'RESEnergy': [0.0]}))
    _write(out_dir, case, 'Data_ReserveMargin', pd.DataFrame({'Period': [PERIOD], 'Area': ['Area1'], 'ReserveMargin': [0.0]}))

    return {'nodes': len(nodes), 'branches': len(rows), 'gens': int((gdf['MaximumPower'] > 0).sum()),
            'condensers': int((gdf['MaximumPower'] == 0).sum()), 'shunts': len(sh),
            'demand_mw': sum(pd_mw.values()), 'demand_mvar': sum(qd_mvar.values()), 'slack': slack}
