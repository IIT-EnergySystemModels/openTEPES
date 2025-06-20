.. openTEPES documentation master file, created by Andres Ramos

Questions & Answers (Q&A)
=========================

How can I install it?
---------------------
- openTEPES has been tested to be used in Microsoft Windows and Ubuntu (a Linux distribution)

- The installation documentation can be found at

   `https://opentepes.readthedocs.io/en/latest/Download.html <https://opentepes.readthedocs.io/en/latest/Download.html>`_

   `https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf <https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf>`_

- We recommend using these solvers

   `Gurobi <https://www.gurobi.com/products/gurobi-optimizer/>`_ because there is a license that is free of charge for academic usage

   `HiGHS <https://ergo-code.github.io/HiGHS/dev/installation/#Precompiled-Binaries>`_ as a free solver

   `GAMS/CPLEX <https://www.gams.com/>`_ for those institutions having the corresponding licenses

What PC do I need?
------------------
- openTEPES requirements depend on the case study

- The main dimensions to take care of are:

   Time (periods, load levels)

   Network (nodes, lines, transportation or DC power flow, ohmic losses)

   Stochasticity (scenarios)

   Binary investment decisions (generators, storage, transmission lines, etc.), operation decisions (commitment, startup, shutdown, etc.), mutual exclusivity

- As a rule of thumb, a linear optimization problem requires 1 GB of memory for every 1 million rows

- So, depending on the size of the optimization problem and the available memory, you may or may not be able to run it on your PC. As an example, the case studies provided can be run in a laptop with 32 GB of memory.

First steps
-----------
- openTEPES is provided with `seven case studies <https://opentepes.readthedocs.io/en/latest/Download.html#cases>`_. Each one has varied characteristics

- Check that you can run them on your PC. Some of them may not run if you have a PC with too little memory

Potential issues
----------------
- Check that any item you define (generator, node, technology, area, etc.) is included in the corresponding dictionary (``oT_Dict_Generation``, ``oT_Dict_Node``, ``oT_Dict_Technology``, ``oT_Dict_Area``, etc.). Otherwise, the optimization problem will not run

- openTEPES is implicitly a network model. Therefore, at least two nodes and one electrical transmission line connecting them must be defined

- At least one generator must be defined. A thermal generator has a larger than zero variable cost (the product of fuel cost times the linear term ≠ 0). A variable renewable energy unit has zero variable cost (the product of fuel cost times the linear term = 0)

- Check the correspondence between the resources you define for the system in the case study to be run and the nodes where they are deemed to be located. The location within the grid of any resource defined must be specified.

- Check that all the demand in the system within the case study is located in a node that can be served with the energy output of some resources located in any node that is connected/to be connected to the former, possibly including generation representing energy not served (ENS).  

Some tips
---------
On building an appropriate set of input data files for a case study that can be run on openTEPES:

- How can I strongly reduce the size of the case study for testing purposes

   Delete the duration (column D in ``oT_Data_Duration``) of the load levels you want to ignore. For example, if you delete the duration beyond the first 168 hours, you are considering just the first week of the year in the case study

   Put a time step of 2 or 3 hours in the ``oT_Data_Parameter`` file. This will reduce the number of load levels by 2 or 3

   For working with representative stages see, for example, the `9n7y case study <https://opentepes.readthedocs.io/en/latest/Download.html#cases>`_

- Relaxing the binary condition of binary variables

   In the ``oT_Data_Option`` file you can force or relax the binary condition of the binary variables.
   
   Besides, in ``oT_Data_Generation`` and ``oT_Data_Network`` they can also be relaxed individually for each generator or transmission line.

- How to ignore a scenario or a period

   Assign probability 0.0 to the scenario in ``oT_Data_Scenario`` or weight 0.0 to the period in ``oT_Data_Period``

- How to ignore a generator

   Don’t assign a node to it in ``oT_Data_Generation``, i.e., leave the node column empty

   Set the initial period where the generator can be in operation beyond the year of study in ``oT_Data_Generation``

- How to ignore a line

   Set the initial period where the line can be in operation beyond the year of study in ``oT_Data_Network``

- All the empty cells of the CSV files are substituted internally by openTEPES with 0.0

   Therefore, if you want to set the generation of a solar PV to 0.0 at night, then you must put a small value 0.000001 that will be substituted internally by openTEPES with 0.0. If the cell is left empty openTEPES will consider the rated capacity of the solar PV unit defined in ``oT_Data_Generation`` as the generation at night.

- There is no need to include the column for a certain resource within an input data file if there is not data to be defined for this resource within that file. Empty columns don’t need to be included in the input data CSV files, including ``oT_Data_VariableMaxGeneration``, ``oT_Data_VariableMinGeneration``, ``oT_Data_VariableMaxConsumption``, ``oT_Data_VariableMinConsumption``, etc.

On analysing output data:

- Make sure the problem solving process has been successfully completed, reaching optimality (console log and solver log file provide information on this).

- If the problem solving process has not produced an optimal solution, check if the system conditions defined within the input data files are too tight, i.e., the system may has not been provided with a large enough amount of flexibility for the model to find the optimal problem solution. If this may be the case, some problem constraints could/should be relaxed to allow the model to compute an optimal solution.

- Check the level of the overall system variables in the output energy balance files (e.g., ``oT_Result_BalanceEnergyPerArea``, ``oT_Result_BalanceEnergyPerTech``) to assess whether they seem to make sense. Focus first on certain specific variables, including the ones that follow:

   Non-served energy amounts

   Amounts of spilled and curtailed energy

   Overall output by technology if you have some reference levels for this to compare to

- Whenever the level of some variables at system level does not seem to be reasonable, check the output data file for the energy balance at area (country) level, to try to locate in which area within the system the problem may be located
