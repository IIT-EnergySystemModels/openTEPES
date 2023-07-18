import numpy              as np
import pandas        as pd
import time          # count clock time

StartTime = time.time()
ModelName = 'openTEPES'
CaseName  = '9n'                              # To select the case

#%%                    IAMC -> openTEPES: Process
#                      1) Loading dictionary
#                      2) Reading data
#                      3) Power Demand data transformation
#                      4) Power Generation data transformation
#                      5) Power System data transformation
#                      6) Power Transmission data transformation
#                      7) Writing CSV

var_PowerSystem          = pd.read_csv('oT_IAMC_var_ID_PowerSystem.csv', index_col=[0    ])

var_PowerTransmission    = pd.read_csv('oT_IAMC_var_ID_PowerTransmission.csv', index_col=[0    ])

var_PowerGeneration      = pd.read_csv('oT_IAMC_var_ID_PowerGeneration.csv', index_col=[0    ])

var_GenDict              = pd.read_csv('oT_GenDict.csv', index_col=[0    ])

var_PowerGeneration.fillna(0, inplace=True)

print('Dictionary                            status: OK')
#%% Loading the IAMC file
dfHeads                  = pd.read_csv('oT_IAMC_openTEPES_'            +CaseName+'.csv', header=None, nrows=1)
dfBulk                   = pd.read_csv('oT_IAMC_openTEPES_'            +CaseName+'.csv')


# ModelName                = dfBulk['Model'].unique()[0]
ScenarioName             = dfBulk['Scenario'].unique()
# CaseName                 = pd.DataFrame(ScenarioName)[0].str.split('|', expand = True)[0][0]
VariableName             = dfBulk['Variable'].unique()
VariableName             = pd.DataFrame(VariableName)
VariableName             = VariableName[0].str.split('|', expand = True)
GenerationName           = VariableName.dropna()
PowerTechnologyName      = pd.DataFrame(GenerationName[len(GenerationName.columns)-2].unique()).dropna()
PowerPlantName           = pd.DataFrame(GenerationName[len(GenerationName.columns)-1].unique()).dropna()

ReadingDataTime          = time.time() - StartTime
StartTime                = time.time()
print('Reading                        input data   ... ', round(ReadingDataTime), 's')

def Converter_Type1(X0,X1,X2,X3,X4,X5):
    dfVariable               = X0[X0.Variable == X1].assign(Period     = X2)
    dfVariable               = dfVariable[[X3, 'Period', X4, X5, X2]]      #Colums: Scenario, Period, Subannual, Region, y2030
    index                    = dfVariable[X3].str.split('|', expand=True)
    index                    = index[len(index.columns) - 1]
    dfVariable[X3]           = index
    return dfVariable

def Converter_Type2(X0,X1,X2,X3,X4):
    data = pd.DataFrame(columns=X0.columns)
    for i in X1.index:
        Variable             = X2 + '|' + X1['Technology'][i] + '|' + i
        data0                = X0[X0.Variable == Variable]
        data                 = data.append(data0, ignore_index = True)
    index                 = data['Variable'].str.split('|', expand = True)
    index                 = index[len(index.columns)-1]
    data['index']         = index
    data                  = data.set_index('index')[[X3]].rename(columns={X3: X4})
    return data

def Converter_Type3(X0,X1,X2,X3,X4,X5,X6):
    data = pd.DataFrame(columns=X0.columns)
    for i in X1.index:
        Variable             = X2 + '|' + X1['Technology'][i] + '|' + i
        data0                = X0[X0.Variable == Variable]
        data                 = data.append(data0, ignore_index = True)
    index                 = data['Variable'].str.split('|', expand = True)
    index                 = index[len(index.columns)-1]
    data['index']         = index
    data                  = data.assign(Period     = X3)
    data                  = data[[X4, 'Period', X5, 'index', X3]]      #Colums: Scenario, Period, Subannual, Region, y2030
    index                 = data[X4].str.split('|', expand=True)
    index                 = index[len(index.columns) - 1]
    data[X4]              = index
    return data

def Converter_Type4(X0,X1,X2,X3,X4,X5):
    dfVariable               = X0[X0.Variable == X1].assign(Period     = X2)
    dfVariable               = dfVariable[[X3, 'Period', X4, X2]].rename(columns={X2: X5})      #Colums: Scenario, Period, Subannual, Region, y2030
    index                    = dfVariable[X3].str.split('|', expand=True)
    index                    = index[len(index.columns) - 1]
    dfVariable[X3]           = index
    return dfVariable

def Converter_Type5(X0,X1):
    a = X0[X0.Variable == X1].reset_index()
    a['From'] = NFrom
    a['To'] = NTo
    a['Circuit'] = circuits[1]
    a = a.set_index(['From', 'To', 'Circuit'])
    a = a['y2030'].rename_axis([None, None, None], axis=0)
    return a
#%%oT_Data_Demand
pDemand                  = Converter_Type1(dfBulk, 'Final Energy|Electricity|Profile', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], dfHeads[2][0])
pd.pivot_table(pDemand, values=dfHeads[6][0], index=[dfHeads[1][0], 'Period', dfHeads[5][0]], columns=[dfHeads[2][0]], aggfunc=np.sum).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1).to_csv('oT_Data_Demand_TEST_'+CaseName+'.csv', sep=',')

PowerDemandDataTime      = time.time() - StartTime
StartTime                = time.time()
print('oT_Data_Demand                 input data   ... ', round(PowerDemandDataTime), 's')
print('Transforming PowerDemand      data   status: OK')


#%%oT_Data_Generation
pStorageType             = Converter_Type2(dfBulk, var_GenDict, 'Storage Type|Electricity|Hydro|Reservoir', dfHeads[6][0], 'StorageType')
pBlank                   = pd.DataFrame(index= pStorageType.index, columns=pStorageType.columns).rename(columns={'StorageType': 'MustRun'}).fillna(0, inplace=True)
pMustRun                 = pBlank
pMaxPower                = Converter_Type2(dfBulk, var_GenDict, 'Maximum Active power|Electricity', dfHeads[6][0], 'MaxPower')
pMinPower                = Converter_Type2(dfBulk, var_GenDict, 'Minimum Active power|Electricity', dfHeads[6][0], 'MinPower')
pMaxCharge               = Converter_Type2(dfBulk, var_GenDict, 'Maximum Charge|Electricity|Energy Storage System', dfHeads[6][0], 'MaxCharge')
pInitialStorage          = Converter_Type2(dfBulk, var_GenDict, 'Initial Storage Level|Electricity|Energy Storage System', dfHeads[6][0], 'InitialStorage')
pMaxStorageCapacity      = Converter_Type2(dfBulk, var_GenDict, 'Maximum Storage|Electricity|Energy Storage System', dfHeads[6][0], 'MaxStorageCapacity')
pMinStorageCapacity      = Converter_Type2(dfBulk, var_GenDict, 'Minimum Storage|Electricity|Energy Storage System', dfHeads[6][0], 'MinStorageCapacity')
pEfficiency              = Converter_Type2(dfBulk, var_GenDict, 'Pumping Efficiency|Electricity|Hydro|Reservoir', dfHeads[6][0], 'Efficiency')
pRampUp                  = Converter_Type2(dfBulk, var_GenDict, 'Maximum Ramping|Upwards|Electricity', dfHeads[6][0], 'RampUp')
pRampDown                = Converter_Type2(dfBulk, var_GenDict, 'Maximum Ramping|Downwards|Electricity', dfHeads[6][0], 'RampDown')
pUpTime                  = Converter_Type2(dfBulk, var_GenDict, 'Minimum On Time|Electricity', dfHeads[6][0], 'UpTime')
pDownTime                = Converter_Type2(dfBulk, var_GenDict, 'Minimum Off Time|Electricity', dfHeads[6][0], 'DownTime')
pFuelCost                = Converter_Type2(dfBulk, var_GenDict, 'Price|Primary Energy', dfHeads[6][0], 'FuelCost')
pLinearVarCost           = Converter_Type2(dfBulk, var_GenDict, 'Linear Var Cost|Electricity', dfHeads[6][0], 'LinearVarCost')
pConstantVarCost         = Converter_Type2(dfBulk, var_GenDict, 'Constant Var Cost|Electricity', dfHeads[6][0], 'ConstantVarCost')
pOMVarCost               = Converter_Type2(dfBulk, var_GenDict, 'Operation and Maintenance Cost|Electricity', dfHeads[6][0], 'OMVarCost')
pStartUpCost             = Converter_Type2(dfBulk, var_GenDict, 'Start-Up Cost|Electricity', dfHeads[6][0], 'StartUpCost')
pShutDownCost            = Converter_Type2(dfBulk, var_GenDict, 'Shut-Down Cost|Electricity', dfHeads[6][0], 'ShutDownCost')
pCO2EmissionRate         = Converter_Type2(dfBulk, var_GenDict, 'Emissions|CO2|Electricity', dfHeads[6][0], 'CO2EmissionRate')
pFixedCost               = Converter_Type2(dfBulk, var_GenDict, 'FixedCost', dfHeads[6][0], 'FixedCost')
pFixedChargeRate         = Converter_Type2(dfBulk, var_GenDict, 'FixedChargeRate', dfHeads[6][0], 'FixedChargeRate')
pBinaryInvestment        = Converter_Type2(dfBulk, var_GenDict, 'Binary Investment|Electricity|Generation', dfHeads[6][0], 'BinaryInvestment')
#
dfVariable               = var_GenDict[['Node', 'Technology']]
# dfVariable               = dfVariable.assign(Variable = dfVariable['Technology']).rename(columns={'Variable': X4})
pGenData                 = pd.concat([dfVariable,
                                      pStorageType,
                                      pMustRun,
                                      pMaxPower,
                                      pMinPower,
                                      pMaxCharge,
                                      pInitialStorage,
                                      pMaxStorageCapacity,
                                      pMinStorageCapacity,
                                      pEfficiency,
                                      pRampUp,
                                      pRampDown,
                                      pUpTime,
                                      pDownTime,
                                      pFuelCost,
                                      pLinearVarCost,
                                      pConstantVarCost,
                                      pOMVarCost,
                                      pStartUpCost,
                                      pShutDownCost,
                                      pCO2EmissionRate,
                                      pFixedCost,
                                      pFixedChargeRate,
                                      pBinaryInvestment], axis=1)

pGenData.to_csv('oT_Data_Generation_TEST_'+CaseName+'.csv', sep=',')

GenerationDataTime = time.time() - StartTime
StartTime           = time.time()
print('oT_Data_Generation             input data   ... ', round(GenerationDataTime), 's')
print('Transforming Generation       data   status: OK')
#%%oT_Data_ESSEnergyInflows
pESSEnergyInflows        = Converter_Type3(dfBulk, var_GenDict, 'Dynamic Energy Inflows|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], dfHeads[2][0])
pd.pivot_table(pESSEnergyInflows, values=dfHeads[6][0], index=[dfHeads[1][0], 'Period', dfHeads[5][0]], columns=['index'], aggfunc=np.sum).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1).to_csv('oT_Data_ESSEnergyInflows_TEST_'+CaseName+'.csv', sep=',')
#
ESSEnergyInflowsDataTime = time.time() - StartTime
StartTime           = time.time()

print('oT_Data_ESSEnergyInflows       input data   ... ', round(ESSEnergyInflowsDataTime), 's')
print('Transforming ESSEnergyInflows data   status: OK')

#%%oT_Data_VariableMaxPower
pVariableMaxPower        = Converter_Type3(dfBulk, var_GenDict, 'Dynamic Maximum Power|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], dfHeads[2][0])
pd.pivot_table(pVariableMaxPower, values=dfHeads[6][0], index=[dfHeads[1][0], 'Period', dfHeads[5][0]], columns=['index'], aggfunc=np.sum).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1).to_csv('oT_Data_VariableGeneration_TEST_'+CaseName+'.csv', sep=',')
#
VariableMaxPowerDataTime = time.time() - StartTime
StartTime                = time.time()
print('oT_Data_VariableMaxPower       input data   ... ', round(VariableMaxPowerDataTime), 's')
print('Transforming VariableMaxPower data   status: OK')

#%%oT_Data_VariableMaxStorage
pVariableMaxStorage      = Converter_Type3(dfBulk, var_GenDict, 'Dynamic Maximum Storage|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], dfHeads[2][0])
pd.pivot_table(pVariableMaxStorage, values=dfHeads[6][0], index=[dfHeads[1][0], 'Period', dfHeads[5][0]], columns=['index'], aggfunc=np.sum).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1).to_csv('oT_Data_VariableMaxStorage_TEST_'+CaseName+'.csv', sep=',')
#
VariableMaxStorageDataTime = time.time() - StartTime
StartTime           = time.time()
print('oT_Data_VariableMaxStorage     input data   ... ', round(VariableMaxStorageDataTime), 's')
print('Transforming VariabMaxStorage data   status: OK')

#%%oT_Data_VariableMinStorage
pVariableMinStorage      = Converter_Type3(dfBulk, var_GenDict, 'Dynamic Minimum Storage|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], dfHeads[2][0])
pd.pivot_table(pVariableMinStorage, values=dfHeads[6][0], index=[dfHeads[1][0], 'Period', dfHeads[5][0]], columns=['index'], aggfunc=np.sum).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1).to_csv('oT_Data_VariableMinStorage_TEST_'+CaseName+'.csv', sep=',')
#
VariableMinStorageDataTime = time.time() - StartTime
StartTime           = time.time()
print('oT_Data_VariableMinStorage     input data   ... ', round(VariableMinStorageDataTime), 's')
print('Transforming VariabMinStorage data   status: OK')


#%%oT_Data_OperatingReserve
pOperatingReserveUp      = Converter_Type4(dfBulk, 'Operating Reserve Up|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], 'Up')
pOperatingReserveDown    = Converter_Type4(dfBulk, 'Operating Reserve Down|Electricity', dfHeads[6][0], dfHeads[1][0], dfHeads[5][0], 'Down')

pOperatingReserveUp      = pOperatingReserveUp.set_index(['Scenario','Period','Subannual']).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1)
pOperatingReserveDown    = pOperatingReserveDown.set_index(['Scenario','Period','Subannual']).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1)
pOperatingReserve        = pd.concat([pOperatingReserveUp, pOperatingReserveDown], axis=1)
pOperatingReserve.to_csv('oT_Data_OperatingReserve_TEST_'+CaseName+'.csv', sep=',')
#
OperatingReserveDataTime = time.time() - StartTime
StartTime                = time.time()
print('oT_Data_OperatingReserve       input data   ... ', round(OperatingReserveDataTime), 's')
print('Transforming OperatingReserve data   status: OK')

#%%oT_Data_Network

data                     = dfBulk[dfBulk.Variable == 'Line Type|Electricity|Transmission|Line']
index                    = data['Region'].str.split('|', expand = True)
circuits                 = index[1]
circuits                 = circuits.reset_index()
branches                 = index[0].str.split('>', expand = True)
branches                 = branches.reset_index()
NFrom                    = branches[0]
NTo                      = branches[1]
nodes                    = pd.unique(branches[[0, 1]].values.ravel('K'))

dfNetwork                = pd.DataFrame(index=[branches[0], branches[1], circuits[1]]).rename_axis([None, None, None], axis=0).rename_axis([None], axis = 1)

pLineType                = Converter_Type5(dfBulk, 'Line Type|Electricity|Transmission|Line')
pLossFactor              = Converter_Type5(dfBulk, 'Loss Factor|Electricity|Transmission|Line')
pReactance               = Converter_Type5(dfBulk, 'Reactance|Electricity|Transmission|Line')
pTTC                     = Converter_Type5(dfBulk, 'Maximum Flow|Electricity|Transmission|Line')
pSecurityFactor          = Converter_Type5(dfBulk, 'Security Factor|Electricity|Transmission|Line')
pFixedCost               = Converter_Type5(dfBulk, 'Investment|Electricity|Transmission|Line')
pFixedChargeRate         = Converter_Type5(dfBulk, 'Fixed Charge Rate|Electricity|Transmission|Line')
pBinaryInvestment        = Converter_Type5(dfBulk, 'Binary Investment|Electricity|Transmission|Line')

dfNetwork['LineType']    = pLineType
dfNetwork['LossFactor']  = pLossFactor
dfNetwork['Reactance']   = pReactance
dfNetwork['TTC']         = pTTC
dfNetwork['SecurityFactor']         = pSecurityFactor
dfNetwork['FixedCost']              = pFixedCost
dfNetwork['FixedChargeRate']        = pFixedChargeRate
dfNetwork['BinaryInvestment']       = pBinaryInvestment

dfNetwork.to_csv('oT_Data_Network_TEST_'+CaseName+'.csv', sep=',')

NetworkDataTime          = time.time() - StartTime
StartTime                = time.time()
print('oT_Data_Network                input data   ... ', round(NetworkDataTime), 's')
print('Transforming Network          data   status: OK')