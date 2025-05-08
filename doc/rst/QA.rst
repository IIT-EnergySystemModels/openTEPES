.. openTEPES documentation master file, created by Andres Ramos

Questions & Answers
===================

How can I install it?
---------------------
- openTEPES has been tested to be used in Microsoft Windows and Ubuntu (a Linux distribution)

- The installation documentation can be found at

   `https://opentepes.readthedocs.io/en/latest/Download.html <https://opentepes.readthedocs.io/en/latest/Download.html>`_

   `https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf <https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf>`_

- We recommend using these solvers:

   Gurobi because there is a free license for academic institutions

   HiGHS as a free solver

   GAMS/CPLEX for those institutions having the corresponding license

What PC do I need?
------------------
- openTEPES requirements depend on the case study

- The main dimensions to take care of are:

   Time (periods, load levels)

   Network (nodes, lines, DC power flow)

   Stochasticity (scenarios)

   Binary investment decisions (generators, transmission lines, etc.)

- As a rule of thumb, an optimization problem needs 1 GB of memory for every 1 million rows

- So, depending on the size of the optimization problem and the available memory, you can run or not run it on your PC

First steps
-----------
- openTEPES is provided with seven case studies. Each one has varied characteristics

- Check that you can run them on your PC. Some of them may not run if you have a PC with limited memory

Potential issues
----------------
- Check that any item you define (generator, node, technology, area, etc.) is included in the corresponding dictionary

- openTEPES is implicitly a network model. Therefore, at least one electrical  transmission line connecting two nodes and at least two nodes must be defined

- At least one generator must be defined. A thermal generator has a variable cost (the product of fuel cost times the linear term) ≠ 0. A variable renewable energy unit has no variable cost (the product of fuel cost times the linear term = 0)

Some tips
---------
- How can we strongly reduce the size of the case study for testing purposes

   Delete the duration (column D in ``oT_Data_Duration``) of the load levels you want to ignore. For example, if you delete the duration beyond the first 168 hours, you are considering just the first week of the year in the case study

   Put a time step of 2 or 3 hours in the ``oT_Data_Parameter`` file. This will reduce the number of load levels by 2 or 3

- Relaxing the binary condition of binary variables

   In the ``oT_Data_Option`` file you can force or relax the binary condition of the binary variables. This is useful for testing purposes.
   Besides, in ``oT_Data_Generation`` and ``oT_Data_Network`` can also be relaxed individually by generator or transmission line.

- How to ignore a scenario or a period

   Assign probability 0.0 to the scenario or weight 0.0 to the period

- How to ignore a generator

   Don’t assign a node to it

   Put the initial period beyond the year of study

- How to ignore a line

   Put the initial period beyond the year of study

- All the empty cells of the CSV files are substituted by 0.

   Therefore, if you want to set the generation of a solar PV to 0.0 at night, then you must put a small value 0.000001 that will be substituted internally by openTEPES by 0.0

- You don’t need to put the generator column if nothing is in this column. Empty columns don’t need to be included in the CSV files
