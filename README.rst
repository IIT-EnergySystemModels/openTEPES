
.. image:: https://pascua.iit.comillas.edu/aramos/openTEPES.png
   :target: https://pascua.iit.comillas.edu/aramos/openTEPES/index.html
   :alt: logo
   :scale: 70%
   :align: center

|

.. image:: https://badge.fury.io/py/openTEPES.svg
    :target: https://badge.fury.io/py/openTEPES
    :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/openTEPES.svg
   :target: https://pypi.python.org/pypi/openTEPES
   :alt: versions

.. image:: https://img.shields.io/readthedocs/opentepes
   :target: https://opentepes.readthedocs.io/en/latest/index.html
   :alt: docs

.. image:: https://img.shields.io/badge/License-AGPL%20v3-blue.svg
   :target: https://github.com/IIT-EnergySystemModels/openTEPES/blob/master/LICENSE
   :alt: AGPL

.. image:: https://static.pepy.tech/badge/openTEPES
   :target: https://pepy.tech/project/openTEPES
   :alt: pepy

.. image:: https://mybinder.org/badge_logo.svg
  :target: https://mybinder.org/v2/gh/IIT-EnergySystemModels/openTEPES-tutorial/HEAD

**Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)**

*Simplicity and Transparency in Power Systems Planning*



The **openTEPES** model has been developed at the `Instituto de Investigación Tecnológica (IIT) <https://www.iit.comillas.edu/index.php.en>`_ of the `Universidad Pontificia Comillas <https://www.comillas.edu/en/>`_.

The **openTEPES** model presents a decision support system for defining the **integrated generation, storage, and transmission resource planning** (IRP, GEP+SEP+TEP) -**Integrated Resource Planning** (IRP)- of a **large-scale electric system** at a tactical level (i.e., time horizons of 5-30 years),
defined as a set of **generation, storage, and (electricity, hydrogen, and heat) networks dynamic investment decisions for multiple future years**.

The `openTEPES complete documentation <https://opentepes.readthedocs.io/en/latest/index.html>`_ presents the input data, output results, mathematical formulation, download and installation, and the research projects where the model has been used.

It is integrated into the `open energy system modelling platform <https://openenergymodels.net/>`_, helping model Europe's energy system and in the list of `energy models published under open source licenses <https://wiki.openmod-initiative.org/wiki/Open_Models>`_.
It is also part of the Africa `open energy system modelling toolbox <https://africaenergymodels.net/>`_, which is a suite of open and linked state-of-the-art open-source energy system models for Africa.

Scripts are provided to exchange information with Integrated Assessment Models (IAM) using their `nomenclature and data formats <https://nomenclature-iamc.readthedocs.io/en/stable/>`_.

It has been used by the **Ministry for the Ecological Transition and the Demographic Challenge (MITECO)** to analyze the electricity sector in the latest Spanish `National Energy and Climate Plan (NECP) Update 2023-2030 <https://www.miteco.gob.es/content/dam/miteco/es/energia/files-1/pniec-2023-2030/PNIEC_2024_240924.pdf>`_ in September 2024.

Reference
############
**A. Ramos, E. Quispe, S. Lumbreras** `“OpenTEPES: Open-source Transmission and Generation Expansion Planning” <https://www.sciencedirect.com/science/article/pii/S235271102200053X>`_ SoftwareX 18: June 2022 `10.1016/j.softx.2022.101070 <https://doi.org/10.1016/j.softx.2022.101070>`_.

**openTEPES**: `summary presentation <https://pascua.iit.comillas.edu/aramos/openTEPES.pdf>`_, `présentation (French) <https://pascua.iit.comillas.edu/aramos/openTEPES_fr.pdf>`_, and `installation <https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf>`_

Authors
########
**Andrés Ramos, Erik Alvarez, Francisco Labora, Sara Lumbreras** Universidad Pontificia Comillas, Instituto de Investigación Tecnológica, Alberto Aguilera 23, 28015 Madrid, Spain

Contact: andres.ramos@comillas.edu

Description
############
**openTEPES** determines the investment plans of new facilities (generators, ESS, and lines)
for supplying the forecasted demand at minimum cost. Tactical planning is concerned with time horizons of 10-20 years. Its objective is to evaluate the future generation, storage, and network needs.
The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

The **openTEPES** model presents a decision support system for defining the integrated generation, storage, and transmission expansion plan of a large-scale electric system at a tactical level,
defined as a set of generation, storage, and network investment decisions for future years. The expansion candidate, generators, ESS and lines, are pre-defined by the user, so the model determines
the optimal decisions among those specified by the user.

It determines automatically optimal expansion plans that satisfy simultaneously several attributes. Its main characteristics are:

- **Dynamic (perfect foresight)**: the scope of the model corresponds to several periods (years) at a long-term horizon, 2030, 2035 and 2040 for example.

  It represents hierarchically the different time scopes to take decisions in an electric system:

  - Load level: one hour, e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00

  The time division allows a user-defined flexible representation of the periods for evaluating the system operation. Moreover, it can be run with chronological periods of several consecutive hours (bi-hourly, tri-hourly resolution) to decrease the computational burden without losing accuracy. The model can be run with a single period (year) or with several periods (years) to allow the analysis of the system evolution. The time definition allows also to specify disconnected representative periods (e.g., days, weeks) to evaluate the system operation.
  The model can be run with a single period (year) or with several periods (years) to allow the analysis of the system evolution. The time definition can also specify disconnected representative periods (e.g., days, weeks) to evaluate the system operation.
  The period (year) must be represented by 8736 hours because several model concepts representing the system operation are based on weeks (168 hours) or months (made of 4 weeks, 672 hours).

- **Stochastic**: several stochastic parameters that can influence the optimal generation, storage, and transmission expansion decisions are considered. The model considers stochastic
  medium-term yearly uncertainties (scenarios) related to the system operation. These operation scenarios are associated with renewable energy sources, energy inflows and outflows, natural water inflows, operating reserves, inertia, and electricity, hydrogen, and heat demand.

The objective function incorporates the two main quantifiable costs: **generation, storage, and transmission investment cost (CAPEX)** and **expected variable operation costs (including generation, consumption, emission, and reliability costs) (system OPEX)**.

The model formulates a **two-stage stochastic optimization** problem, including generation, storage, and electricity, hydrogen, and heat network binary investment/retirement decisions, generation operation decisions (commitment, startup, and shutdown decisions are also binary), and electric line-switching decisions.
The capacity expansion considers adequacy system reserve margin and minimum and maximum energy constraints.

The very detailed operation model is an electric **network-constrained unit commitment (NCUC)** based on a **tight and compact** formulation, including **operating reserves** with a
**DC power flow (DCPF)**, including electric **line-switching** decisions. **ohmic losses of the electricity network** are considered proportional to the electric line flow. It considers different **energy storage systems (ESS)**, e.g., pumped-hydro storage,
battery, demand response, electric vehicles, solar thermal, electrolyzer, etc. It allows analyzing the trade-off between the investment in generation/transmission/pipeline and the investment and/or use of storage capacity.

The model allows also a representation of the **hydro system** based on volume and water inflow data considering the water stream topology (hydro cascade basins). If they are not available it runs with an energy-based representation of the hydro system.

Also, it includes a representation of **Power to Hydrogen (P2H2)** by setting the **hydrogen demand** satisfied by the production of hydrogen with electrolyzers (consume electricity to produce hydrogen) and a **hydrogen pipeline network** to distribute it.
Besides, it includes a representation of **Power to Heat (P2H)** by setting the **heat demand** satisfied by the production of heat with heat pumps or electric heaters (consume electricity to produce heat) and a **heat pipe network** to distribute it. If they are not available it runs with just the other energy carriers.

The main results of the model can be structured in these topics:

- **Investment**: (generation, storage, hydro reservoirs, electric lines, hydrogen pipelines, and heat pipes) investment decisions and cost
- **Operation**: unit commitment, startup, and shutdown of non-renewable units, unit output and aggregation by technologies (thermal, storage hydro, pumped-hydro storage, RES), RES curtailment, electric line, hydrogen pipeline, and heat pipe flows, line ohmic losses, node voltage angles, upward and downward operating reserves, ESS inventory levels, hydro reservoir volumes, power, hydrogen, and heat not served
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC), stored energy value, water volume value
- **Economic**: operation, emission, and reliability costs and revenues from operation and operating reserves
- **Flexibility**: flexibility provided by demand, by the different generation and consumption technologies, and by power not served

Results are shown in csv files and graphical plots.

A careful implementation has been done to avoid numerical problems by scaling parameters, variables and equations of the optimization problem allowing the model to be used for large-scale cases, e.g., the European system with hourly detail.

Installation
############
`Installation guide <https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf>`_.

There are 2 ways to get all required packages under Windows. We recommend using the Python distribution Miniconda. If you don't want to use it or already have an existing Python (version 3.11) installation, you can also download the required packages by yourself.

Miniconda (recommended)
=======================
1. `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_. Choose the 64-bit installer if possible.

   1. During the installation procedure, keep both checkboxes "modify the PATH" and "register Python" selected! If only higher Python versions are available, you can switch to a specific Python Version by typing ``conda install python=<version>``
   2. **Remark:** if Anaconda or Miniconda was installed previously, please check that python is registered in the environment variables.
2. **Packages and Solver**:

   1. Launch a new Anaconda prompt (or terminal in any IDE)
   2. The `HiGHS <https://ergo-code.github.io/HiGHS/dev/interfaces/python/#python-getting-started>`_ is our recommendation if you want a free and open-source solver.
   3. Install openTEPES via pip by ``pip install openTEPES``

Continue at `Get Started <#get-started>`_ and see the `Tips <#tips>`_.


GitHub Repository (the hard way)
================================
1. Clone the openTEPES repository
2. Launch the Anaconda prompt (or terminal in any IDE)
3. Set up the PATH by ``cd "C:\Users\<username>\...\openTEPES"``. (Note that the path is where the repository was cloned.)
4. Install openTEPES via pip by ``pip install .``

Solvers
#######

HiGHS
=====
The `HiGHS solver <https://ergo-code.github.io/HiGHS/dev/interfaces/python/#python-getting-started>`_ can also be used. It can be installed using: ``pip install highspy``.
This solver is activated by calling the openTEPES model with the solver name 'appsi_highs'.

Gurobi
======
Another recommendation is the use of `Gurobi solver <https://www.gurobi.com/>`_. However, it is commercial solver but most powerful than open-source solvers for large-scale problems.
As a commercial solver it needs a license that is free of charge for academic usage by signing up in `Gurobi webpage <https://pages.gurobi.com/registration/>`_. You can also ask for an `evaluation license <https://www.gurobi.com/downloads/request-an-evaluation-license/>`_ for 30 days to test the solver.
It can be installed using: ``conda install -c gurobi gurobi`` and then ask for an academic or commercial license. Activate the license in your computer using the ``grbgetkey`` command (you need to be in a university internet domain if you are installing an academic license).

GLPK
=====
As an easy option for installation, we have the free and open-source `GLPK solver <https://www.gnu.org/software/glpk/>`_. However, it takes too much time for large-scale problems. It can be installed using: ``conda install glpk``.

CBC
=====
The `CBC solver <https://github.com/coin-or/Cbc>`_ is also another free and open-source solver. For Windows users, the effective way to install the CBC solver is downloading the binaries from this `site <https://www.coin-or.org/download/binary/Cbc/>`_, copy and paste the *cbc.exe* file to the PATH that is the "bin" directory of the Anaconda or Miniconda environment. Under Linux, it can be installed using: ``conda install -c conda-forge coincbc``.

Mosek
=====
Another alternative is the `Mosek solver <https://www.mosek.com/>`_. Note that it is a commercial solver and you need a license for it. Mosek is a good alternative to deal with QPs, SOCPs, and SDPs problems. You only need to use ``conda install -c mosek mosek`` for installation and request a license (academic or commercial). To request the academic one, you can request `here <https://www.mosek.com/products/academic-licenses/>`_.
Moreover, Mosek brings a `license guide <https://docs.mosek.com/9.2/licensing/index.html>`_. But if you are request an academic license, you will receive the license by email, and you only need to locate it in the following path ``C:\Users\<username>\mosek`` in your computer.

GAMS
=====
The openTEPES model can also be solved with `GAMS <https://www.gams.com/>`_ and a valid `GAMS license <https://www.gams.com/buy_gams/>`_ for a solver. The GAMS language is not included in the openTEPES package and must be installed separately.
This option is activated by calling the openTEPES model with the solver name 'gams'.

Get started
###########

Developers
==========
By cloning the `openTEPES <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master>`_ repository, you can create branches and propose pull-request. Any help will be very appreciated.

Users
=====

If you are not planning on developing, please follows the instructions of the `openTEPES installation <#installation>`_.

Once installation is complete, `openTEPES <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master>`_ can be executed in a test mode by using a command prompt.
In the directory of your choice, open and execute the openTEPES_run.py script by using the following on the command prompt (Windows) or Terminal (Linux). (Depending on what your standard python version is, you might need to call `python3` instead of `python`.):

     ``openTEPES_Main``

Then, four parameters (case, dir, solver, results, and console log) will be asked for.

**Remark:** at this step only press enter for each input and openTEPES will be executed with the default parameters.

After this in a directory of your choice, make a copy of the `9n <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/9n>`_ or `sSEP <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/sSEP>`_ case to create a new case of your choice but using the current format of the CSV files.
A proper execution by ``openTEPES_Main`` can be made by introducing the new case and the directory of your choice. Note that the solver is **glpk** by default, but it can be changed by other solvers that pyomo supports (e.g., gurobi, highs).

Then, the **results** should be written in the folder who is called with the case name. The results contain plots and summary spreadsheets for multiple optimized energy scenarios, periods and load levels as well as the investment decisions.

**Note that** there is an alternative way to run the model by creating a new script **script.py**, and write the following:

    ``from openTEPES.openTEPES import openTEPES_run``

    ``openTEPES_run(<dir>, <case>, <solver>, <results>, <log>)``

Tips
####

1. A complete documentation of the openTEPES model can be found at `<https://opentepes.readthedocs.io/en/latest/index.html>`_, which presents the mathematical formulation, input data and output results.
2. Try modifying the **TimeStep** in **oT_Data_Parameter_<case>.csv** and see their effect on results.
3. Using **0** or **1**, the optimization options can be activated or deactivated in **oT_Data_Option_<case>.csv**.
4. If you need a nice python editor, think about using `PyCharm <https://www.jetbrains.com/pycharm/>`_. It has many features including project management, etc.
5. We also suggest the use of `Gurobi <https://www.gurobi.com/academia/academic-program-and-licenses/>`_ (for Academics and Recent Graduates) as a solver to deal with MIP and LP problems instead of GLPK.

Run the Tutorial
################

It can be run in Binder: 

.. image:: https://mybinder.org/badge_logo.svg
  :target: https://mybinder.org/v2/gh/IIT-EnergySystemModels/openTEPES-tutorial/HEAD

Expected Results
################
.. image:: doc/img/oT_Map_Network_TF2030.png
  :width: 600px
  :align: center
  :alt: Network map with investment decisions
