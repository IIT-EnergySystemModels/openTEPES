"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 19, 2024
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
    dfDuration              = pd.read_csv(_path+'/oT_Data_Duration_'              +CaseName+'.csv', index_col=[0,1,2])
    dfReserveMargin         = pd.read_csv(_path+'/oT_Data_ReserveMargin_'         +CaseName+'.csv', index_col=[0,1  ])
    dfEmission              = pd.read_csv(_path+'/oT_Data_Emission_'              +CaseName+'.csv', index_col=[0,1  ])
    dfRESEnergy             = pd.read_csv(_path+'/oT_Data_RESEnergy_'             +CaseName+'.csv', index_col=[0,1  ])
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
    dfVariableEmissionCost  = pd.read_csv(_path+'/oT_Data_VariableEmissionCost_'  +CaseName+'.csv', index_col=[0,1,2])
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
        pIndHydroTopology   = 1
    except:
        pIndHydroTopology   = 0
        print('**** No hydropower topology')

    try:
        dfDemandHydrogen    = pd.read_csv(_path+'/oT_Data_DemandHydrogen_'        +CaseName+'.csv', index_col=[0,1,2])
        dfNetworkHydrogen   = pd.read_csv(_path+'/oT_Data_NetworkHydrogen_'       +CaseName+'.csv', index_col=[0,1,2])
        pIndHydrogen        = 1
    except:
        pIndHydrogen        = 0
        print('**** No hydrogen energy carrier')

    try:
        dfDemandHeat        = pd.read_csv(_path+'/oT_Data_DemandHeat_'                +CaseName+'.csv', index_col=[0,1,2])
        dfNetworkHeat       = pd.read_csv(_path+'/oT_Data_NetworkHeat_'               +CaseName+'.csv', index_col=[0,1,2])
        pIndHeat            = 1
    except:
        pIndHeat            = 0
        print('**** No heat energy carrier')

    # substitute NaN by 0
    dfOption.fillna               (0  , inplace=True)
    dfParameter.fillna            (0.0, inplace=True)
    dfPeriod.fillna               (0.0, inplace=True)
    dfScenario.fillna             (0.0, inplace=True)
    dfStage.fillna                (0.0, inplace=True)
    dfDuration.fillna             (0  , inplace=True)
    dfReserveMargin.fillna        (0.0, inplace=True)
    dfEmission.fillna             (math.inf , inplace=True)
    dfRESEnergy.fillna            (0.0, inplace=True)
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
    dfVariableEmissionCost.fillna (0.0, inplace=True)
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

    if pIndHydrogen == 1:
        dfDemandHydrogen.fillna   (0.0, inplace=True)
        dfNetworkHydrogen.fillna  (0.0, inplace=True)

    if pIndHeat == 1:
        dfDemandHeat.fillna       (0.0, inplace=True)
        dfNetworkHeat.fillna      (0.0, inplace=True)

    dfReserveMargin         = dfReserveMargin.where       (dfReserveMargin        > 0.0, 0.0)
    dfEmission              = dfEmission.where            (dfEmission             > 0.0, 0.0)
    dfRESEnergy             = dfRESEnergy.where           (dfRESEnergy            > 0.0, 0.0)
    dfInertia               = dfInertia.where             (dfInertia              > 0.0, 0.0)
    dfUpOperatingReserve    = dfUpOperatingReserve.where  (dfUpOperatingReserve   > 0.0, 0.0)
    dfDwOperatingReserve    = dfDwOperatingReserve.where  (dfDwOperatingReserve   > 0.0, 0.0)
    dfVariableMinPower      = dfVariableMinPower.where    (dfVariableMinPower     > 0.0, 0.0)
    dfVariableMaxPower      = dfVariableMaxPower.where    (dfVariableMaxPower     > 0.0, 0.0)
    dfVariableMinCharge     = dfVariableMinCharge.where   (dfVariableMinCharge    > 0.0, 0.0)
    dfVariableMaxCharge     = dfVariableMaxCharge.where   (dfVariableMaxCharge    > 0.0, 0.0)
    dfVariableMinStorage    = dfVariableMinStorage.where  (dfVariableMinStorage   > 0.0, 0.0)
    dfVariableMaxStorage    = dfVariableMaxStorage.where  (dfVariableMaxStorage   > 0.0, 0.0)
    dfVariableMinEnergy     = dfVariableMinEnergy.where   (dfVariableMinEnergy    > 0.0, 0.0)
    dfVariableMaxEnergy     = dfVariableMaxEnergy.where   (dfVariableMaxEnergy    > 0.0, 0.0)
    dfVariableFuelCost      = dfVariableFuelCost.where    (dfVariableFuelCost     > 0.0, 0.0)
    dfVariableEmissionCost  = dfVariableEmissionCost.where(dfVariableEmissionCost > 0.0, 0.0)
    dfEnergyInflows         = dfEnergyInflows.where       (dfEnergyInflows        > 0.0, 0.0)
    dfEnergyOutflows        = dfEnergyOutflows.where      (dfEnergyOutflows       > 0.0, 0.0)

    if pIndHydroTopology == 1:
        dfVariableMinVolume = dfVariableMinVolume.where   (dfVariableMinVolume    > 0.0, 0.0)
        dfVariableMaxVolume = dfVariableMaxVolume.where   (dfVariableMaxVolume    > 0.0, 0.0)
        dfHydroInflows      = dfHydroInflows.where        (dfHydroInflows         > 0.0, 0.0)
        dfHydroOutflows     = dfHydroOutflows.where       (dfHydroOutflows        > 0.0, 0.0)

    # show some statistics of the data
    if pIndLogConsole == 1:
        print('Reserve margin                        \n', dfReserveMargin.describe       (), '\n')
        print('Maximum CO2 emission                  \n', dfEmission.describe            (), '\n')
        print('Minimum RES energy                    \n', dfRESEnergy.describe           (), '\n')
        print('Electricity demand                    \n', dfDemand.describe              (), '\n')
        print('Inertia                               \n', dfInertia.describe             (), '\n')
        print('Upward   operating reserves           \n', dfUpOperatingReserve.describe  (), '\n')
        print('Downward operating reserves           \n', dfDwOperatingReserve.describe  (), '\n')
        print('Generation                            \n', dfGeneration.describe          (), '\n')
        print('Variable minimum generation           \n', dfVariableMinPower.describe    (), '\n')
        print('Variable maximum generation           \n', dfVariableMaxPower.describe    (), '\n')
        print('Variable minimum consumption          \n', dfVariableMinCharge.describe   (), '\n')
        print('Variable maximum consumption          \n', dfVariableMaxCharge.describe   (), '\n')
        print('Variable minimum storage              \n', dfVariableMinStorage.describe  (), '\n')
        print('Variable maximum storage              \n', dfVariableMaxStorage.describe  (), '\n')
        print('Variable minimum energy               \n', dfVariableMinEnergy.describe   (), '\n')
        print('Variable maximum energy               \n', dfVariableMaxEnergy.describe   (), '\n')
        print('Variable fuel cost                    \n', dfVariableFuelCost.describe    (), '\n')
        print('Variable emission cost                \n', dfVariableEmissionCost.describe(), '\n')
        print('Energy inflows                        \n', dfEnergyInflows.describe       (), '\n')
        print('Energy outflows                       \n', dfEnergyOutflows.describe      (), '\n')
        print('Electric network                      \n', dfNetwork.describe             (), '\n')

        if pIndHydroTopology == 1:
            print('Reservoir                         \n', dfReservoir.describe           (), '\n')
            print('Variable minimum reservoir volume \n', dfVariableMinVolume.describe   (), '\n')
            print('Variable maximum reservoir volume \n', dfVariableMaxVolume.describe   (), '\n')
            print('Hydro inflows                     \n', dfHydroInflows.describe        (), '\n')
            print('Hydro outflows                    \n', dfHydroOutflows.describe       (), '\n')

        if pIndHydrogen == 1:
            print('Hydrogen demand                   \n', dfDemandHydrogen.describe      (), '\n')
            print('Hydrogen pipeline network         \n', dfNetworkHydrogen.describe     (), '\n')

        if pIndHeat == 1:
            print('Heat demand                       \n', dfDemandHeat.describe          (), '\n')
            print('Heat pipe network                 \n', dfNetworkHeat.describe         (), '\n')

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
    mTEPES.nd   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.ni   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.nf   = Set(initialize=dictSets['nd'  ], ordered=False, doc='nodes'                           )
    mTEPES.zn   = Set(initialize=dictSets['zn'  ], ordered=False, doc='zones'                           )
    mTEPES.ar   = Set(initialize=dictSets['ar'  ], ordered=False, doc='areas'                           )
    mTEPES.rg   = Set(initialize=dictSets['rg'  ], ordered=False, doc='regions'                         )
    mTEPES.cc   = Set(initialize=dictSets['cc'  ], ordered=False, doc='circuits'                        )
    mTEPES.c2   = Set(initialize=dictSets['cc'  ], ordered=False, doc='circuits'                        )
    mTEPES.lt   = Set(initialize=dictSets['lt'  ], ordered=False, doc='electric line types'             )
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

        mTEPES.rs  = Set(initialize=[], ordered=False, doc='reservoirs'               )
        mTEPES.r2h = Set(initialize=[], ordered=False, doc='reservoir to hydro'       )
        mTEPES.h2r = Set(initialize=[], ordered=False, doc='hydro to reservoir'       )
        mTEPES.r2r = Set(initialize=[], ordered=False, doc='reservoir to reservoir'   )
        mTEPES.p2r = Set(initialize=[], ordered=False, doc='pumped-hydro to reservoir')
        mTEPES.r2p = Set(initialize=[], ordered=False, doc='reservoir to pumped-hydro')

        if count_lines_in_csv(     _path+'/oT_Dict_Reservoir_'             +CaseName+'.csv') > 1:
            dictSets.load(filename=_path+'/oT_Dict_Reservoir_'             +CaseName+'.csv', set='rs' , format='set')
            mTEPES.del_component(mTEPES.rs)
            mTEPES.rs  = Set(initialize=dictSets['rs' ], ordered=False, doc='reservoirs'               )
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
        pass

    #%% parameters
    pIndBinGenInvest       = dfOption   ['IndBinGenInvest'    ].iloc[0].astype('int')         # Indicator of binary generation        expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinGenRetire       = dfOption   ['IndBinGenRetirement'].iloc[0].astype('int')         # Indicator of binary generation        retirement decisions,0 continuous       - 1 binary - 2 no retirement variables
    pIndBinRsrInvest       = dfOption   ['IndBinRsrInvest'    ].iloc[0].astype('int')         # Indicator of binary reservoir         expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetElecInvest   = dfOption   ['IndBinNetInvest'    ].iloc[0].astype('int')         # Indicator of binary electric network  expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetH2Invest     = dfOption   ['IndBinNetH2Invest'  ].iloc[0].astype('int')         # Indicator of binary hydrogen pipeline expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetHeatInvest   = dfOption   ['IndBinNetHeatInvest'].iloc[0].astype('int')         # Indicator of binary heat     pipe     expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinGenOperat       = dfOption   ['IndBinGenOperat'    ].iloc[0].astype('int')         # Indicator of binary generation        operation decisions, 0 continuous       - 1 binary
    pIndBinSingleNode      = dfOption   ['IndBinSingleNode'   ].iloc[0].astype('int')         # Indicator of single node although with electric network,   0 electric network - 1 single node
    pIndBinGenRamps        = dfOption   ['IndBinGenRamps'     ].iloc[0].astype('int')         # Indicator of ramp constraints,                             0 no ramps         - 1 ramp constraints
    pIndBinGenMinTime      = dfOption   ['IndBinGenMinTime'   ].iloc[0].astype('int')         # Indicator of minimum up/downtime constraints,              0 no min time      - 1 min time constraints
    pIndBinLineCommit      = dfOption   ['IndBinLineCommit'   ].iloc[0].astype('int')         # Indicator of binary electric network switching decisions,  0 continuous       - 1 binary
    pIndBinNetLosses       = dfOption   ['IndBinNetLosses'    ].iloc[0].astype('int')         # Indicator of        electric network losses,               0 lossless         - 1 ohmic losses
    pENSCost               = dfParameter['ENSCost'            ].iloc[0] * 1e-3                # cost of energy   not served               [MEUR/GWh]
    pH2NSCost              = dfParameter['HNSCost'            ].iloc[0] * 1e-3                # cost of hydrogen not served               [MEUR/tH2]
    pHeatNSCost            = dfParameter['HTNSCost'           ].iloc[0] * 1e-3                # cost of heat     not served               [MEUR/GWh]
    pCO2Cost               = dfParameter['CO2Cost'            ].iloc[0]                       # cost of CO2 emission                      [EUR/tCO2]
    pEconomicBaseYear      = dfParameter['EconomicBaseYear'   ].iloc[0]                       # economic base year                        [year]
    pAnnualDiscRate        = dfParameter['AnnualDiscountRate' ].iloc[0]                       # annual discount rate                      [p.u.]
    pUpReserveActivation   = dfParameter['UpReserveActivation'].iloc[0]                       # upward   reserve activation               [p.u.]
    pDwReserveActivation   = dfParameter['DwReserveActivation'].iloc[0]                       # downward reserve activation               [p.u.]
    pMinRatioDwUp          = dfParameter['MinRatioDwUp'       ].iloc[0]                       # minimum ratio down up operating reserves  [p.u.]
    pMaxRatioDwUp          = dfParameter['MaxRatioDwUp'       ].iloc[0]                       # maximum ratio down up operating reserves  [p.u.]
    pSBase                 = dfParameter['SBase'              ].iloc[0] * 1e-3                # base power                                [GW]
    pReferenceNode         = dfParameter['ReferenceNode'      ].iloc[0]                       # reference node
    pTimeStep              = dfParameter['TimeStep'           ].iloc[0].astype('int')         # duration of the unit time step            [h]

    pPeriodWeight          = dfPeriod       ['Weight'        ].astype('int')             # weights of periods                        [p.u.]
    pScenProb              = dfScenario     ['Probability'   ].astype('float')           # probabilities of scenarios                [p.u.]
    pStageWeight           = dfStage        ['Weight'        ].astype('float')           # weights of stages
    pDuration              = dfDuration     ['Duration'      ] * pTimeStep               # duration of load levels                   [h]
    pLevelToStage          = dfDuration     ['Stage'         ]                           # load levels assignment to stages
    pReserveMargin         = dfReserveMargin['ReserveMargin' ]                           # minimum adequacy reserve margin           [p.u.]
    pEmission              = dfEmission     ['CO2Emission'   ]                           # maximum CO2 emission                      [MtCO2]
    pRESEnergy             = dfRESEnergy    ['RESEnergy'     ]                           # minimum RES energy                        [GWh]
    pDemandElec            = dfDemand              [mTEPES.nd] * 1e-3                    # electric demand                           [GW]
    pSystemInertia         = dfInertia             [mTEPES.ar]                           # inertia                                   [s]
    pOperReserveUp         = dfUpOperatingReserve  [mTEPES.ar] * 1e-3                    # upward   operating reserve                [GW]
    pOperReserveDw         = dfDwOperatingReserve  [mTEPES.ar] * 1e-3                    # downward operating reserve                [GW]
    pVariableMinPowerElec  = dfVariableMinPower    [mTEPES.gg] * 1e-3                    # dynamic variable minimum power            [GW]
    pVariableMaxPowerElec  = dfVariableMaxPower    [mTEPES.gg] * 1e-3                    # dynamic variable maximum power            [GW]
    pVariableMinCharge     = dfVariableMinCharge   [mTEPES.gg] * 1e-3                    # dynamic variable minimum charge           [GW]
    pVariableMaxCharge     = dfVariableMaxCharge   [mTEPES.gg] * 1e-3                    # dynamic variable maximum charge           [GW]
    pVariableMinStorage    = dfVariableMinStorage  [mTEPES.gg]                           # dynamic variable minimum storage          [GWh]
    pVariableMaxStorage    = dfVariableMaxStorage  [mTEPES.gg]                           # dynamic variable maximum storage          [GWh]
    pVariableMinEnergy     = dfVariableMinEnergy   [mTEPES.gg] * 1e-3                    # dynamic variable minimum energy           [GW]
    pVariableMaxEnergy     = dfVariableMaxEnergy   [mTEPES.gg] * 1e-3                    # dynamic variable maximum energy           [GW]
    pVariableFuelCost      = dfVariableFuelCost    [mTEPES.gg]                           # dynamic variable fuel cost                [EUR/Mcal]
    pVariableEmissionCost  = dfVariableEmissionCost[mTEPES.gg]                           # dynamic variable fuel cost                [EUR/tCO2]
    pEnergyInflows         = dfEnergyInflows       [mTEPES.gg] * 1e-3                    # dynamic energy inflows                    [GW]
    pEnergyOutflows        = dfEnergyOutflows      [mTEPES.gg] * 1e-3                    # dynamic energy outflows                   [GW]

    if pIndHydroTopology == 1:
        pVariableMinVolume = dfVariableMinVolume   [mTEPES.rs]                           # dynamic variable minimum reservoir volume [hm3]
        pVariableMaxVolume = dfVariableMaxVolume   [mTEPES.rs]                           # dynamic variable maximum reservoir volume [hm3]
        pHydroInflows      = dfHydroInflows        [mTEPES.rs]                           # dynamic hydro inflows                     [m3/s]
        pHydroOutflows     = dfHydroOutflows       [mTEPES.rs]                           # dynamic hydro outflows                    [m3/s]

    if pIndHydrogen == 1:
        pDemandH2          = dfDemandHydrogen      [mTEPES.nd]                           # hydrogen demand                           [tH2/h]

    if pIndHeat == 1:
        pDemandHeat        = dfDemandHeat          [mTEPES.nd] * 1e-3                    # heat     demand                           [GW]

    if pTimeStep > 1:
        # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for the remaining parameters
        if  pDemandElec.sum().sum()            :
            pDemandElec            = pDemandElec.rolling              (pTimeStep).mean()
            pDemandElec.fillna           (0.0, inplace=True)
        if  pSystemInertia.sum().sum()         :
            pSystemInertia         = pSystemInertia.rolling           (pTimeStep).mean()
            pSystemInertia.fillna        (0.0, inplace=True)
        if  pOperReserveUp.sum().sum()         :
            pOperReserveUp         = pOperReserveUp.rolling           (pTimeStep).mean()
            pOperReserveUp.fillna        (0.0, inplace=True)
        if  pOperReserveDw.sum().sum()         :
            pOperReserveDw         = pOperReserveDw.rolling           (pTimeStep).mean()
            pOperReserveDw.fillna        (0.0, inplace=True)
        if  pVariableMinPowerElec.sum().sum()      :
            pVariableMinPowerElec      = pVariableMinPowerElec.rolling(pTimeStep).mean()
            pVariableMinPowerElec.fillna     (0.0, inplace=True)
        if  pVariableMaxPowerElec.sum().sum()      :
            pVariableMaxPowerElec      = pVariableMaxPowerElec.rolling(pTimeStep).mean()
            pVariableMaxPowerElec.fillna     (0.0, inplace=True)
        if  pVariableMinCharge.sum().sum()     :
            pVariableMinCharge     = pVariableMinCharge.rolling       (pTimeStep).mean()
            pVariableMinCharge.fillna    (0.0, inplace=True)
        if  pVariableMaxCharge.sum().sum()     :
            pVariableMaxCharge     = pVariableMaxCharge.rolling       (pTimeStep).mean()
            pVariableMaxCharge.fillna    (0.0, inplace=True)
        if  pVariableMinStorage.sum().sum()    :
            pVariableMinStorage    = pVariableMinStorage.rolling      (pTimeStep).mean()
            pVariableMinStorage.fillna   (0.0, inplace=True)
        if  pVariableMaxStorage.sum().sum()    :
            pVariableMaxStorage    = pVariableMaxStorage.rolling      (pTimeStep).mean()
            pVariableMaxStorage.fillna   (0.0, inplace=True)
        if  pVariableMinEnergy.sum().sum()     :
            pVariableMinEnergy     = pVariableMinEnergy.rolling       (pTimeStep).mean()
            pVariableMinEnergy.fillna    (0.0, inplace=True)
        if  pVariableMaxEnergy.sum().sum()     :
            pVariableMaxEnergy     = pVariableMaxEnergy.rolling       (pTimeStep).mean()
            pVariableMaxEnergy.fillna    (0.0, inplace=True)
        if  pVariableFuelCost.sum().sum()      :
            pVariableFuelCost      = pVariableFuelCost.rolling        (pTimeStep).mean()
            pVariableFuelCost.fillna     (0.0, inplace=True)
        if  pVariableEmissionCost.sum().sum()      :
            pVariableEmissionCost  = pVariableEmissionCost.rolling    (pTimeStep).mean()
            pVariableEmissionCost.fillna (0.0, inplace=True)
        if  pEnergyInflows.sum().sum()         :
            pEnergyInflows         = pEnergyInflows.rolling           (pTimeStep).mean()
            pEnergyInflows.fillna        (0.0, inplace=True)
        if  pEnergyOutflows.sum().sum()        :
            pEnergyOutflows        = pEnergyOutflows.rolling          (pTimeStep).mean()
            pEnergyOutflows.fillna       (0.0, inplace=True)
        if pIndHydroTopology == 1:
            if  pVariableMinVolume.sum().sum() :
                pVariableMinVolume = pVariableMinVolume.rolling       (pTimeStep).mean()
                pVariableMinVolume.fillna(0.0, inplace=True)
            if  pVariableMaxVolume.sum().sum() :
                pVariableMaxVolume = pVariableMaxVolume.rolling       (pTimeStep).mean()
                pVariableMaxVolume.fillna(0.0, inplace=True)
            if  pHydroInflows.sum().sum()      :
                pHydroInflows       = pHydroInflows.rolling           (pTimeStep).mean()
                pHydroInflows.fillna     (0.0, inplace=True)
            if  pHydroOutflows.sum().sum()     :
                pHydroOutflows      = pHydroOutflows.rolling          (pTimeStep).mean()
                pHydroOutflows.fillna    (0.0, inplace=True)
        if pIndHydrogen == 1:
            if  pDemandH2.sum().sum()          :
                pDemandH2           = pDemandH2.rolling               (pTimeStep).mean()
                pDemandH2.fillna         (0.0, inplace=True)
        if pIndHeat == 1:
            if  pDemandHeat.sum().sum()          :
                pDemandHeat         = pDemandHeat.rolling             (pTimeStep).mean()
                pDemandHeat.fillna       (0.0, inplace=True)

        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for n in range(pTimeStep-2,-1,-1):
            pDuration.iloc[[range(n,len(mTEPES.nn),pTimeStep)]] = 0

    #%% generation parameters
    pGenToNode                  = dfGeneration  ['Node'                      ]                                                      # generator location in node
    pGenToTechnology            = dfGeneration  ['Technology'                ]                                                      # generator association to technology
    pGenToExclusiveGen          = dfGeneration  ['MutuallyExclusive'         ]                                                      # mutually exclusive generator
    pIndBinUnitInvest           = dfGeneration  ['BinaryInvestment'          ]                                                      # binary unit investment decision              [Yes]
    pIndBinUnitRetire           = dfGeneration  ['BinaryRetirement'          ]                                                      # binary unit retirement decision              [Yes]
    pIndBinUnitCommit           = dfGeneration  ['BinaryCommitment'          ]                                                      # binary unit commitment decision              [Yes]
    pIndBinStorInvest           = dfGeneration  ['StorageInvestment'         ]                                                      # storage linked to generation investment      [Yes]
    pIndOperReserve             = dfGeneration  ['NoOperatingReserve'        ]                                                      # no contribution to operating reserve         [Yes]
    pMustRun                    = dfGeneration  ['MustRun'                   ]                                                      # must-run unit                                [Yes]
    pInertia                    = dfGeneration  ['Inertia'                   ]                                                      # inertia constant                             [s]
    pElecGenPeriodIni           = dfGeneration  ['InitialPeriod'             ]                                                      # initial period                               [year]
    pElecGenPeriodFin           = dfGeneration  ['FinalPeriod'               ]                                                      # final   period                               [year]
    pAvailability               = dfGeneration  ['Availability'              ]                                                      # unit availability for adequacy               [p.u.]
    pEFOR                       = dfGeneration  ['EFOR'                      ]                                                      # EFOR                                         [p.u.]
    pRatedMinPowerElec          = dfGeneration  ['MinimumPower'              ] * 1e-3 * (1.0-dfGeneration['EFOR'])                  # rated minimum electric power                 [GW]
    pRatedMaxPowerElec          = dfGeneration  ['MaximumPower'              ] * 1e-3 * (1.0-dfGeneration['EFOR'])                  # rated maximum electric power                 [GW]
    pRatedMinPowerHeat          = dfGeneration  ['MinimumPowerHeat'          ] * 1e-3 * (1.0-dfGeneration['EFOR'])                  # rated minimum heat     power                 [GW]
    pRatedMaxPowerHeat          = dfGeneration  ['MaximumPowerHeat'          ] * 1e-3 * (1.0-dfGeneration['EFOR'])                  # rated maximum heat     power                 [GW]
    pRatedLinearFuelCost        = dfGeneration  ['LinearTerm'                ] * 1e-3 *      dfGeneration['FuelCost']               # fuel     term variable cost                  [MEUR/GWh]
    pRatedConstantVarCost       = dfGeneration  ['ConstantTerm'              ] * 1e-6 *      dfGeneration['FuelCost']               # constant term variable cost                  [MEUR/h]
    pLinearOMCost               = dfGeneration  ['OMVariableCost'            ] * 1e-3                                               # O&M      term variable cost                  [MEUR/GWh]
    pOperReserveCost            = dfGeneration  ['OperReserveCost'           ] * 1e-3                                               # operating reserve      cost                  [MEUR/GW]
    pStartUpCost                = dfGeneration  ['StartUpCost'               ]                                                      # startup  cost                                [MEUR]
    pShutDownCost               = dfGeneration  ['ShutDownCost'              ]                                                      # shutdown cost                                [MEUR]
    pRampUp                     = dfGeneration  ['RampUp'                    ] * 1e-3                                               # ramp up   rate                               [GW/h]
    pRampDw                     = dfGeneration  ['RampDown'                  ] * 1e-3                                               # ramp down rate                               [GW/h]
    pEmissionCost               = dfGeneration  ['CO2EmissionRate'           ] * 1e-3 * pCO2Cost                                    # CO2 emission  cost                           [MEUR/GWh]
    pEmissionRate               = dfGeneration  ['CO2EmissionRate'           ]                                                      # CO2 emission  rate                           [tCO2/MWh]
    pUpTime                     = dfGeneration  ['UpTime'                    ]                                                      # minimum up     time                          [h]
    pDwTime                     = dfGeneration  ['DownTime'                  ]                                                      # minimum down   time                          [h]
    pStableTime                 = dfGeneration  ['StableTime'                ]                                                      # minimum stable time                          [h]
    pShiftTime                  = dfGeneration  ['ShiftTime'                 ]                                                      # maximum shift time for DSM                   [h]
    pGenInvestCost              = dfGeneration  ['FixedInvestmentCost'       ] *             dfGeneration['FixedChargeRate']        # generation fixed cost                        [MEUR]
    pGenRetireCost              = dfGeneration  ['FixedRetirementCost'       ] *             dfGeneration['FixedChargeRate']        # generation fixed retirement cost             [MEUR]
    pRatedMinCharge             = dfGeneration  ['MinimumCharge'             ] * 1e-3                                               # rated minimum ESS charge                     [GW]
    pRatedMaxCharge             = dfGeneration  ['MaximumCharge'             ] * 1e-3                                               # rated maximum ESS charge                     [GW]
    pRatedMinStorage            = dfGeneration  ['MinimumStorage'            ]                                                      # rated minimum ESS storage                    [GWh]
    pRatedMaxStorage            = dfGeneration  ['MaximumStorage'            ]                                                      # rated maximum ESS storage                    [GWh]
    pInitialInventory           = dfGeneration  ['InitialStorage'            ]                                                      # initial       ESS storage                    [GWh]
    pProductionFunctionHydro    = dfGeneration  ['ProductionFunctionHydro'   ]                                                      # production function of a hydropower plant    [kWh/m3]
    pProductionFunctionH2       = dfGeneration  ['ProductionFunctionH2'      ] * 1e-3                                               # production function of an electrolyzer       [kWh/gH2]
    pProductionFunctionHeat     = dfGeneration  ['ProductionFunctionHeat'    ]                                                      # production function of a heat pump           [kWh/kWh]
    pProductionFunctionH2ToHeat = dfGeneration  ['ProductionFunctionH2ToHeat'] * 1e-3                                               # production function of a boiler using H2     [gH2/kWh]
    pEfficiency                 = dfGeneration  ['Efficiency'                ]                                                      #               ESS round-trip efficiency      [p.u.]
    pStorageType                = dfGeneration  ['StorageType'               ]                                                      #               ESS storage  type
    pOutflowsType               = dfGeneration  ['OutflowsType'              ]                                                      #               ESS outflows type
    pEnergyType                 = dfGeneration  ['EnergyType'                ]                                                      #               unit  energy type
    pRMaxReactivePower          = dfGeneration  ['MaximumReactivePower'      ] * 1e-3                                               # rated maximum reactive power                 [Gvar]
    pGenLoInvest                = dfGeneration  ['InvestmentLo'              ]                                                      # Lower bound of the investment decision       [p.u.]
    pGenUpInvest                = dfGeneration  ['InvestmentUp'              ]                                                      # Upper bound of the investment decision       [p.u.]
    pGenLoRetire                = dfGeneration  ['RetirementLo'              ]                                                      # Lower bound of the retirement decision       [p.u.]
    pGenUpRetire                = dfGeneration  ['RetirementUp'              ]                                                      # Upper bound of the retirement decision       [p.u.]

    pRatedLinearOperCost        = pRatedLinearFuelCost + pEmissionCost
    pRatedLinearVarCost         = pRatedLinearFuelCost + pLinearOMCost

    if pIndHydroTopology == 1:
        pReservoirType          = dfReservoir   ['StorageType'               ]                                                      #               reservoir type
        pWaterOutfType          = dfReservoir   ['OutflowsType'              ]                                                      #           water outflow type
        pRatedMinVolume         = dfReservoir   ['MinimumStorage'            ]                                                      # rated minimum reservoir volume               [hm3]
        pRatedMaxVolume         = dfReservoir   ['MaximumStorage'            ]                                                      # rated maximum reservoir volume               [hm3]
        pInitialVolume          = dfReservoir   ['InitialStorage'            ]                                                      # initial       reservoir volume               [hm3]
        pIndBinRsrvInvest       = dfReservoir   ['BinaryInvestment'          ]                                                      # binary reservoir investment decision         [Yes]
        pRsrInvestCost          = dfReservoir   ['FixedInvestmentCost'       ] *             dfReservoir['FixedChargeRate']         #        reservoir fixed cost                  [MEUR]
        pRsrPeriodIni           = dfReservoir   ['InitialPeriod'             ]                                                      # initial period                               [year]
        pRsrPeriodFin           = dfReservoir   ['FinalPeriod'               ]                                                      # final   period                               [year]

    pNodeLat                    = dfNodeLocation['Latitude'                  ]                                                      # node latitude                                [º]
    pNodeLon                    = dfNodeLocation['Longitude'                 ]                                                      # node longitude                               [º]

    pLineType                   = dfNetwork     ['LineType'                  ]                                                      # electric line type
    pLineLength                 = dfNetwork     ['Length'                    ]                                                      # electric line length                         [km]
    pLineVoltage                = dfNetwork     ['Voltage'                   ]                                                      # electric line voltage                        [kV]
    pElecNetPeriodIni           = dfNetwork     ['InitialPeriod'             ]                                                      # initial period
    pElecNetPeriodFin           = dfNetwork     ['FinalPeriod'               ]                                                      # final   period
    pLineLossFactor             = dfNetwork     ['LossFactor'                ]                                                      # electric line loss factor                    [p.u.]
    pLineR                      = dfNetwork     ['Resistance'                ]                                                      # electric line resistance                     [p.u.]
    pLineX                      = dfNetwork     ['Reactance'                 ].sort_index()                                         # electric line reactance                      [p.u.]
    pLineBsh                    = dfNetwork     ['Susceptance'               ]                                                      # electric line susceptance                    [p.u.]
    pLineTAP                    = dfNetwork     ['Tap'                       ]                                                      # tap changer                                  [p.u.]
    pLineNTCFrw                 = dfNetwork     ['TTC'                       ] * 1e-3 *      dfNetwork['SecurityFactor' ]           # net transfer capacity in forward  direction  [GW]
    pLineNTCBck                 = dfNetwork     ['TTCBck'                    ] * 1e-3 *      dfNetwork['SecurityFactor' ]           # net transfer capacity in backward direction  [GW]
    pNetFixedCost               = dfNetwork     ['FixedInvestmentCost'       ] *             dfNetwork['FixedChargeRate']           # electric network    fixed cost               [MEUR]
    pIndBinLineSwitch           = dfNetwork     ['Switching'                 ]                                                      # binary electric line switching  decision     [Yes]
    pIndBinLineInvest           = dfNetwork     ['BinaryInvestment'          ]                                                      # binary electric line investment decision     [Yes]
    pSwitchOnTime               = dfNetwork     ['SwOnTime'                  ].astype('int')                                        # minimum on  time                             [h]
    pSwitchOffTime              = dfNetwork     ['SwOffTime'                 ].astype('int')                                        # minimum off time                             [h]
    pAngMin                     = dfNetwork     ['AngMin'                    ] * math.pi / 180                                      # Min phase angle difference                   [rad]
    pAngMax                     = dfNetwork     ['AngMax'                    ] * math.pi / 180                                      # Max phase angle difference                   [rad]
    pNetLoInvest                = dfNetwork     ['InvestmentLo'              ]                                                      # Lower bound of the investment decision       [p.u.]
    pNetUpInvest                = dfNetwork     ['InvestmentUp'              ]                                                      # Upper bound of the investment decision       [p.u.]

    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    pLineNTCBck     = pLineNTCBck.where (pLineNTCBck  > 0.0, pLineNTCFrw)
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    pLineNTCFrw     = pLineNTCFrw.where (pLineNTCFrw  > 0.0, pLineNTCBck)
    # replace pGenUpInvest = 0.0 by 1.0
    pGenUpInvest    = pGenUpInvest.where(pGenUpInvest > 0.0, 1.0        )
    # replace pGenUpRetire = 0.0 by 1.0
    pGenUpRetire    = pGenUpRetire.where(pGenUpRetire > 0.0, 1.0        )
    # replace pNetUpInvest = 0.0 by 1.0
    pNetUpInvest    = pNetUpInvest.where(pNetUpInvest > 0.0, 1.0        )

    # minimum up- and downtime converted to an integer number of time steps
    pSwitchOnTime  = round(pSwitchOnTime /pTimeStep).astype('int')
    pSwitchOffTime = round(pSwitchOffTime/pTimeStep).astype('int')

    if pIndHydrogen == 1:
        pH2PipeLength       = dfNetworkHydrogen['Length'             ]                                                  # hydrogen line length                         [km]
        pH2PipePeriodIni    = dfNetworkHydrogen['InitialPeriod'      ]                                                  # initial period
        pH2PipePeriodFin    = dfNetworkHydrogen['FinalPeriod'        ]                                                  # final   period
        pH2PipeNTCFrw       = dfNetworkHydrogen['TTC'                ] *      dfNetworkHydrogen['SecurityFactor' ]      # net transfer capacity in forward  direction  [tH2]
        pH2PipeNTCBck       = dfNetworkHydrogen['TTCBck'             ] *      dfNetworkHydrogen['SecurityFactor' ]      # net transfer capacity in backward direction  [tH2]
        pH2PipeFixedCost    = dfNetworkHydrogen['FixedInvestmentCost'] *      dfNetworkHydrogen['FixedChargeRate']      # hydrogen network    fixed cost               [MEUR]
        pIndBinH2PipeInvest = dfNetworkHydrogen['BinaryInvestment'   ]                                                  # binary hydrogen pipeline investment decision [Yes]
        pH2PipeLoInvest     = dfNetworkHydrogen['InvestmentLo'       ]                                                  # Lower bound of the investment decision       [p.u.]
        pH2PipeUpInvest     = dfNetworkHydrogen['InvestmentUp'       ]                                                  # Upper bound of the investment decision       [p.u.]

        # replace pH2PipeNTCBck = 0.0 by pH2PipeNTCFrw
        pH2PipeNTCBck     = pH2PipeNTCBck.where  (pH2PipeNTCBck   > 0.0, pH2PipeNTCFrw)
        # replace pH2PipeNTCFrw = 0.0 by pH2PipeNTCBck
        pH2PipeNTCFrw     = pH2PipeNTCFrw.where  (pH2PipeNTCFrw   > 0.0, pH2PipeNTCBck)
        # replace pH2PipeUpInvest = 0.0 by 1.0
        pH2PipeUpInvest   = pH2PipeUpInvest.where(pH2PipeUpInvest > 0.0, 1.0          )

    if pIndHeat == 1:
        pHeatPipeLength       = dfNetworkHeat['Length'             ]                                                    # heat pipe length                             [km]
        pHeatPipePeriodIni    = dfNetworkHeat['InitialPeriod'      ]                                                    # initial period
        pHeatPipePeriodFin    = dfNetworkHeat['FinalPeriod'        ]                                                    # final   period
        pHeatPipeNTCFrw       = dfNetworkHeat['TTC'                ] * 1e-3 * dfNetworkHeat    ['SecurityFactor' ]      # net transfer capacity in forward  direction  [GW]
        pHeatPipeNTCBck       = dfNetworkHeat['TTCBck'             ] * 1e-3 * dfNetworkHeat    ['SecurityFactor' ]      # net transfer capacity in backward direction  [GW]
        pHeatPipeFixedCost    = dfNetworkHeat['FixedInvestmentCost'] *        dfNetworkHeat    ['FixedChargeRate']      # heat    network    fixed cost                [MEUR]
        pIndBinHeatPipeInvest = dfNetworkHeat['BinaryInvestment'   ]                                                    # binary heat     pipe     investment decision [Yes]
        pHeatPipeLoInvest     = dfNetworkHeat['InvestmentLo'       ]                                                    # Lower bound of the investment decision       [p.u.]
        pHeatPipeUpInvest     = dfNetworkHeat['InvestmentUp'       ]                                                    # Upper bound of the investment decision       [p.u.]

        # replace pHeatPipeNTCBck = 0.0 by pHeatPipeNTCFrw
        pHeatPipeNTCBck     = pHeatPipeNTCBck.where  (pHeatPipeNTCBck   > 0.0, pHeatPipeNTCFrw)
        # replace pHeatPipeNTCFrw = 0.0 by pHeatPipeNTCBck
        pHeatPipeNTCFrw     = pHeatPipeNTCFrw.where  (pHeatPipeNTCFrw   > 0.0, pHeatPipeNTCBck)
        # replace pHeatPipeUpInvest = 0.0 by 1.0
        pHeatPipeUpInvest   = pHeatPipeUpInvest.where(pHeatPipeUpInvest > 0.0, 1.0            )

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')

    #%% Getting the branches from the electric network data
    sBr     = [(ni,nf) for (ni,nf,cc) in dfNetwork.index]
    # Dropping duplicate keys
    sBrList = [(ni,nf) for n,(ni,nf)  in enumerate(sBr) if (ni,nf) not in sBr[:n]]

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the electric lines (la), candidate electric lines (lc), candidate DC electric lines (cd), existing DC electric lines (cd), electric lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.p      = Set(initialize=mTEPES.pp,               ordered=True , doc='periods'                         , filter=lambda mTEPES,pp  : pp     in mTEPES.pp  and pPeriodWeight       [pp] >  0.0)
    mTEPES.sc     = Set(initialize=mTEPES.scc,              ordered=True , doc='scenarios'                       , filter=lambda mTEPES,scc : scc    in mTEPES.scc                                    )
    mTEPES.ps     = Set(initialize=mTEPES.p*mTEPES.sc,      ordered=True , doc='periods/scenarios'               , filter=lambda mTEPES,p,sc: (p,sc) in mTEPES.p*mTEPES.sc and pScenProb [p,sc] >  0.0)
    mTEPES.st     = Set(initialize=mTEPES.stt,              ordered=True , doc='stages'                          , filter=lambda mTEPES,stt : stt    in mTEPES.stt and pStageWeight       [stt] >  0.0)
    mTEPES.n      = Set(initialize=mTEPES.nn,               ordered=True , doc='load levels'                     , filter=lambda mTEPES,nn  : nn     in mTEPES.nn  and sum(pDuration  [p,sc,nn] for p,sc in mTEPES.ps) > 0)
    mTEPES.n2     = Set(initialize=mTEPES.nn,               ordered=True , doc='load levels'                     , filter=lambda mTEPES,nn  : nn     in mTEPES.nn  and sum(pDuration  [p,sc,nn] for p,sc in mTEPES.ps) > 0)
    mTEPES.g      = Set(initialize=mTEPES.gg,               ordered=False, doc='generating              units'   , filter=lambda mTEPES,gg  : gg     in mTEPES.gg  and (pRatedMaxPowerElec [gg] >  0.0 or  pRatedMaxCharge[gg] >  0.0 or pRatedMaxPowerHeat    [gg] >  0.0) and pElecGenPeriodIni[gg] <= mTEPES.p.last() and pElecGenPeriodFin[gg] >= mTEPES.p.first() and pGenToNode.reset_index().set_index(['index']).isin(mTEPES.nd)['Node'][gg])  # excludes generators with empty node
    mTEPES.t      = Set(initialize=mTEPES.g ,               ordered=False, doc='thermal                 units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and pRatedLinearOperCost[g ] >  0.0)
    mTEPES.re     = Set(initialize=mTEPES.g ,               ordered=False, doc='RES                     units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and pRatedLinearOperCost[g ] == 0.0 and pRatedMaxStorage[g] == 0.0   and pProductionFunctionH2[g ] == 0.0 and pProductionFunctionHeat[g ] == 0.0  and pProductionFunctionHydro[g ] == 0.0)
    mTEPES.es     = Set(initialize=mTEPES.g ,               ordered=False, doc='ESS                     units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and     (pRatedMaxCharge[g ] >  0.0 or  pRatedMaxStorage[g] >  0.0    or pProductionFunctionH2[g ]  > 0.0  or pProductionFunctionHeat[g ]  > 0.0) and pProductionFunctionHydro[g ] == 0.0)
    mTEPES.h      = Set(initialize=mTEPES.g ,               ordered=False, doc='hydro                   units'   , filter=lambda mTEPES,g   : g      in mTEPES.g                                                                        and pProductionFunctionH2[g ] == 0.0 and pProductionFunctionHeat[g ] == 0.0  and pProductionFunctionHydro[g ]  > 0.0)
    mTEPES.el     = Set(initialize=mTEPES.es,               ordered=False, doc='electrolyzer            units'   , filter=lambda mTEPES,es  : es     in mTEPES.es                                                                       and pProductionFunctionH2[es]  > 0.0 and pProductionFunctionHeat[es] == 0.0  and pProductionFunctionHydro[es] == 0.0)
    mTEPES.hp     = Set(initialize=mTEPES.es,               ordered=False, doc='heat pump & elec boiler units'   , filter=lambda mTEPES,es  : es     in mTEPES.es                                                                       and pProductionFunctionH2[es] == 0.0 and pProductionFunctionHeat[es]  > 0.0  and pProductionFunctionHydro[es] == 0.0)
    mTEPES.ch     = Set(initialize=mTEPES.g ,               ordered=False, doc='CHP       & fuel boiler units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and                                     pRatedMaxPowerHeat[g ] > 0.0 and pProductionFunctionHeat    [g ] == 0.0)
    mTEPES.bo     = Set(initialize=mTEPES.ch,               ordered=False, doc='            fuel boiler units'   , filter=lambda mTEPES,ch  : ch     in mTEPES.ch  and pRatedMaxPowerElec  [ch] == 0.0 and pRatedMaxPowerHeat[ch] > 0.0 and pProductionFunctionHeat    [ch] == 0.0)
    mTEPES.hh     = Set(initialize=mTEPES.bo,               ordered=False, doc='        hydrogen boiler units'   , filter=lambda mTEPES,bo  : bo     in mTEPES.bo                                                                       and pProductionFunctionH2ToHeat[bo] >  0.0)
    mTEPES.gc     = Set(initialize=mTEPES.g ,               ordered=False, doc='candidate               units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and pGenInvestCost      [g ] >  0.0)
    mTEPES.gd     = Set(initialize=mTEPES.g ,               ordered=False, doc='retirement              units'   , filter=lambda mTEPES,g   : g      in mTEPES.g   and pGenRetireCost      [g ] >  0.0)
    mTEPES.ec     = Set(initialize=mTEPES.es,               ordered=False, doc='candidate ESS           units'   , filter=lambda mTEPES,es  : es     in mTEPES.es  and pGenInvestCost      [es] >  0.0)
    mTEPES.bc     = Set(initialize=mTEPES.bo,               ordered=False, doc='candidate boiler        units'   , filter=lambda mTEPES,bo  : bo     in mTEPES.bo  and pGenInvestCost      [bo] >  0.0)
    mTEPES.br     = Set(initialize=sBrList,                 ordered=False, doc='all input       electric branches'                                                                                    )
    mTEPES.ln     = Set(initialize=dfNetwork.index,         ordered=False, doc='all input       electric lines'                                                                                       )
    mTEPES.la     = Set(initialize=mTEPES.ln,               ordered=False, doc='all real        electric lines'  , filter=lambda mTEPES,*ln : ln     in mTEPES.ln  and pLineX              [ln] != 0.0 and pLineNTCFrw[ln] > 0.0 and pLineNTCBck[ln] > 0.0 and pElecNetPeriodIni[ln]  <= mTEPES.p.last() and pElecNetPeriodFin[ln]  >= mTEPES.p.first())
    mTEPES.ls     = Set(initialize=mTEPES.la,               ordered=False, doc='all real switch electric lines'  , filter=lambda mTEPES,*la : la     in mTEPES.la  and pIndBinLineSwitch   [la]       )
    mTEPES.lc     = Set(initialize=mTEPES.la,               ordered=False, doc='candidate       electric lines'  , filter=lambda mTEPES,*la : la     in mTEPES.la  and pNetFixedCost       [la] >  0.0)
    mTEPES.cd     = Set(initialize=mTEPES.la,               ordered=False, doc='             DC electric lines'  , filter=lambda mTEPES,*la : la     in mTEPES.la  and pNetFixedCost       [la] >  0.0 and pLineType[la] == 'DC')
    mTEPES.ed     = Set(initialize=mTEPES.la,               ordered=False, doc='             DC electric lines'  , filter=lambda mTEPES,*la : la     in mTEPES.la  and pNetFixedCost       [la] == 0.0 and pLineType[la] == 'DC')
    mTEPES.ll     = Set(initialize=mTEPES.la,               ordered=False, doc='loss            electric lines'  , filter=lambda mTEPES,*la : la     in mTEPES.la  and pLineLossFactor     [la] >  0.0 and pIndBinNetLosses > 0 )
    mTEPES.rf     = Set(initialize=mTEPES.nd,               ordered=True , doc='reference node'                  , filter=lambda mTEPES,nd  : nd     in                pReferenceNode                 )
    mTEPES.gq     = Set(initialize=mTEPES.gg,               ordered=False, doc='gen    reactive units'           , filter=lambda mTEPES,gg  : gg     in mTEPES.gg  and pRMaxReactivePower  [gg] >  0.0 and                                                     pElecGenPeriodIni[gg]  <= mTEPES.p.last() and pElecGenPeriodFin[gg]  >= mTEPES.p.first())
    mTEPES.sq     = Set(initialize=mTEPES.gg,               ordered=False, doc='synchr reactive units'           , filter=lambda mTEPES,gg  : gg     in mTEPES.gg  and pRMaxReactivePower  [gg] >  0.0 and pGenToTechnology[gg] == 'SynchronousCondenser'  and pElecGenPeriodIni[gg]  <= mTEPES.p.last() and pElecGenPeriodFin[gg]  >= mTEPES.p.first())
    mTEPES.sqc    = Set(initialize=mTEPES.sq,               ordered=False, doc='synchr reactive candidate'                                                                                            )
    mTEPES.shc    = Set(initialize=mTEPES.sq,               ordered=False, doc='shunt           candidate'                                                                                            )
    if pIndHydroTopology == 1:
        mTEPES.rn = Set(initialize=mTEPES.rs,               ordered=False, doc='candidate reservoirs'            , filter=lambda mTEPES,rs  : rs     in mTEPES.rs  and pRsrInvestCost      [rs] >  0.0 and                                                     pRsrPeriodIni[rs]      <= mTEPES.p.last() and pRsrPeriodFin[rs]      >= mTEPES.p.first())
    else:
        mTEPES.rn = Set(initialize=[],                      ordered=False, doc='candidate reservoirs')
    if pIndHydrogen      == 1:
        mTEPES.pn = Set(initialize=dfNetworkHydrogen.index, ordered=False, doc='all input hydrogen pipes'                                                                                             )
        mTEPES.pa = Set(initialize=mTEPES.pn,               ordered=False, doc='all real  hydrogen pipes'        , filter=lambda mTEPES,*pn : pn     in mTEPES.pn  and pH2PipeNTCFrw       [pn] >  0.0 and pH2PipeNTCBck[pn] > 0.0 and                         pH2PipePeriodIni[pn]   <= mTEPES.p.last() and pH2PipePeriodFin[pn]   >= mTEPES.p.first())
        mTEPES.pc = Set(initialize=mTEPES.pa,               ordered=False, doc='candidate hydrogen pipes'        , filter=lambda mTEPES,*pa : pa     in mTEPES.pa  and pH2PipeFixedCost    [pa] >  0.0)
        # existing hydrogen pipelines (pe)
        mTEPES.pe = mTEPES.pa - mTEPES.pc
    else:
        mTEPES.pn = Set(initialize=[],                      ordered=False, doc='all input hydrogen pipes')
        mTEPES.pa = Set(initialize=[],                      ordered=False, doc='all real  hydrogen pipes')
        mTEPES.pc = Set(initialize=[],                      ordered=False, doc='candidate hydrogen pipes')

    if pIndHeat        == 1:
        mTEPES.hn = Set(initialize=dfNetworkHeat.index,     ordered=False, doc='all input heat pipes'                                                                                               )
        mTEPES.ha = Set(initialize=mTEPES.hn,               ordered=False, doc='all real  heat pipes'          , filter=lambda mTEPES,*hn : hn     in mTEPES.hn  and pHeatPipeNTCFrw     [hn] >  0.0 and pHeatPipeNTCBck[hn] > 0.0 and pHeatPipePeriodIni[hn] <= mTEPES.p.last() and pHeatPipePeriodFin[hn] >= mTEPES.p.first())
        mTEPES.hc = Set(initialize=mTEPES.ha,               ordered=False, doc='candidate heat pipes'          , filter=lambda mTEPES,*ha : ha     in mTEPES.ha  and pHeatPipeFixedCost  [ha] >  0.0)
        # existing heat pipes (he)
        mTEPES.he = mTEPES.ha - mTEPES.hc
    else:
        mTEPES.hn = Set(initialize=[],                      ordered=False, doc='all input heat pipes')
        mTEPES.ha = Set(initialize=[],                      ordered=False, doc='all real  heat pipes')
        mTEPES.hc = Set(initialize=[],                      ordered=False, doc='candidate heat pipes')

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
    pStageToLevel = pLevelToStage.reset_index().set_index(['level_0','level_1','Stage'])
    pStageToLevel = pStageToLevel.loc[pStageToLevel['level_2'].keys().isin(mTEPES.ps*mTEPES.st)]
    pStageToLevel = pStageToLevel.loc[pStageToLevel['level_2'].isin(mTEPES.n)].reset_index().set_index(['level_0','level_1','Stage','level_2'])

    mTEPES.s2n = Set(initialize=pStageToLevel.index, ordered=False, doc='load level to stage')
    # all the stages must have the same duration
    pStageDuration = pd.Series([sum(pDuration[p,sc,n] for p,sc,st2,n in mTEPES.s2n if st2 == st) for st in mTEPES.st], index=mTEPES.st)
    # for st in mTEPES.st:
    #     if mTEPES.st.ord(st) > 1 and pStageDuration[st] != pStageDuration[mTEPES.st.prev(st)]:
    #         assert (0 == 1)

    # delete all the load level belonging to stages with duration equal to zero
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.n  = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.nn and sum(pDuration[p,sc,nn] for p,sc in mTEPES.ps) > 0)
    mTEPES.n2 = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.nn and sum(pDuration[p,sc,nn] for p,sc in mTEPES.ps) > 0)

    # instrumental sets
    mTEPES.pg        = [(p,     g       ) for p,     g        in mTEPES.p  *mTEPES.g   if pElecGenPeriodIni[g ] <= p and pElecGenPeriodFin[g ] >= p]
    mTEPES.pgc       = [(p,     gc      ) for p,     gc       in mTEPES.p  *mTEPES.gc  if (p,gc)  in mTEPES.pg]
    mTEPES.pnr       = [(p,     nr      ) for p,     nr       in mTEPES.p  *mTEPES.nr  if (p,nr)  in mTEPES.pg]
    mTEPES.pch       = [(p,     ch      ) for p,     ch       in mTEPES.p  *mTEPES.ch  if (p,ch)  in mTEPES.pg]
    mTEPES.pchp      = [(p,     chp     ) for p,     chp      in mTEPES.p  *mTEPES.chp if (p,chp) in mTEPES.pg]
    mTEPES.pbo       = [(p,     bo      ) for p,     bo       in mTEPES.p  *mTEPES.bo  if (p,bo)  in mTEPES.pg]
    mTEPES.php       = [(p,     hp      ) for p,     hp       in mTEPES.p  *mTEPES.hp  if (p,hp)  in mTEPES.pg]
    mTEPES.phh       = [(p,     hh      ) for p,     hh       in mTEPES.p  *mTEPES.hh  if (p,hh)  in mTEPES.pg]
    mTEPES.pbc       = [(p,     bc      ) for p,     bc       in mTEPES.p  *mTEPES.bc  if (p,bc)  in mTEPES.pg]
    mTEPES.pgb       = [(p,     gb      ) for p,     gb       in mTEPES.p  *mTEPES.gb  if (p,gb)  in mTEPES.pg]
    mTEPES.peb       = [(p,     eb      ) for p,     eb       in mTEPES.p  *mTEPES.eb  if (p,eb)  in mTEPES.pg]
    mTEPES.pes       = [(p,     es      ) for p,     es       in mTEPES.p  *mTEPES.es  if (p,es)  in mTEPES.pg]
    mTEPES.pec       = [(p,     ec      ) for p,     ec       in mTEPES.p  *mTEPES.ec  if (p,ec)  in mTEPES.pg]
    mTEPES.peh       = [(p,     eh      ) for p,     eh       in mTEPES.p  *mTEPES.eh  if (p,eh)  in mTEPES.pg]
    mTEPES.pre       = [(p,     re      ) for p,     re       in mTEPES.p  *mTEPES.re  if (p,re)  in mTEPES.pg]
    mTEPES.ph        = [(p,     h       ) for p,     h        in mTEPES.p  *mTEPES.h   if (p,h )  in mTEPES.pg]
    mTEPES.pgd       = [(p,     gd      ) for p,     gd       in mTEPES.p  *mTEPES.gd  if (p,gd)  in mTEPES.pg]
    mTEPES.par       = [(p,     ar      ) for p,     ar       in mTEPES.p  *mTEPES.ar                                                                                   ]
    mTEPES.pla       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.la  if pElecNetPeriodIni[ni,nf,cc] <= p and pElecNetPeriodFin[ni,nf,cc] >= p]
    mTEPES.plc       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.lc  if (p,ni,nf,cc) in mTEPES.pla]
    mTEPES.pll       = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ll  if (p,ni,nf,cc) in mTEPES.pla]

    mTEPES.psc       = [(p,sc     )       for p,sc            in mTEPES.p  *mTEPES.sc]
    mTEPES.psg       = [(p,sc,  g )       for p,sc,  g        in mTEPES.ps *mTEPES.g   if (p,g )  in mTEPES.pg  ]
    mTEPES.psnr      = [(p,sc,  nr)       for p,sc,  nr       in mTEPES.ps *mTEPES.nr  if (p,nr)  in mTEPES.pnr ]
    mTEPES.pses      = [(p,sc,  es)       for p,sc,  es       in mTEPES.ps *mTEPES.es  if (p,es)  in mTEPES.pes ]
    mTEPES.pseh      = [(p,sc,  eh)       for p,sc,  eh       in mTEPES.ps *mTEPES.eh  if (p,eh)  in mTEPES.peh ]
    mTEPES.psn       = [(p,sc,n   )       for p,sc,n          in mTEPES.ps *mTEPES.n                            ]
    mTEPES.psng      = [(p,sc,n,g )       for p,sc,n,g        in mTEPES.psn*mTEPES.g   if (p,g )  in mTEPES.pg  ]
    mTEPES.psngc     = [(p,sc,n,gc)       for p,sc,n,gc       in mTEPES.psn*mTEPES.gc  if (p,gc)  in mTEPES.pgc ]
    mTEPES.psngb     = [(p,sc,n,gb)       for p,sc,n,gb       in mTEPES.psn*mTEPES.gb  if (p,gb)  in mTEPES.pgc ]
    mTEPES.psnre     = [(p,sc,n,re)       for p,sc,n,re       in mTEPES.psn*mTEPES.re  if (p,re)  in mTEPES.pre ]
    mTEPES.psnnr     = [(p,sc,n,nr)       for p,sc,n,nr       in mTEPES.psn*mTEPES.nr  if (p,nr)  in mTEPES.pnr ]
    mTEPES.psnch     = [(p,sc,n,ch)       for p,sc,n,ch       in mTEPES.psn*mTEPES.ch  if (p,ch)  in mTEPES.pch ]
    mTEPES.psnchp    = [(p,sc,n,chp)      for p,sc,n,chp      in mTEPES.psn*mTEPES.chp if (p,chp) in mTEPES.pchp]
    mTEPES.psnbo     = [(p,sc,n,bo)       for p,sc,n,bo       in mTEPES.psn*mTEPES.bo  if (p,bo)  in mTEPES.pbo ]
    mTEPES.psnhp     = [(p,sc,n,hp)       for p,sc,n,hp       in mTEPES.psn*mTEPES.hp  if (p,hp)  in mTEPES.php ]
    mTEPES.psnes     = [(p,sc,n,es)       for p,sc,n,es       in mTEPES.psn*mTEPES.es  if (p,es)  in mTEPES.pes ]
    mTEPES.psneh     = [(p,sc,n,eh)       for p,sc,n,eh       in mTEPES.psn*mTEPES.eh  if (p,eh)  in mTEPES.peh ]
    mTEPES.psnec     = [(p,sc,n,ec)       for p,sc,n,ec       in mTEPES.psn*mTEPES.ec  if (p,ec)  in mTEPES.pec ]
    mTEPES.psnnd     = [(p,sc,n,nd)       for p,sc,n,nd       in mTEPES.psn*mTEPES.nd                           ]
    mTEPES.psnar     = [(p,sc,n,ar)       for p,sc,n,ar       in mTEPES.psn*mTEPES.ar                           ]

    mTEPES.psnla     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.la if (p,ni,nf,cc) in mTEPES.pla]
    mTEPES.psnle     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.le if (p,ni,nf,cc) in mTEPES.pla]
    mTEPES.psnll     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ll if (p,ni,nf,cc) in mTEPES.pll]
    mTEPES.psnls     = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ls if (p,ni,nf,cc) in mTEPES.pla]

    if pIndHydroTopology == 1:
        mTEPES.prs   = [(p,     rs)       for p,     rs       in mTEPES.p  *mTEPES.rs if pRsrPeriodIni[rs] <= p and pRsrPeriodFin[rs] >= p]
        mTEPES.prc   = [(p,     rc)       for p,     rc       in mTEPES.p  *mTEPES.rn if (p,rc) in mTEPES.prs]
        mTEPES.psrs  = [(p,sc,  rs)       for p,sc,  rs       in mTEPES.ps *mTEPES.rs if (p,rs) in mTEPES.prs]
        mTEPES.psnh  = [(p,sc,n,h )       for p,sc,n,h        in mTEPES.psn*mTEPES.h  if (p,h ) in mTEPES.ph ]
        mTEPES.psnrs = [(p,sc,n,rs)       for p,sc,n,rs       in mTEPES.psn*mTEPES.rs if (p,rs) in mTEPES.prs]
        mTEPES.psnrc = [(p,sc,n,rc)       for p,sc,n,rc       in mTEPES.psn*mTEPES.rn if (p,rc) in mTEPES.prc]
    else:
        mTEPES.prc   = []

    if pIndHydrogen == 1:
        mTEPES.ppa   = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pa if pH2PipePeriodIni[ni,nf,cc] <= p and pH2PipePeriodFin[ni,nf,cc] >= p]
        mTEPES.ppc   = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppa]
        mTEPES.psnpn = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pn if (p,ni,nf,cc) in mTEPES.ppa]
        mTEPES.psnpa = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pa if (p,ni,nf,cc) in mTEPES.ppa]
        mTEPES.psnpe = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pe if (p,ni,nf,cc) in mTEPES.ppa]
    else:
        mTEPES.ppc   = []

    if pIndHeat == 1:
        mTEPES.pha   = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ha if pHeatPipePeriodIni[ni,nf,cc] <= p and pHeatPipePeriodFin[ni,nf,cc] >= p]
        mTEPES.phc   = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.hc if (p,ni,nf,cc) in mTEPES.pha]
        mTEPES.psnhn = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.hn if (p,ni,nf,cc) in mTEPES.pha]
        mTEPES.psnha = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ha if (p,ni,nf,cc) in mTEPES.pha]
        mTEPES.psnhe = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.he if (p,ni,nf,cc) in mTEPES.pha]
    else:
        mTEPES.phc   = []

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

    pIndBinUnitInvest         = pIndBinUnitInvest.map    (idxDict)
    pIndBinUnitRetire         = pIndBinUnitRetire.map    (idxDict)
    pIndBinUnitCommit         = pIndBinUnitCommit.map    (idxDict)
    pIndBinStorInvest         = pIndBinStorInvest.map    (idxDict)
    pIndBinLineInvest         = pIndBinLineInvest.map    (idxDict)
    pIndBinLineSwitch         = pIndBinLineSwitch.map    (idxDict)
    pIndOperReserve           = pIndOperReserve.map      (idxDict)
    pMustRun                  = pMustRun.map             (idxDict)

    if pIndHydroTopology == 1:
        pIndBinRsrvInvest     = pIndBinRsrvInvest.map    (idxDict)

    if pIndHydrogen == 1:
        pIndBinH2PipeInvest   = pIndBinH2PipeInvest.map  (idxDict)

    if pIndHeat == 1:
        pIndBinHeatPipeInvest = pIndBinHeatPipeInvest.map(idxDict)

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

    if pAnnualDiscRate == 0.0:
        pDiscountedWeight = pd.Series([                        pPeriodWeight[p]                                                                                          for p in mTEPES.p], index=mTEPES.p)
    else:
        pDiscountedWeight = pd.Series([((1.0+pAnnualDiscRate)**pPeriodWeight[p]-1.0) / (pAnnualDiscRate*(1.0+pAnnualDiscRate)**(pPeriodWeight[p]-1+p-pEconomicBaseYear)) for p in mTEPES.p], index=mTEPES.p)

    mTEPES.pLoadLevelWeight = Param(mTEPES.psn, initialize=0.0, within=NonNegativeReals, doc='Load level weight', mutable=True)
    for p,sc,st,n in mTEPES.s2n:
        mTEPES.pLoadLevelWeight[p,sc,n] = pStageWeight[st]

    #%% inverse index node to generator
    pNodeToGen = pGenToNode.reset_index().set_index('Node').set_axis(['Generator'], axis=1)[['Generator']]
    pNodeToGen = pNodeToGen.loc[pNodeToGen['Generator'].isin(mTEPES.g)].reset_index().set_index(['Node', 'Generator'])

    mTEPES.n2g = Set(initialize=pNodeToGen.index, ordered=False, doc='node   to generator')

    pZone2Gen   = [(zn,g) for (nd,g,zn      ) in mTEPES.n2g*mTEPES.zn             if (nd,zn) in mTEPES.ndzn                           ]
    pArea2Gen   = [(ar,g) for (nd,g,zn,ar   ) in mTEPES.n2g*mTEPES.znar           if (nd,zn) in mTEPES.ndzn                           ]
    pRegion2Gen = [(rg,g) for (nd,g,zn,ar,rg) in mTEPES.n2g*mTEPES.znar*mTEPES.rg if (nd,zn) in mTEPES.ndzn and [ar,rg] in mTEPES.arrg]

    mTEPES.z2g = Set(initialize=mTEPES.zn*mTEPES.g, ordered=False, doc='zone   to generator', filter=lambda mTEPES,zn,g: (zn,g) in pZone2Gen  )
    mTEPES.a2g = Set(initialize=mTEPES.ar*mTEPES.g, ordered=False, doc='area   to generator', filter=lambda mTEPES,ar,g: (ar,g) in pArea2Gen  )
    mTEPES.r2g = Set(initialize=mTEPES.rg*mTEPES.g, ordered=False, doc='region to generator', filter=lambda mTEPES,rg,g: (rg,g) in pRegion2Gen)

    #%% inverse index generator to technology
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(mTEPES.g)].reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=pTechnologyToGen.index, ordered=False, doc='technology to generator')

    # ESS and RES technologies
    mTEPES.ot = Set(initialize=mTEPES.gt, ordered=False, doc='ESS         technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for es in mTEPES.es if (gt,es) in mTEPES.t2g))
    mTEPES.ht = Set(initialize=mTEPES.gt, ordered=False, doc='hydro       technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for h  in mTEPES.h  if (gt,h ) in mTEPES.t2g))
    mTEPES.et = Set(initialize=mTEPES.gt, ordered=False, doc='ESS & hydro technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for eh in mTEPES.eh if (gt,eh) in mTEPES.t2g))
    mTEPES.rt = Set(initialize=mTEPES.gt, ordered=False, doc='    RES     technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for re in mTEPES.re if (gt,re) in mTEPES.t2g))
    mTEPES.nt = Set(initialize=mTEPES.gt, ordered=False, doc='non-RES     technologies', filter=lambda mTEPES,gt: gt in mTEPES.gt and sum(1 for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g))

    mTEPES.psgt  = [(p,sc,  gt) for p,sc,  gt in mTEPES.ps *mTEPES.gt if sum(1 for g  in mTEPES.g  if (p,g ) in mTEPES.pg  and (gt,g ) in mTEPES.t2g)]
    mTEPES.psot  = [(p,sc,  ot) for p,sc,  ot in mTEPES.ps *mTEPES.ot if sum(1 for es in mTEPES.es if (p,es) in mTEPES.pes and (ot,es) in mTEPES.t2g)]
    mTEPES.psht  = [(p,sc,  ht) for p,sc,  ht in mTEPES.ps *mTEPES.ht if sum(1 for h  in mTEPES.h  if (p,h ) in mTEPES.ph  and (ht,h ) in mTEPES.t2g)]
    mTEPES.pset  = [(p,sc,  et) for p,sc,  et in mTEPES.ps *mTEPES.et if sum(1 for eh in mTEPES.eh if (p,eh) in mTEPES.peh and (et,eh) in mTEPES.t2g)]
    mTEPES.psrt  = [(p,sc,  rt) for p,sc,  rt in mTEPES.ps *mTEPES.rt if sum(1 for re in mTEPES.re if (p,re) in mTEPES.pre and (rt,re) in mTEPES.t2g)]
    mTEPES.psnt  = [(p,sc,  nt) for p,sc,  nt in mTEPES.ps *mTEPES.nt if sum(1 for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and (nt,nr) in mTEPES.t2g)]
    mTEPES.psngt = [(p,sc,n,gt) for p,sc,n,gt in mTEPES.psn*mTEPES.gt if (p,sc,gt) in mTEPES.psgt]
    mTEPES.psnot = [(p,sc,n,ot) for p,sc,n,ot in mTEPES.psn*mTEPES.ot if (p,sc,ot) in mTEPES.psot]
    mTEPES.psnht = [(p,sc,n,ht) for p,sc,n,ht in mTEPES.psn*mTEPES.ht if (p,sc,ht) in mTEPES.psht]
    mTEPES.psnet = [(p,sc,n,et) for p,sc,n,et in mTEPES.psn*mTEPES.et if (p,sc,et) in mTEPES.pset]
    mTEPES.psnrt = [(p,sc,n,rt) for p,sc,n,rt in mTEPES.psn*mTEPES.rt if (p,sc,rt) in mTEPES.psrt]
    mTEPES.psnnt = [(p,sc,n,nt) for p,sc,n,nt in mTEPES.psn*mTEPES.nt if (p,sc,nt) in mTEPES.psnt]

    #%% inverse index generator to mutually exclusive generator
    pExclusiveGenToGen = pGenToExclusiveGen.reset_index().set_index('MutuallyExclusive').set_axis(['Generator'], axis=1)[['Generator']]
    pExclusiveGenToGen = pExclusiveGenToGen.loc[pExclusiveGenToGen['Generator'].isin(mTEPES.g)].reset_index().set_index(['MutuallyExclusive', 'Generator'])

    mTEPES.g2g = Set(initialize=pExclusiveGenToGen.index, ordered=False, doc='mutually exclusive generator to generator', filter=lambda mTEPES,gg,g: (gg,g) in mTEPES.g*mTEPES.g)

    # minimum and maximum variable power, charge, and storage capacity
    pMinPowerElec  = pVariableMinPowerElec.replace(0.0, pRatedMinPowerElec)
    pMaxPowerElec  = pVariableMaxPowerElec.replace(0.0, pRatedMaxPowerElec)
    pMinCharge     = pVariableMinCharge.replace   (0.0, pRatedMinCharge   )
    pMaxCharge     = pVariableMaxCharge.replace   (0.0, pRatedMaxCharge   )
    pMinStorage    = pVariableMinStorage.replace  (0.0, pRatedMinStorage  )
    pMaxStorage    = pVariableMaxStorage.replace  (0.0, pRatedMaxStorage  )
    if pIndHydroTopology == 1:
        pMinVolume = pVariableMinVolume.replace   (0.0, pRatedMinVolume   )
        pMaxVolume = pVariableMaxVolume.replace   (0.0, pRatedMaxVolume   )

    pMinPowerElec  = pMinPowerElec.where(pMinPowerElec > 0.0, 0.0)
    pMaxPowerElec  = pMaxPowerElec.where(pMaxPowerElec > 0.0, 0.0)
    pMinCharge     = pMinCharge.where   (pMinCharge    > 0.0, 0.0)
    pMaxCharge     = pMaxCharge.where   (pMaxCharge    > 0.0, 0.0)
    pMinStorage    = pMinStorage.where  (pMinStorage   > 0.0, 0.0)
    pMaxStorage    = pMaxStorage.where  (pMaxStorage   > 0.0, 0.0)
    if pIndHydroTopology == 1:
        pMinVolume = pMinVolume.where   (pMinVolume    > 0.0, 0.0)
        pMaxVolume = pMaxVolume.where   (pMaxVolume    > 0.0, 0.0)

    # fuel term and constant term variable cost
    pVariableFuelCost = pVariableFuelCost.replace(0.0, dfGeneration['FuelCost'])
    pLinearVarCost    = dfGeneration['LinearTerm'  ] * 1e-3 * pVariableFuelCost + dfGeneration['OMVariableCost'] * 1e-3
    pConstantVarCost  = dfGeneration['ConstantTerm'] * 1e-6 * pVariableFuelCost
    pLinearVarCost    = pLinearVarCost.reindex  (sorted(pLinearVarCost.columns  ), axis=1)
    pConstantVarCost  = pConstantVarCost.reindex(sorted(pConstantVarCost.columns), axis=1)

    # variable emission cost
    pVariableEmissionCost = pVariableEmissionCost.replace(0.0, pCO2Cost)
    pEmissionVarCost      = pEmissionRate * 1e-3 * pVariableEmissionCost
    pEmissionVarCost      = pEmissionVarCost.reindex(sorted(pEmissionVarCost.columns), axis=1)

    # minimum up- and downtime and maximum shift time converted to an integer number of time steps
    pUpTime     = round(pUpTime    /pTimeStep).astype('int')
    pDwTime     = round(pDwTime    /pTimeStep).astype('int')
    pStableTime = round(pStableTime/pTimeStep).astype('int')
    pShiftTime  = round(pShiftTime /pTimeStep).astype('int')

    # %% definition of the time-steps leap to observe the stored energy at an ESS
    idxCycle            = dict()
    idxCycle[0        ] = 8736
    idxCycle[0.0      ] = 8736
    idxCycle['Hourly' ] = 1
    idxCycle['Daily'  ] = 1
    idxCycle['Weekly' ] = round(  24/pTimeStep)
    idxCycle['Monthly'] = round( 168/pTimeStep)
    idxCycle['Yearly' ] = round( 672/pTimeStep)

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

    pStorageTimeStep  = pStorageType.map (idxCycle                                                                                  ).astype('int')
    pOutflowsTimeStep = pOutflowsType.map(idxOutflows).where(pEnergyOutflows.sum()                               > 0.0, other = 8736).astype('int')
    pEnergyTimeStep   = pEnergyType.map  (idxEnergy  ).where(pVariableMinEnergy.sum() + pVariableMaxEnergy.sum() > 0.0, other = 8736).astype('int')

    pStorageTimeStep  = pd.concat([pStorageTimeStep, pOutflowsTimeStep, pEnergyTimeStep], axis=1).min(axis=1)
    # cycle time step can't exceed the stage duration
    pStorageTimeStep  = pStorageTimeStep.where(pStorageTimeStep <= pStageDuration.min(), pStageDuration.min())

    if pIndHydroTopology == 1:
        # %% definition of the time-steps leap to observe the stored energy at a reservoir
        idxCycleRsr            = dict()
        idxCycleRsr[0        ] = 8736
        idxCycleRsr[0.0      ] = 8736
        idxCycleRsr['Hourly' ] = 1
        idxCycleRsr['Daily'  ] = 1
        idxCycleRsr['Weekly' ] = round(  24/pTimeStep)
        idxCycleRsr['Monthly'] = round( 168/pTimeStep)
        idxCycleRsr['Yearly' ] = round( 672/pTimeStep)

        idxWaterOut            = dict()
        idxWaterOut[0        ] = 8736
        idxWaterOut[0.0      ] = 8736
        idxWaterOut['Daily'  ] = round(  24/pTimeStep)
        idxWaterOut['Weekly' ] = round( 168/pTimeStep)
        idxWaterOut['Monthly'] = round( 672/pTimeStep)
        idxWaterOut['Yearly' ] = round(8736/pTimeStep)

        pCycleRsrTimeStep = pReservoirType.map(idxCycleRsr).astype('int')
        pWaterOutTimeStep = pWaterOutfType.map(idxWaterOut).astype('int')

        pReservoirTimeStep = pd.concat([pCycleRsrTimeStep, pWaterOutTimeStep], axis=1).min(axis=1)
        # cycle water step can't exceed the stage duration
        pReservoirTimeStep = pReservoirTimeStep.where(pReservoirTimeStep <= pStageDuration.min(), pStageDuration.min())

    # initial inventory must be between minimum and maximum
    pInitialInventory  = pInitialInventory.where(pInitialInventory > pRatedMinStorage, pRatedMinStorage)
    pInitialInventory  = pInitialInventory.where(pInitialInventory < pRatedMaxStorage, pRatedMaxStorage)
    if pIndHydroTopology == 1:
        pInitialVolume = pInitialVolume.where   (pInitialVolume    > pRatedMinVolume,  pRatedMinVolume )
        pInitialVolume = pInitialVolume.where   (pInitialVolume    < pRatedMaxVolume,  pRatedMaxVolume )

    # initial inventory of the candidate storage units equal to its maximum capacity if the storage capacity is linked to the investment decision
    pInitialInventory.update(pd.Series([pInitialInventory[ec] if pIndBinStorInvest[ec] == 0 else pRatedMaxStorage[ec] for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64'))

    # parameter that allows the initial inventory to change with load level
    pIniInventory  = pd.DataFrame([pInitialInventory]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.es)
    if pIndHydroTopology == 1:
        pIniVolume = pd.DataFrame([pInitialVolume   ]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.rs)

    # initial inventory must be between minimum and maximum
    for p,sc,n,es in mTEPES.psnes:
        if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == pStorageTimeStep[es]:
            if  pIniInventory[es][p,sc,n] < pMinStorage[es][p,sc,n]:
                pIniInventory[es][p,sc,n] = pMinStorage[es][p,sc,n]
                print('### Initial inventory lower than minimum storage ',   es)
            if  pIniInventory[es][p,sc,n] > pMaxStorage[es][p,sc,n]:
                pIniInventory[es][p,sc,n] = pMaxStorage[es][p,sc,n]
                print('### Initial inventory greater than maximum storage ', es)
    if pIndHydroTopology == 1:
        for p,sc,n,rs in mTEPES.psnrs:
            if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == pReservoirTimeStep[rs]:
                if  pIniVolume[rs][p,sc,n] < pMinVolume[rs][p,sc,n]:
                    pIniVolume[rs][p,sc,n] = pMinVolume[rs][p,sc,n]
                    print('### Initial volume lower than minimum volume ',   rs)
                if  pIniVolume[rs][p,sc,n] > pMaxVolume[rs][p,sc,n]:
                    pIniVolume[rs][p,sc,n] = pMaxVolume[rs][p,sc,n]
                    print('### Initial volume greater than maximum volume ', rs)

    # drop load levels with duration 0
    pDuration            = pDuration.loc            [mTEPES.psn  ]
    pDemandElec          = pDemandElec.loc          [mTEPES.psn  ]
    pSystemInertia       = pSystemInertia.loc       [mTEPES.psnar]
    pOperReserveUp       = pOperReserveUp.loc       [mTEPES.psnar]
    pOperReserveDw       = pOperReserveDw.loc       [mTEPES.psnar]
    pMinPowerElec        = pMinPowerElec.loc        [mTEPES.psn  ]
    pMaxPowerElec        = pMaxPowerElec.loc        [mTEPES.psn  ]
    pMinCharge           = pMinCharge.loc           [mTEPES.psn  ]
    pMaxCharge           = pMaxCharge.loc           [mTEPES.psn  ]
    pEnergyInflows       = pEnergyInflows.loc       [mTEPES.psn  ]
    pEnergyOutflows      = pEnergyOutflows.loc      [mTEPES.psn  ]
    pIniInventory        = pIniInventory.loc        [mTEPES.psn  ]
    pMinStorage          = pMinStorage.loc          [mTEPES.psn  ]
    pMaxStorage          = pMaxStorage.loc          [mTEPES.psn  ]
    pVariableMaxEnergy   = pVariableMaxEnergy.loc   [mTEPES.psn  ]
    pVariableMinEnergy   = pVariableMinEnergy.loc   [mTEPES.psn  ]
    pLinearVarCost       = pLinearVarCost.loc       [mTEPES.psn  ]
    pConstantVarCost     = pConstantVarCost.loc     [mTEPES.psn  ]
    pEmissionVarCost     = pEmissionVarCost.loc     [mTEPES.psn  ]

    pRatedLinearOperCost = pRatedLinearFuelCost.loc [mTEPES.g    ]
    pRatedLinearVarCost  = pRatedLinearFuelCost.loc [mTEPES.g    ]

    # drop generators not es
    pEfficiency          = pEfficiency.loc          [mTEPES.eh   ]
    pStorageTimeStep     = pStorageTimeStep.loc     [mTEPES.es   ]
    pOutflowsTimeStep    = pOutflowsTimeStep.loc    [mTEPES.es   ]
    pStorageType         = pStorageType.loc         [mTEPES.es   ]

    if pIndHydroTopology == 1:
        pHydroInflows    = pHydroInflows.loc        [mTEPES.psn  ]
        pHydroOutflows   = pHydroOutflows.loc       [mTEPES.psn  ]
        pIniVolume       = pIniVolume.loc           [mTEPES.psn  ]
        pMinVolume       = pMinVolume.loc           [mTEPES.psn  ]
        pMaxVolume       = pMaxVolume.loc           [mTEPES.psn  ]
    if pIndHydrogen == 1:
        pDemandH2        = pDemandH2.loc            [mTEPES.psn  ]
        pDemandH2Abs     = pDemandH2.where  (pDemandH2   > 0.0, 0.0)
    if pIndHeat == 1:
        pDemandHeat      = pDemandHeat.loc          [mTEPES.psn  ]
        pDemandHeatAbs   = pDemandHeat.where(pDemandHeat > 0.0, 0.0)

    # separate positive and negative demands to avoid converting negative values to 0
    pDemandElecPos       = pDemandElec.where(pDemandElec >= 0.0, 0.0)
    pDemandElecNeg       = pDemandElec.where(pDemandElec <  0.0, 0.0)
    pDemandElecAbs       = pDemandElec.where(pDemandElec >  0.0, 0.0)

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
    pDemandElecPeak          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    for p,ar in mTEPES.par:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        pDemandElecPeak[p,ar] = pDemandElec[[nd for nd in d2a[ar]]].sum(axis=1).max()
        pEpsilon              = pDemandElecPeak[p,ar]*1e-5

        # these parameters are in GW
        pDemandElecPos     [pDemandElecPos [[nd for nd in d2a[ar]]] <  pEpsilon] = 0.0
        pDemandElecNeg     [pDemandElecNeg [[nd for nd in d2a[ar]]] > -pEpsilon] = 0.0
        pSystemInertia     [pSystemInertia [[                 ar ]] <  pEpsilon] = 0.0
        pOperReserveUp     [pOperReserveUp [[                 ar ]] <  pEpsilon] = 0.0
        pOperReserveDw     [pOperReserveDw [[                 ar ]] <  pEpsilon] = 0.0
        if len(g2a[ar]):
            pMinPowerElec  [pMinPowerElec  [[g  for  g in g2a[ar]]] <  pEpsilon] = 0.0
            pMaxPowerElec  [pMaxPowerElec  [[g  for  g in g2a[ar]]] <  pEpsilon] = 0.0
            pMinCharge     [pMinCharge     [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
            pMaxCharge     [pMaxCharge     [[eh for eh in g2a[ar]]] <  pEpsilon] = 0.0
            pEnergyInflows [pEnergyInflows [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
            pEnergyOutflows[pEnergyOutflows[[es for es in e2a[ar]]] <  pEpsilon] = 0.0
            # these parameters are in GWh
            pMinStorage    [pMinStorage    [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
            pMaxStorage    [pMaxStorage    [[es for es in e2a[ar]]] <  pEpsilon] = 0.0
            pIniInventory  [pIniInventory  [[es for es in e2a[ar]]] <  pEpsilon] = 0.0

        # pInitialInventory.update(pd.Series([0.0 for es in e2a[ar] if pInitialInventory[es] < pEpsilon], index=[es for es in e2a[ar] if pInitialInventory[es] < pEpsilon], dtype='float64'))

        # merging positive and negative values of the demand
        pDemandElec        = pDemandElecPos.where(pDemandElecNeg >= 0.0, pDemandElecNeg)

        pMaxPowerElec      = pMaxPowerElec.where(pMaxPowerElec >= pMinPowerElec, pMinPowerElec)
        pMaxCharge         = pMaxCharge.where   (pMaxCharge    >= pMinCharge,    pMinCharge   )
        pMaxPower2ndBlock  = pMaxPowerElec - pMinPowerElec
        pMaxCharge2ndBlock = pMaxCharge    - pMinCharge
        pMaxCapacity       = pMaxPowerElec.where(pMaxPowerElec > pMaxCharge, pMaxCharge)

        if len(g2a[ar]):
            pMaxPower2ndBlock [pMaxPower2ndBlock [[nr for nr in n2a[ar]]] < pEpsilon] = 0.0
            pMaxCharge2ndBlock[pMaxCharge2ndBlock[[eh for eh in g2a[ar]]] < pEpsilon] = 0.0

        pLineNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilon], dtype='float64'))
        pLineNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilon], dtype='float64'))
        pLineNTCMax = pLineNTCFrw.where(pLineNTCFrw > pLineNTCBck, pLineNTCBck)

        if pIndHydrogen == 1:
            pDemandH2[pDemandH2[[nd for nd in d2a[ar]]] < pEpsilon] = 0.0
            pH2PipeNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.pa if pH2PipeNTCFrw[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.pa if pH2PipeNTCFrw[ni,nf,cc] < pEpsilon], dtype='float64'))
            pH2PipeNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.pa if pH2PipeNTCBck[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.pa if pH2PipeNTCBck[ni,nf,cc] < pEpsilon], dtype='float64'))

        if pIndHeat == 1:
            pDemandHeat[pDemandHeat[[nd for nd in d2a[ar]]] < pEpsilon] = 0.0
            pHeatPipeNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.ha if pHeatPipeNTCFrw[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.ha if pHeatPipeNTCFrw[ni,nf,cc] < pEpsilon], dtype='float64'))
            pHeatPipeNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.ha if pHeatPipeNTCBck[ni,nf,cc] < pEpsilon], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.ha if pHeatPipeNTCBck[ni,nf,cc] < pEpsilon], dtype='float64'))

    # drop generators not g or es or eh or ch
    pMinPowerElec      = pMinPowerElec.loc     [:,mTEPES.g ]
    pMaxPowerElec      = pMaxPowerElec.loc     [:,mTEPES.g ]
    pMinCharge         = pMinCharge.loc        [:,mTEPES.eh]
    pMaxCharge         = pMaxCharge.loc        [:,mTEPES.eh]
    pMaxPower2ndBlock  = pMaxPower2ndBlock.loc [:,mTEPES.g ]
    pMaxCharge2ndBlock = pMaxCharge2ndBlock.loc[:,mTEPES.eh]
    pMaxCapacity       = pMaxCapacity.loc      [:,mTEPES.eh]
    pEnergyInflows     = pEnergyInflows.loc    [:,mTEPES.es]
    pEnergyOutflows    = pEnergyOutflows.loc   [:,mTEPES.es]
    pIniInventory      = pIniInventory.loc     [:,mTEPES.es]
    pMinStorage        = pMinStorage.loc       [:,mTEPES.es]
    pMaxStorage        = pMaxStorage.loc       [:,mTEPES.es]
    pVariableMaxEnergy = pVariableMaxEnergy.loc[:,mTEPES.g ]
    pVariableMinEnergy = pVariableMinEnergy.loc[:,mTEPES.g ]
    pLinearVarCost     = pLinearVarCost.loc    [:,mTEPES.g ]
    pConstantVarCost   = pConstantVarCost.loc  [:,mTEPES.g ]
    pEmissionVarCost   = pEmissionVarCost.loc  [:,mTEPES.g ]

    # replace < 0.0 by 0.0
    pMaxPower2ndBlock  = pMaxPower2ndBlock.where (pMaxPower2ndBlock  > 0.0, 0.0)
    pMaxCharge2ndBlock = pMaxCharge2ndBlock.where(pMaxCharge2ndBlock > 0.0, 0.0)

    # computation of the power to heat ratio of the CHP units
    # heat ratio of boiler units is fixed to 1.0
    pPower2HeatRatio   = pd.Series([1.0 if ch in mTEPES.bo else (pRatedMaxPowerElec[ch]-pRatedMinPowerElec[ch])/(pRatedMaxPowerHeat[ch]-pRatedMinPowerHeat[ch]) for ch in mTEPES.ch], index=mTEPES.ch)
    pMinPowerHeat      = pd.DataFrame([[pMinPowerElec     [ch][p,sc,n]/pPower2HeatRatio[ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    pMaxPowerHeat      = pd.DataFrame([[pMaxPowerElec     [ch][p,sc,n]/pPower2HeatRatio[ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    pMinPowerHeat.update(pd.DataFrame([[pRatedMinPowerHeat[bo]                              for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))
    pMaxPowerHeat.update(pd.DataFrame([[pRatedMaxPowerHeat[bo]                              for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))

    # drop values not par, p, or ps
    pReserveMargin  = pReserveMargin.loc [mTEPES.par]
    pEmission       = pEmission.loc      [mTEPES.par]
    pRESEnergy      = pRESEnergy.loc     [mTEPES.par]
    pDemandElecPeak = pDemandElecPeak.loc[mTEPES.par]
    pPeriodWeight   = pPeriodWeight.loc  [mTEPES.p  ]
    pScenProb       = pScenProb.loc      [mTEPES.ps ]

    # drop generators not gc or gd
    pGenInvestCost           = pGenInvestCost.loc   [mTEPES.eb]
    pGenRetireCost           = pGenRetireCost.loc   [mTEPES.gd]
    pIndBinUnitInvest        = pIndBinUnitInvest.loc[mTEPES.eb]
    pIndBinUnitRetire        = pIndBinUnitRetire.loc[mTEPES.gd]
    pGenLoInvest             = pGenLoInvest.loc     [mTEPES.eb]
    pGenLoRetire             = pGenLoRetire.loc     [mTEPES.gd]
    pGenUpInvest             = pGenUpInvest.loc     [mTEPES.eb]
    pGenUpRetire             = pGenUpRetire.loc     [mTEPES.gd]

    # drop generators not nr or ec
    pStartUpCost             = pStartUpCost.loc     [mTEPES.nr]
    pShutDownCost            = pShutDownCost.loc    [mTEPES.nr]
    pIndBinUnitCommit        = pIndBinUnitCommit.loc[mTEPES.nr]
    pIndBinStorInvest        = pIndBinStorInvest.loc[mTEPES.ec]

    # drop lines not la
    pLineR                   = pLineR.loc           [mTEPES.la]
    pLineX                   = pLineX.loc           [mTEPES.la]
    pLineBsh                 = pLineBsh.loc         [mTEPES.la]
    pLineTAP                 = pLineTAP.loc         [mTEPES.la]
    pLineLength              = pLineLength.loc      [mTEPES.la]
    pElecNetPeriodIni        = pElecNetPeriodIni.loc[mTEPES.la]
    pElecNetPeriodFin        = pElecNetPeriodFin.loc[mTEPES.la]
    pLineVoltage             = pLineVoltage.loc     [mTEPES.la]
    pLineNTCFrw              = pLineNTCFrw.loc      [mTEPES.la]
    pLineNTCBck              = pLineNTCBck.loc      [mTEPES.la]
    pLineNTCMax              = pLineNTCMax.loc      [mTEPES.la]
    # pSwOnTime              = pSwOnTime.loc        [mTEPES.la]
    # pSwOffTime             = pSwOffTime.loc       [mTEPES.la]
    pIndBinLineInvest        = pIndBinLineInvest.loc[mTEPES.la]
    pIndBinLineSwitch        = pIndBinLineSwitch.loc[mTEPES.la]
    pAngMin                  = pAngMin.loc          [mTEPES.la]
    pAngMax                  = pAngMax.loc          [mTEPES.la]

    # drop lines not lc or ll
    pNetFixedCost            = pNetFixedCost.loc    [mTEPES.lc]
    pNetLoInvest             = pNetLoInvest.loc     [mTEPES.lc]
    pNetUpInvest             = pNetUpInvest.loc     [mTEPES.lc]
    pLineLossFactor          = pLineLossFactor.loc  [mTEPES.ll]

    if pIndHydroTopology == 1:
        # drop generators not h
        pProductionFunctionHydro = pProductionFunctionHydro.loc[mTEPES.h ]
        # drop reservoirs not rn
        pIndBinRsrvInvest        = pIndBinRsrvInvest.loc       [mTEPES.rn]
        pRsrInvestCost           = pRsrInvestCost.loc          [mTEPES.rn]
        # maximum outflows depending on the downstream hydropower unit
        pMaxOutflows = pd.DataFrame([[sum(pMaxPowerElec[h][p,sc,n]/pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) for rs in mTEPES.rs] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.rs)

    if pIndHydrogen == 1:
        # drop generators not el
        pProductionFunctionH2 = pProductionFunctionH2.loc[mTEPES.el]
        # drop pipelines not pc
        pH2PipeFixedCost      = pH2PipeFixedCost.loc     [mTEPES.pc]
        pH2PipeLoInvest       = pH2PipeLoInvest.loc      [mTEPES.pc]
        pH2PipeUpInvest       = pH2PipeUpInvest.loc      [mTEPES.pc]

    if pIndHeat == 1:
        # drop generators not hp
        pProductionFunctionHeat     = pProductionFunctionHeat.loc    [mTEPES.hp]
        # drop generators not hh
        pProductionFunctionH2ToHeat = pProductionFunctionH2ToHeat.loc[mTEPES.hh]
        # drop heat pipes not hc
        pHeatPipeFixedCost          = pHeatPipeFixedCost.loc         [mTEPES.hc]
        pHeatPipeLoInvest           = pHeatPipeLoInvest.loc          [mTEPES.hc]
        pHeatPipeUpInvest           = pHeatPipeUpInvest.loc          [mTEPES.hc]

    # replace very small costs by 0
    pEpsilon = 1e-5           # this value in EUR/GWh is lower than the O&M variable cost of any technology, independent of the area

    pLinearVarCost  [pLinearVarCost  [[g for g in mTEPES.g]] < pEpsilon] = 0.0
    pConstantVarCost[pConstantVarCost[[g for g in mTEPES.g]] < pEpsilon] = 0.0
    pEmissionVarCost[pEmissionVarCost[[g for g in mTEPES.g]] < pEpsilon] = 0.0

    pRatedLinearVarCost.update  (pd.Series([0.0 for g  in mTEPES.g  if     pRatedLinearVarCost  [g ]  < pEpsilon], index=[g  for g  in mTEPES.g  if     pRatedLinearVarCost  [g ]  < pEpsilon]))
    pRatedConstantVarCost.update(pd.Series([0.0 for g  in mTEPES.g  if     pRatedConstantVarCost[g ]  < pEpsilon], index=[g  for g  in mTEPES.g  if     pRatedConstantVarCost[g ]  < pEpsilon]))
    pLinearOMCost.update        (pd.Series([0.0 for g  in mTEPES.g  if     pLinearOMCost        [g ]  < pEpsilon], index=[g  for g  in mTEPES.g  if     pLinearOMCost        [g ]  < pEpsilon]))
    pOperReserveCost.update     (pd.Series([0.0 for g  in mTEPES.g  if     pOperReserveCost     [g ]  < pEpsilon], index=[g  for g  in mTEPES.g  if     pOperReserveCost     [g ]  < pEpsilon]))
    # pEmissionCost.update      (pd.Series([0.0 for g  in mTEPES.g  if abs(pEmissionCost        [g ]) < pEpsilon], index=[g  for g  in mTEPES.g  if abs(pEmissionCost        [g ]) < pEpsilon]))
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
    pBigMFlowBck = pBigMFlowBck.where(pBigMFlowBck != 0.0, 1.0)
    pBigMFlowFrw = pBigMFlowFrw.where(pBigMFlowFrw != 0.0, 1.0)

    # maximum voltage angle
    pMaxTheta = pDemandElec*0.0 + math.pi/2
    pMaxTheta = pMaxTheta.loc[mTEPES.psn]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    # %% parameters
    mTEPES.pIndBinGenInvest      = Param(initialize=pIndBinGenInvest    , within=NonNegativeIntegers, doc='Indicator of binary generation       investment decisions', mutable=True)
    mTEPES.pIndBinGenRetire      = Param(initialize=pIndBinGenRetire    , within=NonNegativeIntegers, doc='Indicator of binary generation       retirement decisions', mutable=True)
    mTEPES.pIndBinRsrInvest      = Param(initialize=pIndBinRsrInvest    , within=NonNegativeIntegers, doc='Indicator of binary reservoir        investment decisions', mutable=True)
    mTEPES.pIndBinNetElecInvest  = Param(initialize=pIndBinNetElecInvest, within=NonNegativeIntegers, doc='Indicator of binary electric network investment decisions', mutable=True)
    mTEPES.pIndBinNetH2Invest    = Param(initialize=pIndBinNetH2Invest  , within=NonNegativeIntegers, doc='Indicator of binary hydrogen network investment decisions', mutable=True)
    mTEPES.pIndBinNetHeatInvest  = Param(initialize=pIndBinNetHeatInvest, within=NonNegativeIntegers, doc='Indicator of binary heat     network investment decisions', mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=pIndBinGenOperat    , within=Binary,              doc='Indicator of binary generation operation  decisions',       mutable=True)
    mTEPES.pIndBinSingleNode     = Param(initialize=pIndBinSingleNode   , within=Binary,              doc='Indicator of single node within a electric network case',   mutable=True)
    mTEPES.pIndBinGenRamps       = Param(initialize=pIndBinGenRamps     , within=Binary,              doc='Indicator of using or not the ramp constraints',            mutable=True)
    mTEPES.pIndBinGenMinTime     = Param(initialize=pIndBinGenMinTime   , within=Binary,              doc='Indicator of using or not the min time constraints',        mutable=True)
    mTEPES.pIndBinLineCommit     = Param(initialize=pIndBinLineCommit   , within=Binary,              doc='Indicator of binary electric network switching  decisions', mutable=True)
    mTEPES.pIndBinNetLosses      = Param(initialize=pIndBinNetLosses    , within=Binary,              doc='Indicator of binary electric network ohmic losses',         mutable=True)
    mTEPES.pIndHydroTopology     = Param(initialize=pIndHydroTopology   , within=Binary,              doc='Indicator of reservoir and hydropower topology'                         )
    mTEPES.pIndHydrogen          = Param(initialize=pIndHydrogen        , within=Binary,              doc='Indicator of hydrogen demand and pipeline network'                      )
    mTEPES.pIndHeat              = Param(initialize=pIndHeat            , within=Binary,              doc='Indicator of heat     demand and pipe     network'                      )

    mTEPES.pENSCost              = Param(initialize=pENSCost            , within=NonNegativeReals,    doc='ENS cost'                                          )
    mTEPES.pH2NSCost             = Param(initialize=pH2NSCost           , within=NonNegativeReals,    doc='HNS cost'                                          )
    mTEPES.pHeatNSCost           = Param(initialize=pHeatNSCost         , within=NonNegativeReals,    doc='HTNS cost'                                         )
    mTEPES.pCO2Cost              = Param(initialize=pCO2Cost            , within=NonNegativeReals,    doc='CO2 emission cost'                                 )
    mTEPES.pAnnualDiscRate       = Param(initialize=pAnnualDiscRate     , within=UnitInterval,        doc='Annual discount rate'                              )
    mTEPES.pUpReserveActivation  = Param(initialize=pUpReserveActivation, within=UnitInterval,        doc='Proportion of upward   reserve activation'         )
    mTEPES.pDwReserveActivation  = Param(initialize=pDwReserveActivation, within=UnitInterval,        doc='Proportion of downward reserve activation'         )
    mTEPES.pMinRatioDwUp         = Param(initialize=pMinRatioDwUp       , within=UnitInterval,        doc='Minimum ration between upward and downward reserve')
    mTEPES.pMaxRatioDwUp         = Param(initialize=pMaxRatioDwUp       , within=UnitInterval,        doc='Maximum ration between upward and downward reserve')
    mTEPES.pSBase                = Param(initialize=pSBase              , within=PositiveReals,       doc='Base power'                                        )
    mTEPES.pTimeStep             = Param(initialize=pTimeStep           , within=PositiveIntegers,    doc='Unitary time step'                                 )
    mTEPES.pEconomicBaseYear     = Param(initialize=pEconomicBaseYear   , within=PositiveIntegers,    doc='Base year'                                         )

    mTEPES.pReserveMargin        = Param(mTEPES.par,   initialize=pReserveMargin.to_dict()            , within=NonNegativeReals,    doc='Adequacy reserve margin'                             )
    mTEPES.pEmission             = Param(mTEPES.par,   initialize=pEmission.to_dict()                 , within=NonNegativeReals,    doc='Maximum CO2 emission'                                )
    mTEPES.pRESEnergy            = Param(mTEPES.par,   initialize=pRESEnergy.to_dict()                , within=NonNegativeReals,    doc='Minimum RES energy'                                  )
    mTEPES.pDemandElecPeak       = Param(mTEPES.par,   initialize=pDemandElecPeak.to_dict()           , within=NonNegativeReals,    doc='Peak electric demand'                                )
    mTEPES.pDemandElec           = Param(mTEPES.psnnd, initialize=pDemandElec.stack().to_dict()       , within=           Reals,    doc='Electric demand'                                     )
    mTEPES.pDemandElecAbs        = Param(mTEPES.psnnd, initialize=pDemandElecAbs.stack().to_dict()    , within=NonNegativeReals,    doc='Electric demand'                                     )
    mTEPES.pPeriodWeight         = Param(mTEPES.p,     initialize=pPeriodWeight.to_dict()             , within=NonNegativeReals,    doc='Period weight',                          mutable=True)
    mTEPES.pDiscountedWeight     = Param(mTEPES.p,     initialize=pDiscountedWeight.to_dict()         , within=NonNegativeReals,    doc='Discount factor'                                     )
    mTEPES.pScenProb             = Param(mTEPES.psc,   initialize=pScenProb.to_dict()                 , within=UnitInterval    ,    doc='Probability',                            mutable=True)
    mTEPES.pStageWeight          = Param(mTEPES.stt,   initialize=pStageWeight.to_dict()              , within=NonNegativeReals,    doc='Stage weight'                                        )
    mTEPES.pDuration             = Param(mTEPES.psn,   initialize=pDuration.to_dict()                 , within=NonNegativeIntegers, doc='Duration',                               mutable=True)
    mTEPES.pNodeLon              = Param(mTEPES.nd,    initialize=pNodeLon.to_dict()                  ,                             doc='Longitude'                                           )
    mTEPES.pNodeLat              = Param(mTEPES.nd,    initialize=pNodeLat.to_dict()                  ,                             doc='Latitude'                                            )
    mTEPES.pSystemInertia        = Param(mTEPES.psnar, initialize=pSystemInertia.stack().to_dict()    , within=NonNegativeReals,    doc='System inertia'                                      )
    mTEPES.pOperReserveUp        = Param(mTEPES.psnar, initialize=pOperReserveUp.stack().to_dict()    , within=NonNegativeReals,    doc='Upward   operating reserve'                          )
    mTEPES.pOperReserveDw        = Param(mTEPES.psnar, initialize=pOperReserveDw.stack().to_dict()    , within=NonNegativeReals,    doc='Downward operating reserve'                          )
    mTEPES.pMinPowerElec         = Param(mTEPES.psng , initialize=pMinPowerElec.stack().to_dict()     , within=NonNegativeReals,    doc='Minimum electric power'                              )
    mTEPES.pMaxPowerElec         = Param(mTEPES.psng , initialize=pMaxPowerElec.stack().to_dict()     , within=NonNegativeReals,    doc='Maximum electric power'                              )
    mTEPES.pMinCharge            = Param(mTEPES.psneh, initialize=pMinCharge.stack().to_dict()        , within=NonNegativeReals,    doc='Minimum charge'                                      )
    mTEPES.pMaxCharge            = Param(mTEPES.psneh, initialize=pMaxCharge.stack().to_dict()        , within=NonNegativeReals,    doc='Maximum charge'                                      )
    mTEPES.pMaxCapacity          = Param(mTEPES.psneh, initialize=pMaxCapacity.stack().to_dict()      , within=NonNegativeReals,    doc='Maximum capacity'                                    )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.psng , initialize=pMaxPower2ndBlock.stack().to_dict() , within=NonNegativeReals,    doc='Second block power'                                  )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.psneh, initialize=pMaxCharge2ndBlock.stack().to_dict(), within=NonNegativeReals,    doc='Second block charge'                                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.psnes, initialize=pEnergyInflows.stack().to_dict()    , within=NonNegativeReals,    doc='Energy inflows',                         mutable=True)
    mTEPES.pEnergyOutflows       = Param(mTEPES.psnes, initialize=pEnergyOutflows.stack().to_dict()   , within=NonNegativeReals,    doc='Energy outflows',                        mutable=True)
    mTEPES.pMinStorage           = Param(mTEPES.psnes, initialize=pMinStorage.stack().to_dict()       , within=NonNegativeReals,    doc='ESS Minimum storage capacity'                        )
    mTEPES.pMaxStorage           = Param(mTEPES.psnes, initialize=pMaxStorage.stack().to_dict()       , within=NonNegativeReals,    doc='ESS Maximum storage capacity'                        )
    mTEPES.pMinEnergy            = Param(mTEPES.psng , initialize=pVariableMinEnergy.stack().to_dict(), within=NonNegativeReals,    doc='Unit minimum energy demand'                          )
    mTEPES.pMaxEnergy            = Param(mTEPES.psng , initialize=pVariableMaxEnergy.stack().to_dict(), within=NonNegativeReals,    doc='Unit maximum energy demand'                          )
    mTEPES.pRatedMaxPowerElec    = Param(mTEPES.gg,    initialize=pRatedMaxPowerElec.to_dict()        , within=NonNegativeReals,    doc='Rated maximum power'                                 )
    mTEPES.pRatedMaxCharge       = Param(mTEPES.gg,    initialize=pRatedMaxCharge.to_dict()           , within=NonNegativeReals,    doc='Rated maximum charge'                                )
    mTEPES.pMustRun              = Param(mTEPES.gg,    initialize=pMustRun.to_dict()                  , within=Binary          ,    doc='must-run unit'                                       )
    mTEPES.pInertia              = Param(mTEPES.gg,    initialize=pInertia.to_dict()                  , within=NonNegativeReals,    doc='unit inertia constant'                               )
    mTEPES.pElecGenPeriodIni     = Param(mTEPES.gg,    initialize=pElecGenPeriodIni.to_dict()         , within=PositiveIntegers,    doc='installation year',                                  )
    mTEPES.pElecGenPeriodFin     = Param(mTEPES.gg,    initialize=pElecGenPeriodFin.to_dict()         , within=PositiveIntegers,    doc='retirement   year',                                  )
    mTEPES.pAvailability         = Param(mTEPES.gg,    initialize=pAvailability.to_dict()             , within=UnitInterval    ,    doc='unit availability',                      mutable=True)
    mTEPES.pEFOR                 = Param(mTEPES.gg,    initialize=pEFOR.to_dict()                     , within=UnitInterval    ,    doc='EFOR'                                                )
    mTEPES.pRatedLinearVarCost   = Param(mTEPES.gg,    initialize=pRatedLinearVarCost.to_dict()       , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pRatedConstantVarCost = Param(mTEPES.gg,    initialize=pRatedConstantVarCost.to_dict()     , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearVarCost        = Param(mTEPES.psng , initialize=pLinearVarCost.stack().to_dict()    , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pConstantVarCost      = Param(mTEPES.psng , initialize=pConstantVarCost.stack().to_dict()  , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearOMCost         = Param(mTEPES.gg,    initialize=pLinearOMCost.to_dict()             , within=NonNegativeReals,    doc='Linear   O&M      cost'                              )
    mTEPES.pOperReserveCost      = Param(mTEPES.gg,    initialize=pOperReserveCost.to_dict()          , within=NonNegativeReals,    doc='Operating reserve cost'                              )
    mTEPES.pEmissionVarCost      = Param(mTEPES.psng , initialize=pEmissionVarCost.stack().to_dict()  , within=Reals           ,    doc='CO2 Emission      cost'                              )
    mTEPES.pEmissionRate         = Param(mTEPES.gg,    initialize=pEmissionRate.to_dict()             , within=Reals           ,    doc='CO2 Emission      rate'                              )
    mTEPES.pStartUpCost          = Param(mTEPES.nr,    initialize=pStartUpCost.to_dict()              , within=NonNegativeReals,    doc='Startup  cost'                                       )
    mTEPES.pShutDownCost         = Param(mTEPES.nr,    initialize=pShutDownCost.to_dict()             , within=NonNegativeReals,    doc='Shutdown cost'                                       )
    mTEPES.pRampUp               = Param(mTEPES.gg,    initialize=pRampUp.to_dict()                   , within=NonNegativeReals,    doc='Ramp up   rate'                                      )
    mTEPES.pRampDw               = Param(mTEPES.gg,    initialize=pRampDw.to_dict()                   , within=NonNegativeReals,    doc='Ramp down rate'                                      )
    mTEPES.pUpTime               = Param(mTEPES.gg,    initialize=pUpTime.to_dict()                   , within=NonNegativeIntegers, doc='Up     time'                                         )
    mTEPES.pDwTime               = Param(mTEPES.gg,    initialize=pDwTime.to_dict()                   , within=NonNegativeIntegers, doc='Down   time'                                         )
    mTEPES.pStableTime           = Param(mTEPES.gg,    initialize=pStableTime.to_dict()               , within=NonNegativeIntegers, doc='Stable time'                                         )
    mTEPES.pShiftTime            = Param(mTEPES.gg,    initialize=pShiftTime.to_dict()                , within=NonNegativeIntegers, doc='Shift  time'                                         )
    mTEPES.pGenInvestCost        = Param(mTEPES.eb,    initialize=pGenInvestCost.to_dict()            , within=NonNegativeReals,    doc='Generation fixed cost'                               )
    mTEPES.pGenRetireCost        = Param(mTEPES.gd,    initialize=pGenRetireCost.to_dict()            , within=Reals           ,    doc='Generation fixed retire cost'                        )
    mTEPES.pIndBinUnitInvest     = Param(mTEPES.eb,    initialize=pIndBinUnitInvest.to_dict()         , within=Binary          ,    doc='Binary investment decision'                          )
    mTEPES.pIndBinUnitRetire     = Param(mTEPES.gd,    initialize=pIndBinUnitRetire.to_dict()         , within=Binary          ,    doc='Binary retirement decision'                          )
    mTEPES.pIndBinUnitCommit     = Param(mTEPES.nr,    initialize=pIndBinUnitCommit.to_dict()         , within=Binary          ,    doc='Binary commitment decision'                          )
    mTEPES.pIndBinStorInvest     = Param(mTEPES.ec,    initialize=pIndBinStorInvest.to_dict()         , within=Binary          ,    doc='Storage linked to generation investment'             )
    mTEPES.pIndOperReserve       = Param(mTEPES.gg,    initialize=pIndOperReserve.to_dict()           , within=Binary          ,    doc='Indicator of operating reserve'                      )
    mTEPES.pEfficiency           = Param(mTEPES.eh,    initialize=pEfficiency.to_dict()               , within=UnitInterval    ,    doc='Round-trip efficiency'                               )
    mTEPES.pStorageTimeStep      = Param(mTEPES.es,    initialize=pStorageTimeStep.to_dict()          , within=PositiveIntegers,    doc='ESS Storage cycle'                                   )
    mTEPES.pOutflowsTimeStep     = Param(mTEPES.es,    initialize=pOutflowsTimeStep.to_dict()         , within=PositiveIntegers,    doc='ESS Outflows cycle'                                  )
    mTEPES.pEnergyTimeStep       = Param(mTEPES.gg,    initialize=pEnergyTimeStep.to_dict()           , within=PositiveIntegers,    doc='Unit energy cycle'                                   )
    mTEPES.pIniInventory         = Param(mTEPES.psnes, initialize=pIniInventory.stack().to_dict()     , within=NonNegativeReals,    doc='ESS Initial storage',                    mutable=True)
    mTEPES.pStorageType          = Param(mTEPES.es,    initialize=pStorageType.to_dict()              , within=Any             ,    doc='ESS Storage type'                                    )
    mTEPES.pGenLoInvest          = Param(mTEPES.eb,    initialize=pGenLoInvest.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pGenUpInvest          = Param(mTEPES.eb,    initialize=pGenUpInvest.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)
    mTEPES.pGenLoRetire          = Param(mTEPES.gd,    initialize=pGenLoRetire.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the retirement decision', mutable=True)
    mTEPES.pGenUpRetire          = Param(mTEPES.gd,    initialize=pGenUpRetire.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the retirement decision', mutable=True)

    if pIndHydrogen == 1:
        mTEPES.pProductionFunctionH2 = Param(mTEPES.el, initialize=pProductionFunctionH2.to_dict(), within=NonNegativeReals, doc='Production function of an electrolyzer plant')

    if pIndHeat == 1:
        mTEPES.pRatedMaxPowerHeat          = Param(mTEPES.gg,    initialize=pRatedMaxPowerHeat.to_dict()         , within=NonNegativeReals, doc='Rated maximum heat'                       )
        mTEPES.pMinPowerHeat               = Param(mTEPES.psnch, initialize=pMinPowerHeat.stack().to_dict()      , within=NonNegativeReals, doc='Minimum heat     power'                   )
        mTEPES.pMaxPowerHeat               = Param(mTEPES.psnch, initialize=pMaxPowerHeat.stack().to_dict()      , within=NonNegativeReals, doc='Maximum heat     power'                   )
        mTEPES.pPower2HeatRatio            = Param(mTEPES.ch,    initialize=pPower2HeatRatio.to_dict()           , within=NonNegativeReals, doc='Power to heat ratio'                      )
        mTEPES.pProductionFunctionHeat     = Param(mTEPES.hp,    initialize=pProductionFunctionHeat.to_dict()    , within=NonNegativeReals, doc='Production function of an CHP plant'      )
        mTEPES.pProductionFunctionH2ToHeat = Param(mTEPES.hh,    initialize=pProductionFunctionH2ToHeat.to_dict(), within=NonNegativeReals, doc='Production function of an boiler using H2')

    if pIndHydroTopology == 1:
        mTEPES.pProductionFunctionHydro = Param(mTEPES.h ,    initialize=pProductionFunctionHydro.to_dict(), within=NonNegativeReals, doc='Production function of a hydro power plant'  )
        mTEPES.pHydroInflows            = Param(mTEPES.psnrs, initialize=pHydroInflows.stack().to_dict()   , within=NonNegativeReals, doc='Hydro inflows',                  mutable=True)
        mTEPES.pHydroOutflows           = Param(mTEPES.psnrs, initialize=pHydroOutflows.stack().to_dict()  , within=NonNegativeReals, doc='Hydro outflows',                 mutable=True)
        mTEPES.pMaxOutflows             = Param(mTEPES.psnrs, initialize=pMaxOutflows.stack().to_dict()    , within=NonNegativeReals, doc='Maximum hydro outflows',                     )
        mTEPES.pMinVolume               = Param(mTEPES.psnrs, initialize=pMinVolume.stack().to_dict()      , within=NonNegativeReals, doc='Minimum reservoir volume capacity'           )
        mTEPES.pMaxVolume               = Param(mTEPES.psnrs, initialize=pMaxVolume.stack().to_dict()      , within=NonNegativeReals, doc='Maximum reservoir volume capacity'           )
        mTEPES.pIndBinRsrvInvest        = Param(mTEPES.rn,    initialize=pIndBinRsrvInvest.to_dict()       , within=Binary          , doc='Binary  reservoir investment decision'       )
        mTEPES.pRsrInvestCost           = Param(mTEPES.rn,    initialize=pRsrInvestCost.to_dict()          , within=NonNegativeReals, doc='Reservoir fixed cost'                        )
        mTEPES.pRsrPeriodIni            = Param(mTEPES.rs,    initialize=pRsrPeriodIni.to_dict()           , within=PositiveIntegers, doc='Installation year',                          )
        mTEPES.pRsrPeriodFin            = Param(mTEPES.rs,    initialize=pRsrPeriodFin.to_dict()           , within=PositiveIntegers, doc='Retirement   year',                          )
        mTEPES.pReservoirTimeStep       = Param(mTEPES.rs,    initialize=pReservoirTimeStep.to_dict()      , within=PositiveIntegers, doc='Reservoir volume cycle'                      )
        mTEPES.pWaterOutTimeStep        = Param(mTEPES.rs,    initialize=pWaterOutTimeStep.to_dict()       , within=PositiveIntegers, doc='Reservoir outflows cycle'                    )
        mTEPES.pIniVolume               = Param(mTEPES.psnrs, initialize=pIniVolume.stack().to_dict()      , within=NonNegativeReals, doc='Reservoir initial volume',       mutable=True)
        mTEPES.pInitialVolume           = Param(mTEPES.rs,    initialize=pInitialVolume.to_dict()          , within=NonNegativeReals, doc='Reservoir initial volume without load levels')
        mTEPES.pReservoirType           = Param(mTEPES.rs,    initialize=pReservoirType.to_dict()          , within=Any             , doc='Reservoir volume type'                       )

    if pIndHydrogen == 1:
        mTEPES.pDemandH2      = Param(mTEPES.psnnd, initialize=pDemandH2.stack().to_dict()     , within=NonNegativeReals,    doc='Hydrogen demand per hour')
        mTEPES.pDemandH2Abs   = Param(mTEPES.psnnd, initialize=pDemandH2Abs.stack().to_dict()  , within=NonNegativeReals,    doc='Hydrogen demand'         )

    if pIndHeat == 1:
        mTEPES.pDemandHeat    = Param(mTEPES.psnnd, initialize=pDemandHeat.stack().to_dict()   , within=NonNegativeReals,    doc='Heat demand per hour'    )
        mTEPES.pDemandHeatAbs = Param(mTEPES.psnnd, initialize=pDemandHeatAbs.stack().to_dict(), within=NonNegativeReals,    doc='Heat demand'             )

    mTEPES.pLoadLevelDuration = Param(mTEPES.psn,   initialize=0                               , within=NonNegativeIntegers, doc='Load level duration', mutable=True)
    for p,sc,n in mTEPES.psn:
        mTEPES.pLoadLevelDuration[p,sc,n] = mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pDuration[p,sc,n]()

    mTEPES.pPeriodProb         = Param(mTEPES.ps,    initialize=0.0                             , within=NonNegativeReals,   doc='Period probability',  mutable=True)
    for p,sc in mTEPES.ps:
        # periods and scenarios are going to be solved together with their weight and probability
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc]

    mTEPES.pLineLossFactor   = Param(mTEPES.ll,    initialize=pLineLossFactor.to_dict()  , within=           Reals,    doc='Loss factor'                                                       )
    mTEPES.pLineR            = Param(mTEPES.la,    initialize=pLineR.to_dict()           , within=NonNegativeReals,    doc='Resistance'                                                        )
    mTEPES.pLineX            = Param(mTEPES.la,    initialize=pLineX.to_dict()           , within=           Reals,    doc='Reactance'                                                         )
    mTEPES.pLineBsh          = Param(mTEPES.la,    initialize=pLineBsh.to_dict()         , within=NonNegativeReals,    doc='Susceptance',                                          mutable=True)
    mTEPES.pLineTAP          = Param(mTEPES.la,    initialize=pLineTAP.to_dict()         , within=NonNegativeReals,    doc='Tap changer',                                          mutable=True)
    mTEPES.pLineLength       = Param(mTEPES.la,    initialize=pLineLength.to_dict()      , within=NonNegativeReals,    doc='Length',                                               mutable=True)
    mTEPES.pElecNetPeriodIni = Param(mTEPES.la,    initialize=pElecNetPeriodIni.to_dict(), within=PositiveIntegers,    doc='Installation period'                                               )
    mTEPES.pElecNetPeriodFin = Param(mTEPES.la,    initialize=pElecNetPeriodFin.to_dict(), within=PositiveIntegers,    doc='Retirement   period'                                               )
    mTEPES.pLineVoltage      = Param(mTEPES.la,    initialize=pLineVoltage.to_dict()     , within=NonNegativeReals,    doc='Voltage'                                                           )
    mTEPES.pLineNTCFrw       = Param(mTEPES.la,    initialize=pLineNTCFrw.to_dict()      , within=NonNegativeReals,    doc='Electric line NTC forward'                                         )
    mTEPES.pLineNTCBck       = Param(mTEPES.la,    initialize=pLineNTCBck.to_dict()      , within=NonNegativeReals,    doc='Electric line NTC backward'                                        )
    mTEPES.pLineNTCMax       = Param(mTEPES.la,    initialize=pLineNTCMax.to_dict()      , within=NonNegativeReals,    doc='Electric line NTC'                                                 )
    mTEPES.pNetFixedCost     = Param(mTEPES.lc,    initialize=pNetFixedCost.to_dict()    , within=NonNegativeReals,    doc='Electric line fixed cost'                                          )
    mTEPES.pIndBinLineInvest = Param(mTEPES.la,    initialize=pIndBinLineInvest.to_dict(), within=Binary          ,    doc='Binary electric line investment decision'                          )
    mTEPES.pIndBinLineSwitch = Param(mTEPES.la,    initialize=pIndBinLineSwitch.to_dict(), within=Binary          ,    doc='Binary electric line switching  decision'                          )
    # mTEPES.pSwOnTime       = Param(mTEPES.la,    initialize=pSwitchOnTime.to_dict()    , within=NonNegativeIntegers, doc='Minimum switching on  time'                                        )
    # mTEPES.pSwOffTime      = Param(mTEPES.la,    initialize=pSwitchOffTime.to_dict()   , within=NonNegativeIntegers, doc='Minimum switching off time'                                        )
    mTEPES.pBigMFlowBck      = Param(mTEPES.la,    initialize=pBigMFlowBck.to_dict()     , within=NonNegativeReals,    doc='Maximum backward capacity',                            mutable=True)
    mTEPES.pBigMFlowFrw      = Param(mTEPES.la,    initialize=pBigMFlowFrw.to_dict()     , within=NonNegativeReals,    doc='Maximum forward  capacity',                            mutable=True)
    mTEPES.pMaxTheta         = Param(mTEPES.psnnd, initialize=pMaxTheta.stack().to_dict(), within=NonNegativeReals,    doc='Maximum voltage angle',                                mutable=True)
    mTEPES.pAngMin           = Param(mTEPES.la,    initialize=pAngMin.to_dict()          , within=           Reals,    doc='Minimum phase angle difference',                       mutable=True)
    mTEPES.pAngMax           = Param(mTEPES.la,    initialize=pAngMax.to_dict()          , within=           Reals,    doc='Maximum phase angle difference',                       mutable=True)
    mTEPES.pNetLoInvest      = Param(mTEPES.lc,    initialize=pNetLoInvest.to_dict()     , within=NonNegativeReals,    doc='Lower bound of the electric line investment decision', mutable=True)
    mTEPES.pNetUpInvest      = Param(mTEPES.lc,    initialize=pNetUpInvest.to_dict()     , within=NonNegativeReals,    doc='Upper bound of the electric line investment decision', mutable=True)

    if pIndHydrogen == 1:
        mTEPES.pH2PipeLength       = Param(mTEPES.pn,  initialize=pH2PipeLength.to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline length',                        mutable=True)
        mTEPES.pH2PipePeriodIni    = Param(mTEPES.pn,  initialize=pH2PipePeriodIni.to_dict()   , within=PositiveIntegers,    doc='Installation period'                                          )
        mTEPES.pH2PipePeriodFin    = Param(mTEPES.pn,  initialize=pH2PipePeriodFin.to_dict()   , within=PositiveIntegers,    doc='Retirement   period'                                          )
        mTEPES.pH2PipeNTCFrw       = Param(mTEPES.pn,  initialize=pH2PipeNTCFrw.to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC forward'                                )
        mTEPES.pH2PipeNTCBck       = Param(mTEPES.pn,  initialize=pH2PipeNTCBck.to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC backward'                               )
        mTEPES.pH2PipeFixedCost    = Param(mTEPES.pc,  initialize=pH2PipeFixedCost.to_dict()   , within=NonNegativeReals,    doc='Hydrogen pipeline fixed cost'                                 )
        mTEPES.pIndBinH2PipeInvest = Param(mTEPES.pn,  initialize=pIndBinH2PipeInvest.to_dict(), within=Binary          ,    doc='Binary   pipeline investment decision'                        )
        mTEPES.pH2PipeLoInvest     = Param(mTEPES.pc,  initialize=pH2PipeLoInvest.to_dict()    , within=NonNegativeReals,    doc='Lower bound of the pipeline investment decision', mutable=True)
        mTEPES.pH2PipeUpInvest     = Param(mTEPES.pc,  initialize=pH2PipeUpInvest.to_dict()    , within=NonNegativeReals,    doc='Upper bound of the pipeline investment decision', mutable=True)

    if pIndHeat == 1:
        mTEPES.pHeatPipeLength       = Param(mTEPES.hn, initialize=pHeatPipeLength.to_dict()      , within=NonNegativeReals, doc='Heat pipe length',                                 mutable=True)
        mTEPES.pHeatPipePeriodIni    = Param(mTEPES.hn, initialize=pHeatPipePeriodIni.to_dict()   , within=PositiveIntegers, doc='Installation period'                                           )
        mTEPES.pHeatPipePeriodFin    = Param(mTEPES.hn, initialize=pHeatPipePeriodFin.to_dict()   , within=PositiveIntegers, doc='Retirement   period'                                           )
        mTEPES.pHeatPipeNTCFrw       = Param(mTEPES.hn, initialize=pHeatPipeNTCFrw.to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC forward'                                         )
        mTEPES.pHeatPipeNTCBck       = Param(mTEPES.hn, initialize=pHeatPipeNTCBck.to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC backward'                                        )
        mTEPES.pHeatPipeFixedCost    = Param(mTEPES.hc, initialize=pHeatPipeFixedCost.to_dict()   , within=NonNegativeReals, doc='Heat pipe fixed cost'                                          )
        mTEPES.pIndBinHeatPipeInvest = Param(mTEPES.hn, initialize=pIndBinHeatPipeInvest.to_dict(), within=Binary          , doc='Binary  heat pipe investment decision'                         )
        mTEPES.pHeatPipeLoInvest     = Param(mTEPES.hc, initialize=pHeatPipeLoInvest.to_dict()    , within=NonNegativeReals, doc='Lower bound of the heat pipe investment decision', mutable=True)
        mTEPES.pHeatPipeUpInvest     = Param(mTEPES.hc, initialize=pHeatPipeUpInvest.to_dict()    , within=NonNegativeReals, doc='Upper bound of the heat pipe investment decision', mutable=True)

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
    if pIndHydroTopology == 1:
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
    if pIndHydroTopology == 1:
        # reservoirs with outflows
        mTEPES.ro = [(p,sc,rs) for p,sc,rs in mTEPES.psrs if sum(mTEPES.pHydroOutflows [p,sc,n2,rs]() for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    # generators with min/max energy
    mTEPES.gm     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMinEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    mTEPES.gM     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMaxEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]

    # # if unit availability = 0 changed to 1
    # for g in mTEPES.g:
    #     if  mTEPES.pAvailability[g]() == 0.0:
    #         mTEPES.pAvailability[g]   =  1.0

    # if line length = 0 changed to geographical distance with an additional 10%
    for ni,nf,cc in mTEPES.la:
        if  mTEPES.pLineLength[ni,nf,cc]() == 0.0:
            mTEPES.pLineLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if pIndHydrogen == 1:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pH2PipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pH2PipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if pIndHeat == 1:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pHeatPipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pHeatPipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    # initialize generation output, unit commitment and line switching
    pInitialOutput = pd.DataFrame([[0.0]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=     mTEPES.g )
    pInitialUC     = pd.DataFrame([[0  ]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=     mTEPES.g )
    pInitialSwitch = pd.DataFrame([[0  ]*len(mTEPES.la)]*len(mTEPES.psn), index=mTEPES.psn, columns=list(mTEPES.la))

    mTEPES.pInitialOutput = Param(mTEPES.psng , initialize=pInitialOutput.stack().to_dict(), within=NonNegativeReals, doc='unit initial output',     mutable=True)
    mTEPES.pInitialUC     = Param(mTEPES.psng , initialize=pInitialUC.stack().to_dict()    , within=Binary,           doc='unit initial commitment', mutable=True)
    mTEPES.pInitialSwitch = Param(mTEPES.psnla, initialize=pInitialSwitch.stack().to_dict(), within=Binary,           doc='line initial switching',  mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')


def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()

    #%% variables
    OptModel.vTotalSCost               = Var(                       within=NonNegativeReals,                 doc='total system                         cost      [MEUR]')
    OptModel.vTotalICost               = Var(                       within=NonNegativeReals,                 doc='total system investment              cost      [MEUR]')
    OptModel.vTotalFCost               = Var(mTEPES.p,     within=NonNegativeReals,                 doc='total system fixed                   cost      [MEUR]')
    OptModel.vTotalGCost               = Var(mTEPES.psn,   within=NonNegativeReals,                 doc='total variable generation  operation cost      [MEUR]')
    OptModel.vTotalCCost               = Var(mTEPES.psn,   within=NonNegativeReals,                 doc='total variable consumption operation cost      [MEUR]')
    OptModel.vTotalECost               = Var(mTEPES.psn,   within=NonNegativeReals,                 doc='total system emission                cost      [MEUR]')
    OptModel.vTotalRCost               = Var(mTEPES.psn,   within=NonNegativeReals,                 doc='total system reliability             cost      [MEUR]')
    OptModel.vTotalNCost               = Var(mTEPES.psn,   within=NonNegativeReals,                 doc='total network loss penalty operation cost      [MEUR]')
    OptModel.vTotalECostArea           = Var(mTEPES.psnar, within=NonNegativeReals,                 doc='total   area emission                cost      [MEUR]')
    OptModel.vTotalRESEnergyArea       = Var(mTEPES.psnar, within=NonNegativeReals,                 doc='        RES energy                              [GWh]')

    OptModel.vTotalOutput              = Var(mTEPES.psng , within=NonNegativeReals,                 doc='total output of the unit                         [GW]')
    OptModel.vOutput2ndBlock           = Var(mTEPES.psnnr, within=NonNegativeReals,                 doc='second block of the unit                         [GW]')
    OptModel.vReserveUp                = Var(mTEPES.psnnr, within=NonNegativeReals,                 doc='upward   operating reserve                       [GW]')
    OptModel.vReserveDown              = Var(mTEPES.psnnr, within=NonNegativeReals,                 doc='downward operating reserve                       [GW]')
    OptModel.vEnergyInflows            = Var(mTEPES.psnec, within=NonNegativeReals,                 doc='unscheduled inflows  of candidate ESS units      [GW]')
    OptModel.vEnergyOutflows           = Var(mTEPES.psnes, within=NonNegativeReals,                 doc='scheduled   outflows of all       ESS units      [GW]')
    OptModel.vESSInventory             = Var(mTEPES.psnes, within=NonNegativeReals,                 doc='ESS inventory                                   [GWh]')
    OptModel.vESSSpillage              = Var(mTEPES.psnes, within=NonNegativeReals,                 doc='ESS spillage                                    [GWh]')
    OptModel.vIniInventory             = Var(mTEPES.psnec, within=NonNegativeReals,                 doc='initial inventory for ESS candidate             [GWh]')

    OptModel.vESSTotalCharge           = Var(mTEPES.psneh, within=NonNegativeReals,                 doc='ESS total charge power                           [GW]')
    OptModel.vCharge2ndBlock           = Var(mTEPES.psneh, within=NonNegativeReals,                 doc='ESS       charge power                           [GW]')
    OptModel.vESSReserveUp             = Var(mTEPES.psneh, within=NonNegativeReals,                 doc='ESS upward   operating reserve                   [GW]')
    OptModel.vESSReserveDown           = Var(mTEPES.psneh, within=NonNegativeReals,                 doc='ESS downward operating reserve                   [GW]')
    OptModel.vENS                      = Var(mTEPES.psnnd, within=NonNegativeReals,                 doc='energy not served in node                        [GW]')

    if mTEPES.pIndHydroTopology == 1:
        OptModel.vHydroInflows         = Var(mTEPES.psnrc, within=NonNegativeReals,                 doc='unscheduled inflows  of candidate hydro units  [m3/s]')
        OptModel.vHydroOutflows        = Var(mTEPES.psnrs, within=NonNegativeReals,                 doc='scheduled   outflows of all       hydro units  [m3/s]')
        OptModel.vReservoirVolume      = Var(mTEPES.psnrs, within=NonNegativeReals,                 doc='Reservoir volume                                [hm3]')
        OptModel.vReservoirSpillage    = Var(mTEPES.psnrs, within=NonNegativeReals,                 doc='Reservoir spillage                              [hm3]')

    if mTEPES.pIndHeat == 1:
        OptModel.vTotalOutputHeat      = Var(mTEPES.psng , within=NonNegativeReals,                 doc='total heat output of the boiler unit             [GW]')
        [OptModel.vTotalOutputHeat[p,sc,n,ch].setub(mTEPES.pMaxPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
        [OptModel.vTotalOutputHeat[p,sc,n,ch].setlb(mTEPES.pMinPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
        # only boilers are forced to produce at their minimum heat power. CHPs are not forced to produce at their minimum heat power, they are committed or not to produce electricity

    if mTEPES.pIndBinGenInvest() == 0:
        OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=UnitInterval,                     doc='generation       investment decision exists in a year [0,1]')
        OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=UnitInterval,                     doc='generation       investment decision done   in a year [0,1]')
    else:
        OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=Binary,                           doc='generation       investment decision exists in a year {0,1}')
        OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=Binary,                           doc='generation       investment decision done   in a year {0,1}')

    if mTEPES.pIndBinGenRetire() == 0:
        OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=UnitInterval,                     doc='generation       retirement decision exists in a year [0,1]')
        OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=UnitInterval,                     doc='generation       retirement decision exists in a year [0,1]')
    else:
        OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=Binary,                           doc='generation       retirement decision exists in a year {0,1}')
        OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=Binary,                           doc='generation       retirement decision exists in a year {0,1}')

    if mTEPES.pIndBinNetElecInvest() == 0:
        OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=UnitInterval,                     doc='electric network investment decision exists in a year [0,1]')
        OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=UnitInterval,                     doc='electric network investment decision exists in a year [0,1]')
    else:
        OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=Binary,                           doc='electric network investment decision exists in a year {0,1}')
        OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=Binary,                           doc='electric network investment decision exists in a year {0,1}')

    if mTEPES.pIndHydroTopology == 1:
        if mTEPES.pIndBinRsrInvest() == 0:
            OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=UnitInterval,                     doc='reservoir        investment decision exists in a year [0,1]')
            OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=UnitInterval,                     doc='reservoir        investment decision exists in a year [0,1]')
        else:
            OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=Binary,                           doc='reservoir        investment decision exists in a year {0,1}')
            OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=Binary,                           doc='reservoir        investment decision exists in a year {0,1}')

    if mTEPES.pIndHydrogen == 1:
        if mTEPES.pIndBinNetH2Invest() == 0:
            OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=UnitInterval,                     doc='hydrogen network investment decision exists in a year [0,1]')
            OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=UnitInterval,                     doc='hydrogen network investment decision exists in a year [0,1]')
        else:
            OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=Binary,                           doc='hydrogen network investment decision exists in a year {0,1}')
            OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=Binary,                           doc='hydrogen network investment decision exists in a year {0,1}')

    if mTEPES.pIndHeat == 1:
        if mTEPES.pIndBinGenInvest() == 0:
            OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=UnitInterval,                 doc='generation       investment decision exists in a year [0,1]')
            OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=UnitInterval,                 doc='generation       investment decision done   in a year [0,1]')
        else:
            OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=Binary,                       doc='generation       investment decision exists in a year {0,1}')
            OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=Binary,                       doc='generation       investment decision done   in a year {0,1}')
        if mTEPES.pIndBinNetHeatInvest() == 0:
            OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=UnitInterval,                 doc='heat network investment decision exists in a year [0,1]'    )
            OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=UnitInterval,                 doc='heat network investment decision exists in a year [0,1]'    )
        else:
            OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=Binary,                       doc='heat network investment decision exists in a year {0,1}'    )
            OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=Binary,                       doc='heat network investment decision exists in a year {0,1}'    )

    if mTEPES.pIndBinGenOperat() == 0:
        OptModel.vCommitment           = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='commitment         of the unit                        [0,1]')
        OptModel.vStartUp              = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='startup            of the unit                        [0,1]')
        OptModel.vShutDown             = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='shutdown           of the unit                        [0,1]')
        OptModel.vMaxCommitment        = Var(mTEPES.psnr , within=UnitInterval,     initialize=0.0, doc='maximum commitment of the unit                        [0,1]')
        OptModel.vStableState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='stable state       of the unit                        [0,1]')
        OptModel.vRampUpState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp up state      of the unit                        [0,1]')
        OptModel.vRampDwState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp down state    of the unit                        [0,1]')
    else:
        OptModel.vCommitment           = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='commitment         of the unit                        {0,1}')
        OptModel.vStartUp              = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='startup            of the unit                        {0,1}')
        OptModel.vShutDown             = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='shutdown           of the unit                        {0,1}')
        OptModel.vMaxCommitment        = Var(mTEPES.psnr , within=Binary,           initialize=0  , doc='maximum commitment of the unit                        {0,1}')
        OptModel.vStableState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='stable state       of the unit                        {0,1}')
        OptModel.vRampUpState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp up state      of the unit                        {0,1}')
        OptModel.vRampDwState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp down state    of the unit                        {0,1}')

    if mTEPES.pIndBinLineCommit() == 0:
        OptModel.vLineCommit           = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0, doc='line switching      of the electric line              [0,1]')
    else:
        OptModel.vLineCommit           = Var(mTEPES.psnla, within=Binary,           initialize=0  , doc='line switching      of the electric line              {0,1}')

    if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineCommit() == 0:
            OptModel.vLineOnState      = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0, doc='switching on  state of the electric line              [0,1]')
            OptModel.vLineOffState     = Var(mTEPES.psnla, within=UnitInterval,     initialize=0.0, doc='switching off state of the electric line              [0,1]')
        else:
            OptModel.vLineOnState      = Var(mTEPES.psnla, within=Binary,           initialize=0  , doc='switching on  state of the electric line              {0,1}')
            OptModel.vLineOffState     = Var(mTEPES.psnla, within=Binary,           initialize=0  , doc='switching off state of the electric line              {0,1}')

    # assign lower and upper bounds to variables
    [OptModel.vTotalOutput   [p,sc,n,g ].setub(mTEPES.pMaxPowerElec     [p,sc,n,g ]  ) for p,sc,n,g  in mTEPES.psng ]
    [OptModel.vTotalOutput   [p,sc,n,re].setlb(mTEPES.pMinPowerElec     [p,sc,n,re]  ) for p,sc,n,re in mTEPES.psnre]
    [OptModel.vOutput2ndBlock[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
    [OptModel.vReserveUp     [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
    [OptModel.vReserveDown   [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
    [OptModel.vEnergyInflows [p,sc,n,ec].setub(mTEPES.pEnergyInflows    [p,sc,n,ec]()) for p,sc,n,ec in mTEPES.psnec]
    [OptModel.vEnergyOutflows[p,sc,n,es].setub(mTEPES.pMaxCapacity      [p,sc,n,es]  ) for p,sc,n,es in mTEPES.psnes]
    [OptModel.vESSInventory  [p,sc,n,es].setlb(mTEPES.pMinStorage       [p,sc,n,es]  ) for p,sc,n,es in mTEPES.psnes]
    [OptModel.vESSInventory  [p,sc,n,es].setub(mTEPES.pMaxStorage       [p,sc,n,es]  ) for p,sc,n,es in mTEPES.psnes]
    [OptModel.vIniInventory  [p,sc,n,ec].setlb(mTEPES.pMinStorage       [p,sc,n,ec]  ) for p,sc,n,ec in mTEPES.psnec]
    [OptModel.vIniInventory  [p,sc,n,ec].setub(mTEPES.pMaxStorage       [p,sc,n,ec]  ) for p,sc,n,ec in mTEPES.psnec]

    [OptModel.vESSTotalCharge[p,sc,n,eh].setub(mTEPES.pMaxCharge        [p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
    [OptModel.vCharge2ndBlock[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
    [OptModel.vESSReserveUp  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
    [OptModel.vESSReserveDown[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
    [OptModel.vENS           [p,sc,n,nd].setub(mTEPES.pDemandElecAbs    [p,sc,n,nd]) for p,sc,n,nd in mTEPES.psnnd]

    if mTEPES.pIndHydroTopology == 1:
        [OptModel.vHydroInflows   [p,sc,n,rc].setub(mTEPES.pHydroInflows[p,sc,n,rc]()) for p,sc,n,rc in mTEPES.psnrc]
        [OptModel.vHydroOutflows  [p,sc,n,rs].setub(mTEPES.pMaxOutflows [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
        [OptModel.vReservoirVolume[p,sc,n,rs].setlb(mTEPES.pMinVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
        [OptModel.vReservoirVolume[p,sc,n,rs].setub(mTEPES.pMaxVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]

    nFixedVariables = 0

    # relax binary condition in generation, boiler, and electric network investment decisions
    for p,eb in mTEPES.peb:
        if mTEPES.pIndBinGenInvest() != 0 and mTEPES.pIndBinUnitInvest[eb] == 0:
            OptModel.vGenerationInvest    [p,eb      ].domain = UnitInterval
        if mTEPES.pIndBinGenInvest() == 2:
            OptModel.vGenerationInvest    [p,eb      ].fix(0)
            nFixedVariables += 1
    for p,ni,nf,cc in mTEPES.plc:
        if mTEPES.pIndBinNetElecInvest() != 0 and mTEPES.pIndBinLineInvest[ni,nf,cc] == 0:
            OptModel.vNetworkInvest       [p,ni,nf,cc].domain = UnitInterval
        if mTEPES.pIndBinNetElecInvest() == 2:
            OptModel.vNetworkInvest       [p,ni,nf,cc].fix(0)
            nFixedVariables += 1

    # relax binary condition in generation retirement decisions
    for p,gd in mTEPES.pgd:
        if mTEPES.pIndBinGenRetire() != 0 and mTEPES.pIndBinUnitRetire[gd] == 0:
            OptModel.vGenerationRetire    [p,gd      ].domain = UnitInterval
        if mTEPES.pIndBinGenRetire() == 2:
            OptModel.vGenerationRetire    [p,gd      ].fix(0)
            nFixedVariables += 1

    if mTEPES.pIndHydroTopology == 1:
        # relax binary condition in reservoir investment decisions
        for p,rc in mTEPES.prc:
            if mTEPES.pIndBinRsrInvest() != 0 and mTEPES.pIndBinRsrvInvest[rc] == 0:
                OptModel.vReservoirInvest [p,rc      ].domain = UnitInterval
            if mTEPES.pIndBinRsrInvest() == 2:
                OptModel.vReservoirInvest [p,rc      ].fix(0)
                nFixedVariables += 1

    if mTEPES.pIndHydrogen == 1:
        # relax binary condition in hydrogen network investment decisions
        for p,ni,nf,cc in mTEPES.ppc:
            if mTEPES.pIndBinNetH2Invest() != 0 and mTEPES.pIndBinH2PipeInvest[ni,nf,cc] == 0:
                OptModel.vH2PipeInvest  [p,ni,nf,cc].domain = UnitInterval
            if mTEPES.pIndBinNetH2Invest() == 2:
                OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(0)
                nFixedVariables += 1

    if mTEPES.pIndHeat == 1:
        # relax binary condition in heat network investment decisions
        for p,ni,nf,cc in mTEPES.phc:
            if mTEPES.pIndBinNetHeatInvest() != 0 and mTEPES.pIndBinHeatPipeInvest[ni,nf,cc] == 0:
                OptModel.vHeatPipeInvest  [p,ni,nf,cc].domain = UnitInterval
            if mTEPES.pIndBinNetHeatInvest() == 2:
                OptModel.vHeatPipeInvest  [p,ni,nf,cc].fix(0)
                nFixedVariables += 1

    # relax binary condition in unit generation, startup and shutdown decisions
    for p,sc,n,nr in mTEPES.psnnr:
        if mTEPES.pIndBinUnitCommit[nr] == 0:
            OptModel.vCommitment   [p,sc,n,nr].domain = UnitInterval
            OptModel.vStartUp      [p,sc,n,nr].domain = UnitInterval
            OptModel.vShutDown     [p,sc,n,nr].domain = UnitInterval
    for p,sc,  nr in mTEPES.psnr:
        if mTEPES.pIndBinUnitCommit[nr] == 0:
            OptModel.vMaxCommitment[p,sc,  nr].domain = UnitInterval

    # existing lines are always committed if no switching decision is modeled
    [OptModel.vLineCommit[p,sc,n,ni,nf,cc].fix(1) for p,sc,n,ni,nf,cc in mTEPES.psnle if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0]
    nFixedVariables += sum(                    1  for p,sc,n,ni,nf,cc in mTEPES.psnle if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0)

    # no on/off state for lines if no switching decision is modeled
    if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
        [OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0) for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0]
        [OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0) for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0]
        nFixedVariables += sum(                      2  for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0)

    OptModel.vLineLosses = Var(mTEPES.psnll, within=NonNegativeReals, doc='half line losses [GW]')
    OptModel.vFlowElec   = Var(mTEPES.psnla, within=Reals,            doc='electric flow    [GW]')
    OptModel.vTheta      = Var(mTEPES.psnnd, within=Reals,            doc='voltage angle   [rad]')

    [OptModel.vLineLosses[p,sc,n,ni,nf,cc].setub(0.5*mTEPES.pLineLossFactor[ni,nf,cc]*mTEPES.pLineNTCMax[ni,nf,cc]) for p,sc,n,ni,nf,cc in mTEPES.psnll]
    if mTEPES.pIndBinSingleNode() == 0:
        [OptModel.vFlowElec[p,sc,n,ni,nf,cc].setlb(-mTEPES.pLineNTCBck[ni,nf,cc]   ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
        [OptModel.vFlowElec[p,sc,n,ni,nf,cc].setub( mTEPES.pLineNTCFrw[ni,nf,cc]   ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
    [OptModel.vTheta       [p,sc,n,nd      ].setlb(-mTEPES.pMaxTheta  [p,sc,n,nd]()) for p,sc,n,nd       in mTEPES.psnnd]
    [OptModel.vTheta       [p,sc,n,nd      ].setub( mTEPES.pMaxTheta  [p,sc,n,nd]()) for p,sc,n,nd       in mTEPES.psnnd]

    if mTEPES.pIndHydrogen == 1:
        OptModel.vFlowH2 = Var(mTEPES.psnpa, within=Reals,            doc='pipeline flow               [tH2]')
        OptModel.vH2NS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='hydrogen not served in node [tH2]')
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setlb(-mTEPES.pH2PipeNTCBck[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setub( mTEPES.pH2PipeNTCFrw[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
        [OptModel.vH2NS    [p,sc,n,nd      ].setub(mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandH2Abs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]

    if mTEPES.pIndHeat == 1:
        OptModel.vFlowHeat = Var(mTEPES.psnha, within=Reals,            doc='heat pipe flow          [GW]')
        OptModel.vHeatNS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='heat not served in node [GW]')
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setlb(-mTEPES.pHeatPipeNTCBck[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnha]
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setub( mTEPES.pHeatPipeNTCFrw[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnha]
        [OptModel.vHeatNS  [p,sc,n,nd      ].setub(mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandHeatAbs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]

    # fix the must-run units and their output
    # must run units must produce at least their minimum output
    [OptModel.vTotalOutput[p,sc,n,g].setlb(mTEPES.pMinPowerElec[p,sc,n,g]) for p,sc,n,g in mTEPES.psng if mTEPES.pMustRun[g] == 1]
    # if no max power, no total output
    [OptModel.vTotalOutput[p,sc,n,g].fix(0.0) for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0]
    nFixedVariables += sum(                1  for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0)

    for p,sc,n,nr in mTEPES.psnnr:
        # must run units or units with no minimum power or ESS existing units are always committed and must produce at least their minimum output
        # not applicable to mutually exclusive units
        if   len(mTEPES.g2g) == 0:
            OptModel.vMaxCommitment     [p,sc,  nr].fix(1)
            nFixedVariables += 1/len(mTEPES.n)
            if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pRatedConstantVarCost[nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec:
                OptModel.vCommitment    [p,sc,n,nr].fix(1)
                OptModel.vStartUp       [p,sc,n,nr].fix(0)
                OptModel.vShutDown      [p,sc,n,nr].fix(0)
                nFixedVariables += 3
        elif len(mTEPES.g2g) >  0 and sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g) == 0:
            if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pRatedConstantVarCost[nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec:
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
        if  mTEPES.pIndOperReserve  [       nr] ==  1:
            OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
            OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
            nFixedVariables += 2

    # total energy inflows per storage
    pStorageTotalEnergyInflows = pd.Series([sum(mTEPES.pEnergyInflows[p,sc,n,es]() for p,sc,n in mTEPES.psn) for es in mTEPES.es], index=mTEPES.es)

    for p,sc,n,es in mTEPES.psnes:
        # ESS with no charge capacity
        if  mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0:
            OptModel.vESSTotalCharge [p,sc,n,es].fix(0.0)
            nFixedVariables += 1
        # ESS with no charge capacity and no inflows can't produce
        if  mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0 and pStorageTotalEnergyInflows[es] == 0.0:
            OptModel.vTotalOutput    [p,sc,n,es].fix(0.0)
            OptModel.vOutput2ndBlock [p,sc,n,es].fix(0.0)
            OptModel.vReserveUp      [p,sc,n,es].fix(0.0)
            OptModel.vReserveDown    [p,sc,n,es].fix(0.0)
            OptModel.vESSSpillage    [p,sc,n,es].fix(0.0)
            nFixedVariables += 5
        if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0:
            OptModel.vCharge2ndBlock [p,sc,n,es].fix(0.0)
            nFixedVariables += 1
        if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0 or mTEPES.pIndOperReserve[es] == 1:
            OptModel.vESSReserveUp   [p,sc,n,es].fix(0.0)
            OptModel.vESSReserveDown [p,sc,n,es].fix(0.0)
            nFixedVariables += 2
        if  mTEPES.pMaxStorage       [p,sc,n,es] ==  0.0:
            OptModel.vESSInventory   [p,sc,n,es].fix(0.0)
            nFixedVariables += 1

    if mTEPES.pIndHydroTopology == 1:
        for p,sc,n,h in mTEPES.psnh:
            # ESS with no charge capacity or not storage capacity can't charge
            if  mTEPES.pMaxCharge        [p,sc,n,h ] ==  0.0:
                OptModel.vESSTotalCharge [p,sc,n,h ].fix(0.0)
                nFixedVariables += 1
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0:
                OptModel.vCharge2ndBlock [p,sc,n,h ].fix(0.0)
                nFixedVariables += 1
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0 or mTEPES.pIndOperReserve[h ] == 1:
                OptModel.vESSReserveUp   [p,sc,n,h ].fix(0.0)
                OptModel.vESSReserveDown [p,sc,n,h ].fix(0.0)
                nFixedVariables += 2

    # thermal and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if len(mTEPES.tq):
        mTEPES.go = [k for k in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if k not in mTEPES.sq]
    else:
        mTEPES.go = [k for k in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__)                      ]

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in st == stt and mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn , ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.nn                              and           (p,sc,st,nn) in mTEPES.s2n)

        if len(mTEPES.n):
            # determine the first load level of each stage
            n1 = next(iter(mTEPES.psn))
            # commit the units and their output at the first load level of each stage
            pSystemOutput = 0.0
            for nr in mTEPES.nr:
                if pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[nr] == 1:
                    mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPowerElec[n1,nr]
                    mTEPES.pInitialUC    [n1,nr] = 1
                    pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

            # determine the initial committed units and their output at the first load level of each period, scenario, and stage
            for go in mTEPES.go:
                if pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[go] == 0:
                    if go in mTEPES.re:
                        mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPowerElec[n1,go]
                    else:
                        mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPowerElec[n1,go]
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
                if es not in mTEPES.ec and (p,sc,mTEPES.n.last(),es) in mTEPES.psnes:
                    OptModel.vESSInventory[p,sc,mTEPES.n.last(),es].fix(mTEPES.pIniInventory[p,sc,mTEPES.n.last(),es])

            if mTEPES.pIndHydroTopology == 1:
                # fixing the reservoir volume at the last load level of the stage for every period and scenario if between storage limits
                for rs in mTEPES.rs:
                    if rs not in mTEPES.rn and (p,sc,mTEPES.n.last(),rs) in mTEPES.psnrs:
                        OptModel.vReservoirVolume[p,sc,mTEPES.n.last(),rs].fix(mTEPES.pIniVolume[p,sc,mTEPES.n.last(),rs]())

    # activate all the periods, scenarios, and load levels again
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for                    (p,sc,stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn : nn  in mTEPES.nn                               and sum(1 for st in mTEPES.st if (p,sc,st, nn) in mTEPES.s2n))

    # fixing the ESS inventory at the end of the following pStorageTimeStep (daily, weekly, monthly) if between storage limits, i.e.,
    # for daily ESS is fixed at the end of the week, for weekly ESS is fixed at the end of the month, for monthly ESS is fixed at the end of the year
    # for p,sc,n,es in mTEPES.psnes:
    #     if es not in mTEPES.ec:
    #         if mTEPES.pStorageType[es] == 'Hourly'  and mTEPES.n.ord(n) % int(  24/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Weekly'  and mTEPES.n.ord(n) % int( 672/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1

    # if mTEPES.pIndHydroTopology == 1:
        # fixing the reservoir volume at the end of the following pReservoirTimeStep (daily, weekly, monthly) if between storage limits, i.e.,
        # for daily reservoir is fixed at the end of the week, for weekly reservoir is fixed at the end of the month, for monthly reservoir is fixed at the end of the year
        # for p,sc,n,rs in mTEPES.psnrs:
        #     if rs not in mTEPES.rn:
        #         if mTEPES.pReservoirType[rs] == 'Hourly'  and mTEPES.n.ord(n) % int(  24/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Weekly'  and mTEPES.n.ord(n) % int( 672/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1

    for p,sc,n,ec in mTEPES.psnec:
        if mTEPES.pEnergyInflows        [p,sc,n,ec]() == 0.0:
            OptModel.vEnergyInflows     [p,sc,n,ec].fix (0.0)
            nFixedVariables += 1

    # if no operating reserve is required no variables are needed
    for p,sc,n,ar,nr in mTEPES.psnar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g and (p,nr) in mTEPES.pnr:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
    for p,sc,n,ar,es in mTEPES.psnar*mTEPES.es:
        if (ar,es) in mTEPES.a2g and (p,es) in mTEPES.pes:
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
                if (p,es) in mTEPES.pes:
                    OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    if mTEPES.pIndBinSingleNode() == 0:
        for p,sc,n in mTEPES.psn:
            OptModel.vTheta[p,sc,n,mTEPES.rf.first()].fix(0.0)
            nFixedVariables += 1

    # fixing the ENS in nodes with no demand
    for p,sc,n,nd in mTEPES.psnnd:
        if mTEPES.pDemandElec[p,sc,n,nd] ==  0.0:
            OptModel.vENS[p,sc,n,nd].fix(0.0)
            nFixedVariables += 1

    if mTEPES.pIndHydrogen == 1:
        # fixing the H2 ENS in nodes with no hydrogen demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandH2[p,sc,n,nd] == 0.0:
                OptModel.vH2NS[p,sc,n,nd].fix (0.0)
                nFixedVariables += 1

    if mTEPES.pIndHeat == 1:
        # fixing the heat ENS in nodes with no heat demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandHeat[p,sc,n,nd] == 0.0:
                OptModel.vHeatNS[p,sc,n,nd].fix (0.0)
                nFixedVariables += 1

    # do not install/retire power plants and lines if not allowed in this period
    for p,eb in mTEPES.peb:
        if mTEPES.pElecGenPeriodIni[eb] > p:
            OptModel.vGenerationInvest[p,eb].fix(0)
            OptModel.vGenerationInvPer[p,eb].fix(0)
            nFixedVariables += 2
        if mTEPES.pElecGenPeriodFin[eb] < p:
            OptModel.vGenerationInvPer[p,eb].fix(0)
            nFixedVariables += 1

    for p,gd in mTEPES.pgd:
        if mTEPES.pElecGenPeriodIni[gd] > p:
            OptModel.vGenerationRetire[p,gd].fix(0)
            OptModel.vGenerationRetPer[p,gd].fix(0)
            nFixedVariables += 2
        if mTEPES.pElecGenPeriodFin[gd] < p:
            OptModel.vGenerationRetPer[p,gd].fix(0)
            nFixedVariables += 1

    for p,ni,nf,cc in mTEPES.plc:
        if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p:
            OptModel.vNetworkInvest[p,ni,nf,cc].fix(0)
            OptModel.vNetworkInvPer[p,ni,nf,cc].fix(0)
            nFixedVariables += 2
        if mTEPES.pElecNetPeriodFin[ni,nf,cc] < p:
            OptModel.vNetworkInvPer[p,ni,nf,cc].fix(0)
            nFixedVariables += 1

    if mTEPES.pIndHydroTopology == 1:
        for p,rc in mTEPES.prc:
            if mTEPES.pRsrPeriodIni[rc] > p:
                OptModel.vReservoirInvest[p,rc].fix(0)
                OptModel.vReservoirInvPer[p,rc].fix(0)
                nFixedVariables += 2
            if mTEPES.pRsrPeriodFin[rc] < p:
                OptModel.vReservoirInvPer[p,rc].fix(0)
                nFixedVariables += 1

    if mTEPES.pIndHydrogen == 1:
        for p,ni,nf,cc in mTEPES.ppc:
            if mTEPES.pH2PipePeriodIni[ni,nf,cc] > p:
                OptModel.vH2PipeInvest[p,ni,nf,cc].fix(0)
                OptModel.vH2PipeInvPer[p,ni,nf,cc].fix(0)
                nFixedVariables += 2
            if mTEPES.pH2PipePeriodFin[ni,nf,cc] < p:
                OptModel.vH2PipeInvPer[p,ni,nf,cc].fix(0)
                nFixedVariables += 1

    if mTEPES.pIndHeat == 1:
        for p,ni,nf,cc in mTEPES.phc:
            if mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p:
                OptModel.vHeatPipeInvest[p,ni,nf,cc].fix(0)
                OptModel.vHeatPipeInvPer[p,ni,nf,cc].fix(0)
                nFixedVariables += 2
            if mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p:
                OptModel.vHeatPipeInvPer[p,ni,nf,cc].fix(0)
                nFixedVariables += 1

    # remove power plants and lines not installed in this period
    for p,g in mTEPES.pg:
        if g not in mTEPES.eb and mTEPES.pElecGenPeriodIni[g ] > p:
            for sc,n in mTEPES.sc*mTEPES.n:
                OptModel.vTotalOutput   [p,sc,n,g].fix(0.0)
                nFixedVariables += 1

    for p,sc,nr in mTEPES.psnr:
        if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p:
            OptModel.vMaxCommitment[p,sc,nr].fix(0)
            nFixedVariables += 1
    for p,sc,n,nr in mTEPES.psnnr:
        if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p:
            OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
            OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
            OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
            OptModel.vCommitment    [p,sc,n,nr].fix(0  )
            OptModel.vStartUp       [p,sc,n,nr].fix(0  )
            OptModel.vShutDown      [p,sc,n,nr].fix(0  )
            nFixedVariables += 6

    for p,sc,n,es in mTEPES.psnes:
        if es not in mTEPES.ec and mTEPES.pElecGenPeriodIni[es] > p:
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
        for p,sc,n,rs in mTEPES.psnrs:
            if rs not in mTEPES.rn and mTEPES.pRsrPeriodIni[rs] > p:
                OptModel.vEnergyOutflows        [p,sc,n,rs].fix(0.0)
                OptModel.vReservoirVolume       [p,sc,n,rs].fix(0.0)
                OptModel.vReservoirSpillage     [p,sc,n,rs].fix(0.0)
                mTEPES.pIniVolume               [p,sc,n,rs] =   0.0
                mTEPES.pHydroInflows            [p,sc,n,rs] =   0.0
                nFixedVariables += 3
                for h in mTEPES.h:
                    if (rs,h) in mTEPES.r2h:
                        OptModel.vESSTotalCharge[p,sc,n,h ].fix(0.0)
                        OptModel.vCharge2ndBlock[p,sc,n,h ].fix(0.0)
                        OptModel.vESSReserveUp  [p,sc,n,h ].fix(0.0)
                        OptModel.vESSReserveDown[p,sc,n,h ].fix(0.0)
                        nFixedVariables += 4

    [OptModel.vFlowElec    [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    [OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(0  ) for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    [OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0  ) for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    [OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0  ) for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    nFixedVariables += sum(                        4  for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p)

    [OptModel.vLineLosses  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    nFixedVariables += sum(                        1  for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p)

    if mTEPES.pIndHydrogen == 1:
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnpa if (ni,nf,cc) not in mTEPES.pc and mTEPES.pH2PipePeriodIni[ni,nf,cc] > p]
        nFixedVariables += sum(                    4  for p,sc,n,ni,nf,cc in mTEPES.psnpa if (ni,nf,cc) not in mTEPES.pc and mTEPES.pH2PipePeriodIni[ni,nf,cc] > p)

    if mTEPES.pIndHeat == 1:
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnha if (ni,nf,cc) not in mTEPES.hc and mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p]
        nFixedVariables += sum(                    4  for p,sc,n,ni,nf,cc in mTEPES.psnha if (ni,nf,cc) not in mTEPES.hc and mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p)

    # tolerance to consider 0 a number
    pEpsilon = 1e-4
    for p,eb in mTEPES.peb:
        if  mTEPES.pGenLoInvest[  eb      ]() <       pEpsilon:
            mTEPES.pGenLoInvest[  eb      ]   = 0
        if  mTEPES.pGenUpInvest[  eb      ]() <       pEpsilon:
            mTEPES.pGenUpInvest[  eb      ]   = 0
        if  mTEPES.pGenLoInvest[  eb      ]() > 1.0 - pEpsilon:
            mTEPES.pGenLoInvest[  eb      ]   = 1
        if  mTEPES.pGenUpInvest[  eb      ]() > 1.0 - pEpsilon:
            mTEPES.pGenUpInvest[  eb      ]   = 1
        if  mTEPES.pGenLoInvest[  eb      ]() >   mTEPES.pGenUpInvest[eb      ]():
            mTEPES.pGenLoInvest[  eb      ]   =   mTEPES.pGenUpInvest[eb      ]()
    [OptModel.vGenerationInvest[p,eb      ].setlb(mTEPES.pGenLoInvest[eb      ]()) for p,eb in mTEPES.peb]
    [OptModel.vGenerationInvest[p,eb      ].setub(mTEPES.pGenUpInvest[eb      ]()) for p,eb in mTEPES.peb]
    for p,gd in mTEPES.pgd:
        if  mTEPES.pGenLoRetire[  gd      ]() < pEpsilon:
            mTEPES.pGenLoRetire[  gd      ]   = 0
        if  mTEPES.pGenUpRetire[  gd      ]() <       pEpsilon:
            mTEPES.pGenUpRetire[  gd      ]   = 0
        if  mTEPES.pGenLoRetire[  gd      ]() > 1.0 - pEpsilon:
            mTEPES.pGenLoRetire[  gd      ]   = 1
        if  mTEPES.pGenUpRetire[  gd      ]() > 1.0 - pEpsilon:
            mTEPES.pGenUpRetire[  gd      ]   = 1
        if  mTEPES.pGenLoRetire[  gd      ]() >   mTEPES.pGenUpRetire[gd      ]():
            mTEPES.pGenLoRetire[  gd      ]   =   mTEPES.pGenUpRetire[gd      ]()
    [OptModel.vGenerationRetire[p,gd      ].setlb(mTEPES.pGenLoRetire[gd      ]()) for p,gd in mTEPES.pgd]
    [OptModel.vGenerationRetire[p,gd      ].setub(mTEPES.pGenUpRetire[gd      ]()) for p,gd in mTEPES.pgd]
    for p,ni,nf,cc in mTEPES.plc:
        if  mTEPES.pNetLoInvest[  ni,nf,cc]() <       pEpsilon:
            mTEPES.pNetLoInvest[  ni,nf,cc]   = 0
        if  mTEPES.pNetUpInvest[  ni,nf,cc]() <       pEpsilon:
            mTEPES.pNetUpInvest[  ni,nf,cc]   = 0
        if  mTEPES.pNetLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
            mTEPES.pNetLoInvest[  ni,nf,cc]   = 1
        if  mTEPES.pNetUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
            mTEPES.pNetUpInvest[  ni,nf,cc]   = 1
        if  mTEPES.pNetLoInvest[  ni,nf,cc]() >   mTEPES.pNetUpInvest[ni,nf,cc]():
            mTEPES.pNetLoInvest[  ni,nf,cc]   =   mTEPES.pNetUpInvest[ni,nf,cc]()
    [OptModel.vNetworkInvest   [p,ni,nf,cc].setlb(mTEPES.pNetLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.plc]
    [OptModel.vNetworkInvest   [p,ni,nf,cc].setub(mTEPES.pNetUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.plc]

    if mTEPES.pIndHydroTopology == 1:
        for p,rc in mTEPES.prc:
            if  mTEPES.pRsrLoInvest[  rc      ]() <       pEpsilon:
                mTEPES.pRsrLoInvest[  rc      ]   = 0
            if  mTEPES.pRsrUpInvest[  rc      ]() <       pEpsilon:
                mTEPES.pRsrUpInvest[  rc      ]   = 0
            if  mTEPES.pRsrLoInvest[  rc      ]() > 1.0 - pEpsilon:
                mTEPES.pRsrLoInvest[  rc      ]   = 1
            if  mTEPES.pRsrUpInvest[  rc      ]() > 1.0 - pEpsilon:
                mTEPES.pRsrUpInvest[  rc      ]   = 1
            if  mTEPES.pRsrLoInvest[  rc      ]() >   mTEPES.pRsrUpInvest[rc      ]():
                mTEPES.pRsrLoInvest[  rc      ]   =   mTEPES.pRsrUpInvest[rc      ]()
        [OptModel.vReservoirInvest [p,rc      ].setlb(mTEPES.pRsrLoInvest[rc      ]()) for p,rc in mTEPES.prc]
        [OptModel.vReservoirInvest [p,rc      ].setub(mTEPES.pRsrUpInvest[rc      ]()) for p,rc in mTEPES.prc]

    if mTEPES.pIndHydrogen == 1:
        for p,ni,nf,cc in mTEPES.ppc:
            if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pH2PipeLoInvest[  ni,nf,cc]   = 0
            if  mTEPES.pH2PipeUpInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pH2PipeUpInvest[  ni,nf,cc]   = 0
            if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pH2PipeLoInvest[  ni,nf,cc]   = 1
            if  mTEPES.pH2PipeUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pH2PipeUpInvest[  ni,nf,cc]   = 1
            if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() >   mTEPES.pH2PipeUpInvest[ni,nf,cc]():
                mTEPES.pH2PipeLoInvest[  ni,nf,cc]   =   mTEPES.pH2PipeUpInvest[ni,nf,cc]()
        [OptModel.vH2PipeInvest       [p,ni,nf,cc].setlb(mTEPES.pH2PipeLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.ppc]
        [OptModel.vH2PipeInvest       [p,ni,nf,cc].setub(mTEPES.pH2PipeUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.ppc]

    if mTEPES.pIndHeat == 1:
        for p,ni,nf,cc in mTEPES.phc:
            if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   = 0
            if  mTEPES.pHeatPipeUpInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pHeatPipeUpInvest[  ni,nf,cc]   = 0
            if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   = 1
            if  mTEPES.pHeatPipeUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pHeatPipeUpInvest[  ni,nf,cc]   = 1
            if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() >   mTEPES.pHeatPipeUpInvest[ni,nf,cc]():
                mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   =   mTEPES.pHeatPipeUpInvest[ni,nf,cc]()
        [OptModel.vHeatPipeInvest       [p,ni,nf,cc].setlb(mTEPES.pHeatPipeLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.phc]
        [OptModel.vHeatPipeInvest       [p,ni,nf,cc].setub(mTEPES.pHeatPipeUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.phc]

    # detecting infeasibility: sum of scenario probabilities must be 1 in each period
    # for p in mTEPES.p:
    #     if abs(sum(mTEPES.pScenProb[p,sc] for sc in mTEPES.sc)-1.0) > 1e-6:
    #         print('### Sum of scenario probabilities different from 1 in period ', p)
    #         assert (0 == 1)

    for es in mTEPES.es:
        # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows
        if sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn) > 0.0:
            print('### Total minimum output greater than total inflows for ESS unit ', es)
            assert (0 == 1)
        if sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn) < 0.0:
            print('### Total maximum charge lower than total outflows for ESS unit ', es)
            assert (0 == 1)

    # detect inventory infeasibility
    for p,sc,n,es in mTEPES.ps*mTEPES.nesc:
        if mTEPES.pMaxCapacity[p,sc,n,es]:
            if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
                if mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                    print('### Inventory equation violation ', p, sc, n, es)
                    assert (0 == 1)
            elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
                if mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                    print('### Inventory equation violation ', p, sc, n, es)
                    assert (0 == 1)

    # detect minimum energy infeasibility
    for p,sc,n,g in mTEPES.ps*mTEPES.ngen:
        if (p,sc,g) in mTEPES.gm:
            if sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
                print('### Minimum energy violation ', p, sc, n, g)
                assert (0 == 1)

    # detecting reserve margin infeasibility
    for p,ar in mTEPES.p*mTEPES.ar:
        if sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g) < mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]:
            print('### Reserve margin infeasibility ', p, ar)
            assert (0 == 1)

    mTEPES.nFixedVariables = Param(initialize=round(nFixedVariables), within=NonNegativeIntegers, doc='Number of fixed variables')

    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
