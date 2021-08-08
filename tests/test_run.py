import os
import openTEPES.openTEPES as oT


CWD = os.getcwd()
TEST_PATH = CWD + '/openTEPES'
os.chdir(TEST_PATH)

CASE = "9n"
DIR = TEST_PATH
SOLVER = "gurobi"

oT.openTEPES_run(DIR, CASE, SOLVER)
