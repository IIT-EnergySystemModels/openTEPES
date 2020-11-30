"""Libraries."""

import os

import time

import openTEPES as oT

from pyomo.environ import ConcreteModel


CWD = os.getcwd()
TEST_PATH = CWD + '/openTEPES'
os.chdir(TEST_PATH)

START_TIME = time.time()

CASE_NAME = '9n'

# model declaration
M_TEPES = ConcreteModel()

# from .openTEPES import run_openTEPES
oT.InputData(CASE_NAME, M_TEPES)

TOTAL_TIME = time.time() - START_TIME
print('Total time                            ... ', round(TOTAL_TIME), 's')
