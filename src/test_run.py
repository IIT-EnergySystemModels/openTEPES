#%% libraries
import os
import time
import setuptools

from   pyomo.environ import ConcreteModel
from openTEPES import InputData
CWD = os.getcwd()
Test_Path = CWD + '/src/openTEPES'
os.chdir(Test_Path)

StartTime = time.time()

CaseName = '9n'

#%% model declaration
mTEPES = ConcreteModel('Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.15 - September 4, 2020')

# InputData(CaseName, mTEPES)

TotalTime = time.time() - StartTime
print('Total time                            ... ', round(TotalTime), 's')