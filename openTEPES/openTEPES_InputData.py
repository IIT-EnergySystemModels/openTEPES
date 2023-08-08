"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 08, 2023
"""

import datetime
import time
import math
import os
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import DataPortal, Set, Param, Var, Binary, NonNegativeReals, NonNegativeIntegers, PositiveReals, PositiveIntegers, Reals, UnitInterval, Any


def InputData(DirName, CaseName, mTEPES, pIndLogConsole):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% reading data from CSV
    dfOption                = pd.read_csv(_path+'/oT_Data_Option_'                +CaseName+'.csv', index_col=[0    ])
    dfParameter             = pd.read_csv(_path+'/oT_Data_Parameter_'             +CaseName+'.csv', index_col=[0    ])
    dfPeriod                = pd.read_csv(_path+'/oT_Data_Period_'                +CaseName+'.csv', index_col=[0    ])
    dfScenario              = pd.read_csv(_path+'/oT_Data_Scenario_'              +CaseName+'.csv', index_col=[0,1  ])
    dfStage                 = pd.read_csv(_path+'/oT_Data_Stage_'                 +CaseName+'.csv', index_col=[0    ])
    dfDuration              = pd.read_csv(_path+'/oT_Data_Duration_'              +CaseName+'.csv', index_col=[0    ])
    dfReserveMargin         = pd.read_csv(_path+'/oT_Data_ReserveMargin_'         +CaseName+'.csv', index_col=[0    ])
    dfDemand                = pd.read_csv(_path+'/oT_Data_Demand_'                +CaseName+'.csv', index_col=[0,1,2])
    dfInertia               = pd.read_csv(_path+'/oT_Data_Inertia_'               +CaseName+'.csv', index_col=[0,1,2])
    dfUpOperatingReserve    = pd.read_csv(_path+'/oT_Data_OperatingReserveUp_'    +CaseName+'.csv', index_col=[0,1,2])
    dfDwOperatingReserve    = pd.read_csv(_path+'/oT_Data_OperatingReserveDown_'  +CaseName+'.csv', index_col=[0,1,2])
    dfGeneration            = pd.read_csv(_path+'/oT_Data_Generation_'            +CaseName+'.csv', index_col=[0    ])
    dfVariableMinPower      = pd.read_csv(_path+'/oT_Data_VariableMinGeneration_' +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxPower      = pd.read_csv(_path+'/oT_Data_VariableMaxGeneration_' +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinCharge     = pd.read_csv(_path+'/oT_Data_VariableMinConsumption_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxCharge     = pd.read_csv(_path+'/oT_Data_VariableMaxConsumption_'+CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinStorage    = pd.read_csv(_path+'/oT_Data_VariableMinStorage_'    +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxStorage    = pd.read_csv(_path+'/oT_Data_VariableMaxStorage_'    +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMinEnergy     = pd.read_csv(_path+'/oT_Data_VariableMinEnergy_'     +CaseName+'.csv', index_col=[0,1,2])
    dfVariableMaxEnergy     = pd.read_csv(_path+'/oT_Data_VariableMaxEnergy_'     +CaseName+'.csv', index_col=[0,1,2])
    dfVariableFuelCost      = pd.read_csv(_path+'/oT_Data_VariableFuelCost_'      +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyInflows         = pd.read_csv(_path+'/oT_Data_EnergyInflows_'         +CaseName+'.csv', index_col=[0,1,2])
    dfEnergyOutflows        = pd.read_csv(_path+'/oT_Data_EnergyOutflows_'        +CaseName+'.csv', index_col=[0,1,2])
    dfNodeLocation          = pd.read_csv(_path+'/oT_Data_NodeLocation_'          +CaseName+'.csv', index_col=[0    ])
    dfNetwork               = pd.read_csv(_path+'/oT_Data_Network_'               +CaseName+'.csv', index_col=[0,1,2])

    try:
        dfReservoir         = pd.read_csv(_path+'/oT_Data_Reservoir_'             +CaseName+'.csv', index_col=[0    ])
        dfVariableMinVolume = pd.read_csv(_path+'/oT_Data_VariableMinVolume_'     +CaseName+'.csv', index_col=[0,1,2])
        dfVariableMaxVolume = pd.read_csv(_path+'/oT_Data_VariableMaxVolume_'     +CaseName+'.csv', index_col=[0,1,2])
        dfHydroInflows      = pd.read_csv(_path+'/oT_Data_HydroInflows_'          +CaseName+'.csv', index_col=[0,1,2])
        dfHydroOutflows     = pd.read_csv(_path+'/oT_Data_HydroOutflows_'         +CaseName+'.csv', index_col=[0,1,2])
        pIndHydroTopology = 1
    except:
        pIndHydroTopology = 0
        print('No Data_Reservoir file found')
        print('No Data_VariableMinVolume and Data_VariableMaxVolume files found')
        print('No Data_HydroInflows and Data_HydroOutflows files found')

    # substitute NaN by 0
    dfOption.fillna               (0  , inplace=True)
    dfParameter.fillna            (0.0, inplace=True)
    dfPeriod.fillna               (0.0, inplace=True)
    dfScenario.fillna             (0.0, inplace=True)
    dfStage.fillna                (0.0, inplace=True)
    dfDuration.fillna             (0  , inplace=True)
    dfReserveMargin.fillna        (0.0, inplace=True)
    dfDemand.fillna               (0.0, inplace=True)
    dfInertia.fillna              (0.0, inplace=True)
    dfUpOperatingReserve.fillna   (0.0, inplace=True)
    dfDwOperatingReserve.fillna   (0.0, inplace=True)
    dfGeneration.fillna           (0.0, inplace=True)
    dfVariableMinPower.fillna     (0.0, inplace=True)
    dfVariableMaxPower.fillna     (0.0, inplace=True)
    dfVariableMinCharge.fillna    (0.0, inplace=True)
    dfVariableMaxCharge.fillna    (0.0, inplace=True)
    dfVariableMinStorage.fillna   (0.0, inplace=True)
    dfVariableMaxStorage.fillna   (0.0, inplace=True)
    dfVariableMinEnergy.fillna    (0.0, inplace=True)
    dfVariableMaxEnergy.fillna    (0.0, inplace=True)
    dfVariableFuelCost.fillna     (0.0, inplace=True)
    dfEnergyInflows.fillna        (0.0, inplace=True)
    dfEnergyOutflows.fillna       (0.0, inplace=True)
    dfNodeLocation.fillna         (0.0, inplace=True)
    dfNetwork.fillna              (0.0, inplace=True)

    if pIndHydroTopology == 1:
        dfReservoir.fillna        (0.0, inplace=True)
        dfVariableMinVolume.fillna(0.0, inplace=True)
        dfVariableMaxVolume.fillna(0.0, inplace=True)
        dfHydroInflows.fillna     (0.0, inplace=True)
        dfHydroOutflows.fillna    (0.0, inplace=True)

    dfReserveMargin         = dfReserveMargin.where     (dfReserveMargin      > 0.0, other=0.0)
    dfInertia               = dfInertia.where           (dfInertia            > 0.0, other=0.0)
    dfUpOperatingReserve    = dfUpOperatingReserve.where(dfUpOperatingReserve > 0.0, other=0.0)
    dfDwOperatingReserve    = dfDwOperatingReserve.where(dfDwOperatingReserve > 0.0, other=0.0)
    dfVariableMinPower      = dfVariableMinPower.where  (dfVariableMinPower   > 0.0, other=0.0)
    dfVariableMaxPower      = dfVariableMaxPower.where  (dfVariableMaxPower   > 0.0, other=0.0)
    dfVariableMinCharge     = dfVariableMinCharge.where (dfVariableMinCharge  > 0.0, other=0.0)
    dfVariableMaxCharge     = dfVariableMaxCharge.where (dfVariableMaxCharge  > 0.0, other=0.0)
    dfVariableMinStorage    = dfVariableMinStorage.where(dfVariableMinStorage > 0.0, other=0.0)
    dfVariableMaxStorage    = dfVariableMaxStorage.where(dfVariableMaxStorage > 0.0, other=0.0)
    dfVariableMinEnergy     = dfVariableMinEnergy.where (dfVariableMinEnergy  > 0.0, other=0.0)
    dfVariableMaxEnergy     = dfVariableMaxEnergy.where (dfVariableMaxEnergy  > 0.0, other=0.0)
    dfVariableFuelCost      = dfVariableFuelCost.where  (dfVariableFuelCost   > 0.0, other=0.0)
    dfEnergyInflows         = dfEnergyInflows.where     (dfEnergyInflows      > 0.0, other=0.0)
    dfEnergyOutflows        = dfEnergyOutflows.where    (dfEnergyOutflows     > 0.0, other=0.0)

    if pIndHydroTopology == 1:
        dfVariableMinVolume = dfVariableMinVolume.where (dfVariableMinVolume  > 0.0, other=0.0)
        dfVariableMaxVolume = dfVariableMaxVolume.where (dfVariableMaxVolume  > 0.0, other=0.0)
        dfHydroInflows      = dfHydroInflows.where      (dfHydroInflows       > 0.0, other=0.0)
        dfHydroOutflows     = dfHydroOutflows.where     (dfHydroOutflows      > 0.0, other=0.0)

    # show some statistics of the data
    if pIndLogConsole == 1:
        print('Reserve margin                        \n', dfReserveMargin.describe       ())
        print('Demand                                \n', dfDemand.describe              ())
        print('Inertia                               \n', dfInertia.describe             ())
        print('Upward   operating reserves           \n', dfUpOperatingReserve.describe  ())
        print('Downward operating reserves           \n', dfDwOperatingReserve.describe  ())
        print('Generation                            \n', dfGeneration.describe          ())
        print('Variable minimum generation           \n', dfVariableMinPower.describe    ())
        print('Variable maximum generation           \n', dfVariableMaxPower.describe    ())
        print('Variable minimum consumption          \n', dfVariableMinCharge.describe   ())
        print('Variable maximum consumption          \n', dfVariableMaxCharge.describe   ())
        print('Variable minimum storage              \n', dfVariableMinStorage.describe  ())
        print('Variable maximum storage              \n', dfVariableMaxStorage.describe  ())
        print('Variable minimum energy               \n', dfVariableMinEnergy.describe   ())
        print('Variable maximum energy               \n', dfVariableMaxEnergy.describe   ())
        print('Variable fuel cost                    \n', dfVariableFuelCost.describe    ())
        print('Energy inflows                        \n', dfEnergyInflows.describe       ())
        print('Energy outflows                       \n', dfEnergyOutflows.describe      ())
        print('Network                               \n', dfNetwork.describe             ())

        if pIndHydroTopology == 1:
            print('Reservoir                         \n', dfReservoir.describe           ())
            print('Variable minimum reservoir volume \n', dfVariableMinVolume.describe   ())
            print('Variable maximum reservoir volume \n', dfVariableMaxVolume.describe   ())
            print('Hydro inflows                     \n', dfHydroInflows.describe        ())
            print('Hydro outflows                    \n', dfHydroOutflows.describe       ())

    #%% reading the sets
    dictSets = DataPortal()
    dictSets.load(filename=_path+'/oT_Dict_Period_'      +CaseName+'.csv', set='p'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Scenario_'    +CaseName+'.csv', set='sc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Stage_'       +CaseName+'.csv', set='st'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_LoadLevel_'   +CaseName+'.csv', set='n'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Generation_'  +CaseName+'.csv', set='g'   , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Technology_'  +CaseName+'.csv', set='gt'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Storage_'     +CaseName+'.csv', set='et'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Node_'        +CaseName+'.csv', set='nd'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Zone_'        +CaseName+'.csv', set='zn'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Area_'        +CaseName+'.csv', set='ar'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Region_'      +CaseName+'.csv', set='rg'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Circuit_'     +CaseName+'.csv', set='cc'  , format='set')
    dictSets.load(filename=_path+'/oT_Dict_Line_'        +CaseName+'.csv', set='lt'  , format='set')

    dictSets.load(filename=_path+'/oT_Dict_NodeToZone_'  +CaseName+'.csv', set='ndzn', format='set')
    dictSets.load(filename=_path+'/oT_Dict_ZoneToArea_'  +CaseName+'.csv', set='znar', format='set')
    dictSets.load(filename=_path+'/oT_Dict_AreaToRegion_'+CaseName+'.csv', set='arrg', format='set')

    mTEPES.pp   = Set(initialize=dictSets['p'   ], ordered=True,  doc='periods', within=PositiveIntegers)
    mTEPES.scc  = Set(initialize=dictSets['sc'  ], ordered=True,  doc='scenarios'                       )
    mTEPES.stt  = Set(initialize=dictSets['st'  ], ordered=True,  doc='stages'                          )
    mTEPES.nn   = Set(initialize=dictSets['n'   ], ordered=True,  doc='load levels'                     )
    mTEPES.gg   = Set(initialize=dictSets['g'   ], ordered=False, doc='units'                           )
    mTEPES.gt   = Set(initialize=dictSets['gt'  ], ordered=False, doc='technologies'                    )
    mTEPES.et   = Set(initialize=dictSets['et'  ], ordered=False, doc='ESS types'                       )
    mTEPES.nd   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.ni   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.nf   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.zn   = Set(initialize=dictSets['zn'  ], ordered=False, doc='zones'                           )
    mTEPES.ar   = Set(initialize=dictSets['ar'  ], ordered=False, doc='areas'                           )
    mTEPES.rg   = Set(initialize=dictSets['rg'  ], ordered=False, doc='regions'                         )
    mTEPES.cc   = Set(initialize=dictSets['cc'  ], ordered=False, doc='circuits'                        )
    mTEPES.c2   = Set(initialize=dictSets['cc'  ], ordered=False, doc='circuits'                        )
    mTEPES.lt   = Set(initialize=dictSets['lt'  ], ordered=False, doc='line types'                      )
    mTEPES.ndzn = Set(initialize=dictSets['ndzn'], ordered=False, doc='node to zone'                    )
    mTEPES.znar = Set(initialize=dictSets['znar'], ordered=False, doc='zone to area'                    )
    mTEPES.arrg = Set(initialize=dictSets['arrg'], ordered=False, doc='area to region'                  )

    try:
        import csv
        def count_lines_in_csv(csv_file_path):
            with open(csv_file_path, 'r', newline='') as file:
                reader = csv.reader(file)
                num_lines = sum(1 for _ in reader)
            return num_lines

        mTEPES.r2h = Set(initialize=[], ordered=False, doc='reservoir to hydro'       )
        mTEPES.h2r = Set(initialize=[], ordered=False, doc='hydro to reservoir'       )
        mTEPES.r2r = Set(initialize=[], ordered=False, doc='reservoir to reservoir'   )
        mTEPES.p2r = Set(initialize=[], ordered=False, doc='pumped-hydro to reservoir')
        mTEPES.r2p = Set(initialize=[], ordered=False, doc='reservoir to pumped-hydro')

        dictSets.load(    filename=_path+'/oT_Dict_Reservoir_'             +CaseName+'.csv', set='rs' , format='set')
        mTEPES.rs      = Set(initialize=dictSets['rs' ], ordered=False, doc='reservoirs'               )
        if count_lines_in_csv(     _path+'/oT_Dict_ReservoirToHydro_'      +CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_ReservoirToHydro_'      +CaseName+'.csv', set='r2h', format='set')
            mTEPES.del_component(mTEPES.r2h)
            mTEPES.r2h = Set(initialize=dictSets['r2h'], ordered=False, doc='reservoir to hydro'       )
        if count_lines_in_csv(     _path+'/oT_Dict_HydroToReservoir_'      +CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_HydroToReservoir_'      +CaseName+'.csv', set='h2r', format='set')
            mTEPES.del_component(mTEPES.h2r)
            mTEPES.h2r = Set(initialize=dictSets['h2r'], ordered=False, doc='hydro to reservoir'       )
        if count_lines_in_csv(     _path+'/oT_Dict_ReservoirToReservoir_'  +CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_ReservoirToReservoir_'  +CaseName+'.csv', set='r2r', format='set')
            mTEPES.del_component(mTEPES.r2r)
            mTEPES.r2r = Set(initialize=dictSets['r2r'], ordered=False, doc='reservoir to reservoir'   )
        if count_lines_in_csv(     _path+'/oT_Dict_PumpedHydroToReservoir_'+CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_PumpedHydroToReservoir_'+CaseName+'.csv', set='p2r', format='set')
            mTEPES.del_component(mTEPES.p2r)
            mTEPES.p2r = Set(initialize=dictSets['p2r'], ordered=False, doc='pumped-hydro to reservoir')
        if count_lines_in_csv(     _path+'/oT_Dict_ReservoirToPumpedHydro_'+CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_ReservoirToPumpedHydro_'+CaseName+'.csv', set='r2p', format='set')
            mTEPES.del_component(mTEPES.r2p)
            mTEPES.r2p = Set(initialize=dictSets['r2p'], ordered=False, doc='reservoir to pumped-hydro')
    except:
        mTEPES.rs  = Set(initialize=[], ordered=False, doc='reservoirs'            )
        mTEPES.rn  = Set(initialize=[], ordered=False, doc='candidate reservoirs'  )
        mTEPES.prc = Set(initialize=[], ordered=False, doc='periods and reservoirs')
        print('No reservoir and hydropower topology dictionaries found')

    #%% parameters
    pIndBinGenInvest       = dfOption   ['IndBinGenInvest'    ][0].astype('int')         # Indicator of binary generation expansion decisions, 0 continuous  - 1 binary - 2 no investment variables
    pIndBinNetInvest       = dfOption   ['IndBinNetInvest'    ][0].astype('int')         # Indicator of binary network    expansion decisions, 0 continuous  - 1 binary - 2 no investment variables
    pIndBinRsrInvest       = dfOption   ['IndBinRsrInvest'    ][0].astype('int')         # Indicator of binary reservoir  expansion decisions, 0 continuous  - 1 binary - 2 no investment variables
    pIndBinGenRetire       = dfOption   ['IndBinGenRetirement'][0].astype('int')         # Indicator of binary generation retirement decisions,0 continuous  - 1 binary - 2 no retirement variables
    pIndBinGenOperat       = dfOption   ['IndBinGenOperat'    ][0].astype('int')         # Indicator of binary generation operation decisions, 0 continuous  - 1 binary
    pIndBinSingleNode      = dfOption   ['IndBinSingleNode'   ][0].astype('int')         # Indicator of single node although with network,     0 network     - 1 single node
    pIndBinGenRamps        = dfOption   ['IndBinGenRamps'     ][0].astype('int')         # Indicator of ramp constraints,                      0 no ramps    - 1 ramp constraints
    pIndBinGenMinTime      = dfOption   ['IndBinGenMinTime'   ][0].astype('int')         # Indicator of minimum up/down time constraints,      0 no min time - 1 min time constraints
    pIndBinLineCommit      = dfOption   ['IndBinLineCommit'   ][0].astype('int')         # Indicator of binary network    switching decisions, 0 continuous  - 1 binary
    pIndBinNetLosses       = dfOption   ['IndBinNetLosses'    ][0].astype('int')         # Indicator of network losses,                        0 lossless    - 1 ohmic losses
    pENSCost               = dfParameter['ENSCost'            ][0] * 1e-3                # cost of energy not served                [MEUR/GWh]
    pCO2Cost               = dfParameter['CO2Cost'            ][0]                       # cost of CO2 emission                     [EUR/t CO2]
    pEconomicBaseYear      = dfParameter['EconomicBaseYear'   ][0]                       # economic base year                       [year]
    pAnnualDiscRate        = dfParameter['AnnualDiscountRate' ][0]                       # annual discount rate                     [p.u.]
    pUpReserveActivation   = dfParameter['UpReserveActivation'][0]                       # upward   reserve activation              [p.u.]
    pDwReserveActivation   = dfParameter['DwReserveActivation'][0]                       # downward reserve activation              [p.u.]
    pMinRatioDwUp          = dfParameter['MinRatioDwUp'       ][0]                       # minimum ratio down up operating reserves [p.u.]
    pMaxRatioDwUp          = dfParameter['MaxRatioDwUp'       ][0]                       # maximum ratio down up operating reserves [p.u.]
    pSBase                 = dfParameter['SBase'              ][0] * 1e-3                # base power                               [GW]
    pReferenceNode         = dfParameter['ReferenceNode'      ][0]                       # reference node
    pTimeStep              = dfParameter['TimeStep'           ][0].astype('int')         # duration of the unit time step           [h]
    # pStageDuration         = dfParameter['StageDuration'      ][0].astype('int')       # duration of each stage                   [h]

    pPeriodWeight          = dfPeriod       ['Weight'        ].astype('int')             # weights of periods                       [p.u.]
    pScenProb              = dfScenario     ['Probability'   ].astype('float')           # probabilities of scenarios               [p.u.]
    pStageWeight           = dfStage        ['Weight'        ].astype('int')             # weights of stages                        [p.u.]
    pDuration              = dfDuration     ['Duration'      ]  * pTimeStep              # duration of load levels                  [h]
    pReserveMargin         = dfReserveMargin['ReserveMargin' ]                           # minimum adequacy reserve margin          [p.u.]
    pLevelToStage          = dfDuration     ['Stage'         ]                           # load levels assignment to stages
    pDemand                = dfDemand            [mTEPES.nd]    * 1e-3                   # demand                                    [GW]
    pSystemInertia         = dfInertia           [mTEPES.ar]                             # inertia                                   [s]
    pOperReserveUp         = dfUpOperatingReserve[mTEPES.ar]    * 1e-3                   # upward   operating reserve                [GW]
    pOperReserveDw         = dfDwOperatingReserve[mTEPES.ar]    * 1e-3                   # downward operating reserve                [GW]
    pVariableMinPower      = dfVariableMinPower  [mTEPES.gg]    * 1e-3                   # dynamic variable minimum power            [GW]
    pVariableMaxPower      = dfVariableMaxPower  [mTEPES.gg]    * 1e-3                   # dynamic variable maximum power            [GW]
    pVariableMinCharge     = dfVariableMinCharge [mTEPES.gg]    * 1e-3                   # dynamic variable minimum charge           [GW]
    pVariableMaxCharge     = dfVariableMaxCharge [mTEPES.gg]    * 1e-3                   # dynamic variable maximum charge           [GW]
    pVariableMinStorage    = dfVariableMinStorage[mTEPES.gg]                             # dynamic variable minimum storage          [GWh]
    pVariableMaxStorage    = dfVariableMaxStorage[mTEPES.gg]                             # dynamic variable maximum storage          [GWh]
    pVariableMinEnergy     = dfVariableMinEnergy [mTEPES.gg]    * 1e-3                   # dynamic variable minimum energy           [GW]
    pVariableMaxEnergy     = dfVariableMaxEnergy [mTEPES.gg]    * 1e-3                   # dynamic variable maximum energy           [GW]
    pVariableFuelCost      = dfVariableFuelCost  [mTEPES.gg]                             # dynamic variable fuel cost                [€/Mcal]
    pEnergyInflows         = dfEnergyInflows     [mTEPES.gg]    * 1e-3                   # dynamic energy inflows                    [GW]
    pEnergyOutflows        = dfEnergyOutflows    [mTEPES.gg]    * 1e-3                   # dynamic energy outflows                   [GW]

    if pIndHydroTopology == 1:
        pVariableMinVolume = dfVariableMinVolume [mTEPES.rs]                             # dynamic variable minimum reservoir volume [hm3]
        pVariableMaxVolume = dfVariableMaxVolume [mTEPES.rs]                             # dynamic variable maximum reservoir volume [hm3]
        pHydroInflows      = dfHydroInflows      [mTEPES.rs]                             # dynamic hydro inflows                     [m3/s]
        pHydroOutflows     = dfHydroOutflows     [mTEPES.rs]                             # dynamic hydro outflows                    [m3/s]

    if pTimeStep > 1:
        # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for the remaining parameters
        if  pDemand.sum().sum()                :
            pDemand                = pDemand.rolling            (pTimeStep).mean()
            pDemand.fillna               (0.0, inplace=True)
        if  pSystemInertia.sum().sum()         :
            pSystemInertia         = pSystemInertia.rolling     (pTimeStep).mean()
            pSystemInertia.fillna        (0.0, inplace=True)
        if  pOperReserveUp.sum().sum()         :
            pOperReserveUp         = pOperReserveUp.rolling     (pTimeStep).mean()
            pOperReserveUp.fillna        (0.0, inplace=True)
        if  pOperReserveDw.sum().sum()         :
            pOperReserveDw         = pOperReserveDw.rolling     (pTimeStep).mean()
            pOperReserveDw.fillna        (0.0, inplace=True)
        if  pVariableMinPower.sum().sum()      :
            pVariableMinPower      = pVariableMinPower.rolling  (pTimeStep).mean()
            pVariableMinPower.fillna     (0.0, inplace=True)
        if  pVariableMaxPower.sum().sum()      :
            pVariableMaxPower      = pVariableMaxPower.rolling  (pTimeStep).mean()
            pVariableMaxPower.fillna     (0.0, inplace=True)
        if  pVariableMinCharge.sum().sum()     :
            pVariableMinCharge     = pVariableMinCharge.rolling (pTimeStep).mean()
            pVariableMinCharge.fillna    (0.0, inplace=True)
        if  pVariableMaxCharge.sum().sum()     :
            pVariableMaxCharge     = pVariableMaxCharge.rolling (pTimeStep).mean()
            pVariableMaxCharge.fillna    (0.0, inplace=True)
        if  pVariableMinStorage.sum().sum()    :
            pVariableMinStorage    = pVariableMinStorage.rolling(pTimeStep).mean()
            pVariableMinStorage.fillna   (0.0, inplace=True)
        if  pVariableMaxStorage.sum().sum()    :
            pVariableMaxStorage    = pVariableMaxStorage.rolling(pTimeStep).mean()
            pVariableMaxStorage.fillna   (0.0, inplace=True)
        if  pVariableMinEnergy.sum().sum()     :
            pVariableMinEnergy     = pVariableMinEnergy.rolling (pTimeStep).mean()
            pVariableMinEnergy.fillna    (0.0, inplace=True)
        if  pVariableMaxEnergy.sum().sum()     :
            pVariableMaxEnergy     = pVariableMaxEnergy.rolling (pTimeStep).mean()
            pVariableMaxEnergy.fillna    (0.0, inplace=True)
        if  pVariableFuelCost.sum().sum()      :
            pVariableFuelCost      = pVariableFuelCost.rolling  (pTimeStep).mean()
            pVariableFuelCost.fillna     (0.0, inplace=True)
        if  pEnergyInflows.sum().sum()         :
            pEnergyInflows         = pEnergyInflows.rolling     (pTimeStep).mean()
            pEnergyInflows.fillna        (0.0, inplace=True)
        if  pEnergyOutflows.sum().sum()        :
            pEnergyOutflows        = pEnergyOutflows.rolling    (pTimeStep).mean()
            pEnergyOutflows.fillna       (0.0, inplace=True)
        if pIndHydroTopology == 1:
            if  pVariableMinVolume.sum().sum() :
                pVariableMinVolume = pVariableMinVolume.rolling (pTimeStep).mean()
                pVariableMinVolume.fillna(0.0, inplace=True)
            if  pVariableMaxVolume.sum().sum() :
                pVariableMaxVolume = pVariableMaxVolume.rolling (pTimeStep).mean()
                pVariableMaxVolume.fillna(0.0, inplace=True)
            if  pHydroInflows.sum().sum()      :
                pHydroInflows       = pHydroInflows.rolling     (pTimeStep).mean()
                pHydroInflows.fillna     (0.0, inplace=True)
            if  pHydroOutflows.sum().sum()     :
                pHydroOutflows      = pHydroOutflows.rolling    (pTimeStep).mean()
                pHydroOutflows.fillna    (0.0, inplace=True)

        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for i in range(pTimeStep-2,-1,-1):
            pDuration.iloc[[range(i,len(mTEPES.nn),pTimeStep)]] = 0

    #%% generation parameters
    pGenToNode            = dfGeneration  ['Node'                ]                                                                            # generator location in node
    pGenToTechnology      = dfGeneration  ['Technology'          ]                                                                            # generator association to technology
    pGenToExclusiveGen    = dfGeneration  ['MutuallyExclusive'   ]                                                                            # mutually exclusive generator
    pIndBinUnitInvest     = dfGeneration  ['BinaryInvestment'    ]                                                                            # binary unit investment decision             [Yes]
    pIndBinUnitRetire     = dfGeneration  ['BinaryRetirement'    ]                                                                            # binary unit retirement decision             [Yes]
    pIndBinUnitCommit     = dfGeneration  ['BinaryCommitment'    ]                                                                            # binary unit commitment decision             [Yes]
    pIndBinStorInvest     = dfGeneration  ['StorageInvestment'   ]                                                                            # storage linked to generation investment     [Yes]
    pIndOperReserve       = dfGeneration  ['NoOperatingReserve'  ]                                                                            # no contribution to operating reserve        [Yes]
    pMustRun              = dfGeneration  ['MustRun'             ]                                                                            # must-run unit                               [Yes]
    pInertia              = dfGeneration  ['Inertia'             ]                                                                            # inertia constant                            [s]
    pPeriodIniGen         = dfGeneration  ['InitialPeriod'       ]                                                                            # initial period                              [year]
    pPeriodFinGen         = dfGeneration  ['FinalPeriod'         ]                                                                            # final   period                              [year]
    pAvailability         = dfGeneration  ['Availability'        ]                                                                            # unit availability for adequacy              [p.u.]
    pEFOR                 = dfGeneration  ['EFOR'                ]                                                                            # EFOR                                        [p.u.]
    pRatedMinPower        = dfGeneration  ['MinimumPower'        ] * 1e-3 * (1.0-dfGeneration['EFOR'])                                        # rated minimum power                         [GW]
    pRatedMaxPower        = dfGeneration  ['MaximumPower'        ] * 1e-3 * (1.0-dfGeneration['EFOR'])                                        # rated maximum power                         [GW]
    pRatedLinearFuelCost  = dfGeneration  ['LinearTerm'          ] * 1e-3 *      dfGeneration['FuelCost']                                     # fuel     term variable cost                 [MEUR/GWh]
    pRatedConstantVarCost = dfGeneration  ['ConstantTerm'        ] * 1e-6 *      dfGeneration['FuelCost']                                     # constant term variable cost                 [MEUR/h]
    pLinearOMCost         = dfGeneration  ['OMVariableCost'      ] * 1e-3                                                                     # O&M      term variable cost                 [MEUR/GWh]
    pOperReserveCost      = dfGeneration  ['OperReserveCost'     ] * 1e-3                                                                     # operating reserve      cost                 [MEUR/GW]
    pStartUpCost          = dfGeneration  ['StartUpCost'         ]                                                                            # startup  cost                               [MEUR]
    pShutDownCost         = dfGeneration  ['ShutDownCost'        ]                                                                            # shutdown cost                               [MEUR]
    pRampUp               = dfGeneration  ['RampUp'              ] * 1e-3                                                                     # ramp up   rate                              [GW/h]
    pRampDw               = dfGeneration  ['RampDown'            ] * 1e-3                                                                     # ramp down rate                              [GW/h]
    pCO2EmissionCost      = dfGeneration  ['CO2EmissionRate'     ] * 1e-3 * pCO2Cost                                                          # emission  cost                              [MEUR/GWh]
    pCO2EmissionRate      = dfGeneration  ['CO2EmissionRate'     ]                                                                            # emission  rate                              [tCO2/MWh]
    pUpTime               = dfGeneration  ['UpTime'              ]                                                                            # minimum up    time                          [h]
    pDwTime               = dfGeneration  ['DownTime'            ]                                                                            # minimum down  time                          [h]
    pShiftTime            = dfGeneration  ['ShiftTime'           ]                                                                            # maximum shift time for DSM                  [h]
    pGenInvestCost        = dfGeneration  ['FixedInvestmentCost' ] *        dfGeneration['FixedChargeRate']                                   # generation fixed cost                       [MEUR]
    pGenRetireCost        = dfGeneration  ['FixedRetirementCost' ] *        dfGeneration['FixedChargeRate']                                   # generation fixed retirement cost            [MEUR]
    pRatedMinCharge       = dfGeneration  ['MinimumCharge'       ] * 1e-3                                                                     # rated minimum ESS charge                    [GW]
    pRatedMaxCharge       = dfGeneration  ['MaximumCharge'       ] * 1e-3                                                                     # rated maximum ESS charge                    [GW]
    pRatedMinStorage      = dfGeneration  ['MinimumStorage'      ]                                                                            # rated minimum ESS storage                   [GWh]
    pRatedMaxStorage      = dfGeneration  ['MaximumStorage'      ]                                                                            # rated maximum ESS storage                   [GWh]
    pInitialInventory     = dfGeneration  ['InitialStorage'      ]                                                                            # initial       ESS storage                   [GWh]
    pProductionFunction   = dfGeneration  ['ProductionFunction'  ]                                                                            # production function of hydropower plant     [kWh/m3]
    pEfficiency           = dfGeneration  ['Efficiency'          ]                                                                            #         ESS round-trip efficiency           [p.u.]
    pStorageType          = dfGeneration  ['StorageType'         ]                                                                            #         ESS storage  type
    pOutflowsType         = dfGeneration  ['OutflowsType'        ]                                                                            #         ESS outflows type
    pEnergyType           = dfGeneration  ['EnergyType'          ]                                                                            #         unit  energy type
    pRMaxReactivePower    = dfGeneration  ['MaximumReactivePower'] * 1e-3                                                                     # rated maximum reactive power                [Gvar]
    pGenLoInvest          = dfGeneration  ['InvestmentLo'        ]                                                                            # Lower bound of the investment decision      [p.u.]
    pGenUpInvest          = dfGeneration  ['InvestmentUp'        ]                                                                            # Upper bound of the investment decision      [p.u.]
    pGenLoRetire          = dfGeneration  ['RetirementLo'        ]                                                                            # Lower bound of the retirement decision      [p.u.]
    pGenUpRetire          = dfGeneration  ['RetirementUp'        ]                                                                            # Upper bound of the retirement decision      [p.u.]

    pRatedLinearOperCost  = pRatedLinearFuelCost + pCO2EmissionCost
    pRatedLinearVarCost   = pRatedLinearFuelCost + pLinearOMCost

    if pIndHydroTopology == 1:
        pReservoirType    = dfReservoir   ['StorageType'         ]                                                                            #               reservoir type
        pWaterOutfType    = dfReservoir   ['OutflowsType'        ]                                                                            #           water ourflow type
        pRatedMinVolume   = dfReservoir   ['MinimumStorage'      ]                                                                            # rated minimum reservoir volume             [hm3]
        pRatedMaxVolume   = dfReservoir   ['MaximumStorage'      ]                                                                            # rated maximum reservoir volume             [hm3]
        pInitialVolume    = dfReservoir   ['InitialStorage'      ]                                                                            # initial       reservoir volume             [hm3]
        pRsrInvestCost    = dfReservoir   ['FixedInvestmentCost' ] *        dfReservoir['FixedChargeRate']                                    # reservoir fixed cost                       [MEUR]
        pPeriodIniRsr     = dfReservoir   ['InitialPeriod'       ]                                                                            # initial period                             [year]
        pPeriodFinRsr     = dfReservoir   ['FinalPeriod'         ]                                                                            # final   period                             [year]

    pNodeLat              = dfNodeLocation['Latitude'            ]                                                                            # node latitude                               [º]
    pNodeLon              = dfNodeLocation['Longitude'           ]                                                                            # node longitude                              [º]

    pLineType             = dfNetwork     ['LineType'            ]                                                                            # line type
    pLineLength           = dfNetwork     ['Length'              ]                                                                            # line length                                 [km]
    pLineVoltage          = dfNetwork     ['Voltage'             ]                                                                            # line voltage                                [kV]
    pPeriodIniNet         = dfNetwork     ['InitialPeriod'       ]                                                                            # initial period
    pPeriodFinNet         = dfNetwork     ['FinalPeriod'         ]                                                                            # final   period
    pLineLossFactor       = dfNetwork     ['LossFactor'          ]                                                                            # loss factor                                 [p.u.]
    pLineR                = dfNetwork     ['Resistance'          ]                                                                            # resistance                                  [p.u.]
    pLineX                = dfNetwork     ['Reactance'           ].sort_index()                                                               # reactance                                   [p.u.]
    pLineBsh              = dfNetwork     ['Susceptance'         ]                                                                            # susceptance                                 [p.u.]
    pLineTAP              = dfNetwork     ['Tap'                 ]                                                                            # tap changer                                 [p.u.]
    pLineNTCFrw           = dfNetwork     ['TTC'                 ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in forward  direction [GW]
    pLineNTCBck           = dfNetwork     ['TTCBck'              ] * 1e-3 * dfNetwork['SecurityFactor' ]                                      # net transfer capacity in backward direction [GW]
    pNetFixedCost         = dfNetwork     ['FixedInvestmentCost' ] *        dfNetwork['FixedChargeRate']                                      # network    fixed cost                       [MEUR]
    pIndBinLineSwitch     = dfNetwork     ['Switching'           ]                                                                            # binary line switching  decision             [Yes]
    pIndBinLineInvest     = dfNetwork     ['BinaryInvestment'    ]                                                                            # binary line investment decision             [Yes]
    pSwitchOnTime         = dfNetwork     ['SwOnTime'            ].astype('int')                                                              # minimum on  time                            [h]
    pSwitchOffTime        = dfNetwork     ['SwOffTime'           ].astype('int')                                                              # minimum off time                            [h]
    pAngMin               = dfNetwork     ['AngMin'              ] * math.pi / 180                                                            # Min phase angle difference                  [rad]
    pAngMax               = dfNetwork     ['AngMax'              ] * math.pi / 180                                                            # Max phase angle difference                  [rad]
    pNetLoInvest          = dfNetwork     ['InvestmentLo'        ]                                                                            # Lower bound of the investment decision      [p.u.]
    pNetUpInvest          = dfNetwork     ['InvestmentUp'        ]                                                                            # Upper bound of the investment decision      [p.u.]

    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    pLineNTCBck     = pLineNTCBck.where(pLineNTCBck   > 0.0, other=pLineNTCFrw)
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    pLineNTCFrw     = pLineNTCFrw.where(pLineNTCFrw   > 0.0, other=pLineNTCBck)
    # replace pGenUpInvest = 0.0 by 1.0
    pGenUpInvest    = pGenUpInvest.where(pGenUpInvest > 0.0, other=1.0        )
    # replace pGenUpRetire = 0.0 by 1.0
    pGenUpRetire    = pGenUpRetire.where(pGenUpRetire > 0.0, other=1.0        )
    # replace pNetUpInvest = 0.0 by 1.0
    pNetUpInvest    = pNetUpInvest.where(pNetUpInvest > 0.0, other=1.0        )

    # minimum up- and downtime converted to an integer number of time steps
    pSwitchOnTime  = round(pSwitchOnTime /pTimeStep).astype('int')
    pSwitchOffTime = round(pSwitchOffTime/pTimeStep).astype('int')

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')

    #%% Getting the branches from the network data
    sBr = [(ni,nf) for (ni,nf,cc) in dfNetwork.index]
    # Dropping duplicate keys
    sBrList = [(ni,nf) for n,(ni,nf) in enumerate(sBr) if (ni,nf) not in sBr[:n]]

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the lines (la), candidate lines (lc), candidate DC lines (cd), existing DC lines (cd), lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.p      = Set(initialize=mTEPES.pp,          ordered=True , doc='periods'              , filter=lambda mTEPES,pp      :  pp     in mTEPES.pp  and pPeriodWeight       [pp] >  0.0)
    mTEPES.sc     = Set(initialize=mTEPES.scc,         ordered=True , doc='scenarios'            , filter=lambda mTEPES,scc     :  scc    in mTEPES.scc                                    )
    mTEPES.ps     = Set(initialize=mTEPES.p*mTEPES.sc, ordered=True , doc='periods/scenarios'    , filter=lambda mTEPES,p,sc    :  (p,sc) in mTEPES.p*mTEPES.sc and pScenProb [p,sc] >  0.0)
    mTEPES.st     = Set(initialize=mTEPES.stt,         ordered=True , doc='stages'               , filter=lambda mTEPES,stt     :  stt    in mTEPES.stt and pStageWeight       [stt] >  0.0)
    mTEPES.n      = Set(initialize=mTEPES.nn,          ordered=True , doc='load levels'          , filter=lambda mTEPES,nn      :  nn     in mTEPES.nn  and pDuration           [nn] >  0  )
    mTEPES.n2     = Set(initialize=mTEPES.nn,          ordered=True , doc='load levels'          , filter=lambda mTEPES,nn      :  nn     in mTEPES.nn  and pDuration           [nn] >  0  )
    mTEPES.g      = Set(initialize=mTEPES.gg,          ordered=False, doc='generating      units', filter=lambda mTEPES,gg      :  gg     in mTEPES.gg  and (pRatedMaxPower     [gg] >  0.0 or                                  pRatedMaxCharge[gg] > 0.0) and pPeriodIniGen[gg] <= mTEPES.p.last() and pPeriodFinGen[gg] >= mTEPES.p.first() and pGenToNode.reset_index().set_index(['index']).isin(mTEPES.nd)['Node'][gg])  # excludes generators with empty node
    mTEPES.t      = Set(initialize=mTEPES.g ,          ordered=False, doc='thermal         units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and pRatedLinearOperCost[g ] >  0.0)
    mTEPES.re     = Set(initialize=mTEPES.g ,          ordered=False, doc='RES             units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and pRatedLinearOperCost[g ] == 0.0 and pRatedMaxStorage[g] == 0.0                                and pProductionFunction[g] == 0.0)
    mTEPES.es     = Set(initialize=mTEPES.g ,          ordered=False, doc='ESS             units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and                                    (pRatedMaxStorage[g] >  0.0   or pRatedMaxCharge[g] > 0.0) and pProductionFunction[g] == 0.0)
    mTEPES.h      = Set(initialize=mTEPES.g ,          ordered=False, doc='Hydro           units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and                                                                                                   pProductionFunction[g]  > 0.0)
    mTEPES.gc     = Set(initialize=mTEPES.g ,          ordered=False, doc='candidate       units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and pGenInvestCost      [g ] >  0.0)
    mTEPES.gd     = Set(initialize=mTEPES.g ,          ordered=False, doc='retirement      units', filter=lambda mTEPES,g       :  g      in mTEPES.g   and pGenRetireCost      [g ] != 0.0)
    mTEPES.ec     = Set(initialize=mTEPES.es,          ordered=False, doc='candidate   ESS units', filter=lambda mTEPES,es      :  es     in mTEPES.es  and pGenInvestCost      [es] >  0.0)
    mTEPES.br     = Set(initialize=sBrList,            ordered=False, doc='all input branches'                                                                                             )
    mTEPES.ln     = Set(initialize=dfNetwork.index,    ordered=False, doc='all input lines'                                                                                                )
    mTEPES.la     = Set(initialize=mTEPES.ln,          ordered=False, doc='all real        lines', filter=lambda mTEPES,*ln     :  ln     in mTEPES.ln  and pLineX              [ln] != 0.0 and pLineNTCFrw[ln] > 0.0 and pLineNTCBck[ln] > 0.0 and pPeriodIniNet[ln] <= mTEPES.p.last() and pPeriodFinNet[ln] >= mTEPES.p.first())
    mTEPES.ls     = Set(initialize=mTEPES.la,          ordered=False, doc='all real switch lines', filter=lambda mTEPES,*la     :  la     in mTEPES.la  and pIndBinLineSwitch   [la])
    mTEPES.lc     = Set(initialize=mTEPES.la,          ordered=False, doc='candidate       lines', filter=lambda mTEPES,*la     :  la     in mTEPES.la  and pNetFixedCost       [la] >  0.0)
    mTEPES.cd     = Set(initialize=mTEPES.la,          ordered=False, doc='             DC lines', filter=lambda mTEPES,*la     :  la     in mTEPES.la  and pNetFixedCost       [la] >  0.0 and pLineType[la] == 'DC')
    mTEPES.ed     = Set(initialize=mTEPES.la,          ordered=False, doc='             DC lines', filter=lambda mTEPES,*la     :  la     in mTEPES.la  and pNetFixedCost       [la] == 0.0 and pLineType[la] == 'DC')
    mTEPES.ll     = Set(initialize=mTEPES.la,          ordered=False, doc='loss            lines', filter=lambda mTEPES,*la     :  la     in mTEPES.la  and pLineLossFactor     [la] >  0.0 and pIndBinNetLosses > 0 )
    mTEPES.rf     = Set(initialize=mTEPES.nd,          ordered=True , doc='reference node'       , filter=lambda mTEPES,nd      :  nd     in                pReferenceNode                 )
    mTEPES.gq     = Set(initialize=mTEPES.gg,          ordered=False, doc='gen    reactive units', filter=lambda mTEPES,gg      :  gg     in mTEPES.gg  and pRMaxReactivePower  [gg] >  0.0 and                                                     pPeriodIniGen[gg] <= mTEPES.p.last() and pPeriodFinGen[gg] >= mTEPES.p.first())
    mTEPES.sq     = Set(initialize=mTEPES.gg,          ordered=False, doc='syn    reactive units', filter=lambda mTEPES,gg      :  gg     in mTEPES.gg  and pRMaxReactivePower  [gg] >  0.0 and pGenToTechnology[gg] == 'SynchronousCondenser'  and pPeriodIniGen[gg] <= mTEPES.p.last() and pPeriodFinGen[gg] >= mTEPES.p.first())
    mTEPES.sqc    = Set(initialize=mTEPES.sq,          ordered=False, doc='syn    reactive cand '                                                                                          )
    mTEPES.shc    = Set(initialize=mTEPES.sq,          ordered=False, doc='shunt           cand '                                                                                          )
    if pIndHydroTopology == 1:
        mTEPES.rn = Set(initialize=mTEPES.rs,          ordered=False, doc='candidate  reservoirs', filter=lambda mTEPES,rs      :  rs     in mTEPES.rs  and pRsrInvestCost      [rs] >  0.0 and                                                     pPeriodIniRsr[rs] <= mTEPES.p.last() and pPeriodFinRsr[rs] >= mTEPES.p.first())

    # non-RES units, they can be committed and also contribute to the operating reserves
    mTEPES.nr = mTEPES.g - mTEPES.re

    # machines able to provide reactive power
    mTEPES.tq = mTEPES.gq - mTEPES.sq

    # existing lines (le)
    mTEPES.le = mTEPES.la - mTEPES.lc

    # instrumental sets
    mTEPES.psc       = [(p,sc     )       for p,sc            in mTEPES.p  *mTEPES.sc]
    mTEPES.psg       = [(p,sc,  g )       for p,sc,  g        in mTEPES.ps *mTEPES.g ]
    mTEPES.psnr      = [(p,sc,  nr)       for p,sc,  nr       in mTEPES.ps *mTEPES.nr]
    mTEPES.pses      = [(p,sc,  es)       for p,sc,  es       in mTEPES.ps *mTEPES.es]
    mTEPES.psn       = [(p,sc,n   )       for p,sc,n          in mTEPES.ps *mTEPES.n ]
    mTEPES.psng      = [(p,sc,n,g )       for p,sc,n,g        in mTEPES.psn*mTEPES.g ]
    mTEPES.psngg     = [(p,sc,n,gg)       for p,sc,n,gg       in mTEPES.psn*mTEPES.gg]
    mTEPES.psngc     = [(p,sc,n,gc)       for p,sc,n,gc       in mTEPES.psn*mTEPES.gc]
    mTEPES.psnre     = [(p,sc,n,re)       for p,sc,n,re       in mTEPES.psn*mTEPES.re]
    mTEPES.psnnr     = [(p,sc,n,nr)       for p,sc,n,nr       in mTEPES.psn*mTEPES.nr]
    mTEPES.psnes     = [(p,sc,n,es)       for p,sc,n,es       in mTEPES.psn*mTEPES.es]
    mTEPES.psnec     = [(p,sc,n,ec)       for p,sc,n,ec       in mTEPES.psn*mTEPES.ec]
    mTEPES.psnnd     = [(p,sc,n,nd)       for p,sc,n,nd       in mTEPES.psn*mTEPES.nd]
    mTEPES.psnar     = [(p,sc,n,ar)       for p,sc,n,ar       in mTEPES.psn*mTEPES.ar]
    mTEPES.psngt     = [(p,sc,n,gt)       for p,sc,n,gt       in mTEPES.psn*mTEPES.gt]

    mTEPES.psnla     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.la]
    mTEPES.psnle     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.le]
    mTEPES.psnln     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ln]
    mTEPES.psnll     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ll]
    mTEPES.psnls     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ls]

    mTEPES.pg        = [(p,     g       ) for p,     g        in mTEPES.p  *mTEPES.g ]
    mTEPES.pgc       = [(p,     gc      ) for p,     gc       in mTEPES.p  *mTEPES.gc]
    mTEPES.pes       = [(p,     es      ) for p,     es       in mTEPES.p  *mTEPES.es]
    mTEPES.pgd       = [(p,     gd      ) for p,     gd       in mTEPES.p  *mTEPES.gd]
    mTEPES.par       = [(p,     ar      ) for p,     ar       in mTEPES.p  *mTEPES.ar]
    mTEPES.pla       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.la]
    mTEPES.plc       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.lc]
    mTEPES.pll       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ll]

    if pIndHydroTopology == 1:
        mTEPES.psrs  = [(p,sc,  rs)       for p,sc,  rs       in mTEPES.ps *mTEPES.rs]
        mTEPES.psnrs = [(p,sc,n,rs)       for p,sc,n,rs       in mTEPES.psn*mTEPES.rs]
        mTEPES.psnrc = [(p,sc,n,rc)       for p,sc,n,rc       in mTEPES.psn*mTEPES.rn]
        mTEPES.prs   = [(p,     rs)       for p,     rs       in mTEPES.p  *mTEPES.rs]
        mTEPES.prc   = [(p,     rc)       for p,     rc       in mTEPES.p  *mTEPES.rn]

    # assigning a node to an area
    mTEPES.ndar = [(nd,ar) for (nd,zn,ar) in mTEPES.ndzn*mTEPES.ar if (zn,ar) in mTEPES.znar]

    # assigning a line to an area. Both nodes are in the same area. Cross-area lines not included
    mTEPES.laar = [(ni,nf,cc,ar) for ni,nf,cc,ar in mTEPES.la*mTEPES.ar if (ni,ar) in mTEPES.ndar and (nf,ar) in mTEPES.ndar]

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
    pIndBinStorInvest = pIndBinStorInvest.map(idxDict)
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
    mTEPES.led = Set(initialize=mTEPES.le, ordered=False, doc='DC existing  lines and non-switchable lines', filter=lambda mTEPES,*le: le in mTEPES.le and  pIndBinLineSwitch[le] == 0                             and     pLineType[le] == 'DC')
    # define DC candidate lines and     switchable lines
    mTEPES.lcd = Set(initialize=mTEPES.la, ordered=False, doc='DC candidate lines and     switchable lines', filter=lambda mTEPES,*la: la in mTEPES.la and (pIndBinLineSwitch[la] == 1 or pNetFixedCost[la] > 0.0) and     pLineType[la] == 'DC')

    mTEPES.lad = mTEPES.led | mTEPES.lcd

    # line type
    pLineType = pLineType.reset_index().set_index(['level_0','level_1','level_2','LineType'])

    mTEPES.pLineType = Set(initialize=pLineType.index, ordered=False, doc='line type')

    #%% inverse index load level to stage
    pStageToLevel = pLevelToStage.reset_index().set_index('Stage').set_axis(['LoadLevel'], axis=1)[['LoadLevel']]
    pStageToLevel = pStageToLevel.loc[pStageToLevel['LoadLevel'].isin(mTEPES.n)]
    pStage2Level  = pStageToLevel.reset_index().set_index(['Stage','LoadLevel'])

    mTEPES.s2n = Set(initialize=pStage2Level.index, ordered=False, doc='load level to stage')

    if pAnnualDiscRate == 0.0:
        pDiscountFactor = pd.Series([                        pPeriodWeight[p]                                                                                          for p in mTEPES.p], index=mTEPES.p)
    else:
        pDiscountFactor = pd.Series([((1.0+pAnnualDiscRate)**pPeriodWeight[p]-1.0) / (pAnnualDiscRate*(1.0+pAnnualDiscRate)**(pPeriodWeight[p]-1+p-pEconomicBaseYear)) for p in mTEPES.p], index=mTEPES.p)

    mTEPES.pLoadLevelWeight = Param(mTEPES.n, initialize=0.0, within=NonNegativeIntegers, doc='Load level weight', mutable=True)
    for st,n in mTEPES.s2n:
        mTEPES.pLoadLevelWeight[n] = pStageWeight[st]

    #%% inverse index node to generator
    pNodeToGen = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1)[['Generator']]
    pNodeToGen = pNodeToGen.loc[pNodeToGen['Generator'].isin(mTEPES.g)]
    pNode2Gen  = pNodeToGen.reset_index().set_index(['Node', 'Generator'])

    mTEPES.n2g = Set(initialize=pNode2Gen.index, ordered=False, doc='node   to generator')

    pZone2Gen   = [(zn,g) for (nd,g,zn      ) in mTEPES.n2g*mTEPES.zn             if (nd,zn) in mTEPES.ndzn                           ]
    pArea2Gen   = [(ar,g) for (nd,g,zn,ar   ) in mTEPES.n2g*mTEPES.znar           if (nd,zn) in mTEPES.ndzn                           ]
    pRegion2Gen = [(rg,g) for (nd,g,zn,ar,rg) in mTEPES.n2g*mTEPES.znar*mTEPES.rg if (nd,zn) in mTEPES.ndzn and [ar,rg] in mTEPES.arrg]

    mTEPES.z2g = Set(initialize=mTEPES.zn*mTEPES.g, ordered=False, doc='zone   to generator', filter=lambda mTEPES,zn,g: (zn,g) in pZone2Gen  )
    mTEPES.a2g = Set(initialize=mTEPES.ar*mTEPES.g, ordered=False, doc='area   to generator', filter=lambda mTEPES,ar,g: (ar,g) in pArea2Gen  )
    mTEPES.r2g = Set(initialize=mTEPES.rg*mTEPES.g, ordered=False, doc='region to generator', filter=lambda mTEPES,rg,g: (rg,g) in pRegion2Gen)

    #%% inverse index generator to technology
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(mTEPES.g)]
    pTechnology2Gen  = pTechnologyToGen.reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=pTechnology2Gen.index, ordered=False, doc='technology to generator')

    # ESS and RES technologies
    mTEPES.ot = Set(initialize=mTEPES.gt, ordered=False, doc='ESS technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for es in mTEPES.es if (gt,es) in mTEPES.t2g))
    mTEPES.ht = Set(initialize=mTEPES.gt, ordered=False, doc='ESS technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for h  in mTEPES.h  if (gt,h ) in mTEPES.t2g))
    mTEPES.rt = Set(initialize=mTEPES.gt, ordered=False, doc='RES technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for re in mTEPES.re if (gt,re) in mTEPES.t2g))

    mTEPES.psot  = [(p,sc,  ot) for p,sc,  ot in mTEPES.ps *mTEPES.ot]
    mTEPES.psrt  = [(p,sc,  rt) for p,sc,  rt in mTEPES.ps *mTEPES.rt]
    mTEPES.psnot = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psn*mTEPES.ot]
    mTEPES.psnht = [(p,sc,n,ht) for p,sc,n,ht in mTEPES.psn*mTEPES.ht]
    mTEPES.psnrt = [(p,sc,n,rt) for p,sc,n,rt in mTEPES.psn*mTEPES.rt]

    #%% inverse index generator to mutually exclusive generator
    pExclusiveGenToGen = pGenToExclusiveGen.reset_index().set_index('MutuallyExclusive').set_axis(['Generator'], axis=1)[['Generator']]
    pExclusiveGenToGen = pExclusiveGenToGen.loc[pExclusiveGenToGen['Generator'].isin(mTEPES.g)]
    pExclusiveGen2Gen  = pExclusiveGenToGen.reset_index().set_index(['MutuallyExclusive', 'Generator'])

    mTEPES.g2g = Set(initialize=pExclusiveGen2Gen.index, ordered=False, doc='mutually exclusive generator to generator', filter=lambda mTEPES,gg,g: (gg,g) in mTEPES.gg*mTEPES.g)

    # minimum and maximum variable power, charge, and storage capacity
    pMinPower      = pVariableMinPower.replace  (0.0, pRatedMinPower  )
    pMaxPower      = pVariableMaxPower.replace  (0.0, pRatedMaxPower  )
    pMinCharge     = pVariableMinCharge.replace (0.0, pRatedMinCharge )
    pMaxCharge     = pVariableMaxCharge.replace (0.0, pRatedMaxCharge )
    pMinStorage    = pVariableMinStorage.replace(0.0, pRatedMinStorage)
    pMaxStorage    = pVariableMaxStorage.replace(0.0, pRatedMaxStorage)
    if pIndHydroTopology == 1:
        pMinVolume = pVariableMinVolume.replace (0.0, pRatedMinVolume )
        pMaxVolume = pVariableMaxVolume.replace (0.0, pRatedMaxVolume )

    pMinPower      = pMinPower.where  (pMinPower   > 0.0, other=0.0)
    pMaxPower      = pMaxPower.where  (pMaxPower   > 0.0, other=0.0)
    pMinCharge     = pMinCharge.where (pMinCharge  > 0.0, other=0.0)
    pMaxCharge     = pMaxCharge.where (pMaxCharge  > 0.0, other=0.0)
    pMinStorage    = pMinStorage.where(pMinStorage > 0.0, other=0.0)
    pMaxStorage    = pMaxStorage.where(pMaxStorage > 0.0, other=0.0)
    if pIndHydroTopology == 1:
        pMinVolume = pMinVolume.where (pMinVolume  > 0.0, other=0.0)
        pMaxVolume = pMaxVolume.where (pMaxVolume  > 0.0, other=0.0)

    # fuel term and constant term variable cost
    pVarLinearVarCost   =              (dfGeneration['LinearTerm'  ] * 1e-3 * pVariableFuelCost       +dfGeneration['OMVariableCost'] * 1e-3).replace(0.0, float('nan'))
    pVarConstantVarCost =               dfGeneration['ConstantTerm'] * 1e-6 * pVariableFuelCost.replace                                              (0.0, float('nan'))
    pLinearVarCost      = pd.DataFrame([dfGeneration['LinearTerm'  ] * 1e-3 * dfGeneration['FuelCost']+dfGeneration['OMVariableCost'] * 1e-3]*len(pVariableFuelCost.index), index=pVariableFuelCost.index, columns=dfGeneration['FuelCost'].index)
    pConstantVarCost    = pd.DataFrame([dfGeneration['ConstantTerm'] * 1e-6 * dfGeneration['FuelCost']                                      ]*len(pVariableFuelCost.index), index=pVariableFuelCost.index, columns=dfGeneration['FuelCost'].index)
    pLinearVarCost      = pLinearVarCost.reindex     (sorted(pLinearVarCost.columns     ), axis=1)
    pConstantVarCost    = pConstantVarCost.reindex   (sorted(pConstantVarCost.columns   ), axis=1)
    pVarLinearVarCost   = pVarLinearVarCost.reindex  (sorted(pVarLinearVarCost.columns  ), axis=1)
    pVarConstantVarCost = pVarConstantVarCost.reindex(sorted(pVarConstantVarCost.columns), axis=1)
    pLinearVarCost      = pVarLinearVarCost.where  (pVariableFuelCost > 0.0, other=pLinearVarCost  )
    pConstantVarCost    = pVarConstantVarCost.where(pVariableFuelCost > 0.0, other=pConstantVarCost)

    # parameter that allows the initial inventory to change with load level
    pIniInventory       = pd.DataFrame([pInitialInventory]*len(pVariableMinStorage.index), index=pVariableMinStorage.index, columns=pInitialInventory.index)
    if pIndHydroTopology == 1:
        pIniVolume      = pd.DataFrame([pInitialVolume   ]*len(pVariableMinVolume.index ), index=pVariableMinVolume.index , columns=pInitialVolume.index   )
    # initial inventory must be between minimum and maximum
    # pIniInventory       = pMinStorage.where(pMinStorage > pIniInventory, other=pIniInventory)
    # pIniInventory       = pMaxStorage.where(pMaxStorage < pIniInventory, other=pIniInventory)

    # minimum up- and downtime and maximum shift time converted to an integer number of time steps
    pUpTime    = round(pUpTime   /pTimeStep).astype('int')
    pDwTime    = round(pDwTime   /pTimeStep).astype('int')
    pShiftTime = round(pShiftTime/pTimeStep).astype('int')

    # %% definition of the time-steps leap to observe the stored energy at an ESS
    idxCycle            = dict()
    idxCycle[0        ] = 8736
    idxCycle[0.0      ] = 8736
    idxCycle['Hourly' ] = 1
    idxCycle['Daily'  ] = 1
    idxCycle['Weekly' ] = round(  24/pTimeStep)
    idxCycle['Monthly'] = round( 168/pTimeStep)
    idxCycle['Yearly' ] = round( 168/pTimeStep)

    idxOutflows            = dict()
    idxOutflows[0        ] = 8736
    idxOutflows[0.0      ] = 8736
    idxOutflows['Daily'  ] = round(  24/pTimeStep)
    idxOutflows['Weekly' ] = round( 168/pTimeStep)
    idxOutflows['Monthly'] = round( 672/pTimeStep)
    idxOutflows['Yearly' ] = round(8736/pTimeStep)

    idxEnergy            = dict()
    idxEnergy[0        ] = 8736
    idxEnergy[0.0      ] = 8736
    idxEnergy['Daily'  ] = round(  24/pTimeStep)
    idxEnergy['Weekly' ] = round( 168/pTimeStep)
    idxEnergy['Monthly'] = round( 672/pTimeStep)
    idxEnergy['Yearly' ] = round(8736/pTimeStep)

    pCycleTimeStep    = pStorageType.map (idxCycle                                                                                  ).astype('int')
    pOutflowsTimeStep = pOutflowsType.map(idxOutflows).where(pEnergyOutflows.sum()                               > 0.0, other = 8736).astype('int')
    pEnergyTimeStep   = pEnergyType.map  (idxEnergy  ).where(pVariableMinEnergy.sum() + pVariableMaxEnergy.sum() > 0.0, other = 8736).astype('int')

    pCycleTimeStep    = pd.concat([pCycleTimeStep, pOutflowsTimeStep, pEnergyTimeStep], axis=1).min(axis=1)

    if pIndHydroTopology == 1:
        # %% definition of the time-steps leap to observe the stored energy at a reservoir
        idxCycleRsr            = dict()
        idxCycleRsr[0        ] = 8736
        idxCycleRsr[0.0      ] = 8736
        idxCycleRsr['Hourly' ] = 1
        idxCycleRsr['Daily'  ] = 1
        idxCycleRsr['Weekly' ] = round(  24/pTimeStep)
        idxCycleRsr['Monthly'] = round( 168/pTimeStep)
        idxCycleRsr['Yearly' ] = round( 168/pTimeStep)

        idxWaterOut            = dict()
        idxWaterOut[0        ] = 8736
        idxWaterOut[0.0      ] = 8736
        idxWaterOut['Daily'  ] = round(  24/pTimeStep)
        idxWaterOut['Weekly' ] = round( 168/pTimeStep)
        idxWaterOut['Monthly'] = round( 672/pTimeStep)
        idxWaterOut['Yearly' ] = round(8736/pTimeStep)

        pCycleRsrTimeStep = pReservoirType.map(idxCycleRsr).astype('int')
        pWaterOutTimeStep = pWaterOutfType.map(idxWaterOut).astype('int')

        pCycleWaterStep      = pd.concat([pCycleRsrTimeStep, pWaterOutTimeStep], axis=1).min(axis=1)

    # drop load levels with duration 0
    pDuration          = pDuration.loc         [mTEPES.n    ]
    pDemand            = pDemand.loc           [mTEPES.psn  ]
    pSystemInertia     = pSystemInertia.loc    [mTEPES.psnar]
    pOperReserveUp     = pOperReserveUp.loc    [mTEPES.psnar]
    pOperReserveDw     = pOperReserveDw.loc    [mTEPES.psnar]
    pMinPower          = pMinPower.loc         [mTEPES.psn  ]
    pMaxPower          = pMaxPower.loc         [mTEPES.psn  ]
    pMinCharge         = pMinCharge.loc        [mTEPES.psn  ]
    pMaxCharge         = pMaxCharge.loc        [mTEPES.psn  ]
    pEnergyInflows     = pEnergyInflows.loc    [mTEPES.psn  ]
    pEnergyOutflows    = pEnergyOutflows.loc   [mTEPES.psn  ]
    pIniInventory      = pIniInventory.loc     [mTEPES.psn  ]
    pMinStorage        = pMinStorage.loc       [mTEPES.psn  ]
    pMaxStorage        = pMaxStorage.loc       [mTEPES.psn  ]
    pVariableMaxEnergy = pVariableMaxEnergy.loc[mTEPES.psn  ]
    pVariableMinEnergy = pVariableMinEnergy.loc[mTEPES.psn  ]
    pLinearVarCost     = pLinearVarCost.loc    [mTEPES.psn  ]
    pConstantVarCost   = pConstantVarCost.loc  [mTEPES.psn  ]

    if pIndHydroTopology == 1:
        pHydroInflows  = pHydroInflows.loc     [mTEPES.psn  ]
        pHydroOutflows = pHydroOutflows.loc    [mTEPES.psn  ]
        pIniVolume     = pIniVolume.loc        [mTEPES.psn  ]
        pMinVolume     = pMinVolume.loc        [mTEPES.psn  ]
        pMaxVolume     = pMaxVolume.loc        [mTEPES.psn  ]

    # separate positive and negative demands to avoid converting negative values to 0
    pDemandPos        = pDemand.where(pDemand >= 0.0, other=0.0)
    pDemandNeg        = pDemand.where(pDemand <  0.0, other=0.0)

    # generators to area (g2a) (e2a) (n2a)
    g2a = defaultdict(list)
    for ar,g  in mTEPES.a2g:
        g2a[ar].append(g )
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)

    # nodes to area (d2a)
    d2a = defaultdict(list)
    for nd,ar in mTEPES.ndar:
        d2a[ar].append(nd)

    # small values are converted to 0
    pPeakDemand         = pd.Series([0.0 for ar in mTEPES.ar], index=mTEPES.ar)
    for ar in mTEPES.ar:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        pPeakDemand[ar] = pDemand      [[nd for nd in d2a[ar]]].sum(axis=1).max()
        pEpsilon        = pPeakDemand[ar]*2.5e-5
        # values < 1e-5 times the maximum system demand are converted to 0
        # pEpsilon      = pDemand.sum(axis=1).max()*1e-5

        # these parameters are in GW
        pDemandPos     [pDemandPos     [[nd for nd in d2a[ar]]] <  pEpsilon] = 0.0
        pDemandNeg     [pDemandNeg     [[nd for nd in d2a[ar]]] > -pEpsilon] = 0.0
        pSystemInertia [pSystemInertia [[                 ar ]] <  pEpsilon] = 0.0
        pOperReserveUp [pOperReserveUp [[                 ar ]] <  pEpsilon] = 0.0
        pOperReserveDw [pOperReserveDw [[                 ar ]] <  pEpsilon] = 0.0
        pMinPower      [pMinPower      [[g  for  g in g2a[ar]]] <  pEpsilon] = 0.0
        pMaxPower      [pMaxPower      [[g  for  g in g2a[ar]]] <  pEpsilon] = 0.0
        pMinCharge     [pMinCharge     [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
        pMaxCharge     [pMaxCharge     [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
        pEnergyInflows [pEnergyInflows [[es for es in e2a[ar]]] <  pEpsilon/pTimeStep] = 0.0
        pEnergyOutflows[pEnergyOutflows[[es for es in e2a[ar]]] <  pEpsilon/pTimeStep] = 0.0
        # these parameters are in GWh
        pMinStorage    [pMinStorage    [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
        pMaxStorage    [pMaxStorage    [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
        pIniInventory  [pIniInventory  [[es for es in e2a[ar]]] <  pEpsilon] = 0.0

        pInitialInventory.update(pd.Series([0.0 for es in e2a[ar] if pInitialInventory[es] < pEpsilon], index=[es for es in e2a[ar] if pInitialInventory[es] < pEpsilon], dtype='float64'))

        pLineNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilon], dtype='float64'))
        pLineNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilon], dtype='float64'))

        # merging positive and negative values of the demand
        pDemand            = pDemandPos.where(pDemandNeg >= 0.0, other=pDemandNeg)

        pMaxPower2ndBlock  = pMaxPower  - pMinPower
        pMaxCharge2ndBlock = pMaxCharge - pMinCharge

        pMaxPower2ndBlock [pMaxPower2ndBlock [[nr for nr in n2a[ar]]] < pEpsilon] = 0.0
        pMaxCharge2ndBlock[pMaxCharge2ndBlock[[es for es in e2a[ar]]] < pEpsilon] = 0.0

    # replace < 0.0 by 0.0
    pMaxPower2ndBlock  = pMaxPower2ndBlock.where (pMaxPower2ndBlock  > 0.0, other=0.0)
    pMaxCharge2ndBlock = pMaxCharge2ndBlock.where(pMaxCharge2ndBlock > 0.0, other=0.0)

    # drop generators not es
    pMinCharge           = pMinCharge.loc          [:, mTEPES.es]
    pMaxCharge           = pMaxCharge.loc          [:, mTEPES.es]
    pEnergyInflows       = pEnergyInflows.loc      [:, mTEPES.es]
    pEnergyOutflows      = pEnergyOutflows.loc     [:, mTEPES.es]
    pMinStorage          = pMinStorage.loc         [:, mTEPES.es]
    pMaxStorage          = pMaxStorage.loc         [:, mTEPES.es]
    pEfficiency          = pEfficiency.loc         [   mTEPES.es]
    pCycleTimeStep       = pCycleTimeStep.loc      [   mTEPES.es]
    pOutflowsTimeStep    = pOutflowsTimeStep.loc   [   mTEPES.es]
    pIniInventory        = pIniInventory.loc       [:, mTEPES.es]
    pInitialInventory    = pInitialInventory.loc   [   mTEPES.es]
    pStorageType         = pStorageType.loc        [   mTEPES.es]
    pMaxCharge2ndBlock   = pMaxCharge2ndBlock.loc  [:, mTEPES.es]

    # drop generators not gc or gd
    pGenInvestCost       = pGenInvestCost.loc      [   mTEPES.gc]
    pGenRetireCost       = pGenRetireCost.loc      [   mTEPES.gd]
    pIndBinUnitInvest    = pIndBinUnitInvest.loc   [   mTEPES.gc]
    pIndBinUnitRetire    = pIndBinUnitRetire.loc   [   mTEPES.gd]
    pGenLoInvest         = pGenLoInvest.loc        [   mTEPES.gc]
    pGenLoRetire         = pGenLoRetire.loc        [   mTEPES.gd]
    pGenUpInvest         = pGenUpInvest.loc        [   mTEPES.gc]
    pGenUpRetire         = pGenUpRetire.loc        [   mTEPES.gd]

    # drop generators not nr or ec
    pStartUpCost         = pStartUpCost.loc        [   mTEPES.nr]
    pShutDownCost        = pShutDownCost.loc       [   mTEPES.nr]
    pIndBinUnitCommit    = pIndBinUnitCommit.loc   [   mTEPES.nr]
    pIndBinStorInvest    = pIndBinStorInvest.loc   [   mTEPES.ec]

    # drop lines not lc or ll
    pNetFixedCost        = pNetFixedCost.loc       [   mTEPES.lc]
    pNetLoInvest         = pNetLoInvest.loc        [   mTEPES.lc]
    pNetUpInvest         = pNetUpInvest.loc        [   mTEPES.lc]
    pLineLossFactor      = pLineLossFactor.loc     [   mTEPES.ll]

    # drop generators not h
    pProductionFunction  = pProductionFunction.loc [   mTEPES.h ]

    if pIndHydroTopology == 1:
        # drop reservoirs not rn
        pRsrInvestCost   = pRsrInvestCost.loc      [   mTEPES.rn]
        # maximum outflows depending on the downstream hydropower unit
        pMaxOutflows = pd.DataFrame([[sum(pMaxPower[h][p,sc,n]/pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) for rs in mTEPES.rs] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.rs)

    # replace very small costs by 0
    pEpsilon = 1e-4           # this value in €/GWh is related to the smallest reduced cost, independent of the area

    pLinearVarCost  [pLinearVarCost  [[g for g in mTEPES.g]] < pEpsilon] = 0.0
    pConstantVarCost[pConstantVarCost[[g for g in mTEPES.g]] < pEpsilon] = 0.0

    pRatedLinearVarCost.update  (pd.Series([0.0 for gg in mTEPES.gg if     pRatedLinearVarCost  [gg]  < pEpsilon], index=[gg for gg in mTEPES.gg if     pRatedLinearVarCost  [gg]  < pEpsilon]))
    pRatedConstantVarCost.update(pd.Series([0.0 for gg in mTEPES.gg if     pRatedConstantVarCost[gg]  < pEpsilon], index=[gg for gg in mTEPES.gg if     pRatedConstantVarCost[gg]  < pEpsilon]))
    pLinearOMCost.update        (pd.Series([0.0 for gg in mTEPES.gg if     pLinearOMCost        [gg]  < pEpsilon], index=[gg for gg in mTEPES.gg if     pLinearOMCost        [gg]  < pEpsilon]))
    pOperReserveCost.update     (pd.Series([0.0 for gg in mTEPES.gg if     pOperReserveCost     [gg]  < pEpsilon], index=[gg for gg in mTEPES.gg if     pOperReserveCost     [gg]  < pEpsilon]))
    pCO2EmissionCost.update     (pd.Series([0.0 for gg in mTEPES.gg if abs(pCO2EmissionCost     [gg]) < pEpsilon], index=[gg for gg in mTEPES.gg if abs(pCO2EmissionCost     [gg]) < pEpsilon]))
    pStartUpCost.update         (pd.Series([0.0 for nr in mTEPES.nr if     pStartUpCost         [nr]  < pEpsilon], index=[nr for nr in mTEPES.nr if     pStartUpCost         [nr]  < pEpsilon]))
    pShutDownCost.update        (pd.Series([0.0 for nr in mTEPES.nr if     pShutDownCost        [nr]  < pEpsilon], index=[nr for nr in mTEPES.nr if     pShutDownCost        [nr]  < pEpsilon]))

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

    # if BigM are 0.0 then converted to 1.0 to avoid division by 0.0
    pBigMFlowBck = pBigMFlowBck.where(pBigMFlowBck != 0.0, other=1.0)
    pBigMFlowFrw = pBigMFlowFrw.where(pBigMFlowFrw != 0.0, other=1.0)

    # maximum voltage angle
    pMaxTheta = pDemand*0.0 + math.pi/2
    pMaxTheta = pMaxTheta.loc[mTEPES.psn]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    # %% parameters
    mTEPES.pIndBinGenInvest      = Param(initialize=pIndBinGenInvest     , within=NonNegativeIntegers, doc='Indicator of binary generation investment decisions', mutable=True)
    mTEPES.pIndBinGenRetire      = Param(initialize=pIndBinGenRetire     , within=NonNegativeIntegers, doc='Indicator of binary generation retirement decisions', mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=pIndBinGenOperat     , within=Binary,              doc='Indicator of binary generation operation  decisions', mutable=True)
    mTEPES.pIndBinSingleNode     = Param(initialize=pIndBinSingleNode    , within=Binary,              doc='Indicator of single node within a network case',      mutable=True)
    mTEPES.pIndBinGenRamps       = Param(initialize=pIndBinGenRamps      , within=Binary,              doc='Indicator of using or not the ramp constraints',      mutable=True)
    mTEPES.pIndBinGenMinTime     = Param(initialize=pIndBinGenMinTime    , within=Binary,              doc='Indicator of using or not the min time constraints',  mutable=True)
    mTEPES.pIndBinNetInvest      = Param(initialize=pIndBinNetInvest     , within=NonNegativeIntegers, doc='Indicator of binary network    investment decisions', mutable=True)
    mTEPES.pIndBinLineCommit     = Param(initialize=pIndBinLineCommit    , within=Binary,              doc='Indicator of binary network    switching  decisions', mutable=True)
    mTEPES.pIndBinNetLosses      = Param(initialize=pIndBinNetLosses     , within=Binary,              doc='Indicator of binary network ohmic losses',            mutable=True)

    mTEPES.pIndBinRsrInvest      = Param(initialize=pIndBinRsrInvest     , within=NonNegativeIntegers, doc='Indicator of binary reservoir  investment decisions', mutable=True)
    mTEPES.pIndHydroTopology     = Param(initialize=pIndHydroTopology    , within=Binary,              doc='Indicator of reservoir and hydropower topology'    )

    mTEPES.pENSCost              = Param(initialize=pENSCost             , within=NonNegativeReals,    doc='ENS cost'                                          )
    mTEPES.pCO2Cost              = Param(initialize=pCO2Cost             , within=NonNegativeReals,    doc='CO2 emission cost'                                 )
    mTEPES.pAnnualDiscRate       = Param(initialize=pAnnualDiscRate      , within=UnitInterval,        doc='Annual discount rate'                              )
    mTEPES.pUpReserveActivation  = Param(initialize=pUpReserveActivation , within=UnitInterval,        doc='Proportion of upward   reserve activation'         )
    mTEPES.pDwReserveActivation  = Param(initialize=pDwReserveActivation , within=UnitInterval,        doc='Proportion of downward reserve activation'         )
    mTEPES.pMinRatioDwUp         = Param(initialize=pMinRatioDwUp        , within=UnitInterval,        doc='Minimum ration between upward and downward reserve')
    mTEPES.pMaxRatioDwUp         = Param(initialize=pMaxRatioDwUp        , within=UnitInterval,        doc='Maximum ration between upward and downward reserve')
    mTEPES.pSBase                = Param(initialize=pSBase               , within=PositiveReals,       doc='Base power'                                        )
    mTEPES.pTimeStep             = Param(initialize=pTimeStep            , within=PositiveIntegers,    doc='Unitary time step'                                 )
    mTEPES.pEconomicBaseYear     = Param(initialize=pEconomicBaseYear    , within=PositiveIntegers,    doc='Base year'                                         )

    mTEPES.pReserveMargin        = Param(mTEPES.ar,    initialize=pReserveMargin.to_dict()            , within=NonNegativeReals,    doc='Adequacy reserve margin'                             )
    mTEPES.pPeakDemand           = Param(mTEPES.ar,    initialize=pPeakDemand.to_dict()               , within=NonNegativeReals,    doc='Peak demand'                                         )
    mTEPES.pDemand               = Param(mTEPES.psnnd, initialize=pDemand.stack().to_dict()           , within=           Reals,    doc='Demand'                                              )
    mTEPES.pPeriodWeight         = Param(mTEPES.p,     initialize=pPeriodWeight.to_dict()             , within=NonNegativeIntegers, doc='Period weight',                          mutable=True)
    mTEPES.pDiscountFactor       = Param(mTEPES.p,     initialize=pDiscountFactor.to_dict()           , within=NonNegativeReals,    doc='Discount factor'                                     )
    mTEPES.pScenProb             = Param(mTEPES.psc,   initialize=pScenProb.to_dict()                 , within=UnitInterval    ,    doc='Probability',                            mutable=True)
    mTEPES.pStageWeight          = Param(mTEPES.stt,   initialize=pStageWeight.to_dict()              , within=NonNegativeIntegers, doc='Stage weight'                                        )
    mTEPES.pDuration             = Param(mTEPES.n,     initialize=pDuration.to_dict()                 , within=PositiveIntegers,    doc='Duration',                               mutable=True)
    mTEPES.pNodeLon              = Param(mTEPES.nd,    initialize=pNodeLon.to_dict()                  ,                             doc='Longitude'                                           )
    mTEPES.pNodeLat              = Param(mTEPES.nd,    initialize=pNodeLat.to_dict()                  ,                             doc='Latitude'                                            )
    mTEPES.pSystemInertia        = Param(mTEPES.psnar, initialize=pSystemInertia.stack().to_dict()    , within=NonNegativeReals,    doc='System inertia'                                      )
    mTEPES.pOperReserveUp        = Param(mTEPES.psnar, initialize=pOperReserveUp.stack().to_dict()    , within=NonNegativeReals,    doc='Upward   operating reserve'                          )
    mTEPES.pOperReserveDw        = Param(mTEPES.psnar, initialize=pOperReserveDw.stack().to_dict()    , within=NonNegativeReals,    doc='Downward operating reserve'                          )
    mTEPES.pMinPower             = Param(mTEPES.psngg, initialize=pMinPower.stack().to_dict()         , within=NonNegativeReals,    doc='Minimum power'                                       )
    mTEPES.pMaxPower             = Param(mTEPES.psngg, initialize=pMaxPower.stack().to_dict()         , within=NonNegativeReals,    doc='Maximum power'                                       )
    mTEPES.pMinCharge            = Param(mTEPES.psnes, initialize=pMinCharge.stack().to_dict()        , within=NonNegativeReals,    doc='Minimum charge'                                      )
    mTEPES.pMaxCharge            = Param(mTEPES.psnes, initialize=pMaxCharge.stack().to_dict()        , within=NonNegativeReals,    doc='Maximum charge'                                      )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.psngg, initialize=pMaxPower2ndBlock.stack().to_dict() , within=NonNegativeReals,    doc='Second block power'                                  )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.psnes, initialize=pMaxCharge2ndBlock.stack().to_dict(), within=NonNegativeReals,    doc='Second block charge'                                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.psnes, initialize=pEnergyInflows.stack().to_dict()    , within=NonNegativeReals,    doc='Energy inflows',                         mutable=True)
    mTEPES.pEnergyOutflows       = Param(mTEPES.psnes, initialize=pEnergyOutflows.stack().to_dict()   , within=NonNegativeReals,    doc='Energy outflows',                        mutable=True)
    mTEPES.pMinStorage           = Param(mTEPES.psnes, initialize=pMinStorage.stack().to_dict()       , within=NonNegativeReals,    doc='ESS Minimum storage capacity'                        )
    mTEPES.pMaxStorage           = Param(mTEPES.psnes, initialize=pMaxStorage.stack().to_dict()       , within=NonNegativeReals,    doc='ESS Maximum storage capacity'                        )
    mTEPES.pMinEnergy            = Param(mTEPES.psngg, initialize=pVariableMinEnergy.stack().to_dict(), within=NonNegativeReals,    doc='Unit minimum energy demand'                          )
    mTEPES.pMaxEnergy            = Param(mTEPES.psngg, initialize=pVariableMaxEnergy.stack().to_dict(), within=NonNegativeReals,    doc='Unit maximum energy demand'                          )
    mTEPES.pRatedMaxPower        = Param(mTEPES.gg,    initialize=pRatedMaxPower.to_dict()            , within=NonNegativeReals,    doc='Rated maximum power'                                 )
    mTEPES.pRatedMaxCharge       = Param(mTEPES.gg,    initialize=pRatedMaxCharge.to_dict()           , within=NonNegativeReals,    doc='Rated maximum charge'                                )
    mTEPES.pMustRun              = Param(mTEPES.gg,    initialize=pMustRun.to_dict()                  , within=Binary          ,    doc='must-run unit'                                       )
    mTEPES.pInertia              = Param(mTEPES.gg,    initialize=pInertia.to_dict()                  , within=NonNegativeReals,    doc='unit inertia constant'                               )
    mTEPES.pPeriodIniGen         = Param(mTEPES.gg,    initialize=pPeriodIniGen.to_dict()             , within=PositiveIntegers,    doc='installation year',                                  )
    mTEPES.pPeriodFinGen         = Param(mTEPES.gg,    initialize=pPeriodFinGen.to_dict()             , within=PositiveIntegers,    doc='retirement   year',                                  )
    mTEPES.pAvailability         = Param(mTEPES.gg,    initialize=pAvailability.to_dict()             , within=UnitInterval    ,    doc='unit availability',                      mutable=True)
    mTEPES.pEFOR                 = Param(mTEPES.gg,    initialize=pEFOR.to_dict()                     , within=UnitInterval    ,    doc='EFOR'                                                )
    mTEPES.pRatedLinearVarCost   = Param(mTEPES.gg,    initialize=pRatedLinearVarCost.to_dict()       , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pRatedConstantVarCost = Param(mTEPES.gg,    initialize=pRatedConstantVarCost.to_dict()     , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearVarCost        = Param(mTEPES.psngg, initialize=pLinearVarCost.stack().to_dict()    , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pConstantVarCost      = Param(mTEPES.psngg, initialize=pConstantVarCost.stack().to_dict()  , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearOMCost         = Param(mTEPES.gg,    initialize=pLinearOMCost.to_dict()             , within=NonNegativeReals,    doc='Linear   O&M      cost'                              )
    mTEPES.pOperReserveCost      = Param(mTEPES.gg,    initialize=pOperReserveCost.to_dict()          , within=NonNegativeReals,    doc='Operating reserve cost'                              )
    mTEPES.pCO2EmissionCost      = Param(mTEPES.gg,    initialize=pCO2EmissionCost.to_dict()          , within=Reals,               doc='CO2 Emission      cost'                              )
    mTEPES.pCO2EmissionRate      = Param(mTEPES.gg,    initialize=pCO2EmissionRate.to_dict()          , within=Reals,               doc='CO2 Emission      rate'                              )
    mTEPES.pStartUpCost          = Param(mTEPES.nr,    initialize=pStartUpCost.to_dict()              , within=NonNegativeReals,    doc='Startup  cost'                                       )
    mTEPES.pShutDownCost         = Param(mTEPES.nr,    initialize=pShutDownCost.to_dict()             , within=NonNegativeReals,    doc='Shutdown cost'                                       )
    mTEPES.pRampUp               = Param(mTEPES.gg,    initialize=pRampUp.to_dict()                   , within=NonNegativeReals,    doc='Ramp up   rate'                                      )
    mTEPES.pRampDw               = Param(mTEPES.gg,    initialize=pRampDw.to_dict()                   , within=NonNegativeReals,    doc='Ramp down rate'                                      )
    mTEPES.pUpTime               = Param(mTEPES.gg,    initialize=pUpTime.to_dict()                   , within=NonNegativeIntegers, doc='Up    time'                                          )
    mTEPES.pDwTime               = Param(mTEPES.gg,    initialize=pDwTime.to_dict()                   , within=NonNegativeIntegers, doc='Down  time'                                          )
    mTEPES.pShiftTime            = Param(mTEPES.gg,    initialize=pShiftTime.to_dict()                , within=NonNegativeIntegers, doc='Shift time'                                          )
    mTEPES.pGenInvestCost        = Param(mTEPES.gc,    initialize=pGenInvestCost.to_dict()            , within=NonNegativeReals,    doc='Generation fixed cost'                               )
    mTEPES.pGenRetireCost        = Param(mTEPES.gd,    initialize=pGenRetireCost.to_dict()            , within=Reals           ,    doc='Generation fixed retire cost'                        )
    mTEPES.pIndBinUnitInvest     = Param(mTEPES.gc,    initialize=pIndBinUnitInvest.to_dict()         , within=Binary          ,    doc='Binary investment decision'                          )
    mTEPES.pIndBinUnitRetire     = Param(mTEPES.gd,    initialize=pIndBinUnitRetire.to_dict()         , within=Binary          ,    doc='Binary retirement decision'                          )
    mTEPES.pIndBinUnitCommit     = Param(mTEPES.nr,    initialize=pIndBinUnitCommit.to_dict()         , within=Binary          ,    doc='Binary commitment decision'                          )
    mTEPES.pIndBinStorInvest     = Param(mTEPES.ec,    initialize=pIndBinStorInvest.to_dict()         , within=Binary          ,    doc='Storage linked to generation investment'             )
    mTEPES.pIndOperReserve       = Param(mTEPES.gg,    initialize=pIndOperReserve.to_dict()           , within=Binary          ,    doc='Indicator of operating reserve'                      )
    mTEPES.pProductionFunction   = Param(mTEPES.h ,    initialize=pProductionFunction.to_dict()       , within=NonNegativeReals,    doc='Production function of hydro power plant'            )
    mTEPES.pEfficiency           = Param(mTEPES.es,    initialize=pEfficiency.to_dict()               , within=UnitInterval    ,    doc='Round-trip efficiency'                               )
    mTEPES.pCycleTimeStep        = Param(mTEPES.es,    initialize=pCycleTimeStep.to_dict()            , within=PositiveIntegers,    doc='ESS Storage cycle'                                   )
    mTEPES.pOutflowsTimeStep     = Param(mTEPES.es,    initialize=pOutflowsTimeStep.to_dict()         , within=PositiveIntegers,    doc='ESS Outflows cycle'                                  )
    mTEPES.pEnergyTimeStep       = Param(mTEPES.gg,    initialize=pEnergyTimeStep.to_dict()           , within=PositiveIntegers,    doc='Unit energy cycle'                                   )
    mTEPES.pIniInventory         = Param(mTEPES.psnes, initialize=pIniInventory.stack().to_dict()     , within=NonNegativeReals,    doc='ESS Initial storage',                    mutable=True)
    mTEPES.pInitialInventory     = Param(mTEPES.es,    initialize=pInitialInventory.to_dict()         , within=NonNegativeReals,    doc='ESS Initial storage without load levels'             )
    mTEPES.pStorageType          = Param(mTEPES.es,    initialize=pStorageType.to_dict()              , within=Any             ,    doc='ESS Storage type'                                    )
    mTEPES.pGenLoInvest          = Param(mTEPES.gc,    initialize=pGenLoInvest.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pGenUpInvest          = Param(mTEPES.gc,    initialize=pGenUpInvest.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)
    mTEPES.pGenLoRetire          = Param(mTEPES.gd,    initialize=pGenLoRetire.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the retirement decision', mutable=True)
    mTEPES.pGenUpRetire          = Param(mTEPES.gd,    initialize=pGenUpRetire.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the retirement decision', mutable=True)

    if pIndHydroTopology == 1:
        mTEPES.pHydroInflows     = Param(mTEPES.psnrs, initialize=pHydroInflows.stack().to_dict()     , within=NonNegativeReals,    doc='Hydro inflows',                          mutable=True)
        mTEPES.pHydroOutflows    = Param(mTEPES.psnrs, initialize=pHydroOutflows.stack().to_dict()    , within=NonNegativeReals,    doc='Hydro outflows',                         mutable=True)
        mTEPES.pMaxOutflows      = Param(mTEPES.psnrs, initialize=pMaxOutflows.stack().to_dict()      , within=NonNegativeReals,    doc='Maximum hydro outflows',                             )
        mTEPES.pMinVolume        = Param(mTEPES.psnrs, initialize=pMinVolume.stack().to_dict()        , within=NonNegativeReals,    doc='Minimum reservoir volume capacity'                   )
        mTEPES.pMaxVolume        = Param(mTEPES.psnrs, initialize=pMaxVolume.stack().to_dict()        , within=NonNegativeReals,    doc='Maximum reservoir volume capacity'                   )
        mTEPES.pRsrInvestCost    = Param(mTEPES.rn,    initialize=pRsrInvestCost.to_dict()            , within=NonNegativeReals,    doc='Reservoir fixed cost'                                )
        mTEPES.pPeriodIniRsr     = Param(mTEPES.rs,    initialize=pPeriodIniRsr.to_dict()             , within=PositiveIntegers,    doc='Installation year',                                  )
        mTEPES.pPeriodFinRsr     = Param(mTEPES.rs,    initialize=pPeriodFinRsr.to_dict()             , within=PositiveIntegers,    doc='Retirement   year',                                  )
        mTEPES.pCycleWaterStep   = Param(mTEPES.rs,    initialize=pCycleWaterStep.to_dict()           , within=PositiveIntegers,    doc='Reservoir volume cycle'                              )
        mTEPES.pWaterOutTimeStep = Param(mTEPES.rs,    initialize=pWaterOutTimeStep.to_dict()         , within=PositiveIntegers,    doc='Reservoir outflows cycle'                            )
        mTEPES.pIniVolume        = Param(mTEPES.psnrs, initialize=pIniVolume.stack().to_dict()        , within=NonNegativeReals,    doc='Reservoir initial volume',               mutable=True)
        mTEPES.pInitialVolume    = Param(mTEPES.rs,    initialize=pInitialVolume.to_dict()            , within=NonNegativeReals,    doc='Reservoir initial volume without load levels'        )
        mTEPES.pReservoirType    = Param(mTEPES.rs,    initialize=pReservoirType.to_dict()            , within=Any             ,    doc='Reservoir volume type'                               )

    mTEPES.pLoadLevelDuration    = Param(mTEPES.n,     initialize=0                                   , within=NonNegativeIntegers, doc='Load level duration',                    mutable=True)
    for n in mTEPES.n:
        mTEPES.pLoadLevelDuration[n] = mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n]

    mTEPES.pPeriodProb           = Param(mTEPES.ps,    initialize=0.0                                 , within=NonNegativeReals,    doc='Period probability',                     mutable=True)
    for p,sc in mTEPES.ps:
        # periods and scenarios are going to be solved together with their weight and probability
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc]

    mTEPES.pLineLossFactor       = Param(mTEPES.ll,    initialize=pLineLossFactor.to_dict()           , within=           Reals,    doc='Loss factor'                                         )
    mTEPES.pLineR                = Param(mTEPES.ln,    initialize=pLineR.to_dict()                    , within=NonNegativeReals,    doc='Resistance'                                          )
    mTEPES.pLineX                = Param(mTEPES.ln,    initialize=pLineX.to_dict()                    , within=           Reals,    doc='Reactance'                                           )
    mTEPES.pLineBsh              = Param(mTEPES.ln,    initialize=pLineBsh.to_dict()                  , within=NonNegativeReals,    doc='Susceptance',                            mutable=True)
    mTEPES.pLineTAP              = Param(mTEPES.ln,    initialize=pLineTAP.to_dict()                  , within=NonNegativeReals,    doc='Tap changer',                            mutable=True)
    mTEPES.pLineLength           = Param(mTEPES.ln,    initialize=pLineLength.to_dict()               , within=NonNegativeReals,    doc='Length',                                 mutable=True)
    mTEPES.pPeriodIniNet         = Param(mTEPES.ln,    initialize=pPeriodIniNet.to_dict()             , within=PositiveIntegers,    doc='Installation period'                                 )
    mTEPES.pPeriodFinNet         = Param(mTEPES.ln,    initialize=pPeriodFinNet.to_dict()             , within=PositiveIntegers,    doc='Retirement   period'                                 )
    mTEPES.pLineVoltage          = Param(mTEPES.ln,    initialize=pLineVoltage.to_dict()              , within=NonNegativeReals,    doc='Voltage'                                             )
    mTEPES.pLineNTCFrw           = Param(mTEPES.ln,    initialize=pLineNTCFrw.to_dict()               , within=NonNegativeReals,    doc='NTC forward'                                         )
    mTEPES.pLineNTCBck           = Param(mTEPES.ln,    initialize=pLineNTCBck.to_dict()               , within=NonNegativeReals,    doc='NTC backward'                                        )
    mTEPES.pNetFixedCost         = Param(mTEPES.lc,    initialize=pNetFixedCost.to_dict()             , within=NonNegativeReals,    doc='Network fixed cost'                                  )
    mTEPES.pIndBinLineInvest     = Param(mTEPES.ln,    initialize=pIndBinLineInvest.to_dict()         , within=Binary          ,    doc='Binary investment decision'                          )
    mTEPES.pIndBinLineSwitch     = Param(mTEPES.ln,    initialize=pIndBinLineSwitch.to_dict()         , within=Binary          ,    doc='Binary switching  decision'                          )
    mTEPES.pSwOnTime             = Param(mTEPES.ln,    initialize=pSwitchOnTime.to_dict()             , within=NonNegativeIntegers, doc='Minimum switching on  time'                          )
    mTEPES.pSwOffTime            = Param(mTEPES.ln,    initialize=pSwitchOffTime.to_dict()            , within=NonNegativeIntegers, doc='Minimum switching off time'                          )
    mTEPES.pBigMFlowBck          = Param(mTEPES.ln,    initialize=pBigMFlowBck.to_dict()              , within=NonNegativeReals,    doc='Maximum backward capacity',              mutable=True)
    mTEPES.pBigMFlowFrw          = Param(mTEPES.ln,    initialize=pBigMFlowFrw.to_dict()              , within=NonNegativeReals,    doc='Maximum forward  capacity',              mutable=True)
    mTEPES.pMaxTheta             = Param(mTEPES.psnnd, initialize=pMaxTheta.stack().to_dict()         , within=NonNegativeReals,    doc='Maximum voltage angle',                  mutable=True)
    mTEPES.pAngMin               = Param(mTEPES.ln,    initialize=pAngMin.to_dict()                   , within=Reals,               doc='Minimum phase angle diff',               mutable=True)
    mTEPES.pAngMax               = Param(mTEPES.ln,    initialize=pAngMax.to_dict()                   , within=Reals,               doc='Maximum phase angle diff',               mutable=True)
    mTEPES.pNetLoInvest          = Param(mTEPES.lc,    initialize=pNetLoInvest.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pNetUpInvest          = Param(mTEPES.lc,    initialize=pNetUpInvest.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pCycleTimeStep   [es] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pCycleTimeStep   [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
    if pIndHydroTopology == 1:
        mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pCycleWaterStep  [rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
        if sum(1 for h,rs in mTEPES.p2r):
            mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pCycleWaterStep  [rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
        else:
            mTEPES.np2c = []
        if sum(1 for rs,h in mTEPES.r2p):
            mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pCycleWaterStep  [rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
        else:
            mTEPES.npc  = []
        mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pCycleWaterStep  [rs] == 0]
        mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pCycleWaterStep  [rs] == 0]
        mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep[rs] == 0]

    # ESS with outflows
    mTEPES.eo     = [(p,sc,es) for p,sc,es in mTEPES.pses if sum(mTEPES.pEnergyOutflows[p,sc,n2,es]() for n2 in mTEPES.n2)]
    if pIndHydroTopology == 1:
        # reservoirs with outflows
        mTEPES.ro = [(p,sc,rs) for p,sc,rs in mTEPES.psrs if sum(mTEPES.pHydroOutflows [p,sc,n2,rs]() for n2 in mTEPES.n2)]
    # generators with min/Max energy
    mTEPES.gm     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMinEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2)]
    mTEPES.gM     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMaxEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2)]

    # if unit availability = 0 changed to 1
    for g in mTEPES.g:
        if  mTEPES.pAvailability[g]() == 0.0:
            mTEPES.pAvailability[g]   =  1.0

    # if line length = 0 changed to geographical distance with an additional 10%
    for ni,nf,cc in mTEPES.la:
        if  mTEPES.pLineLength[ni,nf,cc]() == 0.0:
            mTEPES.pLineLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    # initialize generation output, unit commitment and line switching
    pInitialOutput = pd.DataFrame([[0.0]*len(mTEPES.gg)]*len(mTEPES.psn), index=mTEPES.psn, columns=list(mTEPES.gg))
    pInitialUC     = pd.DataFrame([[0  ]*len(mTEPES.gg)]*len(mTEPES.psn), index=mTEPES.psn, columns=list(mTEPES.gg))
    pInitialSwitch = pd.DataFrame([[0  ]*len(mTEPES.la)]*len(mTEPES.psn), index=mTEPES.psn, columns=list(mTEPES.la))

    mTEPES.pInitialOutput = Param(mTEPES.psngg, initialize=pInitialOutput.stack().to_dict(), within=NonNegativeReals, doc='unit initial output',     mutable=True)
    mTEPES.pInitialUC     = Param(mTEPES.psngg, initialize=pInitialUC.stack().to_dict()    , within=Binary,           doc='unit initial commitment', mutable=True)
    mTEPES.pInitialSwitch = Param(mTEPES.psnla, initialize=pInitialSwitch.stack().to_dict(), within=Binary,           doc='line initial switching',  mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')


def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()

    #%% variables
    OptModel.vTotalSCost            = Var(              within=NonNegativeReals,                                                                                                                     doc='total system                         cost      [MEUR]')
    OptModel.vTotalICost            = Var(              within=NonNegativeReals,                                                                                                                     doc='total system investment              cost      [MEUR]')
    OptModel.vTotalFCost            = Var(mTEPES.p,     within=NonNegativeReals,                                                                                                            doc='total system fixed                   cost      [MEUR]')
    OptModel.vTotalGCost            = Var(mTEPES.psn,   within=NonNegativeReals,                                                                                                            doc='total variable generation  operation cost      [MEUR]')
    OptModel.vTotalCCost            = Var(mTEPES.psn,   within=NonNegativeReals,                                                                                                            doc='total variable consumption operation cost      [MEUR]')
    OptModel.vTotalECost            = Var(mTEPES.psn,   within=NonNegativeReals,                                                                                                            doc='total system emission                cost      [MEUR]')
    OptModel.vTotalRCost            = Var(mTEPES.psn,   within=NonNegativeReals,                                                                                                            doc='total system reliability             cost      [MEUR]')
    OptModel.vTotalOutput           = Var(mTEPES.psng , within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,g : (0.0,                            mTEPES.pMaxPower         [p,sc,n,g ]),  doc='total output of the unit                         [GW]')
    OptModel.vOutput2ndBlock        = Var(mTEPES.psnnr, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,nr: (0.0,                            mTEPES.pMaxPower2ndBlock [p,sc,n,nr]),  doc='second block of the unit                         [GW]')
    OptModel.vReserveUp             = Var(mTEPES.psnnr, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,nr: (0.0,                            mTEPES.pMaxPower2ndBlock [p,sc,n,nr]),  doc='upward   operating reserve                       [GW]')
    OptModel.vReserveDown           = Var(mTEPES.psnnr, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,nr: (0.0,                            mTEPES.pMaxPower2ndBlock [p,sc,n,nr]),  doc='downward operating reserve                       [GW]')
    OptModel.vEnergyInflows         = Var(mTEPES.psnec, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,ec: (0.0,                                mTEPES.pEnergyInflows[p,sc,n,ec]),  doc='unscheduled inflows  of candidate ESS units      [GW]')
    OptModel.vEnergyOutflows        = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (0.0,max(mTEPES.pMaxPower[p,sc,n,es],mTEPES.pMaxCharge    [p,sc,n,es])), doc='scheduled   outflows of all       ESS units      [GW]')
    OptModel.vESSInventory          = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (      mTEPES.pMinStorage[p,sc,n,es],mTEPES.pMaxStorage   [p,sc,n,es]),  doc='ESS inventory                                   [GWh]')
    OptModel.vESSSpillage           = Var(mTEPES.psnes, within=NonNegativeReals,                                                                                                            doc='ESS spillage                                    [GWh]')
    OptModel.vESSTotalCharge        = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (0.0,                            mTEPES.pMaxCharge        [p,sc,n,es]),  doc='ESS total charge power                           [GW]')
    OptModel.vCharge2ndBlock        = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (0.0,                            mTEPES.pMaxCharge2ndBlock[p,sc,n,es]),  doc='ESS       charge power                           [GW]')
    OptModel.vESSReserveUp          = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (0.0,                            mTEPES.pMaxCharge2ndBlock[p,sc,n,es]),  doc='ESS upward   operating reserve                   [GW]')
    OptModel.vESSReserveDown        = Var(mTEPES.psnes, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,es: (0.0,                            mTEPES.pMaxCharge2ndBlock[p,sc,n,es]),  doc='ESS downward operating reserve                   [GW]')
    OptModel.vENS                   = Var(mTEPES.psnnd, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,nd: (0.0,                            max(0.0,mTEPES.pDemand   [p,sc,n,nd])), doc='energy not served in node                        [GW]')

    if mTEPES.pIndHydroTopology == 1:
        OptModel.vHydroInflows      = Var(mTEPES.psnrc, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,rc: (0.0,                            mTEPES.pHydroInflows     [p,sc,n,rc]),  doc='unscheduled inflows  of candidate hydro units    [GW]')
        OptModel.vHydroOutflows     = Var(mTEPES.psnrs, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,rs: (0.0,                                  mTEPES.pMaxOutflows[p,sc,n,rs]),  doc='scheduled   outflows of all       hydro units    [GW]')
        OptModel.vReservoirVolume   = Var(mTEPES.psnrs, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,rs: (       mTEPES.pMinVolume[p,sc,n,rs],mTEPES.pMaxVolume    [p,sc,n,rs]),  doc='Reservoir volume                                [hm3]')
        OptModel.vReservoirSpillage = Var(mTEPES.psnrs, within=NonNegativeReals,                                                                                                            doc='Reservoir spillage                              [hm3]')

    if mTEPES.pIndBinGenInvest() == 0:
        OptModel.vGenerationInvest    = Var(mTEPES.pgc,   within=UnitInterval,                                                                                                                    doc='generation investment decision exists in a year [0,1]')
    else:
        OptModel.vGenerationInvest    = Var(mTEPES.pgc,   within=Binary,                                                                                                                          doc='generation investment decision exists in a year {0,1}')

    if mTEPES.pIndBinGenRetire() == 0:
        OptModel.vGenerationRetire    = Var(mTEPES.pgd,   within=UnitInterval,                                                                                                                    doc='generation retirement decision exists in a year [0,1]')
    else:
        OptModel.vGenerationRetire    = Var(mTEPES.pgd,   within=Binary,                                                                                                                          doc='generation retirement decision exists in a year {0,1}')

    if mTEPES.pIndBinNetInvest() == 0:
        OptModel.vNetworkInvest       = Var(mTEPES.plc,   within=UnitInterval,                                                                                                                    doc='network    investment decision exists in a year [0,1]')
    else:
        OptModel.vNetworkInvest       = Var(mTEPES.plc,   within=Binary,                                                                                                                          doc='network    investment decision exists in a year {0,1}')

    if mTEPES.pIndHydroTopology == 1:
        if mTEPES.pIndBinRsrInvest() == 0:
            OptModel.vReservoirInvest = Var(mTEPES.prc,   within=UnitInterval,                                                                                                                    doc='reservoir  investment decision exists in a year [0,1]')
        else:
            OptModel.vReservoirInvest = Var(mTEPES.prc,   within=Binary,                                                                                                                          doc='reservoir  investment decision exists in a year {0,1}')

    if mTEPES.pIndBinGenOperat() == 0:
        OptModel.vCommitment        = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0,                                                                                                doc='commitment         of the unit                  [0,1]')
        OptModel.vStartUp           = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0,                                                                                                doc='startup            of the unit                  [0,1]')
        OptModel.vShutDown          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0,                                                                                                doc='shutdown           of the unit                  [0,1]')
        OptModel.vMaxCommitment     = Var(mTEPES.psnr , within=UnitInterval,     initialize=0.0,                                                                                                doc='maximum commitment of the unit                  [0,1]')
    else:
        OptModel.vCommitment        = Var(mTEPES.psnnr, within=Binary,           initialize=0  ,                                                                                                doc='commitment         of the unit                  {0,1}')
        OptModel.vStartUp           = Var(mTEPES.psnnr, within=Binary,           initialize=0  ,                                                                                                doc='startup            of the unit                  {0,1}')
        OptModel.vShutDown          = Var(mTEPES.psnnr, within=Binary,           initialize=0  ,                                                                                                doc='shutdown           of the unit                  {0,1}')
        OptModel.vMaxCommitment     = Var(mTEPES.psnr , within=Binary,           initialize=0  ,                                                                                                doc='maximum commitment of the unit                  {0,1}')

    if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineCommit() == 0:
        OptModel.vLineCommit        = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0,                                                                                                doc='line switching      of the line                 [0,1]')
    else:
        OptModel.vLineCommit        = Var(mTEPES.psnla, within=Binary,           initialize=0  ,                                                                                                doc='line switching      of the line                 {0,1}')

    if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineCommit() == 0:
            OptModel.vLineOnState   = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0,                                                                                                doc='switching on  state of the line                 [0,1]')
            OptModel.vLineOffState  = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0,                                                                                                doc='switching off state of the line                 [0,1]')
        else:
            OptModel.vLineOnState   = Var(mTEPES.psnla, within=Binary,           initialize=0  ,                                                                                                doc='switching on  state of the line                 {0,1}')
            OptModel.vLineOffState  = Var(mTEPES.psnla, within=Binary,           initialize=0  ,                                                                                                doc='switching off state of the line                 {0,1}')

    nFixedVariables = 0.0

    # relax binary condition in generation and network investment decisions
    for p,gc in mTEPES.pgc:
        if mTEPES.pIndBinGenInvest() != 0 and mTEPES.pIndBinUnitInvest[gc      ] == 0:
            OptModel.vGenerationInvest[p,gc      ].domain = UnitInterval
        if mTEPES.pIndBinGenInvest() == 2:
            OptModel.vGenerationInvest[p,gc      ].fix(0)
            nFixedVariables += 1
    for p,ni,nf,cc in mTEPES.plc:
        if mTEPES.pIndBinNetInvest() != 0 and mTEPES.pIndBinLineInvest[ni,nf,cc] == 0:
            OptModel.vNetworkInvest   [p,ni,nf,cc].domain = UnitInterval
        if mTEPES.pIndBinNetInvest() == 2:
            OptModel.vNetworkInvest   [p,ni,nf,cc].fix(0)
            nFixedVariables += 1

    # relax binary condition in generation retirement decisions
    for p,gd in mTEPES.pgd:
        if mTEPES.pIndBinGenRetire() != 0 and mTEPES.pIndBinUnitRetire[gd      ] == 0:
            OptModel.vGenerationRetire[p,gd      ].domain = UnitInterval
        if mTEPES.pIndBinGenRetire() == 2:
            OptModel.vGenerationRetire[p,gd      ].fix(0)
            nFixedVariables += 1

    # assign the minimum power for the RES units
    for p,sc,n,re in mTEPES.psnre:
        OptModel.vTotalOutput[p,sc,n,re].setlb(mTEPES.pMinPower[p,sc,n,re])

    # relax binary condition in unit generation, startup and shutdown decisions
    for p,sc,n,nr in mTEPES.psnnr:
        if mTEPES.pIndBinUnitCommit[nr] == 0:
            OptModel.vCommitment   [p,sc,n,nr].domain = UnitInterval
            OptModel.vStartUp      [p,sc,n,nr].domain = UnitInterval
            OptModel.vShutDown     [p,sc,n,nr].domain = UnitInterval
    for p,sc,  nr in mTEPES.ps*         mTEPES.nr:
        if mTEPES.pIndBinUnitCommit[nr] == 0:
            OptModel.vMaxCommitment[p,sc,  nr].domain = UnitInterval

    # existing lines are always committed if no switching decision is modeled
    for p,sc,n,ni,nf,cc in mTEPES.psnle:
        if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
            OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(1)
            nFixedVariables += 1

    # no on/off state for lines if no switching decision is modeled
    if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
        for p,sc,n,ni,nf,cc in mTEPES.psnla:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
                OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0)
                OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0)
                nFixedVariables += 2

    OptModel.vLineLosses = Var(mTEPES.psnll, within=NonNegativeReals, bounds=lambda OptModel,p,sc,n,*ll: (0.0,0.5*mTEPES.pLineLossFactor[ll]*max(mTEPES.pLineNTCBck[ll],mTEPES.pLineNTCFrw[ll])), doc='half line losses [GW]')
    if mTEPES.pIndBinSingleNode() == 0:
        OptModel.vFlow   = Var(mTEPES.psnla, within=Reals,            bounds=lambda OptModel,p,sc,n,*la: (                                      -mTEPES.pLineNTCBck[la],mTEPES.pLineNTCFrw[la]),  doc='flow             [GW]')
    else:
        OptModel.vFlow   = Var(mTEPES.psnla, within=Reals,                                                                                                                                        doc='flow             [GW]')
    OptModel.vTheta      = Var(mTEPES.psnnd, within=Reals,            bounds=lambda OptModel,p,sc,n, nd: (                            -mTEPES.pMaxTheta[p,sc,n,nd],mTEPES.pMaxTheta[p,sc,n,nd]),  doc='voltage angle   [rad]')

    # fix the must-run units and their output
    for p,sc,n,g  in mTEPES.psng :
        # must run units must produce at least their minimum output
        if mTEPES.pMustRun[g] == 1:
            OptModel.vTotalOutput[p,sc,n,g].setlb(mTEPES.pMinPower[p,sc,n,g])
        # if no max power, no total output
        if mTEPES.pMaxPower      [p,sc,n,g] ==  0.0:
            OptModel.vTotalOutput[p,sc,n,g].fix(0.0)
            nFixedVariables += 1

    for p,sc,n,nr in mTEPES.psnnr:
        # must run units or units with no minimum power or ESS existing units are always committed and must produce at least their minimum output
        # not applicable to mutually exclusive units
        if   len(mTEPES.g2g) == 0:
            OptModel.vMaxCommitment     [p,sc,  nr].fix(1)
            nFixedVariables += 1/len(mTEPES.n)
            if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPower[p,sc,n,nr] == 0.0 and mTEPES.pRatedConstantVarCost[nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec:
                OptModel.vCommitment    [p,sc,n,nr].fix(1)
                OptModel.vStartUp       [p,sc,n,nr].fix(0)
                OptModel.vShutDown      [p,sc,n,nr].fix(0)
                nFixedVariables += 3
        elif len(mTEPES.g2g) >  0 and sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g) == 0:
            if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPower[p,sc,n,nr] == 0.0 and mTEPES.pRatedConstantVarCost[nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec:
                OptModel.vCommitment    [p,sc,n,nr].fix(1)
                OptModel.vStartUp       [p,sc,n,nr].fix(0)
                OptModel.vShutDown      [p,sc,n,nr].fix(0)
                OptModel.vMaxCommitment [p,sc,  nr].fix(1)
                nFixedVariables += 3+1/len(mTEPES.n)
        # if min and max power coincide there are neither second block, nor operating reserve
        if  mTEPES.pMaxPower2ndBlock[p,sc,n,nr] ==  0.0:
            OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
            OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
            OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
            nFixedVariables += 3
        if  mTEPES.pIndOperReserve  [       nr] !=  0.0:
            OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
            OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
            nFixedVariables += 2

    for p,sc,n,es in mTEPES.psnes:
        # ESS with no charge capacity or not storage capacity can't charge
        if mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0:
            OptModel.vESSTotalCharge[p,sc,n,es].fix(0.0)
            nFixedVariables += 1
        # ESS with no charge capacity and no inflows can't produce
        if mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0 and sum(mTEPES.pEnergyInflows[pp,scc,nn,es]() for pp,scc,nn in mTEPES.psn) == 0.0:
            OptModel.vTotalOutput   [p,sc,n,es].fix(0.0)
            OptModel.vOutput2ndBlock[p,sc,n,es].fix(0.0)
            OptModel.vReserveUp     [p,sc,n,es].fix(0.0)
            OptModel.vReserveDown   [p,sc,n,es].fix(0.0)
            OptModel.vESSSpillage   [p,sc,n,es].fix(0.0)
            nFixedVariables += 5
        if mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0:
            OptModel.vCharge2ndBlock[p,sc,n,es].fix(0.0)
            nFixedVariables += 1
        if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0 or mTEPES.pIndOperReserve  [       es] !=  0.0:
            OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
            OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
            nFixedVariables += 2
        if mTEPES.pMaxStorage       [p,sc,n,es] ==  0.0:
            OptModel.vESSInventory  [p,sc,n,es].fix(0.0)
            nFixedVariables += 1

    # thermal and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if len(mTEPES.tq):
        mTEPES.go = [k for k in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if k not in mTEPES.sq]
    else:
        mTEPES.go = [k for k in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__)                      ]

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in st == stt and mTEPES.pStageWeight and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in               mTEPES.pDuration    and           (st,nn) in mTEPES.s2n)

        if len(mTEPES.n):
            # determine the first load level of each stage
            n1 = next(iter(mTEPES.psn))
            # commit the units and their output at the first load level of each stage
            pSystemOutput = 0.0
            for nr in mTEPES.nr:
                if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[nr] == 1:
                    mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPower[n1,nr]
                    mTEPES.pInitialUC    [n1,nr] = 1
                    pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

            # determine the initial committed units and their output at the first load level of each period, scenario, and stage
            for go in mTEPES.go:
                if pSystemOutput < sum(mTEPES.pDemand[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[go] != 1:
                    if go in mTEPES.re:
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

            # fixing the ESS inventory at the last load level of the stage for every period and scenario if between storage limits
            for es in mTEPES.es:
                if mTEPES.pInitialInventory[es] >= mTEPES.pMinStorage[p,sc,mTEPES.n.last(),es] and mTEPES.pInitialInventory[es] <= mTEPES.pMaxStorage[p,sc,mTEPES.n.last(),es]:
                    OptModel.vESSInventory[p,sc,mTEPES.n.last(),es].fix(mTEPES.pInitialInventory[es])

    # activate all the periods, scenarios, and load levels again
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.pStageWeight and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.pDuration                                         )

    # fixing the ESS inventory at the end of the following pCycleTimeStep (daily, weekly, monthly) if between storage limits, i.e., for daily ESS is fixed at the end of the week, for weekly/monthly ESS is fixed at the end of the year
    for p,sc,n,es in mTEPES.psnes:
        if mTEPES.pInitialInventory[es] >= mTEPES.pMinStorage[p,sc,n,es] and mTEPES.pInitialInventory[es] <= mTEPES.pMaxStorage[p,sc,n,es]:
            if mTEPES.pStorageType[es] == 'Hourly'  and mTEPES.n.ord(n) % int(  24/mTEPES.pTimeStep()) == 0:
                OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pInitialInventory[es])
                nFixedVariables += 1
            if mTEPES.pStorageType[es] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
                OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pInitialInventory[es])
                nFixedVariables += 1
            if mTEPES.pStorageType[es] == 'Weekly'  and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
                OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pInitialInventory[es])
                nFixedVariables += 1
            if mTEPES.pStorageType[es] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
                OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pInitialInventory[es])
                nFixedVariables += 1

    for p,sc,n,ec in mTEPES.psnec:
        if mTEPES.pEnergyInflows        [p,sc,n,ec]() == 0.0:
            OptModel.vEnergyInflows     [p,sc,n,ec].fix(0.0)
            nFixedVariables += 1

    # if no operating reserve is required no variables are needed
    for p,sc,n,ar,nr in mTEPES.psnar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
    for p,sc,n,ar,es in mTEPES.psnar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                nFixedVariables += 1

    # if there are no energy outflows no variable is needed
    for es in mTEPES.es:
        if sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn) == 0.0:
            for p,sc,n in mTEPES.psn:
                OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                nFixedVariables += 1

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    if mTEPES.pIndBinSingleNode() == 0:
        for p,sc,n in mTEPES.psn:
            OptModel.vTheta[p,sc,n,mTEPES.rf.first()].fix(0.0)
            nFixedVariables += 1

    # fixing the ENS in nodes with no demand
    for p,sc,n,nd in mTEPES.psnnd:
        if mTEPES.pDemand[p,sc,n,nd] ==  0.0:
            OptModel.vENS[p,sc,n,nd].fix(0.0)
            nFixedVariables += 1

    # do not install/retire power plants and lines if not allowed in this period
    for p,gc in mTEPES.pgc:
        if mTEPES.pPeriodIniGen[gc] > p or mTEPES.pPeriodFinGen[gc] < p:
            OptModel.vGenerationInvest[p,gc].fix(0)
            nFixedVariables += 1

    for p,gd in mTEPES.pgd:
        if mTEPES.pPeriodIniGen[gd] > p or mTEPES.pPeriodFinGen[gd] < p:
            OptModel.vGenerationRetire[p,gd].fix(0)
            nFixedVariables += 1

    for p,ni,nf,cc in mTEPES.plc:
        if mTEPES.pPeriodIniNet[ni,nf,cc] > p or mTEPES.pPeriodFinNet[ni,nf,cc] < p:
            OptModel.vNetworkInvest[p,ni,nf,cc].fix(0)
            nFixedVariables += 1

    # remove power plants and lines not installed in this period
    for p,g in mTEPES.pg:
        if g not in mTEPES.gc and (mTEPES.pPeriodIniGen[g ] > p or mTEPES.pPeriodFinGen[g ] < p):
            for sc,n in mTEPES.sc*mTEPES.n:
                OptModel.vTotalOutput   [p,sc,n,g].fix(0.0)
                nFixedVariables += 1

    for p,sc,nr in mTEPES.psnr:
        if nr not in mTEPES.gc and (mTEPES.pPeriodIniGen[nr] > p or mTEPES.pPeriodFinGen[nr] < p):
            OptModel.vMaxCommitment[p,sc,nr].fix(0)
            nFixedVariables += 1
            for n in mTEPES.n:
                OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                OptModel.vCommitment    [p,sc,n,nr].fix(0  )
                OptModel.vStartUp       [p,sc,n,nr].fix(0  )
                OptModel.vShutDown      [p,sc,n,nr].fix(0  )
                nFixedVariables += 6

    for p,es in mTEPES.pes:
        if es not in mTEPES.gc and (mTEPES.pPeriodIniGen[es] > p or mTEPES.pPeriodFinGen[es] < p):
            for sc,n in mTEPES.sc*mTEPES.n:
                OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                OptModel.vESSInventory  [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage   [p,sc,n,es].fix(0.0)
                OptModel.vESSTotalCharge[p,sc,n,es].fix(0.0)
                OptModel.vCharge2ndBlock[p,sc,n,es].fix(0.0)
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                mTEPES.pIniInventory    [p,sc,n,es] =   0.0
                mTEPES.pEnergyInflows   [p,sc,n,es] =   0.0
                nFixedVariables += 7

    if mTEPES.pIndHydroTopology == 1:
        for p,rs in mTEPES.prs:
            if rs not in mTEPES.rn and (mTEPES.pPeriodIniRsr[rs] > p or mTEPES.pPeriodFinRsr[rs] < p):
                for sc,n in mTEPES.sc*mTEPES.n:
                    OptModel.vEnergyOutflows[p,sc,n,rs].fix(0.0)
                    OptModel.vReservoirVolume  [p,sc,n,rs].fix(0.0)
                    OptModel.vReservoirSpillage[p,sc,n,rs].fix(0.0)
                    mTEPES.pIniVolume          [p,sc,n,rs] =   0.0
                    mTEPES.pHydroInflows       [p,sc,n,rs] =   0.0
                    for h in mTEPES.h:
                        if (rs,h) in mTEPES.r2h:
                            OptModel.vESSTotalCharge[p,sc,n,h].fix(0.0)
                            OptModel.vCharge2ndBlock[p,sc,n,h].fix(0.0)
                            OptModel.vESSReserveUp  [p,sc,n,h].fix(0.0)
                            OptModel.vESSReserveDown[p,sc,n,h].fix(0.0)
                    nFixedVariables += 7

    for p,ni,nf,cc in mTEPES.pla:
        if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pPeriodIniNet[ni,nf,cc] > p or mTEPES.pPeriodFinNet[ni,nf,cc] < p):
            for sc,n in mTEPES.sc*mTEPES.n:
                OptModel.vFlow        [p,sc,n,ni,nf,cc].fix(0.0)
                OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(0  )
                OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0  )
                OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0  )
                nFixedVariables += 4

    for p,ni,nf,cc in mTEPES.pll:
        if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pPeriodIniNet[ni,nf,cc] > p or mTEPES.pPeriodFinNet[ni,nf,cc] < p):
            for sc,n in mTEPES.sc*mTEPES.n:
                OptModel.vLineLosses  [p,sc,n,ni,nf,cc].fix(0.0)
                nFixedVariables += 1

    # tolerance to consider 0 a number
    pEpsilon = 1e-4
    for p,gc in mTEPES.pgc:
        if  mTEPES.pGenLoInvest   [  gc      ]() <       pEpsilon:
            mTEPES.pGenLoInvest   [  gc      ]   = 0
        if  mTEPES.pGenUpInvest   [  gc      ]() <       pEpsilon:
            mTEPES.pGenUpInvest   [  gc      ]   = 0
        if  mTEPES.pGenLoInvest   [  gc      ]() > 1.0 - pEpsilon:
            mTEPES.pGenLoInvest   [  gc      ]   = 1
        if  mTEPES.pGenUpInvest   [  gc      ]() > 1.0 - pEpsilon:
            mTEPES.pGenUpInvest   [  gc      ]   = 1
        if  mTEPES.pGenLoInvest   [  gc      ]() >   mTEPES.pGenUpInvest[gc      ]():
            mTEPES.pGenLoInvest   [  gc      ]   =   mTEPES.pGenUpInvest[gc      ]()
        OptModel.vGenerationInvest[p,gc      ].setlb(mTEPES.pGenLoInvest[gc      ])
        OptModel.vGenerationInvest[p,gc      ].setub(mTEPES.pGenUpInvest[gc      ])
    for p,gd in mTEPES.pgd:
        if  mTEPES.pGenLoRetire   [  gd      ]() < pEpsilon:
            mTEPES.pGenLoRetire   [  gd      ]   = 0
        if  mTEPES.pGenUpRetire   [  gd      ]() <       pEpsilon:
            mTEPES.pGenUpRetire   [  gd      ]   = 0
        if  mTEPES.pGenLoRetire   [  gd      ]() > 1.0 - pEpsilon:
            mTEPES.pGenLoRetire   [  gd      ]   = 1
        if  mTEPES.pGenUpRetire   [  gd      ]() > 1.0 - pEpsilon:
            mTEPES.pGenUpRetire   [  gd      ]   = 1
        if  mTEPES.pGenLoRetire   [  gd      ]() >   mTEPES.pGenUpRetire[gd      ]():
            mTEPES.pGenLoRetire   [  gd      ]   =   mTEPES.pGenUpRetire[gd      ]()
        OptModel.vGenerationRetire[p,gd      ].setlb(mTEPES.pGenLoRetire[gd      ])
        OptModel.vGenerationRetire[p,gd      ].setub(mTEPES.pGenUpRetire[gd      ])
    for p,ni,nf,cc in mTEPES.plc:
        if  mTEPES.pNetLoInvest   [  ni,nf,cc]() <       pEpsilon:
            mTEPES.pNetLoInvest   [  ni,nf,cc]   = 0
        if  mTEPES.pNetUpInvest   [  ni,nf,cc]() <       pEpsilon:
            mTEPES.pNetUpInvest   [  ni,nf,cc]   = 0
        if  mTEPES.pNetLoInvest   [  ni,nf,cc]() > 1.0 - pEpsilon:
            mTEPES.pNetLoInvest   [  ni,nf,cc]   = 1
        if  mTEPES.pNetUpInvest   [  ni,nf,cc]() > 1.0 - pEpsilon:
            mTEPES.pNetUpInvest   [  ni,nf,cc]   = 1
        if  mTEPES.pNetLoInvest   [  ni,nf,cc]() >   mTEPES.pNetUpInvest[ni,nf,cc]():
            mTEPES.pNetLoInvest   [  ni,nf,cc]   =   mTEPES.pNetUpInvest[ni,nf,cc]()
        OptModel.vNetworkInvest   [p,ni,nf,cc].setlb(mTEPES.pNetLoInvest[ni,nf,cc])
        OptModel.vNetworkInvest   [p,ni,nf,cc].setub(mTEPES.pNetUpInvest[ni,nf,cc])

    # detecting infeasibility: sum of scenario probabilities must be 1 in each period
    # for p in mTEPES.p:
    #     if abs(sum(mTEPES.pScenProb[p,sc] for sc in mTEPES.sc)-1.0) > 1e-6:
    #         print('### Sum of scenario probabilities different from 1 in period ', p)
    #         assert (0 == 1)

    for es in mTEPES.es:
        # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows
        if sum(mTEPES.pMinPower [p,sc,n,es] for p,sc,n in mTEPES.psn) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn) > 0.0:
            print('### Total minimum output greater than total inflows for ESS unit ', es)
            assert (0 == 1)
        if sum(mTEPES.pMaxCharge[p,sc,n,es] for p,sc,n in mTEPES.psn) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn) < 0.0:
            print('### Total maximum charge lower than total outflows for ESS unit ', es)
            assert (0 == 1)

    # detect inventory infeasibility
    for p,sc,n,es in mTEPES.ps*mTEPES.nesc:
        if mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es]:
            if   mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
                if mTEPES.pIniInventory[p,sc,n,es]()                                      + sum(mTEPES.pDuration[n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPower[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                    print('### Inventory equation violation ', p, sc, n, es)
                    assert (0 == 1)
            elif mTEPES.n.ord(n) >  mTEPES.pCycleTimeStep[es]:
                if mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPower[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                    print('### Inventory equation violation ', p, sc, n, es)
                    assert (0 == 1)

    # detect minimum energy infeasibility
    for p,sc,n,g in mTEPES.ps*mTEPES.ngen:
        if (p,sc,g) in mTEPES.gm:
            if sum((mTEPES.pMaxPower[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
                print('### Minimum energy violation ', p, sc, n, g)
                assert (0 == 1)

    mTEPES.nFixedVariables = Param(initialize=round(nFixedVariables), within=NonNegativeIntegers, doc='Number of fixed variables')

    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
