Change Log
=============

- [CHANGED] Addition of the sequence of decisions and operation (TEP + transmission switching)
- [FIXED] fixing `<https://pascua.iit.comillas.edu/aramos/openTEPES/index.html#>`_ in README.rst 

[3.1.4] - 2021-09-30
--------------------
- [FIXED] fix initialization of synchronous condenser and shunt candidate

[3.1.3] - 2021-09-10
--------------------
- [FIXED] fix in some equations the activation of the operating reserves

[3.1.2] - 2021-07-12
--------------------
- [FIXED] fix typo in network investment constraint to include candidate lines

[3.1.1] - 2021-07-08
--------------------
- [FIXED] change location of lea and lca computation

[3.1.0] - 2021-07-07
--------------------
- [CHANGED] definition of switching stages with dict and data files to allow less granularity in switching decisions

[2.6.5] - 2021-07-04
--------------------
- [FIXED] typos in line switching equations and redefinition of lea and lca sets

[2.6.4] - 2021-06-23
--------------------
- [FIXED] typo in equation formulating the total output of a unit
- [CHANGED] introduce binary commitment option for each unit
- [CHANGED] introduce adequacy reserve margin for each area
- [CHANGED] introduce availability for each unit

[2.6.3] - 2021-06-20
--------------------
- [FIXED] typo in investment constraint in model formulation

[2.6.2] - 2021-06-18
--------------------
- [CHANGED] updated for pyomo 6.0
- [CHANGED] if not defined length computed as geographical distance

[2.6.1] - 2021-06-14
--------------------
- [CHANGED] line length added in network input file
- [FIXED] error in output results due to stage weight

[2.6.0] - 2021-05-27
--------------------
- [CHANGED] new inertia constraint for each area
- [FIXED] change column BinarySwitching by Switching in network data meaning that line is able to switch or not

[2.5.3] - 2021-05-14
--------------------
- [FIXED] fix output results of storage utilization

[2.5.2] - 2021-05-11
--------------------
- [CHANGED] new ESS inventory utilization result file
- [FIXED] protection against stage with no load levels

[2.5.1] - 2021-05-07
--------------------
- [FIXED] introduction of stage weight in the operation variable cost

[2.5.0] - 2021-04-29
--------------------
- [CHANGED] generalize the definition of stages to allow using representative stages (weeks, days, etc.)

[2.4.2] - 2021-04-29
--------------------
- [CHANGED] initialize shutdown variable
- [FIXED] fix error in conditions to formulate the relationship between UC, startup and shutdown

[2.4.1] - 2021-04-28
--------------------
- [CHANGED] very small parameters -> 0 depending on the area
- [CHANGED] avoid use of list if not needed

[2.4.0] - 2021-04-24
--------------------
- [CHANGED] new input files VariableMaxConsumption and VariableMinConsumption and MininmumCharge column in Generation file
- [CHANGED] change names of MaximumStorage (MinimumStorage) files to VariableMaxStorage (VariableMinStorage)

[2.3.1] - 2021-04-23
--------------------
- [CHANGED] avoid superfluous equations

[2.3.0] - 2021-04-20
--------------------
- [CHANGED] separate model data and optimization model

[2.2.5] - 2021-04-18
--------------------
- [FIXED] fix commitment, startup and shutdown decisions of hydro units
- [FIXED] output results of storage units
- [FIXED] detection of storage units

[2.2.4] - 2021-04-10
--------------------
- [FIXED] fix line switch off constraint

[2.2.3] - 2021-04-07
--------------------
- [FIXED] determine the commitment and output of generating units at the beginning of each stage

[2.2.2] - 2021-04-05
--------------------
- [CHANGED] remove a warning in InputData

[2.2.1] - 2021-04-03
--------------------
- [CHANGED] added three new output files for line commitment, switch on and off
- [CHANGED] added three four output files for ESS energy outflows
- [FIXED]   fix writing flexibility files for ESS

[2.2.0] - 2021-03-31
--------------------
- [CHANGED] introduction of Power-to-X in ESS. Modifies the Generation file and introduces a new EnergyOutflows file
- [CHANGED] introduction of switching decision for transmission lines. Modifies the Option file and introduces a new column BinarySwitching in Network file

[2.1.0] - 2021-03-18
--------------------
- [CHANGED] using README.rst instead of README.md
- [CHANGED] split openTEPES_ModelFormulation.py in multiple functions related to investment and operating constraints
- [CHANGED] split openTEPES_OutputResults.py in multiple functions related to investment and operating variables

[2.0.24] - 2021-03-08
---------------------

- [FIXED] changed location of the shell openTEPES to sub folder openTEPES with all modules
- [FIXED] updated _init_.py

[2.0.23] - 2021-03-08
---------------------

- [CHANGED] included metadata in pyproject.toml and also requirements  (only pyomo, matplotlib, numpy, pandas, and psutil.)
- [CHANGED] created a README.md file
