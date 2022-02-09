"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - February 09, 2022
"""

import time
import math
import os
import pandas        as pd
from   pyomo.environ import DataPortal, Set, Param, Var, Binary, NonNegativeReals, Reals, UnitInterval, Boolean, Any


def InputData(DirName, CaseName, mTEPES, pIndLogConsole):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% reading data from CSV
    dfOption             = pd.read_csv(_path+'/oT_Data_Option_'                +CaseName+'.csv', index_col=[0    ])
    dfParameter          = pd.read_csv(_path+'/oT_Data_Parameter_'             +CaseName+'.csv', index_col=[0    ])
    dfScenario           = pd.read_csv(_path+'/oT_Data_Scenario_'              +CaseName+'.csv', index_col=[0    ])
    dfStage              = pd.read_csv(_path+'/oT_Data_Stage_'                 +CaseName+'.csv', index_col=[0    ])
    dfDuration           = pd.read_csv(_path+'/oT_Data_Duration_'              +CaseName+'.csv', index_col=[0    ])
    dfReserveMargin      = pd.read_csv(_path+'/oT_Data_ReserveMargin_'         +CaseName+'.csv', index_col=[0    ])
    dfDemand             = pd.read_csv(_path+'/oT_Data_Demand_'                +CaseName+'.csv', index_col=[0,1,2])
    dfInertia            = pd.read_csv(_path+'/oT_Data_Inertia_'               +CaseName+'.csv', index_col=[0,1,2])
    dfUpOperatingReserve = pd.read_csv(_path+'/oT_Data_OperatingReserveUp_'    +CaseName+'.csv', index_col=[0,1,2])
    dfDwOperatingReserve = pd.read_csv(_path+'/oT_Data_OperatingReserveDown_'  +CaseName+'.csv', index_col=[0,1,2])
    dfGeneration         = pd.read_csv(_path+'/oT_Data_Generation_'            +CaseName+'.csv', index_col=[0    ])
    dfVariableMinPower   = pd.read_csv(_path+'/oT_Data_VariableMinGeneration_' +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxPower   = pd.read_csv(_path+'/oT_Data_VariableMaxGeneration_' +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinCharge  = pd.read_csv(_path+'/oT_Data_VariableMinConsumption_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxCharge  = pd.read_csv(_path+'/oT_Data_VariableMaxConsumption_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinStorage = pd.read_csv(_path+'/oT_Data_VariableMinStorage_'    +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxStorage = pd.read_csv(_path+'/oT_Data_VariableMaxStorage_'    +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyInflows      = pd.read_csv(_path+'/oT_Data_EnergyInflows_'         +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyOutflows     = pd.read_csv(_path+'/oT_Data_EnergyOutflows_'        +CaseName+'.csv', index_col=[0,1,2])
    dfNodeLocation       = pd.read_csv(_path+'/oT_Data_NodeLocation_'          +CaseName+'.csv', index_col=[0    ])
    dfNetwork            = pd.read_csv(_path+'/oT_Data_Network_'               +CaseName+'.csv', index_col=[0,1,2])

    # substitute NaN by 0
    dfOption.fillna            (0  , inplace=True)
    dfParameter.fillna         (0.0, inplace=True)
    dfScenario.fillna          (0.0, inplace=True)
    dfStage.fillna             (0.0, inplace=True)
    dfDuration.fillna          (0  , inplace=True)
    dfReserveMargin.fillna     (0.0, inplace=True)
    dfDemand.fillna            (0.0, inplace=True)
    dfInertia.fillna           (0.0, inplace=True)
    dfUpOperatingReserve.fillna(0.0, inplace=True)
    dfDwOperatingReserve.fillna(0.0, inplace=True)
    dfGeneration.fillna        (0.0, inplace=True)
    dfVariableMinPower.fillna  (0.0, inplace=True)
    dfVariableMaxPower.fillna  (0.0, inplace=True)
    dfVariableMinCharge.fillna (0.0, inplace=True)
    dfVariableMaxCharge.fillna (0.0, inplace=True)
    dfVariableMinStorage.fillna(0.0, inplace=True)
    dfVariableMaxStorage.fillna(0.0, inplace=True)
    dfEnergyInflows.fillna     (0.0, inplace=True)
    dfEnergyOutflows.fillna    (0.0, inplace=True)
    dfNodeLocation.fillna      (0.0, inplace=True)
    dfNetwork.fillna           (0.0, inplace=True)

    # show some statistics of the data
    if pIndLogConsole == 1:
        print('Reserve margin               \n', dfReserveMargin.describe     ())
        print('Demand                       \n', dfDemand.describe            ())
        print('Inertia                      \n', dfInertia.describe           ())
        print('Upward   operating reserves  \n', dfUpOperatingReserve.describe())
        print('Downward operating reserves  \n', dfDwOperatingReserve.describe())
        print('Generation                   \n', dfGeneration.describe        ())
        print('Variable minimum generation  \n', dfVariableMinPower.describe  ())
        print('Variable maximum generation  \n', dfVariableMaxPower.describe  ())
        print('Variable minimum consumption \n', dfVariableMinCharge.describe ())
        print('Variable maximum consumption \n', dfVariableMaxCharge.describe ())
        print('Variable minimum storage     \n', dfVariableMinStorage.describe())
        print('Variable maximum storage     \n', dfVariableMaxStorage.describe())
        print('Energy inflows               \n', dfEnergyInflows.describe     ())
        print('Energy outflows              \n', dfEnergyOutflows.describe    ())
        print('Network                      \n', dfNetwork.describe           ())

    #%% reading the sets
    dictSets = DataPortal()
    dictSets.load(filename=_path+'/oT_Dict_Scenario_'      +CaseName+'.csv', set='sc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Period_'        +CaseName+'.csv', set='p'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Stage_'         +CaseName+'.csv', set='st'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_LoadLevel_'     +CaseName+'.csv', set='n'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Generation_'    +CaseName+'.csv', set='g'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Technology_'    +CaseName+'.csv', set='gt'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Storage_'       +CaseName+'.csv', set='et'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Node_'          +CaseName+'.csv', set='nd'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Zone_'          +CaseName+'.csv', set='zn'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Area_'          +CaseName+'.csv', set='ar'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Region_'        +CaseName+'.csv', set='rg'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Circuit_'       +CaseName+'.csv', set='cc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Line_'          +CaseName+'.csv', set='lt'  , format='set')

    dictSets.load(filename=_path+'/oT_Dict_NodeToZone_'    +CaseName+'.csv', set='ndzn', format='set')
    dictSets.load(filename=_path+'/oT_Dict_ZoneToArea_'    +CaseName+'.csv', set='znar', format='set')
    dictSets.load(filename=_path+'/oT_Dict_AreaToRegion_'  +CaseName+'.csv', set='arrg', format='set')

    mTEPES.scc  = Set(initialize=dictSets['sc'],   ordered=True,  doc='scenarios'       )
    mTEPES.pp   = Set(initialize=dictSets['p' ],   ordered=True,  doc='periods'         )
    mTEPES.p    = Set(initialize=dictSets['p' ],   ordered=True,  doc='periods'         )
    mTEPES.stt  = Set(initialize=dictSets['st'],   ordered=True,  doc='stages'          )
    mTEPES.nn   = Set(initialize=dictSets['n' ],   ordered=True,  doc='load levels'     )
    mTEPES.gg   = Set(initialize=dictSets['g' ],   ordered=False, doc='units'           )
    mTEPES.gt   = Set(initialize=dictSets['gt'],   ordered=False, doc='technologies'    )
    mTEPES.et   = Set(initialize=dictSets['et'],   ordered=False, doc='ESS types'       )
    mTEPES.nd   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'           )
    mTEPES.ni   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'           )
    mTEPES.nf   = Set(initialize=dictSets['nd'],   ordered=False, doc='nodes'           )
    mTEPES.zn   = Set(initialize=dictSets['zn'],   ordered=False, doc='zones'           )
    mTEPES.ar   = Set(initialize=dictSets['ar'],   ordered=False, doc='areas'           )
    mTEPES.rg   = Set(initialize=dictSets['rg'],   ordered=False, doc='regions'         )
    mTEPES.cc   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'        )
    mTEPES.c2   = Set(initialize=dictSets['cc'],   ordered=False, doc='circuits'        )
    mTEPES.lt   = Set(initialize=dictSets['lt'],   ordered=False, doc='line types'      )

    mTEPES.ndzn = Set(initialize=dictSets['ndzn'], ordered=False, doc='node to zone'    )
    mTEPES.znar = Set(initialize=dictSets['znar'], ordered=False, doc='zone to area'    )
    mTEPES.arrg = Set(initialize=dictSets['arrg'], ordered=False, doc='area to region'  )

    #%% parameters
    pIndBinGenInvest     = dfOption   ['IndBinGenInvest'    ][0].astype('int')                                                            # Indicator of binary generation expansion decisions, 0 continuous - 1 binary
    pIndBinNetInvest     = dfOption   ['IndBinNetInvest'    ][0].astype('int')                                                            # Indicator of binary network    expansion decisions, 0 continuous - 1 binary
    pIndBinGenRetire     = dfOption   ['IndBinGenRetirement'][0].astype('int')                                                            # Indicator of binary generation retirement decisions,0 continuous - 1 binary
    pIndBinGenOperat     = dfOption   ['IndBinGenOperat'    ][0].astype('int')                                                            # Indicator of binary generation operation decisions, 0 continuous - 1 binary
    pIndBinLineCommit    = dfOption   ['IndBinLineCommit'   ][0].astype('int')                                                            # Indicator of binary network    switching decisions, 0 continuous - 1 binary
    pIndNetLosses        = dfOption   ['IndNetLosses'       ][0].astype('int')                                                            # Indicator of network losses,                        0 lossless   - 1 ohmic losses
    pENSCost             = dfParameter['ENSCost'            ][0] * 1e-3                                                                   # cost of energy not served                [MEUR/GWh]
    pCO2Cost             = dfParameter['CO2Cost'            ][0]                                                                          # cost of CO2 emission                     [EUR/t CO2]
    pUpReserveActivation = dfParameter['UpReserveActivation'][0]                                                                          # upward   reserve activation              [p.u.]
    pDwReserveActivation = dfParameter['DwReserveActivation'][0]                                                                          # downward reserve activation              [p.u.]
    pMinRatioDwUp        = dfParameter['MinRatioDwUp'       ][0]                                                                          # minimum ratio down up operating reserves [p.u.]
    pMaxRatioDwUp        = dfParameter['MaxRatioDwUp'       ][0]                                                                          # maximum ratio down up operating reserves [p.u.]
    pSBase               = dfParameter['SBase'              ][0] * 1e-3                                                                   # base power                               [GW]
    pReferenceNode       = dfParameter['ReferenceNode'      ][0]                                                                          # reference node
    pTimeStep            = dfParameter['TimeStep'           ][0].astype('int')                                                            # duration of the unit time step           [h]
    # pStageDuration       = dfParameter['StageDuration'      ][0].astype('int')                                                          # duration of each stage                   [h]

    pScenProb            = dfScenario     ['Probability'   ]                                                                              # probabilities of scenarios               [p.u.]
    pStageWeight         = dfStage        ['Weight'        ]                                                                              # weights of stages                        [p.u.]
    pDuration            = dfDuration     ['Duration'      ]    * pTimeStep                                                               # duration of load levels                  [h]
    pReserveMargin       = dfReserveMargin['ReserveMargin' ]                                                                              # minimum adequacy reserve margin          [p.u.]
    pLevelToStage        = dfDuration     ['Stage'         ]                                                                              # load levels assignment to stages
    pDemand              = dfDemand               [mTEPES.nd]    * 1e-3                                                                   # demand                                   [GW]
    pSystemInertia       = dfInertia              [mTEPES.ar]                                                                             # inertia                                  [s]
    pOperReserveUp       = dfUpOperatingReserve   [mTEPES.ar]    * 1e-3                                                                   # upward   operating reserve               [GW]
    pOperReserveDw       = dfDwOperatingReserve   [mTEPES.ar]    * 1e-3                                                                   # downward operating reserve               [GW]
    pVariableMinPower    = dfVariableMinPower     [mTEPES.gg]    * 1e-3                                                                   # dynamic variable minimum power           [GW]
    pVariableMaxPower    = dfVariableMaxPower     [mTEPES.gg]    * 1e-3                                                                   # dynamic variable maximum power           [GW]
    pVariableMinCharge   = dfVariableMinCharge    [mTEPES.gg]    * 1e-3                                                                   # dynamic variable minimum charge          [GW]
    pVariableMaxCharge   = dfVariableMaxCharge    [mTEPES.gg]    * 1e-3                                                                   # dynamic variable maximum charge          [GW]
    pVariableMinStorage  = dfVariableMinStorage   [mTEPES.gg]                                                                             # dynamic variable minimum storage         [GWh]
    pVariableMaxStorage  = dfVariableMaxStorage   [mTEPES.gg]                                                                             # dynamic variable maximum storage         [GWh]
    pEnergyInflows       = dfEnergyInflows        [mTEPES.gg]    * 1e-3                                                                   # dynamic energy inflows                   [GW]
    pEnergyOutflows      = dfEnergyOutflows       [mTEPES.gg]    * 1e-3                                                                   # dynamic energy outflows                  [GW]

    # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for operating reserve, variable max power, variable min and max storage and inflows
    if pTimeStep > 1:
        pDemand             = pDemand.rolling            (pTimeStep).mean()
        pSystemInertia      = pSystemInertia.rolling     (pTimeStep).mean()
        pOperReserveUp      = pOperReserveUp.rolling     (pTimeStep).mean()
        pOperReserveDw      = pOperReserveDw.rolling     (pTimeStep).mean()
        pVariableMinPower   = pVariableMinPower.rolling  (pTimeStep).mean()
        pVariableMaxPower   = pVariableMaxPower.rolling  (pTimeStep).mean()
        pVariableMinCharge  = pVariableMinCharge.rolling (pTimeStep).mean()
        pVariableMaxCharge  = pVariableMaxCharge.rolling (pTimeStep).mean()
        pVariableMinStorage = pVariableMinStorage.rolling(pTimeStep).mean()
        pVariableMaxStorage = pVariableMaxStorage.rolling(pTimeStep).mean()
        pEnergyInflows      = pEnergyInflows.rolling     (pTimeStep).mean()
        pEnergyOutflows     = pEnergyOutflows.rolling    (pTimeStep).mean()

    pDemand.fillna            (0.0, inplace=True)
    pSystemInertia.fillna     (0.0, inplace=True)
    pOperReserveUp.fillna     (0.0, inplace=True)
    pOperReserveDw.fillna     (0.0, inplace=True)
    pVariableMinPower.fillna  (0.0, inplace=True)
    pVariableMaxPower.fillna  (0.0, inplace=True)
    pVariableMinCharge.fillna (0.0, inplace=True)
    pVariableMaxCharge.fillna (0.0, inplace=True)
    pVariableMinStorage.fillna(0.0, inplace=True)
    pVariableMaxStorage.fillna(0.0, inplace=True)
    pEnergyInflows.fillna     (0.0, inplace=True)
    pEnergyOutflows.fillna    (0.0, inplace=True)

    if pTimeStep > 1:
        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for i in range(pTimeStep-2,-1,-1):
            pDuration[range(i,len(mTEPES.nn),pTimeStep)] = 0

    #%% generation parameters
    pGenToNode          = dfGeneration  ['Node'                  ]                                                                            # generator location in node
    pGenToTechnology    = dfGeneration  ['Technology'            ]                                                                            # generator association to technology
    pGenToExclusiveGen  = dfGeneration  ['MutuallyExclusive'     ]                                                                            # mutually exclusive generator
    pIndBinUnitInvest   = dfGeneration  ['BinaryInvestment'      ]                                                                            # binary unit investment decision             [Yes]
    pIndBinUnitRetire   = dfGeneration  ['BinaryRetirement'      ]                                                                            # binary unit retirement decision             [Yes]
    pIndBinUnitCommit   = dfGeneration  ['BinaryCommitment'      ]                                                                            # binary unit commitment decision             [Yes]
    pIndOperReserve     = dfGeneration  ['NoOperatingReserve'    ]                                                                            # no contribution to operating reserve        [Yes]
    pMustRun            = dfGeneration  ['MustRun'               ]                                                                            # must-run unit                               [Yes]
    pInertia            = dfGeneration  ['Inertia'               ]                                                                            # inertia constant                            [s]
    pAvailability       = dfGeneration  ['Availability'          ]                                                                            # unit availability for adequacy              [p.u.]
    pEFOR               = dfGeneration  ['EFOR'                  ]                                                                            # EFOR                                        [p.u.]
    pRatedMinPower      = dfGeneration  ['MinimumPower'          ] * 1e-3 * (1.0-dfGeneration['EFOR'])                                        # rated minimum power                         [GW]
    pRatedMaxPower      = dfGeneration  ['MaximumPower'          ] * 1e-3 * (1.0-dfGeneration['EFOR'])                                        # rated maximum power                         [GW]
    pLinearFuelCost     = dfGeneration  ['LinearTerm'            ] * 1e-3 *      dfGeneration['FuelCost']                                     # fuel     term variable cost                 [MEUR/GWh]
    pLinearOMCost       = dfGeneration  ['OMVariableCost'        ] * 1e-3                                                                     # O&M      term variable cost                 [MEUR/GWh]
    pConstantVarCost    = dfGeneration  ['ConstantTerm'          ] * 1e-6 *      dfGeneration['FuelCost']                                     # constant term variable cost                 [MEUR/h]
    pOperReserveCost    = dfGeneration  ['OperReserveCost'       ] * 1e-3                                                                     # operating reserve      cost                 [MEUR/GW]
    pStartUpCost        = dfGeneration  ['StartUpCost'           ]                                                                            # startup  cost                               [MEUR]
    pShutDownCost       = dfGeneration  ['ShutDownCost'          ]                                                                            # shutdown cost                               [MEUR]
    pRampUp             = dfGeneration  ['RampUp'                ] * 1e-3                                                                     # ramp up   rate                              [GW/h]
    pRampDw             = dfGeneration  ['RampDown'              ] * 1e-3                                                                     # ramp down rate                              [GW/h]
    pCO2EmissionCost    = dfGeneration  ['CO2EmissionRate'       ] * 1e-3 * pCO2Cost                                                          # emission  cost                              [MEUR/GWh]
    pUpTime             = dfGeneration  ['UpTime'                ]                                                                            # minimum up   time                           [h]
    pDwTime             = dfGeneration  ['DownTime'              ]                                                                            # minimum down time                           [h]
    pGenInvestCost      = dfGeneration  ['FixedInvestmentCost'   ] *        dfGeneration['FixedChargeRate']                                   # generation fixed cost                       [MEUR]
    pGenRetireCost      = dfGeneration  ['FixedRetirementCost'   ] *        dfGeneration['FixedChargeRate']                                   # generation fixed retirement cost            [MEUR]
    pRatedMinCharge     = dfGeneration  ['MinimumCharge'         ] * 1e-3                                                                     # rated minimum ESS charge                    [GW]
    pRatedMaxCharge     = dfGeneration  ['MaximumCharge'         ] * 1e-3                                                                     # rated maximum ESS charge                    [GW]
    pRatedMinStorage    = dfGeneration  ['MinimumStorage'        ]                                                                            # rated minimum ESS storage                   [GWh]
    pRatedMaxStorage    = dfGeneration  ['MaximumStorage'        ]                                                                            # rated maximum ESS storage                   [GWh]
    pInitialInventory   = dfGeneration  ['InitialStorage'        ]                                                                            # initial       ESS storage                   [GWh]
    pEfficiency         = dfGeneration  ['Efficiency'            ]                                                                            #         ESS round-trip efficiency           [p.u.]
    pStorageType        = dfGeneration  ['StorageType'           ]                                                                            #         ESS storage  type
    pOutflowsType       = dfGeneration  ['OutflowsType'          ]                                                                            #         ESS outflows type
    pRMaxReactivePower  = dfGeneration  ['MaximumReactivePower'  ] * 1e-3                                                                     # rated maximum reactive power                [Gvar]

    pLinearOperCost     = pLinearFuelCost + pCO2EmissionCost
    pLinearVarCost      = pLinearFuelCost + pLinearOMCost

    pNodeLat            = dfNodeLocation['Latitude'              ]                                                                            # node latitude                               [º]
    pNodeLon            = dfNodeLocation['Longitude'             ]                                                                            # node longitude                              [º]

    pLineType           = dfNetwork     ['LineType'              ]                                                                            # line type
    pLineLength         = dfNetwork     ['Length'                ]                                                                            # line length                                 [km]
    pLineVoltage        = dfNetwork     ['Voltage'               ]                                                                            # line voltage                                [kV]
    pLineLossFactor     = dfNetwork     ['LossFactor'            ]                                                                            # loss factor                                 [p.u.]
    pLineR              = dfNetwork     ['Resistance'            ]                                                                            # resistance                                  [p.u.]
    pLineX              = dfNetwork     ['Reactance'             ].sort_index()                                                               # reactance                                   [p.u.]
    pLineBsh            = dfNetwork     ['Susceptance'           ]                                                                            # susceptance                                 [p.u.]
    pLineTAP            = dfNetwork     ['Tap'                   ]                                                                            # tap changer                                 [p.u.]
    pLineNTCFrw         = dfNetwork     ['TTC'                   ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in forward  direction [GW]
    pLineNTCBck         = dfNetwork     ['TTCBck'                ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in backward direction [GW]
    pNetFixedCost       = dfNetwork     ['FixedInvestmentCost'   ] *        dfNetwork['FixedChargeRate']                                      # network    fixed cost                       [MEUR]
    pIndBinLineSwitch   = dfNetwork     ['Switching'             ]                                                                            # binary line switching  decision             [Yes]
    pIndBinLineInvest   = dfNetwork     ['BinaryInvestment'      ]                                                                            # binary line investment decision             [Yes]
    pSwitchOnTime       = dfNetwork     ['SwOnTime'              ]                                                                            # minimum on  time                            [h]
    pSwitchOffTime      = dfNetwork     ['SwOffTime'             ]                                                                            # minimum off time                            [h]
    pAngMin             = dfNetwork     ['AngMin'                ] * math.pi / 180                                                            # Min phase angle difference                  [rad]
    pAngMax             = dfNetwork     ['AngMax'                ] * math.pi / 180                                                            # Max phase angle difference                  [rad]

    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    pLineNTCBck     = pLineNTCBck.where(pLineNTCBck > 0.0, other=pLineNTCFrw)
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    pLineNTCFrw     = pLineNTCFrw.where(pLineNTCFrw > 0.0, other=pLineNTCBck)

    # minimum up and down time converted to an integer number of time steps
    pSwitchOnTime  = round(pSwitchOnTime /pTimeStep).astype('int')
    pSwitchOffTime = round(pSwitchOffTime/pTimeStep).astype('int')

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the lines (la), candidate lines (lc), candidate DC lines (cd), existing DC lines (cd), lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.sc = Set(initialize=mTEPES.scc,                    ordered=True , doc='scenarios'            , filter=lambda mTEPES,scc     :  scc       in mTEPES.scc and pScenProb        [scc] >  0.0)
    mTEPES.st = Set(initialize=mTEPES.stt,                    ordered=True , doc='stages'               , filter=lambda mTEPES,stt     :  stt       in mTEPES.stt and pStageWeight     [stt] >  0.0)
    mTEPES.n  = Set(initialize=mTEPES.nn,                     ordered=True , doc='load levels'          , filter=lambda mTEPES,nn      :  nn        in mTEPES.nn  and pDuration         [nn] >  0  )
    mTEPES.n2 = Set(initialize=mTEPES.nn,                     ordered=True , doc='load levels'          , filter=lambda mTEPES,nn      :  nn        in mTEPES.nn  and pDuration         [nn] >  0  )
    mTEPES.g  = Set(initialize=mTEPES.gg,                     ordered=False, doc='generating      units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and (pRatedMaxPower   [gg] >  0.0 or  pRatedMaxCharge[gg] >  0.0) and pGenToNode.reset_index().set_index(['index']).isin(mTEPES.nd)['Node'][gg])  # excludes generators with empty node
    mTEPES.t  = Set(initialize=mTEPES.g ,                     ordered=False, doc='thermal         units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pLinearOperCost   [g ] >  0.0)
    mTEPES.r  = Set(initialize=mTEPES.g ,                     ordered=False, doc='RES             units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pLinearOperCost   [g ] == 0.0 and pRatedMaxStorage[g] == 0.0)
    mTEPES.es = Set(initialize=mTEPES.g ,                     ordered=False, doc='ESS             units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and                                   pRatedMaxStorage[g] >  0.0)
    mTEPES.gc = Set(initialize=mTEPES.g ,                     ordered=False, doc='candidate       units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pGenInvestCost    [g ] >  0.0)
    mTEPES.gd = Set(initialize=mTEPES.g ,                     ordered=False, doc='retirement      units', filter=lambda mTEPES,g       :  g         in mTEPES.g   and pGenRetireCost    [g ] != 0.0)
    mTEPES.ec = Set(initialize=mTEPES.es,                     ordered=False, doc='candidate   ESS units', filter=lambda mTEPES,es      :  es        in mTEPES.es  and pGenInvestCost    [es] >  0.0)
    mTEPES.br = Set(initialize=mTEPES.ni*mTEPES.nf,           ordered=False, doc='all branches         ', filter=lambda mTEPES,ni,nf   : (ni,nf)    in                pLineType                    )
    mTEPES.ln = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all input       lines', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in                pLineType                    )
    mTEPES.la = Set(initialize=mTEPES.ln,                     ordered=False, doc='all real        lines', filter=lambda mTEPES,*ln     :  ln        in mTEPES.ln  and pLineX            [ln] != 0.0 and pLineNTCFrw[ln] > 0.0 and pLineNTCBck[ln] > 0.0)
    mTEPES.lc = Set(initialize=mTEPES.la,                     ordered=False, doc='candidate       lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] >  0.0)
    mTEPES.cd = Set(initialize=mTEPES.la,                     ordered=False, doc='             DC lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] >  0.0 and pLineType[la] == 'DC')
    mTEPES.ed = Set(initialize=mTEPES.la,                     ordered=False, doc='             DC lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pNetFixedCost     [la] == 0.0 and pLineType[la] == 'DC')
    mTEPES.ll = Set(initialize=mTEPES.la,                     ordered=False, doc='loss            lines', filter=lambda mTEPES,*la     :  la        in mTEPES.la  and pLineLossFactor   [la] >  0.0 and pIndNetLosses >   0  )
    mTEPES.rf = Set(initialize=mTEPES.nd,                     ordered=True , doc='reference node'       , filter=lambda mTEPES,nd      :  nd        in                pReferenceNode               )
    mTEPES.gq = Set(initialize=mTEPES.gg,                     ordered=False, doc='gen    reactive units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and pRMaxReactivePower[gg] >  0.0)
    mTEPES.sq = Set(initialize=mTEPES.gg,                     ordered=False, doc='syn    reactive units', filter=lambda mTEPES,gg      :  gg        in mTEPES.gg  and pRMaxReactivePower[gg] >  0.0 and pGenToTechnology[gg] == 'SynchronousCondenser')
    mTEPES.sqc= Set(initialize=mTEPES.sq,                     ordered=False, doc='syn    reactive cand '                                                                                           )
    mTEPES.shc= Set(initialize=mTEPES.sq,                     ordered=False, doc='shunt           cand '                                                                                           )

    # non-RES units, they can be committed and also contribute to the operating reserves
    mTEPES.nr = mTEPES.g - mTEPES.r

    # machines able to provide reactive power
    mTEPES.tq = mTEPES.gq - mTEPES.sq

    # existing lines (le)
    mTEPES.le = mTEPES.la - mTEPES.lc

    # # input lines
    # mTEPES.lin = Set(initialize=mTEPES.nf*mTEPES.ni*mTEPES.cc, ordered=False, doc='input line', filter=lambda mTEPES,nf,ni,cc: (ni,nf,cc) in mTEPES.la)
    # mTEPES.lil = Set(initialize=mTEPES.nf*mTEPES.ni*mTEPES.cc, ordered=False, doc='input line', filter=lambda mTEPES,nf,ni,cc: (ni,nf,cc) in mTEPES.ll)

    # assigning a node to an area
    pNode2Area = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(mTEPES.nd*mTEPES.ar, names=('Node', 'Area')), columns=['Y/N'])
    for nd,zn,ar in mTEPES.ndzn*mTEPES.ar:
        if (zn,ar) in mTEPES.znar:
            pNode2Area.loc[nd,ar] = 1
    mTEPES.ndar = Set(initialize=mTEPES.nd*mTEPES.ar, ordered=False, doc='node to area', filter=lambda mTEPES,nd,ar: (nd,ar) in mTEPES.nd*mTEPES.ar and pNode2Area.loc[nd,ar]['Y/N'] == 1)

    # assigning a line to an area. Both nodes are in the same area. Cross-area lines not included
    pLine2Area = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(mTEPES.la*mTEPES.ar, names=('InitialNode', 'FinalNode', 'Circuit', 'Area')), columns=['Y/N'])
    for ni,nf,cc,ar in mTEPES.la*mTEPES.ar:
        if (ni,ar) in mTEPES.ndar:
            if (nf,ar) in mTEPES.ndar:
                pLine2Area.loc[ni,nf,cc,ar] = 1
    mTEPES.laar = Set(initialize=mTEPES.la*mTEPES.ar, ordered=False, doc='line to area', filter=lambda mTEPES,ni,nf,cc,ar: (ni,nf,cc,ar) in mTEPES.la*mTEPES.ar and pLine2Area.loc[ni,nf,cc,ar]['Y/N'] == 1)

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

    pIndBinUnitInvest = pIndBinUnitInvest.map(idxDict)
    pIndBinUnitRetire = pIndBinUnitRetire.map(idxDict)
    pIndBinUnitCommit = pIndBinUnitCommit.map(idxDict)
    pIndOperReserve   = pIndOperReserve.map  (idxDict)
    pMustRun          = pMustRun.map         (idxDict)
    pIndBinLineInvest = pIndBinLineInvest.map(idxDict)
    pIndBinLineSwitch = pIndBinLineSwitch.map(idxDict)

    # define AC existing  lines     non-switchable
    mTEPES.lea = Set(initialize=mTEPES.le, ordered=False, doc='AC existing  lines and non-switchable lines', filter=lambda mTEPES,*le: le in mTEPES.le and  pIndBinLineSwitch[le] == 0                             and not pLineType[le] == 'DC')
    # define AC candidate lines and     switchable lines
    mTEPES.lca = Set(initialize=mTEPES.la, ordered=False, doc='AC candidate lines and     switchable lines', filter=lambda mTEPES,*la: la in mTEPES.la and (pIndBinLineSwitch[la] == 1 or pNetFixedCost[la] > 0.0) and not pLineType[la] == 'DC')

    mTEPES.laa = mTEPES.lea | mTEPES.lca

    # define DC existing  lines     non-switchable
    mTEPES.led = Set(initialize=mTEPES.le, ordered=False, doc='DC existing  lines and non-switchable lines', filter=lambda mTEPES,*le: le in mTEPES.le and  pIndBinLineSwitch[le] == 0                             and pLineType[le] == 'DC')
    # define DC candidate lines and     switchable lines
    mTEPES.lcd = Set(initialize=mTEPES.la, ordered=False, doc='DC candidate lines and     switchable lines', filter=lambda mTEPES,*la: la in mTEPES.la and (pIndBinLineSwitch[la] == 1 or pNetFixedCost[la] > 0.0) and pLineType[la] == 'DC')

    mTEPES.lad = mTEPES.led | mTEPES.lcd

    # line type
    pLineType = pLineType.reset_index().set_index(['level_0','level_1','level_2','LineType'])

    mTEPES.pLineType = Set(initialize=pLineType.index, ordered=False, doc='line type')

    #%% inverse index load level to stage
    pStageToLevel = pLevelToStage.reset_index().set_index('Stage').set_axis(['LoadLevel'], axis=1, inplace=False)[['LoadLevel']]
    pStageToLevel = pStageToLevel.loc[pStageToLevel['LoadLevel'].isin(mTEPES.n)]
    pStage2Level  = pStageToLevel.reset_index().set_index(['Stage','LoadLevel'])

    mTEPES.s2n = Set(initialize=pStage2Level.index, ordered=False, doc='load level to stage')

    mTEPES.pLoadLevelWeight = Param(mTEPES.n, initialize=0.0, within=NonNegativeReals, doc='Load level weight', mutable=True)
    for st,n in mTEPES.s2n:
        mTEPES.pLoadLevelWeight[n] = pStageWeight[st]

    #%% inverse index node to generator
    pNodeToGen = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pNodeToGen = pNodeToGen.loc[pNodeToGen['Generator'].isin(mTEPES.g)]
    pNode2Gen  = pNodeToGen.reset_index().set_index(['Node', 'Generator'])

    mTEPES.n2g = Set(initialize=pNode2Gen.index, ordered=False, doc='node   to generator')

    pZone2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(mTEPES.zn*mTEPES.g, names=('Zone',   'Generator')), columns=['Y/N'])
    pArea2Gen   = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(mTEPES.ar*mTEPES.g, names=('Area',   'Generator')), columns=['Y/N'])
    pRegion2Gen = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(mTEPES.rg*mTEPES.g, names=('Region', 'Generator')), columns=['Y/N'])

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

    mTEPES.z2g = Set(initialize=mTEPES.zn*mTEPES.g, ordered=False, doc='zone   to generator', filter=lambda mTEPES,zn,g: (zn,g) in mTEPES.zn*mTEPES.g and pZone2Gen.loc  [zn,g]['Y/N'] == 1)
    mTEPES.a2g = Set(initialize=mTEPES.ar*mTEPES.g, ordered=False, doc='area   to generator', filter=lambda mTEPES,ar,g: (ar,g) in mTEPES.ar*mTEPES.g and pArea2Gen.loc  [ar,g]['Y/N'] == 1)
    mTEPES.r2g = Set(initialize=mTEPES.rg*mTEPES.g, ordered=False, doc='region to generator', filter=lambda mTEPES,rg,g: (rg,g) in mTEPES.rg*mTEPES.g and pRegion2Gen.loc[rg,g]['Y/N'] == 1)

    #%% inverse index generator to technology
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(mTEPES.g)]
    pTechnology2Gen  = pTechnologyToGen.reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=pTechnology2Gen.index, ordered=False, doc='technology to generator')

    # ESS and RES technologies
    mTEPES.ot = Set(initialize=mTEPES.gt, ordered=False, doc='storage technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for es in mTEPES.es if (gt,es) in mTEPES.t2g))
    mTEPES.rt = Set(initialize=mTEPES.gt, ordered=False, doc='RES     technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for r  in mTEPES.r  if (gt,r ) in mTEPES.t2g))

    #%% inverse index generator to mutually exclusive generator
    pExclusiveGenToGen = pGenToExclusiveGen.reset_index().set_index('MutuallyExclusive').set_axis(['Generator'], axis=1, inplace=False)[['Generator']]
    pExclusiveGenToGen = pExclusiveGenToGen.loc[pExclusiveGenToGen['Generator'].isin(mTEPES.g)]
    pExclusiveGen2Gen  = pExclusiveGenToGen.reset_index().set_index(['MutuallyExclusive', 'Generator'])

    mTEPES.g2g = Set(initialize=pExclusiveGen2Gen.index, ordered=False, doc='mutually exclusive generator to generator', filter=lambda mTEPES,gg,g: (gg,g) in mTEPES.gg*mTEPES.g)

    # minimum and maximum variable power
    pVariableMinPower   = pVariableMinPower.replace(0.0, float('nan'))
    pVariableMaxPower   = pVariableMaxPower.replace(0.0, float('nan'))
    pMinPower           = pd.DataFrame([pRatedMinPower]*len(pVariableMinPower.index), index=pd.MultiIndex.from_tuples(pVariableMinPower.index), columns=pRatedMinPower.index)
    pMaxPower           = pd.DataFrame([pRatedMaxPower]*len(pVariableMaxPower.index), index=pd.MultiIndex.from_tuples(pVariableMaxPower.index), columns=pRatedMaxPower.index)
    pMinPower           = pMinPower.reindex        (sorted(pMinPower.columns        ), axis=1)
    pMaxPower           = pMaxPower.reindex        (sorted(pMaxPower.columns        ), axis=1)
    pVariableMinPower   = pVariableMinPower.reindex(sorted(pVariableMinPower.columns), axis=1)
    pVariableMaxPower   = pVariableMaxPower.reindex(sorted(pVariableMaxPower.columns), axis=1)
    pMinPower           = pVariableMinPower.where         (pVariableMinPower > pMinPower, other=pMinPower)
    pMaxPower           = pVariableMaxPower.where         (pVariableMaxPower < pMaxPower, other=pMaxPower)
    pMinPower           = pMinPower.where                 (pMinPower         > 0.0,       other=0.0)
    pMaxPower           = pMaxPower.where                 (pMaxPower         > 0.0,       other=0.0)

    # minimum and maximum variable charge
    pVariableMinCharge  = pVariableMinCharge.replace(0.0, float('nan'))
    pVariableMaxCharge  = pVariableMaxCharge.replace(0.0, float('nan'))
    pMinCharge          = pd.DataFrame([pRatedMinCharge]*len(pVariableMinCharge.index), index=pd.MultiIndex.from_tuples(pVariableMinCharge.index), columns=pRatedMinCharge.index)
    pMaxCharge          = pd.DataFrame([pRatedMaxCharge]*len(pVariableMaxCharge.index), index=pd.MultiIndex.from_tuples(pVariableMaxCharge.index), columns=pRatedMaxCharge.index)
    pMinCharge          = pMinCharge.reindex        (sorted(pMinCharge.columns        ), axis=1)
    pMaxCharge          = pMaxCharge.reindex        (sorted(pMaxCharge.columns        ), axis=1)
    pVariableMinCharge  = pVariableMinCharge.reindex(sorted(pVariableMinCharge.columns), axis=1)
    pVariableMaxCharge  = pVariableMaxCharge.reindex(sorted(pVariableMaxCharge.columns), axis=1)
    pMinCharge          = pVariableMinCharge.where         (pVariableMinCharge > pMinCharge, other=pMinCharge)
    pMaxCharge          = pVariableMaxCharge.where         (pVariableMaxCharge < pMaxCharge, other=pMaxCharge)
    pMinCharge          = pMinCharge.where                 (pMinCharge         > 0.0,        other=0.0)
    pMaxCharge          = pMaxCharge.where                 (pMaxCharge         > 0.0,        other=0.0)

    # minimum and maximum variable storage capacity
    pVariableMinStorage = pVariableMinStorage.replace(0.0, float('nan'))
    pVariableMaxStorage = pVariableMaxStorage.replace(0.0, float('nan'))
    pMinStorage         = pd.DataFrame([pRatedMinStorage]*len(pVariableMinStorage.index), index=pd.MultiIndex.from_tuples(pVariableMinStorage.index), columns=pRatedMinStorage.index)
    pMaxStorage         = pd.DataFrame([pRatedMaxStorage]*len(pVariableMaxStorage.index), index=pd.MultiIndex.from_tuples(pVariableMaxStorage.index), columns=pRatedMaxStorage.index)
    pMinStorage         = pMinStorage.reindex        (sorted(pMinStorage.columns        ), axis=1)
    pMaxStorage         = pMaxStorage.reindex        (sorted(pMaxStorage.columns        ), axis=1)
    pVariableMinStorage = pVariableMinStorage.reindex(sorted(pVariableMinStorage.columns), axis=1)
    pVariableMaxStorage = pVariableMaxStorage.reindex(sorted(pVariableMaxStorage.columns), axis=1)
    pMinStorage         = pVariableMinStorage.where         (pVariableMinStorage > pMinStorage, other=pMinStorage)
    pMaxStorage         = pVariableMaxStorage.where         (pVariableMaxStorage < pMaxStorage, other=pMaxStorage)
    pMinStorage         = pMinStorage.where                 (pMinStorage         > 0.0,         other=0.0)
    pMaxStorage         = pMaxStorage.where                 (pMaxStorage         > 0.0,         other=0.0)

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
            pCycleTimeStep[es] =       1
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
    # pStageDuration = max(pStageDuration, pCycleTimeStep.max(), pOutflowsTimeStep.max())

    # drop load levels with duration 0
    pDuration         = pDuration.loc        [                   mTEPES.n          ]
    pDemand           = pDemand.loc          [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pSystemInertia    = pSystemInertia.loc   [mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar]
    pOperReserveUp    = pOperReserveUp.loc   [mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar]
    pOperReserveDw    = pOperReserveDw.loc   [mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar]
    pMinPower         = pMinPower.loc        [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pMaxPower         = pMaxPower.loc        [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pMinCharge        = pMinCharge.loc       [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pMaxCharge        = pMaxCharge.loc       [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pEnergyInflows    = pEnergyInflows.loc   [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pEnergyOutflows   = pEnergyOutflows.loc  [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pMinStorage       = pMinStorage.loc      [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pMaxStorage       = pMaxStorage.loc      [mTEPES.sc*mTEPES.p*mTEPES.n          ]
    pIniInventory     = pIniInventory.loc    [mTEPES.sc*mTEPES.p*mTEPES.n          ]

    # separate positive and negative demands to avoid converting negative values to 0
    pDemandPos          = pDemand.where         (pDemand >= 0.0, other=0.0)
    pDemandNeg          = pDemand.where         (pDemand <  0.0, other=0.0)
    # small values are converted to 0
    pPeakDemand         = pd.Series(data=[0.0 for ar in mTEPES.ar], index=mTEPES.ar)
    for ar in mTEPES.ar:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        pPeakDemand[ar] = pDemand      [[nd for nd in mTEPES.nd if (nd,ar) in mTEPES.ndar]].sum(axis=1).max()
        pEpsilon        = pPeakDemand[ar]*2.5e-5
        # values < 1e-5 times the maximum system demand are converted to 0
        # pEpsilon      = pDemand.sum(axis=1).max()*1e-5

        # these parameters are in GW
        pDemandPos     [pDemandPos     [[nd for nd in mTEPES.nd if (nd,ar) in mTEPES.ndar]] <  pEpsilon] = 0.0
        pDemandNeg     [pDemandNeg     [[nd for nd in mTEPES.nd if (nd,ar) in mTEPES.ndar]] > -pEpsilon] = 0.0
        pSystemInertia [pSystemInertia [[                                              ar]] <  pEpsilon] = 0.0
        pOperReserveUp [pOperReserveUp [[                                              ar]] <  pEpsilon] = 0.0
        pOperReserveDw [pOperReserveDw [[                                              ar]] <  pEpsilon] = 0.0
        pMinPower      [pMinPower      [[g  for  g in mTEPES.g  if (ar,g)  in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pMaxPower      [pMaxPower      [[g  for  g in mTEPES.g  if (ar,g)  in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pMinCharge     [pMinCharge     [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pMaxCharge     [pMaxCharge     [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pEnergyInflows [pEnergyInflows [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon/pTimeStep] = 0.0
        pEnergyOutflows[pEnergyOutflows[[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon/pTimeStep] = 0.0

        # merging positive and negative values of the demand
        pDemand         = pDemandPos.where      (pDemandPos >= 0.0, other=pDemandNeg)

        # these parameters are in GWh
        pMinStorage    [pMinStorage    [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pMaxStorage    [pMaxStorage    [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon] = 0.0
        pIniInventory  [pIniInventory  [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g ]] <  pEpsilon] = 0.0

        # these parameters are in GW
        for ni,nf,cc,ar in mTEPES.laar:
            if  pLineNTCFrw[ni,nf,cc] < pEpsilon:
                pLineNTCFrw[ni,nf,cc] = 0.0
            if  pLineNTCBck[ni,nf,cc] < pEpsilon:
                pLineNTCBck[ni,nf,cc] = 0.0
        for ar,es in mTEPES.a2g:
            if  pInitialInventory[es] < pEpsilon and es in mTEPES.es:
                pInitialInventory[es] = 0.0

        pMaxPower2ndBlock  = pMaxPower  - pMinPower
        pMaxCharge2ndBlock = pMaxCharge - pMinCharge

        pMaxPower2ndBlock [pMaxPower2ndBlock [[es for es in mTEPES.es if (ar,es) in mTEPES.a2g]] < pEpsilon] = 0.0
        pMaxCharge2ndBlock[pMaxCharge2ndBlock[[es for es in mTEPES.es if (ar,es) in mTEPES.a2g]] < pEpsilon] = 0.0

    # replace < 0.0 by 0.0
    pMaxPower2ndBlock  = pMaxPower2ndBlock.where (pMaxPower2ndBlock  > 0.0, other=0.0)
    pMaxCharge2ndBlock = pMaxCharge2ndBlock.where(pMaxCharge2ndBlock > 0.0, other=0.0)

    # BigM maximum flow to be used in the Kirchhoff's 2nd law disjunctive constraint
    pBigMFlowBck = pLineNTCBck*0.0
    pBigMFlowFrw = pLineNTCFrw*0.0
    for lea in mTEPES.lea:
        pBigMFlowBck.loc[lea] = pLineNTCBck[lea]
        pBigMFlowFrw.loc[lea] = pLineNTCFrw[lea]
    for lca in mTEPES.lca:
        pBigMFlowBck.loc[lca] = pLineNTCBck[lca]*1.5
        pBigMFlowFrw.loc[lca] = pLineNTCFrw[lca]*1.5
    for led in mTEPES.led:
        pBigMFlowBck.loc[led] = pLineNTCBck[led]
        pBigMFlowFrw.loc[led] = pLineNTCFrw[led]
    for lcd in mTEPES.lcd:
        pBigMFlowBck.loc[lcd] = pLineNTCBck[lcd]*1.5
        pBigMFlowFrw.loc[lcd] = pLineNTCFrw[lcd]*1.5

    # maximum voltage angle
    pMaxTheta = pDemand*0.0 + math.pi/2
    pMaxTheta = pMaxTheta.loc[mTEPES.sc*mTEPES.p*mTEPES.n]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    # %% parameters
    mTEPES.pIndBinGenInvest      = Param(initialize=pIndBinGenInvest     , within=Boolean, doc='Indicator of binary generation investment decisions', mutable=True)
    mTEPES.pIndBinGenRetire      = Param(initialize=pIndBinGenRetire     , within=Boolean, doc='Indicator of binary generation retirement decisions', mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=pIndBinGenOperat     , within=Boolean, doc='Indicator of binary generation operation  decisions', mutable=True)
    mTEPES.pIndBinNetInvest      = Param(initialize=pIndBinNetInvest     , within=Boolean, doc='Indicator of binary network    investment decisions', mutable=True)
    mTEPES.pIndBinLineCommit     = Param(initialize=pIndBinLineCommit    , within=Boolean, doc='Indicator of binary network    switching  decisions', mutable=True)
    mTEPES.pIndNetLosses         = Param(initialize=pIndNetLosses        , within=Boolean, doc='Indicator of binary network ohmic losses',            mutable=True)

    mTEPES.pENSCost              = Param(initialize=pENSCost             , within=NonNegativeReals)
    mTEPES.pCO2Cost              = Param(initialize=pCO2Cost             , within=NonNegativeReals)
    mTEPES.pUpReserveActivation  = Param(initialize=pUpReserveActivation , within=UnitInterval    )
    mTEPES.pDwReserveActivation  = Param(initialize=pDwReserveActivation , within=UnitInterval    )
    mTEPES.pMinRatioDwUp         = Param(initialize=pMinRatioDwUp        , within=UnitInterval    )
    mTEPES.pMaxRatioDwUp         = Param(initialize=pMaxRatioDwUp        , within=UnitInterval    )
    mTEPES.pSBase                = Param(initialize=pSBase               , within=NonNegativeReals)
    mTEPES.pTimeStep             = Param(initialize=pTimeStep            , within=NonNegativeReals)
    # mTEPES.pStageDuration        = Param(initialize=pStageDuration      , within=NonNegativeReals)

    mTEPES.pReserveMargin        = Param(                               mTEPES.ar, initialize=pReserveMargin.to_dict()            , within=NonNegativeReals, doc='Adequacy reserve margin'        )
    mTEPES.pPeakDemand           = Param(                               mTEPES.ar, initialize=pPeakDemand.to_dict()               , within=NonNegativeReals, doc='Peak demand'                    )
    mTEPES.pDemand               = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pDemand.stack().to_dict()           , within=           Reals, doc='Demand'                         )
    mTEPES.pScenProb             = Param(mTEPES.scc,                               initialize=pScenProb.to_dict()                 , within=UnitInterval    , doc='Probability'                    )
    mTEPES.pStageWeight          = Param(mTEPES.stt,                               initialize=pStageWeight.to_dict()              , within=NonNegativeReals, doc='Stage weight'                   )
    mTEPES.pDuration             = Param(                     mTEPES.n,            initialize=pDuration.to_dict()                 , within=NonNegativeReals, doc='Duration'                       )
    mTEPES.pNodeLon              = Param(                               mTEPES.nd, initialize=pNodeLon.to_dict()                  ,                          doc='Longitude'                      )
    mTEPES.pNodeLat              = Param(                               mTEPES.nd, initialize=pNodeLat.to_dict()                  ,                          doc='Latitude'                       )
    mTEPES.pSystemInertia        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, initialize=pSystemInertia.stack().to_dict()    , within=NonNegativeReals, doc='System inertia'                 )
    mTEPES.pOperReserveUp        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, initialize=pOperReserveUp.stack().to_dict()    , within=NonNegativeReals, doc='Upward   operating reserve'     )
    mTEPES.pOperReserveDw        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, initialize=pOperReserveDw.stack().to_dict()    , within=NonNegativeReals, doc='Downward operating reserve'     )
    mTEPES.pMinPower             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMinPower.stack().to_dict()         , within=NonNegativeReals, doc='Minimum power'                  )
    mTEPES.pMaxPower             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxPower.stack().to_dict()         , within=NonNegativeReals, doc='Maximum power'                  )
    mTEPES.pMinCharge            = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMinCharge.stack().to_dict()        , within=NonNegativeReals, doc='Minimum charge'                 )
    mTEPES.pMaxCharge            = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxCharge.stack().to_dict()        , within=NonNegativeReals, doc='Maximum charge'                 )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxPower2ndBlock.stack().to_dict() , within=NonNegativeReals, doc='Second block power'             )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxCharge2ndBlock.stack().to_dict(), within=NonNegativeReals, doc='Second block charge'            )
    mTEPES.pEnergyInflows        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pEnergyInflows.stack().to_dict()    , within=NonNegativeReals, doc='Energy inflows'                 )
    mTEPES.pEnergyOutflows       = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pEnergyOutflows.stack().to_dict()   , within=NonNegativeReals, doc='Energy outflows'                )
    mTEPES.pMinStorage           = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMinStorage.stack().to_dict()       , within=NonNegativeReals, doc='ESS Minimum stoarage capacity'  )
    mTEPES.pMaxStorage           = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pMaxStorage.stack().to_dict()       , within=NonNegativeReals, doc='ESS Maximum stoarage capacity'  )
    mTEPES.pRatedMaxPower        = Param(                               mTEPES.gg, initialize=pRatedMaxPower.to_dict()            , within=NonNegativeReals, doc='Rated maximum power'            )
    mTEPES.pMustRun              = Param(                               mTEPES.gg, initialize=pMustRun.to_dict()                  , within=Boolean         , doc='must-run unit'                  )
    mTEPES.pInertia              = Param(                               mTEPES.gg, initialize=pInertia.to_dict()                  , within=NonNegativeReals, doc='unit inertia constant'          )
    mTEPES.pAvailability         = Param(                               mTEPES.gg, initialize=pAvailability.to_dict()             , within=UnitInterval    , doc='unit availability',           mutable=True)
    mTEPES.pEFOR                 = Param(                               mTEPES.gg, initialize=pEFOR.to_dict()                     , within=UnitInterval    , doc='EFOR'                           )
    mTEPES.pLinearOperCost       = Param(                               mTEPES.gg, initialize=pLinearOperCost.to_dict()           , within=NonNegativeReals, doc='Linear   variable cost'         )
    mTEPES.pLinearVarCost        = Param(                               mTEPES.gg, initialize=pLinearVarCost.to_dict()            , within=NonNegativeReals, doc='Linear   variable cost'         )
    mTEPES.pLinearOMCost         = Param(                               mTEPES.gg, initialize=pLinearOMCost.to_dict()             , within=NonNegativeReals, doc='Linear   O&M      cost'         )
    mTEPES.pConstantVarCost      = Param(                               mTEPES.gg, initialize=pConstantVarCost.to_dict()          , within=NonNegativeReals, doc='Constant variable cost'         )
    mTEPES.pOperReserveCost      = Param(                               mTEPES.gg, initialize=pOperReserveCost.to_dict()          , within=NonNegativeReals, doc='Operating reserve cost'         )
    mTEPES.pCO2EmissionCost      = Param(                               mTEPES.gg, initialize=pCO2EmissionCost.to_dict()          , within=NonNegativeReals, doc='CO2 Emission      cost'         )
    mTEPES.pStartUpCost          = Param(                               mTEPES.gg, initialize=pStartUpCost.to_dict()              , within=NonNegativeReals, doc='Startup  cost'                  )
    mTEPES.pShutDownCost         = Param(                               mTEPES.gg, initialize=pShutDownCost.to_dict()             , within=NonNegativeReals, doc='Shutdown cost'                  )
    mTEPES.pRampUp               = Param(                               mTEPES.gg, initialize=pRampUp.to_dict()                   , within=NonNegativeReals, doc='Ramp up   rate'                 )
    mTEPES.pRampDw               = Param(                               mTEPES.gg, initialize=pRampDw.to_dict()                   , within=NonNegativeReals, doc='Ramp down rate'                 )
    mTEPES.pUpTime               = Param(                               mTEPES.gg, initialize=pUpTime.to_dict()                   , within=NonNegativeReals, doc='Up   time'                      )
    mTEPES.pDwTime               = Param(                               mTEPES.gg, initialize=pDwTime.to_dict()                   , within=NonNegativeReals, doc='Down time'                      )
    mTEPES.pRatedMaxCharge       = Param(                               mTEPES.gg, initialize=pRatedMaxCharge.to_dict()           , within=NonNegativeReals, doc='Rated maximum charge'           )
    mTEPES.pGenInvestCost        = Param(                               mTEPES.gg, initialize=pGenInvestCost.to_dict()            , within=NonNegativeReals, doc='Generation fixed cost'          )
    mTEPES.pGenRetireCost        = Param(                               mTEPES.gg, initialize=pGenRetireCost.to_dict()            , within=Reals           , doc='Generation fixed retire cost'   )
    mTEPES.pIndBinUnitInvest     = Param(                               mTEPES.gg, initialize=pIndBinUnitInvest.to_dict()         , within=Boolean         , doc='Binary investment decision'     )
    mTEPES.pIndBinUnitRetire     = Param(                               mTEPES.gg, initialize=pIndBinUnitRetire.to_dict()         , within=Boolean         , doc='Binary retirement decision'     )
    mTEPES.pIndBinUnitCommit     = Param(                               mTEPES.gg, initialize=pIndBinUnitCommit.to_dict()         , within=Boolean         , doc='Binary commitment decision'     )
    mTEPES.pIndOperReserve       = Param(                               mTEPES.gg, initialize=pIndOperReserve.to_dict()           , within=Boolean         , doc='Indicator of operating reserve' )
    mTEPES.pEfficiency           = Param(                               mTEPES.gg, initialize=pEfficiency.to_dict()               , within=UnitInterval    , doc='Round-trip efficiency'          )
    mTEPES.pCycleTimeStep        = Param(                               mTEPES.gg, initialize=pCycleTimeStep.to_dict()            , within=NonNegativeReals, doc='ESS Storage cycle'              )
    mTEPES.pOutflowsTimeStep     = Param(                               mTEPES.gg, initialize=pOutflowsTimeStep.to_dict()         , within=NonNegativeReals, doc='ESS Outflows cycle'             )
    mTEPES.pIniInventory         = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pIniInventory.stack().to_dict()     , within=NonNegativeReals, doc='ESS Initial storage',         mutable=True)
    mTEPES.pInitialInventory     = Param(                               mTEPES.gg, initialize=pInitialInventory.to_dict()         , within=NonNegativeReals, doc='ESS Initial storage without load levels'  )
    mTEPES.pStorageType          = Param(                               mTEPES.gg, initialize=pStorageType.to_dict()              , within=Any             , doc='ESS Storage type'               )

    mTEPES.pLineLossFactor       = Param(                               mTEPES.ln, initialize=pLineLossFactor.to_dict()           , within=NonNegativeReals, doc='Loss factor'                    )
    mTEPES.pLineR                = Param(                               mTEPES.ln, initialize=pLineR.to_dict()                    , within=NonNegativeReals, doc='Resistance'                     )
    mTEPES.pLineX                = Param(                               mTEPES.ln, initialize=pLineX.to_dict()                    , within=           Reals, doc='Reactance'                      )
    mTEPES.pLineBsh              = Param(                               mTEPES.ln, initialize=pLineBsh.to_dict()                  , within=NonNegativeReals, doc='Susceptance',                 mutable=True)
    mTEPES.pLineTAP              = Param(                               mTEPES.ln, initialize=pLineTAP.to_dict()                  , within=NonNegativeReals, doc='Tap changer',                 mutable=True)
    mTEPES.pLineLength           = Param(                               mTEPES.ln, initialize=pLineLength.to_dict()               , within=NonNegativeReals, doc='Length',                      mutable=True)
    mTEPES.pLineVoltage          = Param(                               mTEPES.ln, initialize=pLineVoltage.to_dict()              , within=NonNegativeReals, doc='Voltage'                        )
    mTEPES.pLineNTCFrw           = Param(                               mTEPES.ln, initialize=pLineNTCFrw.to_dict()               , within=NonNegativeReals, doc='NTC forward'                    )
    mTEPES.pLineNTCBck           = Param(                               mTEPES.ln, initialize=pLineNTCBck.to_dict()               , within=NonNegativeReals, doc='NTC backward'                   )
    mTEPES.pNetFixedCost         = Param(                               mTEPES.ln, initialize=pNetFixedCost.to_dict()             , within=NonNegativeReals, doc='Network fixed cost'             )
    mTEPES.pIndBinLineInvest     = Param(                               mTEPES.ln, initialize=pIndBinLineInvest.to_dict()         , within=Boolean         , doc='Binary investment decision'     )
    mTEPES.pIndBinLineSwitch     = Param(                               mTEPES.ln, initialize=pIndBinLineSwitch.to_dict()         , within=Boolean         , doc='Binary switching  decision'     )
    mTEPES.pSwOnTime             = Param(                               mTEPES.ln, initialize=pSwitchOnTime.to_dict()             , within=NonNegativeReals, doc='Minimum switching on  time'     )
    mTEPES.pSwOffTime            = Param(                               mTEPES.ln, initialize=pSwitchOffTime.to_dict()            , within=NonNegativeReals, doc='Minimum switching off time'     )
    mTEPES.pBigMFlowBck          = Param(                               mTEPES.ln, initialize=pBigMFlowBck.to_dict()              , within=NonNegativeReals, doc='Maximum backward capacity',   mutable=True)
    mTEPES.pBigMFlowFrw          = Param(                               mTEPES.ln, initialize=pBigMFlowFrw.to_dict()              , within=NonNegativeReals, doc='Maximum forward  capacity',   mutable=True)
    mTEPES.pMaxTheta             = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, initialize=pMaxTheta.stack().to_dict()         , within=NonNegativeReals, doc='Maximum voltage angle',       mutable=True)
    mTEPES.pAngMin               = Param(                               mTEPES.ln, initialize=pAngMin.to_dict()                   , within=Reals,            doc='Minimum phase   angle diff',  mutable=True)
    mTEPES.pAngMax               = Param(                               mTEPES.ln, initialize=pAngMax.to_dict()                   , within=Reals,            doc='Maximum phase   angle diff',  mutable=True)

    # if unit availability = 0 changed to 1
    for g in mTEPES.g:
        if  mTEPES.pAvailability[g]() == 0.0:
            mTEPES.pAvailability[g]   =  1.0

    # if line length = 0 changed to geographical distance
    for ni,nf,cc in mTEPES.la:
        if  mTEPES.pLineLength[ni,nf,cc]() == 0.0:
            mTEPES.pLineLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    # initialize generation output, unit commitment and line switching
    pInitialOutput = pd.DataFrame([[0.0]*len(mTEPES.gg)]*len(mTEPES.sc*mTEPES.p*mTEPES.n), index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n), columns=list(mTEPES.gg))
    pInitialUC     = pd.DataFrame([[0  ]*len(mTEPES.gg)]*len(mTEPES.sc*mTEPES.p*mTEPES.n), index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n), columns=list(mTEPES.gg))
    pInitialSwitch = pd.DataFrame([[0  ]*len(mTEPES.ln)]*len(mTEPES.sc*mTEPES.p*mTEPES.n), index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n), columns=list(mTEPES.ln))

    mTEPES.pInitialOutput        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pInitialOutput.stack().to_dict()    , within=NonNegativeReals, doc='unit initial output',         mutable=True)
    mTEPES.pInitialUC            = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gg, initialize=pInitialUC.stack().to_dict()        , within=Boolean,          doc='unit initial commitment',     mutable=True)
    mTEPES.pInitialSwitch        = Param(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ln, initialize=pInitialSwitch.stack().to_dict()    , within=Boolean,          doc='line initial switching',      mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')


def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()

    #%% variables
    OptModel.vTotalFCost           = Var(                                          within=NonNegativeReals,                                                                                                  doc='total system fixed                   cost      [MEUR]')
    OptModel.vTotalGCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                  doc='total variable generation  operation cost      [MEUR]')
    OptModel.vTotalCCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                  doc='total variable consumption operation cost      [MEUR]')
    OptModel.vTotalECost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                  doc='total system emission                cost      [MEUR]')
    OptModel.vTotalRCost           = Var(mTEPES.sc, mTEPES.p, mTEPES.n,            within=NonNegativeReals,                                                                                                  doc='total system reliability             cost      [MEUR]')
    OptModel.vTotalOutput          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.g , within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,g : (0.0,mTEPES.pMaxPower         [sc,p,n,g ]),                    doc='total output of the unit                         [GW]')
    OptModel.vOutput2ndBlock       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock [sc,p,n,nr]),                    doc='second block of the unit                         [GW]')
    OptModel.vReserveUp            = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock [sc,p,n,nr]),                    doc='upward   operating reserve                       [GW]')
    OptModel.vReserveDown          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,nr: (0.0,mTEPES.pMaxPower2ndBlock [sc,p,n,nr]),                    doc='downward operating reserve                       [GW]')
    OptModel.vEnergyOutflows       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.g , within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,g : (0.0,mTEPES.pMaxPower         [sc,p,n,g ]),                    doc='total outflows of the ESS unit                   [GW]')
    OptModel.vESSInventory         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,es: (mTEPES.pMinStorage[sc,p,n,es],mTEPES.pMaxStorage[sc,p,n,es]), doc='ESS inventory                                   [GWh]')
    OptModel.vESSSpillage          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals,                                                                                                  doc='ESS spillage                                    [GWh]')
    OptModel.vESSTotalCharge       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,es: (0.0,mTEPES.pMaxCharge        [sc,p,n,es]),                    doc='ESS total charge power                           [GW]')
    OptModel.vCharge2ndBlock       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,es: (0.0,mTEPES.pMaxCharge2ndBlock[sc,p,n,es]),                    doc='ESS       charge power                           [GW]')
    OptModel.vESSReserveUp         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,es: (0.0,mTEPES.pMaxCharge2ndBlock[sc,p,n,es]),                    doc='ESS upward   operating reserve                   [GW]')
    OptModel.vESSReserveDown       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,es: (0.0,mTEPES.pMaxCharge2ndBlock[sc,p,n,es]),                    doc='ESS downward operating reserve                   [GW]')
    OptModel.vENS                  = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,nd: (0.0,max(0.0,mTEPES.pDemand   [sc,p,n,nd])),                   doc='energy not served in node                        [GW]')

    if mTEPES.pIndBinGenInvest() == 0:
        OptModel.vGenerationInvest = Var(                               mTEPES.gc, within=UnitInterval,                                                                                                      doc='generation      investment decision exists in a year [0,1]')
    else:
        OptModel.vGenerationInvest = Var(                               mTEPES.gc, within=Binary,                                                                                                            doc='generation      investment decision exists in a year {0,1}')

    if mTEPES.pIndBinGenRetire() == 0:
        OptModel.vGenerationRetire = Var(                               mTEPES.gd, within=UnitInterval,                                                                                                      doc='generation      retirement decision exists in a year [0,1]')
    else:
        OptModel.vGenerationRetire = Var(                               mTEPES.gd, within=Binary,                                                                                                            doc='generation      retirement decision exists in a year {0,1}')

    if mTEPES.pIndBinNetInvest() == 0:
        OptModel.vNetworkInvest    = Var(                               mTEPES.lc, within=UnitInterval,                                                                                                      doc='network         investment decision exists in a year [0,1]')
    else:
        OptModel.vNetworkInvest    = Var(                               mTEPES.lc, within=Binary,                                                                                                            doc='network         investment decision exists in a year {0,1}')

    if mTEPES.pIndBinGenOperat() == 0:
        OptModel.vCommitment       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,     initialize=0.0,                                                                                  doc='commitment of the unit                          [0,1]')
        OptModel.vStartUp          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,     initialize=0.0,                                                                                  doc='startup    of the unit                          [0,1]')
        OptModel.vShutDown         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=UnitInterval,     initialize=0.0,                                                                                  doc='shutdown   of the unit                          [0,1]')
    else:
        OptModel.vCommitment       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,           initialize=0  ,                                                                                  doc='commitment of the unit                          {0,1}')
        OptModel.vStartUp          = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,           initialize=0  ,                                                                                  doc='startup    of the unit                          {0,1}')
        OptModel.vShutDown         = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, within=Binary,           initialize=0  ,                                                                                  doc='shutdown   of the unit                          {0,1}')

    if mTEPES.pIndBinLineCommit() == 0:
        OptModel.vLineCommit       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,     initialize=0.0,                                                                                  doc='line switching      of the line                 [0,1]')
        OptModel.vLineOnState      = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,     initialize=0.0,                                                                                  doc='switching on  state of the line                 [0,1]')
        OptModel.vLineOffState     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=UnitInterval,     initialize=0.0,                                                                                  doc='switching off state of the line                 [0,1]')
    else:
        OptModel.vLineCommit       = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,           initialize=0  ,                                                                                  doc='line switching      of the line                 {0,1}')
        OptModel.vLineOnState      = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,           initialize=0  ,                                                                                  doc='switching on  state of the line                 {0,1}')
        OptModel.vLineOffState     = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Binary,           initialize=0  ,                                                                                  doc='switching off state of the line                 {0,1}')

    # relax binary condition in generation and network investment decisions
    for gc in mTEPES.gc:
        if mTEPES.pIndBinGenInvest() != 0 and mTEPES.pIndBinUnitInvest[gc] == 0:
            OptModel.vGenerationInvest[gc].domain = UnitInterval
    for lc in mTEPES.lc:
        if mTEPES.pIndBinNetInvest() != 0 and mTEPES.pIndBinLineInvest[lc] == 0:
            OptModel.vNetworkInvest   [lc].domain = UnitInterval

    # relax binary condition in generation retirement decisions
    for gd in mTEPES.gd:
        if mTEPES.pIndBinGenRetire() != 0 and mTEPES.pIndBinUnitRetire[gd] == 0:
            OptModel.vGenerationRetire[gd].domain = UnitInterval

    # relax binary condition in unit generation, startup and shutdown decisions
    for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr:
        if mTEPES.pIndBinUnitCommit[nr] == 0:
            OptModel.vCommitment[sc,p,n,nr].domain = UnitInterval
            OptModel.vStartUp   [sc,p,n,nr].domain = UnitInterval
            OptModel.vShutDown  [sc,p,n,nr].domain = UnitInterval

    # maximum value of time step commitment for mutually exclusive non-renewable generators
    OptModel.vMaxCommitment = Var(mTEPES.nr, within=Binary, initialize=0, doc='maximum commitment of the unit                  {0,1}')

    # existing lines are always committed if no decision is modeled
    for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.le:
        if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
            OptModel.vLineCommit    [sc,p,n,ni,nf,cc].fix(1)
            OptModel.vLineOnState   [sc,p,n,ni,nf,cc].fix(0)
            OptModel.vLineOffState  [sc,p,n,ni,nf,cc].fix(0)

    OptModel.vLineLosses           = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, within=NonNegativeReals, bounds=lambda OptModel,sc,p,n,*ll: (0.0,0.5*mTEPES.pLineLossFactor[ll]*max(mTEPES.pLineNTCBck[ll],mTEPES.pLineNTCFrw[ll])), doc='half line losses                                 [GW]')
    OptModel.vFlow                 = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, within=Reals,            bounds=lambda OptModel,sc,p,n,*la: (-mTEPES.pLineNTCBck[la],mTEPES.pLineNTCFrw[la]),                                        doc='flow                                             [GW]')
    OptModel.vTheta                = Var(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, within=Reals,            bounds=lambda OptModel,sc,p,n, nd: (-mTEPES.pMaxTheta[sc,p,n,nd],mTEPES.pMaxTheta[sc,p,n,nd]),                              doc='voltage angle                                   [rad]')

    # fix the must-run units and their output
    for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g :
        # must run units must produce at least their minimum output
        if mTEPES.pMustRun[g] == 1:
            OptModel.vTotalOutput[sc,p,n,g].setlb(mTEPES.pMinPower[sc,p,n,g])
        # if no max power, no total output
        if mTEPES.pMaxPower[sc,p,n,g] == 0.0:
            OptModel.vTotalOutput[sc,p,n,g].fix(0.0)
    #for sc,p,n,r  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r :
    #    if mTEPES.pMinPower[sc,p,n,r] == mTEPES.pMaxPower[sc,p,n,r] and mTEPES.pLinearOMCost[r] == 0.0:
    #        OptModel.vTotalOutput[sc,p,n,r].fix(mTEPES.pMaxPower[sc,p,n,r])

    for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr:
        # must run units or units with no minimum power or ESS units are always committed and must produce at least their minimum output
        # not applicable to mutually exclusive units
        if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPower[sc,p,n,nr] == 0.0 and mTEPES.pConstantVarCost[nr] == 0.0) or nr in mTEPES.es) and sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g) == 0:
            OptModel.vCommitment    [sc,p,n,nr].fix(1)
            OptModel.vStartUp       [sc,p,n,nr].fix(0)
            OptModel.vShutDown      [sc,p,n,nr].fix(0)
        # if min and max power coincide there are neither second block, nor operating reserve
        if  mTEPES.pMaxPower2ndBlock[sc,p,n,nr] ==  0.0:
            OptModel.vOutput2ndBlock[sc,p,n,nr].fix(0.0)
            OptModel.vReserveUp     [sc,p,n,nr].fix(0.0)
            OptModel.vReserveDown   [sc,p,n,nr].fix(0.0)
        if  mTEPES.pIndOperReserve  [       nr] !=  0.0:
            OptModel.vReserveUp     [sc,p,n,nr].fix(0.0)
            OptModel.vReserveDown   [sc,p,n,nr].fix(0.0)

    for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es:
        # ESS with no charge capacity or not storage capacity can't charge
        if mTEPES.pMaxCharge        [sc,p,n,es] == 0.0:
            OptModel.vESSTotalCharge[sc,p,n,es].fix(0.0)
        if mTEPES.pMaxCharge2ndBlock[sc,p,n,es] == 0.0:
            OptModel.vCharge2ndBlock[sc,p,n,es].fix(0.0)
            OptModel.vESSReserveUp  [sc,p,n,es].fix(0.0)
            OptModel.vESSReserveDown[sc,p,n,es].fix(0.0)
        if  mTEPES.pIndOperReserve  [       es] !=  0.0:
            OptModel.vESSReserveUp  [sc,p,n,es].fix(0.0)
            OptModel.vESSReserveDown[sc,p,n,es].fix(0.0)
        if mTEPES.pMaxStorage       [sc,p,n,es] == 0.0:
            OptModel.vESSInventory  [sc,p,n,es].fix(0.0)

    # thermal and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if len(mTEPES.tq):
        mTEPES.go = [k for k in sorted(mTEPES.pLinearVarCost, key=mTEPES.pLinearVarCost.__getitem__) if k not in mTEPES.gq]
    else:
        mTEPES.go = [k for k in sorted(mTEPES.pLinearVarCost, key=mTEPES.pLinearVarCost.__getitem__)]

    for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es:
        if mTEPES.pMaxPower[sc,p,n,es] == 0.0:
            OptModel.vEnergyOutflows[sc,p,n,es].fix(mTEPES.pEnergyOutflows[sc,p,n,es])

    for sc,p,st in mTEPES.scc*mTEPES.pp*mTEPES.stt:
        # activate only scenario, period and load levels to formulate
        mTEPES.del_component(mTEPES.sc)
        mTEPES.del_component(mTEPES.p )
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and sc == scc and mTEPES.pScenProb   [scc])
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.p  = Set(initialize=mTEPES.pp , ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in                p  == pp                              )
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.pDuration and (st,nn) in mTEPES.s2n           )

        if len(mTEPES.n):
            # determine the first load level of each stage
            n1 = next(iter(mTEPES.sc * mTEPES.p * mTEPES.n))
            # commit the units and their output at the first load level of each stage
            pSystemOutput = 0.0
            for nr in mTEPES.nr:
                if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[nr] == 1:
                    mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPower[n1,nr]
                    mTEPES.pInitialUC    [n1,nr] = 1
                    pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

            # determine the initial committed units and their output at the first load level of each stage
            for go in mTEPES.go:
                if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[go] != 1:
                    if go in mTEPES.r:
                        mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPower[n1,go]
                    else:
                        mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPower[n1,go]
                    mTEPES.pInitialUC[n1,go] = 1
                    pSystemOutput = pSystemOutput + mTEPES.pInitialOutput[n1,go]()

            # determine the initial committed lines
            for la in mTEPES.la:
                if la in mTEPES.lc:
                    mTEPES.pInitialSwitch[n1,la] = 0
                else:
                    mTEPES.pInitialSwitch[n1,la] = 1

            # fixing the ESS inventory at the last load level
            for sc,p,es in mTEPES.sc*mTEPES.p*mTEPES.es:
                OptModel.vESSInventory[sc,p,mTEPES.n.last(),es].fix(mTEPES.pInitialInventory[es])

    # activate all the scenarios, periods and load levels again
    mTEPES.del_component(mTEPES.sc)
    mTEPES.del_component(mTEPES.p )
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.sc = Set(initialize=mTEPES.scc, ordered=True, doc='scenarios',   filter=lambda mTEPES,scc: scc in mTEPES.scc and mTEPES.pScenProb   [scc])
    mTEPES.p  = Set(initialize=mTEPES.pp,  ordered=True, doc='periods',     filter=lambda mTEPES,pp : pp  in p == pp                                )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.pDuration                       )

    # fixing the ESS inventory at the end of the following pCycleTimeStep (daily, weekly, monthly), i.e., for daily ESS is fixed at the end of the week, for weekly/monthly ESS is fixed at the end of the year
    for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es:
         if mTEPES.pStorageType[es] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
             OptModel.vESSInventory[sc,p,n,es].fix(mTEPES.pInitialInventory[es])
         if mTEPES.pStorageType[es] == 'Weekly'  and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
             OptModel.vESSInventory[sc,p,n,es].fix(mTEPES.pInitialInventory[es])
         if mTEPES.pStorageType[es] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
             OptModel.vESSInventory[sc,p,n,es].fix(mTEPES.pInitialInventory[es])

    # if no operating reserve is required no variables are needed
    for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            if mTEPES.pOperReserveUp    [sc,p,n,ar] ==  0.0:
                OptModel.vReserveUp     [sc,p,n,nr].fix(0.0)
            if mTEPES.pOperReserveDw    [sc,p,n,ar] ==  0.0:
                OptModel.vReserveDown   [sc,p,n,nr].fix(0.0)
    for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            if mTEPES.pOperReserveUp    [sc,p,n,ar] ==  0.0:
                OptModel.vESSReserveUp  [sc,p,n,es].fix(0.0)
            if mTEPES.pOperReserveDw    [sc,p,n,ar] ==  0.0:
                OptModel.vESSReserveDown[sc,p,n,es].fix(0.0)

    # if there are no energy outflows no variable is needed
    for es in mTEPES.es:
        if sum(mTEPES.pEnergyOutflows[sc,p,n,es] for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n) == 0:
            for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n:
                OptModel.vEnergyOutflows[sc,p,n,es].fix(0.0)

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n:
        OptModel.vTheta[sc,p,n,mTEPES.rf.first()].fix(0.0)

    # fixing the ENS in nodes with no demand
    for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd:
        if mTEPES.pDemand[sc,p,n,nd] == 0.0:
            OptModel.vENS  [sc,p,n,nd].fix(0.0)

    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
