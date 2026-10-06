"""
September 28, 2026

Tool_openTEPES_To_IAMC — converts the input data and the results of an openTEPES case to the IAMC timeseries format (model, scenario, region, variable,
unit, subannual, one column per period).

The tool first loads the variable-ID dictionaries (oT_IAMC_var_ID_*.csv) and the case input CSV files (demand, generation, network, ...), transforms the
power demand, generation, and transmission data to IAMC layout, and saves them as XLSX workbooks (oT_IAMC_Demand_*, oT_IAMC_GenerationTransmission_*).
It then reads the oT_Result_*.csv files of the case, maps each one to its IAMC variable and unit through the output dictionaries (oT_IAMC_var_OD_*.csv),
aggregates node results by zone with the NodeToZone dictionary, and writes one oT_IAMC_<Result>_<Model>_<Case>.xlsx workbook per result file.
"""

from pathlib import Path

import pandas        as pd
import time          # count clock time
import os

StartTime = time.time()
ModelName = 'openTEPES 4.18.17'
# DirName = Path('C:/Users/Erik/Documents/GitHub/openTEPES_PRO/openTEPES')
DirName   = Path('C:/Users/aramos/OneDrive - Universidad Pontificia Comillas/Andres/openTEPES')
CaseName  = 'WAPP_NZ'                              # To select the case
Folder    = '_IAMC'
_path     = os.path.join(DirName, CaseName)
CSV_READ_ENCODINGS = ('utf-8-sig', 'utf-8', 'cp1252')
CSV_WRITE_ENCODING = 'utf-8-sig'
EXCEL_ENGINE       = 'xlsxwriter'


def read_csv_with_fallback(path, **kwargs):
    if 'encoding' in kwargs:
        return pd.read_csv(path, **kwargs)

    last_error = None
    for encoding in CSV_READ_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(
        f"Unable to decode CSV file '{path}'. Tried encodings: {', '.join(CSV_READ_ENCODINGS)}."
    ) from last_error


def read_table_file(path, **kwargs):
    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        return read_csv_with_fallback(path, **kwargs)
    if suffix in ('.xlsx', '.xlsm', '.xls'):
        return pd.read_excel(path, **kwargs)
    raise ValueError(f"Unsupported input file format '{suffix}' for '{path}'.")


def write_table_file(df, path, sheet_name='Sheet1', index=False, **kwargs):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        encoding = kwargs.pop('encoding', CSV_WRITE_ENCODING)
        df.to_csv(path, index=index, encoding=encoding, **kwargs)
        return
    if suffix in ('.xlsx', '.xlsm', '.xls'):
        with pd.ExcelWriter(path, engine=EXCEL_ENGINE) as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=index, **kwargs)
        return
    raise ValueError(f"Unsupported output file format '{suffix}' for '{path}'.")

#%%                    openTEPES -> IAMC: Process
#                      1) Loading dictionary
#                      2) Reading data
#                      3) Power Demand data transformation
#                      4) Power System data transformation
#                      5) Power Generation data transformation
#                      6) Power Transmission data transformation
#                      7) Writing XLSX data
#                      8) Converting openTEPES results to IAMC XLSX
#%% Loading the dictionary
var_PowerSystem       = read_table_file(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerSystem.csv'      ), index_col=[0])
var_PowerTransmission = read_table_file(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerTransmission.csv'), index_col=[0])
var_PowerGeneration   = read_table_file(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerGeneration.csv'  ), index_col=[0])

#%% reading data from CSV (only the four files this tool actually uses; the other oT_Data_* frames were read and never referenced)
dfDemand     = read_table_file(f'{_path}/oT_Data_Demand_'               f'{CaseName}.csv', index_col=[0,1,2])
dfGeneration = read_table_file(f'{_path}/oT_Data_Generation_'           f'{CaseName}.csv', index_col=[0    ])
dfNetwork    = read_table_file(f'{_path}/oT_Data_Network_'              f'{CaseName}.csv', index_col=[0,1,2])
dfNodeToZone = read_table_file(f'{_path}/oT_Dict_NodeToZone_'           f'{CaseName}.csv', index_col=[0    ])
NodeName     = dfNodeToZone.index.tolist()

# substitute NaN by 0 only in numeric columns
def fillna_numeric(df, value=0.0):
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols):
        df[numeric_cols] = df[numeric_cols].fillna(value)

for df in (dfDemand, dfGeneration, dfNetwork):
    fillna_numeric(df)

#%% Function Type 1
def Converter_Type1(X0,X1,X2,X4,X5,X6):
    VariableType = X1['Variable'][X0]
    UnitType     = X1['Unit'    ][X0]
    # From multiple columns to one column
    a = X2.stack()
    # To set index
    a.index.names = ['Period', 'Scenario', 'LoadLevel', 'Node']
    # To save csv for changing indexes
    a = a.reset_index()
    if X6 == 0:
        a = a.rename(columns={0: 'value'})
        a['Period'  ] = a['Period'  ].astype(str)
        a['Scenario'] = a['Scenario'].astype(str)
        period_names = pd.Index(pd.unique(a['Period']))

        a = a.assign(model    = str(X4))
        a = a.assign(scenario = X5 + '|' + a['Scenario'])
        a = a.assign(region   = a['Node'].map(dfNodeToZone['Zone']).fillna(a['Node']))
        a = a.assign(variable = VariableType)
        a = a.assign(unit     = UnitType)
        a['value'] = pd.to_numeric(a['value']) * 1e-3

        a['subannual'] = a['LoadLevel'].astype(str).str[:11]
        a['subannual'] = a['Period'] + '-' + a['subannual'] + '+01:00'
        a['subannual'] = pd.to_datetime(a['subannual'])
        a['subannual'] = a['subannual'].dt.strftime("%m-%d %H:%M+01:00")

        requires_zone_sum = (a['Node'] != a['region']).any()
        if requires_zone_sum:
            a = a.groupby(by=['model', 'scenario', 'region', 'variable', 'unit', 'subannual', 'Period'], as_index=False, sort=False)['value'].sum()
        else:
            a = a[['model', 'scenario', 'region', 'variable', 'unit', 'subannual', 'Period', 'value']]

        a = a.pivot_table(index=['model', 'scenario', 'region', 'variable', 'unit', 'subannual'],
                          columns='Period', values='value', aggfunc='sum', sort=False).reset_index()

        a = a.rename_axis(None, axis=1)
        period_columns = [p for p in period_names if p in a.columns]
        a = a[['model', 'scenario', 'region', 'variable', 'unit', 'subannual'] + period_columns]
        return a

    # Getting scenario and period names
    ScenarioName = a['Scenario'][0]
    # ScenarioName = "TF"
    PeriodName   = str(a['Period'][0])
    # YearName   = PeriodName.split("y")[1]
    if X6 == 2:
        array = pGeneration1['index']
        a = a.loc[a['Node'].isin(array)]
    if X6 == 3:
        array = pGeneration2['index']
        a = a.loc[a['Node'].isin(array)]
    if X6 == 4:
        array = pGeneration3['index']
        a = a.loc[a['Node'].isin(array)]
    # Adding Variable and Unit columns
    if X6 == 0:
        a = a.assign(Variable = VariableType)
        a = a.assign(Unit     = UnitType)
    else:
        a = a.assign(Variable = a['Node'])
        a = a.assign(Unit     = UnitType)
    # Reorder columns
    a = a[['Scenario', 'Period', 'Node', 'Variable', 'Unit', 'LoadLevel', 0]]
    # Changing column names
    a = a.rename(columns={"Period": "model", "Scenario": "scenario", "Node": "region", "Variable": "variable", "Unit": "unit",
                          "LoadLevel": "subannual", 0: PeriodName})
    a['model'   ] = a['model'   ].astype(str)
    a['scenario'] = a['scenario'].astype(str)
    requires_zone_sum = False
    # Changing Values in Model and Scenario columns
    if X6 == 0:
        a.loc[a['model'   ] == PeriodName,   'model'   ] = str(X4)
        a.loc[a['scenario'] == ScenarioName, 'scenario'] = X5 + '|' + ScenarioName
        a['node'  ] = a['region']
        a['region'] = a['region'].map(dfNodeToZone['Zone']).fillna(a['region'])
        requires_zone_sum = (a['node'] != a['region']).any()
        a[PeriodName] = a[PeriodName] * 1e-3
    else:
        a.loc[a['model'   ] == PeriodName,   'model'   ] = str(X4)
        a.loc[a['scenario'] == ScenarioName, 'scenario'] = X5 + '|' + ScenarioName
        for i in dfGeneration.index:
            a.loc[a['region'  ]   == i, 'region']   = dfGeneration['Node'][i]
            a.loc[a['variable'] == i, 'variable'] = var_PowerGeneration.loc[X0]['Variable'] + '|' + dfGeneration['Technology'][i]
        for i in NodeName:
            a.loc[a['region']   == i, 'region']   = dfNodeToZone['Zone'][i]

    a['subannual'] = a['subannual'].str[:11]
    # a['subannual'] = a['subannual'].str[5:]
    a['subannual'] = (str(PeriodName)+'-'+a['subannual'] + '+01:00')
    # a['time'] = pd.to_datetime(a['time'], utc=True)
    a['subannual'] = pd.to_datetime(a['subannual'])
    a['subannual'] = a['subannual'].dt.strftime("%m-%d %H:%M+01:00")
    if X6 == 0 and requires_zone_sum:
        a = a.groupby(by=['model', 'scenario', 'region', 'variable', 'unit', 'subannual'], as_index=False, sort=False)[PeriodName].sum()
    a = a[['model', 'scenario', 'region', 'variable', 'unit', 'subannual', PeriodName]]
    return a

#%% Function Type 2
def Converter_Type2(X1):
    if X1 == 'VariableCost':
        X1 = 'LinearTerm'
    # both idx families apply the same transformation; only the source frame differs
    pGenerationIdx = {0: pGeneration0, 1: pGeneration1}[var_PowerGeneration.loc[X1]['idx']]
    # Selecting Columns
    a = pGenerationIdx[['Model', 'Scenario', 'Node', 'Variable', 'Unit', 'Subannual', X1]]
    # Changing column names
    a = a.rename(columns={"Model": "model", "Scenario": "scenario", "Node": "region", "Variable": "variable", "Unit": "unit",
                          "Subannual": "subannual", X1: PeriodName})
    # Changing Values in Model and Scenario columns
    a.loc[a['variable'] == ScenarioName, 'variable'] = var_PowerGeneration.loc[X1]['Variable'] + '|' + pGenerationIdx['Technology']
    a.loc[a['unit'    ] == ScenarioName, 'unit'    ] = var_PowerGeneration.loc[X1]['Unit']
    for i in NodeName:
        a.loc[a['region'] == i, 'region'] = dfNodeToZone['Zone'][i]
    a = a[['model', 'scenario', 'region', 'variable', 'unit', PeriodName]]

    return a

#%% Function Type 3
def Converter_Type3(X1):
    # Selecting Columns
    a = pNetwork[['Model', 'Scenario', 'Region', 'Variable', 'Unit', 'Subannual', X1]]
    # Changing column names
    a = a.rename(columns={"Model": "model", "Scenario": "scenario", "Region": "region", "Variable": "variable", "Unit": "unit",
                          "Subannual": "subannual", X1: PeriodName})
    # Changing Values in Model and Scenario columns
    a.loc[a['variable'] == ScenarioName, 'variable'] = var_PowerTransmission.loc[X1]['Variable']
    a.loc[a['unit']     == ScenarioName, 'unit']     = var_PowerTransmission.loc[X1]['Unit']
    a = a[['model', 'scenario', 'region', 'variable', 'unit', PeriodName]]

    return a
#%% Power Demand - Dataframe
InputDemand = Converter_Type1('PowerDemand', var_PowerSystem, dfDemand, ModelName, CaseName, 0)

#%% Power Generation - Main Dataframe
ScenarioName = InputDemand['scenario'][0]
PeriodName   = InputDemand.columns[6]
# Changing indexes: the four pGeneration frames only differ in the technology filter applied to dfGeneration
def make_pGeneration(Technologies=None):
    p = dfGeneration.reset_index()
    if Technologies is not None:
        p = p.loc[p['Technology'].isin(Technologies)]
    return p.assign(Model=ModelName, Scenario=ScenarioName, Variable=ScenarioName, Unit=ScenarioName, Subannual='')

pGeneration0            = make_pGeneration()
pGeneration1            = make_pGeneration(['Hydro_Reservoir', 'Hydro_Pumped Storage', 'Hydrogen', 'Battery'])
pGeneration2            = make_pGeneration(['Solar_PV', 'Wind_Offshore', 'Wind_Onshore'])
pGeneration3            = make_pGeneration(['Hydro_Run of River'])

#%% Storing PowerGeneration data - Dataframe
# InputStorageType        = Converter_Type2('StorageType')
InputMaximumPower       = Converter_Type2('MaximumPower')
# InputMinimumPower       = Converter_Type2('MinimumPower')
# InputMaximumCharge      = Converter_Type2('MaximumCharge')
# InputInitialStorage     = Converter_Type2('InitialStorage')
InputMaxStorageCapacity = Converter_Type2('MaximumStorage')
InputMinStorageCapacity = Converter_Type2('MinimumStorage')
InputEfficiency         = Converter_Type2('Efficiency')
# InputRampUp             = Converter_Type2('RampUp')
# InputRampDown           = Converter_Type2('RampDown')
# InputUpTime             = Converter_Type2('UpTime')
# InputDownTime           = Converter_Type2('DownTime')
InputFuelCost           = Converter_Type2('FuelCost')
InputLinearVarCost      = Converter_Type2('LinearTerm')
InputConstantVarCost    = Converter_Type2('ConstantTerm')
InputOMVarCost          = Converter_Type2('OMVariableCost')
# InputStartUpCost        = Converter_Type2('StartUpCost')
# InputShutDownCost       = Converter_Type2('ShutDownCost')
# InputCO2EmissionRate    = Converter_Type2('CO2EmissionRate')
# InputFixedCost          = Converter_Type2('FixedCost')
# InputFixedChargeRate    = Converter_Type2('FixedChargeRate')
# InputBinaryInvestment   = Converter_Type2('BinaryInvestment')
InputVariableCost       = Converter_Type2('VariableCost')

InputVariableCost[PeriodName] = InputFuelCost[PeriodName] * InputLinearVarCost[PeriodName]
InputVariableCost['unit'    ] = var_PowerGeneration.loc['VariableCost']['Unit']

GroupColumns = ["model", "scenario", "region", "variable", "unit"]
InputEfficiency      = InputEfficiency.groupby     (by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
InputVariableCost    = InputVariableCost.groupby   (by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
InputConstantVarCost = InputConstantVarCost.groupby(by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
InputOMVarCost       = InputOMVarCost.groupby      (by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
# InputLossFactor.fillna              ("", inplace=True)
# InputReactance.fillna              ("", inplace=True)
# InputSecurityFactor.fillna              ("", inplace=True)
#%% Merging Dataframes
gen_frames = [
          # InputStorageType.sort_values     (by ='Variable' ),
          InputMaximumPower.sort_values      (by ='variable' ),
          # InputMinimumPower.sort_values    (by ='Variable' ),
          # InputMaximumCharge.sort_values   (by ='Variable' ),
          # InputInitialStorage.sort_values  (by ='Variable' ),
          InputMaxStorageCapacity.sort_values(by ='variable' ),
          InputMinStorageCapacity.sort_values(by ='variable' ),
          InputEfficiency.sort_values        (by ='variable' ),
          # InputRampUp.sort_values          (by ='variable' ),
          # InputRampDown.sort_values        (by ='variable' ),
          # InputUpTime.sort_values          (by ='variable' ),
          # InputDownTime.sort_values        (by ='variable' ),
          # InputFuelCost.sort_values        (by ='Variable' ),
          # InputLinearVarCost.sort_values   (by ='Variable' ),
          InputVariableCost.sort_values      (by ='variable' ),
          InputConstantVarCost.sort_values   (by ='variable' ),
          InputOMVarCost.sort_values         (by ='variable' ),
          # InputStartUpCost.sort_values     (by ='variable' ),
          # InputShutDownCost.sort_values    (by ='variable' ),
    ]

InputGen = pd.concat(gen_frames)
#%% Saving final CSV
InputGen = InputGen.replace({'variable': {'_': '|'}}, regex=True)
InputGen = InputGen.groupby(by=["model", "scenario", "region", "variable", "unit"]).sum().reset_index().sort_values(by = ["variable", "region"])

#%% Power Network - Main Dataframe
# Changing indexes
pNetwork                                                      = dfNetwork.reset_index()
for i in NodeName:
    pNetwork.loc[pNetwork['InitialNode'] == i, 'InitialNode'] = dfNodeToZone['Zone'][i]
    pNetwork.loc[pNetwork['FinalNode'  ] == i, 'FinalNode'  ] = dfNodeToZone['Zone'][i]
pNetwork                                                      = pNetwork.loc[pNetwork['InitialNode'] != pNetwork['FinalNode']].copy()
pNetwork                                                      = pNetwork.assign(Model    = ModelName)
pNetwork                                                      = pNetwork.assign(Scenario = ScenarioName)
pNetwork                                                      = pNetwork.assign(Region   = pNetwork['InitialNode']+'>'+pNetwork['FinalNode'])
pNetwork                                                      = pNetwork.assign(Variable = ScenarioName)
pNetwork                                                      = pNetwork.assign(Unit     = ScenarioName)
pNetwork                                                      = pNetwork.assign(Subannual= '')

#%% Storing PowerTransmission data - Dataframe
# InputLineType                                                 = Converter_Type3('LineType')
# InputVoltage                                                  = Converter_Type3('Voltage')
InputLossFactor                                               = Converter_Type3('LossFactor')
InputReactance                                                = Converter_Type3('Reactance')
InputTTC                                                      = Converter_Type3('TTC')
InputTTC[PeriodName]                                          = pd.to_numeric(InputTTC[PeriodName]) / 1e3
# InputTTCBck                                                   = Converter_Type3('TTCBck')
InputSecurityFactor                                           = Converter_Type3('SecurityFactor')
# InputFxCost                                                   = Converter_Type3('FixedCost')
# InputFxChargeRate                                             = Converter_Type3('FixedChargeRate')
# InputInvestment                                               = Converter_Type3('BinaryInvestment')

InputLossFactor     = InputLossFactor.groupby    (by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
InputReactance      = InputReactance.groupby     (by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])
InputSecurityFactor = InputSecurityFactor.groupby(by=GroupColumns).mean().reset_index().sort_values(by=["variable", "region"])

trans_frames = [
          InputLossFactor.sort_values    (by ='region' ),
          InputReactance.sort_values     (by ='region' ),
          InputTTC.sort_values           (by ='region' ),
          InputSecurityFactor.sort_values(by ='region' )
    ]

InputTran = pd.concat(trans_frames)
InputTran = InputTran.replace({'variable': {'_': '|'}}, regex=True)
InputTran = InputTran.groupby(by=["model", "scenario", "region", "variable", "unit"]).sum().reset_index().sort_values(by = ["variable", "region"])

#%% Saving XLSX (Demand, Generation, Transmission)
# the year headers travel as strings (Converter_Type1 casts Period to str to build subannual); write them as numbers in the XLSX
def YearColumnsToInt(df):
    return df.rename(columns={c: int(c) for c in df.columns if str(c).isdigit()})

output_path = os.path.join(DirName, Folder, 'oT_IAMC_Data_Generation_'f'{ModelName}_{CaseName}.xlsx')
write_table_file(YearColumnsToInt(InputGen), output_path)
print(f"Files saved to {output_path}")
print(f'Writing Generation data: OK')

output_path = os.path.join(DirName, Folder, 'oT_IAMC_Data_Network_'f'{ModelName}_{CaseName}.xlsx')
write_table_file(YearColumnsToInt(InputTran), output_path)
print(f'Writing Network    data: OK')

output_path = os.path.join(DirName, Folder, 'oT_IAMC_Data_Demand_'f'{ModelName}_{CaseName}.xlsx')
write_table_file(YearColumnsToInt(InputDemand), output_path)
print(f'Writing Demand     data: OK')

# Mapping of a short key to each IAMC variable-definition CSV file name.
Files = {
    "generation":   "oT_IAMC_var_OD_PowerGeneration.csv",
    "system":       "oT_IAMC_var_OD_PowerSystem.csv",
    "transmission": "oT_IAMC_var_OD_PowerTransmission.csv",
}

ResultFiles = {
    "NetworkInvestmentPerUnit":       {"header": [0, 1, 2], "index_col": [0      ]},
    "NetworkFlowElecPerNode":         {"header": [0, 1, 2], "index_col": [0, 1, 2]},
    "NetworkLosses":                  {"header": [0, 1, 2], "index_col": [0, 1, 2]},
    "NetworkAngle":                   {"header": [0      ], "index_col": [0, 1, 2]},
    "NetworkPNS":                     {"header": [0      ], "index_col": [0, 1, 2]},
    "NetworkSRMC":                    {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationInvestment":           {"header": [0      ], "index_col": [0      ]},
    # "GenerationCommitment":           {"header": [0      ], "index_col": [0, 1, 2]},
    # "GenerationStartup":              {"header": [0      ], "index_col": [0, 1, 2]},
    # "GenerationShutdown":             {"header": [0      ], "index_col": [0, 1, 2]},
    "Generation":                     {"header": [0      ], "index_col": [0, 1, 2]},
    "Consumption":                    {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationOperatingReserveUp":   {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationOperatingReserveDown": {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationInventory":            {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationSpillage":             {"header": [0      ], "index_col": [0, 1, 2]},
}

ResultDefinitions = {
    "NetworkInvestmentPerUnit":       ("transmission", "vNetworkInvest"),
    "NetworkFlowElecPerNode":         ("transmission", "vFlow"),
    "NetworkLosses":                  ("transmission", "vLineLosses"),
    "NetworkAngle":                   ("transmission", "vTheta"),
    "NetworkPNS":                     ("transmission", "vPNS"),
    "NetworkSRMC":                    ("transmission", "vSRMC"),
    "GenerationInvestment":           ("generation",   "vGenerationInvest"),
    # "GenerationCommitment":           ("generation",   "vCommitment"),
    # "GenerationStartup":              ("generation",   "vStartUp"),
    # "GenerationShutdown":             ("generation",   "vShutDown"),
    "Generation":                     ("generation",   "vTotalOutput"),
    "Consumption":                    ("generation",   "vESSCharge"),
    "GenerationOperatingReserveUp":   ("generation",   "vReserveUp"),
    "GenerationOperatingReserveDown": ("generation",   "vReserveDown"),
    "GenerationInventory":            ("generation",   "vESSInventory"),
    "GenerationSpillage":             ("generation",   "vESSSpillage"),
}


def ReadOutputDictionaries():
    OutputDictionaries = {}
    for key, file_name in Files.items():
        dictionary = read_table_file(os.path.join(DirName, Folder, file_name), index_col=[0])
        dictionary.index = dictionary.index.astype(str).str.strip()
        OutputDictionaries[key] = dictionary
    return OutputDictionaries


def ConvertResultToIAMC(ResultName, ResultData, OutputDictionaries):
    DefinitionFile, DefinitionRow = ResultDefinitions[ResultName]
    VariableName = OutputDictionaries[DefinitionFile].loc[DefinitionRow, 'Variable']
    UnitName     = OutputDictionaries[DefinitionFile].loc[DefinitionRow, 'Unit'    ]
    VariableName = '' if pd.isna(VariableName) else VariableName

    ResultData = ResultData.copy()

    if ResultData.columns.nlevels == 3:
        ResultData.columns.names = ['InitialNode', 'FinalNode', 'Circuit']
    else:
        ResultData.columns.name = 'Node'

    if ResultData.index.nlevels == 3:
        ResultData.index.names = ['Period', 'Scenario', 'LoadLevel']
    elif ResultData.index.nlevels == 2:
        ResultData.index.names = ['Period', 'Scenario']
    else:
        ResultData.index.names = ['Period']

    long_data = ResultData.stack(list(ResultData.columns.names)).rename('value').reset_index()

    if 'InitialNode' in long_data.columns:
        if ResultName in ('NetworkFlowElecPerNode', 'NetworkLosses'):
            # aggregate line flows and losses by zone: both end nodes are mapped to their zone (NodeToZone dictionary), the circuit is dropped from
            # the region name, and every line joining the same pair of zones collapses in the pivot_table below, whose aggfunc='sum' adds them up
            ni = long_data['InitialNode'].astype(str)
            nf = long_data['FinalNode'  ].astype(str)
            ni_zone = ni.map(dfNodeToZone['Zone']).fillna(ni)
            nf_zone = nf.map(dfNodeToZone['Zone']).fillna(nf)
            interzonal_mask = ni_zone != nf_zone
            long_data = long_data.loc[interzonal_mask].copy()
            region = ni_zone.loc[interzonal_mask] + '>' + nf_zone.loc[interzonal_mask]
        else:
            region = (long_data['InitialNode'].astype(str) + '|' + long_data['Circuit'].astype(str) + '>'
                      + long_data['FinalNode'].astype(str) + '|' + long_data['Circuit'].astype(str))
    else:
        # aggregate results by zone. Generation results carry GENERATOR columns, so they are first located at their node (dfGeneration);
        # then every node is mapped to its zone (NodeToZone dictionary), and names without a match keep their own value.
        # Rows sharing the same zone collapse in the pivot_table below, whose aggfunc='sum' adds them up
        node = long_data['Node'].astype(str)
        if DefinitionFile == 'generation':
            node = node.map(dfGeneration['Node']).fillna(node)
        region = node.map(dfNodeToZone['Zone']).fillna(node)

    scenario = CaseName + '|' + long_data['Scenario'].astype(str) if 'Scenario' in long_data.columns else CaseName
    subannual = long_data['LoadLevel'].astype(str) if 'LoadLevel' in long_data.columns else ''

    iamc_data = pd.DataFrame({'model': ModelName, 'scenario': scenario, 'region': region, 'variable': VariableName, 'unit': UnitName,
                              'subannual': subannual, 'Period': long_data['Period'], 'value': long_data['value']})

    iamc_data = iamc_data.pivot_table(index=['model', 'scenario', 'region', 'variable', 'unit', 'subannual'],
                                      columns='Period', values='value', aggfunc='sum').reset_index()

    iamc_data.columns.name = None
    return iamc_data


OutputDictionaries = ReadOutputDictionaries()
ConvertedResults   = 0

for ResultName, ReadOptions in ResultFiles.items():
    candidate_names = [ResultName]
    if 'Startup' in ResultName:
        candidate_names.append(ResultName.replace('Startup', 'StartUp'))
    if 'Shutdown' in ResultName:
        candidate_names.append(ResultName.replace('Shutdown', 'ShutDown'))

    ResultPath = None
    for candidate_name in candidate_names:
        candidate_path = os.path.join(_path, f'oT_Result_{candidate_name}_{CaseName}.csv')
        if os.path.isfile(candidate_path):
            ResultPath = candidate_path
            break

    if ResultPath is None:
        print(f'WARNING: result file not found, skipping: oT_Result_{ResultName}_{CaseName}.csv')
        continue

    ResultData = read_table_file(ResultPath, **ReadOptions)
    IAMCResult = ConvertResultToIAMC(ResultName, ResultData, OutputDictionaries)
    OutputPath = os.path.join(DirName, Folder, f'oT_IAMC_Result_{ResultName}_{ModelName}_{CaseName}.xlsx')
    write_table_file(IAMCResult, OutputPath)
    ConvertedResults += 1
    print(f'Writing {ResultName:31s} result: OK')
