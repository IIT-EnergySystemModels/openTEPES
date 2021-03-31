Change Log
=============

- [CHANGED] Addition of the sequence of decisions and operation (TEP + transmission switching)
- [FIXED] fixing `<https://pascua.iit.comillas.edu/aramos/openTEPES/index.html#>`_ in README.rst 

[2.2.0] - 2021-03-31
----------------------
- [CHANGED] introduction of Power-to-X in ESS. Modifies the Generation file and introduces a new EnergyOutflows file
- [CHANGED] introduction of switching decision for transmission lines

[2.1.0] - 2021-03-18
----------------------
- [CHANGED] using README.rst instead of README.md
- [CHANGED] split openTEPES_ModelFormulation.py in multiple functions related to investment and operating constraints
- [CHANGED] split openTEPES_OutputResults.py in multiple functions related to investment and operating variables

[2.0.24] - 2021-03-08
----------------------

- [FIXED] changed location of the shell openTEPES to sub folder openTEPES with all modules
- [FIXED] updated _init_.py

[2.0.23] - 2021-03-08
----------------------

- [CHANGED] included metadata in pyproject.toml and also requirements  (only pyomo, matplotlib, numpy, pandas, and psutil.)
- [CHANGED] created a README.md file
