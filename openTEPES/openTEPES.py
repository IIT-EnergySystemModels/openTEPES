import time
import setuptools

from   pyomo.environ import ConcreteModel

from openTEPES_InputData        import InputData
from openTEPES_ModelFormulation import ModelFormulation
from openTEPES_ProblemSolving   import ProblemSolving
from openTEPES_OutputResults    import OutputResults

InitialTime = time.time()

CaseName   = '9n'
SolverName = 'gurobi'

#%% model declaration
mTEPES = ConcreteModel('Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.24 - November 30, 2020')

InputData(CaseName, mTEPES)

ModelFormulation(mTEPES)

mTEPES.write(CaseName+'/openTEPES_'+CaseName+'.lp', io_options={'symbolic_solver_labels': True})  # create lp-format file

StartTime = time.time()
WritingLPFileTime = time.time() - StartTime
StartTime = time.time()
print('Writing LP file                       ... ', round(WritingLPFileTime), 's')

ProblemSolving(CaseName, SolverName, mTEPES)

OutputResults(CaseName, mTEPES)

TotalTime = time.time() - InitialTime
print('Total time                            ... ', round(TotalTime), 's')
