#%% libraries
import os
import time

from   pyomo.environ import ConcreteModel
import openTEPES as oT

CWD = os.getcwd()
Test_Path = CWD + '/src/openTEPES'
os.chdir(Test_Path)

StartTime = time.time()

CaseName = '9n'

#%% model declaration
mTEPES = ConcreteModel()

oT.InputData(CaseName, mTEPES)

TotalTime = time.time() - StartTime
print('Total time                            ... ', round(TotalTime), 's')