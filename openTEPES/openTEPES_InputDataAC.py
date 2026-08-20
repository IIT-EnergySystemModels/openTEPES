"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_InputDataAC — input data for the AC optimal power flow.

Two entry points, both no-ops when ``IndACPowerFlow`` is 0 so a DC run pays nothing for this module:

  * ``ReadACInputData``   — called from ``InputData``.          Reads the AC-only tables into ``par``.
  * ``ConfigureACData``   — called from ``DataConfiguration``.  Builds the AC sets and Pyomo parameters.

Conventions used throughout (they differ from the reference implementation in openTEPES_PRO, see doc/design/AC_OPF_Implementation_Plan.md):

  * Branch admittances ``pLineG`` / ``pLineB`` and shunt admittances stay in per unit on ``pSBase``, exactly like the existing ``pLineR`` / ``pLineX``.
    Power quantities stay in GW / Gvar. The conversion factor is ``pSBase`` (already in GVA), applied in the constraints.
  * ``pLineBsh`` is the TOTAL line charging susceptance of the pi model, matching the MATPOWER ``b`` convention. The constraints use half at each end.
  * ``pLineTapFactor`` is ``1 / tap``, i.e. the factor that multiplies the mutual admittance terms, and is 1.0 for a line that is not a transformer.
    The raw ``Tap`` column is left untouched in ``pLineTAP``.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict

import pandas as pd
from pyomo.environ import Param, Set, NonNegativeReals, Reals

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the relative import below has no parent package;
# fall back to an absolute package import in that case.
try:
    from .openTEPES_BoundTightening          import TightenACBounds
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_BoundTightening import TightenACBounds


# Defaults applied when the case does not give the value. Voltage limits are in per unit of nominal.
AC_SCALAR_DEFAULTS = {
    'pVMin':         0.95,
    'pVNom':         1.00,
    'pVMax':         1.05,
    'pCapacitivePF': 0.95,   # leading power factor limit for reactive-capable units
    'pInductivePF':  0.95,   # lagging power factor limit
}

# Columns oT_Data_BusShunt must provide. Missing ones are filled with the default rather than raising, so a minimal shunt table stays valid.
SHUNT_COLUMN_DEFAULTS = {
    'Node':                None,   # mandatory, no default
    'InitialPeriod':       0,
    'FinalPeriod':         0,
    'Gshb':                0.0,
    'Bshb':                0.0,
    'FixedInvestmentCost': 0.0,
    'FixedChargeRate':     0.0,
    'BinaryInvestment':    0,
    'InvestmentLo':        0.0,
    'InvestmentUp':        0.0,
}


def ReadACInputData(dfs, par, mTEPES, pIndLogConsole):
    """Read the AC-only input tables into ``par``.

    Called from ``InputData`` after the sector tables and before the ``pTimeStep`` averaging block, so the reactive demand is averaged on the same
    rolling window as the active demand.
    """
    if not par.get('pIndACPowerFlow', 0):
        return

    StartTime = time.time()

    # --- reactive demand -------------------------------------------------------------------------------------------------------------------------
    # Optional: a case can drive the AC model with no reactive load at all (line charging and shunts still act). An absent table becomes zeros on the
    # index the active demand already uses, so every downstream .loc[psn] and filter_rows call behaves identically either way.
    if 'dfReactiveDemand' in dfs:
        par['pReactiveDemand'] = dfs['dfReactiveDemand'].reindex(columns=mTEPES.nd, fill_value=0.0) * 1e-3   # reactive demand [Gvar]
    else:
        print('WARNING: oT_Data_ReactiveDemand is absent; the AC model runs with zero reactive demand at every node.')
        par['pReactiveDemand'] = par['pDemandElec'] * 0.0

    if par['pTimeStep'] > 1:
        par['pReactiveDemand'] = par['pReactiveDemand'].rolling(par['pTimeStep']).mean()
        par['pReactiveDemand'].fillna(0.0, inplace=True)

    # --- bus shunt devices -----------------------------------------------------------------------------------------------------------------------
    if 'dfBusShunt' in dfs:
        dfShunt = dfs['dfBusShunt']
        missing = [c for c, d in SHUNT_COLUMN_DEFAULTS.items() if c not in dfShunt.columns and d is None]
        if missing:
            raise ValueError(f'oT_Data_BusShunt: mandatory column(s) {missing} are absent')
        for col, default in SHUNT_COLUMN_DEFAULTS.items():
            if col not in dfShunt.columns:
                dfShunt[col] = default
        # SHUNT_COLUMN_DEFAULTS fills a missing COLUMN; a blank CELL still arrives as NaN. Left alone, a blank FinalPeriod fails the window test below
        # and the device disappears from the model with no message, and a blank InvestmentLo reaches setlb() as NaN. Fill the cells too.
        for col, default in SHUNT_COLUMN_DEFAULTS.items():
            if col in dfShunt.columns and default is not None:      # Node is mandatory and has no default to fill with
                dfShunt[col] = dfShunt[col].fillna(default)
        par['pShuntToNode']        = dfShunt['Node'                ]
        par['pShuntPeriodIni']     = dfShunt['InitialPeriod'       ]
        par['pShuntPeriodFin']     = dfShunt['FinalPeriod'         ].where(dfShunt['FinalPeriod'] != 0, 3000)
        par['pBusGshb']            = dfShunt['Gshb'                ]                                          # shunt conductance at the bus [p.u.]
        par['pBusBshb']            = dfShunt['Bshb'                ]                                          # shunt susceptance at the bus [p.u.]
        par['pShuntFixedCost']     = dfShunt['FixedInvestmentCost' ] * dfShunt['FixedChargeRate']              # shunt fixed cost             [MEUR]
        # A device given an investment cost but no charge rate multiplies out to zero, lands in `she`, is always in service and costs nothing. That is
        # a data mistake, not a modelling choice, and it is invisible in the results — so say so.
        pSilent = dfShunt.index[(dfShunt['FixedInvestmentCost'] > 0.0) & (dfShunt['FixedChargeRate'] <= 0.0)].tolist()
        if pSilent:
            print(f'WARNING: bus shunt(s) {pSilent} give a FixedInvestmentCost but no FixedChargeRate, so their annualised cost is zero. '
                  f'They will be treated as existing devices, always in service and free.')
        par['pShuntBinUnitInvest'] = dfShunt['BinaryInvestment'    ]
        par['pShuntLoInvest']      = dfShunt['InvestmentLo'        ]
        par['pShuntUpInvest']      = dfShunt['InvestmentUp'        ].where(dfShunt['InvestmentUp'] > 0.0, 1.0)
        par['pIndBusShunt']        = 1
    else:
        # Warn only when the case OFFERED a shunt table that then failed to arrive. An AC case with no shunts at all is perfectly normal — RTS-GMLC
        # has none — so warning on every such run is noise of exactly the kind the reactive-slack warning had to be cured of.
        if par.get('pBusShuntOffered', 0):
            print('### WARNING: the case provides an oT_Data_BusShunt table but it did not reach the model, so the system has been built with no bus '
                  'shunt devices and no reactive compensation from them. Check that the table was read.')
        par['pIndBusShunt']        = 0

    # --- scalars ---------------------------------------------------------------------------------------------------------------------------------
    # Voltage limits and power-factor limits come from oT_Data_Parameter. They are read by the generic scalar loop in InputData when the columns are
    # present; fill in the defaults for the columns the case leaves out.
    for key, default in AC_SCALAR_DEFAULTS.items():
        # A zero here is read as "not given". openTEPES_InputData fills blank numeric cells with 0.0 before this runs, so a blank cell and a declared
        # zero are the same value by the time they arrive and cannot be told apart. The isna test is kept as a guard for a source that does not fill.
        #
        # The consequence is that CapacitivePF = 0 or InductivePF = 0 cannot be used to say "no reactive support from generators" — it gets the 0.95
        # default instead. Set a very small value rather than zero to express that.
        if key not in par or pd.isna(par[key]) or par[key] == 0.0:
            par[key] = default

    if par['pVMin'] >= par['pVMax']:
        raise ValueError(f"VMin ({par['pVMin']}) must be below VMax ({par['pVMax']})")

    if pIndLogConsole:
        print('Reading AC input data                  ... ', round(time.time() - StartTime), 's')


def ConfigureACData(mTEPES, dfs, par):
    """Build the AC sets and Pyomo parameters on ``mTEPES``.

    Called from ``DataConfiguration`` after the branch parameters have been filtered onto ``mTEPES.la`` and after the psn* index sets exist.
    """
    if not par.get('pIndACPowerFlow', 0):
        return

    StartTime = time.time()

    pFirstPeriod = mTEPES.p.first()
    pLastPeriod  = mTEPES.p.last()

    # --- derived branch model --------------------------------------------------------------------------------------------------------------------
    # Series admittance from the series impedance. pLineX is guaranteed non-zero on mTEPES.la (it is part of the filter that builds la), so the
    # denominator cannot vanish even when a line is given zero resistance.
    pLineZ2 = par['pLineR']**2 + par['pLineX']**2
    par['pLineG']  =  par['pLineR'] / pLineZ2                                       # series conductance [p.u.]
    par['pLineB']  = -par['pLineX'] / pLineZ2                                       # series susceptance [p.u.], negative for an inductive branch
    par['pLineZ2'] = pLineZ2

    # Apparent-power rating. pLineNTCFrw/Bck already carry the security factor, and pLineNTCMax is their element-wise maximum, so this needs no
    # further scaling: it is the larger of the two directional ratings, in GVA.
    par['pLineSmax'] = par['pLineNTCMax']

    # Tap factor. A blank Tap column arrives as 0.0 meaning "not a transformer", which must map to 1.0 and not to a division by zero.
    pTap = par['pLineTAP'].where(par['pLineTAP'] > 0.0, 1.0)
    par['pLineTapFactor'] = 1.0 / pTap

    # Angle-difference limits. A blank AngMin/AngMax pair arrives as 0.0, which would pin the angle difference of every branch to exactly zero and
    # make the model infeasible the moment any power flows. Treat "both zero" as "not given" and open the limits to +/- pi/2.
    # openTEPES_InputData fills every blank numeric cell of dfNetwork with 0.0 before this runs, so a blank angle limit and a declared zero are
    # indistinguishable here — testing for NaN would be dead code. Each side is therefore opened whenever it is zero, not only when both are:
    # a half-filled pair (blank AngMin, AngMax = 30) would otherwise leave pMinAngleDiff at 0, and eAngleBandLo would then require
    # vTheta_i - vTheta_j >= 0, making reverse flow on that branch infeasible.
    #
    # The cost of this reading is that a case genuinely wanting a one-sided band of exactly 0 cannot express it. That is the right trade: a zero
    # angle limit pins the branch, which is almost never intended, while a blank column is common.
    par['pAngMin'] = par['pAngMin'].where(par['pAngMin'] != 0.0, -math.pi/2)
    par['pAngMax'] = par['pAngMax'].where(par['pAngMax'] != 0.0,  math.pi/2)
    if (par['pAngMin'] >= par['pAngMax']).any():
        bad = par['pAngMin'].index[par['pAngMin'] >= par['pAngMax']].tolist()
        raise ValueError(f'oT_Data_Network: AngMin must be below AngMax on line(s) {bad}')

    # --- branch index set ------------------------------------------------------------------------------------------------------------------------
    mTEPES.psnlaa = Set(doc='psn x AC branch', initialize=[(p,sc,n,ni,nf,cc) for p,sc,n in mTEPES.psn for ni,nf,cc in mTEPES.laa if (p,ni,nf,cc) in mTEPES.pla])

    # --- cycles: not computed ---------------------------------------------------------------------------------------------------------------------
    # An earlier version built the cycle basis here for a cyclic angle constraint. That constraint is not built — with vTheta explicit the sum of angle
    # differences round a closed cycle telescopes to zero identically, so it was 0 == 0 on every row (see openTEPES_ModelFormulationAC). The basis is
    # not computed either: nx.minimum_cycle_basis is roughly cubic in the edge count, which is real build time on a national case for a set nothing
    # reads. Eliminating vTheta in favour of the cycle form, as both reference papers do for compactness, would need it back.

    # --- bound tightening ------------------------------------------------------------------------------------------------------------------------
    # Runs here, before the variables are declared, because it is what makes the angle envelope tight enough to be worth anything.
    TightenACBounds(mTEPES, par, pIndLogConsole=0)

    # --- shunt sets ------------------------------------------------------------------------------------------------------------------------------
    # sqc and shc are declared empty in DataConfiguration so the DC path can reference them; replace them here with the real contents.
    mTEPES.del_component(mTEPES.shc)
    mTEPES.del_component(mTEPES.sqc)

    if par['pIndBusShunt']:
        sShunt = [sh for sh in dfs['dfBusShunt'].index
                  if par['pShuntPeriodIni'][sh] <= pLastPeriod and par['pShuntPeriodFin'][sh] >= pFirstPeriod]
        for sh in sShunt:
            if par['pShuntToNode'][sh] not in mTEPES.nd:
                raise ValueError(f"oT_Data_BusShunt: shunt {sh} sits on node {par['pShuntToNode'][sh]}, which is not in the node dictionary")
    else:
        sShunt = []

    mTEPES.sh  = Set(doc='bus shunt devices',       initialize=sShunt)
    mTEPES.she = Set(doc='existing  shunt devices', initialize=[sh for sh in sShunt if par['pShuntFixedCost'][sh] == 0.0])
    mTEPES.shc = Set(doc='candidate shunt devices', initialize=[sh for sh in sShunt if par['pShuntFixedCost'][sh] >  0.0])

    # Synchronous condensers split into existing and candidate on their investment cost, read straight from the generation table rather than from
    # par['pGenInvestCost']: that series is narrowed to mTEPES.eb at openTEPES_DataConfiguration.py:833, which runs before this function, and a
    # condenser is never in eb because eb is a subset of g and a zero-MW unit is not in g.
    pGenTable  = dfs['dfGeneration']
    pSynchCost = (pGenTable['FixedInvestmentCost'].astype(float) * pGenTable['FixedChargeRate'].astype(float)).fillna(0.0)

    mTEPES.sqe = Set(doc='existing  synchronous condensers', initialize=[sq for sq in mTEPES.sq if pSynchCost[sq] == 0.0])
    mTEPES.sqc = Set(doc='candidate synchronous condensers', initialize=[sq for sq in mTEPES.sq if pSynchCost[sq] >  0.0])

    # --- node-to-device maps ---------------------------------------------------------------------------------------------------------------------
    # Built as explicit membership lists rather than through a filtered cross product: nd*sh would be |nd|*|sh| membership tests, which is wasted work
    # on a large case when the relation is already one row per device.
    mTEPES.n2sh = Set(doc='node to shunt device',          initialize=[(par['pShuntToNode'][sh], sh) for sh in sShunt])
    mTEPES.n2gq = Set(doc='node to reactive-capable unit', initialize=[(par['pGenToNode'][gq], gq) for gq in mTEPES.gq if par['pGenToNode'][gq] in mTEPES.nd])
    mTEPES.n2sq = Set(doc='node to synchronous condenser', initialize=[(par['pGenToNode'][sq], sq) for sq in mTEPES.sq if par['pGenToNode'][sq] in mTEPES.nd])
    mTEPES.sh2n = par['pShuntToNode'] if par['pIndBusShunt'] else pd.Series(dtype=object)

    # --- index sets ------------------------------------------------------------------------------------------------------------------------------
    # Availability of a reactive unit is its own period window, NOT membership of mTEPES.pg. A synchronous condenser has MaximumPower = 0, so it never
    # enters mTEPES.g (openTEPES_DataConfiguration.py:60) and therefore never enters pg — filtering through pg would empty these sets for exactly the
    # units they exist to hold. Widening the g filter instead would drag a zero-MW unit through commitment, ramps and the second-block machinery in
    # every case, including DC ones, for no benefit.
    pGenIn = pGenTable['InitialPeriod'].astype(float).fillna(0.0)
    pGenFi = pGenTable['FinalPeriod'  ].astype(float).fillna(0.0).replace(0.0, 3000.0)

    mTEPES.psnsh = Set(doc='psn x shunt',                  initialize=[(p,sc,n,sh) for p,sc,n in mTEPES.psn for sh in sShunt
                                                                       if par['pShuntPeriodIni'][sh] <= p and par['pShuntPeriodFin'][sh] >= p])
    mTEPES.pgq   = Set(doc='period x reactive unit',       initialize=[(p,gq) for p in mTEPES.p for gq in mTEPES.gq
                                                                       if pGenIn[gq] <= p and pGenFi[gq] >= p])
    mTEPES.psqc  = Set(doc='period x candidate condenser', initialize=[(p,sq) for p,sq in mTEPES.pgq if sq in mTEPES.sqc])
    mTEPES.psngq = Set(doc='psn x reactive unit',          initialize=[(p,sc,n,gq) for p,sc,n in mTEPES.psn for gq in mTEPES.gq if (p,gq) in mTEPES.pgq])
    mTEPES.psnsq = Set(doc='psn x synchronous condenser',  initialize=[(p,sc,n,sq) for p,sc,n in mTEPES.psn for sq in mTEPES.sq if (p,sq) in mTEPES.pgq])
    mTEPES.psh   = Set(doc='period x shunt',               initialize=[(p,sh)      for p      in mTEPES.p   for sh in sShunt
                                                                       if par['pShuntPeriodIni'][sh] <= p and par['pShuntPeriodFin'][sh] >= p])
    mTEPES.pshc  = Set(doc='period x candidate shunt',     initialize=[(p,sh)      for p,sh   in mTEPES.psh if sh in mTEPES.shc])

    # --- reactive demand onto the model index ----------------------------------------------------------------------------------------------------
    par['pReactiveDemand'] = par['pReactiveDemand'].loc[mTEPES.psn]

    def _stack_on(df, index_set):
        df = df.stack(future_stack=True)
        return df[df.index.isin(index_set)]

    par['pReactiveDemand'] = _stack_on(par['pReactiveDemand'], mTEPES.psnnd)

    # --- Pyomo parameters ------------------------------------------------------------------------------------------------------------------------
    # The reactive limits are rated nameplate values and do not vary with the load level, so they are indexed on gq alone. Expanding them onto psngq
    # the way the active-power limits are expanded would store |psn| identical copies of every number — 65,520 entries instead of 15 on the 9-bus case.
    mTEPES.pReactiveDemand   = Param(mTEPES.psnnd, initialize=par['pReactiveDemand'].to_dict()                 , within=Reals, doc='Reactive demand [Gvar]', mutable=True)
    mTEPES.pMaxReactivePower = Param(mTEPES.gq,    initialize=par['pRMaxReactivePower'].loc[mTEPES.gq].to_dict(), within=Reals, doc='Rated maximum reactive power [Gvar]')
    mTEPES.pMinReactivePower = Param(mTEPES.gq,    initialize=par['pRMinReactivePower'].loc[mTEPES.gq].fillna(0.0).to_dict(), within=Reals, doc='Rated minimum reactive power [Gvar]')
    if mTEPES.sqc:
        mTEPES.pSynchFixedCost = Param(mTEPES.sqc, initialize=pSynchCost.loc[list(mTEPES.sqc)].to_dict(), within=NonNegativeReals, doc='Synchronous condenser fixed cost [MEUR]')
        # A condenser is never in mTEPES.eb, so the generation investment bounds are narrowed away before they reach it and its own InvestmentLo /
        # InvestmentUp / BinaryInvestment columns were simply not read. A case declaring InvestmentUp = 0 to say "do not build this" got it built
        # anyway, and BinaryInvestment = 0 still produced an integer variable — both unlike an ordinary generator with the same settings. Read here,
        # from the generation table, because this is where the condenser sets are known.
        pSynchLo  = pGenTable['InvestmentLo'    ].astype(float).fillna(0.0) if 'InvestmentLo'     in pGenTable.columns else None
        pSynchUp  = pGenTable['InvestmentUp'    ].astype(float).fillna(1.0) if 'InvestmentUp'     in pGenTable.columns else None
        pSynchBin = pGenTable['BinaryInvestment'].astype(float).fillna(0.0) if 'BinaryInvestment' in pGenTable.columns else None
        sqcList   = list(mTEPES.sqc)
        mTEPES.pSynchLoInvest      = Param(mTEPES.sqc, initialize={sq: (pSynchLo [sq] if pSynchLo  is not None else 0.0) for sq in sqcList}, within=NonNegativeReals, doc='Lower bound of the condenser investment decision [p.u.]')
        # an InvestmentUp of 0 in the data means "not buildable"; a MISSING column means "no limit", which is 1
        mTEPES.pSynchUpInvest      = Param(mTEPES.sqc, initialize={sq: (pSynchUp [sq] if pSynchUp  is not None else 1.0) for sq in sqcList}, within=NonNegativeReals, doc='Upper bound of the condenser investment decision [p.u.]')
        mTEPES.pSynchBinUnitInvest = Param(mTEPES.sqc, initialize={sq: (pSynchBin[sq] if pSynchBin is not None else 0.0) for sq in sqcList}, within=NonNegativeReals, doc='Binary condenser investment decision')

    mTEPES.pLineG            = Param(mTEPES.la,    initialize=par['pLineG'].to_dict()           , within=Reals,            doc='Series conductance [p.u.]'                            )
    mTEPES.pLineB            = Param(mTEPES.la,    initialize=par['pLineB'].to_dict()           , within=Reals,            doc='Series susceptance [p.u.], negative if inductive'     )
    mTEPES.pLineZ2           = Param(mTEPES.la,    initialize=par['pLineZ2'].to_dict()          , within=NonNegativeReals, doc='Squared series impedance R^2+X^2 [p.u.]'              )
    mTEPES.pLineSmax         = Param(mTEPES.la,    initialize=par['pLineSmax'].to_dict()        , within=NonNegativeReals, doc='Apparent power rating [GVA]'                          )
    mTEPES.pLineTapFactor    = Param(mTEPES.la,    initialize=par['pLineTapFactor'].to_dict()   , within=NonNegativeReals, doc='1/tap, multiplies the mutual admittance terms [p.u.]' )

    # Tightened bounds. pMaxAngleDiff is the per-branch angle-difference limit after propagation, and is what the angle envelope's slack
    # tan(t/2) - t/2 is computed from; pVMinBus / pVMaxBus are the per-bus voltage bounds. See openTEPES_BoundTightening.
    # Reals, not NonNegativeReals: the tightening keeps the declared signs, so a branch declared -30 to -5 degrees has a NEGATIVE upper limit and
    # a non-negative domain would refuse to build the model at all.
    mTEPES.pMaxAngleDiff     = Param(mTEPES.laa,   initialize=par['pMaxAngleDiff']              , within=Reals,            doc='Tightened angle-difference limit [rad]'               )
    mTEPES.pMinAngleDiff     = Param(mTEPES.laa,   initialize=par['pMinAngleDiff']              , within=Reals,            doc='Tightened angle-difference limit, lower [rad]'       )
    mTEPES.pVMinBus          = Param(mTEPES.nd,    initialize=par['pVMinBus']                   , within=NonNegativeReals, doc='Tightened minimum voltage magnitude [p.u.]'           )
    mTEPES.pVMaxBus          = Param(mTEPES.nd,    initialize=par['pVMaxBus']                   , within=NonNegativeReals, doc='Tightened maximum voltage magnitude [p.u.]'           )

    mTEPES.pVMin             = Param(initialize=par['pVMin']        , within=NonNegativeReals, doc='Minimum voltage magnitude [p.u.]')
    mTEPES.pVNom             = Param(initialize=par['pVNom']        , within=NonNegativeReals, doc='Nominal voltage magnitude [p.u.]')
    mTEPES.pVMax             = Param(initialize=par['pVMax']        , within=NonNegativeReals, doc='Maximum voltage magnitude [p.u.]')
    mTEPES.pCapacitivePF     = Param(initialize=par['pCapacitivePF'], within=NonNegativeReals, doc='Capacitive power factor limit [p.u.]')
    mTEPES.pInductivePF      = Param(initialize=par['pInductivePF'] , within=NonNegativeReals, doc='Inductive  power factor limit [p.u.]')

    if par['pIndBusShunt']:
        mTEPES.pBusGshb            = Param(mTEPES.sh, initialize=par['pBusGshb'].loc[list(mTEPES.sh)].to_dict()           , within=Reals,            doc='Shunt conductance [p.u.]'                  , mutable=True)
        mTEPES.pBusBshb            = Param(mTEPES.sh, initialize=par['pBusBshb'].loc[list(mTEPES.sh)].to_dict()           , within=Reals,            doc='Shunt susceptance [p.u.]'                  , mutable=True)
        mTEPES.pShuntFixedCost     = Param(mTEPES.sh, initialize=par['pShuntFixedCost'].loc[list(mTEPES.sh)].to_dict()    , within=NonNegativeReals, doc='Shunt fixed cost [MEUR]'                                )
        mTEPES.pShuntBinUnitInvest = Param(mTEPES.sh, initialize=par['pShuntBinUnitInvest'].loc[list(mTEPES.sh)].to_dict(), within=NonNegativeReals, doc='Binary shunt investment decision'                       )
        mTEPES.pShuntLoInvest      = Param(mTEPES.sh, initialize=par['pShuntLoInvest'].loc[list(mTEPES.sh)].to_dict()     , within=NonNegativeReals, doc='Lower bound of the shunt investment decision [p.u.]'    )
        mTEPES.pShuntUpInvest      = Param(mTEPES.sh, initialize=par['pShuntUpInvest'].loc[list(mTEPES.sh)].to_dict()     , within=NonNegativeReals, doc='Upper bound of the shunt investment decision [p.u.]'    )

    print('Setting up AC input data               ... ', round(time.time() - StartTime), 's')
