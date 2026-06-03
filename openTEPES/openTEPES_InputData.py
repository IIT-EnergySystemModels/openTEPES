"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 3, 2026
"""

import time
import math
import os
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import Set, Param, Var, Binary, NonNegativeReals, NonNegativeIntegers, PositiveReals, PositiveIntegers, Reals, UnitInterval, Any
from   pyomo.environ import Block, Boolean

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_InputSource    import open_source, df_to_set_values, InputSource
    from .openTEPES_InputCSVSource import CSVSource
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSource    import open_source, df_to_set_values, InputSource
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
    # if 'pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat' not in par include them and set value to zero
    for key in ['pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat']:
        if key not in par.keys():
            par[key] = 0

    # substitute NaN by 0
    for key,df in dfs.items():
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
    # par['pSwitchOnTime']               = dfs['dfNetwork']     ['SwOnTime'                  ].astype('int')                                               # minimum on  time                             [h]
    # par['pSwitchOffTime']              = dfs['dfNetwork']     ['SwOffTime'                 ].astype('int')                                               # minimum off time                             [h]
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

    # minimum up- and downtime converted to an integer number of time steps
    # par['pSwitchOnTime']  = round(par['pSwitchOnTime'] /par['pTimeStep']).astype('int')
    # par['pSwitchOffTime'] = round(par['pSwitchOffTime']/par['pTimeStep']).astype('int')

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

    mTEPES.pENSCost              = Param(initialize=par['pENSCost']             , within=NonNegativeReals,    doc='ENS cost'                                           )
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

    mTEPES.pReserveMargin        = Param(mTEPES.par,   initialize=par['pReserveMargin'].to_dict()            , within=NonNegativeReals,    doc='Adequacy reserve margin'                             )
    mTEPES.pEmission             = Param(mTEPES.par,   initialize=par['pEmission'].to_dict()                 , within=NonNegativeReals,    doc='Maximum CO2 emission'                                )
    mTEPES.pRESEnergy            = Param(mTEPES.par,   initialize=par['pRESEnergy'].to_dict()                , within=NonNegativeReals,    doc='Minimum RES energy'                                  )
    mTEPES.pDemandElecPeak       = Param(mTEPES.par,   initialize=par['pDemandElecPeak'].to_dict()           , within=NonNegativeReals,    doc='Peak electric demand'                                )
    mTEPES.pDemandElec           = Param(mTEPES.psnnd, initialize=par['pDemandElec'].to_dict()               , within=           Reals,    doc='Electric demand'                                     )
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
    mTEPES.pEFOR                 = Param(mTEPES.gg,    initialize=par['pEFOR'].to_dict()                     , within=UnitInterval    ,    doc='EFOR'                                                )
    mTEPES.pRatedLinearVarCost   = Param(mTEPES.gg,    initialize=par['pRatedLinearVarCost'].to_dict()       , within=NonNegativeReals,    doc='Linear   variable cost'                              )
    mTEPES.pLinearVarCost        = Param(mTEPES.psng , initialize=par['pLinearVarCost'].to_dict()            , within=NonNegativeReals,    doc='Linear   variable cost'                              )
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


# @profile
def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()

    # @profile
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
        OptModel.vTotalSCost               = Var(              within=NonNegativeReals, doc='total system                         cost      [MEUR]')
        OptModel.vTotalICost               = Var(              within=NonNegativeReals, doc='total system investment              cost      [MEUR]')
        OptModel.vTotalFElecCost           = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed elec              cost      [MEUR]')
        OptModel.vTotalGCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable generation  operation cost      [MEUR]')
        OptModel.vTotalCCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable consumption operation cost      [MEUR]')
        OptModel.vTotalECost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system emission                cost      [MEUR]')
        OptModel.vTotalRElecCost           = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability elec        cost      [MEUR]')
        OptModel.vTotalNCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total network loss penalty operation cost      [MEUR]')
        OptModel.vTotalEmissionArea        = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                         [MtCO2]')
        OptModel.vTotalECostArea           = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                cost      [MEUR]')
        OptModel.vTotalRESEnergyArea       = Var(mTEPES.psnar, within=NonNegativeReals, doc='        RES energy                              [GWh]')

        OptModel.vTotalOutput              = Var(mTEPES.psng , within=NonNegativeReals, doc='total output of the unit                         [GW]')
        OptModel.vOutput2ndBlock           = Var(mTEPES.psnnr, within=NonNegativeReals, doc='second block of the unit                         [GW]')
        OptModel.vReserveUp                = Var(mTEPES.psnnr, within=NonNegativeReals, doc='up   operating reserve                           [GW]')
        OptModel.vReserveDown              = Var(mTEPES.psnnr, within=NonNegativeReals, doc='down operating reserve                           [GW]')
        OptModel.vEnergyInflows            = Var(mTEPES.psnec, within=NonNegativeReals, doc='unscheduled inflows  of candidate ESS units      [GW]')
        OptModel.vEnergyOutflows           = Var(mTEPES.psnes, within=NonNegativeReals, doc='scheduled   outflows of all       ESS units      [GW]')
        OptModel.vESSInventory             = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS inventory                                   [GWh]')
        OptModel.vESSSpillage              = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS spillage                                    [GWh]')
        OptModel.vIniInventory             = Var(mTEPES.psnec, within=NonNegativeReals, doc='initial inventory for ESS candidate             [GWh]')

        if mTEPES.pIndRampReserves:
            OptModel.vRampReserveUp        = Var(mTEPES.psnnr, within=NonNegativeReals, doc='ramp up   reserve of the unit                  [GW/h]')
            OptModel.vRampReserveDw        = Var(mTEPES.psnnr, within=NonNegativeReals, doc='ramp down reserve of the unit                  [GW/h]')

        if mTEPES.pIndReserveActivation:
            OptModel.vReserveUpEnergy      = Var(mTEPES.psnnr, within=NonNegativeReals, doc='up   reserve activation of the unit              [GW]')
            OptModel.vReserveDownEnergy    = Var(mTEPES.psnnr, within=NonNegativeReals, doc='down reserve activation of the unit              [GW]')

        OptModel.vESSTotalCharge           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS total charge power                           [GW]')
        OptModel.vCharge2ndBlock           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS       charge power                           [GW]')
        OptModel.vESSReserveUp             = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS up   operating reserve                       [GW]')
        OptModel.vESSReserveDown           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS down operating reserve                       [GW]')
        OptModel.vENS                      = Var(mTEPES.psnnd, within=NonNegativeReals, doc='energy not served in node                        [GW]')

        if mTEPES.pIndReserveActivation:
            OptModel.vESSReserveUpEnergy   = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS up   reserve activation of the unit          [GW]')
            OptModel.vESSReserveDownEnergy = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS down reserve activation of the unit          [GW]')

        if mTEPES.pIndHydroTopology:
            OptModel.vTotalFHydroCost      = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed hydro             cost      [MEUR]')
            OptModel.vHydroInflows         = Var(mTEPES.psnrc, within=NonNegativeReals, doc='unscheduled inflows  of candidate hydro units  [m3/s]')
            OptModel.vHydroOutflows        = Var(mTEPES.psnrs, within=NonNegativeReals, doc='scheduled   outflows of all       hydro units  [m3/s]')
            OptModel.vReservoirVolume      = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir volume                                [hm3]')
            OptModel.vReservoirSpillage    = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir spillage                              [hm3]')

        if mTEPES.pIndHydrogen:
            OptModel.vTotalFH2Cost         = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed H2                cost      [MEUR]')
            OptModel.vTotalRH2Cost         = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability H2          cost      [MEUR]')

        if mTEPES.pIndHeat:
            OptModel.vTotalFHeatCost       = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed heat              cost      [MEUR]')
            OptModel.vTotalRHeatCost       = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability heat        cost      [MEUR]')
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

        if mTEPES.pIndHydroTopology:
            if mTEPES.pIndBinRsrInvest() != 1:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
            else:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')

        if mTEPES.pIndHydrogen:
            if mTEPES.pIndBinNetH2Invest() != 1:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
            else:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')

        if mTEPES.pIndHeat:
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
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='commitment      of the unit                                    [0,1]')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='startup         of the unit                                    [0,1]')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='shutdown        of the unit                                    [0,1]')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='stable    state of the unit                                    [0,1]')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp up   state of the unit                                    [0,1]')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp down state of the unit                                    [0,1]')

            OptModel.vMaxCommitmentYearly  = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=UnitInterval, initialize=0.0, doc='maximum commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly  = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=UnitInterval, initialize=0.0, doc='maximum commitment of the unit hourly [0,1]')

            if mTEPES.pIndHydroTopology:
                OptModel.vCommitmentCons   = Var(mTEPES.psnh,  within=UnitInterval,     doc='consumption commitment of the unit                                             [0,1]')

        else:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='commitment      of the unit                              {0,1}')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='startup         of the unit                              {0,1}')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='shutdown        of the unit                              {0,1}')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='stable    state of the unit                              {0,1}')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp up   state of the unit                              {0,1}')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp down state of the unit                              {0,1}')

            OptModel.vMaxCommitmentYearly  = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=Binary, initialize=0.0, doc='maximum commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly  = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=Binary, initialize=0.0, doc='maximum commitment of the unit hourly [0,1]')
            if mTEPES.pIndHydroTopology:
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
    # @profile
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
        [OptModel.vESSInventory  [p,sc,n,es].setub(mTEPES.pMaxStorage       [p,sc,n,es]()) for p,sc,n,es in mTEPES.psnes]
        [OptModel.vIniInventory  [p,sc,n,ec].setlb(mTEPES.pMinStorage       [p,sc,n,ec]  ) for p,sc,n,ec in mTEPES.psnec]
        [OptModel.vIniInventory  [p,sc,n,ec].setub(mTEPES.pMaxStorage       [p,sc,n,ec]()) for p,sc,n,ec in mTEPES.psnec]

        if mTEPES.pIndRampReserves:
            [OptModel.vRampReserveUp[p,sc,n,nr].setub(min(mTEPES.pMaxPower2ndBlock[p,sc,n,nr], mTEPES.pRampUp[nr])) if mTEPES.pRampUp[nr] else OptModel.vRampReserveUp[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]
            [OptModel.vRampReserveDw[p,sc,n,nr].setub(min(mTEPES.pMaxPower2ndBlock[p,sc,n,nr], mTEPES.pRampDw[nr])) if mTEPES.pRampUp[nr] else OptModel.vRampReserveDw[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]

        if mTEPES.pIndReserveActivation:
            [OptModel.vReserveUpEnergy  [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]
            [OptModel.vReserveDownEnergy[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]

        [OptModel.vESSTotalCharge[p,sc,n,eh].setub(mTEPES.pMaxCharge        [p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vCharge2ndBlock[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveUp  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveDown[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vENS           [p,sc,n,nd].setub(mTEPES.pDemandElecPos    [p,sc,n,nd]  ) for p,sc,n,nd in mTEPES.psnnd]

        if mTEPES.pIndReserveActivation:
            [OptModel.vESSReserveUpEnergy  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
            [OptModel.vESSReserveDownEnergy[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]

        if mTEPES.pIndHydroTopology:
            [OptModel.vHydroInflows   [p,sc,n,rc].setub(mTEPES.pHydroInflows[p,sc,n,rc]()) for p,sc,n,rc in mTEPES.psnrc]
            [OptModel.vHydroOutflows  [p,sc,n,rs].setub(mTEPES.pMaxOutflows [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setlb(mTEPES.pMinVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setub(mTEPES.pMaxVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]

    setVariableBounds(mTEPES, mTEPES)

    nFixedVariables = 0

    # @profile
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

        nFixedVariables = 0

        # relax binary condition in generation, boiler, and electric network investment decisions
        for p,eb in mTEPES.peb:
            if mTEPES.pIndBinGenInvest() == 2 or (mTEPES.pIndBinGenInvest() == 1 and mTEPES.pIndBinUnitInvest[eb] == 0):
                OptModel.vGenerationInvest    [p,eb      ].domain = UnitInterval
            if mTEPES.pIndBinGenInvest() == 2:
                OptModel.vGenerationInvest    [p,eb      ].fix(0)
                nFixedVariables += 1

        # relax binary condition in generation retirement decisions
        for p,gd in mTEPES.pgd:
            if mTEPES.pIndBinGenRetire() == 2 or (mTEPES.pIndBinGenRetire() == 1 and mTEPES.pIndBinUnitRetire[gd] == 0):
                OptModel.vGenerationRetire    [p,gd      ].domain = UnitInterval
            if mTEPES.pIndBinGenRetire() == 2:
                OptModel.vGenerationRetire    [p,gd      ].fix(0)
                nFixedVariables += 1

        for p,ni,nf,cc in mTEPES.plc:
            if mTEPES.pIndBinNetElecInvest() == 2 or (mTEPES.pIndBinNetElecInvest() == 1 and mTEPES.pIndBinLineInvest[ni,nf,cc] == 0):
                OptModel.vNetworkInvest       [p,ni,nf,cc].domain = UnitInterval
            if mTEPES.pIndBinNetElecInvest() == 2:
                OptModel.vNetworkInvest       [p,ni,nf,cc].fix(0)
                nFixedVariables += 1

        # relax binary condition in reservoir investment decisions
        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if mTEPES.pIndBinRsrInvest() == 2 or (mTEPES.pIndBinRsrInvest() == 1 and mTEPES.pIndBinRsrvInvest[rc] == 0):
                    OptModel.vReservoirInvest [p,rc      ].domain = UnitInterval
                if mTEPES.pIndBinRsrInvest() == 2:
                    OptModel.vReservoirInvest [p,rc      ].fix(0)
                    nFixedVariables += 1

        # relax binary condition in hydrogen network investment decisions
        if mTEPES.pIndHydrogen:
            for p,ni,nf,cc in mTEPES.ppc:
                if mTEPES.pIndBinNetH2Invest() == 2 or (mTEPES.pIndBinNetH2Invest() == 1 and mTEPES.pIndBinH2PipeInvest[ni,nf,cc] == 0):
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetH2Invest() == 2:
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedVariables += 1

        if mTEPES.pIndHeat:
            # relax binary condition in heat network investment decisions
            for p,ni,nf,cc in mTEPES.phc:
                if mTEPES.pIndBinNetHeatInvest() == 2 or (mTEPES.pIndBinNetHeatInvest() == 1 and mTEPES.pIndBinHeatPipeInvest[ni,nf,cc] == 0):
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetHeatInvest() == 2:
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedVariables += 1

        for p,sc,n,nr in mTEPES.psnnr:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vCommitment [p,sc,n,nr].domain = UnitInterval
                OptModel.vStartUp    [p,sc,n,nr].domain = UnitInterval
                OptModel.vShutDown   [p,sc,n,nr].domain = UnitInterval
            # fix variables for units that don't have minimum stable time
            if mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
                OptModel.vStableState[p,sc,n,nr].fix(0)
                OptModel.vStableState[p,sc,n,nr].domain = UnitInterval
                OptModel.vRampDwState[p,sc,n,nr].fix(0)
                OptModel.vRampDwState[p,sc,n,nr].domain = UnitInterval
                OptModel.vRampUpState[p,sc,n,nr].fix(0)
                OptModel.vRampUpState[p,sc,n,nr].domain = UnitInterval
                nFixedVariables += 3

        for p,sc,nr,  group in mTEPES.ps*mTEPES.ExclusiveGeneratorsYearly*mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vMaxCommitmentYearly[p,sc,  nr,group].domain = UnitInterval
        for p,sc,n,nr,group in mTEPES.psn*mTEPES.ExclusiveGeneratorsHourly*mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vMaxCommitmentHourly[p,sc,n,nr,group].domain = UnitInterval
        if mTEPES.pIndHydroTopology:
            for p,sc,n,h in mTEPES.psnh:
                if mTEPES.pIndBinUnitCommit[h] == 0 or mTEPES.pMaxCharge[p,sc,n,h] == 0.0:
                    OptModel.vCommitmentCons[p,sc,n,h].domain = UnitInterval
                if mTEPES.pMaxCharge[p,sc,n,h] == 0.0:
                    OptModel.vCommitmentCons[p,sc,n,h].fix(0)
                    nFixedVariables += 1

        return nFixedVariables

    # call the relaxing variables function and add its output to nFixedVariables
    nFixedBinaries = RelaxBinaryInvestmentConditions(mTEPES, mTEPES)
    nFixedVariables += nFixedBinaries

    # @profile
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
        for p,sc,n,ni,nf,cc in mTEPES.psnle:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
                OptModel.vLineCommit[p,sc,n,ni,nf,cc].fix(1)
                OptModel.vLineCommit[p,sc,n,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1

        # no on/off state for lines if no switching decision is modeled
        if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
             for p,sc,n,ni,nf,cc in mTEPES.psnla:
                 if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
                     OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0)
                     OptModel.vLineOnState [p,sc,n,ni,nf,cc].domain = UnitInterval
                     OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0)
                     OptModel.vLineOffState[p,sc,n,ni,nf,cc].domain = UnitInterval
                     nFixedVariables += 2

        OptModel.vLineLosses = Var(mTEPES.psnll, within=NonNegativeReals, doc='half line losses [GW]')
        OptModel.vFlowElec   = Var(mTEPES.psnla, within=Reals,            doc='electric flow    [GW]')
        OptModel.vTheta      = Var(mTEPES.psnnd, within=Reals,            doc='voltage angle   [rad]')

        if mTEPES.pIndVarTTC:
            # lines with TTC and TTCBck = 0 are disconnected and the flow is fixed to 0
            sPSNLA = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] == 0.0 and mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0]
            [OptModel.vFlowElec[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in sPSNLA]
            nFixedVariables += sum(                    1  for p,sc,n,ni,nf,cc in sPSNLA)

        if mTEPES.pIndPTDF:
            OptModel.vNetPosition = Var(mTEPES.psnnd, within=Reals, doc='net position in node [GW]')

        if mTEPES.pIndBinSingleNode() == 0:
            [OptModel.vLineLosses[p,sc,n,ni,nf,cc].setub(0.5*mTEPES.pLineLossFactor[ni,nf,cc]*mTEPES.pLineNTCMax[ni,nf,cc]) for p,sc,n,ni,nf,cc in mTEPES.psnll]
            [OptModel.vFlowElec  [p,sc,n,ni,nf,cc].setlb(-mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]                              ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
            [OptModel.vFlowElec  [p,sc,n,ni,nf,cc].setub( mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]                              ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
        else:
            [OptModel.vLineLosses[p,sc,n,ni,nf,cc].fix(0.0                                                                ) for p,sc,n,ni,nf,cc in mTEPES.psnll]
            nFixedVariables += sum(                    1                                                                    for p,sc,n,ni,nf,cc in mTEPES.psnll)
        [OptModel.vTheta         [p,sc,n,nd      ].setlb(-mTEPES.pMaxTheta [p,sc,n,nd      ]()                            ) for p,sc,n,nd       in mTEPES.psnnd]
        [OptModel.vTheta         [p,sc,n,nd      ].setub( mTEPES.pMaxTheta [p,sc,n,nd      ]()                            ) for p,sc,n,nd       in mTEPES.psnnd]

        if mTEPES.pIndHydrogen:
            OptModel.vFlowH2 = Var(mTEPES.psnpa, within=Reals,            doc='pipeline flow               [tH2]')
            OptModel.vH2NS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='hydrogen not served in node [tH2]')
            OptModel.vH2Exc  = Var(mTEPES.psnnd, within=NonNegativeReals, doc='hydrogen excess     in node [tH2]')
            [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setlb(-mTEPES.pH2PipeNTCBck[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
            [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setub( mTEPES.pH2PipeNTCFrw[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
            [OptModel.vH2NS    [p,sc,n,nd      ].setub(mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandH2Abs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]

        if mTEPES.pIndHeat:
            OptModel.vFlowHeat = Var(mTEPES.psnha, within=Reals,            doc='heat pipe flow          [GW]')
            OptModel.vHeatNS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='heat not served in node [GW]')
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setlb(-mTEPES.pHeatPipeNTCBck[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setub( mTEPES.pHeatPipeNTCFrw[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vHeatNS  [p,sc,n,nd      ].setub( mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandHeatAbs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]
        return nFixedVariables

    nFixedLineCommitments = CreateFlowVariables(mTEPES, mTEPES)
    nFixedVariables += nFixedLineCommitments

    # @profile
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

        # must-run units must produce at least their minimum output
        sPSNG = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if mTEPES.pMustRun[g] and g not in mTEPES.gc]
        [OptModel.vTotalOutput[p,sc,n,g].setlb(mTEPES.pMinPowerElec[p,sc,n,g]) for p,sc,n,g in sPSNG]

        # if no max power, no total output
        sPSNG = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0]
        [OptModel.vTotalOutput[p,sc,n,g].fix(0.0) for p,sc,n,g in sPSNG]
        nFixedVariables += sum(                1  for p,sc,n,g in sPSNG)

        for p,sc,n,nr in mTEPES.psnnr:
            # must-run existing units or units with no minimum power, or ESS existing units are always committed and must produce at least their minimum output
            # not applicable to mutually exclusive units
            if   len(mTEPES.ExclusiveGroups) == 0:
                if ((mTEPES.pMustRun[nr] and nr not in mTEPES.gc) or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                    nFixedVariables += 3
            # If there are mutually exclusive groups do not fix variables from ESS in mutually exclusive groups
            elif len(mTEPES.ExclusiveGroups) >  0 and nr not in mTEPES.ExclusiveGenerators:
                if (mTEPES.pMustRun[nr] or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                    nFixedVariables += 3

            # if min and max power coincide there are neither second block, nor operating reserve, nor ramp reserve
            if  mTEPES.pMaxPower2ndBlock[p,sc,n,nr] ==  0.0:
                OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                # fix the must-run existing units and their output
                if mTEPES.pMustRun[nr] and nr not in mTEPES.gc:
                    OptModel.vTotalOutput[p,sc,n,nr].fix(mTEPES.pMinPowerElec[p,sc,n,nr])
                    nFixedVariables += 1
                if mTEPES.pIndRampReserves:
                    if mTEPES.pRampUp[nr] == 0.0:
                        OptModel.vRampReserveUp[p,sc,n,nr].fix(0.0)
                        OptModel.vRampReserveDw[p,sc,n,nr].fix(0.0)
                        nFixedVariables += 2

            if  mTEPES.pIndOperReserveGen[nr] or mTEPES.pMaxPower2ndBlock [p,sc,n,nr] == 0.0:
                OptModel.vReserveUp  [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown[p,sc,n,nr].fix(0.0)
                nFixedVariables += 2
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
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
            if  mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0:
                OptModel.vTotalOutput    [p,sc,n,es].fix(0.0)
                OptModel.vOutput2ndBlock [p,sc,n,es].fix(0.0)
                OptModel.vReserveUp      [p,sc,n,es].fix(0.0)
                OptModel.vReserveDown    [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage    [p,sc,n,es].fix(0.0)
                OptModel.vESSInventory   [p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
                nFixedVariables += 6
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 2
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0:
                OptModel.vCharge2ndBlock [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            if  mTEPES.pIndOperReserveCon[es] or mTEPES.pMaxCharge2ndBlock[p,sc,n,es] == 0.0:
                OptModel.vESSReserveUp   [p,sc,n,es].fix(0.0)
                OptModel.vESSReserveDown [p,sc,n,es].fix(0.0)
                nFixedVariables += 2
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy  [p,sc,n,es].fix(0.0)
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 2
            if  mTEPES.pMaxStorage       [p,sc,n,es]() == 0.0:
                OptModel.vESSInventory   [p,sc,n,es].fix( 0.0)
                nFixedVariables += 1

        if mTEPES.pIndHydroTopology:
            for p,sc,n,h in mTEPES.psnh:
                # ESS with no charge capacity or not storage capacity can't charge
                if  mTEPES.pMaxCharge        [p,sc,n,h ] ==  0.0:
                    OptModel.vESSTotalCharge [p,sc,n,h ].fix(0.0)
                    OptModel.vCommitmentCons [p,sc,n,h ].fix(0  )
                    OptModel.vCommitmentCons [p,sc,n,h ].domain = UnitInterval
                    nFixedVariables += 2
                if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0:
                    OptModel.vCharge2ndBlock [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 1
                if  mTEPES.pIndOperReserveCon[h ] or mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] == 0.0:
                    OptModel.vESSReserveUp   [p,sc,n,h ].fix(0.0)
                    OptModel.vESSReserveDown [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 2
                    if mTEPES.pIndReserveActivation:
                        OptModel.vESSReserveUpEnergy  [p,sc,n,h ].fix(0.0)
                        OptModel.vESSReserveDownEnergy[p,sc,n,h ].fix(0.0)
                        nFixedVariables += 2
        return nFixedVariables
    nFixedGeneratorCommits = FixGeneratorsCommitment(mTEPES, mTEPES)
    nFixedVariables       += nFixedGeneratorCommits
    # thermal, ESS, and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if mTEPES.tq:
        mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.sq])
    else:
        if mTEPES.pIndHydroTopology:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__)])
        else:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.h])

    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    o2a = defaultdict(list)
    for ar,go in mTEPES.ar*mTEPES.go:
        if (ar,go) in mTEPES.a2g:
            o2a[ar].append(go)

    # nodes to area (d2a)
    d2a = defaultdict(list)
    for ar,nd in mTEPES.ar*mTEPES.nd:
        if (nd,ar) in mTEPES.ndar:
            d2a[ar].append(nd)

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt and mTEPES.pStageWeight[stt] and sum(1 for  p,sc,st,nn  in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                      (p,sc,st,nn) in mTEPES.s2n ])

        if mTEPES.n:
            # determine the first load level of each stage
            n1 = (p,sc,mTEPES.n.first())
            # commit the units of each area and their output at the first load level of each stage
            for ar in mTEPES.ar:
                pSystemOutput = 0.0
                for nr in n2a[ar]:
                    if mTEPES.pMustRun[nr] == 1 and (p,nr) in mTEPES.pnr and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in d2a[ar]):
                        mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPowerElec [n1,nr]
                        mTEPES.pInitialUC    [n1,nr] = 1
                        pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

                # determine the initially committed units and their output at the first load level of each period, scenario, and stage
                for go in o2a[ar]:
                    if mTEPES.pMustRun[go] == 0 and (p,go) in mTEPES.pg and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd] for nd in d2a[ar]):
                        if go in mTEPES.re:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPowerElec [n1,go]
                        else:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPowerElec [n1,go]
                        mTEPES.pInitialUC[n1,go]         = 1
                        pSystemOutput                   += mTEPES.pInitialOutput[n1,go]()

            # determine the initially committed lines
            for la in mTEPES.la:
                if (p,la) in mTEPES.pla:
                    if la in mTEPES.lc:
                        mTEPES.pInitialSwitch[n1,la] = 0
                    else:
                        mTEPES.pInitialSwitch[n1,la] = 1

            # fixing the ESS inventory at the last load level of the stage for every period and scenario if between storage limits
            for es in mTEPES.es:
                if es not in mTEPES.ec and (p,es) in mTEPES.pes:
                    OptModel.vESSInventory[p,sc,mTEPES.n.last(),es].fix(mTEPES.pIniInventory[p,sc,mTEPES.n.last(),es])

            if mTEPES.pIndHydroTopology:
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

    # if mTEPES.pIndHydroTopology:
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
    for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr:
        if nr in n2a[ar] and (p,sc,n,nr) in mTEPES.psnnr:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 1
    for p,sc,n,ar,es in mTEPES.psn*mTEPES.ar*mTEPES.es:
        if es in e2a[ar] and (p,sc,n,es) in mTEPES.psnes:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    # if there are no energy outflows, no variable is needed
    for es in mTEPES.es:
        if sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
            for p,sc,n in mTEPES.psn:
                if (p,es) in mTEPES.pes:
                    OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    if mTEPES.pIndHydroTopology:
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

    if mTEPES.pIndHydrogen:
        # fixing the H2 ENS in nodes with no hydrogen demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandH2[p,sc,n,nd] ==  0.0:
                OptModel.vH2NS [p,sc,n,nd].fix(0.0)
                nFixedVariables += 1

    if mTEPES.pIndHeat:
        # fixing the heat ENS in nodes with no heat demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandHeat[p,sc,n,nd] ==  0.0:
                OptModel.vHeatNS [p,sc,n,nd].fix(0.0)
                nFixedVariables += 1

    # @profile
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
                OptModel.vGenerationInvest[p,eb].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecGenPeriodIni[eb] > p or mTEPES.pElecGenPeriodFin[eb] < p:
                OptModel.vGenerationInvPer[p,eb].fix(0)
                OptModel.vGenerationInvPer[p,eb].domain = UnitInterval
                nFixedVariables += 1

        for p,gd in mTEPES.pgd:
            if mTEPES.pElecGenPeriodIni[gd] > p:
                OptModel.vGenerationRetire[p,gd].fix(0)
                OptModel.vGenerationRetire[p,gd].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecGenPeriodIni[gd] > p or mTEPES.pElecGenPeriodFin[gd] < p:
                OptModel.vGenerationRetPer[p,gd].fix(0)
                OptModel.vGenerationRetPer[p,gd].domain = UnitInterval
                nFixedVariables += 1

        for p,ni,nf,cc in mTEPES.plc:
            if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p:
                OptModel.vNetworkInvest[p,ni,nf,cc].fix(0)
                OptModel.vNetworkInvest[p,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p or mTEPES.pElecNetPeriodFin[ni,nf,cc] < p:
                OptModel.vNetworkInvPer[p,ni,nf,cc].fix(0)
                OptModel.vNetworkInvPer[p,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1

        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if mTEPES.pRsrPeriodIni[rc] > p:
                    OptModel.vReservoirInvest[p,rc].fix(0)
                    OptModel.vReservoirInvest[p,rc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pRsrPeriodIni[rc] > p or mTEPES.pRsrPeriodFin[rc] < p:
                    OptModel.vReservoirInvPer[p,rc].fix(0)
                    OptModel.vReservoirInvPer[p,rc].domain = UnitInterval
                    nFixedVariables += 1

        if mTEPES.pIndHydrogen:
            for p,ni,nf,cc in mTEPES.ppc:
                if mTEPES.pH2PipePeriodIni[ni,nf,cc] > p:
                    OptModel.vH2PipeInvest[p,ni,nf,cc].fix(0)
                    OptModel.vH2PipeInvest[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pH2PipePeriodIni[ni,nf,cc] > p or mTEPES.pH2PipePeriodFin[ni,nf,cc] < p:
                    OptModel.vH2PipeInvPer[p,ni,nf,cc].fix(0)
                    OptModel.vH2PipeInvPer[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1

        if mTEPES.pIndHeat:
            for p,ni,nf,cc in mTEPES.phc:
                if mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p:
                    OptModel.vHeatPipeInvest[p,ni,nf,cc].fix(0)
                    OptModel.vHeatPipeInvest[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p:
                    OptModel.vHeatPipeInvPer[p,ni,nf,cc].fix(0)
                    OptModel.vHeatPipeInvPer[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1

        # remove power plants and lines not installed in this period
        for p,g in mTEPES.pg:
            if g not in mTEPES.eb and mTEPES.pElecGenPeriodIni[g ] > p or mTEPES.pElecGenPeriodFin[g ] < p:
                for sc,n in mTEPES.sc*mTEPES.n:
                    OptModel.vTotalOutput[p,sc,n,g].fix(0.0)
                    nFixedVariables += 1

        for p,sc,nr in mTEPES.psnr:
            if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p or mTEPES.pElecGenPeriodFin[nr] < p:
                OptModel.vMaxCommitment[p,sc,nr].fix(0)
                OptModel.vMaxCommitment[p,sc,nr].domain = UnitInterval
                nFixedVariables += 1
        for p,sc,n,nr in mTEPES.psnnr:
            if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p or mTEPES.pElecGenPeriodFin[nr] < p:
                OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 2
                OptModel.vCommitment    [p,sc,n,nr].fix(0  )
                OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                OptModel.vStartUp       [p,sc,n,nr].fix(0  )
                OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                OptModel.vShutDown      [p,sc,n,nr].fix(0  )
                OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                nFixedVariables += 6

        for p,sc,n,es in mTEPES.psnes:
            if es not in mTEPES.ec and mTEPES.pElecGenPeriodIni[es] > p or mTEPES.pElecGenPeriodFin[es] < p:
                OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                OptModel.vESSInventory  [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage   [p,sc,n,es].fix(0.0)
                OptModel.vESSTotalCharge[p,sc,n,es].fix(0.0)
                OptModel.vCharge2ndBlock[p,sc,n,es].fix(0.0)
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy  [p,sc,n,es].fix(0.0)
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 2
                mTEPES.pIniInventory    [p,sc,n,es] =   0.0
                mTEPES.pEnergyInflows   [p,sc,n,es] =   0.0
                nFixedVariables += 7

        if mTEPES.pIndHydroTopology:
            for p,sc,n,rs in mTEPES.psnrs:
                if rs not in mTEPES.rn and mTEPES.pRsrPeriodIni[rs] > p or mTEPES.pRsrPeriodFin[rs] < p:
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
                            if mTEPES.pIndReserveActivation:
                                OptModel.vESSReserveUpEnergy  [p,sc,n,h ].fix(0.0)
                                OptModel.vESSReserveDownEnergy[p,sc,n,h ].fix(0.0)
                                nFixedVariables += 2
        return nFixedVariables

    nFixedInstallationsAndRetirements = AvoidForbiddenInstallationsAndRetirements(mTEPES, mTEPES)
    nFixedVariables += nFixedInstallationsAndRetirements

    for p,sc,n,ni,nf,cc in mTEPES.psnle:
        if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p or mTEPES.pElecNetPeriodFin[ni,nf,cc] < p:
            OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineCommit  [p,sc,n,ni,nf,cc].domain = UnitInterval
            OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineOnState [p,sc,n,ni,nf,cc].domain = UnitInterval
            OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineOffState[p,sc,n,ni,nf,cc].domain = UnitInterval
            nFixedVariables += 3

    [OptModel.vLineLosses  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p)]
    nFixedVariables     += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p))

    [OptModel.vFlowElec    [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnle if                                  mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p]
    nFixedVariables     += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnle if                                  mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p)

    if mTEPES.pIndHydrogen:
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnpe if                                  mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p or mTEPES.pH2PipePeriodFin  [ni,nf,cc] < p]
        nFixedVariables += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnpe if                                  mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p or mTEPES.pH2PipePeriodFin  [ni,nf,cc] < p)

    if mTEPES.pIndHeat:
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnhe if                                  mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p]
        nFixedVariables += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnhe if                                  mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p)

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
            if  mTEPES.pGenLoInvest[  eb]() <       pEpsilon:
                mTEPES.pGenLoInvest[  eb]   = 0
            if  mTEPES.pGenUpInvest[  eb]() <       pEpsilon:
                mTEPES.pGenUpInvest[  eb]   = 0
            if  mTEPES.pGenLoInvest[  eb]() > 1.0 - pEpsilon:
                mTEPES.pGenLoInvest[  eb]   = 1
            if  mTEPES.pGenUpInvest[  eb]() > 1.0 - pEpsilon:
                mTEPES.pGenUpInvest[  eb]   = 1
            if  mTEPES.pGenLoInvest[  eb]() >   mTEPES.pGenUpInvest[eb]():
                mTEPES.pGenLoInvest[  eb]   =   mTEPES.pGenUpInvest[eb]()
        [OptModel.vGenerationInvest[p,eb].setlb(mTEPES.pGenLoInvest[eb]()) for p,eb in mTEPES.peb]
        [OptModel.vGenerationInvest[p,eb].setub(mTEPES.pGenUpInvest[eb]()) for p,eb in mTEPES.peb]
        for p,gd in mTEPES.pgd:
            if  mTEPES.pGenLoRetire[  gd]() <       pEpsilon:
                mTEPES.pGenLoRetire[  gd]   = 0
            if  mTEPES.pGenUpRetire[  gd]() <       pEpsilon:
                mTEPES.pGenUpRetire[  gd]   = 0
            if  mTEPES.pGenLoRetire[  gd]() > 1.0 - pEpsilon:
                mTEPES.pGenLoRetire[  gd]   = 1
            if  mTEPES.pGenUpRetire[  gd]() > 1.0 - pEpsilon:
                mTEPES.pGenUpRetire[  gd]   = 1
            if  mTEPES.pGenLoRetire[  gd]() >   mTEPES.pGenUpRetire[gd]():
                mTEPES.pGenLoRetire[  gd]   =   mTEPES.pGenUpRetire[gd]()
        [OptModel.vGenerationRetire[p,gd].setlb(mTEPES.pGenLoRetire[gd]()) for p,gd in mTEPES.pgd]
        [OptModel.vGenerationRetire[p,gd].setub(mTEPES.pGenUpRetire[gd]()) for p,gd in mTEPES.pgd]
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

        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if  mTEPES.pRsrLoInvest[  rc]() <       pEpsilon:
                    mTEPES.pRsrLoInvest[  rc]   = 0
                if  mTEPES.pRsrUpInvest[  rc]() <       pEpsilon:
                    mTEPES.pRsrUpInvest[  rc]   = 0
                if  mTEPES.pRsrLoInvest[  rc]() > 1.0 - pEpsilon:
                    mTEPES.pRsrLoInvest[  rc]   = 1
                if  mTEPES.pRsrUpInvest[  rc]() > 1.0 - pEpsilon:
                    mTEPES.pRsrUpInvest[  rc]   = 1
                if  mTEPES.pRsrLoInvest[  rc]() >   mTEPES.pRsrUpInvest[rc]():
                    mTEPES.pRsrLoInvest[  rc]   =   mTEPES.pRsrUpInvest[rc]()
            [OptModel.vReservoirInvest [p,rc].setlb(mTEPES.pRsrLoInvest[rc]()) for p,rc in mTEPES.prc]
            [OptModel.vReservoirInvest [p,rc].setub(mTEPES.pRsrUpInvest[rc]()) for p,rc in mTEPES.prc]

        if mTEPES.pIndHydrogen:
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

        if mTEPES.pIndHeat:
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

    # @profile
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
        # tolerance to consider 0 the difference between parameters
        pEpsilon = 1e-6
        for p in mTEPES.p:
            if abs(sum(mTEPES.pScenProb[p,sc]() for sc in mTEPES.sc if (p,sc) in mTEPES.ps)-1.0) > pEpsilon:
                raise ValueError(f'### Sum of scenario probabilities different from 1 in period {p}.')

        for es in mTEPES.es:
            # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows, or no storage capacity for charging
            if sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -            sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) > 0.0:
                raise ValueError('### Total minimum output greater than total inflows for ESS unit ', es, ' by ', sum(mTEPES.pMinPowerElec  [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -    sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')
            if sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -            sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) < 0.0:
                raise ValueError('### Total maximum charge lower than total outflows for ESS unit ',  es, ' by ', sum(mTEPES.pMaxCharge     [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -    sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')
            if max(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) and          max(mTEPES.pMaxPowerElec  [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) and      max(mTEPES.pMaxStorage[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
                raise ValueError('### This ESS unit has no storage capacity for charging ',  es, ' ',             sum(mTEPES.pMaxCharge     [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' MW ', sum(mTEPES.pMaxStorage[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')

        # detect inventory infeasibility
        for p,sc,n,es in mTEPES.ps*mTEPES.nesc:
            if (p,es) in mTEPES.pes:
                if mTEPES.pMaxCapacity[p,sc,n,es]:
                    if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])
                    elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es]() + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es]() + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])

        # detect minimum energy infeasibility
        for p,sc,n,g in mTEPES.ps*mTEPES.ngen:
            if (p,sc,g) in mTEPES.gm and (p,g) in mTEPES.pg:
                if sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
                    raise ValueError('### Minimum energy violation ', p, sc, n, g, sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]))

        # detecting infeasibility: no capacity in the transmission network
        if sum(mTEPES.pLineNTCMax[:,:,:]) == 0.0:
            raise ValueError('### There is no capacity in the network. All the lines have NTC zero probably due to security factor equal to zero')

        # detecting reserve margin infeasibility
        for p,ar in mTEPES.p*mTEPES.ar:
            if     sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in g2a[ar] if (p,g) in mTEPES.pg) < mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]:
                raise     ValueError('### Electricity reserve margin infeasibility ', p,ar, sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and g in g2a[ar]), mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

            if mTEPES.pIndHeat:
                if sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in g2a[ar] if (p,g) in mTEPES.pg) < mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
                    raise ValueError('### Heat reserve margin infeasibility ',        p,ar, sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (p,g) in mTEPES.pg and g in g2a[ar]), mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMargin[p,ar])

        for p,sc,ar in mTEPES.ps*mTEPES.ar:
            if mTEPES.pRESEnergy[p,ar] > sum(mTEPES.pDemandElec[p,sc,n,nd]*mTEPES.pLoadLevelDuration[p,sc,n]() for n,nd in mTEPES.n*d2a[ar] if (p,sc,n,nd) in mTEPES.psnnd):
                raise ValueError('### Minimum renewable energy requirement exceeds the demand ', p, sc, ar, mTEPES.pRESEnergy[p,ar], sum(mTEPES.pDemandElec[p,sc,n,nd] for n,nd in mTEPES.n*d2a[ar] if (p,sc,n,nd) in mTEPES.psnnd))

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
                Stage.nesc = [(n,es) for n,es in Stage.n*mTEPES.es if Stage.n.ord(n) % mTEPES.pStorageTimeStep[es]  == 0]
                Stage.necc = [(n,ec) for n,ec in Stage.n*mTEPES.ec if Stage.n.ord(n) % mTEPES.pStorageTimeStep[ec]  == 0]
                Stage.neso = [(n,es) for n,es in Stage.n*mTEPES.es if Stage.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0]
                Stage.ngen = [(n,g ) for n,g  in Stage.n*mTEPES.g  if Stage.n.ord(n) % mTEPES.pEnergyTimeStep[g]    == 0]

                if mTEPES.pIndHydroTopology:
                    Stage.nhc      = [(n,h ) for n,h  in Stage.n*mTEPES.h  if Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                    if sum(1 for h,rs in mTEPES.p2r):
                        Stage.np2c = [(n,h ) for n,h  in Stage.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                    else:
                        Stage.np2c = []
                    if sum(1 for rs,h in mTEPES.r2p):
                        Stage.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                    else:
                        Stage.npc  = []
                    Stage.nrsc     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) % mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrcc     = [(n,rs) for n,rs in Stage.n*mTEPES.rn if mTEPES.n.ord(n) % mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrso     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) % mTEPES.pWaterOutTimeStep [rs] == 0]

    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
