"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - December 10, 2024
"""

import datetime
import time
import math
import os
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import DataPortal, Set, Param, Var, Binary, NonNegativeReals, NonNegativeIntegers, PositiveReals, PositiveIntegers, Reals, UnitInterval, Any
from   pyomo.environ import ConcreteModel, Set, Block, Param, Boolean

def InputData(DirName, CaseName, mTEPES, pIndLogConsole):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    #%% reading data from CSV
    dfOption                = pd.read_csv(f'{_path}/oT_Data_Option_'                f'{CaseName}.csv', header=0                   )
    dfParameter             = pd.read_csv(f'{_path}/oT_Data_Parameter_'             f'{CaseName}.csv', header=0                   )
    dfPeriod                = pd.read_csv(f'{_path}/oT_Data_Period_'                f'{CaseName}.csv', header=0, index_col=[0    ])
    dfScenario              = pd.read_csv(f'{_path}/oT_Data_Scenario_'              f'{CaseName}.csv', header=0, index_col=[0,1  ])
    dfStage                 = pd.read_csv(f'{_path}/oT_Data_Stage_'                 f'{CaseName}.csv', header=0, index_col=[0    ])
    dfDuration              = pd.read_csv(f'{_path}/oT_Data_Duration_'              f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfReserveMargin         = pd.read_csv(f'{_path}/oT_Data_ReserveMargin_'         f'{CaseName}.csv', header=0, index_col=[0,1  ])
    dfEmission              = pd.read_csv(f'{_path}/oT_Data_Emission_'              f'{CaseName}.csv', header=0, index_col=[0,1  ])
    dfRESEnergy             = pd.read_csv(f'{_path}/oT_Data_RESEnergy_'             f'{CaseName}.csv', header=0, index_col=[0,1  ])
    dfDemand                = pd.read_csv(f'{_path}/oT_Data_Demand_'                f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfInertia               = pd.read_csv(f'{_path}/oT_Data_Inertia_'               f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfUpOperatingReserve    = pd.read_csv(f'{_path}/oT_Data_OperatingReserveUp_'    f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfDwOperatingReserve    = pd.read_csv(f'{_path}/oT_Data_OperatingReserveDown_'  f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfGeneration            = pd.read_csv(f'{_path}/oT_Data_Generation_'            f'{CaseName}.csv', header=0, index_col=[0    ])
    dfVariableMinPower      = pd.read_csv(f'{_path}/oT_Data_VariableMinGeneration_' f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMaxPower      = pd.read_csv(f'{_path}/oT_Data_VariableMaxGeneration_' f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMinCharge     = pd.read_csv(f'{_path}/oT_Data_VariableMinConsumption_'f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMaxCharge     = pd.read_csv(f'{_path}/oT_Data_VariableMaxConsumption_'f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMinStorage    = pd.read_csv(f'{_path}/oT_Data_VariableMinStorage_'    f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMaxStorage    = pd.read_csv(f'{_path}/oT_Data_VariableMaxStorage_'    f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMinEnergy     = pd.read_csv(f'{_path}/oT_Data_VariableMinEnergy_'     f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableMaxEnergy     = pd.read_csv(f'{_path}/oT_Data_VariableMaxEnergy_'     f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableFuelCost      = pd.read_csv(f'{_path}/oT_Data_VariableFuelCost_'      f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfVariableEmissionCost  = pd.read_csv(f'{_path}/oT_Data_VariableEmissionCost_'  f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfEnergyInflows         = pd.read_csv(f'{_path}/oT_Data_EnergyInflows_'         f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfEnergyOutflows        = pd.read_csv(f'{_path}/oT_Data_EnergyOutflows_'        f'{CaseName}.csv', header=0, index_col=[0,1,2])
    dfNodeLocation          = pd.read_csv(f'{_path}/oT_Data_NodeLocation_'          f'{CaseName}.csv', header=0, index_col=[0    ])
    dfNetwork               = pd.read_csv(f'{_path}/oT_Data_Network_'               f'{CaseName}.csv', header=0, index_col=[0,1,2])

    try:
        dfReservoir         = pd.read_csv(f'{_path}/oT_Data_Reservoir_'             f'{CaseName}.csv', header=0, index_col=[0    ])
        dfVariableMinVolume = pd.read_csv(f'{_path}/oT_Data_VariableMinVolume_'     f'{CaseName}.csv', header=0, index_col=[0,1,2])
        dfVariableMaxVolume = pd.read_csv(f'{_path}/oT_Data_VariableMaxVolume_'     f'{CaseName}.csv', header=0, index_col=[0,1,2])
        dfHydroInflows      = pd.read_csv(f'{_path}/oT_Data_HydroInflows_'          f'{CaseName}.csv', header=0, index_col=[0,1,2])
        dfHydroOutflows     = pd.read_csv(f'{_path}/oT_Data_HydroOutflows_'         f'{CaseName}.csv', header=0, index_col=[0,1,2])
        pIndHydroTopology   = 1
    except:
        pIndHydroTopology   = 0
        print('**** No hydropower topology')

    try:
        dfDemandHydrogen    = pd.read_csv(f'{_path}/oT_Data_DemandHydrogen_'        f'{CaseName}.csv', header=0, index_col=[0,1,2])
        dfNetworkHydrogen   = pd.read_csv(f'{_path}/oT_Data_NetworkHydrogen_'       f'{CaseName}.csv', header=0, index_col=[0,1,2])
        pIndHydrogen        = 1
    except:
        pIndHydrogen        = 0
        print('**** No hydrogen energy carrier')

    try:
        dfDemandHeat        = pd.read_csv(f'{_path}/oT_Data_DemandHeat_'            f'{CaseName}.csv', header=0, index_col=[0,1,2])
        dfReserveMarginHeat = pd.read_csv(f'{_path}/oT_Data_ReserveMarginHeat_'     f'{CaseName}.csv', header=0, index_col=[0,1  ])
        dfNetworkHeat       = pd.read_csv(f'{_path}/oT_Data_NetworkHeat_'           f'{CaseName}.csv', header=0, index_col=[0,1,2])
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
        dfReserveMarginHeat.fillna(0.0, inplace=True)
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
        print('Reserve margin electricity            \n', dfReserveMargin.describe       (), '\n')
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
            print('Reserve margin heat               \n', dfReserveMarginHeat.describe   (), '\n')
            print('Heat pipe network                 \n', dfNetworkHeat.describe         (), '\n')

    #%% reading the sets
    dictSets = DataPortal()
    dictSets.load(filename=f'{_path}/oT_Dict_Period_'       f'{CaseName}.csv', set='p'   , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Scenario_'     f'{CaseName}.csv', set='sc'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Stage_'        f'{CaseName}.csv', set='st'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_LoadLevel_'    f'{CaseName}.csv', set='n'   , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Generation_'   f'{CaseName}.csv', set='g'   , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Technology_'   f'{CaseName}.csv', set='gt'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Storage_'      f'{CaseName}.csv', set='et'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Node_'         f'{CaseName}.csv', set='nd'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Zone_'         f'{CaseName}.csv', set='zn'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Area_'         f'{CaseName}.csv', set='ar'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Region_'       f'{CaseName}.csv', set='rg'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Circuit_'      f'{CaseName}.csv', set='cc'  , format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_Line_'         f'{CaseName}.csv', set='lt'  , format='set')

    dictSets.load(filename=f'{_path}/oT_Dict_NodeToZone_'   f'{CaseName}.csv', set='ndzn', format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_ZoneToArea_'   f'{CaseName}.csv', set='znar', format='set')
    dictSets.load(filename=f'{_path}/oT_Dict_AreaToRegion_' f'{CaseName}.csv', set='arrg', format='set')

    mTEPES.pp   = Set(initialize=dictSets['p'   ], doc='periods', within=PositiveIntegers)
    mTEPES.scc  = Set(initialize=dictSets['sc'  ], doc='scenarios'                       )
    mTEPES.stt  = Set(initialize=dictSets['st'  ], doc='stages'                          )
    mTEPES.nn   = Set(initialize=dictSets['n'   ], doc='load levels'                     )
    mTEPES.gg   = Set(initialize=dictSets['g'   ], doc='units'                           )
    mTEPES.gt   = Set(initialize=dictSets['gt'  ], doc='technologies'                    )
    mTEPES.nd   = Set(initialize=dictSets['nd'  ], doc='nodes'                           )
    mTEPES.ni   = Set(initialize=dictSets['nd'  ], doc='nodes'                           )
    mTEPES.nf   = Set(initialize=dictSets['nd'  ], doc='nodes'                           )
    mTEPES.zn   = Set(initialize=dictSets['zn'  ], doc='zones'                           )
    mTEPES.ar   = Set(initialize=dictSets['ar'  ], doc='areas'                           )
    mTEPES.rg   = Set(initialize=dictSets['rg'  ], doc='regions'                         )
    mTEPES.cc   = Set(initialize=dictSets['cc'  ], doc='circuits'                        )
    mTEPES.c2   = Set(initialize=dictSets['cc'  ], doc='circuits'                        )
    mTEPES.lt   = Set(initialize=dictSets['lt'  ], doc='electric line types'             )
    mTEPES.ndzn = Set(initialize=dictSets['ndzn'], doc='node to zone'                    )
    mTEPES.znar = Set(initialize=dictSets['znar'], doc='zone to area'                    )
    mTEPES.arrg = Set(initialize=dictSets['arrg'], doc='area to region'                  )

    try:
        import csv
        def count_lines_in_csv(csv_file_path):
            with open(csv_file_path, 'r', newline='') as file:
                reader = csv.reader(file)
                num_lines = sum(1 for _ in reader)
            return num_lines

        mTEPES.rs  = Set(initialize=[], doc='reservoirs'               )
        mTEPES.r2h = Set(initialize=[], doc='reservoir to hydro'       )
        mTEPES.h2r = Set(initialize=[], doc='hydro to reservoir'       )
        mTEPES.r2r = Set(initialize=[], doc='reservoir to reservoir'   )
        mTEPES.p2r = Set(initialize=[], doc='pumped-hydro to reservoir')
        mTEPES.r2p = Set(initialize=[], doc='reservoir to pumped-hydro')

        if count_lines_in_csv(     f'{_path}/oT_Dict_Reservoir_'            f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_Reservoir_'            f'{CaseName}.csv', set='rs' , format='set')
            mTEPES.del_component(mTEPES.rs)
            mTEPES.rs  = Set(initialize=dictSets['rs' ], doc='reservoirs'               )
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToHydro_'     f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToHydro_'     f'{CaseName}.csv', set='r2h', format='set')
            mTEPES.del_component(mTEPES.r2h)
            mTEPES.r2h = Set(initialize=dictSets['r2h'], doc='reservoir to hydro'       )
        if count_lines_in_csv(     f'{_path}/oT_Dict_HydroToReservoir_'     f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_HydroToReservoir_'     f'{CaseName}.csv', set='h2r', format='set')
            mTEPES.del_component(mTEPES.h2r)
            mTEPES.h2r = Set(initialize=dictSets['h2r'], doc='hydro to reservoir'       )
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToReservoir_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToReservoir_' f'{CaseName}.csv', set='r2r', format='set')
            mTEPES.del_component(mTEPES.r2r)
            mTEPES.r2r = Set(initialize=dictSets['r2r'], doc='reservoir to reservoir'   )
        if count_lines_in_csv(     f'{_path}/oT_Dict_PumpedHydroToReservoir_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_PumpedHydroToReservoir_' f'{CaseName}.csv', set='p2r', format='set')
            mTEPES.del_component(mTEPES.p2r)
            mTEPES.p2r = Set(initialize=dictSets['p2r'], doc='pumped-hydro to reservoir')
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToPumpedHydro_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToPumpedHydro_' f'{CaseName}.csv', set='r2p', format='set')
            mTEPES.del_component(mTEPES.r2p)
            mTEPES.r2p = Set(initialize=dictSets['r2p'], doc='reservoir to pumped-hydro')
    except:
        pass

    #%% parameters
    pIndBinGenInvest       = dfOption   ['IndBinGenInvest'    ].iloc[0].astype('int')                # Indicator of binary generation        expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinGenRetire       = dfOption   ['IndBinGenRetirement'].iloc[0].astype('int')                # Indicator of binary generation        retirement decisions,0 continuous       - 1 binary - 2 no retirement variables
    pIndBinRsrInvest       = dfOption   ['IndBinRsrInvest'    ].iloc[0].astype('int')                # Indicator of binary reservoir         expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetElecInvest   = dfOption   ['IndBinNetInvest'    ].iloc[0].astype('int')                # Indicator of binary electric network  expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetH2Invest     = dfOption   ['IndBinNetH2Invest'  ].iloc[0].astype('int')                # Indicator of binary hydrogen pipeline expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinNetHeatInvest   = dfOption   ['IndBinNetHeatInvest'].iloc[0].astype('int')                # Indicator of binary heat     pipe     expansion decisions, 0 continuous       - 1 binary - 2 no investment variables
    pIndBinGenOperat       = dfOption   ['IndBinGenOperat'    ].iloc[0].astype('int')                # Indicator of binary generation        operation decisions, 0 continuous       - 1 binary
    pIndBinSingleNode      = dfOption   ['IndBinSingleNode'   ].iloc[0].astype('int')                # Indicator of single node although with electric network,   0 electric network - 1 single node
    pIndBinGenRamps        = dfOption   ['IndBinGenRamps'     ].iloc[0].astype('int')                # Indicator of ramp constraints,                             0 no ramps         - 1 ramp constraints
    pIndBinGenMinTime      = dfOption   ['IndBinGenMinTime'   ].iloc[0].astype('int')                # Indicator of minimum up/downtime constraints,              0 no min time      - 1 min time constraints
    pIndBinLineCommit      = dfOption   ['IndBinLineCommit'   ].iloc[0].astype('int')                # Indicator of binary electric network switching decisions,  0 continuous       - 1 binary
    pIndBinNetLosses       = dfOption   ['IndBinNetLosses'    ].iloc[0].astype('int')                # Indicator of        electric network losses,               0 lossless         - 1 ohmic losses
    pENSCost               = dfParameter['ENSCost'            ].iloc[0] * 1e-3                       # cost of energy   not served               [MEUR/GWh]
    pH2NSCost              = dfParameter['HNSCost'            ].iloc[0] * 1e-3                       # cost of hydrogen not served               [MEUR/tH2]
    pHeatNSCost            = dfParameter['HTNSCost'           ].iloc[0] * 1e-3                       # cost of heat     not served               [MEUR/GWh]
    pCO2Cost               = dfParameter['CO2Cost'            ].iloc[0]                              # cost of CO2 emission                      [EUR/tCO2]
    pEconomicBaseYear      = dfParameter['EconomicBaseYear'   ].iloc[0]                              # economic base year                        [year]
    pAnnualDiscRate        = dfParameter['AnnualDiscountRate' ].iloc[0]                              # annual discount rate                      [p.u.]
    pUpReserveActivation   = dfParameter['UpReserveActivation'].iloc[0]                              # upward   reserve activation               [p.u.]
    pDwReserveActivation   = dfParameter['DwReserveActivation'].iloc[0]                              # downward reserve activation               [p.u.]
    pMinRatioDwUp          = dfParameter['MinRatioDwUp'       ].iloc[0]                              # minimum ratio down up operating reserves  [p.u.]
    pMaxRatioDwUp          = dfParameter['MaxRatioDwUp'       ].iloc[0]                              # maximum ratio down up operating reserves  [p.u.]
    pSBase                 = dfParameter['SBase'              ].iloc[0] * 1e-3                       # base power                                [GW]
    pReferenceNode         = dfParameter['ReferenceNode'      ].iloc[0]                              # reference node
    pTimeStep              = dfParameter['TimeStep'           ].iloc[0].astype('int')                # duration of the unit time step            [h]

    pPeriodWeight          = dfPeriod       ['Weight'        ].astype('int')                         # weights of periods                        [p.u.]
    pScenProb              = dfScenario     ['Probability'   ].astype('float64')                     # probabilities of scenarios                [p.u.]
    pStageWeight           = dfStage        ['Weight'        ].astype('float64')                     # weights of stages
    pDuration              = dfDuration     ['Duration'      ] * pTimeStep                           # duration of load levels                   [h]
    pLevelToStage          = dfDuration     ['Stage'         ]                                       # load levels assignment to stages
    pReserveMargin         = dfReserveMargin['ReserveMargin' ]                                       # minimum adequacy reserve margin           [p.u.]
    pEmission              = dfEmission     ['CO2Emission'   ]                                       # maximum CO2 emission                      [MtCO2]
    pRESEnergy             = dfRESEnergy    ['RESEnergy'     ]                                       # minimum RES energy                        [GWh]
    pDemandElec            = dfDemand              [mTEPES.nd] * 1e-3                                # electric demand                           [GW]
    pSystemInertia         = dfInertia             [mTEPES.ar]                                       # inertia                                   [s]
    pOperReserveUp         = dfUpOperatingReserve  [mTEPES.ar] * 1e-3                                # upward   operating reserve                [GW]
    pOperReserveDw         = dfDwOperatingReserve  [mTEPES.ar] * 1e-3                                # downward operating reserve                [GW]

    pVariableMinPowerElec = dfVariableMinPower.reindex    (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum power            [GW]
    pVariableMaxPowerElec = dfVariableMaxPower.reindex    (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum power            [GW]
    pVariableMinCharge    = dfVariableMinCharge.reindex   (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum charge           [GW]
    pVariableMaxCharge    = dfVariableMaxCharge.reindex   (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum charge           [GW]
    pVariableMinStorage   = dfVariableMinStorage.reindex  (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable minimum storage          [GWh]
    pVariableMaxStorage   = dfVariableMaxStorage.reindex  (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable maximum storage          [GWh]
    pVariableMinEnergy    = dfVariableMinEnergy.reindex   (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum energy           [GW]
    pVariableMaxEnergy    = dfVariableMaxEnergy.reindex   (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum energy           [GW]
    pVariableFuelCost     = dfVariableFuelCost.reindex    (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable fuel cost                [EUR/Mcal]
    pVariableEmissionCost = dfVariableEmissionCost.reindex(columns=mTEPES.gg, fill_value=0.0)        # dynamic variable emission cost            [EUR/tCO2]
    pEnergyInflows        = dfEnergyInflows.reindex       (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy inflows                    [GW]
    pEnergyOutflows       = dfEnergyOutflows.reindex      (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy outflows                   [GW]

    if pIndHydroTopology == 1:
        pVariableMinVolume = dfVariableMinVolume.reindex  (columns=mTEPES.rs, fill_value=0.0)        # dynamic variable minimum reservoir volume [hm3]
        pVariableMaxVolume = dfVariableMaxVolume.reindex  (columns=mTEPES.rs, fill_value=0.0)        # dynamic variable maximum reservoir volume [hm3]
        pHydroInflows      = dfHydroInflows.reindex       (columns=mTEPES.rs, fill_value=0.0)        # dynamic hydro inflows                     [m3/s]
        pHydroOutflows     = dfHydroOutflows.reindex      (columns=mTEPES.rs, fill_value=0.0)        # dynamic hydro outflows                    [m3/s]



    if pIndHydrogen == 1:
        pDemandH2          = dfDemandHydrogen      [mTEPES.nd]                           # hydrogen demand                           [tH2/h]

    if pIndHeat == 1:
        pReserveMarginHeat = dfReserveMarginHeat   ['ReserveMargin']                     # minimum adequacy reserve margin           [p.u.]
        pDemandHeat        = dfDemandHeat          [mTEPES.nd] * 1e-3                    # heat     demand                           [GW]

    if pTimeStep > 1:

        # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for the remaining parameters
        # Skip mean calculation for empty DataFrames (either full of 0s or NaNs)
        def ProcessParameter(pDataFrame: pd.DataFrame, pTimeStep: int) -> pd.DataFrame:
            if ((pDataFrame != 0 ) & (~pDataFrame.isna())).any().any():
                pDataFrame = pDataFrame.rolling(pTimeStep).mean()
                pDataFrame.fillna(0.0, inplace=True)
            return pDataFrame
        # Apply the ProcessParameter function to each DataFrame
        pDemandElec            = ProcessParameter(pDemandElec,           pTimeStep)
        pSystemInertia         = ProcessParameter(pSystemInertia,        pTimeStep)
        pOperReserveUp         = ProcessParameter(pOperReserveUp,        pTimeStep)
        pOperReserveDw         = ProcessParameter(pOperReserveDw,        pTimeStep)
        pVariableMinPowerElec  = ProcessParameter(pVariableMinPowerElec, pTimeStep)
        pVariableMaxPowerElec  = ProcessParameter(pVariableMaxPowerElec, pTimeStep)
        pVariableMinCharge     = ProcessParameter(pVariableMinCharge,    pTimeStep)
        pVariableMaxCharge     = ProcessParameter(pVariableMaxCharge,    pTimeStep)
        pVariableMinStorage    = ProcessParameter(pVariableMinStorage,   pTimeStep)
        pVariableMaxStorage    = ProcessParameter(pVariableMaxStorage,   pTimeStep)
        pVariableMinEnergy     = ProcessParameter(pVariableMinEnergy,    pTimeStep)
        pVariableMaxEnergy     = ProcessParameter(pVariableMaxEnergy,    pTimeStep)
        pVariableFuelCost      = ProcessParameter(pVariableFuelCost,     pTimeStep)
        pVariableEmissionCost  = ProcessParameter(pVariableEmissionCost, pTimeStep)
        pEnergyInflows         = ProcessParameter(pEnergyInflows,        pTimeStep)
        pEnergyOutflows        = ProcessParameter(pEnergyOutflows,       pTimeStep)

        if pIndHydroTopology == 1:
            pVariableMinVolume = ProcessParameter(pVariableMinVolume,    pTimeStep)
            pVariableMaxVolume = ProcessParameter(pVariableMaxVolume,    pTimeStep)
            pHydroInflows      = ProcessParameter(pHydroInflows,         pTimeStep)
            pHydroOutflows     = ProcessParameter(pHydroOutflows,        pTimeStep)

        if pIndHydrogen == 1:
            pDemandH2          = ProcessParameter(pDemandH2,             pTimeStep)

        if pIndHeat == 1:
            pDemandHeat        = ProcessParameter(pDemandHeat,           pTimeStep)

        # assign duration 0 to load levels not being considered, active load levels are at the end of every pTimeStep
        for n in range(pTimeStep-2,-1,-1):
            pDuration.iloc[[range(n,len(mTEPES.pp)*len(mTEPES.scc)*len(mTEPES.nn),pTimeStep)]] = 0

        for psn in pDuration.index:
            p, sc, n = psn
            if pPeriodWeight[p] == 0:
                pDuration.loc[p, sc, n] = 0
            if pScenProb[p, sc] == 0:
                pDuration.loc[p, sc, n] = 0
        print(pDuration)

    #%% generation parameters
    pGenToNode                  = dfGeneration  ['Node'                      ]                                                      # generator location in node
    pGenToTechnology            = dfGeneration  ['Technology'                ]                                                      # generator association to technology
    pGenToExclusiveGen          = dfGeneration  ['MutuallyExclusive'         ]                                                      # mutually exclusive generator
    pIndBinUnitInvest           = dfGeneration  ['BinaryInvestment'          ]                                                      # binary unit investment decision              [Yes]
    pIndBinUnitRetire           = dfGeneration  ['BinaryRetirement'          ]                                                      # binary unit retirement decision              [Yes]
    pIndBinUnitCommit           = dfGeneration  ['BinaryCommitment'          ]                                                      # binary unit commitment decision              [Yes]
    pIndBinStorInvest           = dfGeneration  ['StorageInvestment'         ]                                                      # storage linked to generation investment      [Yes]
    pIndOperReserve             = dfGeneration  ['NoOperatingReserve'        ]                                                      # no contribution to operating reserve         [Yes]
    pIndOutflowIncomp           = dfGeneration  ['OutflowsIncompatibility'   ]                                                      # outflows incompatibility with charging
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

    # replace PeriodFin = 0.0 by year 3000
    pElecGenPeriodFin = pElecGenPeriodFin.where(pElecGenPeriodFin != 0.0, 3000   )
    if pIndHydroTopology == 1:
        pRsrPeriodFin = pRsrPeriodFin.where    (pRsrPeriodFin     != 0.0, 3000   )
    pElecNetPeriodFin = pElecNetPeriodFin.where(pElecNetPeriodFin != 0.0, 3000   )
    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    pLineNTCBck       = pLineNTCBck.where      (pLineNTCBck  > 0.0,   pLineNTCFrw)
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    pLineNTCFrw       = pLineNTCFrw.where      (pLineNTCFrw  > 0.0,   pLineNTCBck)
    # replace pGenUpInvest = 0.0 by 1.0
    pGenUpInvest      = pGenUpInvest.where     (pGenUpInvest > 0.0,   1.0        )
    # replace pGenUpRetire = 0.0 by 1.0
    pGenUpRetire      = pGenUpRetire.where     (pGenUpRetire > 0.0,   1.0        )
    # replace pNetUpInvest = 0.0 by 1.0
    pNetUpInvest      = pNetUpInvest.where     (pNetUpInvest > 0.0,   1.0        )

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

        pH2PipePeriodFin = pH2PipePeriodFin.where(pH2PipePeriodFin != 0.0, 3000       )
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

        pHeatPipePeriodFin = pHeatPipePeriodFin.where(pHeatPipePeriodFin != 0.0, 3000         )
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
    mTEPES.p      = Set(doc='periods'                          , initialize=[pp     for pp   in mTEPES.pp  if pPeriodWeight       [pp] >  0.0 and sum(pDuration[pp,sc,n] for sc,n in mTEPES.scc*mTEPES.nn)])
    mTEPES.sc     = Set(doc='scenarios'                        , initialize=[scc    for scc  in mTEPES.scc                                    ])
    mTEPES.ps     = Set(doc='periods/scenarios'                , initialize=[(p,sc) for p,sc in mTEPES.p*mTEPES.sc if pScenProb [p,sc] >  0.0 and sum(pDuration[p,sc,n ] for    n in            mTEPES.nn)])
    mTEPES.st     = Set(doc='stages'                           , initialize=[stt    for stt  in mTEPES.stt if pStageWeight       [stt] >  0.0])
    mTEPES.n      = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(pDuration  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2     = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(pDuration  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.g      = Set(doc='generating              units'    , initialize=[gg     for gg   in mTEPES.gg  if (pRatedMaxPowerElec [gg] >  0.0 or  pRatedMaxCharge[gg] >  0.0 or pRatedMaxPowerHeat    [gg] >  0.0) and pElecGenPeriodIni[gg] <= mTEPES.p.last() and pElecGenPeriodFin[gg] >= mTEPES.p.first() and pGenToNode.reset_index().set_index(['Generator']).isin(mTEPES.nd)['Node'][gg]])  # excludes generators with empty node
    mTEPES.t      = Set(doc='thermal                 units'    , initialize=[g      for g    in mTEPES.g   if pRatedLinearOperCost[g ] >  0.0])
    mTEPES.re     = Set(doc='RES                     units'    , initialize=[g      for g    in mTEPES.g   if pRatedLinearOperCost[g ] == 0.0 and pRatedMaxStorage[g] == 0.0   and pProductionFunctionH2[g ] == 0.0 and pProductionFunctionHeat[g ] == 0.0  and pProductionFunctionHydro[g ] == 0.0])
    mTEPES.es     = Set(doc='ESS                     units'    , initialize=[g      for g    in mTEPES.g   if     (pRatedMaxCharge[g ] >  0.0 or  pRatedMaxStorage[g] >  0.0    or pProductionFunctionH2[g ]  > 0.0  or pProductionFunctionHeat[g ]  > 0.0) and pProductionFunctionHydro[g ] == 0.0])
    mTEPES.h      = Set(doc='hydro                   units'    , initialize=[g      for g    in mTEPES.g                                                                        if pProductionFunctionH2[g ] == 0.0 and pProductionFunctionHeat[g ] == 0.0  and pProductionFunctionHydro[g ]  > 0.0])
    mTEPES.el     = Set(doc='electrolyzer            units'    , initialize=[es     for es   in mTEPES.es                                                                       if pProductionFunctionH2[es]  > 0.0 and pProductionFunctionHeat[es] == 0.0  and pProductionFunctionHydro[es] == 0.0])
    mTEPES.hp     = Set(doc='heat pump & elec boiler units'    , initialize=[es     for es   in mTEPES.es                                                                       if pProductionFunctionH2[es] == 0.0 and pProductionFunctionHeat[es]  > 0.0  and pProductionFunctionHydro[es] == 0.0])
    mTEPES.ch     = Set(doc='CHP       & fuel boiler units'    , initialize=[g      for g    in mTEPES.g   if                                     pRatedMaxPowerHeat[g ] > 0.0 and pProductionFunctionHeat    [g ] == 0.0])
    mTEPES.bo     = Set(doc='            fuel boiler units'    , initialize=[ch     for ch   in mTEPES.ch  if pRatedMaxPowerElec  [ch] == 0.0 and pRatedMaxPowerHeat[ch] > 0.0 and pProductionFunctionHeat    [ch] == 0.0])
    mTEPES.hh     = Set(doc='        hydrogen boiler units'    , initialize=[bo     for bo   in mTEPES.bo                                                                       if pProductionFunctionH2ToHeat[bo] >  0.0])
    mTEPES.gc     = Set(doc='candidate               units'    , initialize=[g      for g    in mTEPES.g   if pGenInvestCost      [g ] >  0.0])
    mTEPES.gd     = Set(doc='retirement              units'    , initialize=[g      for g    in mTEPES.g   if pGenRetireCost      [g ] >  0.0])
    mTEPES.ec     = Set(doc='candidate ESS           units'    , initialize=[es     for es   in mTEPES.es  if pGenInvestCost      [es] >  0.0])
    mTEPES.bc     = Set(doc='candidate boiler        units'    , initialize=[bo     for bo   in mTEPES.bo  if pGenInvestCost      [bo] >  0.0])
    mTEPES.br     = Set(doc='all input       electric branches', initialize=sBrList        )
    mTEPES.ln     = Set(doc='all input       electric lines'   , initialize=dfNetwork.index)
    if len(mTEPES.ln) != len(dfNetwork.index):
        raise ValueError('### Some electric lines are invalid ', len(mTEPES.ln), len(dfNetwork.index))
    mTEPES.la     = Set(doc='all real        electric lines'   , initialize=[ln     for ln   in mTEPES.ln if pLineX              [ln] != 0.0 and pLineNTCFrw[ln] > 0.0 and pLineNTCBck[ln] > 0.0 and pElecNetPeriodIni[ln]  <= mTEPES.p.last() and pElecNetPeriodFin[ln]  >= mTEPES.p.first()])
    mTEPES.ls     = Set(doc='all real switch electric lines'   , initialize=[la     for la   in mTEPES.la if pIndBinLineSwitch   [la]       ])
    mTEPES.lc     = Set(doc='candidate       electric lines'   , initialize=[la     for la   in mTEPES.la if pNetFixedCost       [la] >  0.0])
    mTEPES.cd     = Set(doc='candidate    DC electric lines'   , initialize=[la     for la   in mTEPES.la if pNetFixedCost       [la] >  0.0 and pLineType[la] == 'DC'])
    mTEPES.ed     = Set(doc='existing     DC electric lines'   , initialize=[la     for la   in mTEPES.la if pNetFixedCost       [la] == 0.0 and pLineType[la] == 'DC'])
    mTEPES.ll     = Set(doc='loss            electric lines'   , initialize=[la     for la   in mTEPES.la if pLineLossFactor     [la] >  0.0 and pIndBinNetLosses > 0 ])
    mTEPES.rf     = Set(doc='reference node'                   , initialize=[pReferenceNode])
    mTEPES.gq     = Set(doc='gen    reactive units'            , initialize=[gg     for gg   in mTEPES.gg if pRMaxReactivePower  [gg] >  0.0 and                                                     pElecGenPeriodIni[gg]  <= mTEPES.p.last() and pElecGenPeriodFin[gg]  >= mTEPES.p.first()])
    mTEPES.sq     = Set(doc='synchr reactive units'            , initialize=[gg     for gg   in mTEPES.gg if pRMaxReactivePower  [gg] >  0.0 and pGenToTechnology[gg] == 'SynchronousCondenser'  and pElecGenPeriodIni[gg]  <= mTEPES.p.last() and pElecGenPeriodFin[gg]  >= mTEPES.p.first()])
    mTEPES.sqc    = Set(doc='synchr reactive candidate')
    mTEPES.shc    = Set(doc='shunt           candidate')
    if pIndHydroTopology == 1:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[rs     for rs   in mTEPES.rs   if pRsrInvestCost      [rs] >  0.0 and                                                     pRsrPeriodIni[rs]    <= mTEPES.p.last() and pRsrPeriodFin[rs]      >= mTEPES.p.first()])
    else:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[]                      )
    if pIndHydrogen      == 1:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=dfNetworkHydrogen.index                                   )
        if len(mTEPES.pn) != len(dfNetworkHydrogen.index):
            raise ValueError('### Some hydrogen pipes are invalid ', len(mTEPES.pn), len(dfNetworkHydrogen.index))
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[pn     for pn   in mTEPES.pn   if pH2PipeNTCFrw       [pn] >  0.0 and pH2PipeNTCBck[pn] > 0.0 and                         pH2PipePeriodIni[pn] <= mTEPES.p.last() and pH2PipePeriodFin[pn]   >= mTEPES.p.first()])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[pa     for pa   in mTEPES.pa   if pH2PipeFixedCost    [pa] >  0.0])
        # existing hydrogen pipelines (pe)
        mTEPES.pe = mTEPES.pa - mTEPES.pc
    else:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=[])
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[])

    if pIndHeat        == 1:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=dfNetworkHeat.index)
        if len(mTEPES.hn) != len(dfNetworkHeat.index):
            raise ValueError('### Some heat pipes are invalid ', len(mTEPES.hn), len(dfNetworkHeat.index))
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[hn     for hn   in mTEPES.hn   if pHeatPipeNTCFrw     [hn] >  0.0 and pHeatPipeNTCBck[hn] > 0.0 and pHeatPipePeriodIni[hn] <= mTEPES.p.last() and pHeatPipePeriodFin[hn] >= mTEPES.p.first()])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[ha     for ha   in mTEPES.ha   if pHeatPipeFixedCost  [ha] >  0.0])
        # existing heat pipes (he)
        mTEPES.he = mTEPES.ha - mTEPES.hc
    else:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=[])
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[])

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
    pStageToLevel = pLevelToStage.reset_index().set_index(['Period','Scenario','Stage'])['LoadLevel']
    #Filter only valid indices
    pStageToLevel = pStageToLevel.loc[
        pStageToLevel.index.isin([(p, s, st) for (p, s) in mTEPES.ps for st in mTEPES.st]) &
        pStageToLevel.isin(mTEPES.n)
        ]
    #Reorder the elements
    pStageToLevel = [(p,sc,st,n) for (p,sc,st),n in pStageToLevel.items()]
    mTEPES.s2n = Set(initialize=pStageToLevel, doc='Load level to stage')
    # all the stages must have the same duration
    pStageDuration = pd.Series([sum(pDuration[p,sc,n] for p,sc,st2,n in mTEPES.s2n if st2 == st) for st in mTEPES.st], index=mTEPES.st)
    # for st in mTEPES.st:
    #     if mTEPES.st.ord(st) > 1 and pStageDuration[st] != pStageDuration[mTEPES.st.prev(st)]:
    #         assert (0 == 1)

    # delete all the load level belonging to stages with duration equal to zero
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.n  = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(pDuration[p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(pDuration[p,sc,nn] for p,sc in mTEPES.ps) > 0])
    # instrumental sets
    def CreateInstrumentalSets(mTEPES, pIndHydroTopology, pIndHydrogen, pIndHeat) -> None:
        '''
                Create mTEPES instrumental sets.

                This function takes a mTEPES instance and adds instrumental sets which will be used later.

                Parameters:
                    mTEPES: The instance of mTEPES.

                Returns:
                    None: Sets are added directly to the mTEPES object.
                '''
        mTEPES.pg        = Set(initialize = [(p,     g       ) for p,     g        in mTEPES.p  *mTEPES.g   if pElecGenPeriodIni[g ] <= p and pElecGenPeriodFin[g ] >= p])
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
        mTEPES.par       = Set(initialize = [(p,     ar      ) for p,     ar       in mTEPES.p  *mTEPES.ar                                                                                   ])
        mTEPES.pla       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.la  if pElecNetPeriodIni[ni,nf,cc] <= p and pElecNetPeriodFin[ni,nf,cc] >= p])
        mTEPES.plc       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.lc  if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.pll       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ll  if (p,ni,nf,cc) in mTEPES.pla])

        mTEPES.psc       = Set(initialize = [(p,sc     )       for p,sc            in mTEPES.p  *mTEPES.sc])
        mTEPES.psg       = Set(initialize = [(p,sc,  g )       for p,sc,  g        in mTEPES.ps *mTEPES.g   if (p,g )  in mTEPES.pg  ])
        mTEPES.psnr      = Set(initialize = [(p,sc,  nr)       for p,sc,  nr       in mTEPES.ps *mTEPES.nr  if (p,nr)  in mTEPES.pnr ])
        mTEPES.pses      = Set(initialize = [(p,sc,  es)       for p,sc,  es       in mTEPES.ps *mTEPES.es  if (p,es)  in mTEPES.pes ])
        mTEPES.pseh      = Set(initialize = [(p,sc,  eh)       for p,sc,  eh       in mTEPES.ps *mTEPES.eh  if (p,eh)  in mTEPES.peh ])
        mTEPES.psn       = Set(initialize = [(p,sc,n   )       for p,sc,n          in mTEPES.ps *mTEPES.n                            ])
        mTEPES.psng      = Set(initialize = [(p,sc,n,g )       for p,sc,n,g        in mTEPES.psn*mTEPES.g   if (p,g )  in mTEPES.pg  ])
        for p,sc,n,g in mTEPES.psng:
            print(p,sc,n,g)
        mTEPES.psngc     = Set(initialize = [(p,sc,n,gc)       for p,sc,n,gc       in mTEPES.psn*mTEPES.gc  if (p,gc)  in mTEPES.pgc ])
        mTEPES.psngb     = Set(initialize = [(p,sc,n,gb)       for p,sc,n,gb       in mTEPES.psn*mTEPES.gb  if (p,gb)  in mTEPES.pgc ])
        mTEPES.psnre     = Set(initialize = [(p,sc,n,re)       for p,sc,n,re       in mTEPES.psn*mTEPES.re  if (p,re)  in mTEPES.pre ])
        mTEPES.psnnr     = Set(initialize = [(p,sc,n,nr)       for p,sc,n,nr       in mTEPES.psn*mTEPES.nr  if (p,nr)  in mTEPES.pnr ])
        mTEPES.psnch     = Set(initialize = [(p,sc,n,ch)       for p,sc,n,ch       in mTEPES.psn*mTEPES.ch  if (p,ch)  in mTEPES.pch ])
        mTEPES.psnchp    = Set(initialize = [(p,sc,n,chp)      for p,sc,n,chp      in mTEPES.psn*mTEPES.chp if (p,chp) in mTEPES.pchp])
        mTEPES.psnbo     = Set(initialize = [(p,sc,n,bo)       for p,sc,n,bo       in mTEPES.psn*mTEPES.bo  if (p,bo)  in mTEPES.pbo ])
        mTEPES.psnhp     = Set(initialize = [(p,sc,n,hp)       for p,sc,n,hp       in mTEPES.psn*mTEPES.hp  if (p,hp)  in mTEPES.php ])
        mTEPES.psnes     = Set(initialize = [(p,sc,n,es)       for p,sc,n,es       in mTEPES.psn*mTEPES.es  if (p,es)  in mTEPES.pes ])
        mTEPES.psneh     = Set(initialize = [(p,sc,n,eh)       for p,sc,n,eh       in mTEPES.psn*mTEPES.eh  if (p,eh)  in mTEPES.peh ])
        mTEPES.psnec     = Set(initialize = [(p,sc,n,ec)       for p,sc,n,ec       in mTEPES.psn*mTEPES.ec  if (p,ec)  in mTEPES.pec ])
        mTEPES.psnnd     = Set(initialize = [(p,sc,n,nd)       for p,sc,n,nd       in mTEPES.psn*mTEPES.nd                           ])
        mTEPES.psnar     = Set(initialize = [(p,sc,n,ar)       for p,sc,n,ar       in mTEPES.psn*mTEPES.ar                           ])

        mTEPES.psnla     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.la if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.psnle     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.le if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.psnll     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ll if (p,ni,nf,cc) in mTEPES.pll])
        mTEPES.psnls     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ls if (p,ni,nf,cc) in mTEPES.pla])

        if pIndHydroTopology == 1:
            mTEPES.prs   = Set(initialize = [(p,     rs)       for p,     rs       in mTEPES.p  *mTEPES.rs if pRsrPeriodIni[rs] <= p and pRsrPeriodFin[rs] >= p])
            mTEPES.prc   = Set(initialize = [(p,     rc)       for p,     rc       in mTEPES.p  *mTEPES.rn if (p,rc) in mTEPES.prs])
            mTEPES.psrs  = Set(initialize = [(p,sc,  rs)       for p,sc,  rs       in mTEPES.ps *mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnh  = Set(initialize = [(p,sc,n,h )       for p,sc,n,h        in mTEPES.psn*mTEPES.h  if (p,h ) in mTEPES.ph ])
            mTEPES.psnrs = Set(initialize = [(p,sc,n,rs)       for p,sc,n,rs       in mTEPES.psn*mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnrc = Set(initialize = [(p,sc,n,rc)       for p,sc,n,rc       in mTEPES.psn*mTEPES.rn if (p,rc) in mTEPES.prc])
        else:
            mTEPES.prc   = []

        if pIndHydrogen == 1:
            mTEPES.ppa   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pa if pH2PipePeriodIni[ni,nf,cc] <= p and pH2PipePeriodFin[ni,nf,cc] >= p])
            mTEPES.ppc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pn if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpa = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pa if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pe if (p,ni,nf,cc) in mTEPES.ppa])
        else:
            mTEPES.ppc   = Set(initialize = [])

        if pIndHeat == 1:
            mTEPES.pha   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ha if pHeatPipePeriodIni[ni,nf,cc] <= p and pHeatPipePeriodFin[ni,nf,cc] >= p])
            mTEPES.phc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.hc if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.hn if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnha = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ha if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.he if (p,ni,nf,cc) in mTEPES.pha])
        else:
            mTEPES.phc   = Set(initialize = [])

        # assigning a node to an area
        mTEPES.ndar = Set(initialize = [(nd,ar) for (nd,zn,ar) in mTEPES.ndzn*mTEPES.ar if (zn,ar) in mTEPES.znar])

        # assigning a line to an area. Both nodes are in the same area. Cross-area lines not included
        mTEPES.laar = Set(initialize = [(ni,nf,cc,ar) for ni,nf,cc,ar in mTEPES.la*mTEPES.ar if (ni,ar) in mTEPES.ndar and (nf,ar) in mTEPES.ndar])


    CreateInstrumentalSets(mTEPES, pIndHydroTopology, pIndHydrogen, pIndHeat)

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
    pIndOutflowIncomp         = pIndOutflowIncomp.map    (idxDict)
    pMustRun                  = pMustRun.map             (idxDict)

    if pIndHydroTopology == 1:
        pIndBinRsrvInvest     = pIndBinRsrvInvest.map    (idxDict)

    if pIndHydrogen == 1:
        pIndBinH2PipeInvest   = pIndBinH2PipeInvest.map  (idxDict)

    if pIndHeat == 1:
        pIndBinHeatPipeInvest = pIndBinHeatPipeInvest.map(idxDict)

    # define AC existing  lines     non-switchable lines
    mTEPES.lea = Set(doc='AC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  pIndBinLineSwitch[le] == 0                             and not pLineType[le] == 'DC'])
    # define AC candidate lines and     switchable lines
    mTEPES.lca = Set(doc='AC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (pIndBinLineSwitch[la] == 1 or pNetFixedCost[la] > 0.0) and not pLineType[la] == 'DC'])

    mTEPES.laa = mTEPES.lea | mTEPES.lca

    # define DC existing  lines     non-switchable lines
    mTEPES.led = Set(doc='DC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  pIndBinLineSwitch[le] == 0                             and     pLineType[le] == 'DC'])
    # define DC candidate lines and     switchable lines
    mTEPES.lcd = Set(doc='DC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (pIndBinLineSwitch[la] == 1 or pNetFixedCost[la] > 0.0) and     pLineType[la] == 'DC'])

    mTEPES.lad = mTEPES.led | mTEPES.lcd

    # line type
    pLineType = pLineType.reset_index().set_index(['InitialNode', 'FinalNode', 'Circuit', 'LineType'])

    mTEPES.pLineType = Set(initialize=pLineType.index, doc='line type')

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

    mTEPES.n2g = Set(initialize=pNodeToGen.index, doc='node   to generator')

    mTEPES.z2g = Set(doc='zone   to generator', initialize=[(zn,g) for (nd,g,zn      ) in mTEPES.n2g*mTEPES.zn             if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.a2g = Set(doc='area   to generator', initialize=[(ar,g) for (nd,g,zn,ar   ) in mTEPES.n2g*mTEPES.znar           if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.r2g = Set(doc='region to generator', initialize=[(rg,g) for (nd,g,zn,ar,rg) in mTEPES.n2g*mTEPES.znar*mTEPES.rg if (nd,zn) in mTEPES.ndzn and [ar,rg] in mTEPES.arrg])

    # mTEPES.z2g  = Set(initialize = [(zn,g) for zn,g in mTEPES.zn*mTEPES.g if (zn,g) in pZone2Gen])

    #%% inverse index generator to technology
    pTechnologyToGen = pGenToTechnology.reset_index().set_index('Technology').set_axis(['Generator'], axis=1)[['Generator']]
    pTechnologyToGen = pTechnologyToGen.loc[pTechnologyToGen['Generator'].isin(mTEPES.g)].reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=pTechnologyToGen.index, doc='technology to generator')

    # ESS and RES technologies
    def Create_ESS_RES_Sets(mTEPES) -> None:
        mTEPES.ot = Set(doc='ESS         technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for es in mTEPES.es if (gt,es) in mTEPES.t2g)])
        mTEPES.ht = Set(doc='hydro       technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for h  in mTEPES.h  if (gt,h ) in mTEPES.t2g)])
        mTEPES.et = Set(doc='ESS & hydro technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for eh in mTEPES.eh if (gt,eh) in mTEPES.t2g)])
        mTEPES.rt = Set(doc='    RES     technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for re in mTEPES.re if (gt,re) in mTEPES.t2g)])
        mTEPES.nt = Set(doc='non-RES     technologies', initialize=[gt for gt in mTEPES.gt if sum(1 for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g)])

        mTEPES.psgt  = Set(initialize=[(p,sc,  gt) for p,sc,  gt in mTEPES.ps *mTEPES.gt if sum(1 for g  in mTEPES.g  if (p,g ) in mTEPES.pg  and (gt,g ) in mTEPES.t2g)])
        mTEPES.psot  = Set(initialize=[(p,sc,  ot) for p,sc,  ot in mTEPES.ps *mTEPES.ot if sum(1 for es in mTEPES.es if (p,es) in mTEPES.pes and (ot,es) in mTEPES.t2g)])
        mTEPES.psht  = Set(initialize=[(p,sc,  ht) for p,sc,  ht in mTEPES.ps *mTEPES.ht if sum(1 for h  in mTEPES.h  if (p,h ) in mTEPES.ph  and (ht,h ) in mTEPES.t2g)])
        mTEPES.pset  = Set(initialize=[(p,sc,  et) for p,sc,  et in mTEPES.ps *mTEPES.et if sum(1 for eh in mTEPES.eh if (p,eh) in mTEPES.peh and (et,eh) in mTEPES.t2g)])
        mTEPES.psrt  = Set(initialize=[(p,sc,  rt) for p,sc,  rt in mTEPES.ps *mTEPES.rt if sum(1 for re in mTEPES.re if (p,re) in mTEPES.pre and (rt,re) in mTEPES.t2g)])
        mTEPES.psnt  = Set(initialize=[(p,sc,  nt) for p,sc,  nt in mTEPES.ps *mTEPES.nt if sum(1 for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and (nt,nr) in mTEPES.t2g)])
        mTEPES.psngt = Set(initialize=[(p,sc,n,gt) for p,sc,n,gt in mTEPES.psn*mTEPES.gt if (p,sc,gt) in mTEPES.psgt])
        mTEPES.psnot = Set(initialize=[(p,sc,n,ot) for p,sc,n,ot in mTEPES.psn*mTEPES.ot if (p,sc,ot) in mTEPES.psot])
        mTEPES.psnht = Set(initialize=[(p,sc,n,ht) for p,sc,n,ht in mTEPES.psn*mTEPES.ht if (p,sc,ht) in mTEPES.psht])
        mTEPES.psnet = Set(initialize=[(p,sc,n,et) for p,sc,n,et in mTEPES.psn*mTEPES.et if (p,sc,et) in mTEPES.pset])
        mTEPES.psnrt = Set(initialize=[(p,sc,n,rt) for p,sc,n,rt in mTEPES.psn*mTEPES.rt if (p,sc,rt) in mTEPES.psrt])
        mTEPES.psnnt = Set(initialize=[(p,sc,n,nt) for p,sc,n,nt in mTEPES.psn*mTEPES.nt if (p,sc,nt) in mTEPES.psnt])

    Create_ESS_RES_Sets(mTEPES)

    #%% inverse index generator to mutually exclusive generator
    pExclusiveGenToGen = pGenToExclusiveGen.reset_index().set_index('MutuallyExclusive').set_axis(['Generator'], axis=1)[['Generator']]
    pExclusiveGenToGen = pExclusiveGenToGen.loc[pExclusiveGenToGen['Generator'].isin(mTEPES.g)].reset_index().set_index(['MutuallyExclusive', 'Generator'])

    mTEPES.g2g = Set(doc='mutually exclusive generator to generator', initialize=[(gg,g) for gg,g in mTEPES.g*mTEPES.g if (gg,g) in pExclusiveGenToGen])

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
    idxOutflows['Hourly' ] = 1
    idxOutflows['Daily'  ] = round(  24/pTimeStep)
    idxOutflows['Weekly' ] = round( 168/pTimeStep)
    idxOutflows['Monthly'] = round( 672/pTimeStep)
    idxOutflows['Yearly' ] = round(8736/pTimeStep)

    idxEnergy            = dict()
    idxEnergy[0        ] = 8736
    idxEnergy[0.0      ] = 8736
    idxEnergy['Hourly' ] = 1
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
        idxWaterOut['Hourly' ] = 1
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
    pIniInventory  = pd.DataFrame([pInitialInventory]*len(mTEPES.psn), index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.es)
    if pIndHydroTopology == 1:
        pIniVolume = pd.DataFrame([pInitialVolume   ]*len(mTEPES.psn), index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.rs)

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
    pDemandHeatPeak          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    for p,ar in mTEPES.par:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        pDemandElecPeak[p,ar] = pDemandElec.loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
        pEpsilonElec          = pDemandElecPeak[p,ar]*1e-5

        # these parameters are in GW
        pDemandElecPos     [pDemandElecPos [[nd for nd in d2a[ar]]] <  pEpsilonElec] = 0.0
        pDemandElecNeg     [pDemandElecNeg [[nd for nd in d2a[ar]]] > -pEpsilonElec] = 0.0
        pSystemInertia     [pSystemInertia [[                 ar ]] <  pEpsilonElec] = 0.0
        pOperReserveUp     [pOperReserveUp [[                 ar ]] <  pEpsilonElec] = 0.0
        pOperReserveDw     [pOperReserveDw [[                 ar ]] <  pEpsilonElec] = 0.0

        if len(g2a[ar]):
            pMinPowerElec  [pMinPowerElec  [[g  for  g in g2a[ar]]] <  pEpsilonElec] = 0.0
            pMaxPowerElec  [pMaxPowerElec  [[g  for  g in g2a[ar]]] <  pEpsilonElec] = 0.0
            pMinCharge     [pMinCharge     [[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0
            pMaxCharge     [pMaxCharge     [[eh for eh in g2a[ar]]] <  pEpsilonElec] = 0.0
            pEnergyInflows [pEnergyInflows [[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0
            pEnergyOutflows[pEnergyOutflows[[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0
            # these parameters are in GWh
            pMinStorage    [pMinStorage    [[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0
            pMaxStorage    [pMaxStorage    [[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0
            pIniInventory  [pIniInventory  [[es for es in e2a[ar]]] <  pEpsilonElec] = 0.0

        # pInitialInventory.update(pd.Series([0.0 for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], index=[es for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], dtype='float64'))

        # merging positive and negative values of the demand
        pDemandElec        = pDemandElecPos.where(pDemandElecNeg >= 0.0, pDemandElecNeg)

        # Increase Maximum to reach minimum
        # pMaxPowerElec      = pMaxPowerElec.where(pMaxPowerElec >= pMinPowerElec, pMinPowerElec)
        # pMaxCharge         = pMaxCharge.where   (pMaxCharge    >= pMinCharge,    pMinCharge   )

        # Decrease Minimum to reach maximum
        pMinPowerElec      = pMinPowerElec.where(pMinPowerElec <= pMaxPowerElec, pMaxPowerElec)
        pMinCharge         = pMinCharge.where   (pMinCharge    <= pMaxCharge,    pMaxCharge   )

        #Calculate 2nd Blocks
        pMaxPower2ndBlock  = pMaxPowerElec - pMinPowerElec
        pMaxCharge2ndBlock = pMaxCharge    - pMinCharge

        pMaxCapacity       = pMaxPowerElec.where(pMaxPowerElec > pMaxCharge, pMaxCharge)

        if len(g2a[ar]):
            pMaxPower2ndBlock [pMaxPower2ndBlock [[g for g in g2a[ar]]] < pEpsilonElec] = 0.0
            pMaxCharge2ndBlock[pMaxCharge2ndBlock[[g for g in g2a[ar]]] < pEpsilonElec] = 0.0

        pLineNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilonElec], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCFrw[ni,nf,cc] < pEpsilonElec], dtype='float64'))
        pLineNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilonElec], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.la if pLineNTCBck[ni,nf,cc] < pEpsilonElec], dtype='float64'))
        pLineNTCMax = pLineNTCFrw.where(pLineNTCFrw > pLineNTCBck, pLineNTCBck)

        if pIndHydrogen == 1:
            pDemandH2[pDemandH2[[nd for nd in d2a[ar]]] < pEpsilonElec] = 0.0
            pH2PipeNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.pa if pH2PipeNTCFrw[ni,nf,cc] < pEpsilonElec], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.pa if pH2PipeNTCFrw[ni,nf,cc] < pEpsilonElec], dtype='float64'))
            pH2PipeNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.pa if pH2PipeNTCBck[ni,nf,cc] < pEpsilonElec], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.pa if pH2PipeNTCBck[ni,nf,cc] < pEpsilonElec], dtype='float64'))

        if pIndHeat == 1:
            pDemandHeatPeak[p,ar] = pDemandHeat.loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
            pEpsilonHeat          = pDemandHeatPeak[p,ar]*1e-5
            pDemandHeat             [pDemandHeat    [[nd for nd in   d2a[ar]]] <  pEpsilonHeat] = 0.0
            pHeatPipeNTCFrw.update(pd.Series([0.0 for ni,nf,cc in mTEPES.ha if pHeatPipeNTCFrw[ni,nf,cc] < pEpsilonHeat], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.ha if pHeatPipeNTCFrw[ni,nf,cc] < pEpsilonHeat], dtype='float64'))
            pHeatPipeNTCBck.update(pd.Series([0.0 for ni,nf,cc in mTEPES.ha if pHeatPipeNTCBck[ni,nf,cc] < pEpsilonHeat], index=[(ni,nf,cc) for ni,nf,cc in mTEPES.ha if pHeatPipeNTCBck[ni,nf,cc] < pEpsilonHeat], dtype='float64'))

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
    pEpsilon = 1e-6
    pMaxPower2ndBlock  = pMaxPower2ndBlock.where (pMaxPower2ndBlock  > pEpsilon, 0.0)
    pMaxCharge2ndBlock = pMaxCharge2ndBlock.where(pMaxCharge2ndBlock > pEpsilon, 0.0)

    # computation of the power to heat ratio of the CHP units
    # heat ratio of boiler units is fixed to 1.0
    pPower2HeatRatio   = pd.Series([1.0 if ch in mTEPES.bo else (pRatedMaxPowerElec[ch]-pRatedMinPowerElec[ch])/(pRatedMaxPowerHeat[ch]-pRatedMinPowerHeat[ch]) for ch in mTEPES.ch], index=mTEPES.ch)
    pMinPowerHeat      = pd.DataFrame([[pMinPowerElec     [ch][p,sc,n]/pPower2HeatRatio[ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.ch)
    pMaxPowerHeat      = pd.DataFrame([[pMaxPowerElec     [ch][p,sc,n]/pPower2HeatRatio[ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.ch)
    pMinPowerHeat.update(pd.DataFrame([[pRatedMinPowerHeat[bo]                              for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.bo))
    pMaxPowerHeat.update(pd.DataFrame([[pRatedMaxPowerHeat[bo]                              for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.bo))
    pMaxPowerHeat.update(pd.DataFrame([[pMaxCharge[hp][p,sc,n]/pProductionFunctionHeat[hp]  for hp in mTEPES.hp] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.hp))

    # drop values not par, p, or ps
    pReserveMargin  = pReserveMargin.loc [mTEPES.par]
    pEmission       = pEmission.loc      [mTEPES.par]
    pRESEnergy      = pRESEnergy.loc     [mTEPES.par]
    pDemandElecPeak = pDemandElecPeak.loc[mTEPES.par]
    pDemandHeatPeak = pDemandHeatPeak.loc[mTEPES.par]
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
        pMaxOutflows = pd.DataFrame([[sum(pMaxPowerElec[h][p,sc,n]/pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) for rs in mTEPES.rs] for p,sc,n in mTEPES.psn], index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=mTEPES.rs)

    if pIndHydrogen == 1:
        # drop generators not el
        pProductionFunctionH2 = pProductionFunctionH2.loc[mTEPES.el]
        # drop pipelines not pc
        pH2PipeFixedCost      = pH2PipeFixedCost.loc     [mTEPES.pc]
        pH2PipeLoInvest       = pH2PipeLoInvest.loc      [mTEPES.pc]
        pH2PipeUpInvest       = pH2PipeUpInvest.loc      [mTEPES.pc]

    if pIndHeat == 1:
        pReserveMarginHeat          = pReserveMarginHeat.loc         [mTEPES.par]
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

    # this rated linear variable cost is going to be used to order the generating units
    # we include a small term to avoid a stochastic behavior due to equal values
    for g in mTEPES.g:
        pRatedLinearVarCost[g] += 1e-3*pEpsilon*mTEPES.g.ord(g)

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

    def filter_rows(df, set):
        df = df.stack(level=list(range(df.columns.nlevels)), future_stack=True)
        df = df[df.index.isin(set)]
        return df

    pMinPowerElec      = filter_rows(pMinPowerElec     , mTEPES.psng )
    pMaxPowerElec      = filter_rows(pMaxPowerElec     , mTEPES.psng )
    pMinCharge         = filter_rows(pMinCharge        , mTEPES.psneh)
    pMaxCharge         = filter_rows(pMaxCharge        , mTEPES.psneh)
    pMaxCapacity       = filter_rows(pMaxCapacity      , mTEPES.psneh)
    pMaxPower2ndBlock  = filter_rows(pMaxPower2ndBlock , mTEPES.psng )
    pMaxCharge2ndBlock = filter_rows(pMaxCharge2ndBlock, mTEPES.psneh)
    pEnergyInflows     = filter_rows(pEnergyInflows    , mTEPES.psnes)
    pEnergyOutflows    = filter_rows(pEnergyOutflows   , mTEPES.psnes)
    pMinStorage        = filter_rows(pMinStorage       , mTEPES.psnes)
    pMaxStorage        = filter_rows(pMaxStorage       , mTEPES.psnes)
    pVariableMaxEnergy = filter_rows(pVariableMaxEnergy, mTEPES.psng )
    pVariableMinEnergy = filter_rows(pVariableMinEnergy, mTEPES.psng )
    pLinearVarCost     = filter_rows(pLinearVarCost    , mTEPES.psng )
    pConstantVarCost   = filter_rows(pConstantVarCost  , mTEPES.psng )
    pEmissionVarCost   = filter_rows(pEmissionVarCost  , mTEPES.psng )
    pIniInventory      = filter_rows(pIniInventory     , mTEPES.psnes)

    pDemandElec        = filter_rows(pDemandElec       , mTEPES.psnnd)
    pDemandElecAbs     = filter_rows(pDemandElecAbs    , mTEPES.psnnd)
    pSystemInertia     = filter_rows(pSystemInertia    , mTEPES.psnar)
    pOperReserveUp     = filter_rows(pOperReserveUp    , mTEPES.psnar)
    pOperReserveDw     = filter_rows(pOperReserveDw    , mTEPES.psnar)

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
    mTEPES.pIndBinGenMinTime     = Param(initialize=pIndBinGenMinTime   , within=Binary,              doc='Indicator of using or not the min up/dw time constraints',  mutable=True)
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
    mTEPES.pDemandElec           = Param(mTEPES.psnnd, initialize=pDemandElec.to_dict()               , within=           Reals,    doc='Electric demand'                                     )
    mTEPES.pDemandElecAbs        = Param(mTEPES.psnnd, initialize=pDemandElecAbs.to_dict()            , within=NonNegativeReals,    doc='Electric demand'                                     )
    mTEPES.pPeriodWeight         = Param(mTEPES.p,     initialize=pPeriodWeight.to_dict()             , within=NonNegativeReals,    doc='Period weight',                          mutable=True)
    mTEPES.pDiscountedWeight     = Param(mTEPES.p,     initialize=pDiscountedWeight.to_dict()         , within=NonNegativeReals,    doc='Discount factor'                                     )
    mTEPES.pScenProb             = Param(mTEPES.psc,   initialize=pScenProb.to_dict()                 , within=UnitInterval    ,    doc='Probability',                            mutable=True)
    mTEPES.pStageWeight          = Param(mTEPES.stt,   initialize=pStageWeight.to_dict()              , within=NonNegativeReals,    doc='Stage weight'                                        )
    mTEPES.pDuration             = Param(mTEPES.psn,   initialize=pDuration.to_dict()                 , within=NonNegativeIntegers, doc='Duration',                               mutable=True)
    mTEPES.pNodeLon              = Param(mTEPES.nd,    initialize=pNodeLon.to_dict()                  ,                             doc='Longitude'                                           )
    mTEPES.pNodeLat              = Param(mTEPES.nd,    initialize=pNodeLat.to_dict()                  ,                             doc='Latitude'                                            )
    mTEPES.pSystemInertia        = Param(mTEPES.psnar, initialize=pSystemInertia.to_dict()            , within=NonNegativeReals,    doc='System inertia'                                      )
    mTEPES.pOperReserveUp        = Param(mTEPES.psnar, initialize=pOperReserveUp.to_dict()            , within=NonNegativeReals,    doc='Upward   operating reserve'                          )
    mTEPES.pOperReserveDw        = Param(mTEPES.psnar, initialize=pOperReserveDw.to_dict()            , within=NonNegativeReals,    doc='Downward operating reserve'                          )
    mTEPES.pMinPowerElec         = Param(mTEPES.psng , initialize=pMinPowerElec.to_dict()             , within=NonNegativeReals,    doc='Minimum electric power'                              )
    mTEPES.pMaxPowerElec         = Param(mTEPES.psng , initialize=pMaxPowerElec.to_dict()             , within=NonNegativeReals,    doc='Maximum electric power'                              )
    mTEPES.pMinCharge            = Param(mTEPES.psneh, initialize=pMinCharge.to_dict()                , within=NonNegativeReals,    doc='Minimum charge'                                      )
    mTEPES.pMaxCharge            = Param(mTEPES.psneh, initialize=pMaxCharge.to_dict()                , within=NonNegativeReals,    doc='Maximum charge'                                      )
    mTEPES.pMaxCapacity          = Param(mTEPES.psneh, initialize=pMaxCapacity.to_dict()              , within=NonNegativeReals,    doc='Maximum capacity'                                    )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.psng , initialize=pMaxPower2ndBlock.to_dict()         , within=NonNegativeReals,    doc='Second block power'                                  )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.psneh, initialize=pMaxCharge2ndBlock.to_dict()        , within=NonNegativeReals,    doc='Second block charge'                                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.psnes, initialize=pEnergyInflows.to_dict()            , within=NonNegativeReals,    doc='Energy inflows',                         mutable=True)
    mTEPES.pEnergyOutflows       = Param(mTEPES.psnes, initialize=pEnergyOutflows.to_dict()           , within=NonNegativeReals,    doc='Energy outflows',                        mutable=True)
    mTEPES.pMinStorage           = Param(mTEPES.psnes, initialize=pMinStorage.to_dict()               , within=NonNegativeReals,    doc='ESS Minimum storage capacity'                        )
    mTEPES.pMaxStorage           = Param(mTEPES.psnes, initialize=pMaxStorage.to_dict()               , within=NonNegativeReals,    doc='ESS Maximum storage capacity'                        )
    mTEPES.pMinEnergy            = Param(mTEPES.psng , initialize=pVariableMinEnergy.to_dict()        , within=NonNegativeReals,    doc='Unit minimum energy demand'                          )
    mTEPES.pMaxEnergy            = Param(mTEPES.psng , initialize=pVariableMaxEnergy.to_dict()        , within=NonNegativeReals,    doc='Unit maximum energy demand'                          )
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
    mTEPES.pLinearVarCost        = Param(mTEPES.psng , initialize=pLinearVarCost.to_dict()            , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pConstantVarCost      = Param(mTEPES.psng , initialize=pConstantVarCost.to_dict()          , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearOMCost         = Param(mTEPES.gg,    initialize=pLinearOMCost.to_dict()             , within=NonNegativeReals,    doc='Linear   O&M      cost'                              )
    mTEPES.pOperReserveCost      = Param(mTEPES.gg,    initialize=pOperReserveCost.to_dict()          , within=NonNegativeReals,    doc='Operating reserve cost'                              )
    mTEPES.pEmissionVarCost      = Param(mTEPES.psng , initialize=pEmissionVarCost.to_dict()          , within=Reals           ,    doc='CO2 Emission      cost'                              )
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
    mTEPES.pIndOutflowIncomp     = Param(mTEPES.gg,    initialize=pIndOutflowIncomp.to_dict()         , within=Binary          ,    doc='Indicator of outflow incompatibility with charging'  )
    mTEPES.pEfficiency           = Param(mTEPES.eh,    initialize=pEfficiency.to_dict()               , within=UnitInterval    ,    doc='Round-trip efficiency'                               )
    mTEPES.pStorageTimeStep      = Param(mTEPES.es,    initialize=pStorageTimeStep.to_dict()          , within=PositiveIntegers,    doc='ESS Storage cycle'                                   )
    mTEPES.pOutflowsTimeStep     = Param(mTEPES.es,    initialize=pOutflowsTimeStep.to_dict()         , within=PositiveIntegers,    doc='ESS Outflows cycle'                                  )
    mTEPES.pEnergyTimeStep       = Param(mTEPES.gg,    initialize=pEnergyTimeStep.to_dict()           , within=PositiveIntegers,    doc='Unit energy cycle'                                   )
    mTEPES.pIniInventory         = Param(mTEPES.psnes, initialize=pIniInventory.to_dict()             , within=NonNegativeReals,    doc='ESS Initial storage',                    mutable=True)
    mTEPES.pStorageType          = Param(mTEPES.es,    initialize=pStorageType.to_dict()              , within=Any             ,    doc='ESS Storage type'                                    )
    mTEPES.pGenLoInvest          = Param(mTEPES.eb,    initialize=pGenLoInvest.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pGenUpInvest          = Param(mTEPES.eb,    initialize=pGenUpInvest.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)
    mTEPES.pGenLoRetire          = Param(mTEPES.gd,    initialize=pGenLoRetire.to_dict()              , within=NonNegativeReals,    doc='Lower bound of the retirement decision', mutable=True)
    mTEPES.pGenUpRetire          = Param(mTEPES.gd,    initialize=pGenUpRetire.to_dict()              , within=NonNegativeReals,    doc='Upper bound of the retirement decision', mutable=True)

    if pIndHydrogen == 1:
        mTEPES.pProductionFunctionH2 = Param(mTEPES.el, initialize=pProductionFunctionH2.to_dict(), within=NonNegativeReals, doc='Production function of an electrolyzer plant')

    if pIndHeat == 1:
        pMinPowerHeat = filter_rows(pMinPowerHeat, mTEPES.psnch)
        pMaxPowerHeat = filter_rows(pMaxPowerHeat, mTEPES.psnch)

        mTEPES.pReserveMarginHeat          = Param(mTEPES.par,   initialize=pReserveMarginHeat.to_dict()         , within=NonNegativeReals, doc='Adequacy reserve margin'                  )
        mTEPES.pRatedMaxPowerHeat          = Param(mTEPES.gg,    initialize=pRatedMaxPowerHeat.to_dict()         , within=NonNegativeReals, doc='Rated maximum heat'                       )
        mTEPES.pMinPowerHeat               = Param(mTEPES.psnch, initialize=pMinPowerHeat.to_dict()              , within=NonNegativeReals, doc='Minimum heat     power'                   )
        mTEPES.pMaxPowerHeat               = Param(mTEPES.psnch, initialize=pMaxPowerHeat.to_dict()              , within=NonNegativeReals, doc='Maximum heat     power'                   )
        mTEPES.pPower2HeatRatio            = Param(mTEPES.ch,    initialize=pPower2HeatRatio.to_dict()           , within=NonNegativeReals, doc='Power to heat ratio'                      )
        mTEPES.pProductionFunctionHeat     = Param(mTEPES.hp,    initialize=pProductionFunctionHeat.to_dict()    , within=NonNegativeReals, doc='Production function of an CHP plant'      )
        mTEPES.pProductionFunctionH2ToHeat = Param(mTEPES.hh,    initialize=pProductionFunctionH2ToHeat.to_dict(), within=NonNegativeReals, doc='Production function of an boiler using H2')

    if pIndHydroTopology == 1:

        pHydroInflows  = filter_rows(pHydroInflows , mTEPES.psnrs)
        pHydroOutflows = filter_rows(pHydroOutflows, mTEPES.psnrs)
        pMaxOutflows   = filter_rows(pMaxOutflows  , mTEPES.psnrs)
        pMinVolume     = filter_rows(pMinVolume    , mTEPES.psnrs)
        pMaxVolume     = filter_rows(pMaxVolume    , mTEPES.psnrs)
        pIniVolume     = filter_rows(pIniVolume    , mTEPES.psnrs)

        mTEPES.pProductionFunctionHydro = Param(mTEPES.h ,    initialize=pProductionFunctionHydro.to_dict(), within=NonNegativeReals, doc='Production function of a hydro power plant'  )
        mTEPES.pHydroInflows            = Param(mTEPES.psnrs, initialize=pHydroInflows.to_dict()           , within=NonNegativeReals, doc='Hydro inflows',                  mutable=True)
        mTEPES.pHydroOutflows           = Param(mTEPES.psnrs, initialize=pHydroOutflows.to_dict()          , within=NonNegativeReals, doc='Hydro outflows',                 mutable=True)
        mTEPES.pMaxOutflows             = Param(mTEPES.psnrs, initialize=pMaxOutflows.to_dict()            , within=NonNegativeReals, doc='Maximum hydro outflows',                     )
        mTEPES.pMinVolume               = Param(mTEPES.psnrs, initialize=pMinVolume.to_dict()              , within=NonNegativeReals, doc='Minimum reservoir volume capacity'           )
        mTEPES.pMaxVolume               = Param(mTEPES.psnrs, initialize=pMaxVolume.to_dict()              , within=NonNegativeReals, doc='Maximum reservoir volume capacity'           )
        mTEPES.pIndBinRsrvInvest        = Param(mTEPES.rn,    initialize=pIndBinRsrvInvest.to_dict()       , within=Binary          , doc='Binary  reservoir investment decision'       )
        mTEPES.pRsrInvestCost           = Param(mTEPES.rn,    initialize=pRsrInvestCost.to_dict()          , within=NonNegativeReals, doc='Reservoir fixed cost'                        )
        mTEPES.pRsrPeriodIni            = Param(mTEPES.rs,    initialize=pRsrPeriodIni.to_dict()           , within=PositiveIntegers, doc='Installation year',                          )
        mTEPES.pRsrPeriodFin            = Param(mTEPES.rs,    initialize=pRsrPeriodFin.to_dict()           , within=PositiveIntegers, doc='Retirement   year',                          )
        mTEPES.pReservoirTimeStep       = Param(mTEPES.rs,    initialize=pReservoirTimeStep.to_dict()      , within=PositiveIntegers, doc='Reservoir volume cycle'                      )
        mTEPES.pWaterOutTimeStep        = Param(mTEPES.rs,    initialize=pWaterOutTimeStep.to_dict()       , within=PositiveIntegers, doc='Reservoir outflows cycle'                    )
        mTEPES.pIniVolume               = Param(mTEPES.psnrs, initialize=pIniVolume.to_dict()              , within=NonNegativeReals, doc='Reservoir initial volume',       mutable=True)
        mTEPES.pInitialVolume           = Param(mTEPES.rs,    initialize=pInitialVolume.to_dict()          , within=NonNegativeReals, doc='Reservoir initial volume without load levels')
        mTEPES.pReservoirType           = Param(mTEPES.rs,    initialize=pReservoirType.to_dict()          , within=Any             , doc='Reservoir volume type'                       )

    if pIndHydrogen == 1:
        pDemandH2    = filter_rows(pDemandH2   ,mTEPES.psnnd)
        pDemandH2Abs = filter_rows(pDemandH2Abs,mTEPES.psnnd)

        mTEPES.pDemandH2    = Param(mTEPES.psnnd, initialize=pDemandH2.to_dict()   , within=NonNegativeReals,    doc='Hydrogen demand per hour')
        mTEPES.pDemandH2Abs = Param(mTEPES.psnnd, initialize=pDemandH2Abs.to_dict(), within=NonNegativeReals,    doc='Hydrogen demand'         )

    if pIndHeat == 1:
        pDemandHeat     = filter_rows(pDemandHeat    , mTEPES.psnnd)
        pDemandHeatAbs  = filter_rows(pDemandHeatAbs , mTEPES.psnnd)

        mTEPES.pDemandHeatPeak = Param(mTEPES.par,   initialize=pDemandHeatPeak.to_dict(), within=NonNegativeReals,    doc='Peak heat demand'        )
        mTEPES.pDemandHeat     = Param(mTEPES.psnnd, initialize=pDemandHeat.to_dict()   ,  within=NonNegativeReals,    doc='Heat demand per hour'    )
        mTEPES.pDemandHeatAbs  = Param(mTEPES.psnnd, initialize=pDemandHeatAbs.to_dict(),  within=NonNegativeReals,    doc='Heat demand'             )

    mTEPES.pLoadLevelDuration = Param(mTEPES.psn,   initialize=0                        ,  within=NonNegativeIntegers, doc='Load level duration', mutable=True)
    for p,sc,n in mTEPES.psn:
        mTEPES.pLoadLevelDuration[p,sc,n] = mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pDuration[p,sc,n]()

    mTEPES.pPeriodProb         = Param(mTEPES.ps,    initialize=0.0                     ,  within=NonNegativeReals,   doc='Period probability',  mutable=True)
    for p,sc in mTEPES.ps:
        # periods and scenarios are going to be solved together with their weight and probability
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc]

    pMaxTheta = filter_rows(pMaxTheta, mTEPES.psnnd)

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
    mTEPES.pMaxTheta         = Param(mTEPES.psnnd, initialize=pMaxTheta.to_dict()        , within=NonNegativeReals,    doc='Maximum voltage angle',                                mutable=True)
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
    pInitialOutput = pd.DataFrame([[0.0]*len(mTEPES.g )]*len(mTEPES.psn), index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=                           mTEPES.g )
    pInitialUC     = pd.DataFrame([[0  ]*len(mTEPES.g )]*len(mTEPES.psn), index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=                           mTEPES.g )
    pInitialSwitch = pd.DataFrame([[0  ]*len(mTEPES.la)]*len(mTEPES.psn), index=pd.MultiIndex.from_tuples(mTEPES.psn), columns=pd.MultiIndex.from_tuples(mTEPES.la))

    pInitialOutput = filter_rows(pInitialOutput, mTEPES.psng )
    pInitialUC     = filter_rows(pInitialUC    , mTEPES.psng )
    pInitialSwitch = filter_rows(pInitialSwitch, mTEPES.psnla)

    mTEPES.pInitialOutput = Param(mTEPES.psng , initialize=pInitialOutput.to_dict(), within=NonNegativeReals, doc='unit initial output',     mutable=True)
    mTEPES.pInitialUC     = Param(mTEPES.psng , initialize=pInitialUC.to_dict()    , within=Binary,           doc='unit initial commitment', mutable=True)
    mTEPES.pInitialSwitch = Param(mTEPES.psnla, initialize=pInitialSwitch.to_dict(), within=Binary,           doc='line initial switching',  mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')


def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()
    def CreateVariables(mTEPES, OptModel) -> None:
        '''
        Create all mTEPES variables.

        This function takes a mTEPES instance with all parameters and sets created and adds variables to it.

        Parameters:
            mTEPES: The instance of mTEPES.

        Returns:
            None: Variables are added directly to the mTEPES object.
        '''
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

        if mTEPES.pIndBinGenInvest() != 1:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=UnitInterval,                     doc='generation       investment decision exists in a year [0,1]')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=UnitInterval,                     doc='generation       investment decision done   in a year [0,1]')
        else:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=Binary,                           doc='generation       investment decision exists in a year {0,1}')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=Binary,                           doc='generation       investment decision done   in a year {0,1}')

        if mTEPES.pIndBinGenRetire() != 1:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=UnitInterval,                     doc='generation       retirement decision exists in a year [0,1]')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=UnitInterval,                     doc='generation       retirement decision exists in a year [0,1]')
        else:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=Binary,                           doc='generation       retirement decision exists in a year {0,1}')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=Binary,                           doc='generation       retirement decision exists in a year {0,1}')

        if mTEPES.pIndBinNetElecInvest() != 1:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=UnitInterval,                     doc='electric network investment decision exists in a year [0,1]')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=UnitInterval,                     doc='electric network investment decision exists in a year [0,1]')
        else:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=Binary,                           doc='electric network investment decision exists in a year {0,1}')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=Binary,                           doc='electric network investment decision exists in a year {0,1}')

        if mTEPES.pIndHydroTopology == 1:
            if mTEPES.pIndBinRsrInvest() != 1:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=UnitInterval,                     doc='reservoir        investment decision exists in a year [0,1]')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=UnitInterval,                     doc='reservoir        investment decision exists in a year [0,1]')
            else:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=Binary,                           doc='reservoir        investment decision exists in a year {0,1}')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=Binary,                           doc='reservoir        investment decision exists in a year {0,1}')

        if mTEPES.pIndHydrogen == 1:
            if mTEPES.pIndBinNetH2Invest() != 1:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=UnitInterval,                     doc='hydrogen network investment decision exists in a year [0,1]')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=UnitInterval,                     doc='hydrogen network investment decision exists in a year [0,1]')
            else:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=Binary,                           doc='hydrogen network investment decision exists in a year {0,1}')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=Binary,                           doc='hydrogen network investment decision exists in a year {0,1}')

        if mTEPES.pIndHeat == 1:
            if mTEPES.pIndBinGenInvest() != 1:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=UnitInterval,                 doc='generation       investment decision exists in a year [0,1]')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=UnitInterval,                 doc='generation       investment decision done   in a year [0,1]')
            else:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=Binary,                       doc='generation       investment decision exists in a year {0,1}')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=Binary,                       doc='generation       investment decision done   in a year {0,1}')
            if mTEPES.pIndBinNetHeatInvest() != 1:
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
            OptModel.vStableState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='stable   state     of the unit                        [0,1]')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp up   state    of the unit                        [0,1]')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp down state    of the unit                        [0,1]')
        else:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='commitment         of the unit                        {0,1}')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='startup            of the unit                        {0,1}')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='shutdown           of the unit                        {0,1}')
            OptModel.vMaxCommitment        = Var(mTEPES.psnr , within=Binary,           initialize=0  , doc='maximum commitment of the unit                        {0,1}')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='stable   state     of the unit                        {0,1}')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp up   state    of the unit                        {0,1}')
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

    CreateVariables(mTEPES, mTEPES)
    # assign lower and upper bounds to variables
    def setVariableBounds(mTEPES, OptModel) -> None:
        '''
        Set upper/lower bounds.

        This function takes a mTEPES instance and adds lower/upper bounds to variables which are limited by a parameter.

        Parameters:
            mTEPES: The instance of mTEPES

        Returns:
            None: Changes are performed directly on the model
        '''

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

        [OptModel.vESSTotalCharge[p,sc,n,eh].setub(mTEPES.pMaxCharge        [p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vCharge2ndBlock[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveUp  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveDown[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vENS           [p,sc,n,nd].setub(mTEPES.pDemandElecAbs    [p,sc,n,nd]  ) for p,sc,n,nd in mTEPES.psnnd]

        if mTEPES.pIndHydroTopology == 1:
            [OptModel.vHydroInflows   [p,sc,n,rc].setub(mTEPES.pHydroInflows[p,sc,n,rc]()) for p,sc,n,rc in mTEPES.psnrc]
            [OptModel.vHydroOutflows  [p,sc,n,rs].setub(mTEPES.pMaxOutflows [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setlb(mTEPES.pMinVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setub(mTEPES.pMaxVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]

    setVariableBounds(mTEPES, mTEPES)

    nFixedVariables = 0
    def RelaxBinaryInvestmentConditions(mTEPES, OptModel) -> int:
        '''
        Relax binary investent variables.

        This function takes a mTEPES instance relaxes binary investment conditions and calculates the amount of variables fixed in the process.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The amount of fixed variables.
        '''

        nFixedBinaries = 0

        # relax binary condition in generation, boiler, and electric network investment decisions
        for p,eb in mTEPES.peb:
            if mTEPES.pIndBinGenInvest() != 0 and mTEPES.pIndBinUnitInvest[eb] == 0:
                OptModel.vGenerationInvest    [p,eb      ].domain = UnitInterval
            if mTEPES.pIndBinGenInvest() == 2:
                OptModel.vGenerationInvest    [p,eb      ].fix(0)
                nFixedBinaries += 1

        for p,ni,nf,cc in mTEPES.plc:
            if mTEPES.pIndBinNetElecInvest() != 0 and mTEPES.pIndBinLineInvest[ni,nf,cc] == 0:
                OptModel.vNetworkInvest       [p,ni,nf,cc].domain = UnitInterval
            if mTEPES.pIndBinNetElecInvest() == 2:
                OptModel.vNetworkInvest       [p,ni,nf,cc].fix(0)
                nFixedBinaries += 1

        # relax binary condition in generation retirement decisions
        for p,gd in mTEPES.pgd:
            if mTEPES.pIndBinGenRetire() != 0 and mTEPES.pIndBinUnitRetire[gd] == 0:
                OptModel.vGenerationRetire    [p,gd      ].domain = UnitInterval
            if mTEPES.pIndBinGenRetire() == 2:
                OptModel.vGenerationRetire    [p,gd      ].fix(0)
                nFixedBinaries += 1

        # relax binary condition in reservoir investment decisions
        if mTEPES.pIndHydroTopology == 1:
            for p,rc in mTEPES.prc:
                if mTEPES.pIndBinRsrInvest() != 0 and mTEPES.pIndBinRsrvInvest[rc] == 0:
                    OptModel.vReservoirInvest [p,rc      ].domain = UnitInterval
                if mTEPES.pIndBinRsrInvest() == 2:
                    OptModel.vReservoirInvest [p,rc      ].fix(0)
                    nFixedBinaries += 1

        # relax binary condition in hydrogen network investment decisions
        if mTEPES.pIndHydrogen == 1:
            for p,ni,nf,cc in mTEPES.ppc:
                if mTEPES.pIndBinNetH2Invest() != 0 and mTEPES.pIndBinH2PipeInvest[ni,nf,cc] == 0:
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetH2Invest() == 2:
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedBinaries += 1

        if mTEPES.pIndHeat == 1:
            # relax binary condition in heat network investment decisions
            for p,ni,nf,cc in mTEPES.phc:
                if mTEPES.pIndBinNetHeatInvest() != 0 and mTEPES.pIndBinHeatPipeInvest[ni,nf,cc] == 0:
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetHeatInvest() == 2:
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedBinaries += 1

        # relax binary condition in unit generation, startup and shutdown decisions
        for p,sc,n,nr in mTEPES.psnnr:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vCommitment   [p,sc,n,nr].domain = UnitInterval
                OptModel.vStartUp      [p,sc,n,nr].domain = UnitInterval
                OptModel.vShutDown     [p,sc,n,nr].domain = UnitInterval

        for p,sc,  nr in mTEPES.psnr:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vMaxCommitment[p,sc,  nr].domain = UnitInterval
        return nFixedBinaries

    #Call the relaxing variables function and add its output to nFixedVariables
    nFixedBinaries = RelaxBinaryInvestmentConditions(mTEPES, mTEPES)
    nFixedVariables += nFixedBinaries

    def CreateFlowVariables(mTEPES,OptModel) -> int:
        #TODO use a more descriptive name for nFixedVariables
        '''
                Create electricity, hydrogen and heat flow related variables.

                This function takes a mTEPES instance and adds the variables necessary to model power, hydrogen and heat flows in a network.

                Parameters:
                    mTEPES: The instance of mTEPES.
                    OptModel:

                Returns:
                    int: The amount of line commitment variables fixed
                '''
        nFixedVariables = 0
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
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setlb(-mTEPES.pHeatPipeNTCBck[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setub( mTEPES.pHeatPipeNTCFrw[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vHeatNS  [p,sc,n,nd      ].setub( mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandHeatAbs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]
        return nFixedVariables

    nFixedLineCommitments = CreateFlowVariables(mTEPES, mTEPES)
    nFixedVariables += nFixedLineCommitments

    def FixGeneratorsCommitment(mTEPES, OptModel) -> int:
        '''
            Fix commitment variables.

            This function takes a mTEPES instance and fixes commitment related variables for must run units, ESS units and units with no minimum power.

            Parameters:
                mTEPES: The instance of mTEPES.
                OptModel:

            Returns:
                int: The amount of commitment variables fixed.
            '''
        nFixedVariables = 0

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
        pStorageTotalEnergyInflows = pd.Series([sum(mTEPES.pEnergyInflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,sc,n,es) in mTEPES.psnes) for es in mTEPES.es], index=mTEPES.es)

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
        return nFixedVariables
    nFixedGeneratorCommits = FixGeneratorsCommitment(mTEPES,mTEPES)
    nFixedVariables += nFixedGeneratorCommits
    # thermal and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if len(mTEPES.tq):
        mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.sq])
    else:
        mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.eh])

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt and mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                      (p,sc,st,nn) in mTEPES.s2n ])

        if len(mTEPES.n):
            mTEPES.psn1 = Set(initialize=[(p,sc,n) for p,sc,n in mTEPES.ps*mTEPES.n])
            # determine the first load level of each stage
            n1 = next(iter(mTEPES.psn1))
            # commit the units and their output at the first load level of each stage
            pSystemOutput = 0.0
            for nr in mTEPES.nr:
                if pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[nr] == 1:
                    mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPowerElec[n1,nr]
                    mTEPES.pInitialUC    [n1,nr] = 1
                    pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()
            mTEPES.del_component(mTEPES.psn1)

            # determine the initial committed units and their output at the first load level of each period, scenario, and stage
            for go in mTEPES.go:
                if pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd) and mTEPES.pMustRun[go] == 0:
                    if (n1,go) in mTEPES.psng:
                        if go in mTEPES.re:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPowerElec[n1,go]
                        else:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPowerElec[n1,go]
                        mTEPES.pInitialUC[n1,go] = 1
                        pSystemOutput           += mTEPES.pInitialOutput[n1,go]()

            # determine the initial committed lines
            for la in mTEPES.la:
                if (n1,la) in mTEPES.psnla:
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
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                    (p,sc,stt,nn) in mTEPES.s2n)])
    mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for st in mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

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
        if sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
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
            OptModel.vENS    [p,sc,n,nd].fix(0.0)
            nFixedVariables += 1

    if mTEPES.pIndHydrogen == 1:
        # fixing the H2 ENS in nodes with no hydrogen demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandH2[p,sc,n,nd] ==   0.0:
                OptModel.vH2NS [p,sc,n,nd].fix (0.0)
                nFixedVariables += 1

    if mTEPES.pIndHeat == 1:
        # fixing the heat ENS in nodes with no heat demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandHeat[p,sc,n,nd] ==   0.0:
                OptModel.vHeatNS [p,sc,n,nd].fix (0.0)
                nFixedVariables += 1

    def AvoidForbiddenInstallationsAndRetirements(mTEPES, OptModel) -> int:
        '''
        Fix installations/retirements forbidden by period.

        This function takes a mTEPES instance and fixes all installation and retirement variables to 0 if they are not allowed in the corresponding period.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The amount of variables fixed.
        '''
        nFixedVariables = 0
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
        return nFixedVariables

    nFixedInstallationsAndRetirements = AvoidForbiddenInstallationsAndRetirements(mTEPES, mTEPES)
    nFixedVariables += nFixedInstallationsAndRetirements

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

    # tolerance to consider 0 an investment decision
    pEpsilon = 1e-4
    def SetToZero(mTEPES, OptModel, pEpsilon) -> None:
        '''
        Set small numbers to 0.

        This function takes a mTEPES instance and sets values under a certain threshold to be 0.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:
            pEpsilon: The threshold for considering a number 0.

        Returns:
            None: Changes are performed directly onto the model object.
        '''
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
            if  mTEPES.pGenLoRetire[  gd      ]() <       pEpsilon:
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

    SetToZero(mTEPES, OptModel, pEpsilon)

    def DetectInfeasibilities(mTEPES) -> None:
        '''
        Detect model infeasibilities.

        This function takes a mTEPES instance and checks for different infeasibilities.

        Parameters:
            mTEPES: The instance of mTEPES.

        Returns:
            None: Raises a ValueError when an infeasibility is found.
        '''
        # detecting infeasibility: sum of scenario probabilities must be 1 in each period
        # for p in mTEPES.p:
        #     if abs(sum(mTEPES.pScenProb[p,sc] for sc in mTEPES.sc)-1.0) > 1e-6:
        #         raise ValueError('### Sum of scenario probabilities different from 1 in period ', p)


        for es in mTEPES.es:
            # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows
            if sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) > 0.0:
                raise ValueError('### Total minimum output greater than total inflows for ESS unit ', es, sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes))
            if sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) < 0.0:
                raise ValueError('### Total maximum charge lower than total outflows for ESS unit ', es, sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes))

        # detect inventory infeasibility
        for p,sc,n,es in mTEPES.ps*mTEPES.nesc:
            if (p,es) in mTEPES.pes:
                if mTEPES.pMaxCapacity[p,sc,n,es]:
                    if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])
                    elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])

        # detect minimum energy infeasibility
        for p,sc,n,g in mTEPES.ps*mTEPES.ngen:
            if (p,g) in mTEPES.pg:
                if (p,sc,g) in mTEPES.gm:
                    if sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
                        raise ValueError('### Minimum energy violation ', p, sc, n, g, sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]))

        # detecting reserve margin infeasibility
        for p,ar in mTEPES.p*mTEPES.ar:
            if     sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g) < mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]:
                raise     ValueError('### Electricity reserve margin infeasibility ', p, ar, sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g), mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

            if mTEPES.pIndHeat == 1:
                if sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g) < mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
                    raise ValueError('### Heat reserve margin infeasibility ',        p, ar, sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g), mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

    DetectInfeasibilities(mTEPES)

    mTEPES.nFixedVariables = Param(initialize=round(nFixedVariables), within=NonNegativeIntegers, doc='Number of fixed variables')

    mTEPES.IndependentPeriods = Param(domain=Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages = Param(mTEPES.pp, domain = Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages2 = Param(domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel = Param(domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel = True
    if (    (len(mTEPES.gc) == 0 or mTEPES.pIndBinGenInvest()     == 2)   # No candidates
        and (len(mTEPES.gd) == 0 or mTEPES.pIndBinGenRetire()     == 2)   # No retirements
        and (len(mTEPES.lc) == 0 or mTEPES.pIndBinNetElecInvest() == 2)): # No line candidates
        # Periods and scenarios are independent from each other
        ScIndep = True
        mTEPES.IndependentPeriods = True
        for p, ar in mTEPES.pEmission:
            print(p,ar)
            print(mTEPES.pEmission[p,ar])
        for p in mTEPES.p:
            if (    (min([mTEPES.pEmission[p, ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)  # No emissions
                and (max([mTEPES.pRESEnergy[p, ar] for ar in mTEPES.ar]) == 0)):  # No minimum RES requirements
            # Stages are independent from each other
                StIndep = True
                mTEPES.IndependentStages[p] = True
    if all(mTEPES.IndependentStages[p]() for p in mTEPES.pp):
        mTEPES.IndependentStages2 = True

    for p in mTEPES.p:
        print("periods in p",p)
    mTEPES.Period = Block(mTEPES.p)
    for p in mTEPES.Period:
        print("period",p)
        Period = mTEPES.Period[p]
        #TODO: Filter in some way that scenarios may not belong to periods
        # period2scenario = [stt for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p]
        Period.Scenario = Block(mTEPES.sc)
        Period.n = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if pp == p])
        for sc in Period.Scenario:
            Scenario = Period.Scenario[sc]
            Scenario.Stage = Block(Set(initialize=[stt for pp,scc,stt, nn in mTEPES.s2n if scc == sc and pp == p]))
            Scenario.n = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p])

        # iterative model formulation for each stage of a year
            for st in Scenario.Stage:
                Stage = Scenario.Stage[st]
                Stage.n = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])
                Stage.n2 = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])

                # load levels multiple of cycles for each ESS/generator
                Stage.nesc = [(n, es) for n, es in Stage.n * mTEPES.es if Stage.n.ord(n) % mTEPES.pStorageTimeStep[es] == 0]
                Stage.necc = [(n, ec) for n, ec in Stage.n * mTEPES.ec if Stage.n.ord(n) % mTEPES.pStorageTimeStep[ec] == 0]
                Stage.neso = [(n, es) for n, es in Stage.n * mTEPES.es if Stage.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0]
                Stage.ngen = [(n, g) for n, g in Stage.n * mTEPES.g if Stage.n.ord(n) % mTEPES.pEnergyTimeStep[g] == 0]

                if mTEPES.pIndHydroTopology == 1:
                    Stage.nhc      = [(n,h ) for n,h  in Stage.n*mTEPES.h  if Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                    if sum(1 for h,rs in mTEPES.p2r):
                        Stage.np2c = [(n,h ) for n,h  in Stage.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                    else:
                        Stage.np2c = []
                    if sum(1 for rs,h in mTEPES.r2p):
                        Stage.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                    else:
                        Stage.npc  = []
                    Stage.nrsc     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrcc     = [(n,rs) for n,rs in Stage.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrso     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]




    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
