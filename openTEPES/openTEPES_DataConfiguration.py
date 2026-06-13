"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 11, 2026

openTEPES.openTEPES_DataConfiguration — builds the derived sets and parameters on the model: instrumental sets, ESS/RES sets, and the flag-driven branches (hydro topology, hydrogen, heat, PTDF). Runs after InputData has read the raw sets and parameters.
"""
from __future__ import annotations

import time
import math
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import Set, Param, Binary, NonNegativeReals, NonNegativeIntegers, PositiveReals, PositiveIntegers, Reals, UnitInterval, Any


# @profile
def DataConfiguration(mTEPES, dfs=None, par=None):
    """Build the derived sets and parameters on ``mTEPES``.

    ``dfs`` and ``par`` are the dicts returned by ``InputData``. They
    default to the legacy ``mTEPES.dFrame`` / ``mTEPES.dPar`` attributes
    so existing callers that don't pass them keep working — but new code
    should pass them explicitly to avoid the dict-on-model anti-pattern.
    """
    if dfs is None:
        dfs = mTEPES.dFrame
    if par is None:
        par = mTEPES.dPar

    # NOTE on floating-point equality below.
    # Many of the Set predicates in this function compare scalar parameters
    # against `0.0` with `==` / `!= 0.0`. These are NOT numeric "close to
    # zero" checks — they test for the user-supplied exact zero that
    # disables a feature (e.g. ``pRatedLinearOperCost == 0.0`` -> the unit
    # is RES, not thermal; ``pNetFixedCost == 0.0`` -> not an investment
    # candidate). Replacing them with ``abs(x) < tol`` would change
    # semantics and reclassify units that have a tiny non-zero rate.
    # Keep `== 0.0` here on purpose; if you need a near-zero numerical
    # comparison anywhere downstream, introduce it explicitly.

    StartTime = time.time()
    #%% Getting the branches from the electric network data
    sBr     = [(ni,nf) for ni,nf,cc in dfs['dfNetwork'].index]
    # Dropping duplicate keys
    sBrList = [(ni,nf) for n,(ni,nf)  in enumerate(sBr) if (ni,nf) not in sBr[:n]]

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the electric lines (la), candidate electric lines (lc), candidate DC electric lines (cd), existing DC electric lines (cd), electric lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.p      = Set(doc='periods'                          , initialize=[pp     for pp   in mTEPES.pp  if par['pPeriodWeight']       [pp] >  0.0 and sum(par['pDuration'][pp,sc,n] for sc,n in mTEPES.scc*mTEPES.nn)])
    mTEPES.sc     = Set(doc='scenarios'                        , initialize=[scc    for scc  in mTEPES.scc                                                  ])
    mTEPES.ps     = Set(doc='periods/scenarios'                , initialize=[(p,sc) for p,sc in mTEPES.p*mTEPES.sc if par['pScenProb'] [p,sc] >  0.0 and sum(par['pDuration'][p,sc,n ] for    n in            mTEPES.nn)])
    mTEPES.st     = Set(doc='stages'                           , initialize=[stt    for stt  in mTEPES.stt if par['pStageWeight']       [stt] >  0.0])
    mTEPES.n      = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(par['pDuration']  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2     = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(par['pDuration']  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.g      = Set(doc='generating              units'    , initialize=[gg     for gg   in mTEPES.gg  if (par['pRatedMaxPowerElec'] [gg] >  0.0 or  par['pRatedMaxCharge'][gg] >  0.0   or  par['pRatedMaxPowerHeat']   [gg] >  0.0) and par['pElecGenPeriodIni'][gg] <= mTEPES.p.last() and par['pElecGenPeriodFin'][gg] >= mTEPES.p.first() and par['pGenToNode'].reset_index().set_index(['Generator']).isin(mTEPES.nd)['Node'][gg]])  # excludes generators with empty node
    mTEPES.tr     = Set(doc='thermal                 units'    , initialize=[g      for g    in mTEPES.g   if par['pRatedLinearOperCost'][g ] >  0.0])
    mTEPES.re     = Set(doc='RES                     units'    , initialize=[g      for g    in mTEPES.g   if par['pRatedLinearOperCost'][g ] == 0.0 and par['pRatedMaxStorage'][g] == 0.0   and par['pProductionFunctionH2'][g ] == 0.0 and par['pProductionFunctionHeat'][g ]       == 0.0  and par['pProductionFunctionHydro'][g ] == 0.0])
    mTEPES.es     = Set(doc='ESS                     units'    , initialize=[g      for g    in mTEPES.g   if     (par['pRatedMaxCharge'][g ] >  0.0 or  par['pRatedMaxStorage'][g] >  0.0    or par['pProductionFunctionH2'][g ]  > 0.0  or par['pProductionFunctionHeat'][g ]        > 0.0) and par['pProductionFunctionHydro'][g ] == 0.0])
    mTEPES.h      = Set(doc='hydro                   units'    , initialize=[g      for g    in mTEPES.g                                                                                                      if par['pProductionFunctionH2'][g ] == 0.0 and par['pProductionFunctionHeat'][g ]       == 0.0  and par['pProductionFunctionHydro'][g ]  > 0.0])
    mTEPES.el     = Set(doc='electrolyzer            units'    , initialize=[es     for es   in mTEPES.es                                                                                                     if par['pProductionFunctionH2'][es]  > 0.0 and par['pProductionFunctionHeat'][es]       == 0.0  and par['pProductionFunctionHydro'][es] == 0.0])
    mTEPES.hp     = Set(doc='heat pump & elec boiler units'    , initialize=[es     for es   in mTEPES.es                                                                                                     if par['pProductionFunctionH2'][es] == 0.0 and par['pProductionFunctionHeat'][es]        > 0.0  and par['pProductionFunctionHydro'][es] == 0.0])
    mTEPES.ch     = Set(doc='CHP       & fuel boiler units'    , initialize=[g      for g    in mTEPES.g   if                                                    par['pRatedMaxPowerHeat'][g ] > 0.0 and par['pProductionFunctionHeat']    [g ] == 0.0])
    mTEPES.bo     = Set(doc='            fuel boiler units'    , initialize=[ch     for ch   in mTEPES.ch  if par['pRatedMaxPowerElec']  [ch] == 0.0 and par['pRatedMaxPowerHeat'][ch] > 0.0 and par['pProductionFunctionHeat']    [ch] == 0.0])
    mTEPES.hh     = Set(doc='        hydrogen boiler units'    , initialize=[bo     for bo   in mTEPES.bo                                                                                                     if par['pProductionFunctionH2ToHeat'][bo] >  0.0])
    mTEPES.gc     = Set(doc='candidate               units'    , initialize=[g      for g    in mTEPES.g   if par['pGenInvestCost']      [g ] >  0.0])
    mTEPES.gd     = Set(doc='retirement              units'    , initialize=[g      for g    in mTEPES.g   if par['pGenRetireCost']      [g ] >  0.0])
    mTEPES.ec     = Set(doc='candidate ESS           units'    , initialize=[es     for es   in mTEPES.es  if par['pGenInvestCost']      [es] >  0.0])
    mTEPES.bc     = Set(doc='candidate boiler        units'    , initialize=[bo     for bo   in mTEPES.bo  if par['pGenInvestCost']      [bo] >  0.0])
    mTEPES.br     = Set(doc='all input       electric branches', initialize=sBrList        )
    mTEPES.ln     = Set(doc='all input       electric lines'   , initialize=dfs['dfNetwork'].index)
    # detect lines with undefined nodes or circuits
    for ni,nf,cc in mTEPES.ln:
        if ni not in mTEPES.nd or nf not in mTEPES.nd or cc not in mTEPES.cc:
            raise ValueError(f'### Line {ni} {nf} {cc} has a node or a circuit not defined in the corresponding dictionary.')
        if ni == nf:
            raise ValueError(f'### Line {ni} {nf} {cc} has equal initial and final nodes.')
    if len(mTEPES.ln) != len(dfs['dfNetwork'].index):
        raise ValueError('### Some electric lines are invalid (not having reactance or are repeated) ', len(mTEPES.ln), len(dfs['dfNetwork'].index))
    mTEPES.la     = Set(doc='all real        electric lines'   , initialize=[ln     for ln   in mTEPES.ln if par['pLineX']              [ln] != 0.0 and par['pLineNTCFrw'][ln] > 0.0 and par['pLineNTCBck'][ln] > 0.0 and par['pElecNetPeriodIni'][ln]  <= mTEPES.p.last() and par['pElecNetPeriodFin'][ln]  >= mTEPES.p.first()])
    mTEPES.ls     = Set(doc='all real switch electric lines'   , initialize=[la     for la   in mTEPES.la if par['pIndBinLineSwitch']   [la]       ])
    mTEPES.lc     = Set(doc='candidate       electric lines'   , initialize=[la     for la   in mTEPES.la if par['pNetFixedCost']       [la] >  0.0])
    mTEPES.cd     = Set(doc='candidate    DC electric lines'   , initialize=[la     for la   in mTEPES.la if par['pNetFixedCost']       [la] >  0.0 and par['pLineType'][la] == 'DC'])
    mTEPES.ed     = Set(doc='existing     DC electric lines'   , initialize=[la     for la   in mTEPES.la if par['pNetFixedCost']       [la] == 0.0 and par['pLineType'][la] == 'DC'])
    mTEPES.ll     = Set(doc='loss            electric lines'   , initialize=[la     for la   in mTEPES.la if par['pLineLossFactor']     [la] >  0.0 and par['pIndBinNetLosses'] > 0 ])
    mTEPES.rf     = Set(doc='reference node'                   , initialize=[par['pReferenceNode']])
    mTEPES.gq     = Set(doc='gen    reactive units'            , initialize=[gg     for gg   in mTEPES.gg if par['pRMaxReactivePower']  [gg] >  0.0 and                                                                    par['pElecGenPeriodIni'][gg]  <= mTEPES.p.last() and par['pElecGenPeriodFin'][gg]  >= mTEPES.p.first()])
    mTEPES.sq     = Set(doc='synchr reactive units'            , initialize=[gg     for gg   in mTEPES.gg if par['pRMaxReactivePower']  [gg] >  0.0 and par['pGenToTechnology'][gg] == 'SynchronousCondenser'  and par['pElecGenPeriodIni'][gg]  <= mTEPES.p.last() and par['pElecGenPeriodFin'][gg]  >= mTEPES.p.first()])
    mTEPES.sqc    = Set(doc='synchr reactive candidate')
    mTEPES.shc    = Set(doc='shunt           candidate')
    if par['pIndHydroTopology']:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[rs     for rs   in mTEPES.rs if par['pRsrInvestCost']      [rs] >  0.0 and                                                                    par['pRsrPeriodIni'][rs]      <= mTEPES.p.last() and par['pRsrPeriodFin'][rs]      >= mTEPES.p.first()])
    else:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[])
    if par['pIndHydrogen']:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=dfs['dfNetworkHydrogen'].index)
        if len(mTEPES.pn) != len(dfs['dfNetworkHydrogen'].index):
            raise ValueError('### Some hydrogen pipes are invalid ', len(mTEPES.pn), len(dfs['dfNetworkHydrogen'].index))
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[pn     for pn   in mTEPES.pn if par['pH2PipeNTCFrw']       [pn] >  0.0 and par['pH2PipeNTCBck'][pn] > 0.0 and                         par['pH2PipePeriodIni'][pn]   <= mTEPES.p.last() and par['pH2PipePeriodFin'][pn]   >= mTEPES.p.first()])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[pa     for pa   in mTEPES.pa if par['pH2PipeFixedCost']    [pa] >  0.0])
        # existing hydrogen pipelines (pe)
        mTEPES.pe = mTEPES.pa - mTEPES.pc
    else:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=[])
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[])

    if par['pIndHeat']:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=dfs['dfNetworkHeat'].index)
        if len(mTEPES.hn) != len(dfs['dfNetworkHeat'].index):
            raise ValueError('### Some heat pipes are invalid ', len(mTEPES.hn), len(dfs['dfNetworkHeat'].index))
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[hn     for hn   in mTEPES.hn if par['pHeatPipeNTCFrw']     [hn] >  0.0 and par['pHeatPipeNTCBck'][hn] > 0.0 and par['pHeatPipePeriodIni'][hn] <= mTEPES.p.last() and par['pHeatPipePeriodFin'][hn] >= mTEPES.p.first()])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[ha     for ha   in mTEPES.ha if par['pHeatPipeFixedCost']  [ha] >  0.0])
        # existing heat pipes (he)
        mTEPES.he = mTEPES.ha - mTEPES.hc
    else:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=[])
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[])

    par['pIndBinLinePTDF'] = pd.Series(index=mTEPES.la, data=0.0)                                                              # indicate if the line has a PTDF or not
    if par['pIndVarTTC']:
        par['pVariableNTCFrw'] = par['pVariableNTCFrw'].reindex(columns=mTEPES.la, fill_value=0.0) * dfs['dfNetwork']['SecurityFactor']      # variable NTC forward  direction because of the security factor
        par['pVariableNTCBck'] = par['pVariableNTCBck'].reindex(columns=mTEPES.la, fill_value=0.0) * dfs['dfNetwork']['SecurityFactor']      # variable NTC backward direction because of the security factor
    if par['pIndPTDF']:
        # get the level_3, level_4, and level_5 from multiindex of pVariablePTDF
        PTDF_columns = par['pVariablePTDF'].columns
        PTDF_lines   = PTDF_columns.droplevel([3]).drop_duplicates()
        par['pIndBinLinePTDF'].loc[:] = par['pIndBinLinePTDF'].index.isin(PTDF_lines).astype(float)

    # non-RES units, they can be committed and also contribute to the operating reserves
    mTEPES.nr = mTEPES.g - mTEPES.re
    # machines able to provide reactive power
    mTEPES.tq = mTEPES.gq - mTEPES.sq
    # existing electric lines (le)
    mTEPES.le = mTEPES.la - mTEPES.lc
    # ESS and hydro units
    mTEPES.eh = mTEPES.es | mTEPES.h
    # heat producers (CHP, heat pump and boiler)
    mTEPES.chp = mTEPES.ch | mTEPES.hp
    # CHP, heat pump and boiler (heat generator) candidates
    mTEPES.gb = (mTEPES.gc & mTEPES.chp) | mTEPES.bc
    # electricity and heat generator candidates
    mTEPES.eb = mTEPES.gc | mTEPES.bc

    #%% inverse index load level to stage
    par['pStageToLevel'] = par['pLevelToStage'].reset_index().set_index(['Period','Scenario','Stage'])['LoadLevel']
    #Filter only valid indices
    par['pStageToLevel'] = par['pStageToLevel'].loc[par['pStageToLevel'].index.isin([(p,s,st) for p,s in mTEPES.ps for st in mTEPES.st]) & par['pStageToLevel'].isin(mTEPES.n)]
    #Reorder the elements
    par['pStageToLevel'] = [(p,sc,st,n) for (p,sc,st),n in par['pStageToLevel'].items()]
    mTEPES.s2n = Set(initialize=par['pStageToLevel'], doc='Load level to stage')
    # all the stages must have the same duration
    par['pStageDuration'] = pd.Series([sum(par['pDuration'][p,sc,n] for p,sc,st2,n in mTEPES.s2n if st2 == st) for st in mTEPES.st], index=mTEPES.st)
    # for st in mTEPES.st:
    #     if mTEPES.st.ord(st) > 1 and pStageDuration[st] != pStageDuration[mTEPES.st.prev(st)]:
    #         assert (0 == 1)

    # delete all the load level belonging to stages with duration equal to zero
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.n  = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(par['pDuration'][p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(par['pDuration'][p,sc,nn] for p,sc in mTEPES.ps) > 0])
    # instrumental sets
    # @profile
    def CreateInstrumentalSets(mTEPES, pIndHydroTopology, pIndHydrogen, pIndHeat, pIndPTDF) -> None:
        '''
                Create mTEPES instrumental sets.

                This function takes an mTEPES instance and adds instrumental sets which will be used later.

                Parameters:
                    mTEPES: The instance of mTEPES.

                Returns:
                    None: Sets are added directly to the mTEPES object.
                '''
        mTEPES.pg        = Set(initialize = [(p,     g       ) for p,     g        in mTEPES.p  *mTEPES.g   if par['pElecGenPeriodIni'][g ] <= p and par['pElecGenPeriodFin'][g ] >= p])
        mTEPES.ptr       = Set(initialize = [(p,     tr      ) for p,     tr       in mTEPES.p  *mTEPES.tr  if (p,tr)  in mTEPES.pg])
        mTEPES.pgc       = Set(initialize = [(p,     gc      ) for p,     gc       in mTEPES.p  *mTEPES.gc  if (p,gc)  in mTEPES.pg])
        mTEPES.pnr       = Set(initialize = [(p,     nr      ) for p,     nr       in mTEPES.p  *mTEPES.nr  if (p,nr)  in mTEPES.pg])
        mTEPES.pch       = Set(initialize = [(p,     ch      ) for p,     ch       in mTEPES.p  *mTEPES.ch  if (p,ch)  in mTEPES.pg])
        mTEPES.pchp      = Set(initialize = [(p,     chp     ) for p,     chp      in mTEPES.p  *mTEPES.chp if (p,chp) in mTEPES.pg])
        mTEPES.pbo       = Set(initialize = [(p,     bo      ) for p,     bo       in mTEPES.p  *mTEPES.bo  if (p,bo)  in mTEPES.pg])
        mTEPES.php       = Set(initialize = [(p,     hp      ) for p,     hp       in mTEPES.p  *mTEPES.hp  if (p,hp)  in mTEPES.pg])
        mTEPES.phh       = Set(initialize = [(p,     hh      ) for p,     hh       in mTEPES.p  *mTEPES.hh  if (p,hh)  in mTEPES.pg])
        mTEPES.pbc       = Set(initialize = [(p,     bc      ) for p,     bc       in mTEPES.p  *mTEPES.bc  if (p,bc)  in mTEPES.pg])
        mTEPES.pgb       = Set(initialize = [(p,     gb      ) for p,     gb       in mTEPES.p  *mTEPES.gb  if (p,gb)  in mTEPES.pg])
        mTEPES.peb       = Set(initialize = [(p,     eb      ) for p,     eb       in mTEPES.p  *mTEPES.eb  if (p,eb)  in mTEPES.pg])
        mTEPES.pes       = Set(initialize = [(p,     es      ) for p,     es       in mTEPES.p  *mTEPES.es  if (p,es)  in mTEPES.pg])
        mTEPES.pec       = Set(initialize = [(p,     ec      ) for p,     ec       in mTEPES.p  *mTEPES.ec  if (p,ec)  in mTEPES.pg])
        mTEPES.peh       = Set(initialize = [(p,     eh      ) for p,     eh       in mTEPES.p  *mTEPES.eh  if (p,eh)  in mTEPES.pg])
        mTEPES.pre       = Set(initialize = [(p,     re      ) for p,     re       in mTEPES.p  *mTEPES.re  if (p,re)  in mTEPES.pg])
        mTEPES.ph        = Set(initialize = [(p,     h       ) for p,     h        in mTEPES.p  *mTEPES.h   if (p,h )  in mTEPES.pg])
        mTEPES.pgd       = Set(initialize = [(p,     gd      ) for p,     gd       in mTEPES.p  *mTEPES.gd  if (p,gd)  in mTEPES.pg])
        mTEPES.par       = Set(initialize = [(p,     ar      ) for p,     ar       in mTEPES.p  *mTEPES.ar                         ])
        mTEPES.pla       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.la  if par['pElecNetPeriodIni'][ni,nf,cc] <= p and par['pElecNetPeriodFin'][ni,nf,cc] >= p])
        mTEPES.plc       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.lc  if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.pll       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ll  if (p,ni,nf,cc) in mTEPES.pla])

        mTEPES.psg       = Set(initialize = [(p,sc,  g )       for p,sc,  g        in mTEPES.ps *mTEPES.g   if (p,g )  in mTEPES.pg  ])
        mTEPES.psnr      = Set(initialize = [(p,sc,  nr)       for p,sc,  nr       in mTEPES.ps *mTEPES.nr  if (p,nr)  in mTEPES.pnr ])
        mTEPES.pses      = Set(initialize = [(p,sc,  es)       for p,sc,  es       in mTEPES.ps *mTEPES.es  if (p,es)  in mTEPES.pes ])
        mTEPES.pseh      = Set(initialize = [(p,sc,  eh)       for p,sc,  eh       in mTEPES.ps *mTEPES.eh  if (p,eh)  in mTEPES.peh ])
        mTEPES.psn       = Set(initialize = [(p,sc,n   )       for p,sc,n          in mTEPES.ps *mTEPES.n   if par['pDuration'][p,sc,n]])
        mTEPES.psng      = Set(initialize = [(p,sc,n,g )       for p,sc,n,g        in mTEPES.psn*mTEPES.g   if (p,g )  in mTEPES.pg  ])
        mTEPES.psntr     = Set(initialize = [(p,sc,n,tr)       for p,sc,n,tr       in mTEPES.psn*mTEPES.tr  if (p,tr)  in mTEPES.ptr ])
        mTEPES.psngc     = Set(initialize = [(p,sc,n,gc)       for p,sc,n,gc       in mTEPES.psn*mTEPES.gc  if (p,gc)  in mTEPES.pgc ])
        mTEPES.psngb     = Set(initialize = [(p,sc,n,gb)       for p,sc,n,gb       in mTEPES.psn*mTEPES.gb  if (p,gb)  in mTEPES.pgc ])
        mTEPES.psnre     = Set(initialize = [(p,sc,n,re)       for p,sc,n,re       in mTEPES.psn*mTEPES.re  if (p,re)  in mTEPES.pre ])
        mTEPES.psnnr     = Set(initialize = [(p,sc,n,nr)       for p,sc,n,nr       in mTEPES.psn*mTEPES.nr  if (p,nr)  in mTEPES.pnr ])
        mTEPES.psnch     = Set(initialize = [(p,sc,n,ch)       for p,sc,n,ch       in mTEPES.psn*mTEPES.ch  if (p,ch)  in mTEPES.pch ])
        mTEPES.psnchp    = Set(initialize = [(p,sc,n,chp)      for p,sc,n,chp      in mTEPES.psn*mTEPES.chp if (p,chp) in mTEPES.pchp])
        mTEPES.psnbo     = Set(initialize = [(p,sc,n,bo)       for p,sc,n,bo       in mTEPES.psn*mTEPES.bo  if (p,bo)  in mTEPES.pbo ])
        mTEPES.psnhp     = Set(initialize = [(p,sc,n,hp)       for p,sc,n,hp       in mTEPES.psn*mTEPES.hp  if (p,hp)  in mTEPES.php ])
        mTEPES.psneb     = Set(initialize = [(p,sc,n,eb)       for p,sc,n,eb       in mTEPES.psn*mTEPES.eb  if (p,eb)  in mTEPES.peb ])
        mTEPES.psnes     = Set(initialize = [(p,sc,n,es)       for p,sc,n,es       in mTEPES.psn*mTEPES.es  if (p,es)  in mTEPES.pes ])
        mTEPES.psneh     = Set(initialize = [(p,sc,n,eh)       for p,sc,n,eh       in mTEPES.psn*mTEPES.eh  if (p,eh)  in mTEPES.peh ])
        mTEPES.psnel     = Set(initialize = [(p,sc,n,el)       for p,sc,n,el       in mTEPES.psn*mTEPES.el  if (p,el)  in mTEPES.peh ])
        mTEPES.psnec     = Set(initialize = [(p,sc,n,ec)       for p,sc,n,ec       in mTEPES.psn*mTEPES.ec  if (p,ec)  in mTEPES.pec ])
        mTEPES.psnnd     = Set(initialize = [(p,sc,n,nd)       for p,sc,n,nd       in mTEPES.psn*mTEPES.nd                           ])
        mTEPES.psnar     = Set(initialize = [(p,sc,n,ar)       for p,sc,n,ar       in mTEPES.psn*mTEPES.ar                           ])

        mTEPES.psnla     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.la if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.psnle     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.le if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.psnll     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ll if (p,ni,nf,cc) in mTEPES.pll])
        mTEPES.psnls     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ls if (p,ni,nf,cc) in mTEPES.pla])

        mTEPES.psnehc    = Set(initialize = [(p,sc,n,eh)       for p,sc,n,eh       in mTEPES.psneh         if par['pRatedMaxCharge'][eh] > 0.0])

        if pIndHydroTopology:
            mTEPES.prs   = Set(initialize = [(p,     rs)       for p,     rs       in mTEPES.p  *mTEPES.rs if par['pRsrPeriodIni'][rs] <= p and par['pRsrPeriodFin'][rs] >= p])
            mTEPES.prc   = Set(initialize = [(p,     rc)       for p,     rc       in mTEPES.p  *mTEPES.rn if (p,rc) in mTEPES.prs])
            mTEPES.psrs  = Set(initialize = [(p,sc,  rs)       for p,sc,  rs       in mTEPES.ps *mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnh  = Set(initialize = [(p,sc,n,h )       for p,sc,n,h        in mTEPES.psn*mTEPES.h  if (p,h ) in mTEPES.ph ])
            mTEPES.psnrs = Set(initialize = [(p,sc,n,rs)       for p,sc,n,rs       in mTEPES.psn*mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnrc = Set(initialize = [(p,sc,n,rc)       for p,sc,n,rc       in mTEPES.psn*mTEPES.rn if (p,rc) in mTEPES.prc])
        else:
            mTEPES.prc   = []

        if pIndHydrogen:
            mTEPES.ppa   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pa if par['pH2PipePeriodIni'][ni,nf,cc] <= p and par['pH2PipePeriodFin'][ni,nf,cc] >= p])
            mTEPES.ppc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pn if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpa = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pa if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pe if (p,ni,nf,cc) in mTEPES.ppa])
        else:
            mTEPES.ppc   = Set(initialize = [])

        if pIndHeat:
            mTEPES.pha   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ha if par['pHeatPipePeriodIni'][ni,nf,cc] <= p and par['pHeatPipePeriodFin'][ni,nf,cc] >= p])
            mTEPES.phc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.hc if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.hn if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnha = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ha if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.he if (p,ni,nf,cc) in mTEPES.pha])
        else:
            mTEPES.phc   = Set(initialize = [])

        if pIndPTDF:
            mTEPES.psnland = Set(initialize = [(p,sc,n,ni,nf,cc,nd) for p,sc,n,ni,nf,cc,nd in mTEPES.psnla*mTEPES.nd if (ni,nf,cc,nd) in par['pVariablePTDF'].columns])

        # assigning a node to an area
        mTEPES.ndar = Set(initialize = [(nd,ar) for nd,zn,ar in mTEPES.ndzn*mTEPES.ar if (zn,ar) in mTEPES.znar])
        mTEPES.arnd = Set(initialize = [(ar,nd) for nd,   ar in mTEPES.ndar])

        # assigning a line to an area. Both nodes are in the same area. Cross-area lines are not included
        mTEPES.laar = Set(initialize = [(ni,nf,cc,ar) for ni,nf,cc,ar in mTEPES.la*mTEPES.ar if (ni,ar) in mTEPES.ndar and (nf,ar) in mTEPES.ndar])


    CreateInstrumentalSets(mTEPES, par['pIndHydroTopology'], par['pIndHydrogen'], par['pIndHeat'], par['pIndPTDF'])

    # replacing string values by numerical values
    idxDict = dict()
    idxDict[0    ] = 0
    idxDict[0.0  ] = 0
    idxDict['No' ] = 0
    idxDict['NO' ] = 0
    idxDict['no' ] = 0
    idxDict['N'  ] = 0
    idxDict['n'  ] = 0
    idxDict['Yes'] = 1
    idxDict['YES'] = 1
    idxDict['yes'] = 1
    idxDict['Y'  ] = 1
    idxDict['y'  ] = 1

    par['pIndBinUnitInvest']         = par['pIndBinUnitInvest'].map    (idxDict)
    par['pIndBinUnitRetire']         = par['pIndBinUnitRetire'].map    (idxDict)
    par['pIndBinUnitCommit']         = par['pIndBinUnitCommit'].map    (idxDict)
    par['pIndBinStorInvest']         = par['pIndBinStorInvest'].map    (idxDict)
    par['pIndBinLineInvest']         = par['pIndBinLineInvest'].map    (idxDict)
    par['pIndBinLineSwitch']         = par['pIndBinLineSwitch'].map    (idxDict)
    # par['pIndOperReserve']           = par['pIndOperReserve'].map      (idxDict)
    par['pIndOutflowIncomp']         = par['pIndOutflowIncomp'].map    (idxDict)
    par['pMustRun']                  = par['pMustRun'].map             (idxDict)

    # Operating reserves can be provided while generating or while consuming
    # So there is need for two options to decide if the unit is able to provide them
    # Due to backwards compatibility reasons instead of adding a new column to Data_Generation NoOperatingReserve column now accepts two inputs
    # They are separated by "|", if only one input is detected, both parameters are set to whatever the input is

    def split_and_map(val):
        # Handle new format with double input. Detect if there is a | character
        if isinstance(val, str) and '|' in val:
            gen, cons = val.split('|', 1)
            return pd.Series([idxDict.get(gen.strip(), 0), idxDict.get(cons.strip(), 0)])
        else:
        # If no | character is found, both options are set to the inputted value
            mapped = idxDict.get(val, 0)
            return pd.Series([mapped, mapped])

    # Split the columns in pIndOperReserve and group them in Generation and Consumption tuples
    par['pIndOperReserveGen'], par['pIndOperReserveCon'] = zip(*par['pIndOperReserve'].map(split_and_map))

    par['pIndOperReserveGen'] = pd.Series(par['pIndOperReserveGen'], index=par['pIndOperReserve'].index)
    par['pIndOperReserveCon'] = pd.Series(par['pIndOperReserveCon'], index=par['pIndOperReserve'].index)

    if par['pIndHydroTopology']:
        par['pIndBinRsrvInvest']     = par['pIndBinRsrvInvest'].map    (idxDict)

    if par['pIndHydrogen']:
        par['pIndBinH2PipeInvest']   = par['pIndBinH2PipeInvest'].map  (idxDict)

    if par['pIndHeat']:
        par['pIndBinHeatPipeInvest'] = par['pIndBinHeatPipeInvest'].map(idxDict)

    # define AC existing  lines     non-switchable lines
    mTEPES.lea = Set(doc='AC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  par['pIndBinLineSwitch'][le] == 0                                            and not par['pLineType'][le] == 'DC'])
    # define AC candidate lines and     switchable lines
    mTEPES.lca = Set(doc='AC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (par['pIndBinLineSwitch'][la] == 1 or par['pNetFixedCost'][la] > 0.0) and not par['pLineType'][la] == 'DC'])

    mTEPES.laa = mTEPES.lea | mTEPES.lca

    # define DC existing  lines     non-switchable lines
    mTEPES.led = Set(doc='DC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  par['pIndBinLineSwitch'][le] == 0                                            and     par['pLineType'][le] == 'DC'])
    # define DC candidate lines and     switchable lines
    mTEPES.lcd = Set(doc='DC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (par['pIndBinLineSwitch'][la] == 1 or par['pNetFixedCost'][la] > 0.0) and     par['pLineType'][la] == 'DC'])

    mTEPES.lad = mTEPES.led | mTEPES.lcd

    # line type
    par['pLineType'] = par['pLineType'].reset_index().set_index(['InitialNode', 'FinalNode', 'Circuit', 'LineType'])

    mTEPES.pLineType = Set(initialize=par['pLineType'].index, doc='line type')

    if par['pAnnualDiscountRate'] == 0.0:
        par['pDiscountedWeight'] = pd.Series([                                           par['pPeriodWeight'][p]                                                                                                                                                              for p in mTEPES.p], index=mTEPES.p)
    else:
        par['pDiscountedWeight'] = pd.Series([((1.0+par['pAnnualDiscountRate'])**par['pPeriodWeight'][p]-1.0) / (par['pAnnualDiscountRate']*(1.0+par['pAnnualDiscountRate'])**(par['pPeriodWeight'][p]-1+p-par['pEconomicBaseYear'])) for p in mTEPES.p], index=mTEPES.p)

    mTEPES.pLoadLevelWeight = Param(mTEPES.psn, initialize=0.0, within=NonNegativeReals, doc='Load level weight', mutable=True)
    for p,sc,st,n in mTEPES.s2n:
        mTEPES.pLoadLevelWeight[p,sc,n] = par['pStageWeight'][st]

    #%% inverse index node to generator
    par['pNodeToGen'] = par['pGenToNode'].reset_index().set_index('Node').set_axis(['Generator'], axis=1)[['Generator']]
    par['pNodeToGen'] = par['pNodeToGen'].loc[par['pNodeToGen']['Generator'].isin(mTEPES.g)].reset_index().set_index(['Node', 'Generator'])

    mTEPES.n2g = Set(initialize=par['pNodeToGen'].index, doc='node   to generator')

    mTEPES.z2g = Set(doc='zone   to generator', initialize=[(zn,g) for nd,g,zn       in mTEPES.n2g*mTEPES.zn             if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.a2g = Set(doc='area   to generator', initialize=[(ar,g) for nd,g,zn,ar    in mTEPES.n2g*mTEPES.znar           if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.r2g = Set(doc='region to generator', initialize=[(rg,g) for nd,g,zn,ar,rg in mTEPES.n2g*mTEPES.znar*mTEPES.rg if (nd,zn) in mTEPES.ndzn and [ar,rg] in mTEPES.arrg])

    # mTEPES.z2g  = Set(initialize = [(zn,g) for zn,g in mTEPES.zn*mTEPES.g if (zn,g) in pZone2Gen])

    # detect technologies not declared in the technology dictionary
    for g in mTEPES.g:
        if par['pGenToTechnology'].loc[g] not in mTEPES.gt:
            raise ValueError(f'### Generator {g} belongs to a technology not declared in the technology dictionary.')

    #%% inverse index generator to technology
    par['pTechnologyToGen'] = par['pGenToTechnology'].reset_index().set_index('Technology').set_axis(['Generator'], axis=1)[['Generator']]
    par['pTechnologyToGen'] = par['pTechnologyToGen'].loc[par['pTechnologyToGen']['Generator'].isin(mTEPES.g)].reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=par['pTechnologyToGen'].index, doc='technology to generator')

    g2t = defaultdict(list)
    for gt,g in mTEPES.t2g:
        g2t[gt].append(g)

    # ESS and RES technologies
    def Create_ESS_RES_Sets(mTEPES) -> None:
        mTEPES.ot = Set(doc='ESS         technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for es in mTEPES.es if es in g2t[gt])])
        mTEPES.ht = Set(doc='hydro       technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for h  in mTEPES.h  if h  in g2t[gt])])
        mTEPES.et = Set(doc='ESS & hydro technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for eh in mTEPES.eh if eh in g2t[gt])])
        mTEPES.rt = Set(doc='    RES     technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for re in mTEPES.re if re in g2t[gt])])
        mTEPES.nt = Set(doc='non-RES     technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for nr in mTEPES.nr if nr in g2t[gt])])

        mTEPES.psgt  = Set(initialize=[(p,sc,  gt) for p,sc,  gt in mTEPES.ps *mTEPES.gt   if sum(1 for g  in mTEPES.g  if g  in g2t[gt] and (p,g ) in mTEPES.pg )])
        mTEPES.psot  = Set(initialize=[(p,sc,  ot) for p,sc,  ot in mTEPES.ps *mTEPES.ot   if sum(1 for es in mTEPES.es if es in g2t[ot] and (p,es) in mTEPES.pes)])
        mTEPES.psht  = Set(initialize=[(p,sc,  ht) for p,sc,  ht in mTEPES.ps *mTEPES.ht   if sum(1 for h  in mTEPES.h  if h  in g2t[ht] and (p,h ) in mTEPES.ph )])
        mTEPES.pset  = Set(initialize=[(p,sc,  et) for p,sc,  et in mTEPES.ps *mTEPES.et   if sum(1 for eh in mTEPES.eh if eh in g2t[et] and (p,eh) in mTEPES.peh)])
        mTEPES.psrt  = Set(initialize=[(p,sc,  rt) for p,sc,  rt in mTEPES.ps *mTEPES.rt   if sum(1 for re in mTEPES.re if re in g2t[rt] and (p,re) in mTEPES.pre)])
        mTEPES.psnt  = Set(initialize=[(p,sc,  nt) for p,sc,  nt in mTEPES.ps *mTEPES.nt   if sum(1 for nr in mTEPES.nr if nr in g2t[nt] and (p,nr) in mTEPES.pnr)])
        mTEPES.psngt = Set(initialize=[(p,sc,n,gt) for p,sc,n,gt in mTEPES.psn*mTEPES.gt   if (p,sc,  gt) in mTEPES.psgt ])
        mTEPES.psnot = Set(initialize=[(p,sc,n,ot) for p,sc,n,ot in mTEPES.psn*mTEPES.ot   if (p,sc,n,ot) in mTEPES.psngt])
        mTEPES.psnht = Set(initialize=[(p,sc,n,ht) for p,sc,n,ht in mTEPES.psn*mTEPES.ht   if (p,sc,n,ht) in mTEPES.psngt])
        mTEPES.psnet = Set(initialize=[(p,sc,n,et) for p,sc,n,et in mTEPES.psn*mTEPES.et   if (p,sc,n,et) in mTEPES.psngt])
        mTEPES.psnrt = Set(initialize=[(p,sc,n,rt) for p,sc,n,rt in mTEPES.psn*mTEPES.rt   if (p,sc,n,rt) in mTEPES.psngt])
        mTEPES.psnnt = Set(initialize=[(p,sc,n,nt) for p,sc,n,nt in mTEPES.psn*mTEPES.nt   if (p,sc,n,nt) in mTEPES.psngt])

    Create_ESS_RES_Sets(mTEPES)

    # Create mutually exclusive groups
    # Store in a group-generator dictionary all the relevant data
    group_dict = {}
    for generator, groups in par['pGenToExclusiveGen'].items():
        if groups != 0.0:
            for group in str(groups).split('|'):
                group_dict.setdefault(group, []).append(generator)

    # These sets store all groups and the generators in them
    mTEPES.ExclusiveGroups            = Set(initialize=list(group_dict.keys()))
    mTEPES.GeneratorsInExclusiveGroup = Set(mTEPES.ExclusiveGroups, initialize=group_dict)

    # Create filtered dictionaries for Yearly and Hourly groups
    group_dict_yearly = {}
    group_dict_hourly = {}

    for group, generators in group_dict.items():
        if all(gen in mTEPES.gc for gen in generators):
            group_dict_yearly[group] = generators
        else:
            group_dict_hourly[group] = generators

    # The exclusive groups sets have all groups which are mutually exclusive in that time scope
    # Generators in group sets are sets with the corresponding generators to a given group
    mTEPES.ExclusiveGroupsYearly   = Set(initialize=list(group_dict_yearly.keys()))
    mTEPES.GeneratorsInYearlyGroup = Set(mTEPES.ExclusiveGroupsYearly, initialize=group_dict_yearly)

    mTEPES.ExclusiveGroupsHourly   = Set(initialize=list(group_dict_hourly.keys()))
    mTEPES.GeneratorsInHourlyGroup = Set(mTEPES.ExclusiveGroupsHourly, initialize=group_dict_hourly)

    # All exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGenerators       = Set(initialize=sorted(sum(group_dict.values(),        [])))
    # All yearly exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGeneratorsYearly = Set(initialize=sorted(sum(group_dict_yearly.values(), [])))
    # All hourly exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGeneratorsHourly = Set(initialize=sorted(sum(group_dict_hourly.values(), [])))

    # minimum and maximum variable power, charge, and storage capacity
    par['pMinPowerElec']  = par['pVariableMinPowerElec'].replace(0.0, par['pRatedMinPowerElec'])
    par['pMaxPowerElec']  = par['pVariableMaxPowerElec'].replace(0.0, par['pRatedMaxPowerElec'])
    par['pMinCharge']     = par['pVariableMinCharge'].replace   (0.0, par['pRatedMinCharge']   )
    par['pMaxCharge']     = par['pVariableMaxCharge'].replace   (0.0, par['pRatedMaxCharge']   )
    par['pMinStorage']    = par['pVariableMinStorage'].replace  (0.0, par['pRatedMinStorage']  )
    par['pMaxStorage']    = par['pVariableMaxStorage'].replace  (0.0, par['pRatedMaxStorage']  )
    if par['pIndHydroTopology']:
        par['pMinVolume'] = par['pVariableMinVolume'].replace   (0.0, par['pRatedMinVolume']   )
        par['pMaxVolume'] = par['pVariableMaxVolume'].replace   (0.0, par['pRatedMaxVolume']   )

    par['pMinPowerElec']  = par['pMinPowerElec'].where(par['pMinPowerElec'] > 0.0, 0.0)
    par['pMaxPowerElec']  = par['pMaxPowerElec'].where(par['pMaxPowerElec'] > 0.0, 0.0)
    par['pMinCharge']     = par['pMinCharge'].where   (par['pMinCharge']    > 0.0, 0.0)
    par['pMaxCharge']     = par['pMaxCharge'].where   (par['pMaxCharge']    > 0.0, 0.0)
    par['pMinStorage']    = par['pMinStorage'].where  (par['pMinStorage']   > 0.0, 0.0)
    par['pMaxStorage']    = par['pMaxStorage'].where  (par['pMaxStorage']   > 0.0, 0.0)
    if par['pIndHydroTopology']:
        par['pMinVolume'] = par['pMinVolume'].where   (par['pMinVolume']    > 0.0, 0.0)
        par['pMaxVolume'] = par['pMaxVolume'].where   (par['pMaxVolume']    > 0.0, 0.0)

    # fuel term and constant term variable cost
    par['pVariableFuelCost'] = par['pVariableFuelCost'].replace(0.0, dfs['dfGeneration']['FuelCost'])
    par['pLinearVarCost']    = dfs['dfGeneration']['LinearTerm'  ] * 1e-3 * par['pVariableFuelCost'] + dfs['dfGeneration']['OMVariableCost'] * 1e-3
    par['pConstantVarCost']  = dfs['dfGeneration']['ConstantTerm'] * 1e-6 * par['pVariableFuelCost']
    par['pLinearVarCost']    = par['pLinearVarCost'].reindex  (sorted(par['pLinearVarCost'].columns  ), axis=1)
    par['pConstantVarCost']  = par['pConstantVarCost'].reindex(sorted(par['pConstantVarCost'].columns), axis=1)

    # variable emission cost [M€/GWh]
    par['pVariableEmissionCost'] = par['pVariableEmissionCost'].replace(0.0, par['pCO2Cost']) #[€/tCO2]
    par['pEmissionVarCost']      = par['pEmissionRate'] * 1e-3 * par['pVariableEmissionCost']                 # [M€/GWh] = [tCO2/MWh] * 1e-3 * [€/tCO2]
    par['pEmissionVarCost']      = par['pEmissionVarCost'].reindex(sorted(par['pEmissionVarCost'].columns), axis=1)

    # minimum up- and downtime and maximum shift time converted to an integer number of time steps
    par['pUpTime']     = round(par['pUpTime']    /mTEPES.pDurationNZMax).astype('int')
    par['pDwTime']     = round(par['pDwTime']    /mTEPES.pDurationNZMax).astype('int')
    par['pStableTime'] = round(par['pStableTime']/mTEPES.pDurationNZMax).astype('int')
    par['pShiftTime']  = round(par['pShiftTime'] /mTEPES.pDurationNZMax).astype('int')

    # %% definition of the time-steps leap to observe the stored energy at an ESS
    idxCycle            = dict()
    idxCycle[0        ] = 1
    idxCycle[0.0      ] = 1
    idxCycle['Hourly' ] = 1
    idxCycle['Daily'  ] = 1
    idxCycle['Weekly' ] = round(  24/mTEPES.pDurationNZMax)
    idxCycle['Monthly'] = round( 168/mTEPES.pDurationNZMax)
    idxCycle['Yearly' ] = round( 672/mTEPES.pDurationNZMax)

    idxOutflows            = dict()
    idxOutflows[0        ] = 1
    idxOutflows[0.0      ] = 1
    idxOutflows['Hourly' ] = 1
    idxOutflows['Daily'  ] = round(  24/mTEPES.pDurationNZMax)
    idxOutflows['Weekly' ] = round( 168/mTEPES.pDurationNZMax)
    idxOutflows['Monthly'] = round( 672/mTEPES.pDurationNZMax)
    idxOutflows['Yearly' ] = round(8736/mTEPES.pDurationNZMax)

    idxEnergy            = dict()
    idxEnergy[0        ] = 1
    idxEnergy[0.0      ] = 1
    idxEnergy['Hourly' ] = 1
    idxEnergy['Daily'  ] = round(  24/mTEPES.pDurationNZMax)
    idxEnergy['Weekly' ] = round( 168/mTEPES.pDurationNZMax)
    idxEnergy['Monthly'] = round( 672/mTEPES.pDurationNZMax)
    idxEnergy['Yearly' ] = round(8736/mTEPES.pDurationNZMax)

    par['pStorageTimeStep']  = par['pStorageType' ].map(idxCycle                                                                                                             ).astype('int')
    par['pOutflowsTimeStep'] = par['pOutflowsType'].map(idxOutflows).where(par['pEnergyOutflows'].sum()                                              > 0.0, other = 1).astype('int')
    par['pEnergyTimeStep']   = par['pEnergyType'  ].map(idxEnergy  ).where(par['pVariableMinEnergy'].sum() + par['pVariableMaxEnergy'].sum() > 0.0, other = 1).astype('int')

    par['pStorageTimeStep']  = pd.concat([par['pStorageTimeStep'], par['pOutflowsTimeStep'], par['pEnergyTimeStep']], axis=1).min(axis=1)
    # cycle time step can't exceed the stage duration
    par['pStorageTimeStep']  = par['pStorageTimeStep'].where(par['pStorageTimeStep'] <= par['pStageDuration'].min(), par['pStageDuration'].min())

    if par['pIndHydroTopology']:
        # %% definition of the time-steps leap to observe the stored energy at a reservoir
        idxCycleRsr            = dict()
        idxCycleRsr[0        ] = 1
        idxCycleRsr[0.0      ] = 1
        idxCycleRsr['Hourly' ] = 1
        idxCycleRsr['Daily'  ] = 1
        idxCycleRsr['Weekly' ] = round(  24/mTEPES.pDurationNZMax)
        idxCycleRsr['Monthly'] = round( 168/mTEPES.pDurationNZMax)
        idxCycleRsr['Yearly' ] = round( 672/mTEPES.pDurationNZMax)

        idxWaterOut            = dict()
        idxWaterOut[0        ] = 1
        idxWaterOut[0.0      ] = 1
        idxWaterOut['Hourly' ] = 1
        idxWaterOut['Daily'  ] = round(  24/mTEPES.pDurationNZMax)
        idxWaterOut['Weekly' ] = round( 168/mTEPES.pDurationNZMax)
        idxWaterOut['Monthly'] = round( 672/mTEPES.pDurationNZMax)
        idxWaterOut['Yearly' ] = round(8736/mTEPES.pDurationNZMax)

        par['pCycleRsrTimeStep'] = par['pReservoirType'].map(idxCycleRsr).astype('int')
        par['pWaterOutTimeStep'] = par['pWaterOutfType'].map(idxWaterOut).astype('int')

        par['pReservoirTimeStep'] = pd.concat([par['pCycleRsrTimeStep'], par['pWaterOutTimeStep']], axis=1).min(axis=1)
        # cycle water step can't exceed the stage duration
        par['pReservoirTimeStep'] = par['pReservoirTimeStep'].where(par['pReservoirTimeStep'] <= par['pStageDuration'].min(), par['pStageDuration'].min())

    # initial inventory must be between minimum and maximum
    par['pInitialInventory']  = par['pInitialInventory'].where(par['pInitialInventory'] > par['pRatedMinStorage'], par['pRatedMinStorage'])
    par['pInitialInventory']  = par['pInitialInventory'].where(par['pInitialInventory'] < par['pRatedMaxStorage'], par['pRatedMaxStorage'])
    if par['pIndHydroTopology']:
        par['pInitialVolume'] = par['pInitialVolume'].where   (par['pInitialVolume']    > par['pRatedMinVolume'],  par['pRatedMinVolume'] )
        par['pInitialVolume'] = par['pInitialVolume'].where   (par['pInitialVolume']    < par['pRatedMaxVolume'],  par['pRatedMaxVolume'] )

    # initial inventory of the candidate storage units equal to its maximum capacity if the storage capacity is linked to the investment decision
    par['pInitialInventory'].update(pd.Series([par['pInitialInventory'][ec] if par['pIndBinStorInvest'][ec] == 0 else par['pRatedMaxStorage'][ec] for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64'))

    # parameter that allows the initial inventory to change with load level
    par['pIniInventory']  = pd.DataFrame([par['pInitialInventory']]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.es)
    if par['pIndHydroTopology']:
        par['pIniVolume'] = pd.DataFrame([par['pInitialVolume']   ]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.rs)

    # initial inventory must be between minimum and maximum
    for p,sc,n,es in mTEPES.psnes:
        if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == par['pStorageTimeStep'][es]:
            if  par['pIniInventory'].at[(p,sc,n),es] < par['pMinStorage'].at[(p,sc,n),es]:
                par['pIniInventory'].at[(p,sc,n),es] = par['pMinStorage'].at[(p,sc,n),es]
                print('### Initial inventory lower than minimum storage ', p, sc, st, es)
            if  par['pIniInventory'].at[(p,sc,n),es] > par['pMaxStorage'].at[(p,sc,n),es]:
                par['pIniInventory'].at[(p,sc,n),es] = par['pMaxStorage'].at[(p,sc,n),es]
                print('### Initial inventory greater than maximum storage ', p, sc, st, es)
    if par['pIndHydroTopology']:
        for p,sc,n,rs in mTEPES.psnrs:
            if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == par['pReservoirTimeStep'][rs]:
                if  par['pIniVolume'].at[(p,sc,n),rs] < par['pMinVolume'].at[(p,sc,n),rs]:
                    par['pIniVolume'].at[(p,sc,n),rs] = par['pMinVolume'].at[(p,sc,n),rs]
                    print('### Initial volume lower than minimum volume ',   p, sc, st, rs)
                if  par['pIniVolume'].at[(p,sc,n),rs] > par['pMaxVolume'].at[(p,sc,n),rs]:
                    par['pIniVolume'].at[(p,sc,n),rs] = par['pMaxVolume'].at[(p,sc,n),rs]
                    print('### Initial volume greater than maximum volume ', p, sc, st, rs)

    # drop load levels with duration 0
    par['pDuration']            = par['pDuration'].loc            [mTEPES.psn  ]
    par['pDemandElec']          = par['pDemandElec'].loc          [mTEPES.psn  ]
    par['pSystemInertia']       = par['pSystemInertia'].loc       [mTEPES.psnar]
    par['pOperReserveUp']       = par['pOperReserveUp'].loc       [mTEPES.psnar]
    par['pOperReserveDw']       = par['pOperReserveDw'].loc       [mTEPES.psnar]
    par['pMinPowerElec']        = par['pMinPowerElec'].loc        [mTEPES.psn  ]
    par['pMaxPowerElec']        = par['pMaxPowerElec'].loc        [mTEPES.psn  ]
    par['pMinCharge']           = par['pMinCharge'].loc           [mTEPES.psn  ]
    par['pMaxCharge']           = par['pMaxCharge'].loc           [mTEPES.psn  ]
    par['pEnergyInflows']       = par['pEnergyInflows'].loc       [mTEPES.psn  ]
    par['pEnergyOutflows']      = par['pEnergyOutflows'].loc      [mTEPES.psn  ]
    par['pIniInventory']        = par['pIniInventory'].loc        [mTEPES.psn  ]
    par['pMinStorage']          = par['pMinStorage'].loc          [mTEPES.psn  ]
    par['pMaxStorage']          = par['pMaxStorage'].loc          [mTEPES.psn  ]
    par['pVariableMaxEnergy']   = par['pVariableMaxEnergy'].loc   [mTEPES.psn  ]
    par['pVariableMinEnergy']   = par['pVariableMinEnergy'].loc   [mTEPES.psn  ]
    par['pLinearVarCost']       = par['pLinearVarCost'].loc       [mTEPES.psn  ]
    par['pConstantVarCost']     = par['pConstantVarCost'].loc     [mTEPES.psn  ]
    par['pEmissionVarCost']     = par['pEmissionVarCost'].loc     [mTEPES.psn  ]

    par['pRatedLinearOperCost'] = par['pRatedLinearFuelCost'].loc [mTEPES.g    ]
    par['pRatedLinearVarCost']  = par['pRatedLinearFuelCost'].loc [mTEPES.g    ]

    # drop generators not es
    par['pEfficiency']          = par['pEfficiency'].loc          [mTEPES.eh   ]
    par['pStorageTimeStep']     = par['pStorageTimeStep'].loc     [mTEPES.es   ]
    par['pOutflowsTimeStep']    = par['pOutflowsTimeStep'].loc    [mTEPES.es   ]
    par['pStorageType']         = par['pStorageType'].loc         [mTEPES.es   ]

    if par['pIndRampReserves']:
        par['pRampReserveUp']   = par['pRampReserveUp'].loc       [mTEPES.psnar]
        par['pRampReserveDw']   = par['pRampReserveDw'].loc       [mTEPES.psnar]

    if par['pIndReserveActivation']:
        par['pOperReserveUpEnergy'] = par['pOperReserveUpEnergy'].loc[mTEPES.psnar]
        par['pOperReserveDwEnergy'] = par['pOperReserveDwEnergy'].loc[mTEPES.psnar]

    if par['pIndHydroTopology']:
        par['pHydroInflows' ]   = par['pHydroInflows' ].loc       [mTEPES.psn  ]
        par['pHydroOutflows']   = par['pHydroOutflows'].loc       [mTEPES.psn  ]
        par['pIniVolume']       = par['pIniVolume'].loc           [mTEPES.psn  ]
        par['pMinVolume']       = par['pMinVolume'].loc           [mTEPES.psn  ]
        par['pMaxVolume']       = par['pMaxVolume'].loc           [mTEPES.psn  ]
    if par['pIndHydrogen']:
        par['pDemandH2']        = par['pDemandH2'].loc            [mTEPES.psn  ]
        par['pDemandH2Abs']     = par['pDemandH2'].where  (par['pDemandH2']   > 0.0, 0.0)
    if par['pIndHeat']:
        par['pDemandHeat']      = par['pDemandHeat'].loc          [mTEPES.psn  ]
        par['pDemandHeatAbs']   = par['pDemandHeat'].where(par['pDemandHeat'] > 0.0, 0.0)

    if par['pIndVarTTC']:
        par['pVariableNTCFrw']  = par['pVariableNTCFrw'].loc      [mTEPES.psn]
        par['pVariableNTCBck']  = par['pVariableNTCBck'].loc      [mTEPES.psn]
    if par['pIndPTDF']:
        par['pVariablePTDF']    = par['pVariablePTDF'].loc        [mTEPES.psn]

    # separate positive and negative demands to avoid converting negative values to 0
    par['pDemandElecPos']       = par['pDemandElec'].where(par['pDemandElec'] >= 0.0, 0.0)
    par['pDemandElecNeg']       = par['pDemandElec'].where(par['pDemandElec'] <  0.0, 0.0)
    # par['pDemandElecAbs']       = par['pDemandElec'].where(par['pDemandElec'] >  0.0, 0.0)

    # generators to area (g2a) (e2a) (n2a)
    g2a = defaultdict(list)
    for ar,g  in mTEPES.a2g:
        g2a[ar].append(g )
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    r2a = defaultdict(list)
    for ar,rs in mTEPES.ar*mTEPES.rs:
        for h in mTEPES.h:
            if (ar,h) in mTEPES.a2g and sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r or (rs,h) in mTEPES.r2p or (h,rs) in mTEPES.p2r) and rs not in r2a[ar]:
                r2a[ar].append(rs)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)

    # nodes to area (d2a)
    d2a = defaultdict(list)
    for nd,ar in mTEPES.ndar:
        d2a[ar].append(nd)

    # small values are converted to 0
    par['pDemandElecPeak']          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    par['pDemandHeatPeak']          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    for p,ar in mTEPES.par:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        par['pDemandElecPeak'][p,ar] = par['pDemandElec'].loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
        par['pEpsilonElec']          = par['pDemandElecPeak'][p,ar]*1e-5

        # these parameters are in GW
        par['pDemandElecPos']     [par['pDemandElecPos'] [[nd for nd in d2a[ar]]] <  par['pEpsilonElec']] = 0.0
        par['pDemandElecNeg']     [par['pDemandElecNeg'] [[nd for nd in d2a[ar]]] > -par['pEpsilonElec']] = 0.0
        par['pSystemInertia']     [par['pSystemInertia'] [[                 ar ]] <  par['pEpsilonElec']] = 0.0
        par['pOperReserveUp']     [par['pOperReserveUp'] [[                 ar ]] <  par['pEpsilonElec']] = 0.0
        par['pOperReserveDw']     [par['pOperReserveDw'] [[                 ar ]] <  par['pEpsilonElec']] = 0.0

        if par['pIndReserveActivation']:
            par['pOperReserveUpEnergy'][par['pOperReserveUpEnergy'] [[      ar ]] <  par['pEpsilonElec']] = 0.0
            par['pOperReserveDwEnergy'][par['pOperReserveDwEnergy'] [[      ar ]] <  par['pEpsilonElec']] = 0.0
            # operating reserve activation can't be greater than operating reserve requirement
            par['pOperReserveUpEnergy'][par['pOperReserveUpEnergy'] [[      ar ]] >  par['pOperReserveUp'][[ar]]] = par['pOperReserveUp'][[ar]]
            par['pOperReserveDwEnergy'][par['pOperReserveDwEnergy'] [[      ar ]] >  par['pOperReserveDw'][[ar]]] = par['pOperReserveDw'][[ar]]


        if g2a[ar]:
            par['pMinPowerElec']  [par['pMinPowerElec']  [[g  for  g in g2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pMaxPowerElec']  [par['pMaxPowerElec']  [[g  for  g in g2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pMinCharge']     [par['pMinCharge']     [[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pMaxCharge']     [par['pMaxCharge']     [[eh for eh in g2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pEnergyInflows'] [par['pEnergyInflows'] [[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pEnergyOutflows'][par['pEnergyOutflows'][[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0
            # these parameters are in GWh
            par['pMinStorage']    [par['pMinStorage']    [[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pMaxStorage']    [par['pMaxStorage']    [[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0
            par['pIniInventory']  [par['pIniInventory']  [[es for es in e2a[ar]]] <  par['pEpsilonElec']] = 0.0

            # the pEpsilonElec units are in GW while the volume is in hm3 and teh hydro inflows in m3/s
            if par['pIndHydroTopology']:
                par['pMinVolume']    [par['pMinVolume']    [[rs for rs in r2a[ar]]] < par['pEpsilonElec']] = 0.0
                par['pMaxVolume']    [par['pMaxVolume']    [[rs for rs in r2a[ar]]] < par['pEpsilonElec']] = 0.0
                par['pHydroInflows'] [par['pHydroInflows'] [[rs for rs in r2a[ar]]] < par['pEpsilonElec']] = 0.0
                par['pHydroOutflows'][par['pHydroOutflows'][[rs for rs in r2a[ar]]] < par['pEpsilonElec']] = 0.0

        # pInitialInventory.update(pd.Series([0.0 for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], index=[es for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], dtype='float64'))

        # merging positive and negative values of the demand
        par['pDemandElec']        = par['pDemandElecPos'].where(par['pDemandElecNeg'] == 0.0, par['pDemandElecNeg'])

        # Increase Maximum to reach minimum
        # par['pMaxPowerElec']      = par['pMaxPowerElec'].where(par['pMaxPowerElec'] >= par['pMinPowerElec'], par['pMinPowerElec'])
        # par['pMaxCharge']         = par['pMaxCharge'].where   (par['pMaxCharge']    >= par['pMinCharge'],    par['pMinCharge']   )

        # Decrease minimum to reach maximum
        par['pMinPowerElec']      = par['pMinPowerElec'].where(par['pMinPowerElec'] <= par['pMaxPowerElec'], par['pMaxPowerElec'])
        par['pMinCharge']         = par['pMinCharge'].where   (par['pMinCharge']    <= par['pMaxCharge'],    par['pMaxCharge']   )

        # calculate 2nd Blocks
        par['pMaxPower2ndBlock']  = par['pMaxPowerElec'] - par['pMinPowerElec']
        par['pMaxCharge2ndBlock'] = par['pMaxCharge']    - par['pMinCharge']

        par['pMaxCapacity']       = par['pMaxPowerElec'].where(par['pMaxPowerElec'] > par['pMaxCharge'], par['pMaxCharge'])

        if g2a[ar]:
            par['pMaxPower2ndBlock'] [par['pMaxPower2ndBlock'] [[g for g in g2a[ar]]] < par['pEpsilonElec']] = 0.0
            par['pMaxCharge2ndBlock'][par['pMaxCharge2ndBlock'][[g for g in g2a[ar]]] < par['pEpsilonElec']] = 0.0

        par['pLineNTCFrw'][par['pLineNTCFrw'] < par['pEpsilonElec']] = 0
        par['pLineNTCBck'][par['pLineNTCBck'] < par['pEpsilonElec']] = 0
        par['pLineNTCMax'] = par['pLineNTCFrw'].where(par['pLineNTCFrw'] > par['pLineNTCBck'], par['pLineNTCBck'])

        if par['pIndHydrogen']:
            par['pDemandH2'][par['pDemandH2'][[nd for nd in d2a[ar]]] < par['pEpsilonElec']] = 0.0
            par['pH2PipeNTCFrw'][par['pH2PipeNTCFrw'] < par['pEpsilonElec']] = 0
            par['pH2PipeNTCBck'][par['pH2PipeNTCBck'] < par['pEpsilonElec']] = 0

        if par['pIndHeat']:
            par['pDemandHeatPeak'][p,ar] = par['pDemandHeat'].loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
            par['pEpsilonHeat']          = par['pDemandHeatPeak'][p,ar]*1e-5
            par['pDemandHeat']             [par['pDemandHeat']    [[nd for nd in   d2a[ar]]] <  par['pEpsilonHeat']] = 0.0
            par['pHeatPipeNTCFrw'][par['pHeatPipeNTCFrw'] < par['pEpsilonElec']] = 0
            par['pHeatPipeNTCBck'][par['pHeatPipeNTCBck'] < par['pEpsilonElec']] = 0

    # drop generators not g or es or eh or ch
    par['pMinPowerElec']      = par['pMinPowerElec'].loc     [:,mTEPES.g ]
    par['pMaxPowerElec']      = par['pMaxPowerElec'].loc     [:,mTEPES.g ]
    par['pMinCharge']         = par['pMinCharge'].loc        [:,mTEPES.eh]
    par['pMaxCharge']         = par['pMaxCharge'].loc        [:,mTEPES.eh]
    par['pMaxPower2ndBlock']  = par['pMaxPower2ndBlock'].loc [:,mTEPES.g ]
    par['pMaxCharge2ndBlock'] = par['pMaxCharge2ndBlock'].loc[:,mTEPES.eh]
    par['pMaxCapacity']       = par['pMaxCapacity'].loc      [:,mTEPES.eh]
    par['pEnergyInflows']     = par['pEnergyInflows'].loc    [:,mTEPES.es]
    par['pEnergyOutflows']    = par['pEnergyOutflows'].loc   [:,mTEPES.es]
    par['pIniInventory']      = par['pIniInventory'].loc     [:,mTEPES.es]
    par['pMinStorage']        = par['pMinStorage'].loc       [:,mTEPES.es]
    par['pMaxStorage']        = par['pMaxStorage'].loc       [:,mTEPES.es]
    par['pVariableMaxEnergy'] = par['pVariableMaxEnergy'].loc[:,mTEPES.g ]
    par['pVariableMinEnergy'] = par['pVariableMinEnergy'].loc[:,mTEPES.g ]
    par['pLinearVarCost']     = par['pLinearVarCost'].loc    [:,mTEPES.g ]
    par['pConstantVarCost']   = par['pConstantVarCost'].loc  [:,mTEPES.g ]
    par['pEmissionVarCost']   = par['pEmissionVarCost'].loc  [:,mTEPES.g ]

    # replace < 0.0 by 0.0
    par['pEpsilon'] = 1e-6
    par['pMaxPower2ndBlock']  = par['pMaxPower2ndBlock'].where (par['pMaxPower2ndBlock']  > par['pEpsilon'], 0.0)
    par['pMaxCharge2ndBlock'] = par['pMaxCharge2ndBlock'].where(par['pMaxCharge2ndBlock'] > par['pEpsilon'], 0.0)

    # computation of the power-to-heat ratio of the CHP units
    # heat ratio of boiler units is fixed to 1.0
    par['pPower2HeatRatio']   = pd.Series([1.0 if ch in mTEPES.bo else (par['pRatedMaxPowerElec'][ch]-par['pRatedMinPowerElec'][ch])/(par['pRatedMaxPowerHeat'][ch]-par['pRatedMinPowerHeat'][ch]) for ch in mTEPES.ch], index=mTEPES.ch)
    par['pMinPowerHeat']      = pd.DataFrame([[par['pMinPowerElec']     [ch][p,sc,n]/par['pPower2HeatRatio'][ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    par['pMaxPowerHeat']      = pd.DataFrame([[par['pMaxPowerElec']     [ch][p,sc,n]/par['pPower2HeatRatio'][ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    par['pMinPowerHeat'].update(pd.DataFrame([[par['pRatedMinPowerHeat'][bo]                                             for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))
    par['pMaxPowerHeat'].update(pd.DataFrame([[par['pRatedMaxPowerHeat'][bo]                                             for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))
    par['pMaxPowerHeat'].update(pd.DataFrame([[par['pMaxCharge'][hp][p,sc,n]/par['pProductionFunctionHeat'][hp]  for hp in mTEPES.hp] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.hp))

    # drop values not par, p, or ps
    par['pReserveMargin']  = par['pReserveMargin'].loc [mTEPES.par]
    par['pEmission']       = par['pEmission'].loc      [mTEPES.par]
    par['pRESEnergy']      = par['pRESEnergy'].loc     [mTEPES.par]
    par['pDemandElecPeak'] = par['pDemandElecPeak'].loc[mTEPES.par]
    par['pDemandHeatPeak'] = par['pDemandHeatPeak'].loc[mTEPES.par]
    par['pPeriodWeight']   = par['pPeriodWeight'].loc  [mTEPES.p  ]
    par['pScenProb']       = par['pScenProb'].loc      [mTEPES.ps ]

    # drop generators not gc or gd
    par['pGenInvestCost']           = par['pGenInvestCost'].loc   [mTEPES.eb]
    par['pGenRetireCost']           = par['pGenRetireCost'].loc   [mTEPES.gd]
    par['pIndBinUnitInvest']        = par['pIndBinUnitInvest'].loc[mTEPES.eb]
    par['pIndBinUnitRetire']        = par['pIndBinUnitRetire'].loc[mTEPES.gd]
    par['pGenLoInvest']             = par['pGenLoInvest'].loc     [mTEPES.eb]
    par['pGenLoRetire']             = par['pGenLoRetire'].loc     [mTEPES.gd]
    par['pGenUpInvest']             = par['pGenUpInvest'].loc     [mTEPES.eb]
    par['pGenUpRetire']             = par['pGenUpRetire'].loc     [mTEPES.gd]

    # drop generators not nr or ec
    par['pStartUpCost']             = par['pStartUpCost'].loc     [mTEPES.nr]
    par['pShutDownCost']            = par['pShutDownCost'].loc    [mTEPES.nr]
    par['pIndBinUnitCommit']        = par['pIndBinUnitCommit'].loc[mTEPES.nr]
    par['pIndBinStorInvest']        = par['pIndBinStorInvest'].loc[mTEPES.ec]

    # drop lines not la
    par['pLineR']                   = par['pLineR'].loc           [mTEPES.la]
    par['pLineX']                   = par['pLineX'].loc           [mTEPES.la]
    par['pLineBsh']                 = par['pLineBsh'].loc         [mTEPES.la]
    par['pLineTAP']                 = par['pLineTAP'].loc         [mTEPES.la]
    par['pLineLength']              = par['pLineLength'].loc      [mTEPES.la]
    par['pElecNetPeriodIni']        = par['pElecNetPeriodIni'].loc[mTEPES.la]
    par['pElecNetPeriodFin']        = par['pElecNetPeriodFin'].loc[mTEPES.la]
    par['pLineVoltage']             = par['pLineVoltage'].loc     [mTEPES.la]
    par['pLineNTCFrw']              = par['pLineNTCFrw'].loc      [mTEPES.la]
    par['pLineNTCBck']              = par['pLineNTCBck'].loc      [mTEPES.la]
    par['pLineNTCMax']              = par['pLineNTCMax'].loc      [mTEPES.la]
    # par['pSwOnTime']              = par['pSwOnTime'].loc        [mTEPES.la]
    # par['pSwOffTime']             = par['pSwOffTime'].loc       [mTEPES.la]
    par['pIndBinLineInvest']        = par['pIndBinLineInvest'].loc[mTEPES.la]
    par['pIndBinLineSwitch']        = par['pIndBinLineSwitch'].loc[mTEPES.la]
    par['pAngMin']                  = par['pAngMin'].loc          [mTEPES.la]
    par['pAngMax']                  = par['pAngMax'].loc          [mTEPES.la]

    # drop lines not lc or ll
    par['pNetFixedCost']            = par['pNetFixedCost'].loc    [mTEPES.lc]
    par['pNetLoInvest']             = par['pNetLoInvest'].loc     [mTEPES.lc]
    par['pNetUpInvest']             = par['pNetUpInvest'].loc     [mTEPES.lc]
    par['pLineLossFactor']          = par['pLineLossFactor'].loc  [mTEPES.ll]

    par['pMaxNTCFrw'] = pd.DataFrame([[par['pLineNTCFrw'][la] for la in mTEPES.la] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.la)
    par['pMaxNTCBck'] = pd.DataFrame([[par['pLineNTCBck'][la] for la in mTEPES.la] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.la)
    if par['pIndVarTTC']:
        par['pMaxNTCFrw'] = par['pVariableNTCFrw'].replace(0.0, par['pLineNTCFrw'])
        par['pMaxNTCBck'] = par['pVariableNTCBck'].replace(0.0, par['pLineNTCBck'])
        par['pMaxNTCFrw']  [par['pMaxNTCFrw'] < par['pEpsilonElec']] = 0.0
        par['pMaxNTCBck']  [par['pMaxNTCBck'] < par['pEpsilonElec']] = 0.0
    par['pMaxNTCMax'] = par['pMaxNTCFrw'].where(par['pMaxNTCFrw'] > par['pMaxNTCBck'], par['pMaxNTCBck'])

    par['pMaxNTCBck']                  = par['pMaxNTCBck'].loc             [:,mTEPES.la]
    par['pMaxNTCFrw']                  = par['pMaxNTCFrw'].loc             [:,mTEPES.la]
    par['pMaxNTCMax']                  = par['pMaxNTCFrw'].loc             [:,mTEPES.la]

    if par['pIndHydroTopology']:
        # drop generators not h
        par['pProductionFunctionHydro'] = par['pProductionFunctionHydro'].loc[mTEPES.h ]
        # drop reservoirs not rn
        par['pIndBinRsrvInvest']        = par['pIndBinRsrvInvest'].loc       [mTEPES.rn]
        par['pRsrInvestCost']           = par['pRsrInvestCost'].loc          [mTEPES.rn]
        # maximum outflows depending on the downstream hydropower unit
        par['pMaxOutflows'] = pd.DataFrame([[sum(par['pMaxPowerElec'][h][p,sc,n]/par['pProductionFunctionHydro'][h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) for rs in mTEPES.rs] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.rs)

    if par['pIndHydrogen']:
        # drop generators not el
        par['pProductionFunctionH2'] = par['pProductionFunctionH2'].loc[mTEPES.el]
        # drop pipelines not pc
        par['pH2PipeFixedCost']      = par['pH2PipeFixedCost'].loc     [mTEPES.pc]
        par['pH2PipeLoInvest']       = par['pH2PipeLoInvest'].loc      [mTEPES.pc]
        par['pH2PipeUpInvest']       = par['pH2PipeUpInvest'].loc      [mTEPES.pc]

    if par['pIndHeat']:
        par['pReserveMarginHeat']          = par['pReserveMarginHeat'].loc         [mTEPES.par]
        # drop generators not hp
        par['pProductionFunctionHeat']     = par['pProductionFunctionHeat'].loc    [mTEPES.hp]
        # drop generators not hh
        par['pProductionFunctionH2ToHeat'] = par['pProductionFunctionH2ToHeat'].loc[mTEPES.hh]
        # drop heat pipes not hc
        par['pHeatPipeFixedCost']          = par['pHeatPipeFixedCost'].loc         [mTEPES.hc]
        par['pHeatPipeLoInvest']           = par['pHeatPipeLoInvest'].loc          [mTEPES.hc]
        par['pHeatPipeUpInvest']           = par['pHeatPipeUpInvest'].loc          [mTEPES.hc]

    # replace very small costs by 0
    par['pEpsilon'] = 1e-5           # this value in EUR/GWh is lower than the O&M variable cost of any technology, independent of the area

    par['pLinearVarCost']  [par['pLinearVarCost']  [[g for g in mTEPES.g]] < par['pEpsilon']] = 0.0
    par['pConstantVarCost'][par['pConstantVarCost'][[g for g in mTEPES.g]] < par['pEpsilon']] = 0.0
    par['pEmissionVarCost'][par['pEmissionVarCost'][[g for g in mTEPES.g]] < par['pEpsilon']] = 0.0

    par['pRatedLinearVarCost'].update  (pd.Series([0.0 for g  in mTEPES.g  if     par['pRatedLinearVarCost']  [g ]  < par['pEpsilon']], index=[g  for g  in mTEPES.g  if     par['pRatedLinearVarCost']  [g ]  < par['pEpsilon']]))
    par['pLinearOMCost'].update        (pd.Series([0.0 for g  in mTEPES.g  if     par['pLinearOMCost']        [g ]  < par['pEpsilon']], index=[g  for g  in mTEPES.g  if     par['pLinearOMCost']        [g ]  < par['pEpsilon']]))
    par['pOperReserveCost'].update     (pd.Series([0.0 for g  in mTEPES.g  if     par['pOperReserveCost']     [g ]  < par['pEpsilon']], index=[g  for g  in mTEPES.g  if     par['pOperReserveCost']     [g ]  < par['pEpsilon']]))
    # par['pEmissionCost'].update      (pd.Series([0.0 for g  in mTEPES.g  if abs(par['pEmissionCost']        [g ]) < par['pEpsilon']], index=[g  for g  in mTEPES.g  if abs(par['pEmissionCost']        [g ]) < par['pEpsilon']]))
    par['pStartUpCost'].update         (pd.Series([0.0 for nr in mTEPES.nr if     par['pStartUpCost']         [nr]  < par['pEpsilon']], index=[nr for nr in mTEPES.nr if     par['pStartUpCost']         [nr]  < par['pEpsilon']]))
    par['pShutDownCost'].update        (pd.Series([0.0 for nr in mTEPES.nr if     par['pShutDownCost']        [nr]  < par['pEpsilon']], index=[nr for nr in mTEPES.nr if     par['pShutDownCost']        [nr]  < par['pEpsilon']]))

    # this rated linear variable cost is going to be used to order the generating units
    # we include a small term to avoid a stochastic behavior due to equal values
    for g in mTEPES.g:
        par['pRatedLinearVarCost'][g] += 1e-3*par['pEpsilon']*mTEPES.g.ord(g)

    # BigM maximum flow to be used in the Kirchhoff's 2nd law disjunctive constraint.
    # For AC candidate lines (lca) the disjunctive form (eKirchhoff2ndLaw1/2) reads,
    # after multiplying through by M:
    #     vFlowElec - (theta_i - theta_j) * pSBase / pLineX  <=  M * (1 - vLineCommit)
    # When vLineCommit = 0 the line is not built, vFlowElec is forced to 0 by
    # eNetCapacity1/2, but the angle term remains and is bounded only by the
    # natural Delta-theta range [-pi, pi] (theta is bounded by pMaxTheta = pi/2 at
    # each bus). The angle bound is pi * pSBase / pLineX. The flow-side bound is
    # pLineNTCBck. Take the max of the two so the Big-M is valid for both sides of
    # the disjunction, and multiply by (1 + epsilon) for numerical slack. Existing
    # AC lines (lea) appear in eKirchhoff2ndLaw1 only as an equality and use
    # pLineNTC purely as a numerical normaliser. DC lines (led, lcd) are not
    # subject to the disjunctive form at all -- their entries are left at 0.0 here
    # and converted to 1.0 by the division-by-zero guard below; the values are
    # never read by the formulation.
    pMBigMEpsilon = 1e-3
    par['pBigMFlowBck'] = par['pLineNTCBck']*0.0
    par['pBigMFlowFrw'] = par['pLineNTCFrw']*0.0
    for lea in mTEPES.lea:
        par['pBigMFlowBck'].loc[lea] = par['pLineNTCBck'][lea]
        par['pBigMFlowFrw'].loc[lea] = par['pLineNTCFrw'][lea]
    for lca in mTEPES.lca:
        M_angle_lca = (1.0 + pMBigMEpsilon) * max(par['pLineNTCBck'][lca], math.pi * par['pSBase'] / par['pLineX'][lca])
        par['pBigMFlowBck'].loc[lca] = M_angle_lca
        par['pBigMFlowFrw'].loc[lca] = M_angle_lca

    # if BigM are 0.0 then converted to 1.0 to avoid division by 0.0
    par['pBigMFlowBck'] = par['pBigMFlowBck'].where(par['pBigMFlowBck'] != 0.0, 1.0)
    par['pBigMFlowFrw'] = par['pBigMFlowFrw'].where(par['pBigMFlowFrw'] != 0.0, 1.0)

    # maximum voltage angle
    par['pMaxTheta'] = par['pDemandElec']*0.0 + math.pi/2
    par['pMaxTheta'] = par['pMaxTheta'].loc[mTEPES.psn]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    # @profile
    def filter_rows(df, set):
        df = df.stack(level=list(range(df.columns.nlevels)), future_stack=True)
        df = df[df.index.isin(set)]
        return df

    par['pMinPowerElec']      = filter_rows(par['pMinPowerElec']     , mTEPES.psng )
    par['pMaxPowerElec']      = filter_rows(par['pMaxPowerElec']     , mTEPES.psng )
    par['pMinCharge']         = filter_rows(par['pMinCharge']        , mTEPES.psneh)
    par['pMaxCharge']         = filter_rows(par['pMaxCharge']        , mTEPES.psneh)
    par['pMaxCapacity']       = filter_rows(par['pMaxCapacity']      , mTEPES.psneh)
    par['pMaxPower2ndBlock']  = filter_rows(par['pMaxPower2ndBlock'] , mTEPES.psng )
    par['pMaxCharge2ndBlock'] = filter_rows(par['pMaxCharge2ndBlock'], mTEPES.psneh)
    par['pEnergyInflows']     = filter_rows(par['pEnergyInflows']    , mTEPES.psnes)
    par['pEnergyOutflows']    = filter_rows(par['pEnergyOutflows']   , mTEPES.psnes)
    par['pMinStorage']        = filter_rows(par['pMinStorage']       , mTEPES.psnes)
    par['pMaxStorage']        = filter_rows(par['pMaxStorage']       , mTEPES.psnes)
    par['pVariableMaxEnergy'] = filter_rows(par['pVariableMaxEnergy'], mTEPES.psng )
    par['pVariableMinEnergy'] = filter_rows(par['pVariableMinEnergy'], mTEPES.psng )
    par['pLinearVarCost']     = filter_rows(par['pLinearVarCost']    , mTEPES.psng )
    par['pConstantVarCost']   = filter_rows(par['pConstantVarCost']  , mTEPES.psng )
    par['pEmissionVarCost']   = filter_rows(par['pEmissionVarCost']  , mTEPES.psng )
    par['pIniInventory']      = filter_rows(par['pIniInventory']     , mTEPES.psnes)

    par['pDemandElec']        = filter_rows(par['pDemandElec']       , mTEPES.psnnd)
    par['pDemandElecPos']     = filter_rows(par['pDemandElecPos']    , mTEPES.psnnd)
    par['pSystemInertia']     = filter_rows(par['pSystemInertia']    , mTEPES.psnar)
    par['pOperReserveUp']     = filter_rows(par['pOperReserveUp']    , mTEPES.psnar)
    par['pOperReserveDw']     = filter_rows(par['pOperReserveDw']    , mTEPES.psnar)

    if par['pIndRampReserves']:
        par['pRampReserveUp'] = filter_rows(par['pRampReserveUp']    , mTEPES.psnar)
        par['pRampReserveDw'] = filter_rows(par['pRampReserveDw']    , mTEPES.psnar)

    if par['pIndReserveActivation']:
        par['pOperReserveUpEnergy'] = filter_rows(par['pOperReserveUpEnergy'], mTEPES.psnar)
        par['pOperReserveDwEnergy'] = filter_rows(par['pOperReserveDwEnergy'], mTEPES.psnar)

    par['pMaxNTCBck']         = filter_rows(par['pMaxNTCBck']        , mTEPES.psnla)
    par['pMaxNTCFrw']         = filter_rows(par['pMaxNTCFrw']        , mTEPES.psnla)
    par['pMaxNTCMax']         = filter_rows(par['pMaxNTCMax']        , mTEPES.psnla)

    if par['pIndPTDF']:
        par['pPTDF'] = par['pVariablePTDF'].stack(level=list(range(par['pVariablePTDF'].columns.nlevels)), future_stack=True)
        par['pPTDF'].index.set_names(['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'Node'], inplace=True)
        # filter rows to keep the same as mTEPES.psnland
        par['pPTDF'] = par['pPTDF'][par['pPTDF'].index.isin(mTEPES.psnland)]

    # %% parameters
    mTEPES.pIndBinGenInvest      = Param(initialize=par['pIndBinGenInvest']     , within=NonNegativeIntegers, doc='Indicator of binary generation       investment decisions', mutable=True)
    mTEPES.pIndBinGenRetire      = Param(initialize=par['pIndBinGenRetirement'] , within=NonNegativeIntegers, doc='Indicator of binary generation       retirement decisions', mutable=True)
    mTEPES.pIndBinRsrInvest      = Param(initialize=par['pIndBinRsrInvest']     , within=NonNegativeIntegers, doc='Indicator of binary reservoir        investment decisions', mutable=True)
    mTEPES.pIndBinNetElecInvest  = Param(initialize=par['pIndBinNetInvest']     , within=NonNegativeIntegers, doc='Indicator of binary electric network investment decisions', mutable=True)
    mTEPES.pIndBinNetH2Invest    = Param(initialize=par['pIndBinNetH2Invest']   , within=NonNegativeIntegers, doc='Indicator of binary hydrogen network investment decisions', mutable=True)
    mTEPES.pIndBinNetHeatInvest  = Param(initialize=par['pIndBinNetHeatInvest'] , within=NonNegativeIntegers, doc='Indicator of binary heat     network investment decisions', mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=par['pIndBinGenOperat']     , within=Binary,              doc='Indicator of binary generation operation  decisions',       mutable=True)
    mTEPES.pIndBinSingleNode     = Param(initialize=par['pIndBinSingleNode']    , within=Binary,              doc='Indicator of single node within a electric network case',   mutable=True)
    mTEPES.pIndBinGenRamps       = Param(initialize=par['pIndBinGenRamps']      , within=Binary,              doc='Indicator of using or not the ramp constraints',            mutable=True)
    mTEPES.pIndBinGenMinTime     = Param(initialize=par['pIndBinGenMinTime']    , within=Binary,              doc='Indicator of using or not the min up/dw time constraints',  mutable=True)
    mTEPES.pIndBinLineCommit     = Param(initialize=par['pIndBinLineCommit']    , within=Binary,              doc='Indicator of binary electric network switching  decisions', mutable=True)
    mTEPES.pIndBinNetLosses      = Param(initialize=par['pIndBinNetLosses']     , within=Binary,              doc='Indicator of binary electric network ohmic losses',         mutable=True)
    mTEPES.pIndRampReserves      = Param(initialize=par['pIndRampReserves']     , within=Binary,              doc='Indicator of ramp reserves'                                             )
    mTEPES.pIndReserveActivation = Param(initialize=par['pIndReserveActivation'], within=Binary,              doc='Indicator of operating reserve activation'                              )
    mTEPES.pIndHydroTopology     = Param(initialize=par['pIndHydroTopology']    , within=Binary,              doc='Indicator of reservoir and hydropower topology'                         )
    mTEPES.pIndHydrogen          = Param(initialize=par['pIndHydrogen']         , within=Binary,              doc='Indicator of hydrogen demand and pipeline network'                      )
    mTEPES.pIndHeat              = Param(initialize=par['pIndHeat']             , within=Binary,              doc='Indicator of heat     demand and pipe     network'                      )
    mTEPES.pIndVarTTC            = Param(initialize=par['pIndVarTTC']           , within=Binary,              doc='Indicator of using or not variable TTC'                                 )
    mTEPES.pIndPTDF              = Param(initialize=par['pIndPTDF']             , within=Binary,              doc='Indicator of using or not the Flow-based method'                        )

    mTEPES.pENSCost              = Param(initialize=par['pENSCost']             , within=NonNegativeReals,    doc='ENS cost'                                           , mutable=True)
    mTEPES.pH2NSCost             = Param(initialize=par['pHNSCost']             , within=NonNegativeReals,    doc='HNS cost'                                           )
    mTEPES.pH2ExcCost            = Param(initialize=par['pHNSCost']*0.5         , within=NonNegativeReals,    doc='H2 excess cost'                                     )
    mTEPES.pHeatNSCost           = Param(initialize=par['pHTNSCost']            , within=NonNegativeReals,    doc='HTNS cost'                                          )
    mTEPES.pCO2Cost              = Param(initialize=par['pCO2Cost']             , within=NonNegativeReals,    doc='CO2 emission cost'                                  )
    mTEPES.pAnnualDiscRate       = Param(initialize=par['pAnnualDiscountRate']  , within=UnitInterval,        doc='Annual discount rate'                               )
    mTEPES.pUpReserveActivation  = Param(initialize=par['pUpReserveActivation'] , within=UnitInterval,        doc='Proportion of up   reserve activation'              )
    mTEPES.pDwReserveActivation  = Param(initialize=par['pDwReserveActivation'] , within=UnitInterval,        doc='Proportion of down reserve activation'              )
    mTEPES.pMinRatioDwUp         = Param(initialize=par['pMinRatioDwUp']        , within=UnitInterval,        doc='Minimum ratio down to up operating reserves'        )
    mTEPES.pMaxRatioDwUp         = Param(initialize=par['pMaxRatioDwUp']        , within=UnitInterval,        doc='Maximum ratio down to up operating reserves'        )
    mTEPES.pSBase                = Param(initialize=par['pSBase']               , within=PositiveReals,       doc='Base power'                                         )
    mTEPES.pTimeStep             = Param(initialize=par['pTimeStep']            , within=PositiveIntegers,    doc='Unitary time step'                                  )
    mTEPES.pEconomicBaseYear     = Param(initialize=par['pEconomicBaseYear']    , within=PositiveIntegers,    doc='Base year'                                          )

    mTEPES.pReserveMargin        = Param(mTEPES.par,   initialize=par['pReserveMargin'].to_dict()            , within=NonNegativeReals,    doc='Adequacy reserve margin'                             , mutable=True)
    mTEPES.pEmission             = Param(mTEPES.par,   initialize=par['pEmission'].to_dict()                 , within=NonNegativeReals,    doc='Maximum CO2 emission'                                )
    mTEPES.pRESEnergy            = Param(mTEPES.par,   initialize=par['pRESEnergy'].to_dict()                , within=NonNegativeReals,    doc='Minimum RES energy'                                  , mutable=True)
    mTEPES.pDemandElecPeak       = Param(mTEPES.par,   initialize=par['pDemandElecPeak'].to_dict()           , within=NonNegativeReals,    doc='Peak electric demand'                                )
    mTEPES.pDemandElec           = Param(mTEPES.psnnd, initialize=par['pDemandElec'].to_dict()               , within=           Reals,    doc='Electric demand'                                     , mutable=True)
    mTEPES.pDemandElecPos        = Param(mTEPES.psnnd, initialize=par['pDemandElecPos'].to_dict()            , within=NonNegativeReals,    doc='Electric demand positive'                            )
    mTEPES.pPeriodWeight         = Param(mTEPES.p,     initialize=par['pPeriodWeight'].to_dict()             , within=NonNegativeReals,    doc='Period weight',                          mutable=True)
    mTEPES.pDiscountedWeight     = Param(mTEPES.p,     initialize=par['pDiscountedWeight'].to_dict()         , within=NonNegativeReals,    doc='Discount factor'                                     )
    mTEPES.pScenProb             = Param(mTEPES.ps,    initialize=par['pScenProb'].to_dict()                 , within=UnitInterval    ,    doc='Probability',                            mutable=True)
    mTEPES.pStageWeight          = Param(mTEPES.stt,   initialize=par['pStageWeight'].to_dict()              , within=NonNegativeReals,    doc='Stage weight'                                        )
    mTEPES.pDuration             = Param(mTEPES.psn,   initialize=par['pDuration'].to_dict()                 , within=NonNegativeIntegers, doc='Duration',                               mutable=True)
    mTEPES.pNodeLon              = Param(mTEPES.nd,    initialize=par['pNodeLon'].to_dict()                  ,                             doc='Longitude'                                           )
    mTEPES.pNodeLat              = Param(mTEPES.nd,    initialize=par['pNodeLat'].to_dict()                  ,                             doc='Latitude'                                            )
    mTEPES.pSystemInertia        = Param(mTEPES.psnar, initialize=par['pSystemInertia'].to_dict()            , within=NonNegativeReals,    doc='System inertia'                                      )
    mTEPES.pOperReserveUp        = Param(mTEPES.psnar, initialize=par['pOperReserveUp'].to_dict()            , within=NonNegativeReals,    doc='up   operating reserve'                              )
    mTEPES.pOperReserveDw        = Param(mTEPES.psnar, initialize=par['pOperReserveDw'].to_dict()            , within=NonNegativeReals,    doc='down operating reserve'                              )
    mTEPES.pMinPowerElec         = Param(mTEPES.psng , initialize=par['pMinPowerElec'].to_dict()             , within=NonNegativeReals,    doc='Minimum electric power'                              )
    mTEPES.pMaxPowerElec         = Param(mTEPES.psng , initialize=par['pMaxPowerElec'].to_dict()             , within=NonNegativeReals,    doc='Maximum electric power'                              )
    mTEPES.pMinCharge            = Param(mTEPES.psneh, initialize=par['pMinCharge'].to_dict()                , within=NonNegativeReals,    doc='Minimum charge'                                      )
    mTEPES.pMaxCharge            = Param(mTEPES.psneh, initialize=par['pMaxCharge'].to_dict()                , within=NonNegativeReals,    doc='Maximum charge'                                      )
    mTEPES.pMaxCapacity          = Param(mTEPES.psneh, initialize=par['pMaxCapacity'].to_dict()              , within=NonNegativeReals,    doc='Maximum capacity'                                    )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.psng , initialize=par['pMaxPower2ndBlock'].to_dict()         , within=NonNegativeReals,    doc='Second block power'                                  )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.psneh, initialize=par['pMaxCharge2ndBlock'].to_dict()        , within=NonNegativeReals,    doc='Second block charge'                                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.psnes, initialize=par['pEnergyInflows'].to_dict()            , within=NonNegativeReals,    doc='Energy inflows',                         mutable=True)
    mTEPES.pEnergyOutflows       = Param(mTEPES.psnes, initialize=par['pEnergyOutflows'].to_dict()           , within=NonNegativeReals,    doc='Energy outflows',                        mutable=True)
    mTEPES.pMinStorage           = Param(mTEPES.psnes, initialize=par['pMinStorage'].to_dict()               , within=NonNegativeReals,    doc='ESS Minimum storage capacity'                        )
    mTEPES.pMaxStorage           = Param(mTEPES.psnes, initialize=par['pMaxStorage'].to_dict()               , within=NonNegativeReals,    doc='ESS Maximum storage capacity',           mutable=True)
    mTEPES.pMinEnergy            = Param(mTEPES.psng , initialize=par['pVariableMinEnergy'].to_dict()        , within=NonNegativeReals,    doc='Unit minimum energy demand'                          )
    mTEPES.pMaxEnergy            = Param(mTEPES.psng , initialize=par['pVariableMaxEnergy'].to_dict()        , within=NonNegativeReals,    doc='Unit maximum energy demand'                          )
    mTEPES.pRatedMaxPowerElec    = Param(mTEPES.gg,    initialize=par['pRatedMaxPowerElec'].to_dict()        , within=NonNegativeReals,    doc='Rated maximum power'                                 )
    mTEPES.pRatedMaxCharge       = Param(mTEPES.gg,    initialize=par['pRatedMaxCharge'].to_dict()           , within=NonNegativeReals,    doc='Rated maximum charge'                                )
    mTEPES.pMustRun              = Param(mTEPES.gg,    initialize=par['pMustRun'].to_dict()                  , within=Binary          ,    doc='must-run unit'                                       )
    mTEPES.pInertia              = Param(mTEPES.gg,    initialize=par['pInertia'].to_dict()                  , within=NonNegativeReals,    doc='unit inertia constant'                               )
    mTEPES.pElecGenPeriodIni     = Param(mTEPES.gg,    initialize=par['pElecGenPeriodIni'].to_dict()         , within=PositiveIntegers,    doc='installation year',                                  )
    mTEPES.pElecGenPeriodFin     = Param(mTEPES.gg,    initialize=par['pElecGenPeriodFin'].to_dict()         , within=PositiveIntegers,    doc='retirement   year',                                  )
    mTEPES.pAvailability         = Param(mTEPES.gg,    initialize=par['pAvailability'].to_dict()             , within=UnitInterval    ,    doc='unit availability',                      mutable=True)
    mTEPES.pEFOR                 = Param(mTEPES.gg,    initialize=par['pEFOR'].to_dict()                     , within=UnitInterval    ,    doc='EFOR'                                                , mutable=True)
    mTEPES.pRatedLinearVarCost   = Param(mTEPES.gg,    initialize=par['pRatedLinearVarCost'].to_dict()       , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pLinearVarCost        = Param(mTEPES.psng , initialize=par['pLinearVarCost'].to_dict()            , within=NonNegativeReals,    doc='Linear   variable cost'                              , mutable=True)
    mTEPES.pConstantVarCost      = Param(mTEPES.psng , initialize=par['pConstantVarCost'].to_dict()          , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearOMCost         = Param(mTEPES.gg,    initialize=par['pLinearOMCost'].to_dict()             , within=NonNegativeReals,    doc='Linear   O&M      cost'                              )
    mTEPES.pOperReserveCost      = Param(mTEPES.gg,    initialize=par['pOperReserveCost'].to_dict()          , within=NonNegativeReals,    doc='Operating reserve cost'                              )
    mTEPES.pEmissionVarCost      = Param(mTEPES.psng , initialize=par['pEmissionVarCost'].to_dict()          , within=Reals           ,    doc='CO2 Emission      cost'                              )
    mTEPES.pEmissionRate         = Param(mTEPES.gg,    initialize=par['pEmissionRate'].to_dict()             , within=Reals           ,    doc='CO2 Emission      rate'                              )
    mTEPES.pStartUpCost          = Param(mTEPES.nr,    initialize=par['pStartUpCost'].to_dict()              , within=NonNegativeReals,    doc='Startup  cost'                                       )
    mTEPES.pShutDownCost         = Param(mTEPES.nr,    initialize=par['pShutDownCost'].to_dict()             , within=NonNegativeReals,    doc='Shutdown cost'                                       )
    mTEPES.pRampUp               = Param(mTEPES.gg,    initialize=par['pRampUp'].to_dict()                   , within=NonNegativeReals,    doc='Ramp up   rate'                                      )
    mTEPES.pRampDw               = Param(mTEPES.gg,    initialize=par['pRampDw'].to_dict()                   , within=NonNegativeReals,    doc='Ramp down rate'                                      )
    mTEPES.pUpTime               = Param(mTEPES.gg,    initialize=par['pUpTime'].to_dict()                   , within=NonNegativeIntegers, doc='Up     time'                                         )
    mTEPES.pDwTime               = Param(mTEPES.gg,    initialize=par['pDwTime'].to_dict()                   , within=NonNegativeIntegers, doc='Down   time'                                         )
    mTEPES.pStableTime           = Param(mTEPES.gg,    initialize=par['pStableTime'].to_dict()               , within=NonNegativeIntegers, doc='Stable time'                                         )
    mTEPES.pShiftTime            = Param(mTEPES.gg,    initialize=par['pShiftTime'].to_dict()                , within=NonNegativeIntegers, doc='Shift  time'                                         )
    mTEPES.pGenInvestCost        = Param(mTEPES.eb,    initialize=par['pGenInvestCost'].to_dict()            , within=NonNegativeReals,    doc='Generation fixed cost'                               )
    mTEPES.pGenRetireCost        = Param(mTEPES.gd,    initialize=par['pGenRetireCost'].to_dict()            , within=Reals           ,    doc='Generation fixed retire cost'                        )
    mTEPES.pIndBinUnitInvest     = Param(mTEPES.eb,    initialize=par['pIndBinUnitInvest'].to_dict()         , within=Binary          ,    doc='Binary investment decision'                          )
    mTEPES.pIndBinUnitRetire     = Param(mTEPES.gd,    initialize=par['pIndBinUnitRetire'].to_dict()         , within=Binary          ,    doc='Binary retirement decision'                          )
    mTEPES.pIndBinUnitCommit     = Param(mTEPES.nr,    initialize=par['pIndBinUnitCommit'].to_dict()         , within=Binary          ,    doc='Binary commitment decision'                          )
    mTEPES.pIndBinStorInvest     = Param(mTEPES.ec,    initialize=par['pIndBinStorInvest'].to_dict()         , within=Binary          ,    doc='Storage linked to generation investment'             )
    mTEPES.pIndOperReserveGen    = Param(mTEPES.gg,    initialize=par['pIndOperReserveGen'].to_dict()        , within=Binary          ,    doc='Indicator of operating reserve when generating power')
    mTEPES.pIndOperReserveCon    = Param(mTEPES.gg,    initialize=par['pIndOperReserveCon'].to_dict()        , within=Binary          ,    doc='Indicator of operating reserve when consuming power' )
    mTEPES.pIndOutflowIncomp     = Param(mTEPES.gg,    initialize=par['pIndOutflowIncomp'].to_dict()         , within=Binary          ,    doc='Indicator of outflow incompatibility with charging'  )
    mTEPES.pEfficiency           = Param(mTEPES.eh,    initialize=par['pEfficiency'].to_dict()               , within=UnitInterval    ,    doc='Round-trip efficiency'                               )
    mTEPES.pStorageTimeStep      = Param(mTEPES.es,    initialize=par['pStorageTimeStep'].to_dict()          , within=PositiveIntegers,    doc='ESS Storage cycle'                                   )
    mTEPES.pOutflowsTimeStep     = Param(mTEPES.es,    initialize=par['pOutflowsTimeStep'].to_dict()         , within=PositiveIntegers,    doc='ESS Outflows cycle'                                  )
    mTEPES.pEnergyTimeStep       = Param(mTEPES.gg,    initialize=par['pEnergyTimeStep'].to_dict()           , within=PositiveIntegers,    doc='Unit energy cycle'                                   )
    mTEPES.pIniInventory         = Param(mTEPES.psnes, initialize=par['pIniInventory'].to_dict()             , within=NonNegativeReals,    doc='ESS Initial storage',                    mutable=True)
    mTEPES.pStorageType          = Param(mTEPES.es,    initialize=par['pStorageType'].to_dict()              , within=Any             ,    doc='ESS Storage type'                                    )
    mTEPES.pGenLoInvest          = Param(mTEPES.eb,    initialize=par['pGenLoInvest'].to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pGenUpInvest          = Param(mTEPES.eb,    initialize=par['pGenUpInvest'].to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)
    mTEPES.pGenLoRetire          = Param(mTEPES.gd,    initialize=par['pGenLoRetire'].to_dict()              , within=NonNegativeReals,    doc='Lower bound of the retirement decision', mutable=True)
    mTEPES.pGenUpRetire          = Param(mTEPES.gd,    initialize=par['pGenUpRetire'].to_dict()              , within=NonNegativeReals,    doc='Upper bound of the retirement decision', mutable=True)

    if par['pIndRampReserves']:
        mTEPES.pRampReserveUp    = Param(mTEPES.psnar, initialize=par['pRampReserveUp'].to_dict()            , within=NonNegativeReals,    doc='Ramp up   reserve'                                   )
        mTEPES.pRampReserveDw    = Param(mTEPES.psnar, initialize=par['pRampReserveDw'].to_dict()            , within=NonNegativeReals,    doc='Ramp down reserve'                                   )

    if par['pIndReserveActivation']:
        mTEPES.pOperReserveUpEnergy = Param(mTEPES.psnar, initialize=par['pOperReserveUpEnergy'].to_dict()   , within=NonNegativeReals,    doc='Operating reserve activation'                        )
        mTEPES.pOperReserveDwEnergy = Param(mTEPES.psnar, initialize=par['pOperReserveDwEnergy'].to_dict()   , within=NonNegativeReals,    doc='Operating reserve activation'                        )

    if par['pIndHydrogen']:
        mTEPES.pProductionFunctionH2 = Param(mTEPES.el, initialize=par['pProductionFunctionH2'].to_dict()    , within=NonNegativeReals,    doc='Production function of an electrolyzer plant'        )

    if par['pIndHeat']:
        par['pMinPowerHeat'] = filter_rows(par['pMinPowerHeat'], mTEPES.psnch)
        par['pMaxPowerHeat'] = filter_rows(par['pMaxPowerHeat'], mTEPES.psnch)

        mTEPES.pReserveMarginHeat          = Param(mTEPES.par,   initialize=par['pReserveMarginHeat'].to_dict()         , within=NonNegativeReals, doc='Adequacy reserve margin'                  )
        mTEPES.pRatedMaxPowerHeat          = Param(mTEPES.gg,    initialize=par['pRatedMaxPowerHeat'].to_dict()         , within=NonNegativeReals, doc='Rated maximum heat'                       )
        mTEPES.pMinPowerHeat               = Param(mTEPES.psnch, initialize=par['pMinPowerHeat'].to_dict()              , within=NonNegativeReals, doc='Minimum heat     power'                   )
        mTEPES.pMaxPowerHeat               = Param(mTEPES.psnch, initialize=par['pMaxPowerHeat'].to_dict()              , within=NonNegativeReals, doc='Maximum heat     power'                   )
        mTEPES.pPower2HeatRatio            = Param(mTEPES.ch,    initialize=par['pPower2HeatRatio'].to_dict()           , within=NonNegativeReals, doc='Power to heat ratio'                      )
        mTEPES.pProductionFunctionHeat     = Param(mTEPES.hp,    initialize=par['pProductionFunctionHeat'].to_dict()    , within=NonNegativeReals, doc='Production function of an CHP plant'      )
        mTEPES.pProductionFunctionH2ToHeat = Param(mTEPES.hh,    initialize=par['pProductionFunctionH2ToHeat'].to_dict(), within=NonNegativeReals, doc='Production function of an boiler using H2')

    if par['pIndPTDF']:
        mTEPES.pPTDF                       = Param(mTEPES.psnland, initialize=par['pPTDF'].to_dict()                    , within=Reals           , doc='Power transfer distribution factor'       )

    if par['pIndHydroTopology']:
        par['pHydroInflows']  = filter_rows(par['pHydroInflows'] , mTEPES.psnrs)
        par['pHydroOutflows'] = filter_rows(par['pHydroOutflows'], mTEPES.psnrs)
        par['pMaxOutflows']   = filter_rows(par['pMaxOutflows']  , mTEPES.psnrs)
        par['pMinVolume']     = filter_rows(par['pMinVolume']    , mTEPES.psnrs)
        par['pMaxVolume']     = filter_rows(par['pMaxVolume']    , mTEPES.psnrs)
        par['pIniVolume']     = filter_rows(par['pIniVolume']    , mTEPES.psnrs)

        mTEPES.pProductionFunctionHydro = Param(mTEPES.h ,    initialize=par['pProductionFunctionHydro'].to_dict(), within=NonNegativeReals, doc='Production function of a hydro power plant'  )
        mTEPES.pHydroInflows            = Param(mTEPES.psnrs, initialize=par['pHydroInflows'].to_dict()           , within=NonNegativeReals, doc='Hydro inflows',                  mutable=True)
        mTEPES.pHydroOutflows           = Param(mTEPES.psnrs, initialize=par['pHydroOutflows'].to_dict()          , within=NonNegativeReals, doc='Hydro outflows',                 mutable=True)
        mTEPES.pMaxOutflows             = Param(mTEPES.psnrs, initialize=par['pMaxOutflows'].to_dict()            , within=NonNegativeReals, doc='Maximum hydro outflows',                     )
        mTEPES.pMinVolume               = Param(mTEPES.psnrs, initialize=par['pMinVolume'].to_dict()              , within=NonNegativeReals, doc='Minimum reservoir volume capacity'           )
        mTEPES.pMaxVolume               = Param(mTEPES.psnrs, initialize=par['pMaxVolume'].to_dict()              , within=NonNegativeReals, doc='Maximum reservoir volume capacity'           )
        mTEPES.pIndBinRsrvInvest        = Param(mTEPES.rn,    initialize=par['pIndBinRsrvInvest'].to_dict()       , within=Binary          , doc='Binary  reservoir investment decision'       )
        mTEPES.pRsrInvestCost           = Param(mTEPES.rn,    initialize=par['pRsrInvestCost'].to_dict()          , within=NonNegativeReals, doc='Reservoir fixed cost'                        )
        mTEPES.pRsrPeriodIni            = Param(mTEPES.rs,    initialize=par['pRsrPeriodIni'].to_dict()           , within=PositiveIntegers, doc='Installation year',                          )
        mTEPES.pRsrPeriodFin            = Param(mTEPES.rs,    initialize=par['pRsrPeriodFin'].to_dict()           , within=PositiveIntegers, doc='Retirement   year',                          )
        mTEPES.pReservoirTimeStep       = Param(mTEPES.rs,    initialize=par['pReservoirTimeStep'].to_dict()      , within=PositiveIntegers, doc='Reservoir volume cycle'                      )
        mTEPES.pWaterOutTimeStep        = Param(mTEPES.rs,    initialize=par['pWaterOutTimeStep'].to_dict()       , within=PositiveIntegers, doc='Reservoir outflows cycle'                    )
        mTEPES.pIniVolume               = Param(mTEPES.psnrs, initialize=par['pIniVolume'].to_dict()              , within=NonNegativeReals, doc='Reservoir initial volume',       mutable=True)
        mTEPES.pInitialVolume           = Param(mTEPES.rs,    initialize=par['pInitialVolume'].to_dict()          , within=NonNegativeReals, doc='Reservoir initial volume without load levels')
        mTEPES.pReservoirType           = Param(mTEPES.rs,    initialize=par['pReservoirType'].to_dict()          , within=Any             , doc='Reservoir volume type'                       )

    if par['pIndHydrogen']:
        par['pDemandH2']    = filter_rows(par['pDemandH2']   ,mTEPES.psnnd)
        par['pDemandH2Abs'] = filter_rows(par['pDemandH2Abs'],mTEPES.psnnd)

        mTEPES.pDemandH2    = Param(mTEPES.psnnd, initialize=par['pDemandH2'].to_dict()   , within=NonNegativeReals,    doc='Hydrogen demand per hour')
        mTEPES.pDemandH2Abs = Param(mTEPES.psnnd, initialize=par['pDemandH2Abs'].to_dict(), within=NonNegativeReals,    doc='Hydrogen demand'         )

    if par['pIndHeat']:
        par['pDemandHeat']     = filter_rows(par['pDemandHeat']    , mTEPES.psnnd)
        par['pDemandHeatAbs']  = filter_rows(par['pDemandHeatAbs'] , mTEPES.psnnd)

        mTEPES.pDemandHeatPeak = Param(mTEPES.par,   initialize=par['pDemandHeatPeak'].to_dict(), within=NonNegativeReals,    doc='Peak heat demand'        )
        mTEPES.pDemandHeat     = Param(mTEPES.psnnd, initialize=par['pDemandHeat'].to_dict()   ,  within=NonNegativeReals,    doc='Heat demand per hour'    )
        mTEPES.pDemandHeatAbs  = Param(mTEPES.psnnd, initialize=par['pDemandHeatAbs'].to_dict(),  within=NonNegativeReals,    doc='Heat demand'             )

    mTEPES.pLoadLevelDuration = Param(mTEPES.psn,   initialize=0.0                                     ,  within=NonNegativeReals,    doc='Load level duration', mutable=True)
    for p,sc,n in mTEPES.psn:
        mTEPES.pLoadLevelDuration[p,sc,n] = float(mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pDuration[p,sc,n]())

    mTEPES.pPeriodProb         = Param(mTEPES.ps,    initialize=0.0                                    ,  within=NonNegativeReals,   doc='Period probability',  mutable=True)
    for p,sc in mTEPES.ps:
        # periods and scenarios are going to be solved together with their weight and probability
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc]

    par['pMaxTheta'] = filter_rows(par['pMaxTheta'], mTEPES.psnnd)

    mTEPES.pLineLossFactor   = Param(mTEPES.ll,    initialize=par['pLineLossFactor'].to_dict()  , within=           Reals,    doc='Loss factor'                                                       )
    mTEPES.pLineR            = Param(mTEPES.la,    initialize=par['pLineR'].to_dict()           , within=NonNegativeReals,    doc='Resistance'                                                        )
    mTEPES.pLineX            = Param(mTEPES.la,    initialize=par['pLineX'].to_dict()           , within=           Reals,    doc='Reactance'                                                         )
    mTEPES.pLineBsh          = Param(mTEPES.la,    initialize=par['pLineBsh'].to_dict()         , within=NonNegativeReals,    doc='Susceptance',                                          mutable=True)
    mTEPES.pLineTAP          = Param(mTEPES.la,    initialize=par['pLineTAP'].to_dict()         , within=NonNegativeReals,    doc='Tap changer',                                          mutable=True)
    mTEPES.pLineLength       = Param(mTEPES.la,    initialize=par['pLineLength'].to_dict()      , within=NonNegativeReals,    doc='Length',                                               mutable=True)
    mTEPES.pElecNetPeriodIni = Param(mTEPES.la,    initialize=par['pElecNetPeriodIni'].to_dict(), within=PositiveIntegers,    doc='Installation period'                                               )
    mTEPES.pElecNetPeriodFin = Param(mTEPES.la,    initialize=par['pElecNetPeriodFin'].to_dict(), within=PositiveIntegers,    doc='Retirement   period'                                               )
    mTEPES.pLineVoltage      = Param(mTEPES.la,    initialize=par['pLineVoltage'].to_dict()     , within=NonNegativeReals,    doc='Voltage'                                                           )
    mTEPES.pLineNTCFrw       = Param(mTEPES.la,    initialize=par['pLineNTCFrw'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC forward'                                         )
    mTEPES.pLineNTCBck       = Param(mTEPES.la,    initialize=par['pLineNTCBck'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC backward'                                        )
    mTEPES.pLineNTCMax       = Param(mTEPES.la,    initialize=par['pLineNTCMax'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC'                                                 )
    mTEPES.pNetFixedCost     = Param(mTEPES.lc,    initialize=par['pNetFixedCost'].to_dict()    , within=NonNegativeReals,    doc='Electric line fixed cost'                                          )
    mTEPES.pIndBinLineInvest = Param(mTEPES.la,    initialize=par['pIndBinLineInvest'].to_dict(), within=Binary          ,    doc='Binary electric line investment decision'                          )
    mTEPES.pIndBinLineSwitch = Param(mTEPES.la,    initialize=par['pIndBinLineSwitch'].to_dict(), within=Binary          ,    doc='Binary electric line switching  decision'                          )
    # mTEPES.pSwOnTime       = Param(mTEPES.la,    initialize=par['pSwitchOnTime'].to_dict()    , within=NonNegativeIntegers, doc='Minimum switching on  time'                                        )
    # mTEPES.pSwOffTime      = Param(mTEPES.la,    initialize=par['pSwitchOffTime'].to_dict()   , within=NonNegativeIntegers, doc='Minimum switching off time'                                        )
    mTEPES.pBigMFlowBck      = Param(mTEPES.la,    initialize=par['pBigMFlowBck'].to_dict()     , within=NonNegativeReals,    doc='Maximum backward capacity',                            mutable=True)
    mTEPES.pBigMFlowFrw      = Param(mTEPES.la,    initialize=par['pBigMFlowFrw'].to_dict()     , within=NonNegativeReals,    doc='Maximum forward  capacity',                            mutable=True)
    mTEPES.pMaxTheta         = Param(mTEPES.psnnd, initialize=par['pMaxTheta'].to_dict()        , within=NonNegativeReals,    doc='Maximum voltage angle',                                mutable=True)
    mTEPES.pAngMin           = Param(mTEPES.la,    initialize=par['pAngMin'].to_dict()          , within=           Reals,    doc='Minimum phase angle difference',                       mutable=True)
    mTEPES.pAngMax           = Param(mTEPES.la,    initialize=par['pAngMax'].to_dict()          , within=           Reals,    doc='Maximum phase angle difference',                       mutable=True)
    mTEPES.pNetLoInvest      = Param(mTEPES.lc,    initialize=par['pNetLoInvest'].to_dict()     , within=NonNegativeReals,    doc='Lower bound of the electric line investment decision', mutable=True)
    mTEPES.pNetUpInvest      = Param(mTEPES.lc,    initialize=par['pNetUpInvest'].to_dict()     , within=NonNegativeReals,    doc='Upper bound of the electric line investment decision', mutable=True)
    mTEPES.pIndBinLinePTDF   = Param(mTEPES.la,    initialize=par['pIndBinLinePTDF'].to_dict()  , within=Binary          ,    doc='Binary indicator of line with'                                     )
    mTEPES.pMaxNTCFrw        = Param(mTEPES.psnla, initialize=par['pMaxNTCFrw'].to_dict()       , within=           Reals,    doc='Maximum NTC forward capacity'                                      )
    mTEPES.pMaxNTCBck        = Param(mTEPES.psnla, initialize=par['pMaxNTCBck'].to_dict()       , within=           Reals,    doc='Maximum NTC backward capacity'                                     )
    mTEPES.pMaxNTCMax        = Param(mTEPES.psnla, initialize=par['pMaxNTCMax'].to_dict()       , within=           Reals,    doc='Maximum NTC capacity'                                              )

    if par['pIndHydrogen']:
        mTEPES.pH2PipeLength       = Param(mTEPES.pn,  initialize=par['pH2PipeLength'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline length',                        mutable=True)
        mTEPES.pH2PipePeriodIni    = Param(mTEPES.pn,  initialize=par['pH2PipePeriodIni'].to_dict()   , within=PositiveIntegers,    doc='Installation period'                                          )
        mTEPES.pH2PipePeriodFin    = Param(mTEPES.pn,  initialize=par['pH2PipePeriodFin'].to_dict()   , within=PositiveIntegers,    doc='Retirement   period'                                          )
        mTEPES.pH2PipeNTCFrw       = Param(mTEPES.pn,  initialize=par['pH2PipeNTCFrw'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC forward'                                )
        mTEPES.pH2PipeNTCBck       = Param(mTEPES.pn,  initialize=par['pH2PipeNTCBck'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC backward'                               )
        mTEPES.pH2PipeFixedCost    = Param(mTEPES.pc,  initialize=par['pH2PipeFixedCost'].to_dict()   , within=NonNegativeReals,    doc='Hydrogen pipeline fixed cost'                                 )
        mTEPES.pIndBinH2PipeInvest = Param(mTEPES.pn,  initialize=par['pIndBinH2PipeInvest'].to_dict(), within=Binary          ,    doc='Binary   pipeline investment decision'                        )
        mTEPES.pH2PipeLoInvest     = Param(mTEPES.pc,  initialize=par['pH2PipeLoInvest'].to_dict()    , within=NonNegativeReals,    doc='Lower bound of the pipeline investment decision', mutable=True)
        mTEPES.pH2PipeUpInvest     = Param(mTEPES.pc,  initialize=par['pH2PipeUpInvest'].to_dict()    , within=NonNegativeReals,    doc='Upper bound of the pipeline investment decision', mutable=True)

    if par['pIndHeat']:
        mTEPES.pHeatPipeLength       = Param(mTEPES.hn, initialize=par['pHeatPipeLength'].to_dict()      , within=NonNegativeReals, doc='Heat pipe length',                                 mutable=True)
        mTEPES.pHeatPipePeriodIni    = Param(mTEPES.hn, initialize=par['pHeatPipePeriodIni'].to_dict()   , within=PositiveIntegers, doc='Installation period'                                           )
        mTEPES.pHeatPipePeriodFin    = Param(mTEPES.hn, initialize=par['pHeatPipePeriodFin'].to_dict()   , within=PositiveIntegers, doc='Retirement   period'                                           )
        mTEPES.pHeatPipeNTCFrw       = Param(mTEPES.hn, initialize=par['pHeatPipeNTCFrw'].to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC forward'                                         )
        mTEPES.pHeatPipeNTCBck       = Param(mTEPES.hn, initialize=par['pHeatPipeNTCBck'].to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC backward'                                        )
        mTEPES.pHeatPipeFixedCost    = Param(mTEPES.hc, initialize=par['pHeatPipeFixedCost'].to_dict()   , within=NonNegativeReals, doc='Heat pipe fixed cost'                                          )
        mTEPES.pIndBinHeatPipeInvest = Param(mTEPES.hn, initialize=par['pIndBinHeatPipeInvest'].to_dict(), within=Binary          , doc='Binary  heat pipe investment decision'                         )
        mTEPES.pHeatPipeLoInvest     = Param(mTEPES.hc, initialize=par['pHeatPipeLoInvest'].to_dict()    , within=NonNegativeReals, doc='Lower bound of the heat pipe investment decision', mutable=True)
        mTEPES.pHeatPipeUpInvest     = Param(mTEPES.hc, initialize=par['pHeatPipeUpInvest'].to_dict()    , within=NonNegativeReals, doc='Upper bound of the heat pipe investment decision', mutable=True)

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) % mTEPES.pStorageTimeStep [es] == 0]
    mTEPES.nesl         = [(n,el) for n,el in mTEPES.n*mTEPES.el if mTEPES.n.ord(n) % mTEPES.pStorageTimeStep [el] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) % mTEPES.pStorageTimeStep [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) % mTEPES.pEnergyTimeStep  [g ] == 0]
    if par['pIndHydroTopology']:
        mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
        if sum(1 for h,rs in mTEPES.p2r):
            mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
        else:
            mTEPES.np2c = []
        if sum(1 for rs,h in mTEPES.r2p):
            mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
        else:
            mTEPES.npc  = []
        mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

    # ESS with outflows
    mTEPES.eo     = [(p,sc,es) for p,sc,es in mTEPES.pses if sum(mTEPES.pEnergyOutflows[p,sc,n2,es]() for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    if par['pIndHydroTopology']:
        # reservoirs with outflows
        mTEPES.ro = [(p,sc,rs) for p,sc,rs in mTEPES.psrs if sum(mTEPES.pHydroOutflows [p,sc,n2,rs]() for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    # generators with min/max energy
    mTEPES.gm     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMinEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn) and sum(mTEPES.pMaxPowerElec[p,sc,n2,g] for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    mTEPES.gM     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMaxEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn) and sum(mTEPES.pMaxPowerElec[p,sc,n2,g] for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]

    # # if unit availability = 0 changed to 1
    # for g in mTEPES.g:
    #     if  mTEPES.pAvailability[g]() == 0.0:
    #         mTEPES.pAvailability[g]   =  1.0

    # if line length = 0 changed to 110% the geographical distance
    for ni,nf,cc in mTEPES.la:
        if  mTEPES.pLineLength[ni,nf,cc]() == 0.0:
            mTEPES.pLineLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if par['pIndHydrogen']:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pH2PipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pH2PipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if par['pIndHeat']:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pHeatPipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pHeatPipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    # initialize generation output, unit commitment and line switching
    par['pInitialOutput'] = pd.DataFrame([[0.0]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.g )
    par['pInitialUC']     = pd.DataFrame([[0  ]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.g )
    par['pInitialSwitch'] = pd.DataFrame([[0  ]*len(mTEPES.la)]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.la)

    par['pInitialOutput'] = filter_rows(par['pInitialOutput'], mTEPES.psng )
    par['pInitialUC']     = filter_rows(par['pInitialUC']    , mTEPES.psng )
    par['pInitialSwitch'] = filter_rows(par['pInitialSwitch'], mTEPES.psnla)

    mTEPES.pInitialOutput = Param(mTEPES.psng , initialize=par['pInitialOutput'].to_dict(), within=NonNegativeReals, doc='unit initial output',     mutable=True)
    mTEPES.pInitialUC     = Param(mTEPES.psng , initialize=par['pInitialUC'].to_dict()    , within=Binary,           doc='unit initial commitment', mutable=True)
    mTEPES.pInitialSwitch = Param(mTEPES.psnla, initialize=par['pInitialSwitch'].to_dict(), within=Binary,           doc='line initial switching',  mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')
