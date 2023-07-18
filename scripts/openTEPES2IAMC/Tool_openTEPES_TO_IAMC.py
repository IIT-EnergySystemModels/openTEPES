import numpy              as np
import pandas        as pd
import time          # count clock time
import psutil        # access the number of CPUs
import pyomo.environ as pyo
from   pyomo.environ import Set, Var, Binary, NonNegativeReals, RealSet, Constraint, ConcreteModel, Objective, minimize, Suffix, DataPortal
from   pyomo.opt     import SolverFactory
from   collections   import defaultdict

StartTime = time.time()
ModelName = 'openTEPES'
CaseName  = 'SEP2030oE'                              # To select the case

#%%                    IAMC -> openTEPES: Process
#                      1) Loading dictionary
#                      2) Reading data
#                      3) Power Demand data transformation
#                      4) Power System data transformation
#                      4) Power Generation data transformation
#                      4) Power Transmission data transformation
#                      5) Writing data
#%% Loading the dictionary
var_PowerSystem        = pd.read_csv('oT_IAMC_var_ID_PowerSystem.csv', index_col=[0    ])

var_PowerTransmission  = pd.read_csv('oT_IAMC_var_ID_PowerTransmission.csv', index_col=[0    ])

var_PowerGeneration    = pd.read_csv('oT_IAMC_var_ID_PowerGeneration.csv', index_col=[0    ])

print('Dictionary                            status: OK')

#%% reading data from CSV
dfOption             = pd.read_csv(CaseName+'/oT_Data_Option_'                    +CaseName+'.csv', index_col=[0    ])
dfParameter          = pd.read_csv(CaseName+'/oT_Data_Parameter_'                 +CaseName+'.csv', index_col=[0    ])
dfDuration           = pd.read_csv(CaseName+'/oT_Data_Duration_'                  +CaseName+'.csv', index_col=[0]    )
dfScenario           = pd.read_csv(CaseName+'/oT_Data_Scenario_'                  +CaseName+'.csv', index_col=[0    ])
dfNodeLocation       = pd.read_csv(CaseName+'/oT_Data_NodeLocation_'              +CaseName+'.csv', index_col=[0    ])
dfDuration           = pd.read_csv(CaseName+'/oT_Data_Duration_'                  +CaseName+'.csv', index_col=[0    ])
dfDemand             = pd.read_csv(CaseName+'/oT_Data_Demand_'                    +CaseName+'.csv', index_col=[0,1,2])
dfDwOperatingReserve = pd.read_csv(CaseName+'/oT_Data_DownwardOperatingReserve_'  +CaseName+'.csv', index_col=[0,1,2])
dfUpOperatingReserve = pd.read_csv(CaseName+'/oT_Data_UpwardOperatingReserve_'    +CaseName+'.csv', index_col=[0,1,2])
dfGeneration         = pd.read_csv(CaseName+'/oT_Data_Generation_'                +CaseName+'.csv', index_col=[0    ])
dfVariableMaxPower   = pd.read_csv(CaseName+'/oT_Data_VariableGeneration_'        +CaseName+'.csv', index_col=[0,1,2])
dfVariableMinStorage = pd.read_csv(CaseName+'/oT_Data_MinimumStorage_'        +CaseName+'.csv', index_col=[0,1,2])
dfVariableMaxStorage = pd.read_csv(CaseName+'/oT_Data_MaximumStorage_'        +CaseName+'.csv', index_col=[0,1,2])
dfESSEnergyInflows   = pd.read_csv(CaseName+'/oT_Data_EnergyInflows_'          +CaseName+'.csv', index_col=[0,1,2])
dfNetwork            = pd.read_csv(CaseName+'/oT_Data_Network_'                   +CaseName+'.csv', index_col=[0,1,2])
dfNodeToZone         = pd.read_csv(CaseName+'/oT_Dict_NodeToZone_'                +CaseName+'.csv', index_col=[0 ])
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
dfVariableMinStorage.fillna  (0, inplace=True)
dfVariableMaxStorage.fillna  (0, inplace=True)
dfESSEnergyInflows.fillna    (0, inplace=True)
dfNetwork.fillna             (0, inplace=True)

ReadingDataTime = time.time() - StartTime
StartTime       = time.time()
print('Reading           input data                ... ', round(ReadingDataTime), 's')

#%% Function Type 1
def Converter_Type1(X0,X1,X2,X4,X5,X6):
    VariableType = X1['Variable'][X0]
    UnitType     = X1['Unit'][X0]
    NodesName    = dfDemand.columns
    # From multiple columns to one colums
    a = X2.stack()
    # To set index
    a.index.names = ['Scenario', 'Period', 'LoadLevel', 'Node']
    # To save csv for changing indexes
    a = a.reset_index()
    # Getting scenario and period names
    ScenarioName = a['Scenario'][0]
    PeriodName   = a['Period'][0]
    # Adding NUTS to Region
    for i in NodesName:
        # a.loc[a['Node']   == i, 'Node']   = dfNodeToZone['Zone'][i] + '|' + i
        # a.loc[a['Node'] == i, 'Node'] = dfNodeToZone['Zone'][i]
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
    a = a.rename(columns={"Scenario": "Model", "Period": "Scenario", "Node": "Region", "Variable": "Variable", "Unit": "Unit", "LoadLevel": "Subannual", 0: PeriodName})
    # Changing Values in Model and Scenario columns
    if X6 == 0:
        a.loc[a['Model']    == ScenarioName, 'Model']  = X4
        a.loc[a['Scenario'] == PeriodName, 'Scenario'] = X5 + '|' + ScenarioName
    else:
        a.loc[a['Model'] == ScenarioName, 'Model'] = X4
        a.loc[a['Scenario'] == PeriodName, 'Scenario'] = X5 + '|' + ScenarioName
        for i in dfGeneration.index:
            a.loc[a['Region']   == i, 'Region']   = dfGeneration['Node'][i]
            a.loc[a['Variable'] == i, 'Variable'] = var_PowerGeneration.loc[X0]['Variable'] + '|' + dfGeneration['Technology'][i] + '|' + i
        for i in NodesName:
            # a.loc[a['Region'] == i, 'Region'] = dfNodeToZone['Zone'][i] + '|' + i
            a.loc[a['Region'] == i, 'Region'] = i
    a['Subannual'] = pd.to_datetime(a['Subannual'])
    return a

#%% Function Type 2
def Converter_Type2(X1):
    NodesName = dfDemand.columns
    # Selecting Columns
    a = pGeneration[['Model', 'Scenario', 'Node', 'Variable', 'Unit', 'Subannual', X1]]
    # Changing column names
    a = a.rename(columns={"Model": "Model", "Scenario": "Scenario", "Node": "Region", "Variable": "Variable", "Unit": "Unit", "Subannual": "Subannual", X1: PeriodName})
    # Changing Values in Model and Scenario columns
    a.loc[a['Variable'] == ScenarioName, 'Variable'] = var_PowerGeneration.loc[X1]['Variable'] + '|' + pGeneration['Technology'] + '|' + pGeneration['index']
    a.loc[a['Unit'] == ScenarioName, 'Unit'] = var_PowerGeneration.loc[X1]['Unit']
    for i in NodesName:
        a.loc[a['Region'] == i, 'Region'] = dfNodeToZone['Zone'][i] + '|' + i

    return a

#%% Function Type 3
def Converter_Type3(X1):
    # Selecting Columns
    a = pNetwork[['Model', 'Scenario', 'Region', 'Variable', 'Unit', 'Subannual', X1]]
    # Changing column names
    a = a.rename(columns={"Model": "Model", "Scenario": "Scenario", "Region": "Region", "Variable": "Variable", "Unit": "Unit", "Subannual": "Subannual", X1: PeriodName})
    # Changing Values in Model and Scenario columns
    a.loc[a['Variable'] == ScenarioName, 'Variable'] = var_PowerTransmission.loc[X1]['Variable']
    a.loc[a['Unit'] == ScenarioName, 'Unit'] = var_PowerTransmission.loc[X1]['Unit']

    return a
#%% Power Demand - Dataframe

InputDemand                                                         = Converter_Type1('PowerDemand', var_PowerSystem, dfDemand, ModelName, CaseName,0)

PowerDemandDataTime = time.time() - StartTime
StartTime           = time.time()
print('PowerDemand       input data                ... ', round(PowerDemandDataTime), 's')
print('Transforming PowerDemand data         status: OK')

#%% Operating Reserve - Dataframe
# From multiple columns to one colums
# InputDwOperatingReserve                                              = dfDwOperatingReserve.rename(columns={"Up": var_PowerSystem.loc['OperatingReserveUp']['Variable'], "Down": var_PowerSystem.loc['OperatingReserveDown']['Variable']}).stack()
# InputDwOperatingReserve                                              = dfDwOperatingReserve.rename(columns={"Up": var_PowerSystem.loc['OperatingReserveUp']['Variable'], "Down": var_PowerSystem.loc['OperatingReserveDown']['Variable']}).stack()
InputDwOperatingReserve                                            = Converter_Type1('OperatingReserveDown', var_PowerSystem, dfDwOperatingReserve, ModelName, CaseName, 0)
InputUpOperatingReserve                                            = Converter_Type1('OperatingReserveUp', var_PowerSystem, dfUpOperatingReserve, ModelName, CaseName, 0)
# # To set index
# InputOperatingReserve.index.names                                  = ['Scenario','Period','LoadLevel','Variable']
# # Changing indexes
# InputOperatingReserve                                              = InputOperatingReserve.reset_index()
# Getting scenario and period names
ScenarioName                                                       = InputDwOperatingReserve['Scenario'][0]
PeriodName                                                         = InputDwOperatingReserve.columns[6]
# # Adding Variable and Unit columns
# InputOperatingReserve                                              = InputOperatingReserve.assign(Node = '')
# InputOperatingReserve                                              = InputOperatingReserve.assign(Unit = 'MW')
# # Reorder columns
# InputOperatingReserve                                              = InputOperatingReserve[['Scenario','Period','Node','Variable','Unit','LoadLevel',0]]
# # Changing column names
# InputOperatingReserve                                              = InputOperatingReserve.rename(columns={"Scenario": "Model", "Period": "Scenario", "Node": "Region", "Variable": "Variable", "Unit": "Unit","LoadLevel": "Subannual", 0: PeriodName})
# Changing Values in Model and Scenario columns
# InputOperatingReserve.loc[InputOperatingReserve['Model']           == ScenarioName, 'Model']  = ModelName
# InputOperatingReserve.loc[InputOperatingReserve['Scenario']        == PeriodName, 'Scenario'] = CaseName+'|'+ScenarioName
# InputOperatingReserve['Subannual']                                 = pd.to_datetime(InputOperatingReserve['Subannual'])

PowerSystemDataTime = time.time() - StartTime
StartTime           = time.time()
print('PowerSystem       input data                ... ', round(PowerSystemDataTime), 's')
print('Transforming PowerSystem data         status: OK')

#%% Power Generation - Main Dataframe
# Changing indexes
pGeneration                                                        = dfGeneration.reset_index()
pGeneration                                                        = pGeneration.assign(Model    = ModelName)
pGeneration                                                        = pGeneration.assign(Scenario = CaseName+'|'+ScenarioName)
pGeneration                                                        = pGeneration.assign(Variable = ScenarioName)
pGeneration                                                        = pGeneration.assign(Unit     = ScenarioName)
pGeneration                                                        = pGeneration.assign(Subannual= '')

#%% Storing PowerGeneration data - Dataframe
InputStorageType                                                   = Converter_Type2('StorageType')
InputMaximumPower                                                  = Converter_Type2('MaximumPower')
InputMinimumPower                                                  = Converter_Type2('MinimumPower')
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
InputFixedCost                                                     = Converter_Type2('FixedCost')
InputFixedChargeRate                                               = Converter_Type2('FixedChargeRate')
InputBinaryInvestment                                              = Converter_Type2('BinaryInvestment')

InputVariableMaxPower                                              = Converter_Type1('VariableMaxPower', var_PowerGeneration, dfVariableMaxPower, ModelName, CaseName,1)
InputVariableMaxStorage                                            = Converter_Type1('VariableMaxStorage', var_PowerGeneration, dfVariableMaxStorage, ModelName, CaseName,1)
InputVariableMinStorage                                            = Converter_Type1('VariableMinStorage', var_PowerGeneration, dfVariableMinStorage, ModelName, CaseName,1)
InputESSEnergyInflows                                              = Converter_Type1('ESSEnergyInflows', var_PowerGeneration, dfVariableMinStorage, ModelName, CaseName,1)


PowerGenerationDataTime   = time.time() - StartTime
StartTime                 = time.time()
print('PowerGeneration   input data                ... ', round(PowerGenerationDataTime), 's')
print('Transforming PowerGeneration data     status: OK')
#%% Power Generation - Main Dataframe
# Changing indexes
pNetwork                                                           = dfNetwork.reset_index()
pNetwork                                                           = pNetwork.assign(Model    = ModelName)
pNetwork                                                           = pNetwork.assign(Scenario = ScenarioName)
pNetwork                                                           = pNetwork.assign(Region   = pNetwork['level_0']+'>'+pNetwork['level_1']+'|'+pNetwork['level_2'])
pNetwork                                                           = pNetwork.assign(Variable = ScenarioName)
pNetwork                                                           = pNetwork.assign(Unit     = ScenarioName)
pNetwork                                                           = pNetwork.assign(Subannual= '')

#%% Storing PowerTransmission data - Dataframe
InputLineType                                                      = Converter_Type3('LineType')
InputVoltage                                                       = Converter_Type3('Voltage')
InputLossFactor                                                    = Converter_Type3('LossFactor')
InputReactance                                                     = Converter_Type3('Reactance')
InputTTC                                                           = Converter_Type3('TTC')
InputSecurityFactor                                                = Converter_Type3('SecurityFactor')
InputFxCost                                                        = Converter_Type3('FixedCost')
InputFxChargeRate                                                  = Converter_Type3('FixedChargeRate')
InputInvestment                                                    = Converter_Type3('BinaryInvestment')

PowerTransmissionDataTime = time.time() - StartTime
StartTime                 = time.time()
print('PowerTransmission input data                ... ', round(PowerTransmissionDataTime), 's')

#%% Merging Dataframes
frames = [
# frames = [InputDemand.sort_values(by =['Region', 'Subannual'] ),
          # InputDwOperatingReserve.sort_values(by =['Variable', 'Subannual'] ),
          # InputUpOperatingReserve.sort_values(by =['Variable', 'Subannual'] ),
          # InputStorageType.sort_values(by ='Variable' ),
          # InputMaximumPower.sort_values(by ='Variable' ),
          # InputMinimumPower.sort_values(by ='Variable' ),
          # InputMaximumCharge.sort_values(by ='Variable' ),
          # InputInitialStorage.sort_values(by ='Variable' ),
          # InputMaxStorageCapacity.sort_values(by ='Variable' ),
          # InputMinStorageCapacity.sort_values(by ='Variable' ),
          # InputEfficiency.sort_values(by ='Variable' ),
          # InputRampUp.sort_values(by ='Variable' ),
          # InputRampDown.sort_values(by ='Variable' ),
          # InputUpTime.sort_values(by ='Variable' ),
          # InputDownTime.sort_values(by ='Variable' ),
          # InputFuelCost.sort_values(by ='Variable' ),
          # InputLinearVarCost.sort_values(by ='Variable' ),
          # InputConstantVarCost.sort_values(by ='Variable' ),
          # InputOMVarCost.sort_values(by ='Variable' ),
          # InputStartUpCost.sort_values(by ='Variable' ),
          # InputShutDownCost.sort_values(by ='Variable' ),
          # InputCO2EmissionRate.sort_values(by ='Variable' ),
          # InputFixedCost.sort_values(by ='Variable' ),
          # InputFixedChargeRate.sort_values(by ='Variable' ),
          # InputBinaryInvestment.sort_values(by = 'Variable'),
          # InputVariableMaxPower.sort_values(by =['Variable', 'Subannual'] ),
          # InputVariableMaxStorage.sort_values(by =['Variable', 'Subannual'] ),
          # InputVariableMinStorage.sort_values(by =['Variable', 'Subannual'] ),
          # InputESSEnergyInflows.sort_values(by =['Variable', 'Subannual'] )]
          InputLineType.sort_values(by ='Region' ),
          # InputVoltage.sort_values(by ='Region' ),
          InputLossFactor.sort_values(by ='Region' ),
          InputReactance.sort_values(by ='Region' ),
          InputTTC.sort_values(by ='Region' ),
          InputSecurityFactor.sort_values(by ='Region' )]
          # InputFxCost.sort_values(by ='Region' ),
          # InputFxChargeRate.sort_values(by ='Region' )]
          # InputInvestment.sort_values(by ='Region' )]

result = pd.concat(frames)
#%% Saving final CSV
result.to_csv('oT_IAMC_'+ModelName+'_'+CaseName+'.csv', index=False, sep=',')

print('Saving openTEPES data                 status: OK')
