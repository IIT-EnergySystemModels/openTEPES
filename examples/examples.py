"""Libraries."""

import os

import time

from pyomo.environ import ConcreteModel

import open_tepes.openTEPES_InputData as openTEPES_InputData


CWD = os.getcwd()
TEST_PATH = CWD + '/open_tepes'
os.chdir(TEST_PATH)

START_TIME = time.time()

CASE_NAME = '9n'

# model declaration
M_TEPES = ConcreteModel()

# from .openTEPES import run_openTEPES
openTEPES_InputData.InputData(CASE_NAME, M_TEPES)

TOTAL_TIME = time.time() - START_TIME
print('Total time                            ... ', round(TOTAL_TIME), 's')
