"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - October 24, 2025
"""

import datetime
import time
import math
import os
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import DataPortal, Set, Param, Var, Binary, NonNegativeReals, NonNegativeIntegers, PositiveReals, PositiveIntegers, Reals, UnitInterval, Any
from   pyomo.environ import Block, Boolean

def InputData(DirName, CaseName, mTEPES, pIndLogConsole):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    set_definitions = {
        'pp': ('Period',     'p' ), 'scc': ('Scenario', 'sc'), 'stt': ('Stage',      'st'),
        'nn': ('LoadLevel',  'n' ), 'gg':  ('Generation','g'), 'gt':  ('Technology', 'gt'),
        'nd': ('Node',       'nd'), 'ni':  ('Node',     'nd'), 'nf':  ('Node',       'nd'),
        'zn': ('Zone',       'zn'), 'ar':  ('Area',     'ar'), 'rg':  ('Region',     'rg'),
        'cc': ('Circuit',    'cc'), 'c2':  ('Circuit',  'cc'), 'lt':  ('Line',       'lt'),
        'ndzn': ('NodeToZone', 'ndzn'), 'znar': ('ZoneToArea', 'znar'), 'arrg': ('AreaToRegion', 'arrg'),
    }

    dictSets = DataPortal()

    # Reading dictionaries from CSV and adding elements to the dictSets
    for set_name, (file_set_name, set_key) in set_definitions.items():
        filename = f'oT_Dict_{file_set_name}_{CaseName}.csv'
        dictSets.load(filename=os.path.join(_path, filename), set=set_key, format='set')
        is_ordered = set_name not in {'gt', 'nd', 'ni', 'nf', 'cc', 'c2', 'ndzn', 'znar', 'arrg'}
        setattr(mTEPES, set_name, Set(initialize=dictSets[set_key], ordered=is_ordered, doc=f'{file_set_name}'))

    # # Defining sets in the model
    # for set_name, (file_set_name, set_key) in set_definitions.items():
    #     is_ordered = set_name not in {'stt', 'gt', 'nd', 'ni', 'nf', 'cc', 'c2', 'ndzn', 'znar', 'arrg'}
    #     setattr(model, set_name, Set(initialize=dictSets[set_key], ordered=is_ordered, doc=f'{file_set_name}'))

    # Constants
    DEFAULT_IDX_COLS = ['Period', 'Scenario', 'LoadLevel', 'Area', 'Generator', 'InitialNode', 'FinalNode', 'Circuit', 'Node', 'Stage']
    SPECIAL_IDX_COLS = {'Generation': ['Generator'], 'Reservoir': ['Reservoir']}
    HEADER_LEVELS = {
        'VariableTTCFrw': [0, 1, 2   ],
        'VariableTTCBck': [0, 1, 2   ],
        'VariablePTDF'  : [0, 1, 2, 3],
    }
    FLAG_MAPPING = {
        'VariableTTCFrw'   : ('pIndVarTTC'       , None, 'No variable transmission line TTCs'  ),
        'VariableTTCBck'   : ('pIndVarTTC'       , None, 'No variable transmission line TTCs'  ),
        'VariablePTDF'     : ('pIndPTDF'         , None, 'No flow-based market coupling method'),
        'Reservoir'        : ('pIndHydroTopology', None, 'No hydropower topology'              ),
        'VariableMinVolume': ('pIndHydroTopology', None, 'No hydropower topology'              ),
        'VariableMaxVolume': ('pIndHydroTopology', None, 'No hydropower topology'              ),
        'HydroInflows'     : ('pIndHydroTopology', None, 'No hydropower topology'              ),
        'HydroOutflows'    : ('pIndHydroTopology', None, 'No hydropower topology'              ),
        'DemandHydrogen'   : ('pIndHydrogen'     , None, 'No hydrogen energy carrier'          ),
        'NetworkHydrogen'  : ('pIndHydrogen'     , None, 'No hydrogen energy carrier'          ),
        'DemandHeat'       : ('pIndHeat'         , None, 'No heat energy carrier'              ),
        'ReserveMarginHeat': ('pIndHeat'         , None, 'No heat energy carrier'              ),
        'NetworkHeat'      : ('pIndHeat'         , None, 'No heat energy carrier'              ),
    }

    factor_1 = 1e-3
    factor_2 = 1e-6

    def load_csv_with_index(path, file_name, idx_cols, header_levels=None):
        """
        Load a CSV file into a DataFrame and set its index based on provided columns.
        """
        full_path = os.path.join(path, file_name)
        if header_levels:
            df = pd.read_csv(full_path, header=header_levels, index_col=[0, 1, 2])
        else:
            df = pd.read_csv(full_path)

            present_idx = [col for col in df.columns if col in idx_cols]
            file_key = file_name.split('_')[2]
            idx_to_set = SPECIAL_IDX_COLS.get(file_key, present_idx)
            if file_key == 'Duration':
                idx_to_set = idx_to_set[:-1]  # Exclude 'Stage' for Duration
            df.set_index(idx_to_set, inplace=True, drop=True)
        return df

    def read_input_data(path, case_name):
        """
        Read all oT_Data files from the given directory, returning
        a dict of DataFrames and a dict of flags for loaded data.
        """
        dfs = {}
        par = {}

        # Identify unique file types
        files = [f for f in os.listdir(path) if 'oT_Data' in f]
        file_sets = set(f.split('_')[2] for f in files)

        for fs in file_sets:
            file_name = f'oT_Data_{fs}_{case_name}.csv'
            dp_key, _, error_msg = FLAG_MAPPING.get(fs, (None, None, None))
            header = HEADER_LEVELS.get(fs)

            try:
                if fs in ('Option', 'Parameter'):
                    dfs[f'df{fs}'] = pd.read_csv(os.path.join(path, file_name))
                else:
                    dfs[f'df{fs}'] = load_csv_with_index(path, file_name, DEFAULT_IDX_COLS, header)

                if dp_key:
                    par[dp_key] = 1
            except FileNotFoundError:
                print(f'WARNING: File not found: {file_name}')
                if dp_key:
                    par[dp_key] = 0
            except Exception as e:
                print(f'No file {file_name}')
                if dp_key:
                    par[dp_key] = 0

        return dfs, par

    dfs, par = read_input_data(_path, CaseName)
    # if 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat' not in par include them and set value to zero
    for key in ['pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat']:
        if key not in par.keys():
            par[key] = 0

    # substitute NaN by 0
    for key, df in dfs.items():
        if 'dfEmission' in key:
            df.fillna(math.inf, inplace=True)
        elif 'dfGeneration' in key:
            # build a dict that gives 1.0 for 'Efficiency', 0.0 for everything else
            fill_values = {col: (1.0 if col == 'Efficiency' else 0.0) for col in df.columns}
            # one pass over the DataFrame
            df.fillna(fill_values, inplace=True)
        else:
            df.fillna(0.0, inplace=True)

    # Define prefixes and suffixes
    mTEPES.gen_frames_suffixes   = ['VariableMinGeneration', 'VariableMaxGeneration',
                                    'VariableMinConsumption', 'VariableMaxConsumption',
                                    'VariableMinStorage', 'VariableMaxStorage',
                                    'EnergyInflows',
                                    'EnergyOutflows',
                                    'VariableMinEnergy', 'VariableMaxEnergy',
                                    'VariableFuelCost',
                                    'VariableEmissionCost',]
    mTEPES.node_frames_suffixes  = ['Demand', 'Inertia']
    mTEPES.area_frames_suffixes  = ['OperatingReserveUp', 'OperatingReserveDown', 'ReserveMargin', 'Emission', 'RESEnergy']
    mTEPES.hydro_frames_suffixes = ['Reservoir', 'VariableMinVolume', 'VariableMaxVolume', 'HydroInflows', 'HydroOutflows']
    mTEPES.hydrogen_frames_suffixes  = ['DemandHydrogen']
    mTEPES.heat_frames_suffixes  = ['DemandHeat', 'ReserveMarginHeat']
    mTEPES.frames_suffixes = (mTEPES.gen_frames_suffixes + mTEPES.node_frames_suffixes + mTEPES.area_frames_suffixes +
                              mTEPES.hydro_frames_suffixes+ mTEPES.hydrogen_frames_suffixes + mTEPES.heat_frames_suffixes)

    # Apply the condition to each specified column
    for keys, df in dfs.items():
        if [1 for suffix in mTEPES.gen_frames_suffixes if suffix in keys]:
            dfs[keys] = df.where(df > 0.0, 0.0)

    reading_time = round(time.time() - StartTime)
    print('Reading the CSV files                  ...  {} s'.format(reading_time))
    StartTime = time.time()

    if (dfs['dfGeneration']['Efficiency'] == 0.0).any():
        print('WARNING: Efficiency values of 0.0 are not valid. They have been changed to 1.0.')
        print("If you want to disable charging, set 'MaximumCharge' to 0.0 or leave it empty.")
    dfs['dfGeneration']['Efficiency'] = dfs['dfGeneration']['Efficiency'].where(dfs['dfGeneration']['Efficiency'] != 0.0, 1.0)

    # show some statistics of the data
    for key, df in dfs.items():
        if pIndLogConsole == 1 and [1 for suffix in mTEPES.frames_suffixes if suffix in key]:
            print(f'{key}:\n', df.describe(), '\n')
    # reading additional data sets related to reservoirs and hydro
    try:
        import csv
        def count_lines_in_csv(csv_file_path):
            with open(csv_file_path, 'r', newline='') as file:
                reader = csv.reader(file)
                num_lines = sum(1 for _ in reader)
            return num_lines

        mTEPES.rs  = Set(initialize=[], doc='reservoirs'                )
        mTEPES.r2h = Set(initialize=[], doc='reservoir to hydro'        )
        mTEPES.h2r = Set(initialize=[], doc='hydro to reservoir'        )
        mTEPES.r2r = Set(initialize=[], doc='reservoir 1 to reservoir 2')
        mTEPES.p2r = Set(initialize=[], doc='pumped-hydro to reservoir' )
        mTEPES.r2p = Set(initialize=[], doc='reservoir to pumped-hydro' )

        if count_lines_in_csv(     f'{_path}/oT_Dict_Reservoir_'            f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_Reservoir_'            f'{CaseName}.csv', set='rs' , format='set')
            mTEPES.del_component(mTEPES.rs)
            mTEPES.rs  = Set(initialize=dictSets['rs' ], doc='reservoirs'                )
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToHydro_'     f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToHydro_'     f'{CaseName}.csv', set='r2h', format='set')
            mTEPES.del_component(mTEPES.r2h)
            mTEPES.r2h = Set(initialize=dictSets['r2h'], doc='reservoir to hydro'        )
        if count_lines_in_csv(     f'{_path}/oT_Dict_HydroToReservoir_'     f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_HydroToReservoir_'     f'{CaseName}.csv', set='h2r', format='set')
            mTEPES.del_component(mTEPES.h2r)
            mTEPES.h2r = Set(initialize=dictSets['h2r'], doc='hydro to reservoir'        )
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToReservoir_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToReservoir_' f'{CaseName}.csv', set='r2r', format='set')
            mTEPES.del_component(mTEPES.r2r)
            mTEPES.r2r = Set(initialize=dictSets['r2r'], doc='reservoir 1 to reservoir 2')
        if count_lines_in_csv(     f'{_path}/oT_Dict_PumpedHydroToReservoir_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_PumpedHydroToReservoir_' f'{CaseName}.csv', set='p2r', format='set')
            mTEPES.del_component(mTEPES.p2r)
            mTEPES.p2r = Set(initialize=dictSets['p2r'], doc='pumped-hydro to reservoir' )
        if count_lines_in_csv(     f'{_path}/oT_Dict_ReservoirToPumpedHydro_' f'{CaseName}.csv') > 1:
            dictSets.load(filename=f'{_path}/oT_Dict_ReservoirToPumpedHydro_' f'{CaseName}.csv', set='r2p', format='set')
            mTEPES.del_component(mTEPES.r2p)
            mTEPES.r2p = Set(initialize=dictSets['r2p'], doc='reservoir to pumped-hydro' )
    except:
        pass

    # load parameters from dfOption
    for col in dfs['dfOption'].columns:
        par[f'p{col}'] = dfs['dfOption'][col].iloc[0].astype('int')

    # load parameters from dfParameter
    for col in dfs['dfParameter'].columns:
        if col in ['ENSCost', 'HNSCost', 'HTNSCost', 'SBase']:
            par[f'p{col}'] = dfs['dfParameter'][col].iloc[0] * factor_1
        elif col in ['TimeStep']:
            par[f'p{col}'] = dfs['dfParameter'][col].iloc[0].astype('int')
        else:
            par[f'p{col}'] = dfs['dfParameter'][col].iloc[0]

    par['pPeriodWeight']         = dfs['dfPeriod']       ['Weight'        ].astype('int')                          # weights of periods                        [p.u.]
    par['pScenProb']             = dfs['dfScenario']     ['Probability'   ].astype('float64')                      # probabilities of scenarios                [p.u.]
    par['pStageWeight']          = dfs['dfStage']        ['Weight'        ].astype('float64')                      # weights of stages
    par['pDuration']             = dfs['dfDuration']     ['Duration'      ] * par['pTimeStep']                     # duration of load levels                   [h]
    par['pLevelToStage']         = dfs['dfDuration']     ['Stage'         ]                                        # load levels assignment to stages
    par['pReserveMargin']        = dfs['dfReserveMargin']['ReserveMargin' ]                                        # minimum adequacy reserve margin           [p.u.]
    par['pEmission']             = dfs['dfEmission']     ['CO2Emission'   ]                                        # maximum CO2 emission                      [MtCO2]
    par['pRESEnergy']            = dfs['dfRESEnergy']    ['RESEnergy'     ]                                        # minimum RES energy                        [GWh]
    par['pDemandElec']           = dfs['dfDemand'].reindex                (columns=mTEPES.nd, fill_value=0.0) * 1e-3 # electric demand                           [GW]
    par['pSystemInertia']        = dfs['dfInertia'].reindex               (columns=mTEPES.ar, fill_value=0.0)        # inertia                                   [s]
    par['pOperReserveUp']        = dfs['dfOperatingReserveUp'].reindex    (columns=mTEPES.ar, fill_value=0.0) * 1e-3 # upward   operating reserve                [GW]
    par['pOperReserveDw']        = dfs['dfOperatingReserveDown'].reindex  (columns=mTEPES.ar, fill_value=0.0) * 1e-3 # downward operating reserve                [GW]
    par['pVariableMinPowerElec'] = dfs['dfVariableMinGeneration'].reindex (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum power            [GW]
    par['pVariableMaxPowerElec'] = dfs['dfVariableMaxGeneration'].reindex (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum power            [GW]
    par['pVariableMinCharge']    = dfs['dfVariableMinConsumption'].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum charge           [GW]
    par['pVariableMaxCharge']    = dfs['dfVariableMaxConsumption'].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum charge           [GW]
    par['pVariableMinStorage']   = dfs['dfVariableMinStorage'].reindex    (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable minimum storage          [GWh]
    par['pVariableMaxStorage']   = dfs['dfVariableMaxStorage'].reindex    (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable maximum storage          [GWh]
    par['pVariableMinEnergy']    = dfs['dfVariableMinEnergy'].reindex     (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum energy           [GW]
    par['pVariableMaxEnergy']    = dfs['dfVariableMaxEnergy'].reindex     (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum energy           [GW]
    par['pVariableFuelCost']     = dfs['dfVariableFuelCost'].reindex      (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable fuel cost                [EUR/MJ]
    par['pVariableEmissionCost'] = dfs['dfVariableEmissionCost'].reindex  (columns=mTEPES.gg, fill_value=0.0)        # dynamic variable emission cost            [EUR/tCO2]
    par['pEnergyInflows']        = dfs['dfEnergyInflows'].reindex         (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy inflows                    [GW]
    par['pEnergyOutflows']       = dfs['dfEnergyOutflows'].reindex        (columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy outflows                   [GW]

    if par['pIndVarTTC'] == 1:
        par['pVariableNTCFrw'] = dfs['dfVariableTTCFrw'] * 1e-3                                                      # variable TTC forward                      [GW]
        par['pVariableNTCBck'] = dfs['dfVariableTTCBck'] * 1e-3                                                      # variable TTC backward                     [GW]
    if par['pIndPTDF'] == 1:
        par['pVariablePTDF']   = dfs['dfVariablePTDF']                                                               # variable PTDF                             [p.u.]

    if par['pIndHydroTopology'] == 1:
        par['pVariableMinVolume'] = dfs['dfVariableMinVolume'].reindex  (columns=mTEPES.rs, fill_value=0.0)          # dynamic variable minimum reservoir volume [hm3]
        par['pVariableMaxVolume'] = dfs['dfVariableMaxVolume'].reindex  (columns=mTEPES.rs, fill_value=0.0)          # dynamic variable maximum reservoir volume [hm3]
        par['pHydroInflows']      = dfs['dfHydroInflows'].reindex       (columns=mTEPES.rs, fill_value=0.0)          # dynamic hydro inflows                     [m3/s]
        par['pHydroOutflows']     = dfs['dfHydroOutflows'].reindex      (columns=mTEPES.rs, fill_value=0.0)          # dynamic hydro outflows                    [m3/s]

    if par['pIndHydrogen'] == 1:
        par['pDemandH2']          = dfs['dfDemandHydrogen']      [mTEPES.nd]                                         # hydrogen demand                           [tH2/h]

    if par['pIndHeat'] == 1:
        par['pReserveMarginHeat'] = dfs['dfReserveMarginHeat']   ['ReserveMargin']                                   # minimum adequacy reserve margin           [p.u.]
        par['pDemandHeat']        = dfs['dfDemandHeat']          [mTEPES.nd] * 1e-3                                  # heat     demand                           [GW]

    if par['pTimeStep'] > 1:
        # compute the demand as the mean over the time step load levels and assign it to active load levels. Idem for the remaining parameters
        # Skip mean calculation for empty DataFrames (either full of 0s or NaNs)
        def ProcessParameter(pDataFrame: pd.DataFrame, pTimeStep: int) -> pd.DataFrame:
            if ((pDataFrame != 0) & (~pDataFrame.isna())).any().any():
                pDataFrame = pDataFrame.rolling(pTimeStep).mean()
                pDataFrame.fillna(0.0, inplace=True)
            return pDataFrame

        # Apply the ProcessParameter function to each DataFrame
        par['pDemandElec']            = ProcessParameter(par['pDemandElec'],           par['pTimeStep'])
        par['pSystemInertia']         = ProcessParameter(par['pSystemInertia'],        par['pTimeStep'])
        par['pOperReserveUp']         = ProcessParameter(par['pOperReserveUp'],        par['pTimeStep'])
        par['pOperReserveDw']         = ProcessParameter(par['pOperReserveDw'],        par['pTimeStep'])
        par['pVariableMinPowerElec']  = ProcessParameter(par['pVariableMinPowerElec'], par['pTimeStep'])
        par['pVariableMaxPowerElec']  = ProcessParameter(par['pVariableMaxPowerElec'], par['pTimeStep'])
        par['pVariableMinCharge']     = ProcessParameter(par['pVariableMinCharge'],    par['pTimeStep'])
        par['pVariableMaxCharge']     = ProcessParameter(par['pVariableMaxCharge'],    par['pTimeStep'])
        par['pVariableMinStorage']    = ProcessParameter(par['pVariableMinStorage'],   par['pTimeStep'])
        par['pVariableMaxStorage']    = ProcessParameter(par['pVariableMaxStorage'],   par['pTimeStep'])
        par['pVariableMinEnergy']     = ProcessParameter(par['pVariableMinEnergy'],    par['pTimeStep'])
        par['pVariableMaxEnergy']     = ProcessParameter(par['pVariableMaxEnergy'],    par['pTimeStep'])
        par['pVariableFuelCost']      = ProcessParameter(par['pVariableFuelCost'],     par['pTimeStep'])
        par['pVariableEmissionCost']  = ProcessParameter(par['pVariableEmissionCost'], par['pTimeStep'])
        par['pEnergyInflows']         = ProcessParameter(par['pEnergyInflows'],        par['pTimeStep'])
        par['pEnergyOutflows']        = ProcessParameter(par['pEnergyOutflows'],       par['pTimeStep'])

        if par['pIndVarTTC'] == 1:
            par['pVariableNTCFrw']    = ProcessParameter(par['pVariableNTCFrw'],       par['pTimeStep'])
            par['pVariableNTCBck']    = ProcessParameter(par['pVariableNTCBck'],       par['pTimeStep'])
        if par['pIndPTDF'] == 1:
            par['pVariablePTDF']      = ProcessParameter(par['pVariablePTDF'],         par['pTimeStep'])

        if par['pIndHydroTopology'] == 1:
            par['pVariableMinVolume'] = ProcessParameter(par['pVariableMinVolume'],    par['pTimeStep'])
            par['pVariableMaxVolume'] = ProcessParameter(par['pVariableMaxVolume'],    par['pTimeStep'])
            par['pHydroInflows']      = ProcessParameter(par['pHydroInflows'],         par['pTimeStep'])
            par['pHydroOutflows']     = ProcessParameter(par['pHydroOutflows'],        par['pTimeStep'])

        if par['pIndHydrogen'] == 1:
            par['pDemandH2']          = ProcessParameter(par['pDemandH2'],             par['pTimeStep'])

        if par['pIndHeat'] == 1:
            par['pDemandHeat']        = ProcessParameter(par['pDemandHeat'],           par['pTimeStep'])

        # assign duration 0 to load levels not being considered; active load levels are at the end of every pTimeStep
        for n in range(par['pTimeStep']-2,-1,-1):
            par['pDuration'].iloc[[range(n,len(mTEPES.pp)*len(mTEPES.scc)*len(mTEPES.nn),par['pTimeStep'])]] = 0

        for psn in par['pDuration'].index:
            p,sc,n = psn
            if par['pPeriodWeight'][p] == 0.0:
                par['pDuration'].loc[p,sc,n] = 0
            if par['pScenProb'][p,sc] == 0.0:
                par['pDuration'].loc[p,sc,n] = 0

    #%% generation parameters
    par['pGenToNode']                  = dfs['dfGeneration']  ['Node'                      ]                                                             # generator location in node
    par['pGenToTechnology']            = dfs['dfGeneration']  ['Technology'                ]                                                             # generator association to technology
    par['pGenToExclusiveGen']          = dfs['dfGeneration']  ['MutuallyExclusive'         ]                                                             # mutually exclusive generator
    par['pIndBinUnitInvest']           = dfs['dfGeneration']  ['BinaryInvestment'          ]                                                             # binary unit investment decision              [Yes]
    par['pIndBinUnitRetire']           = dfs['dfGeneration']  ['BinaryRetirement'          ]                                                             # binary unit retirement decision              [Yes]
    par['pIndBinUnitCommit']           = dfs['dfGeneration']  ['BinaryCommitment'          ]                                                             # binary unit commitment decision              [Yes]
    par['pIndBinStorInvest']           = dfs['dfGeneration']  ['StorageInvestment'         ]                                                             # storage linked to generation investment      [Yes]
    par['pIndOperReserve']             = dfs['dfGeneration']  ['NoOperatingReserve'        ]                                                             # no contribution to operating reserve         [Yes]
    par['pIndOutflowIncomp']           = dfs['dfGeneration']  ['OutflowsIncompatibility'   ]                                                             # outflows incompatibility with charging
    par['pMustRun']                    = dfs['dfGeneration']  ['MustRun'                   ]                                                             # must-run unit                                [Yes]
    par['pInertia']                    = dfs['dfGeneration']  ['Inertia'                   ]                                                             # inertia constant                             [s]
    par['pElecGenPeriodIni']           = dfs['dfGeneration']  ['InitialPeriod'             ]                                                             # initial period                               [year]
    par['pElecGenPeriodFin']           = dfs['dfGeneration']  ['FinalPeriod'               ]                                                             # final   period                               [year]
    par['pAvailability']               = dfs['dfGeneration']  ['Availability'              ]                                                             # unit availability for adequacy               [p.u.]
    par['pEFOR']                       = dfs['dfGeneration']  ['EFOR'                      ]                                                             # EFOR                                         [p.u.]
    par['pRatedMinPowerElec']          = dfs['dfGeneration']  ['MinimumPower'              ] * 1e-3 * (1.0-dfs['dfGeneration']['EFOR'])                  # rated minimum electric power                 [GW]
    par['pRatedMaxPowerElec']          = dfs['dfGeneration']  ['MaximumPower'              ] * 1e-3 * (1.0-dfs['dfGeneration']['EFOR'])                  # rated maximum electric power                 [GW]
    par['pRatedMinPowerHeat']          = dfs['dfGeneration']  ['MinimumPowerHeat'          ] * 1e-3 * (1.0-dfs['dfGeneration']['EFOR'])                  # rated minimum heat     power                 [GW]
    par['pRatedMaxPowerHeat']          = dfs['dfGeneration']  ['MaximumPowerHeat'          ] * 1e-3 * (1.0-dfs['dfGeneration']['EFOR'])                  # rated maximum heat     power                 [GW]
    par['pRatedLinearFuelCost']        = dfs['dfGeneration']  ['LinearTerm'                ] * 1e-3 *      dfs['dfGeneration']['FuelCost']               # fuel     term variable cost                  [MEUR/GWh]
    par['pLinearOMCost']               = dfs['dfGeneration']  ['OMVariableCost'            ] * 1e-3                                                      # O&M      term variable cost                  [MEUR/GWh]
    par['pOperReserveCost']            = dfs['dfGeneration']  ['OperReserveCost'           ] * 1e-3                                                      # operating reserve      cost                  [MEUR/GW]
    par['pStartUpCost']                = dfs['dfGeneration']  ['StartUpCost'               ]                                                             # startup  cost                                [MEUR]
    par['pShutDownCost']               = dfs['dfGeneration']  ['ShutDownCost'              ]                                                             # shutdown cost                                [MEUR]
    par['pRampUp']                     = dfs['dfGeneration']  ['RampUp'                    ] * 1e-3                                                      # ramp up   rate                               [GW/h]
    par['pRampDw']                     = dfs['dfGeneration']  ['RampDown'                  ] * 1e-3                                                      # ramp down rate                               [GW/h]
    par['pEmissionCost']               = dfs['dfGeneration']  ['CO2EmissionRate'           ] * 1e-3 * par['pCO2Cost']                                    # CO2 emission  cost                           [MEUR/GWh]
    par['pEmissionRate']               = dfs['dfGeneration']  ['CO2EmissionRate'           ]                                                             # CO2 emission  rate                           [tCO2/MWh]
    par['pUpTime']                     = dfs['dfGeneration']  ['UpTime'                    ]                                                             # minimum up     time                          [h]
    par['pDwTime']                     = dfs['dfGeneration']  ['DownTime'                  ]                                                             # minimum down   time                          [h]
    par['pStableTime']                 = dfs['dfGeneration']  ['StableTime'                ]                                                             # minimum stable time                          [h]
    par['pShiftTime']                  = dfs['dfGeneration']  ['ShiftTime'                 ]                                                             # maximum shift time for DSM                   [h]
    par['pGenInvestCost']              = dfs['dfGeneration']  ['FixedInvestmentCost'       ] *             dfs['dfGeneration']['FixedChargeRate']        # generation fixed cost                        [MEUR]
    par['pGenRetireCost']              = dfs['dfGeneration']  ['FixedRetirementCost'       ] *             dfs['dfGeneration']['FixedChargeRate']        # generation fixed retirement cost             [MEUR]
    par['pRatedMinCharge']             = dfs['dfGeneration']  ['MinimumCharge'             ] * 1e-3                                                      # rated minimum ESS charge                     [GW]
    par['pRatedMaxCharge']             = dfs['dfGeneration']  ['MaximumCharge'             ] * 1e-3                                                      # rated maximum ESS charge                     [GW]
    par['pRatedMinStorage']            = dfs['dfGeneration']  ['MinimumStorage'            ]                                                             # rated minimum ESS storage                    [GWh]
    par['pRatedMaxStorage']            = dfs['dfGeneration']  ['MaximumStorage'            ]                                                             # rated maximum ESS storage                    [GWh]
    par['pInitialInventory']           = dfs['dfGeneration']  ['InitialStorage'            ]                                                             # initial       ESS storage                    [GWh]
    par['pProductionFunctionHydro']    = dfs['dfGeneration']  ['ProductionFunctionHydro'   ]                                                             # production function of a hydropower plant    [kWh/m3]
    par['pProductionFunctionH2']       = dfs['dfGeneration']  ['ProductionFunctionH2'      ] * 1e-3                                                      # production function of an electrolyzer       [kWh/gH2]
    par['pProductionFunctionHeat']     = dfs['dfGeneration']  ['ProductionFunctionHeat'    ]                                                             # production function of a heat pump           [kWh/kWh]
    par['pProductionFunctionH2ToHeat'] = dfs['dfGeneration']  ['ProductionFunctionH2ToHeat'] * 1e-3                                                      # production function of a boiler using H2     [gH2/kWh]
    par['pEfficiency']                 = dfs['dfGeneration']  ['Efficiency'                ]                                                             #               ESS round-trip efficiency      [p.u.]
    par['pStorageType']                = dfs['dfGeneration']  ['StorageType'               ]                                                             #               ESS storage  type
    par['pOutflowsType']               = dfs['dfGeneration']  ['OutflowsType'              ]                                                             #               ESS outflows type
    par['pEnergyType']                 = dfs['dfGeneration']  ['EnergyType'                ]                                                             #               unit  energy type
    par['pRMaxReactivePower']          = dfs['dfGeneration']  ['MaximumReactivePower'      ] * 1e-3                                                      # rated maximum reactive power                 [Gvar]
    par['pGenLoInvest']                = dfs['dfGeneration']  ['InvestmentLo'              ]                                                             # Lower bound of the investment decision       [p.u.]
    par['pGenUpInvest']                = dfs['dfGeneration']  ['InvestmentUp'              ]                                                             # Upper bound of the investment decision       [p.u.]
    par['pGenLoRetire']                = dfs['dfGeneration']  ['RetirementLo'              ]                                                             # Lower bound of the retirement decision       [p.u.]
    par['pGenUpRetire']                = dfs['dfGeneration']  ['RetirementUp'              ]                                                             # Upper bound of the retirement decision       [p.u.]

    par['pRatedLinearOperCost']        = par['pRatedLinearFuelCost'] + par['pEmissionCost']
    par['pRatedLinearVarCost']         = par['pRatedLinearFuelCost'] + par['pLinearOMCost']

    if par['pIndHydroTopology'] == 1:
        par['pReservoirType']          = dfs['dfReservoir']   ['StorageType'               ]                                                             #               reservoir type
        par['pWaterOutfType']          = dfs['dfReservoir']   ['OutflowsType'              ]                                                             #           water outflow type
        par['pRatedMinVolume']         = dfs['dfReservoir']   ['MinimumStorage'            ]                                                             # rated minimum reservoir volume               [hm3]
        par['pRatedMaxVolume']         = dfs['dfReservoir']   ['MaximumStorage'            ]                                                             # rated maximum reservoir volume               [hm3]
        par['pInitialVolume']          = dfs['dfReservoir']   ['InitialStorage'            ]                                                             # initial       reservoir volume               [hm3]
        par['pIndBinRsrvInvest']       = dfs['dfReservoir']   ['BinaryInvestment'          ]                                                             # binary reservoir investment decision         [Yes]
        par['pRsrInvestCost']          = dfs['dfReservoir']   ['FixedInvestmentCost'       ] *             dfs['dfReservoir']['FixedChargeRate']         #        reservoir fixed cost                  [MEUR]
        par['pRsrPeriodIni']           = dfs['dfReservoir']   ['InitialPeriod'             ]                                                             # initial period                               [year]
        par['pRsrPeriodFin']           = dfs['dfReservoir']   ['FinalPeriod'               ]                                                             # final   period                               [year]

    par['pNodeLat']                    = dfs['dfNodeLocation']['Latitude'                  ]                                                             # node latitude                                [º]
    par['pNodeLon']                    = dfs['dfNodeLocation']['Longitude'                 ]                                                             # node longitude                               [º]

    par['pLineType']                   = dfs['dfNetwork']     ['LineType'                  ]                                                             # electric line type
    par['pLineLength']                 = dfs['dfNetwork']     ['Length'                    ]                                                             # electric line length                         [km]
    par['pLineVoltage']                = dfs['dfNetwork']     ['Voltage'                   ]                                                             # electric line voltage                        [kV]
    par['pElecNetPeriodIni']           = dfs['dfNetwork']     ['InitialPeriod'             ]                                                             # initial period
    par['pElecNetPeriodFin']           = dfs['dfNetwork']     ['FinalPeriod'               ]                                                             # final   period
    par['pLineLossFactor']             = dfs['dfNetwork']     ['LossFactor'                ]                                                             # electric line loss factor                    [p.u.]
    par['pLineR']                      = dfs['dfNetwork']     ['Resistance'                ]                                                             # electric line resistance                     [p.u.]
    par['pLineX']                      = dfs['dfNetwork']     ['Reactance'                 ].sort_index()                                                # electric line reactance                      [p.u.]
    par['pLineBsh']                    = dfs['dfNetwork']     ['Susceptance'               ]                                                             # electric line susceptance                    [p.u.]
    par['pLineTAP']                    = dfs['dfNetwork']     ['Tap'                       ]                                                             # tap changer                                  [p.u.]
    par['pLineNTCFrw']                 = dfs['dfNetwork']     ['TTC'                       ] * 1e-3 *      dfs['dfNetwork']['SecurityFactor' ]           # net transfer capacity in forward  direction  [GW]
    par['pLineNTCBck']                 = dfs['dfNetwork']     ['TTCBck'                    ] * 1e-3 *      dfs['dfNetwork']['SecurityFactor' ]           # net transfer capacity in backward direction  [GW]
    par['pNetFixedCost']               = dfs['dfNetwork']     ['FixedInvestmentCost'       ] *             dfs['dfNetwork']['FixedChargeRate']           # electric network    fixed cost               [MEUR]
    par['pIndBinLineSwitch']           = dfs['dfNetwork']     ['Switching'                 ]                                                             # binary electric line switching  decision     [Yes]
    par['pIndBinLineInvest']           = dfs['dfNetwork']     ['BinaryInvestment'          ]                                                             # binary electric line investment decision     [Yes]
    # par['pSwitchOnTime']               = dfs['dfNetwork']     ['SwOnTime'                  ].astype('int')                                               # minimum on  time                             [h]
    # par['pSwitchOffTime']              = dfs['dfNetwork']     ['SwOffTime'                 ].astype('int')                                               # minimum off time                             [h]
    par['pAngMin']                     = dfs['dfNetwork']     ['AngMin'                    ] * math.pi / 180                                             # Min phase angle difference                   [rad]
    par['pAngMax']                     = dfs['dfNetwork']     ['AngMax'                    ] * math.pi / 180                                             # Max phase angle difference                   [rad]
    par['pNetLoInvest']                = dfs['dfNetwork']     ['InvestmentLo'              ]                                                             # Lower bound of the investment decision       [p.u.]
    par['pNetUpInvest']                = dfs['dfNetwork']     ['InvestmentUp'              ]                                                             # Upper bound of the investment decision       [p.u.]

    # replace PeriodFin = 0.0 by year 3000
    par['pElecGenPeriodFin'] = par['pElecGenPeriodFin'].where(par['pElecGenPeriodFin'] != 0.0, 3000   )
    if par['pIndHydroTopology'] == 1:
        par['pRsrPeriodFin'] = par['pRsrPeriodFin'].where    (par['pRsrPeriodFin']     != 0.0, 3000   )
    par['pElecNetPeriodFin'] = par['pElecNetPeriodFin'].where(par['pElecNetPeriodFin'] != 0.0, 3000   )
    # replace pLineNTCBck = 0.0 by pLineNTCFrw
    par['pLineNTCBck']       = par['pLineNTCBck'].where      (par['pLineNTCBck']  > 0.0,   par['pLineNTCFrw'])
    # replace pLineNTCFrw = 0.0 by pLineNTCBck
    par['pLineNTCFrw']       = par['pLineNTCFrw'].where      (par['pLineNTCFrw']  > 0.0,   par['pLineNTCBck'])
    # replace pGenUpInvest = 0.0 by 1.0
    par['pGenUpInvest']      = par['pGenUpInvest'].where     (par['pGenUpInvest'] > 0.0,   1.0               )
    # replace pGenUpRetire = 0.0 by 1.0
    par['pGenUpRetire']      = par['pGenUpRetire'].where     (par['pGenUpRetire'] > 0.0,   1.0               )
    # replace pNetUpInvest = 0.0 by 1.0
    par['pNetUpInvest']      = par['pNetUpInvest'].where     (par['pNetUpInvest'] > 0.0,   1.0               )

    # minimum up- and downtime converted to an integer number of time steps
    # par['pSwitchOnTime']  = round(par['pSwitchOnTime'] /par['pTimeStep']).astype('int')
    # par['pSwitchOffTime'] = round(par['pSwitchOffTime']/par['pTimeStep']).astype('int')

    if par['pIndHydrogen'] == 1:
        par['pH2PipeLength']       = dfs['dfNetworkHydrogen']['Length'             ]                                                         # hydrogen line length                         [km]
        par['pH2PipePeriodIni']    = dfs['dfNetworkHydrogen']['InitialPeriod'      ]                                                         # initial period
        par['pH2PipePeriodFin']    = dfs['dfNetworkHydrogen']['FinalPeriod'        ]                                                         # final   period
        par['pH2PipeNTCFrw']       = dfs['dfNetworkHydrogen']['TTC'                ] *      dfs['dfNetworkHydrogen']['SecurityFactor' ]      # net transfer capacity in forward  direction  [tH2]
        par['pH2PipeNTCBck']       = dfs['dfNetworkHydrogen']['TTCBck'             ] *      dfs['dfNetworkHydrogen']['SecurityFactor' ]      # net transfer capacity in backward direction  [tH2]
        par['pH2PipeFixedCost']    = dfs['dfNetworkHydrogen']['FixedInvestmentCost'] *      dfs['dfNetworkHydrogen']['FixedChargeRate']      # hydrogen network    fixed cost               [MEUR]
        par['pIndBinH2PipeInvest'] = dfs['dfNetworkHydrogen']['BinaryInvestment'   ]                                                         # binary hydrogen pipeline investment decision [Yes]
        par['pH2PipeLoInvest']     = dfs['dfNetworkHydrogen']['InvestmentLo'       ]                                                         # Lower bound of the investment decision       [p.u.]
        par['pH2PipeUpInvest']     = dfs['dfNetworkHydrogen']['InvestmentUp'       ]                                                         # Upper bound of the investment decision       [p.u.]

        par['pH2PipePeriodFin'] = par['pH2PipePeriodFin'].where(par['pH2PipePeriodFin'] != 0.0, 3000       )
        # replace pH2PipeNTCBck = 0.0 by pH2PipeNTCFrw
        par['pH2PipeNTCBck']    = par['pH2PipeNTCBck'].where   (par['pH2PipeNTCBck']     > 0.0, par['pH2PipeNTCFrw'])
        # replace pH2PipeNTCFrw = 0.0 by pH2PipeNTCBck
        par['pH2PipeNTCFrw']    = par['pH2PipeNTCFrw'].where   (par['pH2PipeNTCFrw']     > 0.0, par['pH2PipeNTCBck'])
        # replace pH2PipeUpInvest = 0.0 by 1.0
        par['pH2PipeUpInvest']  = par['pH2PipeUpInvest'].where(par['pH2PipeUpInvest']    > 0.0, 1.0                 )

    if par['pIndHeat'] == 1:
        par['pHeatPipeLength']       = dfs['dfNetworkHeat']['Length'             ]                                                           # heat pipe length                             [km]
        par['pHeatPipePeriodIni']    = dfs['dfNetworkHeat']['InitialPeriod'      ]                                                           # initial period
        par['pHeatPipePeriodFin']    = dfs['dfNetworkHeat']['FinalPeriod'        ]                                                           # final   period
        par['pHeatPipeNTCFrw']       = dfs['dfNetworkHeat']['TTC'                ] * 1e-3 * dfs['dfNetworkHeat']    ['SecurityFactor' ]      # net transfer capacity in forward  direction  [GW]
        par['pHeatPipeNTCBck']       = dfs['dfNetworkHeat']['TTCBck'             ] * 1e-3 * dfs['dfNetworkHeat']    ['SecurityFactor' ]      # net transfer capacity in backward direction  [GW]
        par['pHeatPipeFixedCost']    = dfs['dfNetworkHeat']['FixedInvestmentCost'] *        dfs['dfNetworkHeat']    ['FixedChargeRate']      # heat    network    fixed cost                [MEUR]
        par['pIndBinHeatPipeInvest'] = dfs['dfNetworkHeat']['BinaryInvestment'   ]                                                           # binary heat     pipe     investment decision [Yes]
        par['pHeatPipeLoInvest']     = dfs['dfNetworkHeat']['InvestmentLo'       ]                                                           # Lower bound of the investment decision       [p.u.]
        par['pHeatPipeUpInvest']     = dfs['dfNetworkHeat']['InvestmentUp'       ]                                                           # Upper bound of the investment decision       [p.u.]

        par['pHeatPipePeriodFin']    = par['pHeatPipePeriodFin'].where(par['pHeatPipePeriodFin'] != 0.0, 3000                  )
        # replace pHeatPipeNTCBck = 0.0 by pHeatPipeNTCFrw
        par['pHeatPipeNTCBck']       = par['pHeatPipeNTCBck'].where   (par['pHeatPipeNTCBck']     > 0.0, par['pHeatPipeNTCFrw'])
        # replace pHeatPipeNTCFrw = 0.0 by pHeatPipeNTCBck
        par['pHeatPipeNTCFrw']       = par['pHeatPipeNTCFrw'].where   (par['pHeatPipeNTCFrw']     > 0.0, par['pHeatPipeNTCBck'])
        # replace pHeatPipeUpInvest = 0.0 by 1.0
        par['pHeatPipeUpInvest']     = par['pHeatPipeUpInvest'].where (par['pHeatPipeUpInvest']   > 0.0, 1.0                   )

    #%% storing the parameters in the model
    mTEPES.dFrame  = dfs
    mTEPES.dPar    = par

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')


def DataConfiguration(mTEPES):

    StartTime = time.time()
    #%% Getting the branches from the electric network data
    sBr     = [(ni,nf) for (ni,nf,cc) in mTEPES.dFrame['dfNetwork'].index]
    # Dropping duplicate keys
    sBrList = [(ni,nf) for n,(ni,nf)  in enumerate(sBr) if (ni,nf) not in sBr[:n]]

    #%% defining subsets: active load levels (n,n2), thermal units (t), RES units (r), ESS units (es), candidate gen units (gc), candidate ESS units (ec), all the electric lines (la), candidate electric lines (lc), candidate DC electric lines (cd), existing DC electric lines (cd), electric lines with losses (ll), reference node (rf), and reactive generating units (gq)
    mTEPES.p      = Set(doc='periods'                          , initialize=[pp     for pp   in mTEPES.pp  if mTEPES.dPar['pPeriodWeight']       [pp] >  0.0 and sum(mTEPES.dPar['pDuration'][pp,sc,n] for sc,n in mTEPES.scc*mTEPES.nn)])
    mTEPES.sc     = Set(doc='scenarios'                        , initialize=[scc    for scc  in mTEPES.scc                                                  ])
    mTEPES.ps     = Set(doc='periods/scenarios'                , initialize=[(p,sc) for p,sc in mTEPES.p*mTEPES.sc if mTEPES.dPar['pScenProb'] [p,sc] >  0.0 and sum(mTEPES.dPar['pDuration'][p,sc,n ] for    n in            mTEPES.nn)])
    mTEPES.st     = Set(doc='stages'                           , initialize=[stt    for stt  in mTEPES.stt if mTEPES.dPar['pStageWeight']       [stt] >  0.0])
    mTEPES.n      = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(mTEPES.dPar['pDuration']  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2     = Set(doc='load levels'                      , initialize=[nn     for nn   in mTEPES.nn  if sum(mTEPES.dPar['pDuration']  [p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.g      = Set(doc='generating              units'    , initialize=[gg     for gg   in mTEPES.gg  if (mTEPES.dPar['pRatedMaxPowerElec'] [gg] >  0.0 or  mTEPES.dPar['pRatedMaxCharge'][gg] >  0.0   or  mTEPES.dPar['pRatedMaxPowerHeat']   [gg] >  0.0) and mTEPES.dPar['pElecGenPeriodIni'][gg] <= mTEPES.p.last() and mTEPES.dPar['pElecGenPeriodFin'][gg] >= mTEPES.p.first() and mTEPES.dPar['pGenToNode'].reset_index().set_index(['Generator']).isin(mTEPES.nd)['Node'][gg]])  # excludes generators with empty node
    mTEPES.t      = Set(doc='thermal                 units'    , initialize=[g      for g    in mTEPES.g   if mTEPES.dPar['pRatedLinearOperCost'][g ] >  0.0])
    mTEPES.re     = Set(doc='RES                     units'    , initialize=[g      for g    in mTEPES.g   if mTEPES.dPar['pRatedLinearOperCost'][g ] == 0.0 and mTEPES.dPar['pRatedMaxStorage'][g] == 0.0   and mTEPES.dPar['pProductionFunctionH2'][g ] == 0.0 and mTEPES.dPar['pProductionFunctionHeat'][g ]       == 0.0  and mTEPES.dPar['pProductionFunctionHydro'][g ] == 0.0])
    mTEPES.es     = Set(doc='ESS                     units'    , initialize=[g      for g    in mTEPES.g   if     (mTEPES.dPar['pRatedMaxCharge'][g ] >  0.0 or  mTEPES.dPar['pRatedMaxStorage'][g] >  0.0    or mTEPES.dPar['pProductionFunctionH2'][g ]  > 0.0  or mTEPES.dPar['pProductionFunctionHeat'][g ]        > 0.0) and mTEPES.dPar['pProductionFunctionHydro'][g ] == 0.0])
    mTEPES.h      = Set(doc='hydro                   units'    , initialize=[g      for g    in mTEPES.g                                                                                                      if mTEPES.dPar['pProductionFunctionH2'][g ] == 0.0 and mTEPES.dPar['pProductionFunctionHeat'][g ]       == 0.0  and mTEPES.dPar['pProductionFunctionHydro'][g ]  > 0.0])
    mTEPES.el     = Set(doc='electrolyzer            units'    , initialize=[es     for es   in mTEPES.es                                                                                                     if mTEPES.dPar['pProductionFunctionH2'][es]  > 0.0 and mTEPES.dPar['pProductionFunctionHeat'][es]       == 0.0  and mTEPES.dPar['pProductionFunctionHydro'][es] == 0.0])
    mTEPES.hp     = Set(doc='heat pump & elec boiler units'    , initialize=[es     for es   in mTEPES.es                                                                                                     if mTEPES.dPar['pProductionFunctionH2'][es] == 0.0 and mTEPES.dPar['pProductionFunctionHeat'][es]        > 0.0  and mTEPES.dPar['pProductionFunctionHydro'][es] == 0.0])
    mTEPES.ch     = Set(doc='CHP       & fuel boiler units'    , initialize=[g      for g    in mTEPES.g   if                                                    mTEPES.dPar['pRatedMaxPowerHeat'][g ] > 0.0 and mTEPES.dPar['pProductionFunctionHeat']    [g ] == 0.0])
    mTEPES.bo     = Set(doc='            fuel boiler units'    , initialize=[ch     for ch   in mTEPES.ch  if mTEPES.dPar['pRatedMaxPowerElec']  [ch] == 0.0 and mTEPES.dPar['pRatedMaxPowerHeat'][ch] > 0.0 and mTEPES.dPar['pProductionFunctionHeat']    [ch] == 0.0])
    mTEPES.hh     = Set(doc='        hydrogen boiler units'    , initialize=[bo     for bo   in mTEPES.bo                                                                                                     if mTEPES.dPar['pProductionFunctionH2ToHeat'][bo] >  0.0])
    mTEPES.gc     = Set(doc='candidate               units'    , initialize=[g      for g    in mTEPES.g   if mTEPES.dPar['pGenInvestCost']      [g ] >  0.0])
    mTEPES.gd     = Set(doc='retirement              units'    , initialize=[g      for g    in mTEPES.g   if mTEPES.dPar['pGenRetireCost']      [g ] >  0.0])
    mTEPES.ec     = Set(doc='candidate ESS           units'    , initialize=[es     for es   in mTEPES.es  if mTEPES.dPar['pGenInvestCost']      [es] >  0.0])
    mTEPES.bc     = Set(doc='candidate boiler        units'    , initialize=[bo     for bo   in mTEPES.bo  if mTEPES.dPar['pGenInvestCost']      [bo] >  0.0])
    mTEPES.br     = Set(doc='all input       electric branches', initialize=sBrList        )
    mTEPES.ln     = Set(doc='all input       electric lines'   , initialize=mTEPES.dFrame['dfNetwork'].index)
    if len(mTEPES.ln) != len(mTEPES.dFrame['dfNetwork'].index):
        raise ValueError('### Some electric lines are invalid ', len(mTEPES.ln), len(mTEPES.dFrame['dfNetwork'].index))
    mTEPES.la     = Set(doc='all real        electric lines'   , initialize=[ln     for ln   in mTEPES.ln if mTEPES.dPar['pLineX']              [ln] != 0.0 and mTEPES.dPar['pLineNTCFrw'][ln] > 0.0 and mTEPES.dPar['pLineNTCBck'][ln] > 0.0 and mTEPES.dPar['pElecNetPeriodIni'][ln]  <= mTEPES.p.last() and mTEPES.dPar['pElecNetPeriodFin'][ln]  >= mTEPES.p.first()])
    mTEPES.ls     = Set(doc='all real switch electric lines'   , initialize=[la     for la   in mTEPES.la if mTEPES.dPar['pIndBinLineSwitch']   [la]       ])
    mTEPES.lc     = Set(doc='candidate       electric lines'   , initialize=[la     for la   in mTEPES.la if mTEPES.dPar['pNetFixedCost']       [la] >  0.0])
    mTEPES.cd     = Set(doc='candidate    DC electric lines'   , initialize=[la     for la   in mTEPES.la if mTEPES.dPar['pNetFixedCost']       [la] >  0.0 and mTEPES.dPar['pLineType'][la] == 'DC'])
    mTEPES.ed     = Set(doc='existing     DC electric lines'   , initialize=[la     for la   in mTEPES.la if mTEPES.dPar['pNetFixedCost']       [la] == 0.0 and mTEPES.dPar['pLineType'][la] == 'DC'])
    mTEPES.ll     = Set(doc='loss            electric lines'   , initialize=[la     for la   in mTEPES.la if mTEPES.dPar['pLineLossFactor']     [la] >  0.0 and mTEPES.dPar['pIndBinNetLosses'] > 0 ])
    mTEPES.rf     = Set(doc='reference node'                   , initialize=[mTEPES.dPar['pReferenceNode']])
    mTEPES.gq     = Set(doc='gen    reactive units'            , initialize=[gg     for gg   in mTEPES.gg if mTEPES.dPar['pRMaxReactivePower']  [gg] >  0.0 and                                                                    mTEPES.dPar['pElecGenPeriodIni'][gg]  <= mTEPES.p.last() and mTEPES.dPar['pElecGenPeriodFin'][gg]  >= mTEPES.p.first()])
    mTEPES.sq     = Set(doc='synchr reactive units'            , initialize=[gg     for gg   in mTEPES.gg if mTEPES.dPar['pRMaxReactivePower']  [gg] >  0.0 and mTEPES.dPar['pGenToTechnology'][gg] == 'SynchronousCondenser'  and mTEPES.dPar['pElecGenPeriodIni'][gg]  <= mTEPES.p.last() and mTEPES.dPar['pElecGenPeriodFin'][gg]  >= mTEPES.p.first()])
    mTEPES.sqc    = Set(doc='synchr reactive candidate')
    mTEPES.shc    = Set(doc='shunt           candidate')
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[rs     for rs   in mTEPES.rs if mTEPES.dPar['pRsrInvestCost']      [rs] >  0.0 and                                                                    mTEPES.dPar['pRsrPeriodIni'][rs]      <= mTEPES.p.last() and mTEPES.dPar['pRsrPeriodFin'][rs]      >= mTEPES.p.first()])
    else:
        mTEPES.rn = Set(doc='candidate reservoirs'             , initialize=[])
    if mTEPES.dPar['pIndHydrogen']      == 1:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=mTEPES.dFrame['dfNetworkHydrogen'].index)
        if len(mTEPES.pn) != len(mTEPES.dFrame['dfNetworkHydrogen'].index):
            raise ValueError('### Some hydrogen pipes are invalid ', len(mTEPES.pn), len(mTEPES.dFrame['dfNetworkHydrogen'].index))
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[pn     for pn   in mTEPES.pn if mTEPES.dPar['pH2PipeNTCFrw']       [pn] >  0.0 and mTEPES.dPar['pH2PipeNTCBck'][pn] > 0.0 and                         mTEPES.dPar['pH2PipePeriodIni'][pn]   <= mTEPES.p.last() and mTEPES.dPar['pH2PipePeriodFin'][pn]   >= mTEPES.p.first()])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[pa     for pa   in mTEPES.pa if mTEPES.dPar['pH2PipeFixedCost']    [pa] >  0.0])
        # existing hydrogen pipelines (pe)
        mTEPES.pe = mTEPES.pa - mTEPES.pc
    else:
        mTEPES.pn = Set(doc='all input hydrogen pipes'         , initialize=[])
        mTEPES.pa = Set(doc='all real  hydrogen pipes'         , initialize=[])
        mTEPES.pc = Set(doc='candidate hydrogen pipes'         , initialize=[])

    if mTEPES.dPar['pIndHeat']        == 1:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=mTEPES.dFrame['dfNetworkHeat'].index)
        if len(mTEPES.hn) != len(mTEPES.dFrame['dfNetworkHeat'].index):
            raise ValueError('### Some heat pipes are invalid ', len(mTEPES.hn), len(mTEPES.dFrame['dfNetworkHeat'].index))
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[hn     for hn   in mTEPES.hn   if mTEPES.dPar['pHeatPipeNTCFrw']     [hn] >  0.0 and mTEPES.dPar['pHeatPipeNTCBck'][hn] > 0.0 and mTEPES.dPar['pHeatPipePeriodIni'][hn] <= mTEPES.p.last() and mTEPES.dPar['pHeatPipePeriodFin'][hn] >= mTEPES.p.first()])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[ha     for ha   in mTEPES.ha   if mTEPES.dPar['pHeatPipeFixedCost']  [ha] >  0.0])
        # existing heat pipes (he)
        mTEPES.he = mTEPES.ha - mTEPES.hc
    else:
        mTEPES.hn = Set(doc='all input heat pipes'             , initialize=[])
        mTEPES.ha = Set(doc='all real  heat pipes'             , initialize=[])
        mTEPES.hc = Set(doc='candidate heat pipes'             , initialize=[])

    mTEPES.dPar['pIndBinLinePTDF'] = pd.Series(index=mTEPES.la, data=0.0)                                                              # indicate if the line has a PTDF or not
    if mTEPES.dPar['pIndVarTTC'] == 1:
        mTEPES.dPar['pVariableNTCFrw'] = mTEPES.dPar['pVariableNTCFrw'].reindex(columns=mTEPES.la, fill_value=0.0) * mTEPES.dFrame['dfNetwork']['SecurityFactor']      # variable NTC forward  direction because of the security factor
        mTEPES.dPar['pVariableNTCBck'] = mTEPES.dPar['pVariableNTCBck'].reindex(columns=mTEPES.la, fill_value=0.0) * mTEPES.dFrame['dfNetwork']['SecurityFactor']      # variable NTC backward direction because of the security factor
    if mTEPES.dPar['pIndPTDF'] == 1:
        # get the level_3, level_4, and level_5 from multiindex of pVariablePTDF
        PTDF_columns = mTEPES.dPar['pVariablePTDF'].columns
        PTDF_lines   = PTDF_columns.droplevel([3]).drop_duplicates()
        mTEPES.dPar['pIndBinLinePTDF'].loc[:] = mTEPES.dPar['pIndBinLinePTDF'].index.isin(PTDF_lines).astype(float)

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
    mTEPES.dPar['pStageToLevel'] = mTEPES.dPar['pLevelToStage'].reset_index().set_index(['Period','Scenario','Stage'])['LoadLevel']
    #Filter only valid indices
    mTEPES.dPar['pStageToLevel'] = mTEPES.dPar['pStageToLevel'].loc[mTEPES.dPar['pStageToLevel'].index.isin([(p,s,st) for (p,s) in mTEPES.ps for st in mTEPES.st]) & mTEPES.dPar['pStageToLevel'].isin(mTEPES.n)]
    #Reorder the elements
    mTEPES.dPar['pStageToLevel'] = [(p,sc,st,n) for (p,sc,st),n in mTEPES.dPar['pStageToLevel'].items()]
    mTEPES.s2n = Set(initialize=mTEPES.dPar['pStageToLevel'], doc='Load level to stage')
    # all the stages must have the same duration
    mTEPES.dPar['pStageDuration'] = pd.Series([sum(mTEPES.dPar['pDuration'][p,sc,n] for p,sc,st2,n in mTEPES.s2n if st2 == st) for st in mTEPES.st], index=mTEPES.st)
    # for st in mTEPES.st:
    #     if mTEPES.st.ord(st) > 1 and pStageDuration[st] != pStageDuration[mTEPES.st.prev(st)]:
    #         assert (0 == 1)

    # delete all the load level belonging to stages with duration equal to zero
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.n  = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(mTEPES.dPar['pDuration'][p,sc,nn] for p,sc in mTEPES.ps) > 0])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn for nn in mTEPES.nn if sum(mTEPES.dPar['pDuration'][p,sc,nn] for p,sc in mTEPES.ps) > 0])
    # instrumental sets
    def CreateInstrumentalSets(mTEPES, pIndHydroTopology, pIndHydrogen, pIndHeat, pIndPTDF) -> None:
        '''
                Create mTEPES instrumental sets.

                This function takes an mTEPES instance and adds instrumental sets which will be used later.

                Parameters:
                    mTEPES: The instance of mTEPES.

                Returns:
                    None: Sets are added directly to the mTEPES object.
                '''
        mTEPES.pg        = Set(initialize = [(p,     g       ) for p,     g        in mTEPES.p  *mTEPES.g   if mTEPES.dPar['pElecGenPeriodIni'][g ] <= p and mTEPES.dPar['pElecGenPeriodFin'][g ] >= p])
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
        mTEPES.pla       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.la  if mTEPES.dPar['pElecNetPeriodIni'][ni,nf,cc] <= p and mTEPES.dPar['pElecNetPeriodFin'][ni,nf,cc] >= p])
        mTEPES.plc       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.lc  if (p,ni,nf,cc) in mTEPES.pla])
        mTEPES.pll       = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ll  if (p,ni,nf,cc) in mTEPES.pla])

        mTEPES.psc       = Set(initialize = [(p,sc     )       for p,sc            in mTEPES.p  *mTEPES.sc])
        mTEPES.psg       = Set(initialize = [(p,sc,  g )       for p,sc,  g        in mTEPES.ps *mTEPES.g   if (p,g )  in mTEPES.pg  ])
        mTEPES.psnr      = Set(initialize = [(p,sc,  nr)       for p,sc,  nr       in mTEPES.ps *mTEPES.nr  if (p,nr)  in mTEPES.pnr ])
        mTEPES.pses      = Set(initialize = [(p,sc,  es)       for p,sc,  es       in mTEPES.ps *mTEPES.es  if (p,es)  in mTEPES.pes ])
        mTEPES.pseh      = Set(initialize = [(p,sc,  eh)       for p,sc,  eh       in mTEPES.ps *mTEPES.eh  if (p,eh)  in mTEPES.peh ])
        mTEPES.psn       = Set(initialize = [(p,sc,n   )       for p,sc,n          in mTEPES.ps *mTEPES.n                            ])
        mTEPES.psng      = Set(initialize = [(p,sc,n,g )       for p,sc,n,g        in mTEPES.psn*mTEPES.g   if (p,g )  in mTEPES.pg  ])
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

        mTEPES.psnla     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.la  if (p,ni,nf,cc) in mTEPES.pla ])
        mTEPES.psnle     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.le  if (p,ni,nf,cc) in mTEPES.pla ])
        mTEPES.psnll     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ll  if (p,ni,nf,cc) in mTEPES.pll ])
        mTEPES.psnls     = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ls  if (p,ni,nf,cc) in mTEPES.pla ])

        mTEPES.psnehc    = Set(initialize = [(p,sc,n,eh)       for p,sc,n,eh       in mTEPES.psneh          if mTEPES.dPar['pRatedMaxCharge'][eh] > 0.0 ])

        if pIndHydroTopology == 1:
            mTEPES.prs   = Set(initialize = [(p,     rs)       for p,     rs       in mTEPES.p  *mTEPES.rs if mTEPES.dPar['pRsrPeriodIni'][rs] <= p and mTEPES.dPar['pRsrPeriodFin'][rs] >= p])
            mTEPES.prc   = Set(initialize = [(p,     rc)       for p,     rc       in mTEPES.p  *mTEPES.rn if (p,rc) in mTEPES.prs])
            mTEPES.psrs  = Set(initialize = [(p,sc,  rs)       for p,sc,  rs       in mTEPES.ps *mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnh  = Set(initialize = [(p,sc,n,h )       for p,sc,n,h        in mTEPES.psn*mTEPES.h  if (p,h ) in mTEPES.ph ])
            mTEPES.psnrs = Set(initialize = [(p,sc,n,rs)       for p,sc,n,rs       in mTEPES.psn*mTEPES.rs if (p,rs) in mTEPES.prs])
            mTEPES.psnrc = Set(initialize = [(p,sc,n,rc)       for p,sc,n,rc       in mTEPES.psn*mTEPES.rn if (p,rc) in mTEPES.prc])
        else:
            mTEPES.prc   = []

        if pIndHydrogen == 1:
            mTEPES.ppa   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pa if mTEPES.dPar['pH2PipePeriodIni'][ni,nf,cc] <= p and mTEPES.dPar['pH2PipePeriodFin'][ni,nf,cc] >= p])
            mTEPES.ppc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pn if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpa = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pa if (p,ni,nf,cc) in mTEPES.ppa])
            mTEPES.psnpe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.pe if (p,ni,nf,cc) in mTEPES.ppa])
        else:
            mTEPES.ppc   = Set(initialize = [])

        if pIndHeat == 1:
            mTEPES.pha   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.ha if mTEPES.dPar['pHeatPipePeriodIni'][ni,nf,cc] <= p and mTEPES.dPar['pHeatPipePeriodFin'][ni,nf,cc] >= p])
            mTEPES.phc   = Set(initialize = [(p,     ni,nf,cc) for p,     ni,nf,cc in mTEPES.p  *mTEPES.hc if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhn = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.hn if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnha = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.ha if (p,ni,nf,cc) in mTEPES.pha])
            mTEPES.psnhe = Set(initialize = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psn*mTEPES.he if (p,ni,nf,cc) in mTEPES.pha])
        else:
            mTEPES.phc   = Set(initialize = [])

        if pIndPTDF == 1:
            mTEPES.psnland = Set(initialize = [(p,sc,n,ni,nf,cc,nd) for p,sc,n,ni,nf,cc,nd in mTEPES.psnla*mTEPES.nd if (ni,nf,cc,nd) in mTEPES.dPar['pVariablePTDF'].columns])

        # assigning a node to an area
        mTEPES.ndar = Set(initialize = [(nd,ar) for (nd,zn,ar) in mTEPES.ndzn*mTEPES.ar if (zn,ar) in mTEPES.znar])

        # assigning a line to an area. Both nodes are in the same area. Cross-area lines are not included
        mTEPES.laar = Set(initialize = [(ni,nf,cc,ar) for ni,nf,cc,ar in mTEPES.la*mTEPES.ar if (ni,ar) in mTEPES.ndar and (nf,ar) in mTEPES.ndar])


    CreateInstrumentalSets(mTEPES, mTEPES.dPar['pIndHydroTopology'], mTEPES.dPar['pIndHydrogen'], mTEPES.dPar['pIndHeat'], mTEPES.dPar['pIndPTDF'])

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

    mTEPES.dPar['pIndBinUnitInvest']         = mTEPES.dPar['pIndBinUnitInvest'].map    (idxDict)
    mTEPES.dPar['pIndBinUnitRetire']         = mTEPES.dPar['pIndBinUnitRetire'].map    (idxDict)
    mTEPES.dPar['pIndBinUnitCommit']         = mTEPES.dPar['pIndBinUnitCommit'].map    (idxDict)
    mTEPES.dPar['pIndBinStorInvest']         = mTEPES.dPar['pIndBinStorInvest'].map    (idxDict)
    mTEPES.dPar['pIndBinLineInvest']         = mTEPES.dPar['pIndBinLineInvest'].map    (idxDict)
    mTEPES.dPar['pIndBinLineSwitch']         = mTEPES.dPar['pIndBinLineSwitch'].map    (idxDict)
    # mTEPES.dPar['pIndOperReserve']           = mTEPES.dPar['pIndOperReserve'].map      (idxDict)
    mTEPES.dPar['pIndOutflowIncomp']         = mTEPES.dPar['pIndOutflowIncomp'].map    (idxDict)
    mTEPES.dPar['pMustRun']                  = mTEPES.dPar['pMustRun'].map             (idxDict)

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
    mTEPES.dPar['pIndOperReserveGen'], mTEPES.dPar['pIndOperReserveCon'] = zip(*mTEPES.dPar['pIndOperReserve'].map(split_and_map))

    mTEPES.dPar['pIndOperReserveGen'] = pd.Series(mTEPES.dPar['pIndOperReserveGen'], index=mTEPES.dPar['pIndOperReserve'].index)
    mTEPES.dPar['pIndOperReserveCon'] = pd.Series(mTEPES.dPar['pIndOperReserveCon'], index=mTEPES.dPar['pIndOperReserve'].index)

    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pIndBinRsrvInvest']     = mTEPES.dPar['pIndBinRsrvInvest'].map    (idxDict)

    if mTEPES.dPar['pIndHydrogen'] == 1:
        mTEPES.dPar['pIndBinH2PipeInvest']   = mTEPES.dPar['pIndBinH2PipeInvest'].map  (idxDict)

    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.dPar['pIndBinHeatPipeInvest'] = mTEPES.dPar['pIndBinHeatPipeInvest'].map(idxDict)

    # define AC existing  lines     non-switchable lines
    mTEPES.lea = Set(doc='AC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  mTEPES.dPar['pIndBinLineSwitch'][le] == 0                                            and not mTEPES.dPar['pLineType'][le] == 'DC'])
    # define AC candidate lines and     switchable lines
    mTEPES.lca = Set(doc='AC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (mTEPES.dPar['pIndBinLineSwitch'][la] == 1 or mTEPES.dPar['pNetFixedCost'][la] > 0.0) and not mTEPES.dPar['pLineType'][la] == 'DC'])

    mTEPES.laa = mTEPES.lea | mTEPES.lca

    # define DC existing  lines     non-switchable lines
    mTEPES.led = Set(doc='DC existing  lines and non-switchable lines', initialize=[le for le in mTEPES.le if  mTEPES.dPar['pIndBinLineSwitch'][le] == 0                                            and     mTEPES.dPar['pLineType'][le] == 'DC'])
    # define DC candidate lines and     switchable lines
    mTEPES.lcd = Set(doc='DC candidate lines and     switchable lines', initialize=[la for la in mTEPES.la if (mTEPES.dPar['pIndBinLineSwitch'][la] == 1 or mTEPES.dPar['pNetFixedCost'][la] > 0.0) and     mTEPES.dPar['pLineType'][la] == 'DC'])

    mTEPES.lad = mTEPES.led | mTEPES.lcd

    # line type
    mTEPES.dPar['pLineType'] = mTEPES.dPar['pLineType'].reset_index().set_index(['InitialNode', 'FinalNode', 'Circuit', 'LineType'])

    mTEPES.pLineType = Set(initialize=mTEPES.dPar['pLineType'].index, doc='line type')

    if mTEPES.dPar['pAnnualDiscountRate'] == 0.0:
        mTEPES.dPar['pDiscountedWeight'] = pd.Series([                                           mTEPES.dPar['pPeriodWeight'][p]                                                                                                                                                              for p in mTEPES.p], index=mTEPES.p)
    else:
        mTEPES.dPar['pDiscountedWeight'] = pd.Series([((1.0+mTEPES.dPar['pAnnualDiscountRate'])**mTEPES.dPar['pPeriodWeight'][p]-1.0) / (mTEPES.dPar['pAnnualDiscountRate']*(1.0+mTEPES.dPar['pAnnualDiscountRate'])**(mTEPES.dPar['pPeriodWeight'][p]-1+p-mTEPES.dPar['pEconomicBaseYear'])) for p in mTEPES.p], index=mTEPES.p)

    mTEPES.pLoadLevelWeight = Param(mTEPES.psn, initialize=0.0, within=NonNegativeReals, doc='Load level weight', mutable=True)
    for p,sc,st,n in mTEPES.s2n:
        mTEPES.pLoadLevelWeight[p,sc,n] = mTEPES.dPar['pStageWeight'][st]

    #%% inverse index node to generator
    mTEPES.dPar['pNodeToGen'] = mTEPES.dPar['pGenToNode'].reset_index().set_index('Node').set_axis(['Generator'], axis=1)[['Generator']]
    mTEPES.dPar['pNodeToGen'] = mTEPES.dPar['pNodeToGen'].loc[mTEPES.dPar['pNodeToGen']['Generator'].isin(mTEPES.g)].reset_index().set_index(['Node', 'Generator'])

    mTEPES.n2g = Set(initialize=mTEPES.dPar['pNodeToGen'].index, doc='node   to generator')

    mTEPES.z2g = Set(doc='zone   to generator', initialize=[(zn,g) for (nd,g,zn      ) in mTEPES.n2g*mTEPES.zn             if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.a2g = Set(doc='area   to generator', initialize=[(ar,g) for (nd,g,zn,ar   ) in mTEPES.n2g*mTEPES.znar           if (nd,zn) in mTEPES.ndzn                           ])
    mTEPES.r2g = Set(doc='region to generator', initialize=[(rg,g) for (nd,g,zn,ar,rg) in mTEPES.n2g*mTEPES.znar*mTEPES.rg if (nd,zn) in mTEPES.ndzn and [ar,rg] in mTEPES.arrg])

    # mTEPES.z2g  = Set(initialize = [(zn,g) for zn,g in mTEPES.zn*mTEPES.g if (zn,g) in pZone2Gen])

    #%% inverse index generator to technology
    mTEPES.dPar['pTechnologyToGen'] = mTEPES.dPar['pGenToTechnology'].reset_index().set_index('Technology').set_axis(['Generator'], axis=1)[['Generator']]
    mTEPES.dPar['pTechnologyToGen'] = mTEPES.dPar['pTechnologyToGen'].loc[mTEPES.dPar['pTechnologyToGen']['Generator'].isin(mTEPES.g)].reset_index().set_index(['Technology', 'Generator'])

    mTEPES.t2g = Set(initialize=mTEPES.dPar['pTechnologyToGen'].index, doc='technology to generator')

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

    # Create mutually exclusive groups
    # Store in a group-generator dictionary all the relevant data
    group_dict = {}
    for generator, groups in mTEPES.dPar['pGenToExclusiveGen'].items():
        if groups != 0.0:
            for group in str(groups).split('|'):
                group_dict.setdefault(group, []).append(generator)

    # These sets store all groups and the generators in them
    mTEPES.ExclusiveGroups = Set(initialize=list(group_dict.keys()))
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
    mTEPES.ExclusiveGroupsYearly = Set(initialize=list(group_dict_yearly.keys()))
    mTEPES.GeneratorsInYearlyGroup = Set(mTEPES.ExclusiveGroupsYearly, initialize=group_dict_yearly)

    mTEPES.ExclusiveGroupsHourly = Set(initialize=list(group_dict_hourly.keys()))
    mTEPES.GeneratorsInHourlyGroup = Set(mTEPES.ExclusiveGroupsHourly, initialize=group_dict_hourly)

    # All exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGenerators = Set(initialize=sorted(sum(group_dict.values(), [])))
    # All yearly exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGeneratorsYearly = Set(initialize=sorted(sum(group_dict_yearly.values(), [])))
    # All hourly exclusive generators (sorting to ensure deterministic behavior)
    mTEPES.ExclusiveGeneratorsHourly = Set(initialize=sorted(sum(group_dict_hourly.values(), [])))

    # minimum and maximum variable power, charge, and storage capacity
    mTEPES.dPar['pMinPowerElec']  = mTEPES.dPar['pVariableMinPowerElec'].replace(0.0, mTEPES.dPar['pRatedMinPowerElec'])
    mTEPES.dPar['pMaxPowerElec']  = mTEPES.dPar['pVariableMaxPowerElec'].replace(0.0, mTEPES.dPar['pRatedMaxPowerElec'])
    mTEPES.dPar['pMinCharge']     = mTEPES.dPar['pVariableMinCharge'].replace   (0.0, mTEPES.dPar['pRatedMinCharge']   )
    mTEPES.dPar['pMaxCharge']     = mTEPES.dPar['pVariableMaxCharge'].replace   (0.0, mTEPES.dPar['pRatedMaxCharge']   )
    mTEPES.dPar['pMinStorage']    = mTEPES.dPar['pVariableMinStorage'].replace  (0.0, mTEPES.dPar['pRatedMinStorage']  )
    mTEPES.dPar['pMaxStorage']    = mTEPES.dPar['pVariableMaxStorage'].replace  (0.0, mTEPES.dPar['pRatedMaxStorage']  )
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pMinVolume'] = mTEPES.dPar['pVariableMinVolume'].replace   (0.0, mTEPES.dPar['pRatedMinVolume']   )
        mTEPES.dPar['pMaxVolume'] = mTEPES.dPar['pVariableMaxVolume'].replace   (0.0, mTEPES.dPar['pRatedMaxVolume']   )

    mTEPES.dPar['pMinPowerElec']  = mTEPES.dPar['pMinPowerElec'].where(mTEPES.dPar['pMinPowerElec'] > 0.0, 0.0)
    mTEPES.dPar['pMaxPowerElec']  = mTEPES.dPar['pMaxPowerElec'].where(mTEPES.dPar['pMaxPowerElec'] > 0.0, 0.0)
    mTEPES.dPar['pMinCharge']     = mTEPES.dPar['pMinCharge'].where   (mTEPES.dPar['pMinCharge']    > 0.0, 0.0)
    mTEPES.dPar['pMaxCharge']     = mTEPES.dPar['pMaxCharge'].where   (mTEPES.dPar['pMaxCharge']    > 0.0, 0.0)
    mTEPES.dPar['pMinStorage']    = mTEPES.dPar['pMinStorage'].where  (mTEPES.dPar['pMinStorage']   > 0.0, 0.0)
    mTEPES.dPar['pMaxStorage']    = mTEPES.dPar['pMaxStorage'].where  (mTEPES.dPar['pMaxStorage']   > 0.0, 0.0)
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pMinVolume'] = mTEPES.dPar['pMinVolume'].where   (mTEPES.dPar['pMinVolume']    > 0.0, 0.0)
        mTEPES.dPar['pMaxVolume'] = mTEPES.dPar['pMaxVolume'].where   (mTEPES.dPar['pMaxVolume']    > 0.0, 0.0)

    # fuel term and constant term variable cost
    mTEPES.dPar['pVariableFuelCost'] = mTEPES.dPar  ['pVariableFuelCost'].replace(0.0, mTEPES.dFrame['dfGeneration']['FuelCost'])
    mTEPES.dPar['pLinearVarCost']    = mTEPES.dFrame['dfGeneration']['LinearTerm'  ] * 1e-3 * mTEPES.dPar['pVariableFuelCost'] + mTEPES.dFrame['dfGeneration']['OMVariableCost'] * 1e-3
    mTEPES.dPar['pConstantVarCost']  = mTEPES.dFrame['dfGeneration']['ConstantTerm'] * 1e-6 * mTEPES.dPar['pVariableFuelCost']
    mTEPES.dPar['pLinearVarCost']    = mTEPES.dPar  ['pLinearVarCost'].reindex  (sorted(mTEPES.dPar['pLinearVarCost'].columns  ), axis=1)
    mTEPES.dPar['pConstantVarCost']  = mTEPES.dPar  ['pConstantVarCost'].reindex(sorted(mTEPES.dPar['pConstantVarCost'].columns), axis=1)

    # variable emission cost [M€/GWh]
    mTEPES.dPar['pVariableEmissionCost'] = mTEPES.dPar['pVariableEmissionCost'].replace(0.0, mTEPES.dPar['pCO2Cost']) #[€/tCO2]
    mTEPES.dPar['pEmissionVarCost']      = mTEPES.dPar['pEmissionRate'] * 1e-3 * mTEPES.dPar['pVariableEmissionCost']                 #[M€/GWh] = [tCO2/MWh] * 1e-3 * [€/tCO2]
    mTEPES.dPar['pEmissionVarCost']      = mTEPES.dPar['pEmissionVarCost'].reindex(sorted(mTEPES.dPar['pEmissionVarCost'].columns), axis=1)

    # minimum up- and downtime and maximum shift time converted to an integer number of time steps
    mTEPES.dPar['pUpTime']     = round(mTEPES.dPar['pUpTime']    /mTEPES.dPar['pTimeStep']).astype('int')
    mTEPES.dPar['pDwTime']     = round(mTEPES.dPar['pDwTime']    /mTEPES.dPar['pTimeStep']).astype('int')
    mTEPES.dPar['pStableTime'] = round(mTEPES.dPar['pStableTime']/mTEPES.dPar['pTimeStep']).astype('int')
    mTEPES.dPar['pShiftTime']  = round(mTEPES.dPar['pShiftTime'] /mTEPES.dPar['pTimeStep']).astype('int')

    # %% definition of the time-steps leap to observe the stored energy at an ESS
    idxCycle            = dict()
    idxCycle[0        ] = 1
    idxCycle[0.0      ] = 1
    idxCycle['Hourly' ] = 1
    idxCycle['Daily'  ] = 1
    idxCycle['Weekly' ] = round(  24/mTEPES.dPar['pTimeStep'])
    idxCycle['Monthly'] = round( 168/mTEPES.dPar['pTimeStep'])
    idxCycle['Yearly' ] = round( 672/mTEPES.dPar['pTimeStep'])

    idxOutflows            = dict()
    idxOutflows[0        ] = 1
    idxOutflows[0.0      ] = 1
    idxOutflows['Hourly' ] = 1
    idxOutflows['Daily'  ] = round(  24/mTEPES.dPar['pTimeStep'])
    idxOutflows['Weekly' ] = round( 168/mTEPES.dPar['pTimeStep'])
    idxOutflows['Monthly'] = round( 672/mTEPES.dPar['pTimeStep'])
    idxOutflows['Yearly' ] = round(8736/mTEPES.dPar['pTimeStep'])

    idxEnergy            = dict()
    idxEnergy[0        ] = 1
    idxEnergy[0.0      ] = 1
    idxEnergy['Hourly' ] = 1
    idxEnergy['Daily'  ] = round(  24/mTEPES.dPar['pTimeStep'])
    idxEnergy['Weekly' ] = round( 168/mTEPES.dPar['pTimeStep'])
    idxEnergy['Monthly'] = round( 672/mTEPES.dPar['pTimeStep'])
    idxEnergy['Yearly' ] = round(8736/mTEPES.dPar['pTimeStep'])

    mTEPES.dPar['pStorageTimeStep']  = mTEPES.dPar['pStorageType' ].map(idxCycle                                                                                                             ).astype('int')
    mTEPES.dPar['pOutflowsTimeStep'] = mTEPES.dPar['pOutflowsType'].map(idxOutflows).where(mTEPES.dPar['pEnergyOutflows'].sum()                                              > 0.0, other = 1).astype('int')
    mTEPES.dPar['pEnergyTimeStep']   = mTEPES.dPar['pEnergyType'  ].map(idxEnergy  ).where(mTEPES.dPar['pVariableMinEnergy'].sum() + mTEPES.dPar['pVariableMaxEnergy'].sum() > 0.0, other = 1).astype('int')

    mTEPES.dPar['pStorageTimeStep']  = pd.concat([mTEPES.dPar['pStorageTimeStep'], mTEPES.dPar['pOutflowsTimeStep'], mTEPES.dPar['pEnergyTimeStep']], axis=1).min(axis=1)
    # cycle time step can't exceed the stage duration
    mTEPES.dPar['pStorageTimeStep']  = mTEPES.dPar['pStorageTimeStep'].where(mTEPES.dPar['pStorageTimeStep'] <= mTEPES.dPar['pStageDuration'].min(), mTEPES.dPar['pStageDuration'].min())

    if mTEPES.dPar['pIndHydroTopology'] == 1:
        # %% definition of the time-steps leap to observe the stored energy at a reservoir
        idxCycleRsr            = dict()
        idxCycleRsr[0        ] = 1
        idxCycleRsr[0.0      ] = 1
        idxCycleRsr['Hourly' ] = 1
        idxCycleRsr['Daily'  ] = 1
        idxCycleRsr['Weekly' ] = round(  24/mTEPES.dPar['pTimeStep'])
        idxCycleRsr['Monthly'] = round( 168/mTEPES.dPar['pTimeStep'])
        idxCycleRsr['Yearly' ] = round( 672/mTEPES.dPar['pTimeStep'])

        idxWaterOut            = dict()
        idxWaterOut[0        ] = 1
        idxWaterOut[0.0      ] = 1
        idxWaterOut['Hourly' ] = 1
        idxWaterOut['Daily'  ] = round(  24/mTEPES.dPar['pTimeStep'])
        idxWaterOut['Weekly' ] = round( 168/mTEPES.dPar['pTimeStep'])
        idxWaterOut['Monthly'] = round( 672/mTEPES.dPar['pTimeStep'])
        idxWaterOut['Yearly' ] = round(8736/mTEPES.dPar['pTimeStep'])

        mTEPES.dPar['pCycleRsrTimeStep'] = mTEPES.dPar['pReservoirType'].map(idxCycleRsr).astype('int')
        mTEPES.dPar['pWaterOutTimeStep'] = mTEPES.dPar['pWaterOutfType'].map(idxWaterOut).astype('int')

        mTEPES.dPar['pReservoirTimeStep'] = pd.concat([mTEPES.dPar['pCycleRsrTimeStep'], mTEPES.dPar['pWaterOutTimeStep']], axis=1).min(axis=1)
        # cycle water step can't exceed the stage duration
        mTEPES.dPar['pReservoirTimeStep'] = mTEPES.dPar['pReservoirTimeStep'].where(mTEPES.dPar['pReservoirTimeStep'] <= mTEPES.dPar['pStageDuration'].min(), mTEPES.dPar['pStageDuration'].min())

    # initial inventory must be between minimum and maximum
    mTEPES.dPar['pInitialInventory']  = mTEPES.dPar['pInitialInventory'].where(mTEPES.dPar['pInitialInventory'] > mTEPES.dPar['pRatedMinStorage'], mTEPES.dPar['pRatedMinStorage'])
    mTEPES.dPar['pInitialInventory']  = mTEPES.dPar['pInitialInventory'].where(mTEPES.dPar['pInitialInventory'] < mTEPES.dPar['pRatedMaxStorage'], mTEPES.dPar['pRatedMaxStorage'])
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pInitialVolume'] = mTEPES.dPar['pInitialVolume'].where   (mTEPES.dPar['pInitialVolume']    > mTEPES.dPar['pRatedMinVolume'],  mTEPES.dPar['pRatedMinVolume'] )
        mTEPES.dPar['pInitialVolume'] = mTEPES.dPar['pInitialVolume'].where   (mTEPES.dPar['pInitialVolume']    < mTEPES.dPar['pRatedMaxVolume'],  mTEPES.dPar['pRatedMaxVolume'] )

    # initial inventory of the candidate storage units equal to its maximum capacity if the storage capacity is linked to the investment decision
    mTEPES.dPar['pInitialInventory'].update(pd.Series([mTEPES.dPar['pInitialInventory'][ec] if mTEPES.dPar['pIndBinStorInvest'][ec] == 0 else mTEPES.dPar['pRatedMaxStorage'][ec] for ec in mTEPES.ec], index=mTEPES.ec, dtype='float64'))

    # parameter that allows the initial inventory to change with load level
    mTEPES.dPar['pIniInventory']  = pd.DataFrame([mTEPES.dPar['pInitialInventory']]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.es)
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pIniVolume'] = pd.DataFrame([mTEPES.dPar['pInitialVolume']   ]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.rs)

    # initial inventory must be between minimum and maximum
    for p,sc,n,es in mTEPES.psnes:
        if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.dPar['pStorageTimeStep'][es]:
            if  mTEPES.dPar['pIniInventory'][es].loc[p,sc,n] < mTEPES.dPar['pMinStorage'][es].loc[p,sc,n]:
                mTEPES.dPar['pIniInventory'][es].loc[p,sc,n] = mTEPES.dPar['pMinStorage'][es].loc[p,sc,n]
                print('### Initial inventory lower than minimum storage ',   p, sc, st, es)
            if  mTEPES.dPar['pIniInventory'][es].loc[p,sc,n] > mTEPES.dPar['pMaxStorage'][es].loc[p,sc,n]:
                mTEPES.dPar['pIniInventory'][es].loc[p,sc,n] = mTEPES.dPar['pMaxStorage'][es].loc[p,sc,n]
                print('### Initial inventory greater than maximum storage ', p, sc, st, es)
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        for p,sc,n,rs in mTEPES.psnrs:
            if (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.dPar['pReservoirTimeStep'][rs]:
                if  mTEPES.dPar['pIniVolume'][rs].loc[p,sc,n] < mTEPES.dPar['pMinVolume'][rs].loc[p,sc,n]:
                    mTEPES.dPar['pIniVolume'][rs].loc[p,sc,n] = mTEPES.dPar['pMinVolume'][rs].loc[p,sc,n]
                    print('### Initial volume lower than minimum volume ',   p, sc, st, rs)
                if  mTEPES.dPar['pIniVolume'][rs].loc[p,sc,n] > mTEPES.dPar['pMaxVolume'][rs].loc[p,sc,n]:
                    mTEPES.dPar['pIniVolume'][rs].loc[p,sc,n] = mTEPES.dPar['pMaxVolume'][rs].loc[p,sc,n]
                    print('### Initial volume greater than maximum volume ', p, sc, st, rs)

    # drop load levels with duration 0
    mTEPES.dPar['pDuration']            = mTEPES.dPar['pDuration'].loc            [mTEPES.psn  ]
    mTEPES.dPar['pDemandElec']          = mTEPES.dPar['pDemandElec'].loc          [mTEPES.psn  ]
    mTEPES.dPar['pSystemInertia']       = mTEPES.dPar['pSystemInertia'].loc       [mTEPES.psnar]
    mTEPES.dPar['pOperReserveUp']       = mTEPES.dPar['pOperReserveUp'].loc       [mTEPES.psnar]
    mTEPES.dPar['pOperReserveDw']       = mTEPES.dPar['pOperReserveDw'].loc       [mTEPES.psnar]
    mTEPES.dPar['pMinPowerElec']        = mTEPES.dPar['pMinPowerElec'].loc        [mTEPES.psn  ]
    mTEPES.dPar['pMaxPowerElec']        = mTEPES.dPar['pMaxPowerElec'].loc        [mTEPES.psn  ]
    mTEPES.dPar['pMinCharge']           = mTEPES.dPar['pMinCharge'].loc           [mTEPES.psn  ]
    mTEPES.dPar['pMaxCharge']           = mTEPES.dPar['pMaxCharge'].loc           [mTEPES.psn  ]
    mTEPES.dPar['pEnergyInflows']       = mTEPES.dPar['pEnergyInflows'].loc       [mTEPES.psn  ]
    mTEPES.dPar['pEnergyOutflows']      = mTEPES.dPar['pEnergyOutflows'].loc      [mTEPES.psn  ]
    mTEPES.dPar['pIniInventory']        = mTEPES.dPar['pIniInventory'].loc        [mTEPES.psn  ]
    mTEPES.dPar['pMinStorage']          = mTEPES.dPar['pMinStorage'].loc          [mTEPES.psn  ]
    mTEPES.dPar['pMaxStorage']          = mTEPES.dPar['pMaxStorage'].loc          [mTEPES.psn  ]
    mTEPES.dPar['pVariableMaxEnergy']   = mTEPES.dPar['pVariableMaxEnergy'].loc   [mTEPES.psn  ]
    mTEPES.dPar['pVariableMinEnergy']   = mTEPES.dPar['pVariableMinEnergy'].loc   [mTEPES.psn  ]
    mTEPES.dPar['pLinearVarCost']       = mTEPES.dPar['pLinearVarCost'].loc       [mTEPES.psn  ]
    mTEPES.dPar['pConstantVarCost']     = mTEPES.dPar['pConstantVarCost'].loc     [mTEPES.psn  ]
    mTEPES.dPar['pEmissionVarCost']     = mTEPES.dPar['pEmissionVarCost'].loc     [mTEPES.psn  ]

    mTEPES.dPar['pRatedLinearOperCost'] = mTEPES.dPar['pRatedLinearFuelCost'].loc [mTEPES.g    ]
    mTEPES.dPar['pRatedLinearVarCost']  = mTEPES.dPar['pRatedLinearFuelCost'].loc [mTEPES.g    ]

    # drop generators not es
    mTEPES.dPar['pEfficiency']          = mTEPES.dPar['pEfficiency'].loc          [mTEPES.eh   ]
    mTEPES.dPar['pStorageTimeStep']     = mTEPES.dPar['pStorageTimeStep'].loc     [mTEPES.es   ]
    mTEPES.dPar['pOutflowsTimeStep']    = mTEPES.dPar['pOutflowsTimeStep'].loc    [mTEPES.es   ]
    mTEPES.dPar['pStorageType']         = mTEPES.dPar['pStorageType'].loc         [mTEPES.es   ]

    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pHydroInflows']    = mTEPES.dPar['pHydroInflows'].loc        [mTEPES.psn  ]
        mTEPES.dPar['pHydroOutflows']   = mTEPES.dPar['pHydroOutflows'].loc       [mTEPES.psn  ]
        mTEPES.dPar['pIniVolume']       = mTEPES.dPar['pIniVolume'].loc           [mTEPES.psn  ]
        mTEPES.dPar['pMinVolume']       = mTEPES.dPar['pMinVolume'].loc           [mTEPES.psn  ]
        mTEPES.dPar['pMaxVolume']       = mTEPES.dPar['pMaxVolume'].loc           [mTEPES.psn  ]
    if mTEPES.dPar['pIndHydrogen'] == 1:
        mTEPES.dPar['pDemandH2']        = mTEPES.dPar['pDemandH2'].loc            [mTEPES.psn  ]
        mTEPES.dPar['pDemandH2Abs']     = mTEPES.dPar['pDemandH2'].where  (mTEPES.dPar['pDemandH2']   > 0.0, 0.0)
    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.dPar['pDemandHeat']      = mTEPES.dPar['pDemandHeat'].loc          [mTEPES.psn  ]
        mTEPES.dPar['pDemandHeatAbs']   = mTEPES.dPar['pDemandHeat'].where(mTEPES.dPar['pDemandHeat'] > 0.0, 0.0)

    if mTEPES.dPar['pIndVarTTC'] == 1:
        mTEPES.dPar['pVariableNTCFrw']  = mTEPES.dPar['pVariableNTCFrw'].loc      [mTEPES.psn]
        mTEPES.dPar['pVariableNTCBck']  = mTEPES.dPar['pVariableNTCBck'].loc      [mTEPES.psn]
    if mTEPES.dPar['pIndPTDF'] == 1:
        mTEPES.dPar['pVariablePTDF']    = mTEPES.dPar['pVariablePTDF'].loc        [mTEPES.psn]

    # separate positive and negative demands to avoid converting negative values to 0
    mTEPES.dPar['pDemandElecPos']       = mTEPES.dPar['pDemandElec'].where(mTEPES.dPar['pDemandElec'] >= 0.0, 0.0)
    mTEPES.dPar['pDemandElecNeg']       = mTEPES.dPar['pDemandElec'].where(mTEPES.dPar['pDemandElec'] <  0.0, 0.0)
    # mTEPES.dPar['pDemandElecAbs']       = mTEPES.dPar['pDemandElec'].where(mTEPES.dPar['pDemandElec'] >  0.0, 0.0)

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
    mTEPES.dPar['pDemandElecPeak']          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    mTEPES.dPar['pDemandHeatPeak']          = pd.Series([0.0 for p,ar in mTEPES.par], index=mTEPES.par)
    for p,ar in mTEPES.par:
        # values < 1e-5 times the maximum demand for each area (an area is related to operating reserves procurement, i.e., country) are converted to 0
        mTEPES.dPar['pDemandElecPeak'][p,ar] = mTEPES.dPar['pDemandElec'].loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
        mTEPES.dPar['pEpsilonElec']          = mTEPES.dPar['pDemandElecPeak'][p,ar]*1e-5

        # these parameters are in GW
        mTEPES.dPar['pDemandElecPos']     [mTEPES.dPar['pDemandElecPos'] [[nd for nd in d2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
        mTEPES.dPar['pDemandElecNeg']     [mTEPES.dPar['pDemandElecNeg'] [[nd for nd in d2a[ar]]] > -mTEPES.dPar['pEpsilonElec']] = 0.0
        mTEPES.dPar['pSystemInertia']     [mTEPES.dPar['pSystemInertia'] [[                 ar ]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
        mTEPES.dPar['pOperReserveUp']     [mTEPES.dPar['pOperReserveUp'] [[                 ar ]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
        mTEPES.dPar['pOperReserveDw']     [mTEPES.dPar['pOperReserveDw'] [[                 ar ]] <  mTEPES.dPar['pEpsilonElec']] = 0.0

        if g2a[ar]:
            mTEPES.dPar['pMinPowerElec']  [mTEPES.dPar['pMinPowerElec']  [[g  for  g in g2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pMaxPowerElec']  [mTEPES.dPar['pMaxPowerElec']  [[g  for  g in g2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pMinCharge']     [mTEPES.dPar['pMinCharge']     [[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pMaxCharge']     [mTEPES.dPar['pMaxCharge']     [[eh for eh in g2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pEnergyInflows'] [mTEPES.dPar['pEnergyInflows'] [[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pEnergyOutflows'][mTEPES.dPar['pEnergyOutflows'][[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            # these parameters are in GWh
            mTEPES.dPar['pMinStorage']    [mTEPES.dPar['pMinStorage']    [[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pMaxStorage']    [mTEPES.dPar['pMaxStorage']    [[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pIniInventory']  [mTEPES.dPar['pIniInventory']  [[es for es in e2a[ar]]] <  mTEPES.dPar['pEpsilonElec']] = 0.0

            if mTEPES.dPar['pIndHydroTopology'] == 1:
                mTEPES.dPar['pMinVolume']    [mTEPES.dPar['pMinVolume']    [[rs for rs in r2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0
                mTEPES.dPar['pMaxVolume']    [mTEPES.dPar['pMaxVolume']    [[rs for rs in r2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0
                mTEPES.dPar['pHydroInflows'] [mTEPES.dPar['pHydroInflows'] [[rs for rs in r2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0
                mTEPES.dPar['pHydroOutflows'][mTEPES.dPar['pHydroOutflows'][[rs for rs in r2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0

        # pInitialInventory.update(pd.Series([0.0 for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], index=[es for es in e2a[ar] if pInitialInventory[es] < pEpsilonElec], dtype='float64'))

        # merging positive and negative values of the demand
        mTEPES.dPar['pDemandElec']        = mTEPES.dPar['pDemandElecPos'].where(mTEPES.dPar['pDemandElecNeg'] == 0.0, mTEPES.dPar['pDemandElecNeg'])

        # Increase Maximum to reach minimum
        # mTEPES.dPar['pMaxPowerElec']      = mTEPES.dPar['pMaxPowerElec'].where(mTEPES.dPar['pMaxPowerElec'] >= mTEPES.dPar['pMinPowerElec'], mTEPES.dPar['pMinPowerElec'])
        # mTEPES.dPar['pMaxCharge']         = mTEPES.dPar['pMaxCharge'].where   (mTEPES.dPar['pMaxCharge']    >= mTEPES.dPar['pMinCharge'],    mTEPES.dPar['pMinCharge']   )

        # Decrease Minimum to reach maximum
        mTEPES.dPar['pMinPowerElec']      = mTEPES.dPar['pMinPowerElec'].where(mTEPES.dPar['pMinPowerElec'] <= mTEPES.dPar['pMaxPowerElec'], mTEPES.dPar['pMaxPowerElec'])
        mTEPES.dPar['pMinCharge']         = mTEPES.dPar['pMinCharge'].where   (mTEPES.dPar['pMinCharge']    <= mTEPES.dPar['pMaxCharge'],    mTEPES.dPar['pMaxCharge']   )

        # calculate 2nd Blocks
        mTEPES.dPar['pMaxPower2ndBlock']  = mTEPES.dPar['pMaxPowerElec'] - mTEPES.dPar['pMinPowerElec']
        mTEPES.dPar['pMaxCharge2ndBlock'] = mTEPES.dPar['pMaxCharge']    - mTEPES.dPar['pMinCharge']

        mTEPES.dPar['pMaxCapacity']       = mTEPES.dPar['pMaxPowerElec'].where(mTEPES.dPar['pMaxPowerElec'] > mTEPES.dPar['pMaxCharge'], mTEPES.dPar['pMaxCharge'])

        if g2a[ar]:
            mTEPES.dPar['pMaxPower2ndBlock'] [mTEPES.dPar['pMaxPower2ndBlock'] [[g for g in g2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pMaxCharge2ndBlock'][mTEPES.dPar['pMaxCharge2ndBlock'][[g for g in g2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0

        mTEPES.dPar['pLineNTCFrw'][mTEPES.dPar['pLineNTCFrw'] < mTEPES.dPar['pEpsilonElec']] = 0
        mTEPES.dPar['pLineNTCBck'][mTEPES.dPar['pLineNTCBck'] < mTEPES.dPar['pEpsilonElec']] = 0
        mTEPES.dPar['pLineNTCMax'] = mTEPES.dPar['pLineNTCFrw'].where(mTEPES.dPar['pLineNTCFrw'] > mTEPES.dPar['pLineNTCBck'], mTEPES.dPar['pLineNTCBck'])

        if mTEPES.dPar['pIndHydrogen'] == 1:
            mTEPES.dPar['pDemandH2'][mTEPES.dPar['pDemandH2'][[nd for nd in d2a[ar]]] < mTEPES.dPar['pEpsilonElec']] = 0.0
            mTEPES.dPar['pH2PipeNTCFrw'][mTEPES.dPar['pH2PipeNTCFrw'] < mTEPES.dPar['pEpsilonElec']] = 0
            mTEPES.dPar['pH2PipeNTCBck'][mTEPES.dPar['pH2PipeNTCBck'] < mTEPES.dPar['pEpsilonElec']] = 0

        if mTEPES.dPar['pIndHeat'] == 1:
            mTEPES.dPar['pDemandHeatPeak'][p,ar] = mTEPES.dPar['pDemandHeat'].loc[p,:,:][[nd for nd in d2a[ar]]].sum(axis=1).max()
            mTEPES.dPar['pEpsilonHeat']          = mTEPES.dPar['pDemandHeatPeak'][p,ar]*1e-5
            mTEPES.dPar['pDemandHeat']             [mTEPES.dPar['pDemandHeat']    [[nd for nd in   d2a[ar]]] <  mTEPES.dPar['pEpsilonHeat']] = 0.0
            mTEPES.dPar['pHeatPipeNTCFrw'][mTEPES.dPar['pHeatPipeNTCFrw'] < mTEPES.dPar['pEpsilonElec']] = 0
            mTEPES.dPar['pHeatPipeNTCBck'][mTEPES.dPar['pHeatPipeNTCBck'] < mTEPES.dPar['pEpsilonElec']] = 0

    # drop generators not g or es or eh or ch
    mTEPES.dPar['pMinPowerElec']      = mTEPES.dPar['pMinPowerElec'].loc     [:,mTEPES.g ]
    mTEPES.dPar['pMaxPowerElec']      = mTEPES.dPar['pMaxPowerElec'].loc     [:,mTEPES.g ]
    mTEPES.dPar['pMinCharge']         = mTEPES.dPar['pMinCharge'].loc        [:,mTEPES.eh]
    mTEPES.dPar['pMaxCharge']         = mTEPES.dPar['pMaxCharge'].loc        [:,mTEPES.eh]
    mTEPES.dPar['pMaxPower2ndBlock']  = mTEPES.dPar['pMaxPower2ndBlock'].loc [:,mTEPES.g ]
    mTEPES.dPar['pMaxCharge2ndBlock'] = mTEPES.dPar['pMaxCharge2ndBlock'].loc[:,mTEPES.eh]
    mTEPES.dPar['pMaxCapacity']       = mTEPES.dPar['pMaxCapacity'].loc      [:,mTEPES.eh]
    mTEPES.dPar['pEnergyInflows']     = mTEPES.dPar['pEnergyInflows'].loc    [:,mTEPES.es]
    mTEPES.dPar['pEnergyOutflows']    = mTEPES.dPar['pEnergyOutflows'].loc   [:,mTEPES.es]
    mTEPES.dPar['pIniInventory']      = mTEPES.dPar['pIniInventory'].loc     [:,mTEPES.es]
    mTEPES.dPar['pMinStorage']        = mTEPES.dPar['pMinStorage'].loc       [:,mTEPES.es]
    mTEPES.dPar['pMaxStorage']        = mTEPES.dPar['pMaxStorage'].loc       [:,mTEPES.es]
    mTEPES.dPar['pVariableMaxEnergy'] = mTEPES.dPar['pVariableMaxEnergy'].loc[:,mTEPES.g ]
    mTEPES.dPar['pVariableMinEnergy'] = mTEPES.dPar['pVariableMinEnergy'].loc[:,mTEPES.g ]
    mTEPES.dPar['pLinearVarCost']     = mTEPES.dPar['pLinearVarCost'].loc    [:,mTEPES.g ]
    mTEPES.dPar['pConstantVarCost']   = mTEPES.dPar['pConstantVarCost'].loc  [:,mTEPES.g ]
    mTEPES.dPar['pEmissionVarCost']   = mTEPES.dPar['pEmissionVarCost'].loc  [:,mTEPES.g ]

    # replace < 0.0 by 0.0
    mTEPES.dPar['pEpsilon'] = 1e-6
    mTEPES.dPar['pMaxPower2ndBlock']  = mTEPES.dPar['pMaxPower2ndBlock'].where (mTEPES.dPar['pMaxPower2ndBlock']  > mTEPES.dPar['pEpsilon'], 0.0)
    mTEPES.dPar['pMaxCharge2ndBlock'] = mTEPES.dPar['pMaxCharge2ndBlock'].where(mTEPES.dPar['pMaxCharge2ndBlock'] > mTEPES.dPar['pEpsilon'], 0.0)

    # computation of the power-to-heat ratio of the CHP units
    # heat ratio of boiler units is fixed to 1.0
    mTEPES.dPar['pPower2HeatRatio']   = pd.Series([1.0 if ch in mTEPES.bo else (mTEPES.dPar['pRatedMaxPowerElec'][ch]-mTEPES.dPar['pRatedMinPowerElec'][ch])/(mTEPES.dPar['pRatedMaxPowerHeat'][ch]-mTEPES.dPar['pRatedMinPowerHeat'][ch]) for ch in mTEPES.ch], index=mTEPES.ch)
    mTEPES.dPar['pMinPowerHeat']      = pd.DataFrame([[mTEPES.dPar['pMinPowerElec']     [ch][p,sc,n]/mTEPES.dPar['pPower2HeatRatio'][ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    mTEPES.dPar['pMaxPowerHeat']      = pd.DataFrame([[mTEPES.dPar['pMaxPowerElec']     [ch][p,sc,n]/mTEPES.dPar['pPower2HeatRatio'][ch] for ch in mTEPES.ch] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.ch)
    mTEPES.dPar['pMinPowerHeat'].update(pd.DataFrame([[mTEPES.dPar['pRatedMinPowerHeat'][bo]                                             for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))
    mTEPES.dPar['pMaxPowerHeat'].update(pd.DataFrame([[mTEPES.dPar['pRatedMaxPowerHeat'][bo]                                             for bo in mTEPES.bo] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.bo))
    mTEPES.dPar['pMaxPowerHeat'].update(pd.DataFrame([[mTEPES.dPar['pMaxCharge'][hp][p,sc,n]/mTEPES.dPar['pProductionFunctionHeat'][hp]  for hp in mTEPES.hp] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.hp))

    # drop values not par, p, or ps
    mTEPES.dPar['pReserveMargin']  = mTEPES.dPar['pReserveMargin'].loc [mTEPES.par]
    mTEPES.dPar['pEmission']       = mTEPES.dPar['pEmission'].loc      [mTEPES.par]
    mTEPES.dPar['pRESEnergy']      = mTEPES.dPar['pRESEnergy'].loc     [mTEPES.par]
    mTEPES.dPar['pDemandElecPeak'] = mTEPES.dPar['pDemandElecPeak'].loc[mTEPES.par]
    mTEPES.dPar['pDemandHeatPeak'] = mTEPES.dPar['pDemandHeatPeak'].loc[mTEPES.par]
    mTEPES.dPar['pPeriodWeight']   = mTEPES.dPar['pPeriodWeight'].loc  [mTEPES.p  ]
    mTEPES.dPar['pScenProb']       = mTEPES.dPar['pScenProb'].loc      [mTEPES.ps ]

    # drop generators not gc or gd
    mTEPES.dPar['pGenInvestCost']           = mTEPES.dPar['pGenInvestCost'].loc   [mTEPES.eb]
    mTEPES.dPar['pGenRetireCost']           = mTEPES.dPar['pGenRetireCost'].loc   [mTEPES.gd]
    mTEPES.dPar['pIndBinUnitInvest']        = mTEPES.dPar['pIndBinUnitInvest'].loc[mTEPES.eb]
    mTEPES.dPar['pIndBinUnitRetire']        = mTEPES.dPar['pIndBinUnitRetire'].loc[mTEPES.gd]
    mTEPES.dPar['pGenLoInvest']             = mTEPES.dPar['pGenLoInvest'].loc     [mTEPES.eb]
    mTEPES.dPar['pGenLoRetire']             = mTEPES.dPar['pGenLoRetire'].loc     [mTEPES.gd]
    mTEPES.dPar['pGenUpInvest']             = mTEPES.dPar['pGenUpInvest'].loc     [mTEPES.eb]
    mTEPES.dPar['pGenUpRetire']             = mTEPES.dPar['pGenUpRetire'].loc     [mTEPES.gd]

    # drop generators not nr or ec
    mTEPES.dPar['pStartUpCost']             = mTEPES.dPar['pStartUpCost'].loc     [mTEPES.nr]
    mTEPES.dPar['pShutDownCost']            = mTEPES.dPar['pShutDownCost'].loc    [mTEPES.nr]
    mTEPES.dPar['pIndBinUnitCommit']        = mTEPES.dPar['pIndBinUnitCommit'].loc[mTEPES.nr]
    mTEPES.dPar['pIndBinStorInvest']        = mTEPES.dPar['pIndBinStorInvest'].loc[mTEPES.ec]

    # drop lines not la
    mTEPES.dPar['pLineR']                   = mTEPES.dPar['pLineR'].loc           [mTEPES.la]
    mTEPES.dPar['pLineX']                   = mTEPES.dPar['pLineX'].loc           [mTEPES.la]
    mTEPES.dPar['pLineBsh']                 = mTEPES.dPar['pLineBsh'].loc         [mTEPES.la]
    mTEPES.dPar['pLineTAP']                 = mTEPES.dPar['pLineTAP'].loc         [mTEPES.la]
    mTEPES.dPar['pLineLength']              = mTEPES.dPar['pLineLength'].loc      [mTEPES.la]
    mTEPES.dPar['pElecNetPeriodIni']        = mTEPES.dPar['pElecNetPeriodIni'].loc[mTEPES.la]
    mTEPES.dPar['pElecNetPeriodFin']        = mTEPES.dPar['pElecNetPeriodFin'].loc[mTEPES.la]
    mTEPES.dPar['pLineVoltage']             = mTEPES.dPar['pLineVoltage'].loc     [mTEPES.la]
    mTEPES.dPar['pLineNTCFrw']              = mTEPES.dPar['pLineNTCFrw'].loc      [mTEPES.la]
    mTEPES.dPar['pLineNTCBck']              = mTEPES.dPar['pLineNTCBck'].loc      [mTEPES.la]
    mTEPES.dPar['pLineNTCMax']              = mTEPES.dPar['pLineNTCMax'].loc      [mTEPES.la]
    # mTEPES.dPar['pSwOnTime']              = mTEPES.dPar['pSwOnTime'].loc        [mTEPES.la]
    # mTEPES.dPar['pSwOffTime']             = mTEPES.dPar['pSwOffTime'].loc       [mTEPES.la]
    mTEPES.dPar['pIndBinLineInvest']        = mTEPES.dPar['pIndBinLineInvest'].loc[mTEPES.la]
    mTEPES.dPar['pIndBinLineSwitch']        = mTEPES.dPar['pIndBinLineSwitch'].loc[mTEPES.la]
    mTEPES.dPar['pAngMin']                  = mTEPES.dPar['pAngMin'].loc          [mTEPES.la]
    mTEPES.dPar['pAngMax']                  = mTEPES.dPar['pAngMax'].loc          [mTEPES.la]

    # drop lines not lc or ll
    mTEPES.dPar['pNetFixedCost']            = mTEPES.dPar['pNetFixedCost'].loc    [mTEPES.lc]
    mTEPES.dPar['pNetLoInvest']             = mTEPES.dPar['pNetLoInvest'].loc     [mTEPES.lc]
    mTEPES.dPar['pNetUpInvest']             = mTEPES.dPar['pNetUpInvest'].loc     [mTEPES.lc]
    mTEPES.dPar['pLineLossFactor']          = mTEPES.dPar['pLineLossFactor'].loc  [mTEPES.ll]

    mTEPES.dPar['pMaxNTCFrw'] = pd.DataFrame([[mTEPES.dPar['pLineNTCFrw'][la] for la in mTEPES.la] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.la)
    mTEPES.dPar['pMaxNTCBck'] = pd.DataFrame([[mTEPES.dPar['pLineNTCBck'][la] for la in mTEPES.la] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.la)
    if mTEPES.dPar['pIndVarTTC'] == 1:
        mTEPES.dPar['pMaxNTCFrw'] = mTEPES.dPar['pVariableNTCFrw'].replace(0.0, mTEPES.dPar['pLineNTCFrw'])
        mTEPES.dPar['pMaxNTCBck'] = mTEPES.dPar['pVariableNTCBck'].replace(0.0, mTEPES.dPar['pLineNTCBck'])
        mTEPES.dPar['pMaxNTCFrw']  [mTEPES.dPar['pMaxNTCFrw'] < mTEPES.dPar['pEpsilonElec']] = 0.0
        mTEPES.dPar['pMaxNTCBck']  [mTEPES.dPar['pMaxNTCBck'] < mTEPES.dPar['pEpsilonElec']] = 0.0
    mTEPES.dPar['pMaxNTCMax'] = mTEPES.dPar['pMaxNTCFrw'].where(mTEPES.dPar['pMaxNTCFrw'] > mTEPES.dPar['pMaxNTCBck'], mTEPES.dPar['pMaxNTCBck'])

    mTEPES.dPar['pMaxNTCBck']                  = mTEPES.dPar['pMaxNTCBck'].loc             [:,mTEPES.la]
    mTEPES.dPar['pMaxNTCFrw']                  = mTEPES.dPar['pMaxNTCFrw'].loc             [:,mTEPES.la]
    mTEPES.dPar['pMaxNTCMax']                  = mTEPES.dPar['pMaxNTCFrw'].loc             [:,mTEPES.la]

    if mTEPES.dPar['pIndHydroTopology'] == 1:
        # drop generators not h
        mTEPES.dPar['pProductionFunctionHydro'] = mTEPES.dPar['pProductionFunctionHydro'].loc[mTEPES.h ]
        # drop reservoirs not rn
        mTEPES.dPar['pIndBinRsrvInvest']        = mTEPES.dPar['pIndBinRsrvInvest'].loc       [mTEPES.rn]
        mTEPES.dPar['pRsrInvestCost']           = mTEPES.dPar['pRsrInvestCost'].loc          [mTEPES.rn]
        # maximum outflows depending on the downstream hydropower unit
        mTEPES.dPar['pMaxOutflows'] = pd.DataFrame([[sum(mTEPES.dPar['pMaxPowerElec'][h][p,sc,n]/mTEPES.dPar['pProductionFunctionHydro'][h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) for rs in mTEPES.rs] for p,sc,n in mTEPES.psn], index=mTEPES.psn, columns=mTEPES.rs)

    if mTEPES.dPar['pIndHydrogen'] == 1:
        # drop generators not el
        mTEPES.dPar['pProductionFunctionH2'] = mTEPES.dPar['pProductionFunctionH2'].loc[mTEPES.el]
        # drop pipelines not pc
        mTEPES.dPar['pH2PipeFixedCost']      = mTEPES.dPar['pH2PipeFixedCost'].loc     [mTEPES.pc]
        mTEPES.dPar['pH2PipeLoInvest']       = mTEPES.dPar['pH2PipeLoInvest'].loc      [mTEPES.pc]
        mTEPES.dPar['pH2PipeUpInvest']       = mTEPES.dPar['pH2PipeUpInvest'].loc      [mTEPES.pc]

    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.dPar['pReserveMarginHeat']          = mTEPES.dPar['pReserveMarginHeat'].loc         [mTEPES.par]
        # drop generators not hp
        mTEPES.dPar['pProductionFunctionHeat']     = mTEPES.dPar['pProductionFunctionHeat'].loc    [mTEPES.hp]
        # drop generators not hh
        mTEPES.dPar['pProductionFunctionH2ToHeat'] = mTEPES.dPar['pProductionFunctionH2ToHeat'].loc[mTEPES.hh]
        # drop heat pipes not hc
        mTEPES.dPar['pHeatPipeFixedCost']          = mTEPES.dPar['pHeatPipeFixedCost'].loc         [mTEPES.hc]
        mTEPES.dPar['pHeatPipeLoInvest']           = mTEPES.dPar['pHeatPipeLoInvest'].loc          [mTEPES.hc]
        mTEPES.dPar['pHeatPipeUpInvest']           = mTEPES.dPar['pHeatPipeUpInvest'].loc          [mTEPES.hc]

    # replace very small costs by 0
    mTEPES.dPar['pEpsilon'] = 1e-5           # this value in EUR/GWh is lower than the O&M variable cost of any technology, independent of the area

    mTEPES.dPar['pLinearVarCost']  [mTEPES.dPar['pLinearVarCost']  [[g for g in mTEPES.g]] < mTEPES.dPar['pEpsilon']] = 0.0
    mTEPES.dPar['pConstantVarCost'][mTEPES.dPar['pConstantVarCost'][[g for g in mTEPES.g]] < mTEPES.dPar['pEpsilon']] = 0.0
    mTEPES.dPar['pEmissionVarCost'][mTEPES.dPar['pEmissionVarCost'][[g for g in mTEPES.g]] < mTEPES.dPar['pEpsilon']] = 0.0

    mTEPES.dPar['pRatedLinearVarCost'].update  (pd.Series([0.0 for g  in mTEPES.g  if     mTEPES.dPar['pRatedLinearVarCost']  [g ]  < mTEPES.dPar['pEpsilon']], index=[g  for g  in mTEPES.g  if     mTEPES.dPar['pRatedLinearVarCost']  [g ]  < mTEPES.dPar['pEpsilon']]))
    mTEPES.dPar['pLinearOMCost'].update        (pd.Series([0.0 for g  in mTEPES.g  if     mTEPES.dPar['pLinearOMCost']        [g ]  < mTEPES.dPar['pEpsilon']], index=[g  for g  in mTEPES.g  if     mTEPES.dPar['pLinearOMCost']        [g ]  < mTEPES.dPar['pEpsilon']]))
    mTEPES.dPar['pOperReserveCost'].update     (pd.Series([0.0 for g  in mTEPES.g  if     mTEPES.dPar['pOperReserveCost']     [g ]  < mTEPES.dPar['pEpsilon']], index=[g  for g  in mTEPES.g  if     mTEPES.dPar['pOperReserveCost']     [g ]  < mTEPES.dPar['pEpsilon']]))
    # mTEPES.dPar['pEmissionCost'].update      (pd.Series([0.0 for g  in mTEPES.g  if abs(mTEPES.dPar['pEmissionCost']        [g ]) < mTEPES.dPar['pEpsilon']], index=[g  for g  in mTEPES.g  if abs(mTEPES.dPar['pEmissionCost']        [g ]) < mTEPES.dPar['pEpsilon']]))
    mTEPES.dPar['pStartUpCost'].update         (pd.Series([0.0 for nr in mTEPES.nr if     mTEPES.dPar['pStartUpCost']         [nr]  < mTEPES.dPar['pEpsilon']], index=[nr for nr in mTEPES.nr if     mTEPES.dPar['pStartUpCost']         [nr]  < mTEPES.dPar['pEpsilon']]))
    mTEPES.dPar['pShutDownCost'].update        (pd.Series([0.0 for nr in mTEPES.nr if     mTEPES.dPar['pShutDownCost']        [nr]  < mTEPES.dPar['pEpsilon']], index=[nr for nr in mTEPES.nr if     mTEPES.dPar['pShutDownCost']        [nr]  < mTEPES.dPar['pEpsilon']]))

    # this rated linear variable cost is going to be used to order the generating units
    # we include a small term to avoid a stochastic behavior due to equal values
    for g in mTEPES.g:
        mTEPES.dPar['pRatedLinearVarCost'][g] += 1e-3*mTEPES.dPar['pEpsilon']*mTEPES.g.ord(g)

    # BigM maximum flow to be used in the Kirchhoff's 2nd law disjunctive constraint
    mTEPES.dPar['pBigMFlowBck'] = mTEPES.dPar['pLineNTCBck']*0.0
    mTEPES.dPar['pBigMFlowFrw'] = mTEPES.dPar['pLineNTCFrw']*0.0
    for lea in mTEPES.lea:
        mTEPES.dPar['pBigMFlowBck'].loc[lea] = mTEPES.dPar['pLineNTCBck'][lea]
        mTEPES.dPar['pBigMFlowFrw'].loc[lea] = mTEPES.dPar['pLineNTCFrw'][lea]
    for lca in mTEPES.lca:
        mTEPES.dPar['pBigMFlowBck'].loc[lca] = mTEPES.dPar['pLineNTCBck'][lca]*1.5
        mTEPES.dPar['pBigMFlowFrw'].loc[lca] = mTEPES.dPar['pLineNTCFrw'][lca]*1.5
    for led in mTEPES.led:
        mTEPES.dPar['pBigMFlowBck'].loc[led] = mTEPES.dPar['pLineNTCBck'][led]
        mTEPES.dPar['pBigMFlowFrw'].loc[led] = mTEPES.dPar['pLineNTCFrw'][led]
    for lcd in mTEPES.lcd:
        mTEPES.dPar['pBigMFlowBck'].loc[lcd] = mTEPES.dPar['pLineNTCBck'][lcd]*1.5
        mTEPES.dPar['pBigMFlowFrw'].loc[lcd] = mTEPES.dPar['pLineNTCFrw'][lcd]*1.5

    # if BigM are 0.0 then converted to 1.0 to avoid division by 0.0
    mTEPES.dPar['pBigMFlowBck'] = mTEPES.dPar['pBigMFlowBck'].where(mTEPES.dPar['pBigMFlowBck'] != 0.0, 1.0)
    mTEPES.dPar['pBigMFlowFrw'] = mTEPES.dPar['pBigMFlowFrw'].where(mTEPES.dPar['pBigMFlowFrw'] != 0.0, 1.0)

    # maximum voltage angle
    mTEPES.dPar['pMaxTheta'] = mTEPES.dPar['pDemandElec']*0.0 + math.pi/2
    mTEPES.dPar['pMaxTheta'] = mTEPES.dPar['pMaxTheta'].loc[mTEPES.psn]

    # this option avoids a warning in the following assignments
    pd.options.mode.chained_assignment = None

    def filter_rows(df, set):
        df = df.stack(level=list(range(df.columns.nlevels)), future_stack=True)
        df = df[df.index.isin(set)]
        return df

    mTEPES.dPar['pMinPowerElec']      = filter_rows(mTEPES.dPar['pMinPowerElec']     , mTEPES.psng )
    mTEPES.dPar['pMaxPowerElec']      = filter_rows(mTEPES.dPar['pMaxPowerElec']     , mTEPES.psng )
    mTEPES.dPar['pMinCharge']         = filter_rows(mTEPES.dPar['pMinCharge']        , mTEPES.psneh)
    mTEPES.dPar['pMaxCharge']         = filter_rows(mTEPES.dPar['pMaxCharge']        , mTEPES.psneh)
    mTEPES.dPar['pMaxCapacity']       = filter_rows(mTEPES.dPar['pMaxCapacity']      , mTEPES.psneh)
    mTEPES.dPar['pMaxPower2ndBlock']  = filter_rows(mTEPES.dPar['pMaxPower2ndBlock'] , mTEPES.psng )
    mTEPES.dPar['pMaxCharge2ndBlock'] = filter_rows(mTEPES.dPar['pMaxCharge2ndBlock'], mTEPES.psneh)
    mTEPES.dPar['pEnergyInflows']     = filter_rows(mTEPES.dPar['pEnergyInflows']    , mTEPES.psnes)
    mTEPES.dPar['pEnergyOutflows']    = filter_rows(mTEPES.dPar['pEnergyOutflows']   , mTEPES.psnes)
    mTEPES.dPar['pMinStorage']        = filter_rows(mTEPES.dPar['pMinStorage']       , mTEPES.psnes)
    mTEPES.dPar['pMaxStorage']        = filter_rows(mTEPES.dPar['pMaxStorage']       , mTEPES.psnes)
    mTEPES.dPar['pVariableMaxEnergy'] = filter_rows(mTEPES.dPar['pVariableMaxEnergy'], mTEPES.psng )
    mTEPES.dPar['pVariableMinEnergy'] = filter_rows(mTEPES.dPar['pVariableMinEnergy'], mTEPES.psng )
    mTEPES.dPar['pLinearVarCost']     = filter_rows(mTEPES.dPar['pLinearVarCost']    , mTEPES.psng )
    mTEPES.dPar['pConstantVarCost']   = filter_rows(mTEPES.dPar['pConstantVarCost']  , mTEPES.psng )
    mTEPES.dPar['pEmissionVarCost']   = filter_rows(mTEPES.dPar['pEmissionVarCost']  , mTEPES.psng )
    mTEPES.dPar['pIniInventory']      = filter_rows(mTEPES.dPar['pIniInventory']     , mTEPES.psnes)

    mTEPES.dPar['pDemandElec']        = filter_rows(mTEPES.dPar['pDemandElec']       , mTEPES.psnnd)
    mTEPES.dPar['pDemandElecPos']     = filter_rows(mTEPES.dPar['pDemandElecPos']    , mTEPES.psnnd)
    mTEPES.dPar['pSystemInertia']     = filter_rows(mTEPES.dPar['pSystemInertia']    , mTEPES.psnar)
    mTEPES.dPar['pOperReserveUp']     = filter_rows(mTEPES.dPar['pOperReserveUp']    , mTEPES.psnar)
    mTEPES.dPar['pOperReserveDw']     = filter_rows(mTEPES.dPar['pOperReserveDw']    , mTEPES.psnar)

    mTEPES.dPar['pMaxNTCBck']         = filter_rows(mTEPES.dPar['pMaxNTCBck']        , mTEPES.psnla)
    mTEPES.dPar['pMaxNTCFrw']         = filter_rows(mTEPES.dPar['pMaxNTCFrw']        , mTEPES.psnla)
    mTEPES.dPar['pMaxNTCMax']         = filter_rows(mTEPES.dPar['pMaxNTCMax']        , mTEPES.psnla)

    if mTEPES.dPar['pIndPTDF'] == 1:
        mTEPES.dPar['pPTDF'] = mTEPES.dPar['pVariablePTDF'].stack(level=list(range(mTEPES.dPar['pVariablePTDF'].columns.nlevels)), future_stack=True)
        mTEPES.dPar['pPTDF'].index.set_names(['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit', 'Node'], inplace=True)
        # filter rows to keep the same as mTEPES.psnland
        mTEPES.dPar['pPTDF'] = mTEPES.dPar['pPTDF'][mTEPES.dPar['pPTDF'].index.isin(mTEPES.psnland)]

    # %% parameters
    mTEPES.pIndBinGenInvest      = Param(initialize=mTEPES.dPar['pIndBinGenInvest']    , within=NonNegativeIntegers, doc='Indicator of binary generation       investment decisions', mutable=True)
    mTEPES.pIndBinGenRetire      = Param(initialize=mTEPES.dPar['pIndBinGenRetirement'], within=NonNegativeIntegers, doc='Indicator of binary generation       retirement decisions', mutable=True)
    mTEPES.pIndBinRsrInvest      = Param(initialize=mTEPES.dPar['pIndBinRsrInvest']    , within=NonNegativeIntegers, doc='Indicator of binary reservoir        investment decisions', mutable=True)
    mTEPES.pIndBinNetElecInvest  = Param(initialize=mTEPES.dPar['pIndBinNetInvest']    , within=NonNegativeIntegers, doc='Indicator of binary electric network investment decisions', mutable=True)
    mTEPES.pIndBinNetH2Invest    = Param(initialize=mTEPES.dPar['pIndBinNetH2Invest']  , within=NonNegativeIntegers, doc='Indicator of binary hydrogen network investment decisions', mutable=True)
    mTEPES.pIndBinNetHeatInvest  = Param(initialize=mTEPES.dPar['pIndBinNetHeatInvest'], within=NonNegativeIntegers, doc='Indicator of binary heat     network investment decisions', mutable=True)
    mTEPES.pIndBinGenOperat      = Param(initialize=mTEPES.dPar['pIndBinGenOperat']    , within=Binary,              doc='Indicator of binary generation operation  decisions',       mutable=True)
    mTEPES.pIndBinSingleNode     = Param(initialize=mTEPES.dPar['pIndBinSingleNode']   , within=Binary,              doc='Indicator of single node within a electric network case',   mutable=True)
    mTEPES.pIndBinGenRamps       = Param(initialize=mTEPES.dPar['pIndBinGenRamps']     , within=Binary,              doc='Indicator of using or not the ramp constraints',            mutable=True)
    mTEPES.pIndBinGenMinTime     = Param(initialize=mTEPES.dPar['pIndBinGenMinTime']   , within=Binary,              doc='Indicator of using or not the min up/dw time constraints',  mutable=True)
    mTEPES.pIndBinLineCommit     = Param(initialize=mTEPES.dPar['pIndBinLineCommit']   , within=Binary,              doc='Indicator of binary electric network switching  decisions', mutable=True)
    mTEPES.pIndBinNetLosses      = Param(initialize=mTEPES.dPar['pIndBinNetLosses']    , within=Binary,              doc='Indicator of binary electric network ohmic losses',         mutable=True)
    mTEPES.pIndHydroTopology     = Param(initialize=mTEPES.dPar['pIndHydroTopology']   , within=Binary,              doc='Indicator of reservoir and hydropower topology'                         )
    mTEPES.pIndHydrogen          = Param(initialize=mTEPES.dPar['pIndHydrogen']        , within=Binary,              doc='Indicator of hydrogen demand and pipeline network'                      )
    mTEPES.pIndHeat              = Param(initialize=mTEPES.dPar['pIndHeat']            , within=Binary,              doc='Indicator of heat     demand and pipe     network'                      )
    mTEPES.pIndVarTTC            = Param(initialize=mTEPES.dPar['pIndVarTTC']          , within=Binary,              doc='Indicator of using or not variable TTC'                                 )
    mTEPES.pIndPTDF              = Param(initialize=mTEPES.dPar['pIndPTDF']            , within=Binary,              doc='Indicator of using or not the Flow-based method'                        )

    mTEPES.pENSCost              = Param(initialize=mTEPES.dPar['pENSCost']            , within=NonNegativeReals,    doc='ENS cost'                                           )
    mTEPES.pH2NSCost             = Param(initialize=mTEPES.dPar['pHNSCost']            , within=NonNegativeReals,    doc='HNS cost'                                           )
    mTEPES.pHeatNSCost           = Param(initialize=mTEPES.dPar['pHTNSCost']           , within=NonNegativeReals,    doc='HTNS cost'                                          )
    mTEPES.pCO2Cost              = Param(initialize=mTEPES.dPar['pCO2Cost']            , within=NonNegativeReals,    doc='CO2 emission cost'                                  )
    mTEPES.pAnnualDiscRate       = Param(initialize=mTEPES.dPar['pAnnualDiscountRate'] , within=UnitInterval,        doc='Annual discount rate'                               )
    mTEPES.pUpReserveActivation  = Param(initialize=mTEPES.dPar['pUpReserveActivation'], within=UnitInterval,        doc='Proportion of upward   reserve activation'          )
    mTEPES.pDwReserveActivation  = Param(initialize=mTEPES.dPar['pDwReserveActivation'], within=UnitInterval,        doc='Proportion of downward reserve activation'          )
    mTEPES.pMinRatioDwUp         = Param(initialize=mTEPES.dPar['pMinRatioDwUp']       , within=UnitInterval,        doc='Minimum ratio downward to upward operating reserves')
    mTEPES.pMaxRatioDwUp         = Param(initialize=mTEPES.dPar['pMaxRatioDwUp']       , within=UnitInterval,        doc='Maximum ratio downward to upward operating reserves')
    mTEPES.pSBase                = Param(initialize=mTEPES.dPar['pSBase']              , within=PositiveReals,       doc='Base power'                                         )
    mTEPES.pTimeStep             = Param(initialize=mTEPES.dPar['pTimeStep']           , within=PositiveIntegers,    doc='Unitary time step'                                  )
    mTEPES.pEconomicBaseYear     = Param(initialize=mTEPES.dPar['pEconomicBaseYear']   , within=PositiveIntegers,    doc='Base year'                                          )

    mTEPES.pReserveMargin        = Param(mTEPES.par,   initialize=mTEPES.dPar['pReserveMargin'].to_dict()            , within=NonNegativeReals,    doc='Adequacy reserve margin'                             )
    mTEPES.pEmission             = Param(mTEPES.par,   initialize=mTEPES.dPar['pEmission'].to_dict()                 , within=NonNegativeReals,    doc='Maximum CO2 emission'                                )
    mTEPES.pRESEnergy            = Param(mTEPES.par,   initialize=mTEPES.dPar['pRESEnergy'].to_dict()                , within=NonNegativeReals,    doc='Minimum RES energy'                                  )
    mTEPES.pDemandElecPeak       = Param(mTEPES.par,   initialize=mTEPES.dPar['pDemandElecPeak'].to_dict()           , within=NonNegativeReals,    doc='Peak electric demand'                                )
    mTEPES.pDemandElec           = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandElec'].to_dict()               , within=           Reals,    doc='Electric demand'                                     )
    mTEPES.pDemandElecPos        = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandElecPos'].to_dict()            , within=NonNegativeReals,    doc='Electric demand positive'                            )
    mTEPES.pPeriodWeight         = Param(mTEPES.p,     initialize=mTEPES.dPar['pPeriodWeight'].to_dict()             , within=NonNegativeReals,    doc='Period weight',                          mutable=True)
    mTEPES.pDiscountedWeight     = Param(mTEPES.p,     initialize=mTEPES.dPar['pDiscountedWeight'].to_dict()         , within=NonNegativeReals,    doc='Discount factor'                                     )
    mTEPES.pScenProb             = Param(mTEPES.psc,   initialize=mTEPES.dPar['pScenProb'].to_dict()                 , within=UnitInterval    ,    doc='Probability',                            mutable=True)
    mTEPES.pStageWeight          = Param(mTEPES.stt,   initialize=mTEPES.dPar['pStageWeight'].to_dict()              , within=NonNegativeReals,    doc='Stage weight'                                        )
    mTEPES.pDuration             = Param(mTEPES.psn,   initialize=mTEPES.dPar['pDuration'].to_dict()                 , within=NonNegativeIntegers, doc='Duration',                               mutable=True)
    mTEPES.pNodeLon              = Param(mTEPES.nd,    initialize=mTEPES.dPar['pNodeLon'].to_dict()                  ,                             doc='Longitude'                                           )
    mTEPES.pNodeLat              = Param(mTEPES.nd,    initialize=mTEPES.dPar['pNodeLat'].to_dict()                  ,                             doc='Latitude'                                            )
    mTEPES.pSystemInertia        = Param(mTEPES.psnar, initialize=mTEPES.dPar['pSystemInertia'].to_dict()            , within=NonNegativeReals,    doc='System inertia'                                      )
    mTEPES.pOperReserveUp        = Param(mTEPES.psnar, initialize=mTEPES.dPar['pOperReserveUp'].to_dict()            , within=NonNegativeReals,    doc='Upward   operating reserve'                          )
    mTEPES.pOperReserveDw        = Param(mTEPES.psnar, initialize=mTEPES.dPar['pOperReserveDw'].to_dict()            , within=NonNegativeReals,    doc='Downward operating reserve'                          )
    mTEPES.pMinPowerElec         = Param(mTEPES.psng , initialize=mTEPES.dPar['pMinPowerElec'].to_dict()             , within=NonNegativeReals,    doc='Minimum electric power'                              )
    mTEPES.pMaxPowerElec         = Param(mTEPES.psng , initialize=mTEPES.dPar['pMaxPowerElec'].to_dict()             , within=NonNegativeReals,    doc='Maximum electric power'                              )
    mTEPES.pMinCharge            = Param(mTEPES.psneh, initialize=mTEPES.dPar['pMinCharge'].to_dict()                , within=NonNegativeReals,    doc='Minimum charge'                                      )
    mTEPES.pMaxCharge            = Param(mTEPES.psneh, initialize=mTEPES.dPar['pMaxCharge'].to_dict()                , within=NonNegativeReals,    doc='Maximum charge'                                      )
    mTEPES.pMaxCapacity          = Param(mTEPES.psneh, initialize=mTEPES.dPar['pMaxCapacity'].to_dict()              , within=NonNegativeReals,    doc='Maximum capacity'                                    )
    mTEPES.pMaxPower2ndBlock     = Param(mTEPES.psng , initialize=mTEPES.dPar['pMaxPower2ndBlock'].to_dict()         , within=NonNegativeReals,    doc='Second block power'                                  )
    mTEPES.pMaxCharge2ndBlock    = Param(mTEPES.psneh, initialize=mTEPES.dPar['pMaxCharge2ndBlock'].to_dict()        , within=NonNegativeReals,    doc='Second block charge'                                 )
    mTEPES.pEnergyInflows        = Param(mTEPES.psnes, initialize=mTEPES.dPar['pEnergyInflows'].to_dict()            , within=NonNegativeReals,    doc='Energy inflows',                         mutable=True)
    mTEPES.pEnergyOutflows       = Param(mTEPES.psnes, initialize=mTEPES.dPar['pEnergyOutflows'].to_dict()           , within=NonNegativeReals,    doc='Energy outflows',                        mutable=True)
    mTEPES.pMinStorage           = Param(mTEPES.psnes, initialize=mTEPES.dPar['pMinStorage'].to_dict()               , within=NonNegativeReals,    doc='ESS Minimum storage capacity'                        )
    mTEPES.pMaxStorage           = Param(mTEPES.psnes, initialize=mTEPES.dPar['pMaxStorage'].to_dict()               , within=NonNegativeReals,    doc='ESS Maximum storage capacity'                        )
    mTEPES.pMinEnergy            = Param(mTEPES.psng , initialize=mTEPES.dPar['pVariableMinEnergy'].to_dict()        , within=NonNegativeReals,    doc='Unit minimum energy demand'                          )
    mTEPES.pMaxEnergy            = Param(mTEPES.psng , initialize=mTEPES.dPar['pVariableMaxEnergy'].to_dict()        , within=NonNegativeReals,    doc='Unit maximum energy demand'                          )
    mTEPES.pRatedMaxPowerElec    = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRatedMaxPowerElec'].to_dict()        , within=NonNegativeReals,    doc='Rated maximum power'                                 )
    mTEPES.pRatedMaxCharge       = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRatedMaxCharge'].to_dict()           , within=NonNegativeReals,    doc='Rated maximum charge'                                )
    mTEPES.pMustRun              = Param(mTEPES.gg,    initialize=mTEPES.dPar['pMustRun'].to_dict()                  , within=Binary          ,    doc='must-run unit'                                       )
    mTEPES.pInertia              = Param(mTEPES.gg,    initialize=mTEPES.dPar['pInertia'].to_dict()                  , within=NonNegativeReals,    doc='unit inertia constant'                               )
    mTEPES.pElecGenPeriodIni     = Param(mTEPES.gg,    initialize=mTEPES.dPar['pElecGenPeriodIni'].to_dict()         , within=PositiveIntegers,    doc='installation year',                                  )
    mTEPES.pElecGenPeriodFin     = Param(mTEPES.gg,    initialize=mTEPES.dPar['pElecGenPeriodFin'].to_dict()         , within=PositiveIntegers,    doc='retirement   year',                                  )
    mTEPES.pAvailability         = Param(mTEPES.gg,    initialize=mTEPES.dPar['pAvailability'].to_dict()             , within=UnitInterval    ,    doc='unit availability',                      mutable=True)
    mTEPES.pEFOR                 = Param(mTEPES.gg,    initialize=mTEPES.dPar['pEFOR'].to_dict()                     , within=UnitInterval    ,    doc='EFOR'                                                )
    mTEPES.pRatedLinearVarCost   = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRatedLinearVarCost'].to_dict()       , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pLinearVarCost        = Param(mTEPES.psng , initialize=mTEPES.dPar['pLinearVarCost'].to_dict()            , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pConstantVarCost      = Param(mTEPES.psng , initialize=mTEPES.dPar['pConstantVarCost'].to_dict()          , within=NonNegativeReals,    doc='Constant variable cost'                              )
    mTEPES.pLinearOMCost         = Param(mTEPES.gg,    initialize=mTEPES.dPar['pLinearOMCost'].to_dict()             , within=NonNegativeReals,    doc='Linear   O&M      cost'                              )
    mTEPES.pOperReserveCost      = Param(mTEPES.gg,    initialize=mTEPES.dPar['pOperReserveCost'].to_dict()          , within=NonNegativeReals,    doc='Operating reserve cost'                              )
    mTEPES.pEmissionVarCost      = Param(mTEPES.psng , initialize=mTEPES.dPar['pEmissionVarCost'].to_dict()          , within=Reals           ,    doc='CO2 Emission      cost'                              )
    mTEPES.pEmissionRate         = Param(mTEPES.gg,    initialize=mTEPES.dPar['pEmissionRate'].to_dict()             , within=Reals           ,    doc='CO2 Emission      rate'                              )
    mTEPES.pStartUpCost          = Param(mTEPES.nr,    initialize=mTEPES.dPar['pStartUpCost'].to_dict()              , within=NonNegativeReals,    doc='Startup  cost'                                       )
    mTEPES.pShutDownCost         = Param(mTEPES.nr,    initialize=mTEPES.dPar['pShutDownCost'].to_dict()             , within=NonNegativeReals,    doc='Shutdown cost'                                       )
    mTEPES.pRampUp               = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRampUp'].to_dict()                   , within=NonNegativeReals,    doc='Ramp up   rate'                                      )
    mTEPES.pRampDw               = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRampDw'].to_dict()                   , within=NonNegativeReals,    doc='Ramp down rate'                                      )
    mTEPES.pUpTime               = Param(mTEPES.gg,    initialize=mTEPES.dPar['pUpTime'].to_dict()                   , within=NonNegativeIntegers, doc='Up     time'                                         )
    mTEPES.pDwTime               = Param(mTEPES.gg,    initialize=mTEPES.dPar['pDwTime'].to_dict()                   , within=NonNegativeIntegers, doc='Down   time'                                         )
    mTEPES.pStableTime           = Param(mTEPES.gg,    initialize=mTEPES.dPar['pStableTime'].to_dict()               , within=NonNegativeIntegers, doc='Stable time'                                         )
    mTEPES.pShiftTime            = Param(mTEPES.gg,    initialize=mTEPES.dPar['pShiftTime'].to_dict()                , within=NonNegativeIntegers, doc='Shift  time'                                         )
    mTEPES.pGenInvestCost        = Param(mTEPES.eb,    initialize=mTEPES.dPar['pGenInvestCost'].to_dict()            , within=NonNegativeReals,    doc='Generation fixed cost'                               )
    mTEPES.pGenRetireCost        = Param(mTEPES.gd,    initialize=mTEPES.dPar['pGenRetireCost'].to_dict()            , within=Reals           ,    doc='Generation fixed retire cost'                        )
    mTEPES.pIndBinUnitInvest     = Param(mTEPES.eb,    initialize=mTEPES.dPar['pIndBinUnitInvest'].to_dict()         , within=Binary          ,    doc='Binary investment decision'                          )
    mTEPES.pIndBinUnitRetire     = Param(mTEPES.gd,    initialize=mTEPES.dPar['pIndBinUnitRetire'].to_dict()         , within=Binary          ,    doc='Binary retirement decision'                          )
    mTEPES.pIndBinUnitCommit     = Param(mTEPES.nr,    initialize=mTEPES.dPar['pIndBinUnitCommit'].to_dict()         , within=Binary          ,    doc='Binary commitment decision'                          )
    mTEPES.pIndBinStorInvest     = Param(mTEPES.ec,    initialize=mTEPES.dPar['pIndBinStorInvest'].to_dict()         , within=Binary          ,    doc='Storage linked to generation investment'             )
    mTEPES.pIndOperReserveGen    = Param(mTEPES.gg,    initialize=mTEPES.dPar['pIndOperReserveGen'].to_dict()        , within=Binary          ,    doc='Indicator of operating reserve when generating power')
    mTEPES.pIndOperReserveCon    = Param(mTEPES.gg,    initialize=mTEPES.dPar['pIndOperReserveCon'].to_dict()        , within=Binary          ,    doc='Indicator of operating reserve when consuming power' )
    mTEPES.pIndOutflowIncomp     = Param(mTEPES.gg,    initialize=mTEPES.dPar['pIndOutflowIncomp'].to_dict()         , within=Binary          ,    doc='Indicator of outflow incompatibility with charging'  )
    mTEPES.pEfficiency           = Param(mTEPES.eh,    initialize=mTEPES.dPar['pEfficiency'].to_dict()               , within=UnitInterval    ,    doc='Round-trip efficiency'                               )
    mTEPES.pStorageTimeStep      = Param(mTEPES.es,    initialize=mTEPES.dPar['pStorageTimeStep'].to_dict()          , within=PositiveIntegers,    doc='ESS Storage cycle'                                   )
    mTEPES.pOutflowsTimeStep     = Param(mTEPES.es,    initialize=mTEPES.dPar['pOutflowsTimeStep'].to_dict()         , within=PositiveIntegers,    doc='ESS Outflows cycle'                                  )
    mTEPES.pEnergyTimeStep       = Param(mTEPES.gg,    initialize=mTEPES.dPar['pEnergyTimeStep'].to_dict()           , within=PositiveIntegers,    doc='Unit energy cycle'                                   )
    mTEPES.pIniInventory         = Param(mTEPES.psnes, initialize=mTEPES.dPar['pIniInventory'].to_dict()             , within=NonNegativeReals,    doc='ESS Initial storage',                    mutable=True)
    mTEPES.pStorageType          = Param(mTEPES.es,    initialize=mTEPES.dPar['pStorageType'].to_dict()              , within=Any             ,    doc='ESS Storage type'                                    )
    mTEPES.pGenLoInvest          = Param(mTEPES.eb,    initialize=mTEPES.dPar['pGenLoInvest'].to_dict()              , within=NonNegativeReals,    doc='Lower bound of the investment decision', mutable=True)
    mTEPES.pGenUpInvest          = Param(mTEPES.eb,    initialize=mTEPES.dPar['pGenUpInvest'].to_dict()              , within=NonNegativeReals,    doc='Upper bound of the investment decision', mutable=True)
    mTEPES.pGenLoRetire          = Param(mTEPES.gd,    initialize=mTEPES.dPar['pGenLoRetire'].to_dict()              , within=NonNegativeReals,    doc='Lower bound of the retirement decision', mutable=True)
    mTEPES.pGenUpRetire          = Param(mTEPES.gd,    initialize=mTEPES.dPar['pGenUpRetire'].to_dict()              , within=NonNegativeReals,    doc='Upper bound of the retirement decision', mutable=True)

    if mTEPES.dPar['pIndHydrogen'] == 1:
        mTEPES.pProductionFunctionH2 = Param(mTEPES.el, initialize=mTEPES.dPar['pProductionFunctionH2'].to_dict(), within=NonNegativeReals, doc='Production function of an electrolyzer plant')

    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.dPar['pMinPowerHeat'] = filter_rows(mTEPES.dPar['pMinPowerHeat'], mTEPES.psnch)
        mTEPES.dPar['pMaxPowerHeat'] = filter_rows(mTEPES.dPar['pMaxPowerHeat'], mTEPES.psnch)

        mTEPES.pReserveMarginHeat          = Param(mTEPES.par,   initialize=mTEPES.dPar['pReserveMarginHeat'].to_dict()         , within=NonNegativeReals, doc='Adequacy reserve margin'                  )
        mTEPES.pRatedMaxPowerHeat          = Param(mTEPES.gg,    initialize=mTEPES.dPar['pRatedMaxPowerHeat'].to_dict()         , within=NonNegativeReals, doc='Rated maximum heat'                       )
        mTEPES.pMinPowerHeat               = Param(mTEPES.psnch, initialize=mTEPES.dPar['pMinPowerHeat'].to_dict()              , within=NonNegativeReals, doc='Minimum heat     power'                   )
        mTEPES.pMaxPowerHeat               = Param(mTEPES.psnch, initialize=mTEPES.dPar['pMaxPowerHeat'].to_dict()              , within=NonNegativeReals, doc='Maximum heat     power'                   )
        mTEPES.pPower2HeatRatio            = Param(mTEPES.ch,    initialize=mTEPES.dPar['pPower2HeatRatio'].to_dict()           , within=NonNegativeReals, doc='Power to heat ratio'                      )
        mTEPES.pProductionFunctionHeat     = Param(mTEPES.hp,    initialize=mTEPES.dPar['pProductionFunctionHeat'].to_dict()    , within=NonNegativeReals, doc='Production function of an CHP plant'      )
        mTEPES.pProductionFunctionH2ToHeat = Param(mTEPES.hh,    initialize=mTEPES.dPar['pProductionFunctionH2ToHeat'].to_dict(), within=NonNegativeReals, doc='Production function of an boiler using H2')

    if mTEPES.dPar['pIndPTDF'] == 1:
        mTEPES.pPTDF                       = Param(mTEPES.psnland, initialize=mTEPES.dPar['pPTDF'].to_dict()                    , within=Reals           , doc='Power transfer distribution factor'       )

    if mTEPES.dPar['pIndHydroTopology'] == 1:
        mTEPES.dPar['pHydroInflows']  = filter_rows(mTEPES.dPar['pHydroInflows'] , mTEPES.psnrs)
        mTEPES.dPar['pHydroOutflows'] = filter_rows(mTEPES.dPar['pHydroOutflows'], mTEPES.psnrs)
        mTEPES.dPar['pMaxOutflows']   = filter_rows(mTEPES.dPar['pMaxOutflows']  , mTEPES.psnrs)
        mTEPES.dPar['pMinVolume']     = filter_rows(mTEPES.dPar['pMinVolume']    , mTEPES.psnrs)
        mTEPES.dPar['pMaxVolume']     = filter_rows(mTEPES.dPar['pMaxVolume']    , mTEPES.psnrs)
        mTEPES.dPar['pIniVolume']     = filter_rows(mTEPES.dPar['pIniVolume']    , mTEPES.psnrs)

        mTEPES.pProductionFunctionHydro = Param(mTEPES.h ,    initialize=mTEPES.dPar['pProductionFunctionHydro'].to_dict(), within=NonNegativeReals, doc='Production function of a hydro power plant'  )
        mTEPES.pHydroInflows            = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pHydroInflows'].to_dict()           , within=NonNegativeReals, doc='Hydro inflows',                  mutable=True)
        mTEPES.pHydroOutflows           = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pHydroOutflows'].to_dict()          , within=NonNegativeReals, doc='Hydro outflows',                 mutable=True)
        mTEPES.pMaxOutflows             = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pMaxOutflows'].to_dict()            , within=NonNegativeReals, doc='Maximum hydro outflows',                     )
        mTEPES.pMinVolume               = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pMinVolume'].to_dict()              , within=NonNegativeReals, doc='Minimum reservoir volume capacity'           )
        mTEPES.pMaxVolume               = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pMaxVolume'].to_dict()              , within=NonNegativeReals, doc='Maximum reservoir volume capacity'           )
        mTEPES.pIndBinRsrvInvest        = Param(mTEPES.rn,    initialize=mTEPES.dPar['pIndBinRsrvInvest'].to_dict()       , within=Binary          , doc='Binary  reservoir investment decision'       )
        mTEPES.pRsrInvestCost           = Param(mTEPES.rn,    initialize=mTEPES.dPar['pRsrInvestCost'].to_dict()          , within=NonNegativeReals, doc='Reservoir fixed cost'                        )
        mTEPES.pRsrPeriodIni            = Param(mTEPES.rs,    initialize=mTEPES.dPar['pRsrPeriodIni'].to_dict()           , within=PositiveIntegers, doc='Installation year',                          )
        mTEPES.pRsrPeriodFin            = Param(mTEPES.rs,    initialize=mTEPES.dPar['pRsrPeriodFin'].to_dict()           , within=PositiveIntegers, doc='Retirement   year',                          )
        mTEPES.pReservoirTimeStep       = Param(mTEPES.rs,    initialize=mTEPES.dPar['pReservoirTimeStep'].to_dict()      , within=PositiveIntegers, doc='Reservoir volume cycle'                      )
        mTEPES.pWaterOutTimeStep        = Param(mTEPES.rs,    initialize=mTEPES.dPar['pWaterOutTimeStep'].to_dict()       , within=PositiveIntegers, doc='Reservoir outflows cycle'                    )
        mTEPES.pIniVolume               = Param(mTEPES.psnrs, initialize=mTEPES.dPar['pIniVolume'].to_dict()              , within=NonNegativeReals, doc='Reservoir initial volume',       mutable=True)
        mTEPES.pInitialVolume           = Param(mTEPES.rs,    initialize=mTEPES.dPar['pInitialVolume'].to_dict()          , within=NonNegativeReals, doc='Reservoir initial volume without load levels')
        mTEPES.pReservoirType           = Param(mTEPES.rs,    initialize=mTEPES.dPar['pReservoirType'].to_dict()          , within=Any             , doc='Reservoir volume type'                       )

    if mTEPES.dPar['pIndHydrogen'] == 1:
        mTEPES.dPar['pDemandH2']    = filter_rows(mTEPES.dPar['pDemandH2']   ,mTEPES.psnnd)
        mTEPES.dPar['pDemandH2Abs'] = filter_rows(mTEPES.dPar['pDemandH2Abs'],mTEPES.psnnd)

        mTEPES.pDemandH2    = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandH2'].to_dict()   , within=NonNegativeReals,    doc='Hydrogen demand per hour')
        mTEPES.pDemandH2Abs = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandH2Abs'].to_dict(), within=NonNegativeReals,    doc='Hydrogen demand'         )

    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.dPar['pDemandHeat']     = filter_rows(mTEPES.dPar['pDemandHeat']    , mTEPES.psnnd)
        mTEPES.dPar['pDemandHeatAbs']  = filter_rows(mTEPES.dPar['pDemandHeatAbs'] , mTEPES.psnnd)

        mTEPES.pDemandHeatPeak = Param(mTEPES.par,   initialize=mTEPES.dPar['pDemandHeatPeak'].to_dict(), within=NonNegativeReals,    doc='Peak heat demand'        )
        mTEPES.pDemandHeat     = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandHeat'].to_dict()   ,  within=NonNegativeReals,    doc='Heat demand per hour'    )
        mTEPES.pDemandHeatAbs  = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pDemandHeatAbs'].to_dict(),  within=NonNegativeReals,    doc='Heat demand'             )

    mTEPES.pLoadLevelDuration = Param(mTEPES.psn,   initialize=0                        ,  within=NonNegativeIntegers, doc='Load level duration', mutable=True)
    for p,sc,n in mTEPES.psn:
        mTEPES.pLoadLevelDuration[p,sc,n] = mTEPES.pLoadLevelWeight[p,sc,n]() * mTEPES.pDuration[p,sc,n]()

    mTEPES.pPeriodProb         = Param(mTEPES.ps,    initialize=0.0                     ,  within=NonNegativeReals,   doc='Period probability',  mutable=True)
    for p,sc in mTEPES.ps:
        # periods and scenarios are going to be solved together with their weight and probability
        mTEPES.pPeriodProb[p,sc] = mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc]

    mTEPES.dPar['pMaxTheta'] = filter_rows(mTEPES.dPar['pMaxTheta'], mTEPES.psnnd)

    mTEPES.pLineLossFactor   = Param(mTEPES.ll,    initialize=mTEPES.dPar['pLineLossFactor'].to_dict()  , within=           Reals,    doc='Loss factor'                                                       )
    mTEPES.pLineR            = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineR'].to_dict()           , within=NonNegativeReals,    doc='Resistance'                                                        )
    mTEPES.pLineX            = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineX'].to_dict()           , within=           Reals,    doc='Reactance'                                                         )
    mTEPES.pLineBsh          = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineBsh'].to_dict()         , within=NonNegativeReals,    doc='Susceptance',                                          mutable=True)
    mTEPES.pLineTAP          = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineTAP'].to_dict()         , within=NonNegativeReals,    doc='Tap changer',                                          mutable=True)
    mTEPES.pLineLength       = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineLength'].to_dict()      , within=NonNegativeReals,    doc='Length',                                               mutable=True)
    mTEPES.pElecNetPeriodIni = Param(mTEPES.la,    initialize=mTEPES.dPar['pElecNetPeriodIni'].to_dict(), within=PositiveIntegers,    doc='Installation period'                                               )
    mTEPES.pElecNetPeriodFin = Param(mTEPES.la,    initialize=mTEPES.dPar['pElecNetPeriodFin'].to_dict(), within=PositiveIntegers,    doc='Retirement   period'                                               )
    mTEPES.pLineVoltage      = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineVoltage'].to_dict()     , within=NonNegativeReals,    doc='Voltage'                                                           )
    mTEPES.pLineNTCFrw       = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineNTCFrw'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC forward'                                         )
    mTEPES.pLineNTCBck       = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineNTCBck'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC backward'                                        )
    mTEPES.pLineNTCMax       = Param(mTEPES.la,    initialize=mTEPES.dPar['pLineNTCMax'].to_dict()      , within=NonNegativeReals,    doc='Electric line NTC'                                                 )
    mTEPES.pNetFixedCost     = Param(mTEPES.lc,    initialize=mTEPES.dPar['pNetFixedCost'].to_dict()    , within=NonNegativeReals,    doc='Electric line fixed cost'                                          )
    mTEPES.pIndBinLineInvest = Param(mTEPES.la,    initialize=mTEPES.dPar['pIndBinLineInvest'].to_dict(), within=Binary          ,    doc='Binary electric line investment decision'                          )
    mTEPES.pIndBinLineSwitch = Param(mTEPES.la,    initialize=mTEPES.dPar['pIndBinLineSwitch'].to_dict(), within=Binary          ,    doc='Binary electric line switching  decision'                          )
    # mTEPES.pSwOnTime       = Param(mTEPES.la,    initialize=mTEPES.dPar['pSwitchOnTime'].to_dict()    , within=NonNegativeIntegers, doc='Minimum switching on  time'                                        )
    # mTEPES.pSwOffTime      = Param(mTEPES.la,    initialize=mTEPES.dPar['pSwitchOffTime'].to_dict()   , within=NonNegativeIntegers, doc='Minimum switching off time'                                        )
    mTEPES.pBigMFlowBck      = Param(mTEPES.la,    initialize=mTEPES.dPar['pBigMFlowBck'].to_dict()     , within=NonNegativeReals,    doc='Maximum backward capacity',                            mutable=True)
    mTEPES.pBigMFlowFrw      = Param(mTEPES.la,    initialize=mTEPES.dPar['pBigMFlowFrw'].to_dict()     , within=NonNegativeReals,    doc='Maximum forward  capacity',                            mutable=True)
    mTEPES.pMaxTheta         = Param(mTEPES.psnnd, initialize=mTEPES.dPar['pMaxTheta'].to_dict()        , within=NonNegativeReals,    doc='Maximum voltage angle',                                mutable=True)
    mTEPES.pAngMin           = Param(mTEPES.la,    initialize=mTEPES.dPar['pAngMin'].to_dict()          , within=           Reals,    doc='Minimum phase angle difference',                       mutable=True)
    mTEPES.pAngMax           = Param(mTEPES.la,    initialize=mTEPES.dPar['pAngMax'].to_dict()          , within=           Reals,    doc='Maximum phase angle difference',                       mutable=True)
    mTEPES.pNetLoInvest      = Param(mTEPES.lc,    initialize=mTEPES.dPar['pNetLoInvest'].to_dict()     , within=NonNegativeReals,    doc='Lower bound of the electric line investment decision', mutable=True)
    mTEPES.pNetUpInvest      = Param(mTEPES.lc,    initialize=mTEPES.dPar['pNetUpInvest'].to_dict()     , within=NonNegativeReals,    doc='Upper bound of the electric line investment decision', mutable=True)
    mTEPES.pIndBinLinePTDF   = Param(mTEPES.la,    initialize=mTEPES.dPar['pIndBinLinePTDF'].to_dict()  , within=Binary          ,    doc='Binary indicator of line with'                                     )
    mTEPES.pMaxNTCFrw        = Param(mTEPES.psnla, initialize=mTEPES.dPar['pMaxNTCFrw'].to_dict()       , within=           Reals,    doc='Maximum NTC forward capacity'                                      )
    mTEPES.pMaxNTCBck        = Param(mTEPES.psnla, initialize=mTEPES.dPar['pMaxNTCBck'].to_dict()       , within=           Reals,    doc='Maximum NTC backward capacity'                                     )
    mTEPES.pMaxNTCMax        = Param(mTEPES.psnla, initialize=mTEPES.dPar['pMaxNTCMax'].to_dict()       , within=           Reals,    doc='Maximum NTC capacity'                                              )

    if mTEPES.dPar['pIndHydrogen'] == 1:
        mTEPES.pH2PipeLength       = Param(mTEPES.pn,  initialize=mTEPES.dPar['pH2PipeLength'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline length',                        mutable=True)
        mTEPES.pH2PipePeriodIni    = Param(mTEPES.pn,  initialize=mTEPES.dPar['pH2PipePeriodIni'].to_dict()   , within=PositiveIntegers,    doc='Installation period'                                          )
        mTEPES.pH2PipePeriodFin    = Param(mTEPES.pn,  initialize=mTEPES.dPar['pH2PipePeriodFin'].to_dict()   , within=PositiveIntegers,    doc='Retirement   period'                                          )
        mTEPES.pH2PipeNTCFrw       = Param(mTEPES.pn,  initialize=mTEPES.dPar['pH2PipeNTCFrw'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC forward'                                )
        mTEPES.pH2PipeNTCBck       = Param(mTEPES.pn,  initialize=mTEPES.dPar['pH2PipeNTCBck'].to_dict()      , within=NonNegativeReals,    doc='Hydrogen pipeline NTC backward'                               )
        mTEPES.pH2PipeFixedCost    = Param(mTEPES.pc,  initialize=mTEPES.dPar['pH2PipeFixedCost'].to_dict()   , within=NonNegativeReals,    doc='Hydrogen pipeline fixed cost'                                 )
        mTEPES.pIndBinH2PipeInvest = Param(mTEPES.pn,  initialize=mTEPES.dPar['pIndBinH2PipeInvest'].to_dict(), within=Binary          ,    doc='Binary   pipeline investment decision'                        )
        mTEPES.pH2PipeLoInvest     = Param(mTEPES.pc,  initialize=mTEPES.dPar['pH2PipeLoInvest'].to_dict()    , within=NonNegativeReals,    doc='Lower bound of the pipeline investment decision', mutable=True)
        mTEPES.pH2PipeUpInvest     = Param(mTEPES.pc,  initialize=mTEPES.dPar['pH2PipeUpInvest'].to_dict()    , within=NonNegativeReals,    doc='Upper bound of the pipeline investment decision', mutable=True)

    if mTEPES.dPar['pIndHeat'] == 1:
        mTEPES.pHeatPipeLength       = Param(mTEPES.hn, initialize=mTEPES.dPar['pHeatPipeLength'].to_dict()      , within=NonNegativeReals, doc='Heat pipe length',                                 mutable=True)
        mTEPES.pHeatPipePeriodIni    = Param(mTEPES.hn, initialize=mTEPES.dPar['pHeatPipePeriodIni'].to_dict()   , within=PositiveIntegers, doc='Installation period'                                           )
        mTEPES.pHeatPipePeriodFin    = Param(mTEPES.hn, initialize=mTEPES.dPar['pHeatPipePeriodFin'].to_dict()   , within=PositiveIntegers, doc='Retirement   period'                                           )
        mTEPES.pHeatPipeNTCFrw       = Param(mTEPES.hn, initialize=mTEPES.dPar['pHeatPipeNTCFrw'].to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC forward'                                         )
        mTEPES.pHeatPipeNTCBck       = Param(mTEPES.hn, initialize=mTEPES.dPar['pHeatPipeNTCBck'].to_dict()      , within=NonNegativeReals, doc='Heat pipe NTC backward'                                        )
        mTEPES.pHeatPipeFixedCost    = Param(mTEPES.hc, initialize=mTEPES.dPar['pHeatPipeFixedCost'].to_dict()   , within=NonNegativeReals, doc='Heat pipe fixed cost'                                          )
        mTEPES.pIndBinHeatPipeInvest = Param(mTEPES.hn, initialize=mTEPES.dPar['pIndBinHeatPipeInvest'].to_dict(), within=Binary          , doc='Binary  heat pipe investment decision'                         )
        mTEPES.pHeatPipeLoInvest     = Param(mTEPES.hc, initialize=mTEPES.dPar['pHeatPipeLoInvest'].to_dict()    , within=NonNegativeReals, doc='Lower bound of the heat pipe investment decision', mutable=True)
        mTEPES.pHeatPipeUpInvest     = Param(mTEPES.hc, initialize=mTEPES.dPar['pHeatPipeUpInvest'].to_dict()    , within=NonNegativeReals, doc='Upper bound of the heat pipe investment decision', mutable=True)

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
    if mTEPES.dPar['pIndHydroTopology'] == 1:
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
    if mTEPES.dPar['pIndHydroTopology'] == 1:
        # reservoirs with outflows
        mTEPES.ro = [(p,sc,rs) for p,sc,rs in mTEPES.psrs if sum(mTEPES.pHydroOutflows [p,sc,n2,rs]() for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    # generators with min/max energy
    mTEPES.gm     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMinEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]
    mTEPES.gM     = [(p,sc,g ) for p,sc,g  in mTEPES.psg  if sum(mTEPES.pMaxEnergy     [p,sc,n2,g ]   for n2 in mTEPES.n2 if (p,sc,n2) in mTEPES.psn)]

    # # if unit availability = 0 changed to 1
    # for g in mTEPES.g:
    #     if  mTEPES.pAvailability[g]() == 0.0:
    #         mTEPES.pAvailability[g]   =  1.0

    # if line length = 0 changed to 110% the geographical distance
    for ni,nf,cc in mTEPES.la:
        if  mTEPES.pLineLength[ni,nf,cc]() == 0.0:
            mTEPES.pLineLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if mTEPES.dPar['pIndHydrogen'] == 1:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pH2PipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pH2PipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    if mTEPES.dPar['pIndHeat'] == 1:
        # if line length = 0 changed to geographical distance with an additional 10%
        for ni,nf,cc in mTEPES.pa:
            if  mTEPES.pHeatPipeLength[ni,nf,cc]() == 0.0:
                mTEPES.pHeatPipeLength[ni,nf,cc]   =  1.1 * 6371 * 2 * math.asin(math.sqrt(math.pow(math.sin((mTEPES.pNodeLat[nf]-mTEPES.pNodeLat[ni])*math.pi/180/2),2) + math.cos(mTEPES.pNodeLat[ni]*math.pi/180)*math.cos(mTEPES.pNodeLat[nf]*math.pi/180)*math.pow(math.sin((mTEPES.pNodeLon[nf]-mTEPES.pNodeLon[ni])*math.pi/180/2),2)))

    # initialize generation output, unit commitment and line switching
    mTEPES.dPar['pInitialOutput'] = pd.DataFrame([[0.0]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.g )
    mTEPES.dPar['pInitialUC']     = pd.DataFrame([[0  ]*len(mTEPES.g )]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.g )
    mTEPES.dPar['pInitialSwitch'] = pd.DataFrame([[0  ]*len(mTEPES.la)]*len(mTEPES.psn), index=mTEPES.psn, columns=mTEPES.la)

    mTEPES.dPar['pInitialOutput'] = filter_rows(mTEPES.dPar['pInitialOutput'], mTEPES.psng )
    mTEPES.dPar['pInitialUC']     = filter_rows(mTEPES.dPar['pInitialUC']    , mTEPES.psng )
    mTEPES.dPar['pInitialSwitch'] = filter_rows(mTEPES.dPar['pInitialSwitch'], mTEPES.psnla)

    mTEPES.pInitialOutput = Param(mTEPES.psng , initialize=mTEPES.dPar['pInitialOutput'].to_dict(), within=NonNegativeReals, doc='unit initial output',     mutable=True)
    mTEPES.pInitialUC     = Param(mTEPES.psng , initialize=mTEPES.dPar['pInitialUC'].to_dict()    , within=Binary,           doc='unit initial commitment', mutable=True)
    mTEPES.pInitialSwitch = Param(mTEPES.psnla, initialize=mTEPES.dPar['pInitialSwitch'].to_dict(), within=Binary,           doc='line initial switching',  mutable=True)

    SettingUpDataTime = time.time() - StartTime
    print('Setting up input data                  ... ', round(SettingUpDataTime), 's')


def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()
    def CreateVariables(mTEPES, OptModel) -> None:
        '''
        Create all mTEPES variables.

        This function takes an mTEPES instance with all parameters and sets created and adds variables to it.

        Parameters:
            mTEPES: The instance of mTEPES.

        Returns:
            None: Variables are added directly to the mTEPES object.
        '''
        #%% variables
        OptModel.vTotalSCost               = Var(                       within=NonNegativeReals, doc='total system                         cost      [MEUR]')
        OptModel.vTotalICost               = Var(                       within=NonNegativeReals, doc='total system investment              cost      [MEUR]')
        OptModel.vTotalFCost               = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed                   cost      [MEUR]')
        OptModel.vTotalGCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable generation  operation cost      [MEUR]')
        OptModel.vTotalCCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable consumption operation cost      [MEUR]')
        OptModel.vTotalECost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system emission                cost      [MEUR]')
        OptModel.vTotalRCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability             cost      [MEUR]')
        OptModel.vTotalNCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total network loss penalty operation cost      [MEUR]')
        OptModel.vTotalEmissionArea        = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                         [MtCO2]')
        OptModel.vTotalECostArea           = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                cost      [MEUR]')
        OptModel.vTotalRESEnergyArea       = Var(mTEPES.psnar, within=NonNegativeReals, doc='        RES energy                              [GWh]')

        OptModel.vTotalOutput              = Var(mTEPES.psng , within=NonNegativeReals, doc='total output of the unit                         [GW]')
        OptModel.vOutput2ndBlock           = Var(mTEPES.psnnr, within=NonNegativeReals, doc='second block of the unit                         [GW]')
        OptModel.vReserveUp                = Var(mTEPES.psnnr, within=NonNegativeReals, doc='upward   operating reserve                       [GW]')
        OptModel.vReserveDown              = Var(mTEPES.psnnr, within=NonNegativeReals, doc='downward operating reserve                       [GW]')
        OptModel.vEnergyInflows            = Var(mTEPES.psnec, within=NonNegativeReals, doc='unscheduled inflows  of candidate ESS units      [GW]')
        OptModel.vEnergyOutflows           = Var(mTEPES.psnes, within=NonNegativeReals, doc='scheduled   outflows of all       ESS units      [GW]')
        OptModel.vESSInventory             = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS inventory                                   [GWh]')
        OptModel.vESSSpillage              = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS spillage                                    [GWh]')
        OptModel.vIniInventory             = Var(mTEPES.psnec, within=NonNegativeReals, doc='initial inventory for ESS candidate             [GWh]')

        OptModel.vESSTotalCharge           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS total charge power                           [GW]')
        OptModel.vCharge2ndBlock           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS       charge power                           [GW]')
        OptModel.vESSReserveUp             = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS upward   operating reserve                   [GW]')
        OptModel.vESSReserveDown           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS downward operating reserve                   [GW]')
        OptModel.vENS                      = Var(mTEPES.psnnd, within=NonNegativeReals, doc='energy not served in node                        [GW]')

        if mTEPES.pIndHydroTopology == 1:
            OptModel.vHydroInflows         = Var(mTEPES.psnrc, within=NonNegativeReals, doc='unscheduled inflows  of candidate hydro units  [m3/s]')
            OptModel.vHydroOutflows        = Var(mTEPES.psnrs, within=NonNegativeReals, doc='scheduled   outflows of all       hydro units  [m3/s]')
            OptModel.vReservoirVolume      = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir volume                                [hm3]')
            OptModel.vReservoirSpillage    = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir spillage                              [hm3]')

        if mTEPES.pIndHeat == 1:
            OptModel.vTotalOutputHeat      = Var(mTEPES.psng , within=NonNegativeReals, doc='total heat output of the boiler unit             [GW]')
            [OptModel.vTotalOutputHeat[p,sc,n,ch].setub(mTEPES.pMaxPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
            [OptModel.vTotalOutputHeat[p,sc,n,ch].setlb(mTEPES.pMinPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
            # only boilers are forced to produce at their minimum heat power. CHPs are not forced to produce at their minimum heat power, they are committed or not to produce electricity

        if mTEPES.pIndBinGenInvest() != 1:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=UnitInterval,     doc='generation       investment decision exists in a year [0,1]')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=UnitInterval,     doc='generation       investment decision done   in a year [0,1]')
        else:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=Binary,           doc='generation       investment decision exists in a year {0,1}')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=Binary,           doc='generation       investment decision done   in a year {0,1}')

        if mTEPES.pIndBinGenRetire() != 1:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=UnitInterval,     doc='generation       retirement decision exists in a year [0,1]')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=UnitInterval,     doc='generation       retirement decision exists in a year [0,1]')
        else:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=Binary,           doc='generation       retirement decision exists in a year {0,1}')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=Binary,           doc='generation       retirement decision exists in a year {0,1}')

        if mTEPES.pIndBinNetElecInvest() != 1:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=UnitInterval,     doc='electric network investment decision exists in a year [0,1]')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=UnitInterval,     doc='electric network investment decision exists in a year [0,1]')
        else:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=Binary,           doc='electric network investment decision exists in a year {0,1}')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=Binary,           doc='electric network investment decision exists in a year {0,1}')

        if mTEPES.pIndHydroTopology == 1:
            if mTEPES.pIndBinRsrInvest() != 1:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
            else:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')

        if mTEPES.pIndHydrogen == 1:
            if mTEPES.pIndBinNetH2Invest() != 1:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
            else:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')

        if mTEPES.pIndHeat == 1:
            if mTEPES.pIndBinGenInvest() != 1:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=UnitInterval, doc='generation       investment decision exists in a year [0,1]')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=UnitInterval, doc='generation       investment decision done   in a year [0,1]')
            else:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=Binary,       doc='generation       investment decision exists in a year {0,1}')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=Binary,       doc='generation       investment decision done   in a year {0,1}')
            if mTEPES.pIndBinNetHeatInvest() != 1:
                OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=UnitInterval, doc='heat network investment decision exists in a year [0,1]'    )
                OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=UnitInterval, doc='heat network investment decision exists in a year [0,1]'    )
            else:
                OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=Binary,       doc='heat network investment decision exists in a year {0,1}'    )
                OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=Binary,       doc='heat network investment decision exists in a year {0,1}'    )

        if mTEPES.pIndBinGenOperat() == 0:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='commitment         of the unit                        [0,1]')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='startup            of the unit                        [0,1]')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='shutdown           of the unit                        [0,1]')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='stable    state    of the unit                        [0,1]')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp up   state    of the unit                        [0,1]')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp down state    of the unit                        [0,1]')

            OptModel.vMaxCommitmentYearly  = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=UnitInterval, initialize=0.0, doc='maximum commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly  = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=UnitInterval, initialize=0.0, doc='maximum commitment of the unit hourly [0,1]')

            if mTEPES.pIndHydroTopology == 1:
                OptModel.vCommitmentCons   = Var(mTEPES.psnh,  within=UnitInterval,     doc='consumption commitment of the unit                    [0,1]')

        else:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='commitment         of the unit                        {0,1}')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='startup            of the unit                        {0,1}')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='shutdown           of the unit                        {0,1}')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='stable    state    of the unit                        {0,1}')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp up   state    of the unit                        {0,1}')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp down state    of the unit                        {0,1}')

            OptModel.vMaxCommitmentYearly  = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=Binary, initialize=0.0, doc='maximum commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly  = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=Binary, initialize=0.0, doc='maximum commitment of the unit hourly [0,1]')
            if mTEPES.pIndHydroTopology == 1:
                OptModel.vCommitmentCons   = Var(mTEPES.psnh,  within=Binary,           doc='consumption commitment of the unit                    {0,1}')

        if mTEPES.pIndBinLineCommit() == 0:
            OptModel.vLineCommit           = Var(mTEPES.psnla, within=UnitInterval,     doc='line switching      of the electric line              [0,1]')
        else:
            OptModel.vLineCommit           = Var(mTEPES.psnla, within=Binary,           doc='line switching      of the electric line              {0,1}')

        if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
            if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineCommit() == 0:
                OptModel.vLineOnState      = Var(mTEPES.psnla, within=UnitInterval,     doc='switching on  state of the electric line              [0,1]')
                OptModel.vLineOffState     = Var(mTEPES.psnla, within=UnitInterval,     doc='switching off state of the electric line              [0,1]')
            else:
                OptModel.vLineOnState      = Var(mTEPES.psnla, within=Binary,           doc='switching on  state of the electric line              {0,1}')
                OptModel.vLineOffState     = Var(mTEPES.psnla, within=Binary,           doc='switching off state of the electric line              {0,1}')

    CreateVariables(mTEPES, mTEPES)
    # assign lower and upper bounds to variables
    def setVariableBounds(mTEPES, OptModel) -> None:
        '''
        Set upper/lower bounds.

        This function takes an mTEPES instance and adds lower/upper bounds to variables which are limited by a parameter.

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
        [OptModel.vENS           [p,sc,n,nd].setub(mTEPES.pDemandElecPos    [p,sc,n,nd]  ) for p,sc,n,nd in mTEPES.psnnd]

        if mTEPES.pIndHydroTopology == 1:
            [OptModel.vHydroInflows   [p,sc,n,rc].setub(mTEPES.pHydroInflows[p,sc,n,rc]()) for p,sc,n,rc in mTEPES.psnrc]
            [OptModel.vHydroOutflows  [p,sc,n,rs].setub(mTEPES.pMaxOutflows [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setlb(mTEPES.pMinVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setub(mTEPES.pMaxVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]

    setVariableBounds(mTEPES, mTEPES)

    nFixedVariables = 0
    def RelaxBinaryInvestmentConditions(mTEPES, OptModel) -> int:
        '''
        Relax binary investment variables.

        This function takes an mTEPES instance, relaxes binary investment conditions and calculates the number of variables fixed in the process.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The number of fixed variables.
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
            # fix variables for units that don't have minimum stable time
            if mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
                OptModel.vStableState  [p,sc,n,nr].fix(0)
                OptModel.vRampDwState  [p,sc,n,nr].fix(0)
                OptModel.vRampUpState  [p,sc,n,nr].fix(0)

        for p,sc,nr,  group in mTEPES.psnr * mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0 and nr in mTEPES.ExclusiveGeneratorsYearly:
                OptModel.vMaxCommitmentYearly[p,sc,  nr,group].domain = UnitInterval
        for p,sc,n,nr,group in mTEPES.psnnr * mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0 and nr in mTEPES.ExclusiveGeneratorsHourly:
                OptModel.vMaxCommitmentHourly[p,sc,n,nr,group].domain = UnitInterval
        if mTEPES.pIndHydroTopology == 1:
            for p,sc,n,h in mTEPES.psnh:
                if mTEPES.pIndBinUnitCommit[h] == 0:
                    OptModel.vCommitmentCons[p,sc,n,h].domain = UnitInterval
                if mTEPES.pMaxCharge[p,sc,n,h] == 0.0:
                    OptModel.vCommitmentCons[p,sc,n,h].fix(0)
                    nFixedBinaries += 1

        return nFixedBinaries

    # call the relaxing variables function and add its output to nFixedVariables
    nFixedBinaries = RelaxBinaryInvestmentConditions(mTEPES, mTEPES)
    nFixedVariables += nFixedBinaries

    def CreateFlowVariables(mTEPES,OptModel) -> int:
        #TODO use a more descriptive name for nFixedVariables
        '''
                Create electricity, hydrogen and heat-flow-related variables.

                This function takes a mTEPES instance and adds the variables necessary to model power, hydrogen and heat flows in a network.

                Parameters:
                    mTEPES: The instance of mTEPES.
                    OptModel:

                Returns:
                    int: The number of line commitment variables fixed
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

        if mTEPES.pIndVarTTC == 1:
            # lines with TTC and TTCBck = 0 are disconnected and the flow is fixed to 0
            [OptModel.vFlowElec[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] == 0.0 and mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0]
            nFixedVariables += sum(                    1  for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] == 0.0 and mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0)

        if mTEPES.pIndPTDF == 1:
            OptModel.vNetPosition = Var(mTEPES.psnnd, within=Reals, doc='net position in node [GW]')

        [OptModel.vLineLosses[p,sc,n,ni,nf,cc].setub(0.5*mTEPES.pLineLossFactor[ni,nf,cc]*mTEPES.pLineNTCMax[ni,nf,cc]) for p,sc,n,ni,nf,cc in mTEPES.psnll]
        if mTEPES.pIndBinSingleNode() == 0:
            [OptModel.vFlowElec[p,sc,n,ni,nf,cc].setlb(-mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]   ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
            [OptModel.vFlowElec[p,sc,n,ni,nf,cc].setub( mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]   ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
        [OptModel.vTheta       [p,sc,n,nd      ].setlb(-mTEPES.pMaxTheta [p,sc,n,nd      ]() ) for p,sc,n,nd       in mTEPES.psnnd]
        [OptModel.vTheta       [p,sc,n,nd      ].setub( mTEPES.pMaxTheta [p,sc,n,nd      ]() ) for p,sc,n,nd       in mTEPES.psnnd]

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

            This function takes an mTEPES instance and fixes commitment-related variables for must run units, ESS units and units with no minimum power.

            Parameters:
                mTEPES: The instance of mTEPES.
                OptModel:

            Returns:
                int: The number of commitment variables fixed.
            '''
        nFixedVariables = 0

        # fix the must-run existing units and their output
        # must-run units must produce at least their minimum output
        [OptModel.vTotalOutput[p,sc,n,g].setlb(mTEPES.pMinPowerElec[p,sc,n,g]) for p,sc,n,g in mTEPES.psng if mTEPES.pMustRun[g] == 1 and g not in mTEPES.gc]

        # if no max power, no total output
        [OptModel.vTotalOutput[p,sc,n,g].fix(0.0) for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0]
        nFixedVariables += sum(                1  for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0)

        for p,sc,n,nr in mTEPES.psnnr:
            # must-run existing units or units with no minimum power, or ESS existing units are always committed and must produce at least their minimum output
            # not applicable to mutually exclusive units
            if   len(mTEPES.ExclusiveGroups) == 0:
                if (mTEPES.pMustRun[nr] == 1 and nr not in mTEPES.gc or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    nFixedVariables += 3
            # If there are mutually exclusive groups do not fix variables from ESS in mutually exclusive groups
            elif len(mTEPES.ExclusiveGroups) >  0 and nr not in mTEPES.ExclusiveGenerators:
                if (mTEPES.pMustRun[nr] == 1 or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    nFixedVariables += 3

            # if min and max power coincide there are neither second block, nor operating reserve
            if  mTEPES.pMaxPower2ndBlock [p,sc,n,nr] ==  0.0:
                OptModel.vOutput2ndBlock [p,sc,n,nr].fix(0.0)
                OptModel.vReserveUp      [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown    [p,sc,n,nr].fix(0.0)
                nFixedVariables += 3
            if  mTEPES.pIndOperReserveGen[       nr] ==  1:
                OptModel.vReserveUp      [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown    [p,sc,n,nr].fix(0.0)
                nFixedVariables += 2

        # total energy inflows per storage
        pTotalEnergyInflows = pd.Series([sum(mTEPES.pEnergyInflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,sc,n,es) in mTEPES.psnes) for es in mTEPES.es], index=mTEPES.es)
        pTotalMaxCharge     = pd.Series([sum(mTEPES.pMaxCharge[p,sc,n,es]       for p,sc,n in mTEPES.psn if (p,sc,n,es) in mTEPES.psnes) for es in mTEPES.es], index=mTEPES.es)
        mTEPES.pTotalEnergyInflows = Param(mTEPES.es, initialize=pTotalEnergyInflows.to_dict(), within=NonNegativeReals, doc='Total energy outflows')
        mTEPES.pTotalMaxCharge     = Param(mTEPES.es, initialize=pTotalMaxCharge.to_dict(),     within=NonNegativeReals, doc='Total maximum charge' )

        for p,sc,n,es in mTEPES.psnes:
            # ESS with no charge capacity
            if  mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0:
                OptModel.vESSTotalCharge [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            # ESS with no charge capacity and no inflows can't produce
            if  pTotalMaxCharge[es] == 0.0 and pTotalEnergyInflows[es] == 0.0:
                OptModel.vTotalOutput    [p,sc,n,es].fix(0.0)
                OptModel.vOutput2ndBlock [p,sc,n,es].fix(0.0)
                OptModel.vReserveUp      [p,sc,n,es].fix(0.0)
                OptModel.vReserveDown    [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage    [p,sc,n,es].fix(0.0)
                OptModel.vESSInventory   [p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
                nFixedVariables += 5
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0:
                OptModel.vCharge2ndBlock [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0 or mTEPES.pIndOperReserveCon[es] == 1:
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
                    OptModel.vCommitmentCons [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 2
                if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0:
                    OptModel.vCharge2ndBlock [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 1
                if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0 or mTEPES.pIndOperReserveCon[h ] == 1:
                    OptModel.vESSReserveUp   [p,sc,n,h ].fix(0.0)
                    OptModel.vESSReserveDown [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 2
        return nFixedVariables
    nFixedGeneratorCommits = FixGeneratorsCommitment(mTEPES,mTEPES)
    nFixedVariables       += nFixedGeneratorCommits
    # thermal, ESS, and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if mTEPES.tq:
        mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.sq])
    else:
        if mTEPES.pIndHydroTopology == 1:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__)])
        else:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.h])

    g2a = defaultdict(list)
    for ar,g in mTEPES.ar*mTEPES.g:
        if (ar,g) in mTEPES.a2g:
            g2a[ar].append(g)

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt and mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                      (p,sc,st,nn) in mTEPES.s2n ])

        if mTEPES.n:
            # determine the first load level of each stage
            n1 = (p,sc,mTEPES.n.first())
            # commit the units of each area and their output at the first load level of each stage
            for ar in mTEPES.ar:
                pSystemOutput = 0.0
                for nr in mTEPES.nr:
                    if nr in g2a[ar] and (p,nr) in mTEPES.pnr and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd if (nd,ar) in mTEPES.ndar) and mTEPES.pMustRun[nr] == 1:
                        mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPowerElec [n1,nr]
                        mTEPES.pInitialUC    [n1,nr] = 1
                        pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

                # determine the initially committed units and their output at the first load level of each period, scenario, and stage
                for go in mTEPES.go:
                    if go in g2a[ar] and (p,go) in mTEPES.pg and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in mTEPES.nd if (nd,ar) in mTEPES.ndar) and mTEPES.pMustRun[go] == 0:
                        if go in mTEPES.re:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPowerElec [n1,go]
                        else:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPowerElec [n1,go]
                        mTEPES.pInitialUC[n1,go]         = 1
                        pSystemOutput                   += mTEPES.pInitialOutput[n1,go]()

            # determine the initially committed lines
            for la in mTEPES.la:
                if la in mTEPES.lc:
                    mTEPES.pInitialSwitch[n1,la] = 0
                else:
                    mTEPES.pInitialSwitch[n1,la] = 1

            # fixing the ESS inventory at the last load level of the stage for every period and scenario if between storage limits
            for es in mTEPES.es:
                if es not in mTEPES.ec and (p,es) in mTEPES.pes:
                    OptModel.vESSInventory[p,sc,mTEPES.n.last(),es].fix(mTEPES.pIniInventory[p,sc,mTEPES.n.last(),es])

            if mTEPES.pIndHydroTopology == 1:
                # fixing the reservoir volume at the last load level of the stage for every period and scenario if between storage limits
                for rs in mTEPES.rs:
                    if rs not in mTEPES.rn:
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

    # if no operating reserve is required, no variables are needed
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

    # if there are no energy outflows, no variable is needed
    for es in mTEPES.es:
        if sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
            for p,sc,n in mTEPES.psn:
                if (p,es) in mTEPES.pes:
                    OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    if mTEPES.pIndHydroTopology == 1:
        # if there are no hydro outflows, no variable is needed
        for rs in mTEPES.rs:
            if sum(mTEPES.pHydroOutflows[p,sc,n,rs]() for p,sc,n in mTEPES.psn if (p,rs) in mTEPES.prs) == 0.0:
                for p,sc,n in mTEPES.psn:
                    if (p,rs) in mTEPES.prs:
                        OptModel.vHydroOutflows[p,sc,n,rs].fix(0.0)
                        nFixedVariables += 1

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    if mTEPES.pIndBinSingleNode() == 0:
        for p,sc,n in mTEPES.psn:
            OptModel.vTheta[p,sc,n,mTEPES.rf.first()].fix(0.0)
            nFixedVariables += 1

    # fixing the ENS in nodes with no demand
    for p,sc,n,nd in mTEPES.psnnd:
        if mTEPES.pDemandElec[p,sc,n,nd] <=  0.0:
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

        This function takes an mTEPES instance and fixes all installation and retirement variables to 0 if they are not allowed in the corresponding period.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The number of variables fixed.
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
                    OptModel.vHydroOutflows         [p,sc,n,rs].fix(0.0)
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
    nFixedVariables += sum(                      4    for p,sc,n,ni,nf,cc in mTEPES.psnla if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p)

    [OptModel.vLineLosses  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p]
    nFixedVariables += sum(                      1    for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and mTEPES.pElecNetPeriodIni [ni,nf,cc] > p)

    if mTEPES.pIndHydrogen == 1:
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnpa if (ni,nf,cc) not in mTEPES.pc and mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p]
        nFixedVariables += sum(                  4    for p,sc,n,ni,nf,cc in mTEPES.psnpa if (ni,nf,cc) not in mTEPES.pc and mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p)

    if mTEPES.pIndHeat == 1:
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnha if (ni,nf,cc) not in mTEPES.hc and mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p]
        nFixedVariables += sum(                  4    for p,sc,n,ni,nf,cc in mTEPES.psnha if (ni,nf,cc) not in mTEPES.hc and mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p)

    # tolerance to consider 0 an investment decision
    pEpsilon = 1e-4
    def SetToZero(mTEPES, OptModel, pEpsilon) -> None:
        '''
        Set small numbers to 0.

        This function takes an mTEPES instance and sets values under a certain threshold to be 0.

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

        if len(mTEPES.p ) == 0:
            raise ValueError('### No active periods in the case study'  )
        if len(mTEPES.sc) == 0:
            raise ValueError('### No active scenarios in the case study')
        if len(mTEPES.st) == 0:
            raise ValueError('### No active stages in the case study'   )

        # detecting infeasibility: sum of scenario probabilities must be 1 in each period
        # for p in mTEPES.p:
        #     if abs(sum(mTEPES.pScenProb[p,sc] for sc in mTEPES.sc)-1.0) > 1e-6:
        #         raise ValueError('### Sum of scenario probabilities different from 1 in period ', p)

        for es in mTEPES.es:
            # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows
            if sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) > 0.0:
                raise ValueError('### Total minimum output greater than total inflows for ESS unit ', es, ' by ', sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')
            if sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) < 0.0:
                raise ValueError('### Total maximum charge lower than total outflows for ESS unit ',  es, ' by ', sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) - sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')

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

        # detecting infeasibility: no capacity in the transmission network
        if sum(mTEPES.pLineNTCMax[:,:,:]) == 0.0:
            raise ValueError('### There is no capacity in the network. All the lines have NTC zero probably due to security factor equal to zero')

        # detecting reserve margin infeasibility
        for p,ar in mTEPES.p*mTEPES.ar:
            if     sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g) < mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]:
                raise     ValueError('### Electricity reserve margin infeasibility ', p,ar, sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g), mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

            if mTEPES.pIndHeat == 1:
                if sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g) < mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
                    raise ValueError('### Heat reserve margin infeasibility ',        p,ar, sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and (ar,g) in mTEPES.a2g), mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

        for p,sc,ar in mTEPES.p*mTEPES.sc*mTEPES.ar:
            if mTEPES.pRESEnergy[p,ar] > sum(mTEPES.pDemandElec[p,sc,n,nd]*mTEPES.pLoadLevelDuration[p,sc,n]() for n,nd in mTEPES.n*mTEPES.nd if (nd,ar) in mTEPES.ndar and (p,sc,n,nd) in mTEPES.psnnd):
                raise ValueError('### Minimum renewable energy requirement exceeds the demand ', p, sc, ar, mTEPES.pRESEnergy[p,ar], sum(mTEPES.pDemandElec[p,sc,n,nd] for n,nd in mTEPES.n*mTEPES.nd if  (nd,ar) in mTEPES.ndar and (p,sc,n,nd) in mTEPES.psnnd))

    DetectInfeasibilities(mTEPES)

    mTEPES.nFixedVariables    = Param(initialize=round(nFixedVariables), within=NonNegativeIntegers, doc='Number of fixed variables')

    mTEPES.IndependentPeriods = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages  = Param(mTEPES.pp, domain=Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages2 = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel           = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel           = True
    if (    (len(mTEPES.gc) == 0 or mTEPES.pIndBinGenInvest()     == 2)   # No candidates
        and (len(mTEPES.gd) == 0 or mTEPES.pIndBinGenRetire()     == 2)   # No retirements
        and (len(mTEPES.lc) == 0 or mTEPES.pIndBinNetElecInvest() == 2)): # No line candidates
        # Periods and scenarios are independent each other
        ScIndep = True
        mTEPES.IndependentPeriods = True
        for p in mTEPES.p:
            if (    (min([mTEPES.pEmission[p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)  # No emissions
                and (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) == 0)):                                                                # No minimum RES requirements
            # Stages are independent from each other
                StIndep = True
                mTEPES.IndependentStages[p] = True
    if all(mTEPES.IndependentStages[p]() for p in mTEPES.pp):
        mTEPES.IndependentStages2 = True

    mTEPES.Period = Block(mTEPES.p)
    for p in mTEPES.Period:
        Period = mTEPES.Period[p]
        #TODO: Filter in some way that scenarios may not belong to periods
        # period2scenario = [stt for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p]
        Period.Scenario = Block(mTEPES.sc)
        Period.n        = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if pp == p])
        for sc in Period.Scenario:
            Scenario       = Period.Scenario[sc]
            Scenario.Stage = Block(Set(initialize=[stt for pp,scc,stt, nn in mTEPES.s2n if scc == sc and pp == p]))
            Scenario.n     = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p])

        # iterative model formulation for each stage of a year
            for st in Scenario.Stage:
                Stage    = Scenario.Stage[st]
                Stage.n  = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])
                Stage.n2 = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])

                # load levels multiple of cycles for each ESS/generator
                Stage.nesc = [(n, es) for n,es in Stage.n * mTEPES.es if Stage.n.ord(n) % mTEPES.pStorageTimeStep[es]  == 0]
                Stage.necc = [(n, ec) for n,ec in Stage.n * mTEPES.ec if Stage.n.ord(n) % mTEPES.pStorageTimeStep[ec]  == 0]
                Stage.neso = [(n, es) for n,es in Stage.n * mTEPES.es if Stage.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0]
                Stage.ngen = [(n, g ) for n,g  in Stage.n * mTEPES.g  if Stage.n.ord(n) % mTEPES.pEnergyTimeStep[g]    == 0]

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
