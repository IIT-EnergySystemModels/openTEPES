Change Log
=============

- [CHANGED] Addition of the sequence of decisions and operation (TEP + transmission switching)
- [FIXED] fixing `<https://pascua.iit.comillas.edu/aramos/openTEPES/index.html#>`_ in README.rst 

[2.4.2] - 2021-04-29
--------------------
- [CHANGED] initialize shutdown variable
- [CHANGED] fix error in conditions to formulate the relationship between UC, startup and shutdown

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
