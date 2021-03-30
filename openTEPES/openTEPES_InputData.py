""" Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)- March 30, 2021
"""

import time
import math
import os
import pandas        as pd
from   pyomo.environ import DataPortal, Set, Param, Var, Binary, NonNegativeReals, Reals, UnitInterval, Boolean, Any


def InputData(DirName, CaseName, mTEPES):
    print('Input data                  ****')
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()
    #%% reading data from CSV
    dfOption             = pd.read_csv(_path+'/oT_Data_Option_'               +CaseName+'.csv', index_col=[0    ])
    dfParameter          = pd.read_csv(_path+'/oT_Data_Parameter_'            +CaseName+'.csv', index_col=[0    ])
    dfScenario           = pd.read_csv(_path+'/oT_Data_Scenario_'             +CaseName+'.csv', index_col=[0    ])
    dfDuration           = pd.read_csv(_path+'/oT_Data_Duration_'             +CaseName+'.csv', index_col=[0    ])
    dfDemand             = pd.read_csv(_path+'/oT_Data_Demand_'               +CaseName+'.csv', index_col=[0,1,2])
    dfUpOperatingReserve = pd.read_csv(_path+'/oT_Data_OperatingReserveUp_'   +CaseName+'.csv', index_col=[0,1,2])
    dfDwOperatingReserve = pd.read_csv(_path+'/oT_Data_OperatingReserveDown_' +CaseName+'.csv', index_col=[0,1,2])
    dfGeneration         = pd.read_csv(_path+'/oT_Data_Generation_'           +CaseName+'.csv', index_col=[0    ])
    dfVariableMinPower   = pd.read_csv(_path+'/oT_Data_VariableMinGeneration_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxPower   = pd.read_csv(_path+'/oT_Data_VariableMaxGeneration_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinStorage = pd.read_csv(_path+'/oT_Data_MinimumStorage_'       +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxStorage = pd.read_csv(_path+'/oT_Data_MaximumStorage_'       +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyInflows      = pd.read_csv(_path+'/oT_Data_EnergyInflows_'        +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyOutflows     = pd.read_csv(_path+'/oT_Data_EnergyOutflows_'       +CaseName+'.csv', index_col=[0,1,2])
    dfNodeLocation       = pd.read_csv(_path+'/oT_Data_NodeLocation_'         +CaseName+'.csv', index_col=[0    ])
    dfNetwork            = pd.read_csv(_path+'/oT_Data_Network_'              +CaseName+'.csv', index_col=[0,1,2])

    # substitute NaN by 0
    dfOption.fillna            (0  , inplace=True)
    dfParameter.fillna         (0.0, inplace=True)
    dfScenario.fillna          (0.0, inplace=True)
    dfDuration.fillna          (0  , inplace=True)
    dfDemand.fillna            (0.0, inplace=True)
    dfUpOperatingReserve.fillna(0.0, inplace=True)
    dfDwOperatingReserve.fillna(0.0, inplace=True)
    dfGeneration.fillna        (0.0, inplace=True)
    dfVariableMinPower.fillna  (0.0, inplace=True)
    dfVariableMaxPower.fillna  (0.0, inplace=True)
    dfVariableMinStorage.fillna(0.0, inplace=True)
    dfVariableMaxStorage.fillna(0.0, inplace=True)
    dfEnergyInflows.fillna     (0.0, inplace=True)
    dfEnergyOutflows.fillna    (0.0, inplace=True)
    dfNodeLocation.fillna      (0.0, inplace=True)
    dfNetwork.fillna           (0.0, inplace=True)

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
    print('Energy outflows              \n', dfEnergyOutflows.describe()    )
    print('Network                      \n', dfNetwork.describe()           )

    #%% reading the sets
    dictSets = DataPortal()
    dictSets.load(filename=_path+'/oT_Dict_Scenario_'    +CaseName+'.csv', set='sc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Period_'      +CaseName+'.csv', set='p'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_LoadLevel_'   +CaseName+'.csv', set='n'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Generation_'  +CaseName+'.csv', set='g'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Technology_'  +CaseName+'.csv', set='gt'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Storage_'     +CaseName+'.csv', set='st'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Node_'        +CaseName+'.csv', set='nd'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Zone_'        +CaseName+'.csv', set='zn'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Area_'        +CaseName+'.csv', set='ar'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Region_'      +CaseName+'.csv', set='rg'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Circuit_'     +CaseName+'.csv', set='cc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Line_'        +CaseName+'.csv', set='lt'  , format='set')

    dictSets.load(filename=_path+'/oT_Dict_NodeToZone_'  +CaseName+'.csv', set='ndzn', format='set')
    dictSets.load(filename=_path+'/oT_Dict_ZoneToArea_'  +CaseName+'.csv', set='znar', format='set')
    dictSets.load(filename=_path+'/oT_Dict_AreaToRegion_'+CaseName+'.csv', set='arrg', format='set')

    mTEPES.scc  = Set(initialize=dictSets['sc'],   ordered=True,  doc='scenarios'     )
    mTEPES.pp   = Set(initialize=dictSets['p' ],   ordered=True,  doc='periods'       )
    mTEPES.p    = Set(initialize=dictSets['p' ],   ordered=True,  doc='periods'       )
    mTEPES.nn   = Set(initialize=dictSets['n' ],   ordered=True,  doc='load levels'   )
    mTEPES.gg   = Set(initialize=dictSets['g' ],   ordered=False, doc='units'         )
    mTEPES.gt   = Set(initialize=dictSets['gt'],   ordered=False, doc='technologies'  )
    mTEPES.st   = Set(initialize=dictSets['st'],   ordered=False, doc='ESS types'     )
    mTEPES.nd   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    mTEPES.ni   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    mTEPES.nf   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'         )
    mTEPES.zn   = Set(initialize=dictSets['zn'],   ordered=False, doc='zones'         )
    mTEPES.ar   = Set(initialize=dictSets['ar'],   ordered=False, doc='areas'         )
    mTEPES.rg   = Set(initialize=dictSets['rg'],   ordered=False, doc='regions'       )
    mTEPES.cc   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'      )
    mTEPES.c2   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'      )
    mTEPES.lt   = Set(initialize=dictSets['lt'],   ordered=False, doc='line types'    )

    mTEPES.ndzn = Set(initialize=dictSets['ndzn'], ordered=False, doc='node to zone'  )
    mTEPES.znar = Set(initialize=dictSets['znar'], ordered=False, doc='zone to area'  )
    mTEPES.arrg = Set(initialize=dictSets['arrg'], ordered=False, doc='area to region')

    #%% parameters
    pIndBinGenInvest     = dfOption   ['IndBinGenInvest'    ][0].astype('int')                                                            # Indicator of binary generation expansion decisions, 0 continuous - 1 binary
    pIndBinNetInvest     = dfOption   ['IndBinNetInvest'    ][0].astype('int')                                                            # Indicator of binary network    expansion decisions, 0 continuous - 1 binary
    pIndBinGenOperat     = dfOption   ['IndBinGenOperat'    ][0].astype('int')                                                            # Indicator of binary generation operation decisions, 0 continuous - 1 binary
    pIndNetLosses        = dfOption   ['IndNetLosses'       ][0].astype('int')                                                            # Indicator of network losses,                        0 lossless   - 1 ohmic losses
    pIndBinLineSwitch    = dfOption   ['IndBinLineSwitch'   ][0].astype('int')                                                            # Indicator of binary switching decisions,            0 continuous - 1 binary
    pIndBinLineOperat    = dfOption   ['IndBinLineOperat'   ][0].astype('int')                                                            # Indicator of binary line operation decisions,       0 continuous - 1 binary
    pENSCost             = dfParameter['ENSCost'            ][0] * 1e-3                                                                   # cost of energy not served           [MEUR/GWh]
    pCO2Cost             = dfParameter['CO2Cost'            ][0]                                                                          # cost of CO2 emission                [EUR/t CO2]
    pUpReserveActivation = dfParameter['UpReserveActivation'][0]                                                                          # upward   reserve activation         [p.u.]
    pDwReserveActivation = dfParameter['DwReserveActivation'][0]                                                                          # downward reserve activation         [p.u.]
    pSBase               = dfParameter['SBase'              ][0] * 1e-3                                                                   # base power                          [GW]
    pReferenceNode       = dfParameter['ReferenceNode'      ][0]                                                                          # reference node
    pTimeStep            = dfParameter['TimeStep'           ][0].astype('int')                                                            # duration of the unit time step      [h]
    pStageDuration       = dfParameter['StageDuration'      ][0].astype('int')                                                            # duration of each stage              [h]

    pScenProb            = dfScenario          ['Probability'  ]                                                                          # probabilities of scenarios          [p.u.]
    pDuration            = dfDuration          ['Duration'     ] * pTimeStep                                                              # duration of load levels             [h]
    pDemand              = dfDemand            [list(mTEPES.nd)] * 1e-3                                                                   #           demand                    [GW]
    pOperReserveUp       = dfUpOperatingReserve[list(mTEPES.ar)] * 1e-3                                                                   # upward   operating reserve          [GW]
    pOperReserveDw       = dfDwOperatingReserve[list(mTEPES.ar)] * 1e-3                                                                   # downward operating reserve          [GW]
    pVariableMinPower    = dfVariableMinPower  [list(mTEPES.gg)] * 1e-3                                                                   # dynamic variable minimum power      [GW]
    pVariableMaxPower    = dfVariableMaxPower  [list(mTEPES.gg)] * 1e-3                                                                   # dynamic variable maximum power      [GW]
    pVariableMinStorage  = dfVariableMinStorage[list(mTEPES.gg)]                                                                          # dynamic variable minimum storage    [GWh]
    pVariableMaxStorage  = dfVariableMaxStorage[list(mTEPES.gg)]                                                                          # dynamic variable maximum storage    [GWh]
    pEnergyInflows       = dfEnergyInflows     [list(mTEPES.gg)] * 1e-3                                                                   # dynamic energy inflows              [GW]
    pEnergyOutflows      = dfEnergyOutflows    [list(mTEPES.gg)] * 1e-3                                                                   # dynamic energy outflows             [GW]

    # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for operating reserve, variable max power, variable min and max storage and inflows
    if pTimeStep > 1:
        pDemand             = pDemand.rolling            (pTimeStep).mean()
        pOperReserveUp      = pOperReserveUp.rolling     (pTimeStep).mean()
        pOperReserveDw      = pOperReserveDw.rolling     (pTimeStep).mean()
        pVariableMinPower   = pVariableMinPower.rolling  (pTimeStep).mean()
        pVariableMaxPower   = pVariableMaxPower.rolling  (pTimeStep).mean()
        pVariableMinStorage = pVariableMinStorage.rolling(pTimeStep).mean()
        pVariableMaxStorage = pVariableMaxStorage.rolling(pTimeStep).mean()
        pEnergyInflows      = pEnergyInflows.rolling     (pTimeStep).mean()
        pEnergyOutflows     = pEnergyOutflows.rolling    (pTimeStep).mean()

    pDemand.fillna            (0.0, inplace=True)
    pOperReserveUp.fillna     (0.0, inplace=True)
    pOperReserveDw.fillna     (0.0, inplace=True)
    pVariableMinPower.fillna  (0.0, inplace=True)
    pVariableMaxPower.fillna  (0.0, inplace=True)
    pVariableMinStorage.fillna(0.0, inplace=True)
    pVariableMaxStorage.fillna(0.0, inplace=True)
    pEnergyInflows.fillna     (0.0, inplace=True)
    pEnergyOutflows.fillna    (0.0, inplace=True)

    if pTimeStep > 1:
        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for i in range(pTimeStep-2,-1,-1):
            pDuration[range(i,len(mTEPES.nn),pTimeStep)] = 0

    #%% generation parameters
    pGenToNode          = dfGeneration  ['Node'                ]                                                                            # generator location in node
    pGenToTechnology    = dfGeneration  ['Technology'          ]                                                                            # generator association to technology
    pMustRun            = dfGeneration  ['MustRun'             ]                                                                            # must-run unit                               [Yes]
    pRatedMinPower      = dfGeneration  ['MinimumPower'        ] * 1e-3 * (1-dfGeneration['EFOR'])                                          # rated minimum power                         [GW]
    pRatedMaxPower      = dfGeneration  ['MaximumPower'        ] * 1e-3 * (1-dfGeneration['EFOR'])                                          # rated maximum power                         [GW]
    pLinearFuelCost     = dfGeneration  ['LinearTerm'          ] * 1e-3 * dfGeneration['FuelCost']                                          # fuel     term variable cost                 [MEUR/GWh]
    pLinearOMCost       = dfGeneration  ['OMVariableCost'      ] * 1e-3                                                                     # O&M      term variable cost                 [MEUR/GWh]
    pConstantVarCost    = dfGeneration  ['ConstantTerm'        ] * 1e-6 * dfGeneration['FuelCost']                                          # constant term variable cost                 [MEUR/h]
    pStartUpCost        = dfGeneration  ['StartUpCost'         ]                                                                            # startup  cost                               [MEUR]
    pShutDownCost       = dfGeneration  ['ShutDownCost'        ]                                                                            # shutdown cost                               [MEUR]
    pRampUp             = dfGeneration  ['RampUp'              ] * 1e-3                                                                     # ramp up   rate                              [GW/h]
    pRampDw             = dfGeneration  ['RampDown'            ] * 1e-3                                                                     # ramp down rate                              [GW/h]
    pCO2EmissionCost    = dfGeneration  ['CO2EmissionRate'     ] * 1e-3 * pCO2Cost                                                          # emission  cost                              [MEUR/GWh]
    pUpTime             = dfGeneration  ['UpTime'              ]                                                                            # minimum up   time                           [h]
    pDwTime             = dfGeneration  ['DownTime'            ]                                                                            # minimum down time                           [h]
    pGenFixedCost       = dfGeneration  ['FixedCost'           ] *        dfGeneration['FixedChargeRate']                                   # generation fixed cost                       [MEUR]
    pIndBinUnitInvest   = dfGeneration  ['BinaryInvestment'    ]                                                                            # binary unit investment decision             [Yes]
    pMaxCharge          = dfGeneration  ['MaximumCharge'       ] * 1e-3                                                                     # maximum ESS charge                          [GW]
    pInitialInventory   = dfGeneration  ['InitialStorage'      ]                                                                            # initial ESS storage                         [GWh]
    pRatedMinStorage    = dfGeneration  ['MinimumStorage'      ]                                                                            # minimum ESS storage                         [GWh]
    pRatedMaxStorage    = dfGeneration  ['MaximumStorage'      ]                                                                            # maximum ESS storage                         [GWh]
    pEfficiency         = dfGeneration  ['Efficiency'          ]                                                                            #         ESS efficiency                      [p.u.]
    pStorageType        = dfGeneration  ['StorageType'         ]                                                                            #         ESS storage  type
    pOutflowsType       = dfGeneration  ['OutflowsType'        ]                                                                            #         ESS outflows type
    pRMaxReactivePower  = dfGeneration  ['MaximumReactivePower'] * 1e-3                                                                     # rated maximum reactive power                [Gvar]

    pLinearOperCost     = pLinearFuelCost + pCO2EmissionCost
    pLinearVarCost      = pLinearFuelCost + pLinearOMCost

    pNodeLat            = dfNodeLocation['Latitude'            ]                                                                            # node latitude                               [º]
    pNodeLon            = dfNodeLocation['Longitude'           ]                                                                            # node longitude                              [º]

    pLineType           = dfNetwork     ['LineType'            ]                                                                            # line type
    pLineVoltage        = dfNetwork     ['Voltage'             ]                                                                            # line voltage                                [kV]
    pLineLossFactor     = dfNetwork     ['LossFactor'          ]                                                                            # loss     factor                             [p.u.]
    pLineR              = dfNetwork     ['Resistance'          ]                                                                            # resistance                                  [p.u.]
    pLineX              = dfNetwork     ['Reactance'           ].sort_index()                                                               # reactance                                   [p.u.]
    pLineBsh            = dfNetwork     ['Susceptance'         ]                                                                            # susceptance                                 [p.u.]
    pLineTAP            = dfNetwork     ['Tap'                 ]                                                                            # tap changer                                 [p.u.]
    pConverter          = dfNetwork     ['Converter'           ]                                                                            # converter station                           [Yes]
    pLineNTCFrw         = dfNetwork     ['TTC'                 ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in forward  direction [GW]
    pLineNTCBck         = dfNetwork     ['TTCBck'              ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in backward direction [GW]
    pNetFixedCost       = dfNetwork     ['FixedCost'           ] *        dfNetwork['FixedChargeRate']                                      # network    fixed cost                       [MEUR]
    pIndBinLineInvest   = dfNetwork     ['BinaryInvestment'    ]                                                                            # binary line    investment decision          [Yes]
    pIndBinSwitch       = dfNetwork     ['BinarySwitch'        ]                                                                            # binary line    switching  decision          [Yes]
    pSwitchOnTime       = dfNetwork     ['SwOnTime'            ]                                                                            # minimum on time                             [h]
    pSwitchOffTime      = dfNetwork     ['SwOnTime'            ]                                                                            # minimum off time                            [h]
    pAngMin             = dfNetwork     ['AngMin'              ] * math.pi / 180                                                            # Min phase angle difference                  [rad]
    pAngMax             = dfNetwork     ['AngMax'              ] * math.pi / 180                                                            # Max phase angle difference                  [rad]

    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    pLineNTCBck     = pLineNTCBck.where(pLineNTCBck > 0.0, other=pLineNTCFrw)
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    pLineNTCFrw     = pLineNTCFrw.where(pLineNTCFrw > 0.0, other=pLineNTCBck)

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                 ... ', round(ReadingDataTime), 's')

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the lines (la), candidate lines (lc), candidate DC lines (cd), existing DC lines (cd), lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.sc = Set(initialize=mTEPES.scc,                    ordered=True , doc='scenarios'          , filter=lambda mTEPES,scc     :  scc       in mTEPES.scc and pScenProb        [scc] >  0.0)
    mTEPES.n  = Set(initialize=mTEPES.nn,                     ordered=True , doc='load levels'        , filter=lambda mTEPES,nn      :  nn        in mTEPES.nn  and pDuration         [nn] >  0  )
    mTEPES.n2 = Set(initialize=mTEPES.nn,                     ordered=True , doc='load levels'        , filter=lambda mTEPES,nn      :  nn        in mTEPES.nn  and pDuration         [nn] >  0  )
    mTEPES.g  = Set(initialize=mTEPES.gg,                     ordered=False, doc='generating    units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and pRatedMaxPower    [gg] >  0.0)
    mTEPES.t  = Set(initialize=mTEPES.g ,                     ordered=False, doc='thermal       units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pLinearOperCost   [g ] >  0.0)
    mTEPES.r  = Set(initialize=mTEPES.g ,                     ordered=False, doc='RES           units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pLinearOperCost   [g ] == 0.0 and pRatedMaxStorage[g] == 0.0)
    mTEPES.es = Set(initialize=mTEPES.g ,                     ordered=False, doc='ESS           units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and                                   pRatedMaxStorage[g] >  0.0)
    mTEPES.gc = Set(initialize=mTEPES.g ,                     ordered=False, doc='candidate     units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pGenFixedCost     [g ] >  0.0)
    mTEPES.ec = Set(initialize=mTEPES.es,                     ordered=False, doc='candidate ESS units', filter=lambda mTEPES,es      :  es        in mTEPES.es  and pGenFixedCost     [es] >  0.0)
    mTEPES.br = Set(initialize=mTEPES.ni*mTEPES.nf,           ordered=False, doc='all branches       ', filter=lambda mTEPES,ni,nf   : (ni,nf)    in                pLineType                    )
    mTEPES.ln = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all input     lines', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in                pLineType                    )
    mTEPES.la = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all real      lines', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in                pLineX                        and pLineNTCFrw[ni,nf,cc] > 0.0 and pLineNTCBck[ni,nf,cc] > 0.0)
    mTEPES.lc = Set(initialize=mTEPES.la,                     ordered=False, doc='candidate     lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] >  0.0)
    mTEPES.cd = Set(initialize=mTEPES.la,                     ordered=False, doc='           DC lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] >  0.0 and pLineType[la] == 'DC')
    mTEPES.ed = Set(initialize=mTEPES.la,                     ordered=False, doc='           DC lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] == 0.0 and pLineType[la] == 'DC')
    mTEPES.ll = Set(initialize=mTEPES.la,                     ordered=False, doc='loss          lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pLineLossFactor   [la] >  0.0 and pIndNetLosses >   0  )
    mTEPES.rf = Set(initialize=mTEPES.nd,                     ordered=True , doc='reference node'     , filter=lambda mTEPES,nd      :  nd        in                pReferenceNode               )
    mTEPES.gq = Set(initialize=mTEPES.gg,                     ordered=False, doc='gen  reactive units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and pRMaxReactivePower[gg] >  0.0)
    mTEPES.sq = Set(initialize=mTEPES.gg,                     ordered=False, doc='syn  reactive units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and pRMaxReactivePower[gg] >  0.0 and pGenToTechnology[gg] == 'SynchronousCondenser')

    # non-RES units, they can be committed and also contribute to the operating reserves
    mTEPES.nr = mTEPES.g - mTEPES.r

    # machines able to provide reactive power
    mTEPES.tq = mTEPES.gq - mTEPES.sq

    # existing lines (le)
    mTEPES.le = mTEPES.la - mTEPES.lc

    # AC existing and candidate lines (lca and lea) and all of them (laa)
    mTEPES.lea = mTEPES.le  - mTEPES.ed
    mTEPES.lca = mTEPES.lc  - mTEPES.cd
    mTEPES.laa = mTEPES.lea | mTEPES.lca

    # # input lines
    # mTEPES.lin = Set(initialize=mTEPES.nf*mTEPES.ni*mTEPES.cc, doc='input line', filter=lambda mTEPES,nf,ni,cc: (ni,nf,cc) in mTEPES.la)
    # mTEPES.lil = Set(initialize=mTEPES.nf*mTEPES.ni*mTEPES.cc, doc='input line', filter=lambda mTEPES,nf,ni,cc: (ni,nf,cc) in mTEPES.ll)

    # replacing string values by numerical values
    idxDict = dict()
    idxDict[0] = 0
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

    mTEPES.pLineType = Set(initialize=mTEPES.la*mTEPES.lt, doc='line type', filter=lambda mTEPES,ni,nf,cc,lt: (ni,nf,cc,lt) in pLineType)

    #%% inverse index node to generator
    pNodeToGen = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pNodeToGen = pNodeToGen.loc[pNodeToGen['Generator'].isin(mTEPES.g)]

    pNode2Gen = pNodeToGen.reset_index()
    pNode2Gen['Y/N'] = 1
    pNode2Gen = pNode2Gen.set_index(['Node','Generator'])['Y/N']

    mTEPES.n2g = Set(initialize=mTEPES.nd*mTEPES.g, doc='node   to generator', filter=lambda mTEPES,nd,g: (nd,g) in pNode2Gen)

    pZone2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(mTEPES.zn*mTEPES.g), names=('zone',  'generator')), columns=['Y/N'])
    pArea2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(mTEPES.ar*mTEPES.g), names=('area',  'generator')), columns=['Y/N'])
    pRegion2Gen = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(list(mTEPES.rg*mTEPES.g), names=('region','generator')), columns=['Y/N'])

    for nd,g in mTEPES.n2g:
        for zn in mTEPES.zn:
            if (nd,zn) in mTEPES.ndzn:
                pZone2Gen.loc[zn,g] = 1
            for ar in mTEPES.ar:
                if (nd,zn) in mTEPES.ndzn and (zn,ar) in mTEPES.znar:
                    pArea2Gen.loc[ar,g] = 1
                for rg in mTEPES.rg:
                    if (nd,zn) in mTEPES.ndzn and (zn,ar) in mTEPES.znar and (zn,rg) in mTEPES.arrg:
                        pRegion2Gen.loc[rg,g] = 1

    mTEPES.z2g = Set(initialize=mTEPES.zn*mTEPES.g, doc='zone   to generator', filter=lambda mTEPES,zn,g: (zn,g) in mTEPES.zn*mTEPES.g and pZone2Gen.loc  [zn,g]['Y/N'] == 1)
    mTEPES.a2g = Set(initialize=mTEPES.ar*mTEPES.g, doc='area   to generator', filter=lambda mTEPES,ar,g: (ar,g) in mTEPES.ar*mTEPES.g and pArea2Gen.loc  [ar,g]['Y/N'] == 1)
    mTEPES.r2g = Set(initialize=mTEPES.rg*mTEPES.g, doc='region to generator', filter=lambda mTEPES,rg,g: (rg,g) in mTEPES.rg*mTEPES.g and pRegion2Gen.loc[rg,g]['Y/N'] == 1)

    #%% inverse index generator to technology
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(mTEPES.g)]

    pTechnology2Gen = pTechnologyToGen.reset_index()
    pTechnology2Gen['Y/N'] = 1
    pTechnology2Gen = pTechnology2Gen.set_index(['Technology','Generator'])['Y/N']

    mTEPES.t2g = Set(initialize=mTEPES.gt*mTEPES.g, doc='technology to generator', filter=lambda mTEPES,gt,g: (gt,g) in pTechnology2Gen)

    # minimum and maximum variable power
    pVariableMinPower   = pVariableMinPower.replace(0.0, float('nan'))
    pVariableMaxPower   = pVariableMaxPower.replace(0.0, float('nan'))
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
    pVariableMinStorage = pVariableMinStorage.replace(0.0, float('nan'))
    pVariableMaxStorage = pVariableMaxStorage.replace(0.0, float('nan'))
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
    # initial inventory must be between minimum and maximum
    # pIniInventory       = pMinStorage.where(pMinStorage > pIniInventory, other=pIniInventory)
    # pIniInventory       = pMaxStorage.where(pMaxStorage < pIniInventory, other=pIniInventory)

    # minimum up and down time converted to an integer number of time steps
    pUpTime = round(pUpTime/pTimeStep).astype('int')
    pDwTime = round(pDwTime/pTimeStep).astype('int')

    #%% definition of the time-steps leap to observe the stored energy at ESS
    pCycleTimeStep    = (pUpTime*0).astype('int')
    pOutflowsTimeStep = (pUpTime*0).astype('int')
    for es in mTEPES.es:
        if  pStorageType  [es] == 'Daily'  :
            pCycleTimeStep[es] = 1
        if  pStorageType  [es] == 'Weekly' :
            pCycleTimeStep[es] = int( 24/pTimeStep)
        if  pStorageType  [es] == 'Monthly':
            pCycleTimeStep[es] = int(168/pTimeStep)

        if  pOutflowsType    [es] == 'Hourly' :
            pOutflowsTimeStep[es] =    1
        if  pOutflowsType    [es] == 'Daily'  :
            pOutflowsTimeStep[es] =   24/pTimeStep
        if  pOutflowsType    [es] == 'Weekly' :
            pOutflowsTimeStep[es] =  168/pTimeStep
        if  pOutflowsType    [es] == 'Monthly':
            pOutflowsTimeStep[es] =  672/pTimeStep
        if  pOutflowsType    [es] == 'Yearly' :
            pOutflowsTimeStep[es] = 8736/pTimeStep

        pCycleTimeStep[es] = min(pCycleTimeStep[es], pOutflowsTimeStep[es])

    # the stage duration is the maximum between the defined stage duration and the storage type and the outflows type for any ESS to avoid breaking the energy outflows constraints
    pStageDuration = max(pStageDuration, pCycleTimeStep.max(), pOutflowsTimeStep.max())

    # pStorageType = pStorageType[pStorageType.index.isin(mTEPES.es)]
    # mTEPES.pStorageType = Param(mTEPES.es, initialize=pStorageType.to_dict(),   within=Any, doc='ESS storage type')
    # pOutflowsType = pOutflowsType[pOutflowsType.index.isin(mTEPES.es)]
    # mTEPES.pOutflowsType = Param(mTEPES.es, initialize=pOutflowsType.to_dict(), within=Any, doc='ESS outflows type')

    # drop load levels with duration 0
    pDuration         = pDuration.loc        [list(                   mTEPES.n          )]
    pDemand           = pDemand.loc          [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pOperReserveUp    = pOperReserveUp.loc   [list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar)]
    pOperReserveDw    = pOperReserveDw.loc   [list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar)]
    pMinPower         = pMinPower.loc        [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pMaxPower         = pMaxPower.loc        [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pMaxPower2ndBlock = pMaxPower2ndBlock.loc[list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pEnergyInflows    = pEnergyInflows.loc   [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pEnergyOutflows   = pEnergyOutflows.loc  [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pMinStorage       = pMinStorage.loc      [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pMaxStorage       = pMaxStorage.loc      [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]
    pIniInventory     = pIniInventory.loc    [list(mTEPES.sc*mTEPES.p*mTEPES.n          )]

    # values < 1e-5 times the maximum system demand are converted to 0
    # these parameters are in GW
    pEpsilon = pDemand.max().sum()*1e-5
    pDemand          [pDemand           < pEpsilon] = 0.0
    pOperReserveUp   [pOperReserveUp    < pEpsilon] = 0.0
    pOperReserveDw   [pOperReserveDw    < pEpsilon] = 0.0
    pMinPower        [pMinPower         < pEpsilon] = 0.0
    pMaxPower        [pMaxPower         < pEpsilon] = 0.0
    pMaxPower2ndBlock[pMaxPower2ndBlock < pEpsilon] = 0.0
    pMaxCharge       [pMaxCharge        < pEpsilon] = 0.0
    pEnergyInflows   [pEnergyInflows    < pEpsilon/pTimeStep] = 0.0
    pEnergyOutflows  [pEnergyOutflows   < pEpsilon/pTimeStep] = 0.0
    pLineNTCFrw      [pLineNTCFrw       < pEpsilon] = 0.0
    pLineNTCBck      [pLineNTCBck       < pEpsilon] = 0.0

    # these parameters are in GWh
    pMinStorage      [pMinStorage       < pEpsilon] = 0.0
    pMaxStorage      [pMaxStorage       < pEpsilon] = 0.0
    pIniInventory    [pIniInventory     < pEpsilon] = 0.0
    pInitialInventory[pInitialInventory < pEpsilon] = 0.0

    # BigM maximum flow to be used in the Kirchhoff's 2nd law disjunctive constraint
    pBigMFlowBck = pLineNTCBck*0.0
    pBigMFlowFrw = pLineNTCFrw*0.0
    for lea in mTEPES.lea:
        pBigMFlowBck.loc[lea] = pLineNTCBck[lea]
        pBigMFlowFrw.loc[lea] = pLineNTCFrw[lea]
    for lca in mTEPES.lca:
        pBigMFlowBck.loc[lca] = pLineNTCBck[lca]*1.5
        pBigMFlowFrw.loc[lca] = pLineNTCFrw[lca]*1.5

    # maximum voltage angle
    pMaxTheta = pDemand*0.0 + math.pi/2
    pMaxTheta = pMaxTheta.loc[list(mTEPES.sc*mTEPES.p*mTEPES.n)]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    mTEPES.pIndBinGenInvest      = Param(initialize=pIndBinGenInvest    , within=Boolean, mutable=True)
    mTEPES.pIndBinNetInvest      = Param(initialize=pIndBinNetInvest    , within=Boolean, mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=pIndBinGenOperat    , within=Boolean, mutable=True)
    mTEPES.pIndNetLosses         = Param(initialize=pIndNetLosses       , within=Boolean, mutable=True)
    mTEPES.pIndBinLineSwitch     = Param(initialize=pIndBinLineSwitch   , within=Boolean, mutable=True)
    mTEPES.pIndBinLineOperat     = Param(initialize=pIndBinLineOperat   , within=Boolean, mutable=True)

    mTEPES.pENSCost              = Param(initialize=pENSCost            , within=NonNegativeReals)
    mTEPES.pCO2Cost              = Param(initialize=pCO2Cost            , within=NonNegativeReals)
    mTEPES.pUpReserveActivation  = Param(initialize=pUpReserveActivation, within=NonNegativeReals)
    mTEPES.pDwReserveActivation  = Param(initialize=pDwReserveActivation, within=NonNegativeReals)
    mTEPES.pSBase                = Param(initialize=pSBase              , within=NonNegativeReals)
    mTEPES.pTimeStep             = Param(initialize=pTimeStep           , within=NonNegativeReals)
    mTEPES.pStageDuration        = Param(initialize=pStageDuration      , within=NonNegativeReals)

    mTEPES.pDemand               = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pDemand.stack().to_dict()          , within=NonNegativeReals, doc='Demand'                       )
    mTEPES.pScenProb             = Param(mTEPES.scc,                               initialize=pScenProb.to_dict()                , within=NonNegativeReals, doc='Probability'                  )
    mTEPES.pDuration             = Param(                     mTEPES.n,            initialize=pDuration.to_dict()                , within=NonNegativeReals, doc='Duration'                     )
    mTEPES.pNodeLon              = Param(                               mTEPES.nd, initialize=pNodeLon.to_dict()                 ,                          doc='Longitude'                    )
    mTEPES.pNodeLat              = Param(                               mTEPES.nd, initialize=pNodeLat.to_dict()                 ,                          doc='Latitude'                     )
    mTEPES.pOperReserveUp        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, initialize=pOperReserveUp.stack().to_dict()   , within=NonNegativeReals, doc='Upward   operating reserve'   )
    mTEPES.pOperReserveDw        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, initialize=pOperReserveDw.stack().to_dict()   , within=NonNegativeReals, doc='Downward operating reserve'   )
    mTEPES.pMinPower             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMinPower.stack().to_dict()        , within=NonNegativeReals, doc='Minimum power'                )
    mTEPES.pMaxPower             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxPower.stack().to_dict()        , within=NonNegativeReals, doc='Maximum power'                )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxPower2ndBlock.stack().to_dict(), within=NonNegativeReals, doc='Second block'                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pEnergyInflows.stack().to_dict()   , within=NonNegativeReals, doc='Energy inflows'               )
    mTEPES.pEnergyOutflows       = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pEnergyOutflows.stack().to_dict()  , within=NonNegativeReals, doc='Energy outflows'              )
    mTEPES.pMinStorage           = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMinStorage.stack().to_dict()      , within=NonNegativeReals, doc='ESS Minimum stoarage capacity')
    mTEPES.pMaxStorage           = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxStorage.stack().to_dict()      , within=NonNegativeReals, doc='ESS Maximum stoarage capacity')

    mTEPES.pRatedMaxPower        = Param(                               mTEPES.gg, initialize=pRatedMaxPower.to_dict()           , within=NonNegativeReals, doc='Rated maximum power'          )
    mTEPES.pLinearVarCost        = Param(                               mTEPES.gg, initialize=pLinearVarCost.to_dict()           , within=NonNegativeReals, doc='Linear   variable cost'       )
    mTEPES.pLinearOMCost         = Param(                               mTEPES.gg, initialize=pLinearOMCost.to_dict()            , within=NonNegativeReals, doc='Linear   O&M      cost'       )
    mTEPES.pConstantVarCost      = Param(                               mTEPES.gg, initialize=pConstantVarCost.to_dict()         , within=NonNegativeReals, doc='Constant variable cost'       )
    mTEPES.pCO2EmissionCost      = Param(                               mTEPES.gg, initialize=pCO2EmissionCost.to_dict()         , within=NonNegativeReals, doc='CO2 Emission      cost'       )
    mTEPES.pStartUpCost          = Param(                               mTEPES.gg, initialize=pStartUpCost.to_dict()             , within=NonNegativeReals, doc='Startup  cost'                )
    mTEPES.pShutDownCost         = Param(                               mTEPES.gg, initialize=pShutDownCost.to_dict()            , within=NonNegativeReals, doc='Shutdown cost'                )
    mTEPES.pRampUp               = Param(                               mTEPES.gg, initialize=pRampUp.to_dict()                  , within=NonNegativeReals, doc='Ramp up   rate'               )
    mTEPES.pRampDw               = Param(                               mTEPES.gg, initialize=pRampDw.to_dict()                  , within=NonNegativeReals, doc='Ramp down rate'               )
    mTEPES.pUpTime               = Param(                               mTEPES.gg, initialize=pUpTime.to_dict()                  , within=NonNegativeReals, doc='Up   time'                    )
    mTEPES.pDwTime               = Param(                               mTEPES.gg, initialize=pDwTime.to_dict()                  , within=NonNegativeReals, doc='Down time'                    )
    mTEPES.pMaxCharge            = Param(                               mTEPES.gg, initialize=pMaxCharge.to_dict()               , within=NonNegativeReals, doc='Maximum charge power'         )
    mTEPES.pGenFixedCost         = Param(                               mTEPES.gg, initialize=pGenFixedCost.to_dict()            , within=NonNegativeReals, doc='Generation fixed cost'        )
    mTEPES.pIndBinUnitInvest     = Param(                               mTEPES.gg, initialize=pIndBinUnitInvest.to_dict()        , within=NonNegativeReals, doc='Binary investment decision'   )
    mTEPES.pEfficiency           = Param(                               mTEPES.gg, initialize=pEfficiency.to_dict()              , within=NonNegativeReals, doc='Round-trip efficiency'        )
    mTEPES.pCycleTimeStep        = Param(                               mTEPES.gg, initialize=pCycleTimeStep.to_dict()           , within=NonNegativeReals, doc='ESS Storage cycle'            )
    mTEPES.pOutflowsTimeStep     = Param(                               mTEPES.gg, initialize=pOutflowsTimeStep.to_dict()        , within=NonNegativeReals, doc='ESS Outflows cycle'           )
    mTEPES.pIniInventory         = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pIniInventory.stack().to_dict()    , within=NonNegativeReals, doc='ESS Initial storage',         mutable=True)

    mTEPES.pLineLossFactor       = Param(                               mTEPES.ln, initialize=pLineLossFactor.to_dict()          , within=NonNegativeReals, doc='Loss factor'                  )
    mTEPES.pLineR                = Param(                               mTEPES.ln, initialize=pLineR.to_dict()                   , within=NonNegativeReals, doc='Resistance'                   )
    mTEPES.pLineX                = Param(                               mTEPES.ln, initialize=pLineX.to_dict()                   , within=NonNegativeReals, doc='Reactance'                    )
    mTEPES.pLineBsh              = Param(                               mTEPES.ln, initialize=pLineBsh.to_dict()                 , within=NonNegativeReals, doc='Susceptance',                 mutable=True)
    mTEPES.pLineTAP              = Param(                               mTEPES.ln, initialize=pLineTAP.to_dict()                 , within=NonNegativeReals, doc='Tap changer',                 mutable=True)
    mTEPES.pConverter            = Param(                               mTEPES.ln, initialize=pConverter.to_dict()               , within=NonNegativeReals, doc='Converter'                    )
    mTEPES.pLineVoltage          = Param(                               mTEPES.ln, initialize=pLineVoltage.to_dict()             , within=NonNegativeReals, doc='Voltage'                      )
    mTEPES.pLineNTCFrw           = Param(                               mTEPES.ln, initialize=pLineNTCFrw.to_dict()              , within=NonNegativeReals, doc='NTC forward'                  )
    mTEPES.pLineNTCBck           = Param(                               mTEPES.ln, initialize=pLineNTCBck.to_dict()              , within=NonNegativeReals, doc='NTC backward'                 )
    mTEPES.pNetFixedCost         = Param(                               mTEPES.ln, initialize=pNetFixedCost.to_dict()            , within=NonNegativeReals, doc='Network fixed cost'           )
    mTEPES.pIndBinLineInvest     = Param(                               mTEPES.ln, initialize=pIndBinLineInvest.to_dict()        , within=NonNegativeReals, doc='Binary investment decision'   )
    mTEPES.pSwOnTime             = Param(                               mTEPES.ln, initialize=pSwitchOnTime.to_dict()            , within=NonNegativeReals, doc='Minimum Switch On Time'       )
    mTEPES.pSwOffTime            = Param(                               mTEPES.ln, initialize=pSwitchOffTime.to_dict()           , within=NonNegativeReals, doc='Minimum Switch Off Time'      )
    mTEPES.pIndBinSwitch         = Param(                               mTEPES.ln, initialize=pIndBinSwitch.to_dict()            , within=NonNegativeReals, doc='Switch decision'              )
    mTEPES.pBigMFlowBck          = Param(                               mTEPES.ln, initialize=pBigMFlowBck.to_dict()             , within=NonNegativeReals, doc='Maximum backward capacity',   mutable=True)
    mTEPES.pBigMFlowFrw          = Param(                               mTEPES.ln, initialize=pBigMFlowFrw.to_dict()             , within=NonNegativeReals, doc='Maximum forward  capacity',   mutable=True)
    mTEPES.pMaxTheta             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pMaxTheta.stack().to_dict()        , within=NonNegativeReals, doc='Maximum voltage angle',       mutable=True)
    mTEPES.pAngMin               = Param(                               mTEPES.ln, initialize=pAngMin.to_dict()                  , within=Reals,            doc='Minimum phase angle diff',    mutable=True)
    mTEPES.pAngMax               = Param(                               mTEPES.ln, initialize=pAngMax.to_dict()                  , within=Reals,            doc='Maximum phase angle diff',    mutable=True)

    #%% variables
    mTEPES.vTotalFCost           = Var(                                          within=NonNegativeReals,                                                                                                doc='total system fixed                   cost      [MEUR]')
    mTEPES.vTotalGCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                doc='total variable generation  operation cost      [MEUR]')
    mTEPES.vTotalCCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                doc='total variable consumption operation cost      [MEUR]')
    mTEPES.vTotalECost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                doc='total system emission                cost      [MEUR]')
    mTEPES.vTotalRCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                doc='total system reliability             cost      [MEUR]')
    mTEPES.vTotalOutput          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.g , within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,g : (0.0,mTEPES.pMaxPower        [sc,p,n,g ]),                     doc='total output of the unit                         [GW]')
    mTEPES.vOutput2ndBlock       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock[sc,p,n,nr]),                     doc='second block of the unit                         [GW]')
    mTEPES.vReserveUp            = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock[sc,p,n,nr]),                     doc='upward   operating reserve                       [GW]')
    mTEPES.vReserveDown          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock[sc,p,n,nr]),                     doc='downward operating reserve                       [GW]')
    mTEPES.vEnergyOutflows       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.g , within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,g : (0.0,mTEPES.pMaxPower        [sc,p,n,g ]),                     doc='total outflows of the unit                       [GW]')
    mTEPES.vESSInventory         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,es: (mTEPES.pMinStorage[sc,p,n,es],mTEPES.pMaxStorage[sc,p,n,es]), doc='ESS inventory                                   [GWh]')
    mTEPES.vESSSpillage          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals,                                                                                                doc='ESS spillage                                    [GWh]')
    mTEPES.vESSTotalCharge       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,es: (0.0,mTEPES.pMaxCharge       [es]       ),                     doc='ESS total charge power                           [GW]')
    mTEPES.vESSCharge            = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,es: (0.0,mTEPES.pMaxCharge       [es]       ),                     doc='ESS charge power                                 [GW]')
    mTEPES.vESSReserveUp         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,es: (0.0,mTEPES.pMaxCharge       [es]       ),                     doc='ESS upward   operating reserve                   [GW]')
    mTEPES.vESSReserveDown       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,es: (0.0,mTEPES.pMaxCharge       [es]       ),                     doc='ESS downward operating reserve                   [GW]')
    mTEPES.vENS                  = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,nd: (0.0,mTEPES.pDemand          [sc,p,n,nd]),                     doc='energy not served in node                        [GW]')

    if mTEPES.pIndBinGenOperat == 0:
        mTEPES.vCommitment       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,                                                                                                    doc='commitment of the unit                          [0,1]')
        mTEPES.vStartUp          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,                                                                                                    doc='startup    of the unit                          [0,1]')
        mTEPES.vShutDown         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,                                                                                                    doc='shutdown   of the unit                          [0,1]')
    else:
        mTEPES.vCommitment       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,                                                                                                          doc='commitment of the unit                          {0,1}')
        mTEPES.vStartUp          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,                                                                                                          doc='startup    of the unit                          {0,1}')
        mTEPES.vShutDown         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,                                                                                                          doc='shutdown   of the unit                          {0,1}')

    if mTEPES.pIndBinGenInvest == 0:
        mTEPES.vGenerationInvest = Var(                               mTEPES.gc, within=UnitInterval,                                                                                                    doc='generation investment decision exists in a year [0,1]')
    else:
        mTEPES.vGenerationInvest = Var(                               mTEPES.gc, within=Binary,                                                                                                          doc='generation investment decision exists in a year {0,1}')

    if mTEPES.pIndBinNetInvest == 0:
        mTEPES.vNetworkInvest    = Var(                               mTEPES.lc, within=UnitInterval,                                                                                                    doc='network    investment decision exists in a year [0,1]')
    else:
        mTEPES.vNetworkInvest    = Var(                               mTEPES.lc, within=Binary,                                                                                                          doc='network    investment decision exists in a year {0,1}')

    if mTEPES.pIndBinLineSwitch == 0:
        mTEPES.vLineSwitch       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,                                                                                                    doc='line switching decision exists in a year [0,1]'       )
        mTEPES.vLineOnState      = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,                                                                                                    doc='on state    of the line                         [0,1]')
        mTEPES.vLineOffState     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,                                                                                                    doc='off state   of the line                         [0,1]')
    else:
        mTEPES.vLineSwitch       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,                                                                                                          doc='line switching decision exists in a year {0,1}'       )
        mTEPES.vLineOnState      = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,                                                                                                          doc='on state    of the line                         {0,1}')
        mTEPES.vLineOffState     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,                                                                                                          doc='off state   of the line                         {0,1}')

    if mTEPES.pIndBinLineOperat == 0:
        mTEPES.vLineOperat       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,                                                                                                    doc='line state decision  [0,1]'                           )
    else:
        mTEPES.vLineOperat       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,                                                                                                          doc='line state decision  {0,1}'                           )

    # relax binary condition in generation and network investment decisions
    for gc in mTEPES.gc:
        if mTEPES.pIndBinGenInvest != 0 and pIndBinUnitInvest[gc] == 0:
            mTEPES.vGenerationInvest[gc].domain = UnitInterval
    for lc in mTEPES.lc:
        if mTEPES.pIndBinNetInvest != 0 and pIndBinLineInvest[lc] == 0:
            mTEPES.vNetworkInvest   [lc].domain = UnitInterval
    for sc,p,n,ni,nf,cc in list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la):
        if pIndBinSwitch[ni,nf,cc] == 0:
            mTEPES.vLineSwitch      [sc,p,n,ni,nf,cc].fix(1.0)


    mTEPES.vLineLosses           = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, within=NonNegativeReals, bounds=lambda mTEPES,sc,p,n,*ll: (0.0,0.5*mTEPES.pLineLossFactor[ll]*max(mTEPES.pLineNTCBck[ll],mTEPES.pLineNTCFrw[ll])), doc='half line losses                                 [GW]')
    mTEPES.vFlow                 = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Reals,            bounds=lambda mTEPES,sc,p,n,*la: (-mTEPES.pLineNTCBck[la],mTEPES.pLineNTCFrw[la]),                                        doc='flow                                             [GW]')
    mTEPES.vTheta                = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, within=Reals,            bounds=lambda mTEPES,sc,p,n, nd: (-mTEPES.pMaxTheta[sc,p,n,nd],mTEPES.pMaxTheta[sc,p,n,nd]),                              doc='voltage angle                                   [rad]')

    # fix the must-run units and their output
    mTEPES.pInitialSwitch        = pd.Series([0.0]*len(mTEPES.la), index=list(mTEPES.la))
    for la in mTEPES.la:
        if la in mTEPES.lc:
            mTEPES.pInitialSwitch[la] = 0
        else:
            mTEPES.pInitialSwitch[la] = 1

    pMustRun = pMustRun.map(idxDict)

    mTEPES.pMustRun = Param(mTEPES.gg, within=Any, initialize=pMustRun.to_dict())

    for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g :
        # must run units must produce at least their minimum output
        if mTEPES.pMustRun[g] == 1:
            mTEPES.vTotalOutput[sc,p,n,g].setlb(mTEPES.pMinPower[sc,p,n,g])
        # if no max power, no total output
        if mTEPES.pMaxPower[sc,p,n,g] == 0.0:
            mTEPES.vTotalOutput[sc,p,n,g].fix(0.0)
    #for sc,p,n,r  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r :
    #    if mTEPES.pMinPower[sc,p,n,r] == mTEPES.pMaxPower[sc,p,n,r] and mTEPES.pLinearOMCost[r] == 0.0:
    #        mTEPES.vTotalOutput[sc,p,n,r].fix(mTEPES.pMaxPower[sc,p,n,r])

    for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr:
        # must run units or units with no minimum power are always committed and must produce at least their minimum output
        if mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPower[sc,p,n,nr] == 0.0 and mTEPES.pConstantVarCost[nr] == 0.0):
            mTEPES.vCommitment[sc,p,n,nr].fix(1)
            mTEPES.vStartUp   [sc,p,n,nr].fix(0)
            mTEPES.vShutDown  [sc,p,n,nr].fix(0)
        # if min and max power coincide there are neither second block, nor operating reserve
        if mTEPES.pMaxPower2ndBlock[sc,p,n,nr] ==  0.0:
            mTEPES.vOutput2ndBlock [sc,p,n,nr].fix(0.0)
            mTEPES.vReserveUp      [sc,p,n,nr].fix(0.0)
            mTEPES.vReserveDown    [sc,p,n,nr].fix(0.0)

    for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es:
        # ESS with no charge capacity or not storage capacity can't charge
        if mTEPES.pMaxCharge[es] == 0.0 or mTEPES.pMaxStorage[sc,p,n,es] == 0.0:
            mTEPES.vESSTotalCharge[sc,p,n,es].fix(0.0)
            mTEPES.vESSCharge     [sc,p,n,es].fix(0.0)
            mTEPES.vESSReserveUp  [sc,p,n,es].fix(0.0)
            mTEPES.vESSReserveDown[sc,p,n,es].fix(0.0)

    # if no operating reserve is required no variables are needed
    for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            if mTEPES.pOperReserveUp  [sc,p,n,ar] ==  0.0:
                mTEPES.vReserveUp     [sc,p,n,nr].fix(0.0)
            if mTEPES.pOperReserveDw  [sc,p,n,ar] ==  0.0:
                mTEPES.vReserveDown   [sc,p,n,nr].fix(0.0)
    for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            if mTEPES.pOperReserveUp  [sc,p,n,ar] ==  0.0:
                mTEPES.vESSReserveUp  [sc,p,n,es].fix(0.0)
            if mTEPES.pOperReserveDw  [sc,p,n,ar] ==  0.0:
                mTEPES.vESSReserveDown[sc,p,n,es].fix(0.0)

    # fix the must-run units and their output
    mTEPES.pInitialOutput = pd.Series([0.0]*len(mTEPES.nr), index=list(mTEPES.nr))
    mTEPES.pInitialUC     = pd.Series([0.0]*len(mTEPES.nr), index=list(mTEPES.nr))
    pSystemOutput  = 0.0
    n1 = next(iter(mTEPES.sc*mTEPES.p*mTEPES.n))
    for nr in mTEPES.nr:
        if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[nr] == 1:
            mTEPES.pInitialOutput[nr] = mTEPES.pMaxPower[n1,nr]
            mTEPES.pInitialUC    [nr] = 1
            pSystemOutput            += mTEPES.pInitialOutput[nr]

    # thermal and variable units ordered by increasing variable operation cost
    if len(mTEPES.tq) > 0:
        mTEPES.go = pLinearOperCost.sort_values().index.drop(list(mTEPES.gq))
    else:
        mTEPES.go = pLinearOperCost.sort_values().index

    # determine the initial committed units and their output
    for go in mTEPES.go:
        if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[go] != 1:
            if go in mTEPES.r:
                mTEPES.pInitialOutput[go] = mTEPES.pMaxPower[n1,go]
            else:
                mTEPES.pInitialOutput[go] = mTEPES.pMinPower[n1,go]
            mTEPES.pInitialUC    [go] = 1
            pSystemOutput      = pSystemOutput + mTEPES.pInitialOutput[go]

    # fixing the ESS inventory at the last load level
    for sc,p,es in mTEPES.sc*mTEPES.p*mTEPES.es:
        mTEPES.vESSInventory[sc,p,mTEPES.n.last(),es].fix(pInitialInventory[es])

    # fixing the ESS inventory at the end of the following pCycleTimeStep (daily, weekly, monthly), i.e., for daily ESS is fixed at the end of the week, for weekly/monthly ESS is fixed at the end of the year
    for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es:
         if pStorageType[es] == 'Daily'   and mTEPES.n.ord(n) % int( 168/pTimeStep) == 0:
             mTEPES.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])
         if pStorageType[es] == 'Weekly'  and mTEPES.n.ord(n) % int(8736/pTimeStep) == 0:
             mTEPES.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])
         if pStorageType[es] == 'Monthly' and mTEPES.n.ord(n) % int(8736/pTimeStep) == 0:
             mTEPES.vESSInventory[sc,p,n,es].fix(pInitialInventory[es])

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n:
        mTEPES.vTheta[sc,p,n,mTEPES.rf.first()].fix(0.0)

    # fixing the ENS in nodes with no demand
    for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd:
        if mTEPES.pDemand[sc,p,n,nd] ==  0.0:
            mTEPES.vENS  [sc,p,n,nd].fix(0.0)

    SettingUpDataTime = time.time() - StartTime
    StartTime         = time.time()
    print('Setting up input data                 ... ', round(SettingUpDataTime), 's')
