from pathlib import Path

import pandas        as pd
import time          # count clock time
import os

StartTime = time.time()
ModelName = 'openTEPES 2.0.5'
# DirName   = Path('C:/Users/Erik/Documents/GitHub/openTEPES_PRO/openTEPES')
DirName   = Path('C:/Users/aramos/OneDrive - Universidad Pontificia Comillas/Andres/openTEPES')
CaseName  = 'EAPP'                              # To select the case
Folder = '_IAMC'
_path = os.path.join(DirName, CaseName)

#%%                    IAMC -> openTEPES: Process
#                      1) Loading dictionary
#                      2) Reading data
#                      3) Power Demand data transformation
#                      4) Power System data transformation
#                      4) Power Generation data transformation
#                      4) Power Transmission data transformation
#                      5) Writing data
#%% Loading the dictionary
var_PowerSystem        = pd.read_csv(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerSystem.csv'      ), index_col=[0])
var_PowerTransmission  = pd.read_csv(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerTransmission.csv'), index_col=[0])
var_PowerGeneration    = pd.read_csv(os.path.join(DirName, Folder, 'oT_IAMC_var_ID_PowerGeneration.csv'  ), index_col=[0])

print('Dictionary                            status: OK')

#%% reading data from CSV
dfOption             = pd.read_csv(f'{_path}/oT_Data_Option_'               f'{CaseName}.csv', index_col=[0    ])
dfParameter          = pd.read_csv(f'{_path}/oT_Data_Parameter_'            f'{CaseName}.csv', index_col=[0    ])
dfDuration           = pd.read_csv(f'{_path}/oT_Data_Duration_'             f'{CaseName}.csv', index_col=[0]    )
dfScenario           = pd.read_csv(f'{_path}/oT_Data_Scenario_'             f'{CaseName}.csv', index_col=[0    ])
dfNodeLocation       = pd.read_csv(f'{_path}/oT_Data_NodeLocation_'         f'{CaseName}.csv', index_col=[0    ])
dfDuration           = pd.read_csv(f'{_path}/oT_Data_Duration_'             f'{CaseName}.csv', index_col=[0    ])
dfDemand             = pd.read_csv(f'{_path}/oT_Data_Demand_'               f'{CaseName}.csv', index_col=[0,1,2])
dfDwOperatingReserve = pd.read_csv(f'{_path}/oT_Data_OperatingReserveDown_' f'{CaseName}.csv', index_col=[0,1,2])
dfUpOperatingReserve = pd.read_csv(f'{_path}/oT_Data_OperatingReserveUp_'   f'{CaseName}.csv', index_col=[0,1,2])
dfGeneration         = pd.read_csv(f'{_path}/oT_Data_Generation_'           f'{CaseName}.csv', index_col=[0    ])
dfVariableMaxPower   = pd.read_csv(f'{_path}/oT_Data_VariableMaxGeneration_'f'{CaseName}.csv', index_col=[0,1,2])
dfVariableMinPower   = pd.read_csv(f'{_path}/oT_Data_VariableMinGeneration_'f'{CaseName}.csv', index_col=[0,1,2])
dfVariableMinStorage = pd.read_csv(f'{_path}/oT_Data_VariableMinStorage_'   f'{CaseName}.csv', index_col=[0,1,2])
dfVariableMaxStorage = pd.read_csv(f'{_path}/oT_Data_VariableMaxStorage_'   f'{CaseName}.csv', index_col=[0,1,2])
dfESSEnergyInflows   = pd.read_csv(f'{_path}/oT_Data_EnergyInflows_'        f'{CaseName}.csv', index_col=[0,1,2])
dfNetwork            = pd.read_csv(f'{_path}/oT_Data_Network_'              f'{CaseName}.csv', index_col=[0,1,2])
dfNodeToZone         = pd.read_csv(f'{_path}/oT_Dict_NodeToZone_'           f'{CaseName}.csv', index_col=[0 ])
# substitute NaN by 0
dfOption.fillna              (0, inplace=True)
dfParameter.fillna           (0, inplace=True)
dfDuration.fillna            (0, inplace=True)
dfScenario.fillna            (0, inplace=True)
dfNodeLocation.fillna        (0, inplace=True)
dfDuration.fillna            (0, inplace=True)
dfDemand.fillna              (0, inplace=True)
dfDwOperatingReserve.fillna  (0, inplace=True)
dfUpOperatingReserve.fillna  (0, inplace=True)
dfGeneration.fillna          (0, inplace=True)
dfVariableMaxPower.fillna    (0, inplace=True)
dfVariableMinPower.fillna    (0, inplace=True)
dfVariableMinStorage.fillna  (0, inplace=True)
dfVariableMaxStorage.fillna  (0, inplace=True)
dfESSEnergyInflows.fillna    (0, inplace=True)
dfNetwork.fillna             (0, inplace=True)

dfESSEnergyInflows = dfESSEnergyInflows/1000

ReadingDataTime = time.time() - StartTime
StartTime       = time.time()
print('Reading           input data                ... ', round(ReadingDataTime), 's')

#%% Function Type 1
def Converter_Type1(X0,X1,X2,X4,X5,X6):
    VariableType = X1['Variable'][X0]
    UnitType     = X1['Unit'][X0]
    NodeName    = dfDemand.columns
    # From multiple columns to one colums
    a = X2.stack()
    # To set index
    a.index.names = ['Period', 'Scenario', 'LoadLevel', 'Node']
    # To save csv for changing indexes
    a = a.reset_index()
    # Getting scenario and period names
    ScenarioName = a['Scenario'][0]
    # ScenarioName = "TF"
    PeriodName   = a['Period'][0]
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
    # Adding NUTS to Region
    for i in NodeName:
        a.loc[a['Node'] == i, 'Node'] = i
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
    a = a.rename(columns={"Period": "model", "Scenario": "scenario", "Node": "region", "Variable": "variable", "Unit": "unit", "LoadLevel": "subannual", 0: 2030})
    # Changing Values in Model and Scenario columns
    if X6 == 0:
        a.loc[a['model'] == PeriodName, 'model'] = str(X4)
        a.loc[a['scenario'] == ScenarioName, 'scenario'] = X5 + '|' + ScenarioName
        for k in NodeName:
            a.loc[a['region'] == k, 'region'] = dfNodeToZone['Zone'][k]
        a[2030] = a[2030] * 3.6e-9
    else:
        a.loc[a['model'] == PeriodName, 'model'] = str(X4)
        a.loc[a['scenario'] == ScenarioName, 'scenario'] = X5 + '|' + ScenarioName
        for k in dfGeneration.index:
            a.loc[a['region']   == k, 'region']   = dfGeneration['Node'][k]
            a.loc[a['variable'] == k, 'variable'] = var_PowerGeneration.loc[X0]['Variable'] + '|' + dfGeneration['Technology'][k]
        for k in NodeName:
            a.loc[a['region'] == k, 'region'] = dfNodeToZone['Zone'][k]

    a['subannual'] = a['subannual'].str[:11]
    # a['subannual'] = a['subannual'].str[5:]
    a['subannual'] = (str(PeriodName)+'-'+a['subannual'] + '+01:00')
    # a['time'] = pd.to_datetime(a['time'], utc=True)
    a['subannual'] = pd.to_datetime(a['subannual'])
    a['subannual'] = a['subannual'].dt.strftime("%m-%d %H:%M+01:00")
    return a

#%% Function Type 2
def Converter_Type2(X1):
    NodeName = dfDemand.columns
    if X1 == 'VariableCost':
        X1 = 'LinearTerm'
    if var_PowerGeneration.loc[X1]['idx'] == 0:
        # Selecting Columns
        a = pGeneration0[['Model', 'Scenario', 'Node', 'Variable', 'Unit', 'Subannual', X1]]
        # Changing column names
        a = a.rename(columns={"Model": "model", "Scenario": "scenario", "Node": "region", "Variable": "variable", "Unit": "unit", "Subannual": "subannual", X1: 2030})
        # Changing Values in Model and Scenario columns
        a.loc[a['variable'] == ScenarioName, 'variable'] = var_PowerGeneration.loc[X1]['Variable'] + '|' + pGeneration0['Technology']
    elif var_PowerGeneration.loc[X1]['idx'] == 1:
        # Selecting Columns
        a = pGeneration1[['Model', 'Scenario', 'Node', 'Variable', 'Unit', 'Subannual', X1]]
        # Changing column names
        a = a.rename(columns={"Model": "model", "Scenario": "scenario", "Node": "region", "Variable": "variable", "Unit": "unit", "Subannual": "subannual", X1: 2030})
        a.loc[a['variable'] == ScenarioName, 'variable'] = var_PowerGeneration.loc[X1]['Variable'] + '|' + pGeneration1['Technology']
    a.loc[a['unit'] == ScenarioName, 'unit'] = var_PowerGeneration.loc[X1]['Unit']
    for i in NodeName:
        a.loc[a['region'] == i, 'region'] = dfNodeToZone['Zone'][i]
    a = a[['model', 'scenario', 'region', 'variable', 'unit', 2030]]

    return a

#%% Function Type 3
def Converter_Type3(X1):
    # Selecting Columns
    a = pNetwork[['Model', 'Scenario', 'Region', 'Variable', 'Unit', 'Subannual', X1]]
    # Changing column names
    a = a.rename(columns={"Model": "model", "Scenario": "scenario", "Region": "region", "Variable": "variable", "Unit": "unit", "Subannual": "subannual", X1: 2030})
    # Changing Values in Model and Scenario columns
    a.loc[a['variable'] == ScenarioName, 'variable'] = var_PowerTransmission.loc[X1]['Variable']
    a.loc[a['unit'] == ScenarioName, 'unit'] = var_PowerTransmission.loc[X1]['Unit']
    a = a[['model', 'scenario', 'region', 'variable', 'unit', 2030]]

    return a
#%% Power Demand - Dataframe

InputDemand                                                         = Converter_Type1('PowerDemand', var_PowerSystem, dfDemand, ModelName, CaseName,0)

PowerDemandDataTime = time.time() - StartTime
StartTime           = time.time()
print('PowerDemand       input data                ... ', round(PowerDemandDataTime), 's')
InputDemand.to_csv(f'{Folder}/oT_IAMC_PowerDemand_'f'{ModelName}_{CaseName}.csv', index=False, sep=',')
print('Transforming PowerDemand data         status: OK')

PowerSystemDataTime = time.time() - StartTime
StartTime           = time.time()
print('PowerSystem       input data                ... ', round(PowerSystemDataTime), 's')

#%% Power Generation - Main Dataframe
ScenarioName = InputDemand['scenario'][0]
PeriodName   = InputDemand.columns[6]
# Changing indexes
pGeneration0                                                        = dfGeneration.reset_index()
pGeneration0                                                        = pGeneration0.assign(Model    = ModelName)
pGeneration0                                                        = pGeneration0.assign(Scenario = ScenarioName)
pGeneration0                                                        = pGeneration0.assign(Variable = ScenarioName)
pGeneration0                                                        = pGeneration0.assign(Unit     = ScenarioName)
pGeneration0                                                        = pGeneration0.assign(Subannual= '')

pGeneration1                                                        = dfGeneration.reset_index()
array = ['Hydro_Reservoir', 'Hydro_Pumped Storage', 'Hydrogen', 'Battery']
pGeneration1                                                        = pGeneration1.loc[pGeneration1['Technology'].isin(array)]
pGeneration1                                                        = pGeneration1.assign(Model    = ModelName)
pGeneration1                                                        = pGeneration1.assign(Scenario = ScenarioName)
pGeneration1                                                        = pGeneration1.assign(Variable = ScenarioName)
pGeneration1                                                        = pGeneration1.assign(Unit     = ScenarioName)
pGeneration1                                                        = pGeneration1.assign(Subannual= '')

pGeneration2                                                        = dfGeneration.reset_index()
array = ['Solar_PV', 'Wind_Offshore', 'Wind_Onshore']
pGeneration2                                                        = pGeneration2.loc[pGeneration2['Technology'].isin(array)]
pGeneration2                                                        = pGeneration2.assign(Model    = ModelName)
pGeneration2                                                        = pGeneration2.assign(Scenario = ScenarioName)
pGeneration2                                                        = pGeneration2.assign(Variable = ScenarioName)
pGeneration2                                                        = pGeneration2.assign(Unit     = ScenarioName)
pGeneration2                                                        = pGeneration2.assign(Subannual= '')

pGeneration3                                                        = dfGeneration.reset_index()
array = ['Hydro_Run of River']
pGeneration3                                                        = pGeneration3.loc[pGeneration3['Technology'].isin(array)]
pGeneration3                                                        = pGeneration3.assign(Model    = ModelName)
pGeneration3                                                        = pGeneration3.assign(Scenario = ScenarioName)
pGeneration3                                                        = pGeneration3.assign(Variable = ScenarioName)
pGeneration3                                                        = pGeneration3.assign(Unit     = ScenarioName)
pGeneration3                                                        = pGeneration3.assign(Subannual= '')

#%% Storing PowerGeneration data - Dataframe
# InputStorageType                                                   = Converter_Type2('StorageType')
InputMaximumPower                                                  = Converter_Type2('MaximumPower')
# InputMinimumPower                                                  = Converter_Type2('MinimumPower')
InputMaximumCharge                                                 = Converter_Type2('MaximumCharge')
InputInitialStorage                                                = Converter_Type2('InitialStorage')
InputMaxStorageCapacity                                            = Converter_Type2('MaximumStorage')
InputMinStorageCapacity                                            = Converter_Type2('MinimumStorage')
InputEfficiency                                                    = Converter_Type2('Efficiency')
InputRampUp                                                        = Converter_Type2('RampUp')
InputRampDown                                                      = Converter_Type2('RampDown')
InputUpTime                                                        = Converter_Type2('UpTime')
InputDownTime                                                      = Converter_Type2('DownTime')
InputFuelCost                                                      = Converter_Type2('FuelCost')
InputLinearVarCost                                                 = Converter_Type2('LinearTerm')
InputConstantVarCost                                               = Converter_Type2('ConstantTerm')
InputOMVarCost                                                     = Converter_Type2('OMVariableCost')
InputStartUpCost                                                   = Converter_Type2('StartUpCost')
InputShutDownCost                                                  = Converter_Type2('ShutDownCost')
InputCO2EmissionRate                                               = Converter_Type2('CO2EmissionRate')
# InputFixedCost                                                     = Converter_Type2('FixedCost')
# InputFixedChargeRate                                               = Converter_Type2('FixedChargeRate')
# InputBinaryInvestment                                              = Converter_Type2('BinaryInvestment')
InputVariableCost                                                  = Converter_Type2('VariableCost')

PowerGenerationDataTime   = time.time() - StartTime
StartTime                 = time.time()
print('PowerGeneration   input data                ... ', round(PowerGenerationDataTime), 's')
print('Transforming PowerGeneration data     status: OK')

#%% Power Network - Main Dataframe
# Changing indexes
pNetwork                                                           = dfNetwork.reset_index()
NodeName = dfDemand.columns
for i in NodeName:
    pNetwork.loc[pNetwork['InitialNode'] == i, 'InitialNode'] = dfNodeToZone['Zone'][i]
    pNetwork.loc[pNetwork['FinalNode'  ] == i, 'FinalNode'  ] = dfNodeToZone['Zone'][i]
pNetwork                                                      = pNetwork.assign(Model    = ModelName)
pNetwork                                                      = pNetwork.assign(Scenario = ScenarioName)
pNetwork                                                      = pNetwork.assign(Region   = pNetwork['InitialNode']+'>'+pNetwork['FinalNode'])
pNetwork                                                      = pNetwork.assign(Variable = ScenarioName)
pNetwork                                                      = pNetwork.assign(Unit     = ScenarioName)
pNetwork                                                      = pNetwork.assign(Subannual= '')

#%% Storing PowerTransmission data - Dataframe
# InputLineType                                                      = Converter_Type3('LineType')
# InputVoltage                                                       = Converter_Type3('Voltage')
InputLossFactor                                                    = Converter_Type3('LossFactor')
InputReactance                                                     = Converter_Type3('Reactance')
InputTTC                                                           = Converter_Type3('TTC')
# InputTTCBck                                                        = Converter_Type3('TTCBck')
InputSecurityFactor                                                = Converter_Type3('SecurityFactor')
# InputFxCost                                                        = Converter_Type3('FixedCost')
# InputFxChargeRate                                                  = Converter_Type3('FixedChargeRate')
# InputInvestment                                                    = Converter_Type3('BinaryInvestment')

InputVariableCost[2030] = InputFuelCost[2030] * InputLinearVarCost[2030]
InputVariableCost['unit'] = var_PowerGeneration.loc['VariableCost']['Unit']

InputEfficiency      = InputEfficiency.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
InputVariableCost    = InputVariableCost.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
InputConstantVarCost = InputConstantVarCost.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
InputOMVarCost       = InputOMVarCost.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
# InputLossFactor.fillna              ("", inplace=True)
# InputReactance.fillna              ("", inplace=True)
# InputSecurityFactor.fillna              ("", inplace=True)
#%% Merging Dataframes
gen_frames = [
          # InputStorageType.sort_values(by ='Variable' ),
          InputMaximumPower.sort_values(by ='variable' ),
          # InputMinimumPower.sort_values(by ='Variable' ),
          # InputMaximumCharge.sort_values(by ='Variable' ),
          # InputInitialStorage.sort_values(by ='Variable' ),
          InputMaxStorageCapacity.sort_values(by ='variable' ),
          InputMinStorageCapacity.sort_values(by ='variable' ),
          InputEfficiency.sort_values(by ='variable' ),
          # InputRampUp.sort_values(by ='variable' ),
          # InputRampDown.sort_values(by ='variable' ),
          # InputUpTime.sort_values(by ='variable' ),
          # InputDownTime.sort_values(by ='variable' ),
          # InputFuelCost.sort_values(by ='Variable' ),
          # InputLinearVarCost.sort_values(by ='Variable' ),
          InputVariableCost.sort_values(by = 'variable'),
          InputConstantVarCost.sort_values(by ='variable' ),
          InputOMVarCost.sort_values(by ='variable' ),
          # InputStartUpCost.sort_values(by ='variable' ),
          # InputShutDownCost.sort_values(by ='variable' ),
    ]

InputGen = pd.concat(gen_frames)
#%% Saving final CSV
InputGen = InputGen.replace({'variable': {'_': '|'}}, regex=True)
InputGen = InputGen.groupby(by=["model", "scenario", "region", "variable", "unit"]).sum().reset_index().sort_values(by = ["variable", "region"])
InputGen.to_csv(f'{Folder}/oT_IAMC_PowerGeneration_'f'{ModelName}_{CaseName}.csv', index=False, sep=',')
# result.to_excel(pd.ExcelWriter('oT_IAMC_'f'{ModelName}_'f'{CaseName}.xlsx'), index=False)
PowerTransmissionDataTime = time.time() - StartTime
StartTime                 = time.time()
print('PowerGeneration   input data                ... ', round(PowerTransmissionDataTime), 's')

InputLossFactor = InputLossFactor.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
InputReactance = InputReactance.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])
InputSecurityFactor = InputSecurityFactor.groupby(by=["model", "scenario", "region", "variable", "unit"]).mean().reset_index().sort_values(by = ["variable", "region"])

trans_frames = [
          InputLossFactor.sort_values(by ='region' ),
          InputReactance.sort_values(by ='region' ),
          InputTTC.sort_values(by ='region' ),
          InputSecurityFactor.sort_values(by ='region' )
    ]

InputTran = pd.concat(trans_frames)
InputTran = InputTran.replace({'variable': {'_': '|'}}, regex=True)
InputTran = InputTran.groupby(by=["model", "scenario", "region", "variable", "unit"]).sum().reset_index().sort_values(by = ["variable", "region"])
InputTran.to_csv(f'{Folder}/oT_IAMC_PowerTransmission_'f'{ModelName}_{CaseName}.csv', index=False, sep=',')
# result.to_excel(pd.ExcelWriter('oT_IAMC_'f'{ModelName}_{CaseName}'.xlsx'), index=False)
PowerTransmissionDataTime = time.time() - StartTime
StartTime                 = time.time()
print('PowerTransmission input data                ... ', round(PowerTransmissionDataTime), 's')

# Dictionary of DataFrames and their corresponding sheet names
dataframes = {
    'PowerDemand': InputDemand,
    'PowerGeneration': InputGen,
    'PowerTransmission': InputTran
}

# Save DataFrames to an Excel file
output_path = os.path.join(DirName, Folder, 'oT_IAMC_'f'{ModelName}_{CaseName}.xlsx')

with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
    for sheet_name, df in dataframes.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"DataFrames have been saved to {output_path}")

print('Saving openTEPES data                 status: OK')
