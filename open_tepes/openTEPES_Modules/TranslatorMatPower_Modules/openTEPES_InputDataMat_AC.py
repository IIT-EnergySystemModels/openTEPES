# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020

import time
import math
import pandas as pd

from   pyomo.environ import Param, RangeSet, NonNegativeReals, Var, Reals, Set, DataPortal, UnitInterval, Binary

from openTEPES_Modules.TranslatorMatPower_Modules.ParseMatPower import parse_mp_case


def InputDataMat_AC(CaseName, mTEPES, pVmin, pVnom, pVmax, pCapacitivePF, pInductivePF):
    StartTime = time.time()

    #%% AC Power Flow: Additional Sets
    mTEPES.L            = RangeSet(20)

    #%% AC Power Flow: Additional Parameters
    pVmin               = 0.94
    pVnom               = 1.00
    pVmax               = 1.06
    pCapacitivePF       = 0.95                #Capacitive Power Factor
    pInductivePF        = 0.99                #Inductive  Power Factor

    #%% reading the sets
    dictSets            = DataPortal()
    dictSets.load(filename='MatCases/oT_Dict_BusShunt.csv', set='sh'  , format='set')

    #%% reading data from CSV
    dfGeneration        = pd.read_csv('MatCases/oT_Data_Generation.csv',                      index_col=[0    ])
    dfBusShunt          = pd.read_csv('MatCases/oT_Data_BusShunt.csv',                        index_col=[0    ])
    dfVariableMaxPower  = pd.read_csv('MatCases/oT_Data_VariableGeneration.csv',              index_col=[0,1,2])
    dfReactiveDemand    = pd.read_csv('MatCases/oT_Data_ReactiveDemand.csv',                  index_col=[0,1,2])

    # substitute NaN by 0
    dfGeneration.fillna      (0, inplace=True)
    dfVariableMaxPower.fillna(0, inplace=True)
    dfReactiveDemand.fillna  (0, inplace=True)
    dfBusShunt.fillna        (0, inplace=True)

    #%%________________________________________________________________________________________
    # Modifying relevant DATA
    case = parse_mp_case('MatCases/'+CaseName+'.m')
    case = case.make_per_unit()
    case = case.make_radians()

    buses            = {x.bus_i : x for x in case.bus}
    BusesIdx         = [*buses]
    dfReactiveDemand = pd.DataFrame(0, index=dfReactiveDemand.index, columns=BusesIdx)
    dfBusShunt       = pd.DataFrame(0, index=['BusBshb_'+str(key) for key in BusesIdx], columns=dfBusShunt.columns)
    dfBusShunt['Node'] = BusesIdx

    for b, bus in buses.items():
        dfReactiveDemand[b] = bus.Qd*1e2
        dfBusShunt.loc['BusBshb_'+str(b), 'Gshb'] = bus.Gs/10
        dfBusShunt.loc['BusBshb_'+str(b), 'Bshb'] = bus.Bs/10

    generators   = {x.idx : x for x in case.gen}
    GenIdx       = [*generators]
    dfGeneration = pd.DataFrame(0, index=GenIdx, columns=dfGeneration.columns)
    for g, gen in generators.items():
        dfGeneration.loc[g, 'Node']         = gen.bus
        dfGeneration.loc[g, 'MaximumReactivePower'] = gen.Qmax*1e2
        dfGeneration.loc[g, 'MinimumReactivePower'] = gen.Qmin*1e2

    dfVariableMaxPower   = pd.DataFrame(0, index = dfVariableMaxPower.index,   columns = dfGeneration.index)
    #%%________________________________________________________________________________________
    # Modifying relevant METADATA
    dictSets['sh' ]     = list(['BusBshb_'+str(key) for key in BusesIdx])
    mTEPES.sh           = Set(initialize=dictSets['sh']     ,   ordered=True,  doc='Bus shunt'     )
    # mTEPES.gr           = mTEPES.nr + mTEPES.gq

    pGenToNode          = dfGeneration      ['Node'                ]                                   # generator location in node
    pRMinReactivePower  = dfGeneration      ['MinimumReactivePower'] * 1e-3                            # rated minimum reactive power        [Gvar]
    pRMaxReactivePower  = dfGeneration      ['MaximumReactivePower'] * 1e-3
    pShuntToNode        = dfBusShunt        ['Node'                ]                                   # Shunt location in node
    pBusGshb            = dfBusShunt        ['Gshb'                ]                                   # Conductance shunt at bus i          [pu]
    pBusBshb            = dfBusShunt        ['Bshb'                ]                                   # Susceptance shunt at bus i          [pu]
    pShuntFixedCost     = dfBusShunt        ['FixedCost'           ] * dfBusShunt['FixedChargeRate']   # Shunt compensation fixed cost       [MEUR]
    pShuntBinUnitInvest = dfBusShunt        ['BinaryInvestment'    ]                                   # Shunt binary unit investment
    pVariableMaxPower   = dfVariableMaxPower[list(mTEPES.gq)       ] * 1e-3                            # dynamic variable maximum power      [GW]
    pReactiveDemand     = dfReactiveDemand  [list(mTEPES.nd)       ] * 1e-3                            # Reactive demand                     [Gvar]

    pTimeStep = mTEPES.pTimeStep*1

    pVariableMaxPower   = pVariableMaxPower.rolling(pTimeStep).mean()
    pReactiveDemand     = pReactiveDemand.rolling  (pTimeStep).mean()

    pVariableMaxPower.fillna(0, inplace=True)
    pReactiveDemand.fillna  (0, inplace=True)

    #%% defining subsets: shc (candidate shunt compensation)
    mTEPES.shc   = Set(initialize=mTEPES.sh , ordered=False, doc='candidate shunt units', filter=lambda mTEPES,sh : sh in mTEPES.sh  and pShuntFixedCost[sh ] >  0)

    # Existing shunt compensation (she)
    mTEPES.she   = mTEPES.sh - mTEPES.shc

    #%% inverse index node to equipment
    pNodeToSynch = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pNodeToSynch = pNodeToSynch.loc[pNodeToSynch['Generator'].isin(mTEPES.sq)]

    pNodeToShunt = pShuntToNode.reset_index().set_index('Node').set_axis(['Shunt'], axis=1, inplace=False)[['Shunt']]
    pNodeToShunt = pNodeToShunt.loc[pNodeToShunt['Shunt'].isin(mTEPES.sh)]

    pNode2Synch  = pNodeToSynch.reset_index()
    pNode2Synch['Y/N'] = 1
    pNode2Synch  = pNode2Synch.set_index(['Node','Generator'])['Y/N']

    pNode2Shunt  = pNodeToShunt.reset_index()
    pNode2Shunt['Y/N'] = 1
    pNode2Shunt  = pNode2Shunt.set_index(['Node','Shunt'])['Y/N']

    mTEPES.n2gq  = Set(initialize=mTEPES.nd*mTEPES.sq, doc='node to synchronous condenser', filter=lambda mTEPES,nd,sq: (nd,sq) in pNode2Synch)
    mTEPES.n2sh  = Set(initialize=mTEPES.nd*mTEPES.sh, doc='node to shunt compensation'   , filter=lambda mTEPES,nd,sh: (nd,sh) in pNode2Shunt)
    mTEPES.sh2n  = pShuntToNode
    # minimum and maximum variable power
    pVariableMaxPower   = pVariableMaxPower.replace(0, float('nan'))[mTEPES.gq]

    pMinReactivePower   = pd.DataFrame([pRMinReactivePower]*len(pVariableMaxPower.index), index=pd.MultiIndex.from_tuples(pVariableMaxPower.index), columns=pRMinReactivePower.index)[mTEPES.gq]
    pMaxReactivePower   = pd.DataFrame([pRMaxReactivePower]*len(pVariableMaxPower.index), index=pd.MultiIndex.from_tuples(pVariableMaxPower.index), columns=pRMaxReactivePower.index)[mTEPES.gq]

    # values < 1e-5 times the maximum system demand are converted to 0
    pEpsilon = pReactiveDemand.max().sum()*1e-5
    pReactiveDemand  [pReactiveDemand   < pEpsilon] = 0
    pVariableMaxPower[pVariableMaxPower < pEpsilon] = 0
    pMaxReactivePower[pMaxReactivePower < pEpsilon] = 0

    pReactiveDemand   = pReactiveDemand.loc  [list(mTEPES.sc*mTEPES.p*mTEPES.n)]
    pMinReactivePower = pMinReactivePower.loc[list(mTEPES.sc*mTEPES.p*mTEPES.n)]
    pMaxReactivePower = pMaxReactivePower.loc[list(mTEPES.sc*mTEPES.p*mTEPES.n)]

    #%% Parameters: Nodes
    mTEPES.pReactiveDemand   = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pReactiveDemand.stack().to_dict(), within=NonNegativeReals, doc='ReactiveDemand'                                     )
    mTEPES.pBusGshb          = Param(                               mTEPES.sh, initialize=pBusGshb.to_dict(),                within=Reals,            doc='Shunt Conductance'                                  )
    mTEPES.pBusBshb          = Param(                               mTEPES.sh, initialize=pBusBshb.to_dict(),                within=Reals,            doc='Shunt Susceptance'                                  )

    #%% Parameters: Branches
    mTEPES.pLineFi           = Param(mTEPES.la,                                initialize=(0.*math.pi)/180,                                           doc='Line phase angle'                                   )
    mTEPES.pLineSmax         = Param(mTEPES.la,                                initialize=0.,                                                         doc='Maximum apparent power flow in line',   mutable=True)
    # mTEPES.pLineBshl         = Param(mTEPES.la,                                initialize=0.,                                                         doc='Line susceptance',                              )
    mTEPES.pLineZ            = Param(mTEPES.la,                                initialize=0.,                                                         doc='Line impedance',                        mutable=True)
    mTEPES.pLineZ2           = Param(mTEPES.la,                                initialize=0.,                                                         doc='Square of line impedance',              mutable=True)
    mTEPES.pLineG            = Param(mTEPES.la,                                initialize=0.,                                                         doc='Series conductance of line',            mutable=True)
    mTEPES.pLineB            = Param(mTEPES.la,                                initialize=0.,                                                         doc='Series susceptance of line',            mutable=True)
    mTEPES.pLineDelta_S      = Param(mTEPES.la,                                initialize=0.,                                within=NonNegativeReals, doc='Delta of Smax splitted by L',           mutable=True)
    mTEPES.pLineM            = Param(mTEPES.la,mTEPES.L,                       initialize=0.,                                within=NonNegativeReals, doc='M partitions of Delta Smax',            mutable=True)
    mTEPES.pShuntFixedCost   = Param(                               mTEPES.sh, initialize=pShuntFixedCost.to_dict()        , within=NonNegativeReals, doc='Shunt device fixed cost'                            )
    mTEPES.pShuntBinUnitInvest = Param(                             mTEPES.sh, initialize=pShuntBinUnitInvest.to_dict()    , within=NonNegativeReals, doc='Binary investment decision'                         )

    #%% Parameters: Power generation
    mTEPES.pMinReactivePower = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gq, initialize=pMinReactivePower.stack().to_dict(),                        doc='Minimum reactive power'                             )
    mTEPES.pMaxReactivePower = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gq, initialize=pMaxReactivePower.stack().to_dict(),                        doc='Maximum reactive power'                             )

    #%% Parameters: Power System
    mTEPES.pVmin             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pVmin        ,                     within=NonNegativeReals, doc='Minimum voltage magnitude',             mutable=True)
    mTEPES.pVnom             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pVnom        ,                     within=NonNegativeReals, doc='Nominal voltage magnitude',             mutable=True)
    mTEPES.pVmax             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pVmax        ,                     within=NonNegativeReals, doc='Maximum voltage magnitude',             mutable=True)
    mTEPES.pCapacitivePF     = Param(                                          initialize=pCapacitivePF,                     within=NonNegativeReals, doc='Capacitive power factor'                            )
    mTEPES.pInductivePF      = Param(                                          initialize=pInductivePF ,                     within=NonNegativeReals, doc='Inductive power factor'                             )

    for la in mTEPES.la:
        # he comentado estas dos líneas porque no están definidos como mutables estos parámetros, hay que modificarlos en los datos
        mTEPES.pLineBsh    [la] = mTEPES.pLineBsh[la] / 20
        mTEPES.pLineSmax   [la] = mTEPES.pLineNTC[la]*1
        mTEPES.pLineZ2     [la] = mTEPES.pLineR  [la]**2 + mTEPES.pLineX[la]**2
        mTEPES.pLineG      [la] = mTEPES.pLineR  [la] / (mTEPES.pLineR  [la]**2 + mTEPES.pLineX[la]**2)
        mTEPES.pLineB      [la] =-1*mTEPES.pLineX  [la] / (mTEPES.pLineR  [la]**2 + mTEPES.pLineX[la]**2)
        mTEPES.pLineDelta_S[la] = mTEPES.pLineSmax[la] / len(mTEPES.L)
        if mTEPES.pLineTAP[la] == 0:
            mTEPES.pLineTAP[la] = 1
        else:
            mTEPES.pLineTAP[la] = 1. / mTEPES.pLineTAP[la]
        for l in mTEPES.L:
            mTEPES.pLineM[la,l] = (2*l-1)*mTEPES.pLineDelta_S[la]

    #%% Deleting and redefining variables:
    mTEPES.vENS.setlb(0)
    mTEPES.vENS.setub(1)

    # Variables related to investments:
    if mTEPES.pIndBinNetInvest == 0:
        mTEPES.vShuntInvest     = Var(                               mTEPES.shc, within=UnitInterval,                                                 doc='shunt investment decision exists in a year    {0,1}')
    else:
        mTEPES.vShuntInvest     = Var(                               mTEPES.shc, within=Binary,                                                       doc='shunt investment decision exists in a year    {0,1}')

    # relax binary condition in generation and network investment decisions
    for shc in mTEPES.shc:
        if mTEPES.pIndBinNetInvest != 0 and pShuntBinUnitInvest[shc] == 0:
            mTEPES.vShuntInvest[shc].domain = UnitInterval

    # Variables related to power system operation:
    mTEPES.vVoltageMag_sqr      = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd,           within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,nd:(mTEPES.pVmin[sc,p,n,nd]**2,mTEPES.pVmax[sc,p,n,nd]**2),                   doc='Voltage magnitude                                                [p.u.]')
    mTEPES.vCurrentFlow_sqr     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,*la:(0,(mTEPES.pLineSmax[la]**2/pVmax**2)),                                   doc='Current flow                                                        [A]')
    # mTEPES.vCurrentFlow_sqr     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals,                    doc='Current flow                                 [A]')
    mTEPES.vP                   = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=Reals,            bounds=lambda mTEPES,sc,p,n,*la:(-mTEPES.pLineSmax[la],mTEPES.pLineSmax[la]),                             doc='Active Power Flow through lines                                    [GW]')
    mTEPES.vQ                   = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=Reals,            bounds=lambda mTEPES,sc,p,n,*la:(-mTEPES.pLineSmax[la],mTEPES.pLineSmax[la]),                             doc='Reactive Power Flow through lines                                [Gvar]')
    mTEPES.vQ_shl               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.la,within=Reals,                                                                                                                      doc='Reactive Power injection from shunt component of lines           [Gvar]')
    mTEPES.vQ_shc               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.sh,           within=Reals,                                                                                                                      doc='Reactive Power injection from VAr source located in a bus        [Gvar]')
    mTEPES.vThD                 = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=Reals,            bounds=lambda mTEPES,sc,p,n,*la:(mTEPES.pAngMin[la],mTEPES.pAngMax[la]),                                  doc='Phase angle difference                                            [rad]')

    # Variables related to power demand:
    # mTEPES.vENS                 = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd,           within=NonNegativeReals, bounds=(0,1),                                                                        doc='energy not served in node                              [%]')

    # Variables related to the linearization:
    mTEPES.vDelta_P             = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, mTEPES.L, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,ni,nf,cc,l:(0, mTEPES.pLineDelta_S[ni,nf,cc]),                                doc='Delta Active Power Flow                                          [  GW]')
    mTEPES.vDelta_Q             = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, mTEPES.L, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,ni,nf,cc,l:(0, mTEPES.pLineDelta_S[ni,nf,cc]),                                doc='Delta Reactive Power Flow                                        [Gvar]')
    mTEPES.vP_max               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals,                                                                                                           doc='Maximum bound of Active Power Flow                               [  GW]')
    mTEPES.vP_min               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals,                                                                                                           doc='Minimum bound of Active Power Flow                               [  GW]')
    mTEPES.vQ_max               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals,                                                                                                           doc='Maximum bound of Reactive Power Flow                             [Gvar]')
    mTEPES.vQ_min               = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la,           within=NonNegativeReals,                                                                                                           doc='Minimum bound of Reactive Power Flow                             [Gvar]')

    # Variables related to power generation:
    # mTEPES.vReactiveTotalOutput = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr,           within=RealSet,          bounds=lambda mTEPES,sc,p,n,nr :(-mTEPES.pMaxPower[sc,p,n,nr ],mTEPES.pMaxPower[sc,p,n,nr ]),                   doc='Total output of reactive power generators [Gvar]')
    mTEPES.vReactiveTotalOutput = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.tq,           within=Reals,          bounds=lambda mTEPES,sc,p,n,tq :(mTEPES.pMinReactivePower[sc,p,n,tq],mTEPES.pMaxReactivePower[sc,p,n,tq]), doc='Total output of reactive power generators [Gvar]')
    mTEPES.vSynchTotalOutput    = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.sq,           within=Reals,          bounds=lambda mTEPES,sc,p,n,sq :(mTEPES.pMinReactivePower[sc,p,n,sq],mTEPES.pMaxReactivePower[sc,p,n,sq]), doc='Total output of synchronous condenser     [Gvar]')

    SettingUpDataTime = time.time() - StartTime
    StartTime         = time.time()
    print('Setting up AC input data              ... ', round(SettingUpDataTime), 's')
