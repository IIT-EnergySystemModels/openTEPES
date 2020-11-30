"""Libraries."""

import os

import time

import openTEPES as oT
from pyomo.environ import ConcreteModel


CWD = os.getcwd()
Test_Path = CWD + '/openTEPES'
os.chdir(Test_Path)

StartTime = time.time()

CaseName = '9n'

# model declaration
mTEPES = ConcreteModel()

oT.InputData(CaseName, mTEPES)

TotalTime = time.time() - StartTime
print('Total time                            ... ', round(TotalTime), 's')
