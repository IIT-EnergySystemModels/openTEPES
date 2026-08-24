"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 23, 2026
"""

import time
import math
import os
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import Set, Param, NonNegativeReals, Reals

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_InputSource             import df_to_set_values, InputSource
    from .openTEPES_InputCSVSource          import CSVSource
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_InputSource    import df_to_set_values, InputSource
    from openTEPES.openTEPES_InputCSVSource import CSVSource

# from line_profiler import profile


# @profile
def InputData(DirName, CaseName, mTEPES, pIndLogConsole, option_overrides=None):
    print('Input data                             ****')

    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # set_definitions: maps each mTEPES Set attribute to the underlying dictionary file stem and whether the Set is ordered. The 'ordered'
    # flag was previously a hardcoded membership check in the read loop; making it declarative keeps the policy next to the data.
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

    # Source resolution: prefer mTEPES.pInputSource if openTEPES_run set one (DuckDB or CSV); otherwise build a CSVSource from (DirName,
    # CaseName). The CSV path through CSVSource is byte-identical to the historical pd.read_csv calls.
    source: InputSource = getattr(mTEPES, "pInputSource", None) or CSVSource(_path)
    mTEPES.pInputSource = source  # make accessible to DataConfiguration etc.

    # Reading dictionaries through the source. df_to_set_values converts a 1-col DataFrame -> list of values, an n-col DataFrame -> list of
    # tuples (relation/membership), which is exactly the shape Set(initialize=...) accepts.
    # the same dimension dict backs several sets (nd/ni/nf, cc/c2): read it once
    pDictCache: dict[str, list] = {}
    for set_name, (dict_stem, is_ordered) in set_definitions.items():
        if dict_stem not in pDictCache:
            pDictCache[dict_stem] = df_to_set_values(source.read_dict(dict_stem))
        setattr(mTEPES, set_name, Set(initialize=pDictCache[dict_stem], ordered=is_ordered, doc=dict_stem))

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

    # Tables only the AC optimal power flow consumes. Unlike the hydrogen and heat tables, whose mere presence switches the sector on, these are driven
    # by an explicit option flag — so a case can carry AC data and still be run as DC. ReactiveDemand is a full time series, hence worth not reading.
    AC_ONLY_STEMS = {'ReactiveDemand', 'BusShunt'}

    def _peek_option(flag: str) -> int:
        """Read one flag out of oT_Data_Option, or out of oT_Data_Parameter when that is where the case put it.

        Both tables are single rows, so this is cheap. Looking in BOTH matters: the main read loop below copies every
        Parameter column into ``par``, so a case that puts IndACPowerFlow there builds a full AC model. If this peek
        only consulted Option it would answer 0, skip ReactiveDemand and BusShunt, and the run would go all the way to
        a solved AC case carrying no reactive demand and no shunts -- a wrong model that looks like a right one.
        """
        # the overrides first: a flag given on the command line has to reach this peek as well, or an AC run started that
        # way would skip ReactiveDemand and BusShunt and solve a system with no reactive demand and no shunts
        if option_overrides and flag in option_overrides:
            try:
                return int(option_overrides[flag])
            except (TypeError, ValueError):
                return 0
        for stem in ('Option', 'Parameter'):
            try:
                df = source.read_data(stem)
                # the conversion belongs inside the try as well: a blank cell reads as NaN and int(NaN) raises
                if flag in df.columns:
                    return int(df[flag].iloc[0])
            except Exception:
                continue
        # The main read loop below tolerates a malformed Option table with a warning and carries on. This peek runs first, so it must not be the
        # stricter of the two: a table that used to warn would otherwise abort the run before the loop is ever reached.
        return 0

    def read_input_data():
        """Read every oT_Data table the source knows about.

        Returns (dfs, par) — dfs maps 'df{stem}' to its wide-format (indexed where applicable) DataFrame; par carries the per-feature availability flags driven by FLAG_MAPPING.
        """
        dfs: dict[str, pd.DataFrame] = {}
        par: dict[str, int] = {}

        pIndAC = _peek_option('IndACPowerFlow')

        # Remember what the source OFFERED, so the AC reader can tell "this case has no shunts" from "this case has shunts that failed to arrive".
        # Only the second is worth a warning, and it is otherwise silent: _peek_option swallows every exception and returns 0, which skips the AC
        # stems, while the main loop below still reads IndACPowerFlow = 1 and the AC model is built with no reactive compensation at all.
        pStems = list(source.list_data_stems())
        par['pBusShuntOffered'] = 1 if 'BusShunt' in pStems else 0

        for fs in pStems:
            if fs in AC_ONLY_STEMS and not pIndAC:
                continue
            dp_key, _, _ = FLAG_MAPPING.get(fs, (None, None, None))
            header = HEADER_LEVELS.get(fs)
            try:
                dfs[f'df{fs}'] = source.read_data(fs, header_levels=header)
                if dp_key:
                    par[dp_key] = 1
            except (KeyError, ValueError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
                # the table is there but its shape or encoding does not fit: the model has always tolerated this, so warn loudly
                # and carry on with the feature disabled instead of aborting the whole run
                print(f'WARNING: oT_Data_{fs} is present but could not be parsed and will be IGNORED ({type(e).__name__}: {e})')
                if dp_key:
                    par[dp_key] = 0
            except Exception as e:
                # anything else is a programming error, not a data problem: fail loudly
                raise RuntimeError(f'oT_Data_{fs}: present in the source but could not be read ({type(e).__name__}: {e})') from e

        return dfs, par

    dfs, par = read_input_data()
    # if 'pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat' are not in par, add them and set their value to zero
    for key in ['pIndRampReserves', 'pIndReserveActivation', 'pIndVarTTC', 'pIndPTDF', 'pIndHydroTopology', 'pIndHydrogen', 'pIndHeat']:
        if key not in par.keys():
            par[key] = 0

    # replace NaN with 0 (only on numeric columns to avoid dtype errors on string columns)
    for key,df in dfs.items():
        num_cols = df.select_dtypes(include='number').columns
        # A blank cell in a text column arrives as NaN from the CSV reader but as None from DuckDB. Both mean "not given", so write NaN in every text column and
        # the model sees the same case whichever way it was read.
        for col in df.columns.difference(num_cols):
            df[col] = df[col].where(df[col].notna(), math.nan)
        if   key == 'dfEmission':
            df.fillna({col: math.inf for col in num_cols}, inplace=True)
        elif key == 'dfGeneration':
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

    if 'dfGeneration' not in dfs:
        raise RuntimeError(f'oT_Data_Generation_{CaseName}: the generation table is mandatory and could not be read')

    if (dfs['dfGeneration']['Efficiency'] == 0.0).any():
        print('WARNING: Efficiency values of 0.0 are not valid. They have been changed to 1.0.')
        print("If you want to disable charging, set 'MaximumCharge' to 0.0 or leave it empty.")
    dfs['dfGeneration']['Efficiency'] = dfs['dfGeneration']['Efficiency'].where(dfs['dfGeneration']['Efficiency'] != 0.0, 1.0)

    # show some statistics of the data
    for key, df in dfs.items():
        if pIndLogConsole and any(suffix in key for suffix in mTEPES.frames_suffixes):
            if df.shape[1] == 0:
                print(f'{key}: DataFrame without columns (shape={df.shape}). describe() is omitted.\n')
            else:
                print(f'{key}:\n', df.describe(), '\n')
    # Optional reservoir / hydro topology dicts. Each is present in the source iff the user populated the corresponding oT_Dict_*.csv (or DB table);
    # an absent / empty dict yields an empty Pyomo Set.
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

    # load parameters from dfOption — single-row 0/1 binary flags. Direct int() avoids the unusual .iloc[0].astype('int') pattern
    # (astype on a numpy scalar works but is unidiomatic).
    for col in dfs['dfOption'].columns:
        par[f'p{col}'] = int(dfs['dfOption'][col].iloc[0])

    # Option flags a case may leave out of oT_Data_Option entirely. Absent means the historical behaviour: DC network, no AC model.
    #   pIndACPowerFlow  0 = DC (default)
    #                    1 = branch flow: |V|^2, |I|^2 and P, Q per branch, with the angle carried as a node potential
    #                    2 = bus injection in W space: W_ii = |V_i|^2 and W_ij = V_i conj(V_j) per branch, relaxed by a second-order cone
    #                    3 = bus injection in rectangular coordinates: V = e + jf, the exact non-convex equations, for a non-linear solver
    #                    Bose & Low prove 1 and 2 give the SAME bound. That is a statement about the optimal value, not about conditioning, solve
    #                    time or behaviour inside branch and bound, which is why both are offered and measured rather than one assumed better.
    #   pIndACCycle      0 = off (default), 1 = add the loop condition sum(arg W_ij) = 0 around each independent cycle.
    #                    Meaningful only for 2: in W space the angle lives in arg(W_ij) and nothing ties it around a loop. For 1 the angle is an
    #                    explicit node potential so the sum is identically zero and the constraint says nothing; for 3 the voltages are explicit.
    #   pIndACModelType  0 = SOCP relaxation (default, the only option that returns a valid bound)
    #                    1 = piecewise-linear branch flow, a MILP and therefore the only variant that scales to a full year
    #                    2 = exact NLP, for the Phase 7 validation pass with the binaries fixed
    # See doc/design/AC_OPF_Formulation_Choices.md for why these three and not the rest.
    #   pIndACRestore    0 = report the relaxed solution as it stands (default)
    #                    1 = after solving, hold the plan and re-solve the network at the exact current equality on a non-linear
    #                        solver, so the reported operating point satisfies the AC equations. See ACRestorationPass.
    #   pIndACConverter  0 = HVDC links carry active power only, with no converter (default, and what the DC model has always done)
    #                    1 = line-commutated converters: each station DRAWS reactive power, tan(acos(pf)) times the active power it
    #                        transfers, at both ends. This is the realistic default for classic HVDC and it makes the AC system need
    #                        more compensation, not less.
    #                    2 = voltage-source converters: each station is a controllable reactive source or sink within its rating, so
    #                        it behaves like a STATCOM and RELIEVES the AC system instead of burdening it.
    #   pIndBinShuntSwitch  1 = a switchable shunt is discrete, on or off (default, and what a mechanically switched bank actually does)
    #                       0 = the same state relaxed to [0,1], which keeps an AC run continuous at the cost of letting a bank sit half in
    for key in ['pIndACPowerFlow', 'pIndACModelType', 'pIndACRestore', 'pIndACConverter', 'pIndACCycle']:
        par.setdefault(key, 0)
    # Command-line overrides land here: after both tables have been read, so they win, and before the validation below,
    # so a bad value is refused with the same message a bad cell in the case would get.
    if option_overrides:
        for pKey, pVal in option_overrides.items():
            pName = pKey if pKey.startswith('p') and pKey[1:2].isupper() else f'p{pKey}'
            pCast = pVal
            if isinstance(pVal, str):
                try:
                    pCast = int(pVal)
                except ValueError:
                    try:
                        pCast = float(pVal)
                    except ValueError:
                        pCast = pVal
            par[pName] = pCast
        print(f'### NOTE: option(s) overridden on the command line: '
              f'{", ".join(f"{k}={v}" for k, v in option_overrides.items())}')

    #   pIndPTDF         0 = no flow-based coupling (default)
    #                    1 = read the factors from oT_Data_VariablePTDF
    #                    2 = compute them from the reactances, so the factors cannot disagree with the network beside them
    # The flag used to be implied by the presence of the table alone. That still works, and is the default when the case
    # says nothing, but an explicit value now wins and a value that contradicts the case is an error rather than a guess.
    pPTDFOffered = 1 if 'dfVariablePTDF' in dfs else 0
    par['pIndPTDF'] = int(par.get('pIndPTDF', pPTDFOffered))
    if par['pIndPTDF'] not in (0, 1, 2):
        raise NotImplementedError(f"IndPTDF = {par['pIndPTDF']} is not implemented; use 0 (off), 1 (read from the case) or 2 (computed)")
    if par['pIndPTDF'] == 1 and not pPTDFOffered:
        raise ValueError('IndPTDF = 1 reads the factors from oT_Data_VariablePTDF, and the case has no such table. '
                         'Use IndPTDF = 2 to have them computed from the reactances, or 0 to switch flow-based coupling off.')
    if par['pIndPTDF'] == 2 and pPTDFOffered:
        raise ValueError('IndPTDF = 2 computes the factors from the reactances, but the case also provides '
                         'oT_Data_VariablePTDF. Remove the table, or use IndPTDF = 1 to read it.')

    # How the problem is solved, as opposed to what is modelled. These were literals in openTEPES.py until now, so no case
    # could select any of them. The defaults are the values that used to be hard-coded.
    #   pIndCycleFlow            0 = Kirchhoff's second law per branch (default), 1 = cycle formulation. DC only.
    #   pIndSectorDecomposition  0 = one problem (default), 1 = Benders decomposition by sector
    #   pIndCompleteProblem      1 = solve the complete problem (default), 0 = time Benders decomposition
    #   pIndSequentialSolving    0 = stages in parallel, 1 = sequentially through an LP file (default),
    #                            2 = sequentially in memory, 3 = by sensitivity analysis
    for pKey, pDefault, pAllowed in (('pIndCycleFlow', 0, (0, 1)), ('pIndSectorDecomposition', 0, (0, 1)),
                                     ('pIndCompleteProblem', 1, (0, 1)), ('pIndSequentialSolving', 1, (0, 1, 2, 3))):
        par.setdefault(pKey, pDefault)
        if par[pKey] not in pAllowed:
            raise NotImplementedError(f'{pKey[1:]} = {par[pKey]} is not implemented; use one of {list(pAllowed)}')

    # oT_Data_Option is where the indicators belong; oT_Data_Parameter is for the numeric scalars. Both are read, because
    # a flag that only reaches one of them used to build a different model from the one the case asked for, but a flag in
    # the wrong file is still worth saying out loud: the next reader of the case will look in Option and not find it.
    pOptionCols = set(dfs['dfOption'].columns) if 'dfOption' in dfs else set()
    pMisplaced  = sorted(c for c in dfs['dfParameter'].columns if c.startswith('Ind') and c not in pOptionCols)
    if pMisplaced:
        print(f'### WARNING: {", ".join(pMisplaced)} found in oT_Data_Parameter. They are honoured, but they belong in '
              f'oT_Data_Option, which is where a reader of the case will look for them.')

    # How hard the AC branch current is priced. It has to be case data: the value that closes the cone depends on the cost
    # scale and the loading of the case, not on anything the model can derive. Measured on a tight cone, 9n_AC needs 1e-3,
    # RTS-GMLC 1e-4 and pglib case118 1e-6 — a thousandfold spread. Too small and the relaxation buys voltage with current
    # that is not there; too large and it distorts the dispatch, by 16% on RTS-GMLC at 1e-3. IndACRestore is the way to a
    # physical operating point that costs nothing in the objective, so this can be kept small.
    from openTEPES.openTEPES_ModelFormulationObjective import AC_CURRENT_PENALTY as pDefaultEps
    par.setdefault('pEpsilonCurrent', pDefaultEps)
    if float(par['pEpsilonCurrent']) < 0.0:
        raise ValueError(f"EpsilonCurrent = {par['pEpsilonCurrent']} is negative; it prices the branch current and must be at least 0")

    par.setdefault('pIndBinShuntSwitch', 1)
    if par['pIndBinShuntSwitch'] not in (0, 1):
        raise NotImplementedError(f"IndBinShuntSwitch = {par['pIndBinShuntSwitch']} is not implemented; use 1 (binary) or 0 (relaxed)")
    if par['pIndACPowerFlow'] not in (0, 1, 2, 3):
        raise NotImplementedError(f"IndACPowerFlow = {par['pIndACPowerFlow']} is not implemented; use 0 (DC), 1 (branch flow), "
                                  f"2 (bus injection, W space) or 3 (bus injection, rectangular)")
    if par['pIndACCycle'] not in (0, 1):
        raise NotImplementedError(f"IndACCycle = {par['pIndACCycle']} is not implemented; use 0 (off) or 1 (loop condition)")
    if par['pIndACCycle'] and par['pIndACPowerFlow'] != 2:
        raise NotImplementedError('IndACCycle applies only to IndACPowerFlow = 2. Under branch flow the angle is a node potential, so the loop '
                                  'condition is identically satisfied; under rectangular coordinates the voltages are explicit.')
    if par['pIndACModelType'] not in (0, 1, 2):
        raise NotImplementedError(f"IndACModelType = {par['pIndACModelType']} is not implemented; use 0 (SOCP), 1 (piecewise linear) or 2 (NLP)")
    if par['pIndACRestore'] not in (0, 1):
        raise NotImplementedError(f"IndACRestore = {par['pIndACRestore']} is not implemented; use 0 (off) or 1 (exact restoration pass)")
    if par['pIndACConverter'] not in (0, 1, 2):
        raise NotImplementedError(f"IndACConverter = {par['pIndACConverter']} is not implemented; use 0 (none), 1 (LCC) or 2 (VSC)")

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
    if par['pIndPTDF'] == 1:
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

    # AC optimal power flow tables. Called here so the reactive demand is averaged on the same rolling window as the active demand just below.
    ReadACInputData(dfs, par, mTEPES, pIndLogConsole)

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

        if par['pIndPTDF'] == 1:
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
    par['pNameplateMaxPowerElec']      = dfs['dfGeneration']  ['MaximumPower'              ] * 1e-3                                                      # nameplate maximum electric power, NOT derated[GW]
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
    par['pRMinReactivePower']          = dfs['dfGeneration']  ['MinimumReactivePower'      ] * 1e-3                                                      # rated minimum reactive power                 [Gvar]
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

    #%% storing the parameters on the model for backward compatibility (external consumers that pickle mTEPES or inspect inputs post-load
    # rely on these). New callers should consume dfs/par from the return value instead.
    mTEPES.dFrame  = dfs
    mTEPES.dPar    = par

    ReadingDataTime = time.time() - StartTime
    StartTime       = time.time()
    print('Reading    input data                  ... ', round(ReadingDataTime), 's')

    return dfs, par


# ======================================================================================================================
# AC input data
# ======================================================================================================================
# Everything the AC formulations need from the case files, and the bound tightening that runs before the variables are
# declared. Read by ReadACInputData below; ConfigureACData is called later by openTEPES_DataConfiguration, which imports
# it from here.

# Bound tightening limits. The sweep stops at MAX_SWEEPS or when the largest change falls below TOLERANCE; MAX_ANGLE is the widest angle the
# arcsine can return and is the cap when the thermal limit implies no bound at all.
MAX_ANGLE  = math.pi / 2
MAX_SWEEPS = 20
TOLERANCE  = 1e-6


def TightenACBounds(mTEPES, par, pIndLogConsole=0):
    """Compute tightened per-branch angle bounds and per-bus voltage bounds, and store them on ``par``.

    Writes ``par['pMaxAngleDiff']`` and ``par['pMinAngleDiff']`` (radians, per branch), ``par['pVMinBus']`` and ``par['pVMaxBus']`` (per unit, per bus).
    Returns a small dict of statistics for logging.
    """
    StartTime = time.time()

    branches = list(mTEPES.laa)
    vmin, vmax = par['pVMin'], par['pVMax']
    pSBase = par['pSBase']

    # --- angle bounds ------------------------------------------------------------------------------------------------------------------------------
    # The two sides are carried separately. Collapsing them to one symmetric band with min(|AngMin|, |AngMax|) cuts off range the case explicitly
    # permits: a branch declared -50 to +20 degrees would be solved at +/-20, losing 30 degrees on the negative side. This module's whole contract is
    # that it may only use inequalities the model already implies, so a tightening the data does not support does not belong here.
    pMaxAngleDiff, pMinAngleDiff, pTightened = {}, {}, 0
    for la in branches:
        z = math.sqrt(par['pLineR'][la] ** 2 + par['pLineX'][la] ** 2)
        # per unit, and at the largest apparent power the thermal limit together with the voltage band actually permits
        smax = par['pLineSmax'][la] / pSBase * vmax / vmin
        pTapF = par['pLineTapFactor'][la]
        # The declared values are used with their SIGNS. Taking abs() of each side misreads a one-sided band: a branch declared +5 to +30 degrees
        # would come out with a lower limit of -5, and one declared -30 to -5 with an upper limit of +5 — in both cases the band enforced is not the
        # band the case asked for. ConfigureACData has already checked AngMin < AngMax.
        pHi = min(par['pAngMax'][la],  MAX_ANGLE)
        pLo = max(par['pAngMin'][la], -MAX_ANGLE)
        if z <= 0.0 or smax <= 0.0:
            # No implied bound to apply — a branch with no impedance or no rating. The clamp above still matters here: the angle envelope divides by
            # cos(t/2), so a limit near pi would give cos(t/2) ~ 6e-17 and coefficients around 1e16, which no solver will handle.
            pMaxAngleDiff[la], pMinAngleDiff[la] = pHi, pLo
            continue
        # the sending-end voltage the impedance sees carries the tap, so the divisor is (Vmin_i/tau) * Vmin_j
        implied = math.asin(min(1.0, smax * z / (vmin * pTapF * vmin)))
        pMaxAngleDiff[la] = min(pHi,  implied)
        pMinAngleDiff[la] = max(pLo, -implied)
        if implied < min(pHi, -pLo) - TOLERANCE:
            pTightened += 1

    # --- voltage bounds ----------------------------------------------------------------------------------------------------------------------------
    # Only branches that are ALWAYS in service may propagate a voltage bound. eVoltageDropUp/Lo release the drop equation through a big-M on
    # vLineCommit when a candidate or switchable branch is out of service, so its drop equation is not something the model always implies — and this
    # module may only use what the model always implies. Propagating across a candidate line narrows the vW box of a node reachable only through it,
    # which can cut off the do-not-build plan.
    # mTEPES.lc (candidates) and mTEPES.ls (switchable) are already built by the time this runs and carry exactly this distinction. They are used in
    # preference to the par Series, whose index has been remapped by this point in DataConfiguration.
    # A branch also drops out of the model in periods outside its own commissioning window: SettingUpVariables fixes its vLineCommit to 0 and
    # eVoltageDropUp/Lo is skipped for it. pVMinBus and pVMaxBus are per bus and shared across every period, so a bound justified by a branch that
    # exists only from period 2 would still be imposed in period 1. Propagate only across branches that are in service in EVERY period.
    pFirst, pLast = mTEPES.p.first(), mTEPES.p.last()
    pReleasable = set(mTEPES.lc) | set(mTEPES.ls) | {
        la for la in branches
        if par['pElecNetPeriodIni'][la] > pFirst or par['pElecNetPeriodFin'][la] < pLast}
    incident = defaultdict(list)
    for la in branches:
        if la in pReleasable:
            continue
        ni, nf, cc = la
        incident[ni].append(la)
        incident[nf].append(la)

    lo = {nd: vmin ** 2 for nd in mTEPES.nd}
    hi = {nd: vmax ** 2 for nd in mTEPES.nd}
    # the reference bus voltage is the anchor the propagation spreads from
    ref = mTEPES.rf.first()
    lo[ref] = hi[ref] = par['pVNom'] ** 2

    pSweeps = 0
    for pSweeps in range(1, MAX_SWEEPS + 1):
        pMoved = 0.0
        for nd in mTEPES.nd:
            if nd == ref:
                continue
            pNewLo, pNewHi = lo[nd], hi[nd]
            for la in incident[nd]:
                z2 = par['pLineR'][la] ** 2 + par['pLineX'][la] ** 2
                z  = math.sqrt(z2)
                smax = par['pLineSmax'][la] / pSBase * vmax / vmin
                if smax <= 0.0:
                    continue
                pTapF   = par['pLineTapFactor'][la]
                pTap2   = pTapF ** 2
                pSpan   = 2.0 * smax * z
                pLossUb = z2 * (smax / (vmin * pTapF)) ** 2
                # The drop equation is w_j = w_i*f^2 - 2(rP+xQ) + z^2*l, with f = 1/tau. It is not symmetric once f differs from 1, so which end of
                # the branch this node sits on decides whether f^2 multiplies or divides.
                if la[0] == nd:                                     # nd sends: w_nd = (w_other + 2(rP+xQ) - z^2*l) / f^2
                    other  = la[1]
                    pNewLo = max(pNewLo, (lo[other] - pSpan - pLossUb) / pTap2)
                    pNewHi = min(pNewHi, (hi[other] + pSpan          ) / pTap2)
                else:                                               # nd receives: w_nd = w_other*f^2 - 2(rP+xQ) + z^2*l
                    other  = la[0]
                    pNewLo = max(pNewLo,  lo[other] * pTap2 - pSpan)
                    pNewHi = min(pNewHi,  hi[other] * pTap2 + pSpan + pLossUb)
            if pNewLo > pNewHi:          # the propagation crossed: the case is infeasible on these data
                raise ValueError(f'### Bound tightening: node {nd} has no feasible voltage range '
                                 f'([{math.sqrt(max(pNewLo,0)):.4f}, {math.sqrt(max(pNewHi,0)):.4f}] p.u.). '
                                 f'Check the line ratings and the voltage band.')
            pMoved = max(pMoved, abs(pNewLo - lo[nd]), abs(pNewHi - hi[nd]))
            lo[nd], hi[nd] = pNewLo, pNewHi
        if pMoved < TOLERANCE:
            break

    par['pMaxAngleDiff'] = pMaxAngleDiff
    par['pMinAngleDiff'] = pMinAngleDiff
    par['pVMinBus'] = {nd: math.sqrt(max(lo[nd], 0.0)) for nd in mTEPES.nd}
    par['pVMaxBus'] = {nd: math.sqrt(max(hi[nd], 0.0)) for nd in mTEPES.nd}

    pStats = {
        'branches':          len(branches),
        'angle_tightened':   pTightened,
        'angle_max_deg':     max((max(abs(pMaxAngleDiff[la]), abs(pMinAngleDiff[la])) for la in pMaxAngleDiff), default=0.0) * 180 / math.pi,
        'angle_median_deg':  (sorted(pMaxAngleDiff.values())[len(pMaxAngleDiff) // 2] * 180 / math.pi) if pMaxAngleDiff else 0.0,
        'voltage_sweeps':    pSweeps,
        'voltage_band_min':  min(par['pVMinBus'].values()),
        'voltage_band_max':  max(par['pVMaxBus'].values()),
        'seconds':           time.time() - StartTime,
    }

    print(f"Bound tightening                       ...  {pStats['angle_tightened']}/{pStats['branches']} branch angle bounds tightened, "
          f"median {pStats['angle_median_deg']:.2f} deg, max {pStats['angle_max_deg']:.2f} deg; "
          f"voltage {pStats['voltage_band_min']:.4f}-{pStats['voltage_band_max']:.4f} p.u. in {pStats['voltage_sweeps']} sweeps")
    return pStats


AC_SCALAR_DEFAULTS = {
    'pVMin':         0.95,
    'pVNom':         1.00,
    'pVMax':         1.05,
    'pCapacitivePF': 0.95,   # leading power factor limit for reactive-capable units
    'pInductivePF':  0.95,   # lagging power factor limit
    # Converter power factor, used for both HVDC converter models. 0.85 gives tan(acos(pf)) = 0.62, which is in the usual range for a
    # line-commutated station: an LCC draws roughly half to two thirds of the transferred active power as reactive power.
    'pConverterPF':  0.85,
    # Converter station losses, one station. Zero by default, so a case that does not ask for them gets exactly the results it got before.
    # NoLoad is a fraction of the link rating and is paid whenever the link is in service; Marginal is a fraction of the power the station
    # carries. A modern VSC station is roughly 0.001 and 0.010, an LCC station roughly 0.001 and 0.007. Both stations of a link are charged,
    # so a link with the VSC figures loses about 2% of what it carries, plus 0.2% of its rating standing.
    'pConverterNoLoadLoss':   0.0,
    'pConverterMarginalLoss': 0.0,
}

# Columns oT_Data_BusShunt must provide. Missing ones are filled with the default rather than raising, so a minimal shunt table stays valid.
SHUNT_COLUMN_DEFAULTS = {
    'Node':                None,   # mandatory, no default
    'InitialPeriod':       0,
    'FinalPeriod':         0,
    'Gshb':                0.0,
    'Bshb':                0.0,
    'FixedInvestmentCost': 0.0,
    'FixedChargeRate':     0.0,
    'BinaryInvestment':    0,
    'Switchable':          0,
    'Units':               1,
    'InvestmentLo':        0.0,
    'InvestmentUp':        0.0,
}


def ReadACInputData(dfs, par, mTEPES, pIndLogConsole):
    """Read the AC-only input tables into ``par``.

    Called from ``InputData`` after the sector tables and before the ``pTimeStep`` averaging block, so the reactive demand is averaged on the same
    rolling window as the active demand.
    """
    if not par.get('pIndACPowerFlow', 0):
        return

    StartTime = time.time()

    # --- reactive demand -------------------------------------------------------------------------------------------------------------------------
    # Optional: a case can drive the AC model with no reactive load at all (line charging and shunts still act). An absent table becomes zeros on the
    # index the active demand already uses, so every downstream .loc[psn] and filter_rows call behaves identically either way.
    if 'dfReactiveDemand' in dfs:
        par['pReactiveDemand'] = dfs['dfReactiveDemand'].reindex(columns=mTEPES.nd, fill_value=0.0) * 1e-3   # reactive demand [Gvar]
    else:
        print('WARNING: oT_Data_ReactiveDemand is absent; the AC model runs with zero reactive demand at every node.')
        par['pReactiveDemand'] = par['pDemandElec'] * 0.0

    if par['pTimeStep'] > 1:
        par['pReactiveDemand'] = par['pReactiveDemand'].rolling(par['pTimeStep']).mean()
        par['pReactiveDemand'].fillna(0.0, inplace=True)

    # --- bus shunt devices -----------------------------------------------------------------------------------------------------------------------
    if 'dfBusShunt' in dfs:
        dfShunt = dfs['dfBusShunt']
        missing = [c for c, d in SHUNT_COLUMN_DEFAULTS.items() if c not in dfShunt.columns and d is None]
        if missing:
            raise ValueError(f'oT_Data_BusShunt: mandatory column(s) {missing} are absent')
        for col, default in SHUNT_COLUMN_DEFAULTS.items():
            if col not in dfShunt.columns:
                dfShunt[col] = default
        # SHUNT_COLUMN_DEFAULTS fills a missing COLUMN; a blank CELL still arrives as NaN. Left alone, a blank FinalPeriod fails the window test below
        # and the device disappears from the model with no message, and a blank InvestmentLo reaches setlb() as NaN. Fill the cells too.
        for col, default in SHUNT_COLUMN_DEFAULTS.items():
            if col in dfShunt.columns and default is not None:      # Node is mandatory and has no default to fill with
                dfShunt[col] = dfShunt[col].fillna(default)
        # A device with Units > 1 is a bank of that many IDENTICAL units. The decision is then how many units are in service, not a continuous
        # susceptance -- the VAR source model of Alvarez, Paredes and Rider (IET GTD 13(13), 2019), where a bus carries an integer count of sources
        # of fixed susceptance. Expanding the bank into one device per unit here means every set, variable, constraint and result downstream handles
        # it with the machinery that already exists for single devices, and the count in service is simply how many are on.
        pUnits = dfShunt['Units'].fillna(1).astype(float).round().astype(int).clip(lower=1)
        par['pShuntStepPairs'] = []
        if (pUnits > 1).any():
            pRows = []
            for sh in dfShunt.index:
                if pUnits[sh] == 1:
                    pRows.append(dfShunt.loc[[sh]])
                    continue
                pNames = [f'{sh}_u{k + 1}' for k in range(pUnits[sh])]
                pBank  = pd.concat([dfShunt.loc[[sh]]] * pUnits[sh])
                pBank.index = pNames
                pRows.append(pBank)
                # consecutive pairs, so the ordering constraint can break the permutation symmetry between identical units
                par['pShuntStepPairs'] += list(zip(pNames, pNames[1:]))
            dfShunt = pd.concat(pRows)
            dfs['dfBusShunt'] = dfShunt

        par['pShuntToNode']        = dfShunt['Node'                ]
        par['pShuntPeriodIni']     = dfShunt['InitialPeriod'       ]
        par['pShuntPeriodFin']     = dfShunt['FinalPeriod'         ].where(dfShunt['FinalPeriod'] != 0, 3000)
        par['pBusGshb']            = dfShunt['Gshb'                ]                                          # shunt conductance at the bus [p.u.]
        par['pBusBshb']            = dfShunt['Bshb'                ]                                          # shunt susceptance at the bus [p.u.]
        par['pShuntFixedCost']     = dfShunt['FixedInvestmentCost' ] * dfShunt['FixedChargeRate']              # shunt fixed cost             [MEUR]
        # A device given an investment cost but no charge rate multiplies out to zero, lands in `she`, is always in service and costs nothing. That is
        # a data mistake, not a modelling choice, and it is invisible in the results — so say so.
        pSilent = dfShunt.index[(dfShunt['FixedInvestmentCost'] > 0.0) & (dfShunt['FixedChargeRate'] <= 0.0)].tolist()
        if pSilent:
            print(f'WARNING: bus shunt(s) {pSilent} give a FixedInvestmentCost but no FixedChargeRate, so their annualised cost is zero. '
                  f'They will be treated as existing devices, always in service and free.')
        par['pShuntBinUnitInvest'] = dfShunt['BinaryInvestment'    ]
        par['pShuntSwitchable']    = dfShunt['Switchable'          ]                                          # hourly on/off state [0,1]
        par['pShuntLoInvest']      = dfShunt['InvestmentLo'        ]
        par['pShuntUpInvest']      = dfShunt['InvestmentUp'        ].where(dfShunt['InvestmentUp'] > 0.0, 1.0)
        par['pIndBusShunt']        = 1
    else:
        # Warn only when the case OFFERED a shunt table that then failed to arrive. An AC case with no shunts at all is perfectly normal — RTS-GMLC
        # has none — so warning on every such run is noise of exactly the kind the reactive-slack warning had to be cured of.
        if par.get('pBusShuntOffered', 0):
            print('### WARNING: the case provides an oT_Data_BusShunt table but it did not reach the model, so the system has been built with no bus '
                  'shunt devices and no reactive compensation from them. Check that the table was read.')
        par['pIndBusShunt']        = 0
        par['pShuntStepPairs']     = []

    # --- scalars ---------------------------------------------------------------------------------------------------------------------------------
    # Voltage limits and power-factor limits come from oT_Data_Parameter. They are read by the generic scalar loop in InputData when the columns are
    # present; fill in the defaults for the columns the case leaves out.
    for key, default in AC_SCALAR_DEFAULTS.items():
        # A zero here is read as "not given". openTEPES_InputData fills blank numeric cells with 0.0 before this runs, so a blank cell and a declared
        # zero are the same value by the time they arrive and cannot be told apart. The isna test is kept as a guard for a source that does not fill.
        #
        # The consequence is that CapacitivePF = 0 or InductivePF = 0 cannot be used to say "no reactive support from generators" — it gets the 0.95
        # default instead. Set a very small value rather than zero to express that.
        if key not in par or pd.isna(par[key]) or par[key] == 0.0:
            par[key] = default

    if par['pVMin'] >= par['pVMax']:
        raise ValueError(f"VMin ({par['pVMin']}) must be below VMax ({par['pVMax']})")

    # A converter that loses a quarter of what it carries is a data error, not a converter. The bound is loose on purpose: it is there to catch a
    # percentage entered as 2 instead of 0.02, which would otherwise solve and quietly report a link that consumes more than it delivers.
    for key in ('pConverterNoLoadLoss', 'pConverterMarginalLoss'):
        if par[key] >= 0.25:
            raise ValueError(f"{key[1:]} = {par[key]} is a fraction, not a percentage; 0.02 means 2%")

    if pIndLogConsole:
        print('Reading AC input data                  ... ', round(time.time() - StartTime), 's')


def ConfigureACData(mTEPES, dfs, par):
    """Build the AC sets and Pyomo parameters on ``mTEPES``.

    Called from ``DataConfiguration`` after the branch parameters have been filtered onto ``mTEPES.la`` and after the psn* index sets exist.
    """
    if not par.get('pIndACPowerFlow', 0):
        return

    StartTime = time.time()

    pFirstPeriod = mTEPES.p.first()
    pLastPeriod  = mTEPES.p.last()

    # --- derived branch model --------------------------------------------------------------------------------------------------------------------
    # Series admittance from the series impedance. pLineX is guaranteed non-zero on mTEPES.la (it is part of the filter that builds la), so the
    # denominator cannot vanish even when a line is given zero resistance.
    pLineZ2 = par['pLineR']**2 + par['pLineX']**2
    par['pLineG']  =  par['pLineR'] / pLineZ2                                       # series conductance [p.u.]
    par['pLineB']  = -par['pLineX'] / pLineZ2                                       # series susceptance [p.u.], negative for an inductive branch
    par['pLineZ2'] = pLineZ2

    # Apparent-power rating. pLineNTCFrw/Bck already carry the security factor, and pLineNTCMax is their element-wise maximum, so this needs no
    # further scaling: it is the larger of the two directional ratings, in GVA.
    par['pLineSmax'] = par['pLineNTCMax']

    # Tap factor. A blank Tap column arrives as 0.0 meaning "not a transformer", which must map to 1.0 and not to a division by zero.
    pTap = par['pLineTAP'].where(par['pLineTAP'] > 0.0, 1.0)
    par['pLineTapFactor'] = 1.0 / pTap

    # Angle-difference limits. A blank AngMin/AngMax pair arrives as 0.0, which would pin the angle difference of every branch to exactly zero and
    # make the model infeasible the moment any power flows. Treat "both zero" as "not given" and open the limits to +/- pi/2.
    # openTEPES_InputData fills every blank numeric cell of dfNetwork with 0.0 before this runs, so a blank angle limit and a declared zero are
    # indistinguishable here — testing for NaN would be dead code. Each side is therefore opened whenever it is zero, not only when both are:
    # a half-filled pair (blank AngMin, AngMax = 30) would otherwise leave pMinAngleDiff at 0, and eAngleBandLo would then require
    # vTheta_i - vTheta_j >= 0, making reverse flow on that branch infeasible.
    #
    # The cost of this reading is that a case genuinely wanting a one-sided band of exactly 0 cannot express it. That is the right trade: a zero
    # angle limit pins the branch, which is almost never intended, while a blank column is common.
    par['pAngMin'] = par['pAngMin'].where(par['pAngMin'] != 0.0, -math.pi/2)
    par['pAngMax'] = par['pAngMax'].where(par['pAngMax'] != 0.0,  math.pi/2)
    if (par['pAngMin'] >= par['pAngMax']).any():
        bad = par['pAngMin'].index[par['pAngMin'] >= par['pAngMax']].tolist()
        raise ValueError(f'oT_Data_Network: AngMin must be below AngMax on line(s) {bad}')

    # --- branch index set ------------------------------------------------------------------------------------------------------------------------
    mTEPES.psnlad = Set(doc='psn x DC branch', initialize=[(p,sc,n,ni,nf,cc) for p,sc,n in mTEPES.psn for ni,nf,cc in mTEPES.lad if (p,ni,nf,cc) in mTEPES.pla])
    mTEPES.psnlaa = Set(doc='psn x AC branch', initialize=[(p,sc,n,ni,nf,cc) for p,sc,n in mTEPES.psn for ni,nf,cc in mTEPES.laa if (p,ni,nf,cc) in mTEPES.pla])

    # --- cycles: not computed ---------------------------------------------------------------------------------------------------------------------
    # An earlier version built the cycle basis here for a cyclic angle constraint. That constraint is not built — with vTheta explicit the sum of angle
    # differences round a closed cycle telescopes to zero identically, so it was 0 == 0 on every row (see openTEPES_ModelFormulationElectricity). The basis is
    # not computed either: nx.minimum_cycle_basis is roughly cubic in the edge count, which is real build time on a national case for a set nothing
    # reads. Eliminating vTheta in favour of the cycle form, as both reference papers do for compactness, would need it back.

    # --- bound tightening ------------------------------------------------------------------------------------------------------------------------
    # Runs here, before the variables are declared, because it is what makes the angle envelope tight enough to be worth anything.
    TightenACBounds(mTEPES, par, pIndLogConsole=0)

    # --- shunt sets ------------------------------------------------------------------------------------------------------------------------------
    # sqc and shc are declared empty in DataConfiguration so the DC path can reference them; replace them here with the real contents.
    mTEPES.del_component(mTEPES.shc)
    mTEPES.del_component(mTEPES.sqc)

    if par['pIndBusShunt']:
        sShunt = [sh for sh in dfs['dfBusShunt'].index
                  if par['pShuntPeriodIni'][sh] <= pLastPeriod and par['pShuntPeriodFin'][sh] >= pFirstPeriod]
        for sh in sShunt:
            if par['pShuntToNode'][sh] not in mTEPES.nd:
                raise ValueError(f"oT_Data_BusShunt: shunt {sh} sits on node {par['pShuntToNode'][sh]}, which is not in the node dictionary")
    else:
        sShunt = []

    mTEPES.sh  = Set(doc='bus shunt devices',       initialize=sShunt)
    mTEPES.she = Set(doc='existing  shunt devices', initialize=[sh for sh in sShunt if par['pShuntFixedCost'][sh] == 0.0])
    mTEPES.shc = Set(doc='candidate shunt devices', initialize=[sh for sh in sShunt if par['pShuntFixedCost'][sh] >  0.0])
    # A switchable device carries an on/off state per hour. Devices are fixed unless the case says otherwise, so a table written before this
    # column existed keeps behaving exactly as it did.
    sShuntSw   = [sh for sh in sShunt if par['pShuntSwitchable'][sh] == 1]
    mTEPES.shw = Set(doc='switchable shunt devices', initialize=sShuntSw)
    # consecutive units of one bank, restricted to the devices that survived the period window
    mTEPES.shp = Set(doc='ordered pairs of sibling bank units', dimen=2,
                     initialize=[(a, b) for a, b in par.get('pShuntStepPairs', []) if a in sShunt and b in sShunt])

    # Synchronous condensers split into existing and candidate on their investment cost, read straight from the generation table rather than from
    # par['pGenInvestCost']: that series is narrowed to mTEPES.eb at openTEPES_DataConfiguration.py:833, which runs before this function, and a
    # condenser is never in eb because eb is a subset of g and a zero-MW unit is not in g.
    pGenTable  = dfs['dfGeneration']
    pSynchCost = (pGenTable['FixedInvestmentCost'].astype(float) * pGenTable['FixedChargeRate'].astype(float)).fillna(0.0)

    mTEPES.sqe = Set(doc='existing  synchronous condensers', initialize=[sq for sq in mTEPES.sq if pSynchCost[sq] == 0.0])
    mTEPES.sqc = Set(doc='candidate synchronous condensers', initialize=[sq for sq in mTEPES.sq if pSynchCost[sq] >  0.0])

    # --- node-to-device maps ---------------------------------------------------------------------------------------------------------------------
    # Built as explicit membership lists rather than through a filtered cross product: nd*sh would be |nd|*|sh| membership tests, which is wasted work
    # on a large case when the relation is already one row per device.
    mTEPES.n2sh = Set(doc='node to shunt device',          initialize=[(par['pShuntToNode'][sh], sh) for sh in sShunt])
    mTEPES.n2gq = Set(doc='node to reactive-capable unit', initialize=[(par['pGenToNode'][gq], gq) for gq in mTEPES.gq if par['pGenToNode'][gq] in mTEPES.nd])
    mTEPES.n2sq = Set(doc='node to synchronous condenser', initialize=[(par['pGenToNode'][sq], sq) for sq in mTEPES.sq if par['pGenToNode'][sq] in mTEPES.nd])
    mTEPES.sh2n = par['pShuntToNode'] if par['pIndBusShunt'] else pd.Series(dtype=object)

    # --- index sets ------------------------------------------------------------------------------------------------------------------------------
    # Availability of a reactive unit is its own period window, NOT membership of mTEPES.pg. A synchronous condenser has MaximumPower = 0, so it never
    # enters mTEPES.g (openTEPES_DataConfiguration.py:60) and therefore never enters pg — filtering through pg would empty these sets for exactly the
    # units they exist to hold. Widening the g filter instead would drag a zero-MW unit through commitment, ramps and the second-block machinery in
    # every case, including DC ones, for no benefit.
    pGenIn = pGenTable['InitialPeriod'].astype(float).fillna(0.0)
    pGenFi = pGenTable['FinalPeriod'  ].astype(float).fillna(0.0).replace(0.0, 3000.0)

    mTEPES.psnsh = Set(doc='psn x shunt',                  initialize=[(p,sc,n,sh) for p,sc,n in mTEPES.psn for sh in sShunt
                                                                       if par['pShuntPeriodIni'][sh] <= p and par['pShuntPeriodFin'][sh] >= p])
    mTEPES.psnshw= Set(doc='psn x switchable shunt',       initialize=[(p,sc,n,sh) for p,sc,n in mTEPES.psn for sh in sShuntSw
                                                                       if par['pShuntPeriodIni'][sh] <= p and par['pShuntPeriodFin'][sh] >= p])
    mTEPES.pgq   = Set(doc='period x reactive unit',       initialize=[(p,gq) for p in mTEPES.p for gq in mTEPES.gq
                                                                       if pGenIn[gq] <= p and pGenFi[gq] >= p])
    mTEPES.psqc  = Set(doc='period x candidate condenser', initialize=[(p,sq) for p,sq in mTEPES.pgq if sq in mTEPES.sqc])
    mTEPES.psngq = Set(doc='psn x reactive unit',          initialize=[(p,sc,n,gq) for p,sc,n in mTEPES.psn for gq in mTEPES.gq if (p,gq) in mTEPES.pgq])
    mTEPES.psnsq = Set(doc='psn x synchronous condenser',  initialize=[(p,sc,n,sq) for p,sc,n in mTEPES.psn for sq in mTEPES.sq if (p,sq) in mTEPES.pgq])
    mTEPES.psh   = Set(doc='period x shunt',               initialize=[(p,sh)      for p      in mTEPES.p   for sh in sShunt
                                                                       if par['pShuntPeriodIni'][sh] <= p and par['pShuntPeriodFin'][sh] >= p])
    mTEPES.pshc  = Set(doc='period x candidate shunt',     initialize=[(p,sh)      for p,sh   in mTEPES.psh if sh in mTEPES.shc])

    # --- reactive demand onto the model index ----------------------------------------------------------------------------------------------------
    par['pReactiveDemand'] = par['pReactiveDemand'].loc[mTEPES.psn]

    def _stack_on(df, index_set):
        df = df.stack(future_stack=True)
        return df[df.index.isin(index_set)]

    par['pReactiveDemand'] = _stack_on(par['pReactiveDemand'], mTEPES.psnnd)

    # --- Pyomo parameters ------------------------------------------------------------------------------------------------------------------------
    # The reactive limits are rated nameplate values and do not vary with the load level, so they are indexed on gq alone. Expanding them onto psngq
    # the way the active-power limits are expanded would store |psn| identical copies of every number — 65,520 entries instead of 15 on the 9-bus case.
    mTEPES.pReactiveDemand   = Param(mTEPES.psnnd, initialize=par['pReactiveDemand'].to_dict()                 , within=Reals, doc='Reactive demand [Gvar]', mutable=True)
    mTEPES.pMaxReactivePower = Param(mTEPES.gq,    initialize=par['pRMaxReactivePower'].loc[mTEPES.gq].to_dict(), within=Reals, doc='Rated maximum reactive power [Gvar]')
    mTEPES.pMinReactivePower = Param(mTEPES.gq,    initialize=par['pRMinReactivePower'].loc[mTEPES.gq].fillna(0.0).to_dict(), within=Reals, doc='Rated minimum reactive power [Gvar]')
    if mTEPES.sqc:
        mTEPES.pSynchFixedCost = Param(mTEPES.sqc, initialize=pSynchCost.loc[list(mTEPES.sqc)].to_dict(), within=NonNegativeReals, doc='Synchronous condenser fixed cost [MEUR]')
        # A condenser is never in mTEPES.eb, so the generation investment bounds are narrowed away before they reach it and its own InvestmentLo /
        # InvestmentUp / BinaryInvestment columns were simply not read. A case declaring InvestmentUp = 0 to say "do not build this" got it built
        # anyway, and BinaryInvestment = 0 still produced an integer variable — both unlike an ordinary generator with the same settings. Read here,
        # from the generation table, because this is where the condenser sets are known.
        pSynchLo  = pGenTable['InvestmentLo'    ].astype(float).fillna(0.0) if 'InvestmentLo'     in pGenTable.columns else None
        pSynchUp  = pGenTable['InvestmentUp'    ].astype(float).fillna(1.0) if 'InvestmentUp'     in pGenTable.columns else None
        pSynchBin = pGenTable['BinaryInvestment'].astype(float).fillna(0.0) if 'BinaryInvestment' in pGenTable.columns else None
        sqcList   = list(mTEPES.sqc)
        mTEPES.pSynchLoInvest      = Param(mTEPES.sqc, initialize={sq: (pSynchLo [sq] if pSynchLo  is not None else 0.0) for sq in sqcList}, within=NonNegativeReals, doc='Lower bound of the condenser investment decision [p.u.]')
        # an InvestmentUp of 0 in the data means "not buildable"; a MISSING column means "no limit", which is 1
        mTEPES.pSynchUpInvest      = Param(mTEPES.sqc, initialize={sq: (pSynchUp [sq] if pSynchUp  is not None else 1.0) for sq in sqcList}, within=NonNegativeReals, doc='Upper bound of the condenser investment decision [p.u.]')
        mTEPES.pSynchBinUnitInvest = Param(mTEPES.sqc, initialize={sq: (pSynchBin[sq] if pSynchBin is not None else 0.0) for sq in sqcList}, within=NonNegativeReals, doc='Binary condenser investment decision')

    mTEPES.pLineG            = Param(mTEPES.la,    initialize=par['pLineG'].to_dict()           , within=Reals,            doc='Series conductance [p.u.]'                            )
    mTEPES.pLineB            = Param(mTEPES.la,    initialize=par['pLineB'].to_dict()           , within=Reals,            doc='Series susceptance [p.u.], negative if inductive'     )
    mTEPES.pLineZ2           = Param(mTEPES.la,    initialize=par['pLineZ2'].to_dict()          , within=NonNegativeReals, doc='Squared series impedance R^2+X^2 [p.u.]'              )
    mTEPES.pLineSmax         = Param(mTEPES.la,    initialize=par['pLineSmax'].to_dict()        , within=NonNegativeReals, doc='Apparent power rating [GVA]'                          )
    mTEPES.pLineTapFactor    = Param(mTEPES.la,    initialize=par['pLineTapFactor'].to_dict()   , within=NonNegativeReals, doc='1/tap, multiplies the mutual admittance terms [p.u.]' )

    # Tightened bounds. pMaxAngleDiff is the per-branch angle-difference limit after propagation, and is what the angle envelope's slack
    # tan(t/2) - t/2 is computed from; pVMinBus / pVMaxBus are the per-bus voltage bounds. See TightenACBounds above.
    # Reals, not NonNegativeReals: the tightening keeps the declared signs, so a branch declared -30 to -5 degrees has a NEGATIVE upper limit and
    # a non-negative domain would refuse to build the model at all.
    mTEPES.pMaxAngleDiff     = Param(mTEPES.laa,   initialize=par['pMaxAngleDiff']              , within=Reals,            doc='Tightened angle-difference limit [rad]'               )
    mTEPES.pMinAngleDiff     = Param(mTEPES.laa,   initialize=par['pMinAngleDiff']              , within=Reals,            doc='Tightened angle-difference limit, lower [rad]'       )
    mTEPES.pVMinBus          = Param(mTEPES.nd,    initialize=par['pVMinBus']                   , within=NonNegativeReals, doc='Tightened minimum voltage magnitude [p.u.]'           )
    mTEPES.pVMaxBus          = Param(mTEPES.nd,    initialize=par['pVMaxBus']                   , within=NonNegativeReals, doc='Tightened maximum voltage magnitude [p.u.]'           )

    mTEPES.pVMin             = Param(initialize=par['pVMin']        , within=NonNegativeReals, doc='Minimum voltage magnitude [p.u.]')
    mTEPES.pVNom             = Param(initialize=par['pVNom']        , within=NonNegativeReals, doc='Nominal voltage magnitude [p.u.]')
    mTEPES.pVMax             = Param(initialize=par['pVMax']        , within=NonNegativeReals, doc='Maximum voltage magnitude [p.u.]')
    mTEPES.pCapacitivePF     = Param(initialize=par['pCapacitivePF'], within=NonNegativeReals, doc='Capacitive power factor limit [p.u.]')
    mTEPES.pInductivePF      = Param(initialize=par['pInductivePF'] , within=NonNegativeReals, doc='Inductive  power factor limit [p.u.]')
    mTEPES.pConverterPF      = Param(initialize=par['pConverterPF'] , within=NonNegativeReals, doc='HVDC converter power factor [p.u.]')
    mTEPES.pConverterNoLoadLoss   = Param(initialize=par['pConverterNoLoadLoss']  , within=NonNegativeReals, doc='HVDC converter no-load loss, one station, per unit of the link rating [p.u.]')
    mTEPES.pConverterMarginalLoss = Param(initialize=par['pConverterMarginalLoss'], within=NonNegativeReals, doc='HVDC converter marginal loss, one station, per unit of the power it carries [p.u.]')

    if par['pIndBusShunt']:
        mTEPES.pBusGshb            = Param(mTEPES.sh, initialize=par['pBusGshb'].loc[list(mTEPES.sh)].to_dict()           , within=Reals,            doc='Shunt conductance [p.u.]'                  , mutable=True)
        mTEPES.pBusBshb            = Param(mTEPES.sh, initialize=par['pBusBshb'].loc[list(mTEPES.sh)].to_dict()           , within=Reals,            doc='Shunt susceptance [p.u.]'                  , mutable=True)
        mTEPES.pShuntFixedCost     = Param(mTEPES.sh, initialize=par['pShuntFixedCost'].loc[list(mTEPES.sh)].to_dict()    , within=NonNegativeReals, doc='Shunt fixed cost [MEUR]'                                )
        mTEPES.pShuntBinUnitInvest = Param(mTEPES.sh, initialize=par['pShuntBinUnitInvest'].loc[list(mTEPES.sh)].to_dict(), within=NonNegativeReals, doc='Binary shunt investment decision'                       )
        mTEPES.pShuntLoInvest      = Param(mTEPES.sh, initialize=par['pShuntLoInvest'].loc[list(mTEPES.sh)].to_dict()     , within=NonNegativeReals, doc='Lower bound of the shunt investment decision [p.u.]'    )
        mTEPES.pShuntUpInvest      = Param(mTEPES.sh, initialize=par['pShuntUpInvest'].loc[list(mTEPES.sh)].to_dict()     , within=NonNegativeReals, doc='Upper bound of the shunt investment decision [p.u.]'    )

    print('Setting up AC input data               ... ', round(time.time() - StartTime), 's')
