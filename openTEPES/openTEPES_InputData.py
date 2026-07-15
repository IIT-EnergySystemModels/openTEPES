"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 15, 2026
"""

import time
import math
import os
import pandas        as pd
from   pyomo.environ import Set

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_InputSource    import open_source, df_to_set_values, InputSource
    from .openTEPES_InputCSVSource import CSVSource
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSource    import df_to_set_values, InputSource
    from openTEPES.openTEPES_InputCSVSource import CSVSource

# from line_profiler import profile


# @profile
def InputData(DirName, CaseName, mTEPES, pIndLogConsole):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # set_definitions: maps each mTEPES Set attribute to the underlying
    # dictionary file stem and whether the Set is ordered. The 'ordered'
    # flag was previously a hardcoded membership check in the read loop;
    # making it declarative keeps the policy next to the data.
    set_definitions = {
        # attr   (dict_stem,      ordered)
        'pp':    ('Period',       True ),
        'scc':   ('Scenario',     True ),
        'stt':   ('Stage',        True ),
        'nn':    ('LoadLevel',    True ),
        'gg':    ('Generation',   True ),
        'gt':    ('Technology',   False),
        'nd':    ('Node',         False),
        'ni':    ('Node',         False),
        'nf':    ('Node',         False),
        'zn':    ('Zone',         True ),
        'ar':    ('Area',         True ),
        'rg':    ('Region',       True ),
        'cc':    ('Circuit',      False),
        'c2':    ('Circuit',      False),
        'lt':    ('Line',         True ),
        'ndzn':  ('NodeToZone',   False),
        'znar':  ('ZoneToArea',   False),
        'arrg':  ('AreaToRegion', False),
    }

    # Source resolution: prefer mTEPES.pInputSource if openTEPES_run set
    # one (DuckDB or CSV); otherwise build a CSVSource from (DirName,
    # CaseName). The CSV path through CSVSource is byte-identical to the
    # historical pd.read_csv calls.
    source: InputSource = getattr(mTEPES, "pInputSource", None) or CSVSource(_path)
    mTEPES.pInputSource = source  # make accessible to DataConfiguration etc.

    # Reading dictionaries through the source. df_to_set_values converts
    # a 1-col DataFrame -> list of values, an n-col DataFrame -> list of
    # tuples (relation/membership), which is exactly the shape
    # Set(initialize=...) accepts.
    for set_name, (dict_stem, is_ordered) in set_definitions.items():
        df = source.read_dict(dict_stem)
        values = df_to_set_values(df)
        setattr(mTEPES, set_name, Set(initialize=values, ordered=is_ordered, doc=dict_stem))

    HEADER_LEVELS = {
        'VariableTTCFrw': [0, 1, 2   ],
        'VariableTTCBck': [0, 1, 2   ],
        'VariablePTDF'  : [0, 1, 2, 3],
    }
    FLAG_MAPPING = {
        'RampReserveUp'             : ('pIndRampReserves',      None, 'No ramp reserves'                    ),
        'RampReserveDown'           : ('pIndRampReserves',      None, 'No ramp reserves'                    ),
        'OperatingReserveDownEnergy': ('pIndReserveActivation', None, 'No operating reserve activation'     ),
        'OperatingReserveUpEnergy'  : ('pIndReserveActivation', None, 'No operating reserve activation'     ),
        'VariableTTCFrw'            : ('pIndVarTTC'           , None, 'No variable transmission line TTCs'  ),
        'VariableTTCBck'            : ('pIndVarTTC'           , None, 'No variable transmission line TTCs'  ),
        'VariablePTDF'              : ('pIndPTDF'             , None, 'No flow-based market coupling method'),
        'Reservoir'                 : ('pIndHydroTopology'    , None, 'No hydropower topology'              ),
        'VariableMinVolume'         : ('pIndHydroTopology'    , None, 'No hydropower topology'              ),
        'VariableMaxVolume'         : ('pIndHydroTopology'    , None, 'No hydropower topology'              ),
        'HydroInflows'              : ('pIndHydroTopology'    , None, 'No hydropower topology'              ),
        'HydroOutflows'             : ('pIndHydroTopology'    , None, 'No hydropower topology'              ),
        'DemandHydrogen'            : ('pIndHydrogen'         , None, 'No hydrogen energy carrier'          ),
        'NetworkHydrogen'           : ('pIndHydrogen'         , None, 'No hydrogen energy carrier'          ),
        'DemandHeat'                : ('pIndHeat'             , None, 'No heat energy carrier'              ),
        'ReserveMarginHeat'         : ('pIndHeat'             , None, 'No heat energy carrier'              ),
        'NetworkHeat'               : ('pIndHeat'             , None, 'No heat energy carrier'              ),
    }

    def read_input_data():
        """Read every oT_Data table the source knows about.

        Returns (dfs, par) — dfs maps 'df{stem}' to its wide-format
        (indexed where applicable) DataFrame; par carries the per-feature
        availability flags driven by FLAG_MAPPING.
        """
        dfs: dict[str, pd.DataFrame] = {}
        par: dict[str, int] = {}

        for fs in source.list_data_stems():
            dp_key, _, _ = FLAG_MAPPING.get(fs, (None, None, None))
            header = HEADER_LEVELS.get(fs)
            try:
                dfs[f'df{fs}'] = source.read_data(fs, header_levels=header)
                if dp_key:
                    par[dp_key] = 1
            except FileNotFoundError:
                print(f'WARNING: table not found: oT_Data_{fs}_{CaseName}.csv')
                if dp_key:
                    par[dp_key] = 0
            except Exception as e:
                print(f'No data for {fs}: {e}')
                if dp_key:
                    par[dp_key] = 0

        return dfs, par

    dfs, par = read_input_data()
    # if 'pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat' are not in par, add them and set their value to zero
    for key in ['pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat']:
        if key not in par.keys():
            par[key] = 0

    # replace NaN with 0 (only on numeric columns to avoid dtype errors on string columns)
    for key,df in dfs.items():
        num_cols = df.select_dtypes(include='number').columns
        if 'dfEmission' in key:
            df.fillna({col: math.inf for col in num_cols}, inplace=True)
        elif 'dfGeneration' in key:
            # build a dict that gives 1.0 for 'Efficiency', 0.0 for everything else
            fill_values = {col: (1.0 if col == 'Efficiency' else 0.0) for col in num_cols}
            # one pass over the DataFrame
            df.fillna(fill_values, inplace=True)
        else:
            df.fillna({col: 0.0 for col in num_cols}, inplace=True)

    # Define prefixes and suffixes
    mTEPES.gen_frames_suffixes      = ['VariableMinGeneration',  'VariableMaxGeneration',
                                       'VariableMinConsumption', 'VariableMaxConsumption',
                                       'VariableMinStorage',     'VariableMaxStorage',
                                       'EnergyInflows',          'EnergyOutflows',
                                       'VariableMinEnergy',      'VariableMaxEnergy',
                                       'VariableFuelCost',       'VariableEmissionCost',]
    mTEPES.node_frames_suffixes     = ['Demand', 'Inertia']
    mTEPES.area_frames_suffixes     = ['RampReserveUp', 'RampReserveDown', 'OperatingReserveUp', 'OperatingReserveDown', 'OperatingReserveUpEnergy', 'OperatingReserveDownEnergy', 'ReserveMargin', 'Emission', 'RESEnergy']
    mTEPES.hydro_frames_suffixes    = ['Reservoir', 'VariableMinVolume', 'VariableMaxVolume', 'HydroInflows', 'HydroOutflows']
    mTEPES.hydrogen_frames_suffixes = ['DemandHydrogen']
    mTEPES.heat_frames_suffixes     = ['DemandHeat', 'ReserveMarginHeat']
    mTEPES.frames_suffixes = mTEPES.gen_frames_suffixes + mTEPES.node_frames_suffixes + mTEPES.area_frames_suffixes + mTEPES.hydro_frames_suffixes + mTEPES.hydrogen_frames_suffixes + mTEPES.heat_frames_suffixes

    # Clamp negatives to zero on every generator-keyed wide table.
    for keys, df in dfs.items():
        if any(suffix in keys for suffix in mTEPES.gen_frames_suffixes):
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
        if pIndLogConsole and any(suffix in key for suffix in mTEPES.frames_suffixes):
            print(f'{key}:\n', df.describe(), '\n')
    # Optional reservoir / hydro topology dicts. Each is present in the
    # source iff the user populated the corresponding oT_Dict_*.csv (or
    # DB table); an absent / empty dict yields an empty Pyomo Set.
    reservoir_dicts = [
        ('rs',  'Reservoir',                 'reservoirs'                 ),
        ('r2h', 'ReservoirToHydro',          'reservoir to hydro'         ),
        ('h2r', 'HydroToReservoir',          'hydro to reservoir'         ),
        ('r2r', 'ReservoirToReservoir',      'reservoir 1 to reservoir 2' ),
        ('p2r', 'PumpedHydroToReservoir',    'pumped-hydro to reservoir'  ),
        ('r2p', 'ReservoirToPumpedHydro',    'reservoir to pumped-hydro'  ),
    ]
    for set_name, dict_stem, doc in reservoir_dicts:
        df = source.read_dict(dict_stem)
        values = df_to_set_values(df) if not df.empty else []
        setattr(mTEPES, set_name, Set(initialize=values, doc=doc))

    # load parameters from dfOption — single-row 0/1 binary flags.
    # Direct int() avoids the unusual .iloc[0].astype('int') pattern
    # (astype on a numpy scalar works but is unidiomatic).
    for col in dfs['dfOption'].columns:
        par[f'p{col}'] = int(dfs['dfOption'][col].iloc[0])

    # load parameters from dfParameter — single-row mixed scalars.
    for col in dfs['dfParameter'].columns:
        v = dfs['dfParameter'][col].iloc[0]
        if col in ['ENSCost', 'HNSCost', 'HTNSCost', 'SBase']:
            par[f'p{col}'] = v * 1e-3
        elif col == 'TimeStep':
            par[f'p{col}'] = int(v)
        else:
            par[f'p{col}'] = v

    par['pPeriodWeight']         = dfs['dfPeriod']       ['Weight'        ].astype('int')                            # weights of periods                        [p.u.]
    par['pScenProb']             = dfs['dfScenario']     ['Probability'   ].astype('float64')                        # probabilities of scenarios                [p.u.]
    par['pStageWeight']          = dfs['dfStage']        ['Weight'        ].astype('float64')                        # weights of stages
    par['pDuration']             = dfs['dfDuration']     ['Duration'      ] * par['pTimeStep']                       # duration of load levels                   [h]
    par['pLevelToStage']         = dfs['dfDuration']     ['Stage'         ]                                          # load levels assignment to stages
    par['pReserveMargin']        = dfs['dfReserveMargin']['ReserveMargin' ]                                          # minimum adequacy reserve margin           [p.u.]
    par['pEmission']             = dfs['dfEmission']     ['CO2Emission'   ]                                          # maximum CO2 emission                      [MtCO2]
    par['pRESEnergy']            = dfs['dfRESEnergy']    ['RESEnergy'     ]                                          # minimum RES energy                        [GWh]
    par['pDemandElec']           = dfs['dfDemand'                ].reindex(columns=mTEPES.nd, fill_value=0.0) * 1e-3 # electric demand                           [GW]
    par['pSystemInertia']        = dfs['dfInertia'               ].reindex(columns=mTEPES.ar, fill_value=0.0)        # inertia                                   [s]
    par['pOperReserveUp']        = dfs['dfOperatingReserveUp'    ].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # up   operating reserve                    [GW]
    par['pOperReserveDw']        = dfs['dfOperatingReserveDown'  ].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # down operating reserve                    [GW]
    par['pVariableMinPowerElec'] = dfs['dfVariableMinGeneration' ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum power            [GW]
    par['pVariableMaxPowerElec'] = dfs['dfVariableMaxGeneration' ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum power            [GW]
    par['pVariableMinCharge']    = dfs['dfVariableMinConsumption'].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum charge           [GW]
    par['pVariableMaxCharge']    = dfs['dfVariableMaxConsumption'].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum charge           [GW]
    par['pVariableMinStorage']   = dfs['dfVariableMinStorage'    ].reindex(columns=mTEPES.gg, fill_value=0.0)        # dynamic variable minimum storage          [GWh]
    par['pVariableMaxStorage']   = dfs['dfVariableMaxStorage'    ].reindex(columns=mTEPES.gg, fill_value=0.0)        # dynamic variable maximum storage          [GWh]
    par['pVariableMinEnergy']    = dfs['dfVariableMinEnergy'     ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable minimum energy           [GW]
    par['pVariableMaxEnergy']    = dfs['dfVariableMaxEnergy'     ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic variable maximum energy           [GW]
    par['pVariableFuelCost']     = dfs['dfVariableFuelCost'      ].reindex(columns=mTEPES.gg, fill_value=0.0)        # dynamic variable fuel cost                [EUR/MJ]
    par['pVariableEmissionCost'] = dfs['dfVariableEmissionCost'  ].reindex(columns=mTEPES.gg, fill_value=0.0)        # dynamic variable emission cost            [EUR/tCO2]
    par['pEnergyInflows']        = dfs['dfEnergyInflows'         ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy inflows                    [GW]
    par['pEnergyOutflows']       = dfs['dfEnergyOutflows'        ].reindex(columns=mTEPES.gg, fill_value=0.0) * 1e-3 # dynamic energy outflows                   [GW]

    if par['pIndRampReserves']:
        par['pRampReserveUp']    = dfs['dfRampReserveUp'         ].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # system ramp up   reserves                 [GW/h]
        par['pRampReserveDw']    = dfs['dfRampReserveDown'       ].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # system ramp down reserves                 [GW/h]

    if par['pIndReserveActivation']:
        par['pOperReserveUpEnergy'] = dfs['dfOperatingReserveUpEnergy'  ].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # system operating reserve activation [GW]
        par['pOperReserveDwEnergy'] = dfs['dfOperatingReserveDownEnergy'].reindex(columns=mTEPES.ar, fill_value=0.0) * 1e-3 # system operating reserve activation [GW]

    if par['pIndVarTTC']:
        par['pVariableNTCFrw'] = dfs['dfVariableTTCFrw'] * 1e-3                                                      # variable TTC forward                      [GW]
        par['pVariableNTCBck'] = dfs['dfVariableTTCBck'] * 1e-3                                                      # variable TTC backward                     [GW]
    if par['pIndPTDF']:
        par['pVariablePTDF']   = dfs['dfVariablePTDF']                                                               # variable PTDF                             [p.u.]

    if par['pIndHydroTopology']:
        par['pVariableMinVolume'] = dfs['dfVariableMinVolume'].reindex(columns=mTEPES.rs, fill_value=0.0)            # dynamic variable minimum reservoir volume [hm3]
        par['pVariableMaxVolume'] = dfs['dfVariableMaxVolume'].reindex(columns=mTEPES.rs, fill_value=0.0)            # dynamic variable maximum reservoir volume [hm3]
        par['pHydroInflows']      = dfs['dfHydroInflows'     ].reindex(columns=mTEPES.rs, fill_value=0.0)            # dynamic hydro inflows                     [m3/s]
        par['pHydroOutflows']     = dfs['dfHydroOutflows'    ].reindex(columns=mTEPES.rs, fill_value=0.0)            # dynamic hydro outflows                    [m3/s]

    if par['pIndHydrogen']:
        par['pDemandH2']          = dfs['dfDemandHydrogen']      [mTEPES.nd]                                         # hydrogen demand                           [tH2/h]

    if par['pIndHeat']:
        par['pReserveMarginHeat'] = dfs['dfReserveMarginHeat']   ['ReserveMargin']                                   # minimum adequacy reserve margin           [p.u.]
        par['pDemandHeat']        = dfs['dfDemandHeat']          [mTEPES.nd] * 1e-3                                  # heat     demand                           [GW]

    if par['pTimeStep'] > 1:
        # compute the demand as the mean over the time step load levels and assign it to active load levels. The same applies to the remaining parameters
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

        if par['pIndRampReserves']:
            par['pRampReserveUp']     = ProcessParameter(par['pRampReserveUp'],        par['pTimeStep'])
            par['pRampReserveDw']     = ProcessParameter(par['pRampReserveDw'],        par['pTimeStep'])

        if par['pIndReserveActivation']:
            par['pOperReserveUpEnergy'] = ProcessParameter(par['pOperReserveUpEnergy'], par['pTimeStep'])
            par['pOperReserveDwEnergy'] = ProcessParameter(par['pOperReserveDwEnergy'], par['pTimeStep'])

        if par['pIndVarTTC']:
            par['pVariableNTCFrw']    = ProcessParameter(par['pVariableNTCFrw'],       par['pTimeStep'])
            par['pVariableNTCBck']    = ProcessParameter(par['pVariableNTCBck'],       par['pTimeStep'])

        if par['pIndPTDF']:
            par['pVariablePTDF']      = ProcessParameter(par['pVariablePTDF'],         par['pTimeStep'])

        if par['pIndHydroTopology']:
            par['pVariableMinVolume'] = ProcessParameter(par['pVariableMinVolume'],    par['pTimeStep'])
            par['pVariableMaxVolume'] = ProcessParameter(par['pVariableMaxVolume'],    par['pTimeStep'])
            par['pHydroInflows']      = ProcessParameter(par['pHydroInflows'],         par['pTimeStep'])
            par['pHydroOutflows']     = ProcessParameter(par['pHydroOutflows'],        par['pTimeStep'])

        if par['pIndHydrogen']:
            par['pDemandH2']          = ProcessParameter(par['pDemandH2'],             par['pTimeStep'])

        if par['pIndHeat']:
            par['pDemandHeat']        = ProcessParameter(par['pDemandHeat'],           par['pTimeStep'])

        # assign duration 0 to load levels not being considered; active load levels are at the end of every pTimeStep
        n_levels = len(mTEPES.pp) * len(mTEPES.scc) * len(mTEPES.nn)
        for n in range(par['pTimeStep']-2, -1, -1):
            par['pDuration'].iloc[range(n, n_levels, par['pTimeStep'])] = 0

        for p,sc,n in par['pDuration'].index:
            if par['pPeriodWeight'][p] == 0.0:
                par['pDuration'].loc[p,sc,n] = 0
            if par['pScenProb'][p,sc] == 0.0:
                par['pDuration'].loc[p,sc,n] = 0

    # remove load levels with duration 0 to determine min and max values correctly
    parDuration = par['pDuration']
    parDurationNZ = parDuration[(parDuration != 0)]
    if parDurationNZ.max() != parDurationNZ.min():
        raise ValueError('### Some load levels have different duration. Max ', parDurationNZ.max(), ' Min ', parDurationNZ.min())
    mTEPES.pDurationNZMax = parDurationNZ.max()

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
    par['pShiftTime']                  = dfs['dfGeneration']  ['ShiftTime'                 ]                                                             # maximum shift  time for DSM                  [h]
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

    if par['pIndHydroTopology']:
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
    par['pSwitchOnTime']               = (dfs['dfNetwork']['SwOnTime' ].astype('int') if 'SwOnTime'  in dfs['dfNetwork'].columns else pd.Series(0, index=dfs['dfNetwork'].index, dtype='int'))  # minimum on  time [h]
    par['pSwitchOffTime']              = (dfs['dfNetwork']['SwOffTime'].astype('int') if 'SwOffTime' in dfs['dfNetwork'].columns else pd.Series(0, index=dfs['dfNetwork'].index, dtype='int'))  # minimum off time [h]
    par['pAngMin']                     = dfs['dfNetwork']     ['AngMin'                    ] * math.pi / 180                                             # Min phase angle difference                   [rad]
    par['pAngMax']                     = dfs['dfNetwork']     ['AngMax'                    ] * math.pi / 180                                             # Max phase angle difference                   [rad]
    par['pNetLoInvest']                = dfs['dfNetwork']     ['InvestmentLo'              ]                                                             # Lower bound of the investment decision       [p.u.]
    par['pNetUpInvest']                = dfs['dfNetwork']     ['InvestmentUp'              ]                                                             # Upper bound of the investment decision       [p.u.]

    # replace PeriodFin = 0.0 by year 3000
    par['pElecGenPeriodFin'] = par['pElecGenPeriodFin'].where(par['pElecGenPeriodFin'] != 0, 3000)
    if par['pIndHydroTopology']:
        par['pRsrPeriodFin'] = par['pRsrPeriodFin'].where    (par['pRsrPeriodFin']     != 0, 3000)
    par['pElecNetPeriodFin'] = par['pElecNetPeriodFin'].where(par['pElecNetPeriodFin'] != 0, 3000)
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

    # minimum switching on/off time converted to an integer number of time steps
    par['pSwitchOnTime']  = round(par['pSwitchOnTime'] /par['pTimeStep']).astype('int')
    par['pSwitchOffTime'] = round(par['pSwitchOffTime']/par['pTimeStep']).astype('int')

    if par['pIndHydrogen']:
        par['pH2PipeLength']       = dfs['dfNetworkHydrogen']['Length'             ]                                                         # hydrogen line length                         [km]
        par['pH2PipePeriodIni']    = dfs['dfNetworkHydrogen']['InitialPeriod'      ]                                                         # initial period
        par['pH2PipePeriodFin']    = dfs['dfNetworkHydrogen']['FinalPeriod'        ]                                                         # final   period
        par['pH2PipeNTCFrw']       = dfs['dfNetworkHydrogen']['TTC'                ] *      dfs['dfNetworkHydrogen']['SecurityFactor' ]      # net transfer capacity in forward  direction  [tH2]
        par['pH2PipeNTCBck']       = dfs['dfNetworkHydrogen']['TTCBck'             ] *      dfs['dfNetworkHydrogen']['SecurityFactor' ]      # net transfer capacity in backward direction  [tH2]
        par['pH2PipeFixedCost']    = dfs['dfNetworkHydrogen']['FixedInvestmentCost'] *      dfs['dfNetworkHydrogen']['FixedChargeRate']      # hydrogen network    fixed cost               [MEUR]
        par['pIndBinH2PipeInvest'] = dfs['dfNetworkHydrogen']['BinaryInvestment'   ]                                                         # binary hydrogen pipeline investment decision [Yes]
        par['pH2PipeLoInvest']     = dfs['dfNetworkHydrogen']['InvestmentLo'       ]                                                         # Lower bound of the investment decision       [p.u.]
        par['pH2PipeUpInvest']     = dfs['dfNetworkHydrogen']['InvestmentUp'       ]                                                         # Upper bound of the investment decision       [p.u.]

        par['pH2PipePeriodFin'] = par['pH2PipePeriodFin'].where(par['pH2PipePeriodFin'] != 0, 3000)
        # replace pH2PipeNTCBck = 0.0 by pH2PipeNTCFrw
        par['pH2PipeNTCBck']    = par['pH2PipeNTCBck'].where   (par['pH2PipeNTCBck']     > 0.0, par['pH2PipeNTCFrw'])
        # replace pH2PipeNTCFrw = 0.0 by pH2PipeNTCBck
        par['pH2PipeNTCFrw']    = par['pH2PipeNTCFrw'].where   (par['pH2PipeNTCFrw']     > 0.0, par['pH2PipeNTCBck'])
        # replace pH2PipeUpInvest = 0.0 by 1.0
        par['pH2PipeUpInvest']  = par['pH2PipeUpInvest'].where(par['pH2PipeUpInvest']    > 0.0, 1.0                 )

    if par['pIndHeat']:
        par['pHeatPipeLength']       = dfs['dfNetworkHeat']['Length'             ]                                                           # heat pipe length                             [km]
        par['pHeatPipePeriodIni']    = dfs['dfNetworkHeat']['InitialPeriod'      ]                                                           # initial period
        par['pHeatPipePeriodFin']    = dfs['dfNetworkHeat']['FinalPeriod'        ]                                                           # final   period
        par['pHeatPipeNTCFrw']       = dfs['dfNetworkHeat']['TTC'                ] * 1e-3 * dfs['dfNetworkHeat']    ['SecurityFactor' ]      # net transfer capacity in forward  direction  [GW]
        par['pHeatPipeNTCBck']       = dfs['dfNetworkHeat']['TTCBck'             ] * 1e-3 * dfs['dfNetworkHeat']    ['SecurityFactor' ]      # net transfer capacity in backward direction  [GW]
        par['pHeatPipeFixedCost']    = dfs['dfNetworkHeat']['FixedInvestmentCost'] *        dfs['dfNetworkHeat']    ['FixedChargeRate']      # heat    network    fixed cost                [MEUR]
        par['pIndBinHeatPipeInvest'] = dfs['dfNetworkHeat']['BinaryInvestment'   ]                                                           # binary heat     pipe     investment decision [Yes]
        par['pHeatPipeLoInvest']     = dfs['dfNetworkHeat']['InvestmentLo'       ]                                                           # Lower bound of the investment decision       [p.u.]
        par['pHeatPipeUpInvest']     = dfs['dfNetworkHeat']['InvestmentUp'       ]                                                           # Upper bound of the investment decision       [p.u.]

        par['pHeatPipePeriodFin']    = par['pHeatPipePeriodFin'].where(par['pHeatPipePeriodFin'] != 0, 3000)
        # replace pHeatPipeNTCBck = 0.0 by pHeatPipeNTCFrw
        par['pHeatPipeNTCBck']       = par['pHeatPipeNTCBck'].where   (par['pHeatPipeNTCBck']     > 0.0, par['pHeatPipeNTCFrw'])
        # replace pHeatPipeNTCFrw = 0.0 by pHeatPipeNTCBck
        par['pHeatPipeNTCFrw']       = par['pHeatPipeNTCFrw'].where   (par['pHeatPipeNTCFrw']     > 0.0, par['pHeatPipeNTCBck'])
        # replace pHeatPipeUpInvest = 0.0 by 1.0
        par['pHeatPipeUpInvest']     = par['pHeatPipeUpInvest'].where (par['pHeatPipeUpInvest']   > 0.0, 1.0                   )

    #%% storing the parameters on the model for backward compatibility
    # (external consumers that pickle mTEPES or inspect inputs post-load
    # rely on these). New callers should consume dfs/par from the return
    # value instead.
    mTEPES.dFrame  = dfs
    mTEPES.dPar    = par

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')

    return dfs, par
