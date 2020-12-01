"""Input data.

Open Generation and Transmission Operation and Expansion Planning Model with
RES and ESS (openTEPES) - Version 1.7.24 - November 30, 2020
"""

import time

import math

import pandas as pd

from pyomo.environ import DataPortal

from pyomo.environ import Set

from pyomo.environ import Param

from pyomo.environ import Var

from pyomo.environ import Binary

from pyomo.environ import NonNegativeReals

from pyomo.environ import Reals

from pyomo.environ import UnitInterval

from pyomo.environ import Boolean

from pyomo.environ import Any


def InputData(case_name, m_tepes):
    """Input data.

    Input:
        case_name: str
        m_tepes:

    """
    startt_ime = time.time()

    # reading data from CSV
    dfOption = pd.read_csv(
        case_name
        + '/oT_Data_Option_' + case_name + '.csv',
        index_col=[0])

    dfParameter = pd.read_csv(
        case_name
        + '/oT_Data_Parameter_' + case_name + '.csv',
        index_col=[0])

    dfScenario = pd.read_csv(
        case_name
        + '/oT_Data_Scenario_' + case_name + '.csv',
        index_col=[0])

    dfDuration = pd.read_csv(
        case_name
        + '/oT_Data_Duration_' + case_name + '.csv',
        index_col=[0])

    dfDemand = pd.read_csv(
        case_name
        + '/oT_Data_Demand_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfUpOperatingReserve = pd.read_csv(
        case_name
        + '/oT_Data_OperatingReserveUp_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfDwOperatingReserve = pd.read_csv(
        case_name
        + '/oT_Data_OperatingReserveDown_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfGeneration = pd.read_csv(
        case_name
        + '/oT_Data_Generation_' + case_name + '.csv',
        index_col=[0])

    dfVariableMinPower = pd.read_csv(
        case_name
        + '/oT_Data_VariableMinGeneration_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfVariableMaxPower = pd.read_csv(
        case_name
        + '/oT_Data_VariableMaxGeneration_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfVariableMinStorage = pd.read_csv(
        case_name
        + '/oT_Data_MinimumStorage_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfVariableMaxStorage = pd.read_csv(
        case_name
        + '/oT_Data_MaximumStorage_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfEnergyInflows = pd.read_csv(
        case_name
        + '/oT_Data_EnergyInflows_' + case_name + '.csv',
        index_col=[0, 1, 2])

    dfNodeLocation = pd.read_csv(
        case_name
        + '/oT_Data_NodeLocation_' + case_name + '.csv',
        index_col=[0])

    dfNetwork = pd.read_csv(
        case_name
        + '/oT_Data_Network_' + case_name + '.csv',
        index_col=[0, 1, 2])


    # substitute NaN by 0
    dfOption.fillna            (0, inplace=True)
    dfParameter.fillna         (0, inplace=True)
    dfScenario.fillna          (0, inplace=True)
    dfDuration.fillna          (0, inplace=True)
    dfDemand.fillna            (0, inplace=True)
    dfUpOperatingReserve.fillna(0, inplace=True)
    dfDwOperatingReserve.fillna(0, inplace=True)
    dfGeneration.fillna        (0, inplace=True)
    dfVariableMinPower.fillna  (0, inplace=True)
    dfVariableMaxPower.fillna  (0, inplace=True)
    dfVariableMinStorage.fillna(0, inplace=True)
    dfVariableMaxStorage.fillna(0, inplace=True)
    dfEnergyInflows.fillna     (0, inplace=True)
    dfNodeLocation.fillna      (0, inplace=True)
    dfNetwork.fillna           (0, inplace=True)

    # show some statistics of the data
    print('Demand                       \n', dfDemand.describe()            )
    print('Upward operating reserves    \n', dfUpOperatingReserve.describe())
    print('Downward operating reserves  \n', dfDwOperatingReserve.describe())
    print('Generation                   \n', dfGeneration.describe()        )
    print('Variable minimum generation  \n', dfVariableMinPower.describe()  )
    print('Variable maximum generation  \n', dfVariableMaxPower.describe()  )
    print('Minimum storage              \n', dfVariableMinStorage.describe())
    print('Maximum storage              \n', dfVariableMaxStorage.describe())
    print('Energy inflows               \n', dfEnergyInflows.describe()     )
    print('Network                      \n', dfNetwork.describe()           )

    # reading the sets
    dictSets = DataPortal()
    dictSets.load(filename=case_name+'/oT_Dict_Scenario_'    +case_name+'.csv', set='sc'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Period_'      +case_name+'.csv', set='p'   , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_LoadLevel_'   +case_name+'.csv', set='n'   , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Generation_'  +case_name+'.csv', set='g'   , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Technology_'  +case_name+'.csv', set='gt'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Storage_'     +case_name+'.csv', set='st'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Node_'        +case_name+'.csv', set='nd'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Zone_'        +case_name+'.csv', set='zn'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Area_'        +case_name+'.csv', set='ar'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Region_'      +case_name+'.csv', set='rg'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Circuit_'     +case_name+'.csv', set='cc'  , format='set')
    dictSets.load(filename=case_name+'/oT_Dict_Line_'        +case_name+'.csv', set='lt'  , format='set')

    dictSets.load(filename=case_name+'/oT_Dict_NodeToZone_'  +case_name+'.csv', set='ndzn', format='set')
    dictSets.load(filename=case_name+'/oT_Dict_ZoneToArea_'  +case_name+'.csv', set='znar', format='set')
    dictSets.load(filename=case_name+'/oT_Dict_AreaToRegion_'+case_name+'.csv', set='arrg', format='set')

    m_tepes.scc  = Set(initialize=dictSets['sc'],   ordered=True,  doc='scenarios'     )
    m_tepes.p    = Set(initialize=dictSets['p' ],   ordered=True,  doc='periods'       )
    m_tepes.nn   = Set(initialize=dictSets['n' ],   ordered=True,  doc='load levels'   )
    m_tepes.gg   = Set(initialize=dictSets['g' ],   ordered=False, doc='units'         )
    m_tepes.gt   = Set(initialize=dictSets['gt'],   ordered=False, doc='technologies'  )
    m_tepes.st   = Set(initialize=dictSets['st'],   ordered=False, doc='ESS types'     )
    m_tepes.nd   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    m_tepes.ni   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    m_tepes.nf   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    m_tepes.zn   = Set(initialize=dictSets['zn'],   ordered=False, doc='zones'         )
    m_tepes.ar   = Set(initialize=dictSets['ar'],   ordered=False, doc='areas'         )
    m_tepes.rg   = Set(initialize=dictSets['rg'],   ordered=False, doc='regions'       )
    m_tepes.cc   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'      )
    m_tepes.c2   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'      )
    m_tepes.lt   = Set(initialize=dictSets['lt'],   ordered=False, doc='line types'    )

    m_tepes.ndzn = Set(initialize=dictSets['ndzn'], ordered=False, doc='node to zone'  )
    m_tepes.znar = Set(initialize=dictSets['znar'], ordered=False, doc='zone to area'  )
    m_tepes.arrg = Set(initialize=dictSets['arrg'], ordered=False, doc='area to region')

    #%% parameters
    pIndBinGenInvest     = dfOption   ['IndBinGenInvest'][0].astype('int')                                                                # Indicator of binary generation expansion decisions, 0 continuous - 1 binary
    pIndBinNetInvest     = dfOption   ['IndBinNetInvest'][0].astype('int')                                                                # Indicator of binary network    expansion decisions, 0 continuous - 1 binary
    pIndBinGenOperat     = dfOption   ['IndBinGenOperat'][0].astype('int')                                                                # Indicator of binary generation operation decisions, 0 continuous - 1 binary
    pIndNetLosses        = dfOption   ['IndNetLosses'][0].astype('int')                                                                # Indicator of network losses,                        0 lossless   - 1 ohmic losses
    pENSCost             = dfParameter['ENSCost'][0] * 1e-3                                                                       # cost of energy not served           [MEUR/GWh]
    pCO2Cost             = dfParameter['CO2Cost'][0]                                                                              # cost of CO2 emission                [EUR/t CO2]
    pUpReserveActivation = dfParameter['UpReserveActivation'][0]                                                                              # upward   reserve activation         [p.u.]
    pDwReserveActivation = dfParameter['DwReserveActivation'][0]                                                                              # downward reserve activation         [p.u.]
    pSBase               = dfParameter['SBase'][0] * 1e-3                                                                       # base power                          [GW]
    pReferenceNode       = dfParameter['ReferenceNode'][0]                                                                              # reference node
    pTimeStep            = dfParameter['TimeStep'][0].astype('int')                                                                # duration of the unit time step      [h]

    pScenProb            = dfScenario          ['Probability'  ]                                                                          # probabilities of scenarios          [p.u.]
    pDuration            = dfDuration          ['Duration'] * pTimeStep                                                              # duration of load levels             [h]
    pDemand              = dfDemand            [list(m_tepes.nd)] * 1e-3                                                                   # demand                              [GW]
    pOperReserveUp       = dfUpOperatingReserve[list(m_tepes.ar)] * 1e-3                                                                   # upward   operating reserve          [GW]
    pOperReserveDw       = dfDwOperatingReserve[list(m_tepes.ar)] * 1e-3                                                                   # downward operating reserve          [GW]
    pVariableMinPower    = dfVariableMinPower  [list(m_tepes.gg)] * 1e-3                                                                   # dynamic variable minimum power      [GW]
    pVariableMaxPower    = dfVariableMaxPower  [list(m_tepes.gg)] * 1e-3                                                                   # dynamic variable maximum power      [GW]
    pVariableMinStorage  = dfVariableMinStorage[list(m_tepes.gg)] * 1e-3                                                                   # dynamic variable minimum storage    [TWh]
    pVariableMaxStorage  = dfVariableMaxStorage[list(m_tepes.gg)] * 1e-3                                                                   # dynamic variable maximum storage    [TWh]
    pEnergyInflows       = dfEnergyInflows     [list(m_tepes.gg)] * 1e-3                                                                   # dynamic energy inflows              [GW]

    # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for operating reserve, variable max power, variable min and max storage and inflows
    pDemand              = pDemand.rolling            (pTimeStep).mean()
    pOperReserveUp       = pOperReserveUp.rolling     (pTimeStep).mean()
    pOperReserveDw       = pOperReserveDw.rolling     (pTimeStep).mean()
    pVariableMinPower    = pVariableMinPower.rolling  (pTimeStep).mean()
    pVariableMaxPower    = pVariableMaxPower.rolling  (pTimeStep).mean()
    pVariableMinStorage  = pVariableMinStorage.rolling(pTimeStep).mean()
    pVariableMaxStorage  = pVariableMaxStorage.rolling(pTimeStep).mean()
    pEnergyInflows       = pEnergyInflows.rolling     (pTimeStep).mean()

    pDemand.fillna            (0, inplace=True)
    pOperReserveUp.fillna     (0, inplace=True)
    pOperReserveDw.fillna     (0, inplace=True)
    pVariableMinPower.fillna  (0, inplace=True)
    pVariableMaxPower.fillna  (0, inplace=True)
    pVariableMinStorage.fillna(0, inplace=True)
    pVariableMaxStorage.fillna(0, inplace=True)
    pEnergyInflows.fillna     (0, inplace=True)

    if pTimeStep > 1:
        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for i in range(pTimeStep-2,-1,-1):
            pDuration[range(i,len(m_tepes.nn),pTimeStep)] = 0

    # generation parameters
    pGenToNode          = dfGeneration  ['Node']                                                                            # generator location in node
    pGenToTechnology    = dfGeneration  ['Technology']                                                                            # generator association to technology
    pMustRun            = dfGeneration  ['MustRun']                                                                            # must-run unit                       [Yes]
    pRatedMinPower      = dfGeneration  ['MinimumPower'] * 1e-3 * (1-dfGeneration['EFOR'])                                          # rated minimum power                 [GW]
    pRatedMaxPower      = dfGeneration  ['MaximumPower'] * 1e-3 * (1-dfGeneration['EFOR'])                                          # rated maximum power                 [GW]
    pLinearVarCost      = dfGeneration  ['LinearTerm'] * 1e-3 * dfGeneration['FuelCost'] + dfGeneration['OMVariableCost'] * 1e-3  # linear   term variable cost         [MEUR/GWh]
    pConstantVarCost    = dfGeneration  ['ConstantTerm'] * 1e-6 * dfGeneration['FuelCost']                                          # constant term variable cost         [MEUR/h]
    pStartUpCost        = dfGeneration  ['StartUpCost']                                                                            # startup  cost                       [MEUR]
    pShutDownCost       = dfGeneration  ['ShutDownCost']                                                                            # shutdown cost                       [MEUR]
    pRampUp             = dfGeneration  ['RampUp'] * 1e-3                                                                     # ramp up   rate                      [GW/h]
    pRampDw             = dfGeneration  ['RampDown'] * 1e-3                                                                     # ramp down rate                      [GW/h]
    pCO2EmissionCost    = dfGeneration  ['CO2EmissionRate'] * 1e-3 * pCO2Cost                                                          # emission  cost                      [MEUR/GWh]
    pUpTime             = dfGeneration  ['UpTime']                                                                            # minimum up   time                   [h]
    pDwTime             = dfGeneration  ['DownTime']                                                                            # minimum down time                   [h]
    pGenFixedCost       = dfGeneration  ['FixedCost'] *        dfGeneration['FixedChargeRate']                                   # generation fixed cost               [MEUR]
    pIndBinUnitInvest   = dfGeneration  ['BinaryInvestment']                                                                            # binary unit investment decision     [Yes]
    pMaxCharge          = dfGeneration  ['MaximumCharge'] * 1e-3                                                                     # maximum ESS charge                  [GW]
    pInitialInventory   = dfGeneration  ['InitialStorage'] * 1e-3                                                                     # initial ESS storage                 [TWh]
    pRatedMinStorage    = dfGeneration  ['MinimumStorage'] * 1e-3                                                                     # minimum ESS storage                 [TWh]
    pRatedMaxStorage    = dfGeneration  ['MaximumStorage'] * 1e-3                                                                     # maximum ESS storage                 [TWh]
    pEfficiency         = dfGeneration  ['Efficiency']                                                                            #         ESS efficiency              [p.u.]
    pStorageType        = dfGeneration  ['StorageType']                                                                            #         ESS type
    pRMaxReactivePower  = dfGeneration  ['MaximumReactivePower'] * 1e-3                                                                     # rated maximum reactive power        [Gvar]

    pLinearOperCost     = pLinearVarCost + pCO2EmissionCost

    pNodeLat            = dfNodeLocation['Latitude']                                                                            # node latitude                       [º]
    pNodeLon            = dfNodeLocation['Longitude']                                                                            # node longitude                      [º]

    pLineType           = dfNetwork     ['LineType']                                                                            # line type
    pLineVoltage        = dfNetwork     ['Voltage']                                                                            # line voltage                        [kV]
    pLineLossFactor     = dfNetwork     ['LossFactor']                                                                            # loss     factor                     [p.u.]
    pLineR              = dfNetwork     ['Resistance']                                                                            # resistance                          [p.u.]
    pLineX              = dfNetwork     ['Reactance'].sort_index()                                                               # reactance                           [p.u.]
    pLineBsh            = dfNetwork     ['Susceptance']                                                                            # susceptance                         [p.u.]
    pLineTAP            = dfNetwork     ['Tap']                                                                            # tap changer                         [p.u.]
    pConverter          = dfNetwork     ['Converter']                                                                            # converter station                   [Yes]
    pLineNTC            = dfNetwork     ['TTC'] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity               [GW]
    pNetFixedCost       = dfNetwork     ['FixedCost'] *        dfNetwork['FixedChargeRate']                                      # network    fixed cost               [MEUR]
    pIndBinLineInvest   = dfNetwork     ['BinaryInvestment']                                                                            # binary line    investment decision  [Yes]
    pAngMin             = dfNetwork     ['AngMin'] * math.pi / 180                                                            # Min phase angle difference          [rad]
    pAngMax             = dfNetwork     ['AngMax'] * math.pi / 180                                                            # Max phase angle difference          [rad]

    ReadingDataTime = time.time() - startt_ime
    startt_ime       = time.time()
    print('Reading    input data                 ... ', round(ReadingDataTime), 's')

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the lines (la), candidate lines (lc), candidate DC lines (cd), existing DC lines (cd), lines with losses (ll), reference node (rf), and reactive generating units (gq)
    m_tepes.sc = Set(initialize=m_tepes.scc,                    ordered=True , doc='scenarios'          , filter=lambda m_tepes,scc     :  scc       in m_tepes.scc and pScenProb        [scc] >  0)
    m_tepes.n  = Set(initialize=m_tepes.nn,                     ordered=True , doc='load levels'        , filter=lambda m_tepes,nn      :  nn        in m_tepes.nn  and pDuration         [nn] >  0)
    m_tepes.n2 = Set(initialize=m_tepes.nn,                     ordered=True , doc='load levels'        , filter=lambda m_tepes,nn      :  nn        in m_tepes.nn  and pDuration         [nn] >  0)
    m_tepes.g  = Set(initialize=m_tepes.gg,                     ordered=False, doc='generating    units', filter=lambda m_tepes,gg      :  gg        in m_tepes.gg  and pRatedMaxPower    [gg] >  0)
    m_tepes.t  = Set(initialize=m_tepes.g ,                     ordered=False, doc='thermal       units', filter=lambda m_tepes,g       :  g         in m_tepes.g   and pLinearOperCost   [g ] >  0)
    m_tepes.r  = Set(initialize=m_tepes.g ,                     ordered=False, doc='RES           units', filter=lambda m_tepes,g       :  g         in m_tepes.g   and pLinearOperCost   [g ] == 0 and pRatedMaxStorage[g] == 0)
    m_tepes.es = Set(initialize=m_tepes.g ,                     ordered=False, doc='ESS           units', filter=lambda m_tepes,g       :  g         in m_tepes.g   and                                 pRatedMaxStorage[g] >  0)
    m_tepes.gc = Set(initialize=m_tepes.g ,                     ordered=False, doc='candidate     units', filter=lambda m_tepes,g       :  g         in m_tepes.g   and pGenFixedCost     [g ] >  0)
    m_tepes.ec = Set(initialize=m_tepes.es,                     ordered=False, doc='candidate ESS units', filter=lambda m_tepes,es      :  es        in m_tepes.es  and pGenFixedCost     [es] >  0)
    m_tepes.br = Set(initialize=m_tepes.ni*m_tepes.nf,           ordered=False, doc='all branches       ', filter=lambda m_tepes,ni,nf   : (ni,nf)    in                pLineX                     )
    m_tepes.la = Set(initialize=m_tepes.ni*m_tepes.nf*m_tepes.cc, ordered=False, doc='all           lines', filter=lambda m_tepes,ni,nf,cc: (ni,nf,cc) in                pLineX                     )
    m_tepes.lc = Set(initialize=m_tepes.la,                     ordered=False, doc='candidate     lines', filter=lambda m_tepes,*la     :  la        in m_tepes.la  and pNetFixedCost     [la] >  0)
    m_tepes.cd = Set(initialize=m_tepes.la,                     ordered=False, doc='           DC lines', filter=lambda m_tepes,*la     :  la        in m_tepes.la  and pNetFixedCost     [la] >  0 and pLineType[la] == 'DC')
    m_tepes.ed = Set(initialize=m_tepes.la,                     ordered=False, doc='           DC lines', filter=lambda m_tepes,*la     :  la        in m_tepes.la  and pNetFixedCost     [la] == 0 and pLineType[la] == 'DC')
    m_tepes.ll = Set(initialize=m_tepes.la,                     ordered=False, doc='loss          lines', filter=lambda m_tepes,*la     :  la        in m_tepes.la  and pLineLossFactor   [la] >  0 and pIndNetLosses >   0  )
    m_tepes.rf = Set(initialize=m_tepes.nd,                     ordered=True , doc='reference node'     , filter=lambda m_tepes,nd      :  nd        in                pReferenceNode             )
    m_tepes.gq = Set(initialize=m_tepes.gg,                     ordered=False, doc='gen  reactive units', filter=lambda m_tepes,gg      :  gg        in m_tepes.gg  and pRMaxReactivePower[gg] >  0)
    m_tepes.sq = Set(initialize=m_tepes.gg,                     ordered=False, doc='Syn  reactive units', filter=lambda m_tepes,gg      :  gg        in m_tepes.gg  and pRMaxReactivePower[gg] >  0 and pGenToTechnology[gg] == 'SynchronousCondenser')

    # non-RES units, they can be committed
    m_tepes.nr = m_tepes.g - m_tepes.r

    # machines able to provide reactive power
    m_tepes.tq = m_tepes.gq - m_tepes.sq

    # operating reserve units, they can contribute to the operating reserve and are not ESS
    m_tepes.op = m_tepes.nr - m_tepes.es

    # existing lines (le)
    m_tepes.le = m_tepes.la - m_tepes.lc

    # AC existing and candidate lines (lca and lea) and all of them (laa)
    m_tepes.lea = m_tepes.le  - m_tepes.ed
    m_tepes.lca = m_tepes.lc  - m_tepes.cd
    m_tepes.laa = m_tepes.lea | m_tepes.lca

    # # input lines
    # m_tepes.lin = Set(initialize=m_tepes.nf*m_tepes.ni*m_tepes.cc, doc='input line', filter=lambda m_tepes,nf,ni,cc: (ni,nf,cc) in m_tepes.la)
    # m_tepes.lil = Set(initialize=m_tepes.nf*m_tepes.ni*m_tepes.cc, doc='input line', filter=lambda m_tepes,nf,ni,cc: (ni,nf,cc) in m_tepes.ll)

    # replacing string values by numerical values
    idxDict = dict()
    idxDict[0] = 0.0
    idxDict['Yes'] = 1
    idxDict['YES'] = 1
    idxDict['Y'  ] = 1
    idxDict['y'  ] = 1

    pIndBinUnitInvest = pIndBinUnitInvest.map(idxDict)
    pIndBinLineInvest = pIndBinLineInvest.map(idxDict)

    # line type
    pLineType = pLineType.reset_index()
    pLineType['Y/N'] = 1
    pLineType = pLineType.set_index(['level_0','level_1','level_2','LineType'])['Y/N']

    m_tepes.pLineType = Set(initialize=m_tepes.la*m_tepes.lt, doc='line type', filter=lambda m_tepes,ni,nf,cc,lt: (ni,nf,cc,lt) in pLineType)

    #%% inverse index node to generator
    pNodeToGen = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pNodeToGen = pNodeToGen.loc[pNodeToGen['Generator'].isin(m_tepes.g)]

    pNode2Gen = pNodeToGen.reset_index()
    pNode2Gen['Y/N'] = 1
    pNode2Gen = pNode2Gen.set_index(['Node','Generator'])['Y/N']

    m_tepes.n2g = Set(initialize=m_tepes.nd*m_tepes.g, doc='node   to generator', filter=lambda m_tepes,nd,g: (nd,g) in pNode2Gen)

    pZone2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(m_tepes.zn*m_tepes.g), names=('zone',  'generator')), columns=['Y/N'])
    pArea2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(m_tepes.ar*m_tepes.g), names=('area',  'generator')), columns=['Y/N'])
    pRegion2Gen = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(m_tepes.rg*m_tepes.g), names=('region','generator')), columns=['Y/N'])

    for nd,g in m_tepes.n2g:
        for zn in m_tepes.zn:
            if (nd,zn) in m_tepes.ndzn:
                pZone2Gen.loc[zn,g] = 1
            for ar in m_tepes.ar:
                if (nd,zn) in m_tepes.ndzn and (zn,ar) in m_tepes.znar:
                    pArea2Gen.loc[ar,g] = 1
                for rg in m_tepes.rg:
                    if (nd,zn) in m_tepes.ndzn and (zn,ar) in m_tepes.znar and (zn,rg) in m_tepes.arrg:
                        pRegion2Gen.loc[rg,g] = 1

    m_tepes.z2g = Set(initialize=m_tepes.zn*m_tepes.g, doc='zone   to generator', filter=lambda m_tepes,zn,g: (zn,g) in m_tepes.zn*m_tepes.g and pZone2Gen.loc  [zn,g]['Y/N'] == 1)
    m_tepes.a2g = Set(initialize=m_tepes.ar*m_tepes.g, doc='area   to generator', filter=lambda m_tepes,ar,g: (ar,g) in m_tepes.ar*m_tepes.g and pArea2Gen.loc  [ar,g]['Y/N'] == 1)
    m_tepes.r2g = Set(initialize=m_tepes.rg*m_tepes.g, doc='region to generator', filter=lambda m_tepes,rg,g: (rg,g) in m_tepes.rg*m_tepes.g and pRegion2Gen.loc[rg,g]['Y/N'] == 1)

    #%% inverse index generator to technology
    # m_tepes.t2g = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1, inplace=False)['Generator']
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(m_tepes.g)]

    pTechnology2Gen = pTechnologyToGen.reset_index()
    pTechnology2Gen['Y/N'] = 1
    pTechnology2Gen = pTechnology2Gen.set_index(['Technology','Generator'])['Y/N']

    m_tepes.t2g = Set(initialize=m_tepes.gt*m_tepes.g, doc='technology to generator', filter=lambda m_tepes,gt,g: (gt,g) in pTechnology2Gen)

    # minimum and maximum variable power
    pVariableMinPower   = pVariableMinPower.replace(0, float('nan'))
    pVariableMaxPower   = pVariableMaxPower.replace(0, float('nan'))
    pMinPower           = pd.DataFrame([pRatedMinPower]*len(pVariableMinPower.index), index=pd.MultiIndex.from_tuples(pVariableMinPower.index), columns=pRatedMinPower.index)
    pMaxPower           = pd.DataFrame([pRatedMaxPower]*len(pVariableMaxPower.index), index=pd.MultiIndex.from_tuples(pVariableMaxPower.index), columns=pRatedMaxPower.index)

    pVariableMinPower   = pVariableMinPower.reindex(sorted(pVariableMinPower.columns), axis=1)
    pVariableMaxPower   = pVariableMaxPower.reindex(sorted(pVariableMaxPower.columns), axis=1)
    pMinPower           = pMinPower.reindex        (sorted(pMinPower.columns        ), axis=1)
    pMaxPower           = pMaxPower.reindex        (sorted(pMaxPower.columns        ), axis=1)
    pMinPower           = pVariableMinPower.where(pVariableMinPower > pMinPower, other=pMinPower)
    pMaxPower           = pVariableMaxPower.where(pVariableMaxPower < pMaxPower, other=pMaxPower)
    pMaxPower2ndBlock   = pMaxPower - pMinPower

    # minimum and maximum variable storage capacity
    pVariableMinStorage = pVariableMinStorage.replace(0, float('nan'))
    pVariableMaxStorage = pVariableMaxStorage.replace(0, float('nan'))
    pMinStorage         = pd.DataFrame([pRatedMinStorage]*len(pVariableMinStorage.index), index=pd.MultiIndex.from_tuples(pVariableMinStorage.index), columns=pRatedMinStorage.index)
    pMaxStorage         = pd.DataFrame([pRatedMaxStorage]*len(pVariableMaxStorage.index), index=pd.MultiIndex.from_tuples(pVariableMaxStorage.index), columns=pRatedMaxStorage.index)

    pVariableMinStorage = pVariableMinStorage.reindex(sorted(pVariableMinStorage.columns), axis=1)
    pMinStorage         = pMinStorage.reindex        (sorted(pMinStorage.columns        ), axis=1)

    pVariableMaxStorage = pVariableMaxStorage.reindex(sorted(pVariableMaxStorage.columns), axis=1)
    pMaxStorage         = pMaxStorage.reindex        (sorted(pMaxStorage.columns        ), axis=1)

    pMinStorage         = pVariableMinStorage.where(pVariableMinStorage > pMinStorage, other=pMinStorage)
    pMaxStorage         = pVariableMaxStorage.where(pVariableMaxStorage < pMaxStorage, other=pMaxStorage)

    # parameter that allows the initial inventory to change with load level
    pIniInventory       = pd.DataFrame([pInitialInventory]*len(pVariableMinStorage.index), index=pd.MultiIndex.from_tuples(pVariableMinStorage.index), columns=pInitialInventory.index)

    # minimum up and down time converted to an integer number of time steps
    pUpTime = round(pUpTime/pTimeStep).astype('int')
    pDwTime = round(pDwTime/pTimeStep).astype('int')

    #%% definition of the time-steps leap to observe the stored energy at ESS
    pCycleTimeStep = (pUpTime*0).astype('int')
    for es in m_tepes.es:
        if  pStorageType[es] == 'Daily'  :
            pCycleTimeStep[es] = int(  24/pTimeStep)
        if  pStorageType[es] == 'Weekly' :
            pCycleTimeStep[es] = int( 168/pTimeStep)
        if  pStorageType[es] == 'Monthly':
            pCycleTimeStep[es] = int( 672/pTimeStep)
        if  pStorageType[es] == 'Yearly' :
            pCycleTimeStep[es] = int(8736/pTimeStep)

    pStorageType = pStorageType[pStorageType.index.isin(m_tepes.es)]
    m_tepes.pStorageType = Param(m_tepes.es, initialize=pStorageType.to_dict(), within=Any)

    # values < 1e-5 times the maximum system demand are converted to 0
    # these parameters are in GW
    pEpsilon = pDemand.max().sum()*1e-5
    pDemand          [pDemand           < pEpsilon] = 0
    pOperReserveUp   [pOperReserveUp    < pEpsilon] = 0
    pOperReserveDw   [pOperReserveDw    < pEpsilon] = 0
    pMinPower        [pMinPower         < pEpsilon] = 0
    pMaxPower        [pMaxPower         < pEpsilon] = 0
    pMaxPower2ndBlock[pMaxPower2ndBlock < pEpsilon] = 0
    pMaxCharge       [pMaxCharge        < pEpsilon] = 0
    pEnergyInflows   [pEnergyInflows    < pEpsilon] = 0
    pLineNTC         [pLineNTC          < pEpsilon] = 0

    # these parameters are in TWh
    pMinStorage      [pMinStorage       < pEpsilon*1e-3] = 0
    pMaxStorage      [pMaxStorage       < pEpsilon*1e-3] = 0
    pIniInventory    [pIniInventory     < pEpsilon*1e-3] = 0
    pInitialInventory[pInitialInventory < pEpsilon*1e-3] = 0

    # BigM maximum flow to be used in the Kirchhoff's 2nd law disjunctive constraint
    pBigMFlow = pLineNTC*0
    for lea in m_tepes.lea:
        pBigMFlow.loc[lea] = pLineNTC[lea]
    for lca in m_tepes.lca:
        pBigMFlow.loc[lca] = pLineNTC[lca]*1.5

    # maximum voltage angle
    pMaxTheta = pDemand*0 + math.pi/2

    # drop load levels with duration 0
    pDemand           = pDemand.loc          [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pOperReserveUp    = pOperReserveUp.loc   [list(m_tepes.sc*m_tepes.p*m_tepes.n*m_tepes.ar)]
    pOperReserveDw    = pOperReserveDw.loc   [list(m_tepes.sc*m_tepes.p*m_tepes.n*m_tepes.ar)]
    pMinPower         = pMinPower.loc        [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pMaxPower         = pMaxPower.loc        [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pMaxPower2ndBlock = pMaxPower2ndBlock.loc[list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pEnergyInflows    = pEnergyInflows.loc   [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pMinStorage       = pMinStorage.loc      [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pMaxStorage       = pMaxStorage.loc      [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pIniInventory     = pIniInventory.loc    [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pMaxTheta         = pMaxTheta.loc        [list(m_tepes.sc*m_tepes.p*m_tepes.n          )]
    pDuration         = pDuration.loc        [list(                   m_tepes.n          )]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    m_tepes.pIndBinGenInvest      = Param(initialize=pIndBinGenInvest    , within=Boolean, mutable=True)
    m_tepes.pIndBinNetInvest      = Param(initialize=pIndBinNetInvest    , within=Boolean, mutable=True)
    m_tepes.pIndBinGenOperat      = Param(initialize=pIndBinGenOperat    , within=Boolean, mutable=True)
    m_tepes.pIndNetLosses         = Param(initialize=pIndNetLosses       , within=Boolean, mutable=True)

    m_tepes.pENSCost              = Param(initialize=pENSCost            , within=NonNegativeReals)
    m_tepes.pCO2Cost              = Param(initialize=pCO2Cost            , within=NonNegativeReals)
    m_tepes.pUpReserveActivation  = Param(initialize=pUpReserveActivation, within=NonNegativeReals)
    m_tepes.pDwReserveActivation  = Param(initialize=pDwReserveActivation, within=NonNegativeReals)
    m_tepes.pSBase                = Param(initialize=pSBase              , within=NonNegativeReals)
    m_tepes.pTimeStep             = Param(initialize=pTimeStep           , within=NonNegativeReals)

    m_tepes.pDemand               = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nd, initialize=pDemand.stack().to_dict()          , within=NonNegativeReals, doc='Demand'                       )
    m_tepes.pScenProb             = Param(m_tepes.scc,                               initialize=pScenProb.to_dict()                , within=NonNegativeReals, doc='Probability'                  )
    m_tepes.pDuration             = Param(                     m_tepes.n,            initialize=pDuration.to_dict()                , within=NonNegativeReals, doc='Duration'                     )
    m_tepes.pNodeLon              = Param(                               m_tepes.nd, initialize=pNodeLon.to_dict()                 ,                          doc='Longitude'                    )
    m_tepes.pNodeLat              = Param(                               m_tepes.nd, initialize=pNodeLat.to_dict()                 ,                          doc='Latitude'                     )
    m_tepes.pOperReserveUp        = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.ar, initialize=pOperReserveUp.stack().to_dict()   , within=NonNegativeReals, doc='Upward   operating reserve'   )
    m_tepes.pOperReserveDw        = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.ar, initialize=pOperReserveDw.stack().to_dict()   , within=NonNegativeReals, doc='Downward operating reserve'   )
    m_tepes.pMinPower             = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pMinPower.stack().to_dict()        , within=NonNegativeReals, doc='Minimum power'                )
    m_tepes.pMaxPower             = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pMaxPower.stack().to_dict()        , within=NonNegativeReals, doc='Maximum power'                )
    m_tepes.pMaxPower2ndBlock     = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pMaxPower2ndBlock.stack().to_dict(), within=NonNegativeReals, doc='Second block'                 )
    m_tepes.pEnergyInflows        = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pEnergyInflows.stack().to_dict()   , within=NonNegativeReals, doc='Energy inflows'               )
    m_tepes.pMinStorage           = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pMinStorage.stack().to_dict()      , within=NonNegativeReals, doc='ESS Minimum stoarage capacity')
    m_tepes.pMaxStorage           = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pMaxStorage.stack().to_dict()      , within=NonNegativeReals, doc='ESS Maximum stoarage capacity')

    m_tepes.pRatedMaxPower        = Param(                               m_tepes.gg, initialize=pRatedMaxPower.to_dict()           , within=NonNegativeReals, doc='Rated maximum power'          )
    m_tepes.pLinearVarCost        = Param(                               m_tepes.gg, initialize=pLinearVarCost.to_dict()           , within=NonNegativeReals, doc='Linear   variable cost'       )
    m_tepes.pConstantVarCost      = Param(                               m_tepes.gg, initialize=pConstantVarCost.to_dict()         , within=NonNegativeReals, doc='Constant variable cost'       )
    m_tepes.pCO2EmissionCost      = Param(                               m_tepes.gg, initialize=pCO2EmissionCost.to_dict()         , within=NonNegativeReals, doc='CO2 Emission      cost'       )
    m_tepes.pStartUpCost          = Param(                               m_tepes.gg, initialize=pStartUpCost.to_dict()             , within=NonNegativeReals, doc='Startup  cost'                )
    m_tepes.pShutDownCost         = Param(                               m_tepes.gg, initialize=pShutDownCost.to_dict()            , within=NonNegativeReals, doc='Shutdown cost'                )
    m_tepes.pRampUp               = Param(                               m_tepes.gg, initialize=pRampUp.to_dict()                  , within=NonNegativeReals, doc='Ramp up   rate'               )
    m_tepes.pRampDw               = Param(                               m_tepes.gg, initialize=pRampDw.to_dict()                  , within=NonNegativeReals, doc='Ramp down rate'               )
    m_tepes.pUpTime               = Param(                               m_tepes.gg, initialize=pUpTime.to_dict()                  , within=NonNegativeReals, doc='Up   time'                    )
    m_tepes.pDwTime               = Param(                               m_tepes.gg, initialize=pDwTime.to_dict()                  , within=NonNegativeReals, doc='Down time'                    )
    m_tepes.pMaxCharge            = Param(                               m_tepes.gg, initialize=pMaxCharge.to_dict()               , within=NonNegativeReals, doc='Maximum charge power'         )
    m_tepes.pGenFixedCost         = Param(                               m_tepes.gg, initialize=pGenFixedCost.to_dict()            , within=NonNegativeReals, doc='Generation fixed cost'        )
    m_tepes.pIndBinUnitInvest     = Param(                               m_tepes.gg, initialize=pIndBinUnitInvest.to_dict()        , within=NonNegativeReals, doc='Binary investment decision'   )
    m_tepes.pEfficiency           = Param(                               m_tepes.gg, initialize=pEfficiency.to_dict()              , within=NonNegativeReals, doc='Round-trip efficiency'        )
    m_tepes.pCycleTimeStep        = Param(                               m_tepes.gg, initialize=pCycleTimeStep.to_dict()           , within=NonNegativeReals, doc='ESS Storage cycle'            )
    m_tepes.pIniInventory         = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.gg, initialize=pIniInventory.stack().to_dict()    , within=NonNegativeReals, doc='ESS Initial storage',         mutable=True)

    m_tepes.pLineLossFactor       = Param(                               m_tepes.la, initialize=pLineLossFactor.to_dict()          , within=NonNegativeReals, doc='Loss factor'                  )
    m_tepes.pLineR                = Param(                               m_tepes.la, initialize=pLineR.to_dict()                   , within=NonNegativeReals, doc='Resistance'                   )
    m_tepes.pLineX                = Param(                               m_tepes.la, initialize=pLineX.to_dict()                   , within=NonNegativeReals, doc='Reactance'                    )
    m_tepes.pLineBsh              = Param(                               m_tepes.la, initialize=pLineBsh.to_dict()                 , within=NonNegativeReals, doc='Susceptance',                 mutable=True)
    m_tepes.pLineTAP              = Param(                               m_tepes.la, initialize=pLineTAP.to_dict()                 , within=NonNegativeReals, doc='Tap changer',                 mutable=True)
    m_tepes.pConverter            = Param(                               m_tepes.la, initialize=pConverter.to_dict()               , within=NonNegativeReals, doc='Converter'                    )
    m_tepes.pLineVoltage          = Param(                               m_tepes.la, initialize=pLineVoltage.to_dict()             , within=NonNegativeReals, doc='Voltage'                      )
    m_tepes.pLineNTC              = Param(                               m_tepes.la, initialize=pLineNTC.to_dict()                 , within=NonNegativeReals, doc='NTC'                          )
    m_tepes.pNetFixedCost         = Param(                               m_tepes.la, initialize=pNetFixedCost.to_dict()            , within=NonNegativeReals, doc='Network fixed cost'           )
    m_tepes.pIndBinLineInvest     = Param(                               m_tepes.la, initialize=pIndBinLineInvest.to_dict()        , within=NonNegativeReals, doc='Binary investment decision'   )
    m_tepes.pBigMFlow             = Param(                               m_tepes.la, initialize=pBigMFlow.to_dict()                , within=NonNegativeReals, doc='Maximum capacity',            mutable=True)
    m_tepes.pMaxTheta             = Param(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nd, initialize=pMaxTheta.stack().to_dict()        , within=NonNegativeReals, doc='Maximum voltage angle',       mutable=True)
    m_tepes.pAngMin               = Param(                               m_tepes.la, initialize=pAngMin.to_dict()                  , within=Reals,            doc='Minimum phase angle diff',    mutable=True)
    m_tepes.pAngMax               = Param(                               m_tepes.la, initialize=pAngMax.to_dict()                  , within=Reals,            doc='Maximum phase angle diff',    mutable=True)

    #%% variables
    m_tepes.vTotalFCost           = Var(                                          within=NonNegativeReals,                                                                                               doc='total system fixed                   cost      [MEUR]')
    m_tepes.vTotalGCost           = Var(                                          within=NonNegativeReals,                                                                                               doc='total variable generation  operation cost      [MEUR]')
    m_tepes.vTotalCCost           = Var(                                          within=NonNegativeReals,                                                                                               doc='total variable consumption operation cost      [MEUR]')
    m_tepes.vTotalECost           = Var(                                          within=NonNegativeReals,                                                                                               doc='total system emission                cost      [MEUR]')
    m_tepes.vTotalRCost           = Var(                                          within=NonNegativeReals,                                                                                               doc='total system reliability             cost      [MEUR]')
    m_tepes.vTotalOutput          = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.g , within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,g :(0,m_tepes.pMaxPower        [sc,p,n,g ]),                       doc='total output of the unit                         [GW]')
    m_tepes.vOutput2ndBlock       = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,nr:(0,m_tepes.pMaxPower2ndBlock[sc,p,n,nr]),                       doc='second block of the unit                         [GW]')
    m_tepes.vReserveUp            = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,nr:(0,m_tepes.pMaxPower2ndBlock[sc,p,n,nr]),                       doc='upward   operating reserve                       [GW]')
    m_tepes.vReserveDown          = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,nr:(0,m_tepes.pMaxPower2ndBlock[sc,p,n,nr]),                       doc='downward operating reserve                       [GW]')
    m_tepes.vESSInventory         = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,es:(m_tepes.pMinStorage[sc,p,n,es],m_tepes.pMaxStorage[sc,p,n,es]), doc='ESS inventory                                   [TWh]')
    m_tepes.vESSSpillage          = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals,                                                                                               doc='ESS spillage                                    [TWh]')
    m_tepes.vESSTotalCharge       = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,es:(0,m_tepes.pMaxCharge       [es]       ),                       doc='ESS total charge power                           [GW]')
    m_tepes.vESSCharge            = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,es:(0,m_tepes.pMaxCharge       [es]       ),                       doc='ESS charge power                                 [GW]')
    m_tepes.vESSReserveUp         = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,es:(0,m_tepes.pMaxCharge       [es]       ),                       doc='ESS upward   operating reserve                  [GW]')
    m_tepes.vESSReserveDown       = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.es, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,es:(0,m_tepes.pMaxCharge       [es]       ),                       doc='ESS downward operating reserve                   [GW]')
    m_tepes.vENS                  = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nd, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,nd:(0,m_tepes.pDemand          [sc,p,n,nd]),                       doc='energy not served in node                        [GW]')

    if m_tepes.pIndBinGenOperat == 0:
        m_tepes.vCommitment       = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=UnitInterval,                                                                                                   doc='commitment of the unit                          [0,1]')
        m_tepes.vStartUp          = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=UnitInterval,                                                                                                   doc='startup    of the unit                          [0,1]')
        m_tepes.vShutDown         = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=UnitInterval,                                                                                                   doc='shutdown   of the unit                          [0,1]')
    else:
        m_tepes.vCommitment       = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=Binary,                                                                                                         doc='commitment of the unit                          {0,1}')
        m_tepes.vStartUp          = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=Binary,                                                                                                         doc='startup    of the unit                          {0,1}')
        m_tepes.vShutDown         = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nr, within=Binary,                                                                                                         doc='shutdown   of the unit                          {0,1}')

    if m_tepes.pIndBinGenInvest == 0:
        m_tepes.vGenerationInvest = Var(                               m_tepes.gc, within=UnitInterval,                                                                                                   doc='generation investment decision exists in a year [0,1]')
    else:
        m_tepes.vGenerationInvest = Var(                               m_tepes.gc, within=Binary,                                                                                                         doc='generation investment decision exists in a year {0,1}')

    if m_tepes.pIndBinNetInvest == 0:
        m_tepes.vNetworkInvest    = Var(                               m_tepes.lc, within=UnitInterval,                                                                                                   doc='network    investment decision exists in a year [0,1]')
    else:
        m_tepes.vNetworkInvest    = Var(                               m_tepes.lc, within=Binary,                                                                                                         doc='network    investment decision exists in a year {0,1}')

    # relax binary condition in generation and network investment decisions
    for gc in m_tepes.gc:
        if m_tepes.pIndBinGenInvest != 0 and pIndBinUnitInvest[gc] == 0:
            m_tepes.vGenerationInvest[gc].domain = UnitInterval
    for lc in m_tepes.lc:
        if m_tepes.pIndBinNetInvest != 0 and pIndBinLineInvest[lc] == 0:
            m_tepes.vNetworkInvest   [lc].domain = UnitInterval

    m_tepes.vLineLosses           = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.ll, within=NonNegativeReals, bounds=lambda m_tepes,sc,p,n,*ll:(0,0.5*m_tepes.pLineLossFactor[ll]*m_tepes.pLineNTC[ll]),     doc='half line losses                                 [GW]')
    m_tepes.vFlow                 = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.la, within=Reals,            bounds=lambda m_tepes,sc,p,n,*la:(-m_tepes.pLineNTC[la],m_tepes.pLineNTC[la]),                 doc='flow                                             [GW]')
    m_tepes.vTheta                = Var(m_tepes.sc, m_tepes.p, m_tepes.n, m_tepes.nd, within=Reals,            bounds=lambda m_tepes,sc,p,n, nd:(-m_tepes.pMaxTheta[sc,p,n,nd],m_tepes.pMaxTheta[sc,p,n,nd]), doc='voltage angle                                   [rad]')

    for nr in m_tepes.nr:
        if pMustRun[nr] == 'Yes' or pMustRun[nr] == 'YES' or pMustRun[nr] == 'yes' or pMustRun[nr] == 'Y' or pMustRun[nr] == 'y':
            pMustRun[nr] = 1
        else:
            pMustRun[nr] = 0

    for sc,p,n,nr in m_tepes.sc*m_tepes.p*m_tepes.n*m_tepes.nr:
        if pMustRun[nr] == 1:
            m_tepes.vCommitment[sc,p,n,nr].fix(1)

    m_tepes.pMustRun = Param(m_tepes.gg, within=Any, initialize=pMustRun.to_dict())

    # fix the must-run units and their output
    m_tepes.pInitialOutput = pd.Series([0.]*len(m_tepes.gg), dfGeneration.index)
    m_tepes.pInitialUC     = pd.Series([0.]*len(m_tepes.gg), dfGeneration.index)
    pSystemOutput  = 0
    n1 = next(iter(m_tepes.sc*m_tepes.p*m_tepes.n))
    for g in m_tepes.g:
        if pSystemOutput < sum(m_tepes.pDemand[n1,nd] for nd in m_tepes.nd) and m_tepes.pMustRun[g] == 1:
            m_tepes.pInitialOutput[g] = m_tepes.pMaxPower[n1,g]
            m_tepes.pInitialUC    [g] = 1
            pSystemOutput           += m_tepes.pInitialOutput[g]

    # thermal and variable units ordered by increasing variable operation cost
    if len(m_tepes.tq) > 0:
        m_tepes.go = pLinearOperCost.sort_values().index.drop(list(m_tepes.gq))
    else:
        m_tepes.go = pLinearOperCost.sort_values().index

    # determine the initial committed units and their output
    for go in m_tepes.go:
        if pSystemOutput < sum(m_tepes.pDemand[n1,nd] for nd in m_tepes.nd) and m_tepes.pMustRun[go] != 1:
            if go in m_tepes.r:
                m_tepes.pInitialOutput[go] = m_tepes.pMaxPower[n1,go]
            else:
                m_tepes.pInitialOutput[go] = m_tepes.pMinPower[n1,go]
            m_tepes.pInitialUC    [go] = 1
            pSystemOutput      = pSystemOutput + m_tepes.pInitialOutput[go]

    # fixing the ESS inventory at the last load level
    for sc,p,es in m_tepes.sc*m_tepes.p*m_tepes.es:
        m_tepes.vESSInventory[sc,p,m_tepes.n.last(),es].fix(pInitialInventory[es])

    # fixing the ESS inventory at the end of the following pCycleTimeStep (weekly, yearly), i.e., for daily ESS is fixed at the end of the week, for weekly/monthly ESS is fixed at the end of the year
    for sc,p,n,es in m_tepes.sc*m_tepes.p*m_tepes.n*m_tepes.es:
         if pStorageType[es] == 'Daily'   and m_tepes.n.ord(n) % int( 168/pTimeStep) == 0:
             m_tepes.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])
         if pStorageType[es] == 'Weekly'  and m_tepes.n.ord(n) % int(8736/pTimeStep) == 0:
             m_tepes.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])
         if pStorageType[es] == 'Monthly' and m_tepes.n.ord(n) % int(8736/pTimeStep) == 0:
             m_tepes.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    for sc,p,n in m_tepes.sc*m_tepes.p*m_tepes.n:
        m_tepes.vTheta[sc,p,n,m_tepes.rf.first()].fix(0)

    SettingUpDataTime = time.time() - startt_ime
    startt_ime         = time.time()
    print('Setting up input data                 ... ', round(SettingUpDataTime), 's')
