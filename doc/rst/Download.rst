.. openTEPES documentation master file, created by Andres Ramos

Download & Installation
=======================
The **openTEPES** model has been developed using `Python 3.12.3 <https://www.python.org/>`_ and `Pyomo 6.8.0 <https://pyomo.readthedocs.io/en/stable/>`_ and it uses `Gurobi 11.0.3 <https://www.gurobi.com/products/gurobi-optimizer/>`_ as commercial MIP solver for which a free academic license is available.
It uses Pyomo so that it is independent of the preferred solver. You can alternatively use one of the free solvers `HiGHS 1.7.2 <https://ergo-code.github.io/HiGHS/dev/interfaces/python/#python-getting-started>`_, `SCIP 9.1.0 <https://www.scipopt.org/>`_, `GLPK 5.0 <https://www.gnu.org/software/glpk/>`_,
and `CBC 2.10.11 <https://github.com/coin-or/Cbc/releases>`_. List the serial solver interfaces under Pyomo with this call::

  pyomo help -s

Gurobi, HiGHS, SCIP, or GLPK  solvers can be installed as a package::

  conda install -c gurobi      gurobi
  pip   install                highspy
  conda install -c conda-forge pyscipopt
  conda install                glpk

The openTEPES model can also be solved with `GAMS <https://www.gams.com/>`_ and a valid `GAMS license <https://www.gams.com/buy_gams/>`_ for a solver. The GAMS language is not included in the openTEPES package and must be installed separately.
This option is activated by calling the openTEPES model with the solver name 'gams'.

Besides, it also requires the following packages:

- `Pandas <https://pandas.pydata.org/>`_ for inputting data and outputting results
- `psutil <https://pypi.org/project/psutil/>`_ for detecting the number of CPUs
- `Plotly <https://plotly.com/python/>`_,  `Altair <https://altair-viz.github.io/#>`_, `Colour <https://pypi.org/project/colour/>`_ for plotting results and drawing the network map
- `NetworkX <https://networkx.org/>`_ for representing the DC power flow formulation with cycle constraints

Cases
-----
Here, you have the input files of:

- a `static small case study of 9 nodes <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/9n>`_,
- a `dynamic (multiyear) small case study of 9 nodes <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/9n7y>`_ with 13 representative weeks per year,
- another one like a `small Spanish system <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/sSEP>`_,
- a `modified RTS24 case study <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/RTS24>`_,
- the `static Reliability Test System Grid Modernization Lab Consortium (RTS-GMLC) <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/RTS-GMLC>`_,
- a `dynamic (multiyear) Reliability Test System Grid Modernization Lab Consortium (RTS-GMLC) <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/RTS-GMLC_6y>`_ with 13 representative weeks per year, and
- a `Nigeria 2030 case study <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/NG2030>`_.

Code
----

The **openTEPES** code is provided under the `GNU Affero General Public License <https://www.gnu.org/licenses/agpl-3.0.en.html>`_:

- the code can't become part of a closed-source commercial software product
- any future changes and improvements to the code remain free and open

Source code can be downloaded from `GitHub <https://github.com/IIT-EnergySystemModels/openTEPES>`_ or installed with `pip <https://pypi.org/project/openTEPES/>`_

This model is a work in progress and will be updated accordingly. If you want to subscribe to the **openTEPES** model updates send an email to andres.ramos@comillas.edu

Installation
------------
`Installation guide <https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf>`_.

There are 2 ways to get all required packages under Windows. We recommend using the Python distribution `Miniconda <https://docs.anaconda.com/free/miniconda/index.html>`_. If you don't want to use it or already have an existing Python (version 3.10) installation, you can also download the required packages by yourself.


**Miniconda (recommended)**

1. `Miniconda <https://docs.anaconda.com/free/miniconda/index.html>`_. Choose the 64-bit installer if possible.

   1. During the installation procedure, keep both checkboxes "modify the PATH" and "register Python" selected! If only higher Python versions are available, you can switch to a specific Python version by typing ``conda install python=<version>``
   2. **Remark:** if Anaconda or Miniconda was installed previously, please check that Python is registered in the environment variables.
2. **Packages and Solver**:

   1. Launch a new Anaconda prompt (or terminal in any IDE)
   2. The `HiGHS 1.7.1 <https://ergo-code.github.io/HiGHS/dev/interfaces/python/#python-getting-started>`_ is our recommendation if you want a free and open-source solver.
   3. Install openTEPES via pip by ``pip install openTEPES``

Continue at `Get Started <#get-started>`_ and see the `Tips <#tips>`_.


**GitHub Repository (the hard way)**

1. Clone the `openTEPES <https://github.com/IIT-EnergySystemModels/openTEPES.git>`_ repository
2. Launch the Anaconda prompt (or terminal in any IDE)
3. Set up the path by ``cd "C:\Users\<username>\...\openTEPES"``. (Note that the path is where the repository was cloned.)
4. Install openTEPES via pip by ``pip install .``


**Solvers**

HiGHS

The `HiGHS solver <https://ergo-code.github.io/HiGHS/dev/interfaces/python/#python-getting-started>`_ can also be used. It can be installed using: ``pip install highspy``.
This solver is activated by calling the openTEPES model with the solver name 'appsi_highs'.

Gurobi

Another recommendation is the use of `Gurobi solver <https://www.gurobi.com/>`_. However, it is commercial solver but most powerful than open-source solvers for large-scale problems.
As a commercial solver it needs a license that is free of charge for academic usage by signing up in `Gurobi webpage <https://pages.gurobi.com/registration/>`_. You can also ask for an `evaluation license <https://www.gurobi.com/downloads/request-an-evaluation-license/>`_ for 30 days to test the solver.
It can be installed using: ``conda install -c gurobi gurobi`` and then ask for an academic or commercial license. Activate the license in your computer using the ``grbgetkey`` command (you need to be in a university internet domain if you are installing an academic license).

GLPK

As an easy option for installation, we have the free and open-source `GLPK solver <https://www.gnu.org/software/glpk/>`_. However, it takes too much time for large-scale problems. It can be installed using: ``conda install glpk``.

CBC

The `CBC solver <https://github.com/coin-or/Cbc>`_ is also another free and open-source solver. For Windows users, the effective way to install the CBC solver is downloading the binaries from this `site <https://www.coin-or.org/download/binary/Cbc/>`_, copy and paste the *cbc.exe* file to the PATH that is the "bin" directory of the Anaconda or Miniconda environment. Under Linux, it can be installed using: ``conda install -c conda-forge coincbc``.

Mosek

Another alternative is the `Mosek solver <https://www.mosek.com/>`_. Note that it is a commercial solver and you need a license for it. Mosek is a good alternative to deal with QPs, SOCPs, and SDPs problems. You only need to use ``conda install -c mosek mosek`` for installation and request a license (academic or commercial). To request the academic one, you can request `here <https://www.mosek.com/products/academic-licenses/>`_.
Moreover, Mosek brings a `license guide <https://docs.mosek.com/9.2/licensing/index.html>`_. But if you are request an academic license, you will receive the license by email, and you only need to locate it in the following path ``C:\Users\<username>\mosek`` in your computer.

GAMS

The openTEPES model can also be solved with `GAMS <https://www.gams.com/>`_ and a valid `GAMS license <https://www.gams.com/buy_gams/>`_ for a solver. The GAMS language is not included in the openTEPES package and must be installed separately.
This option is activated by calling the openTEPES model with the solver name 'gams'.

Get started
-----------

Developers

By cloning the `openTEPES repository <https://github.com/IIT-EnergySystemModels/openTEPES/tree/master>`_, you can create branches and propose pull-request. Any help will be very appreciated.

Users

If you are not planning on developing, please follows the instructions of the `Installation <#installation>`_.

Once installation is complete, openTEPES can be executed in a test mode by using a command prompt.
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
-----------

1. A complete documentation of the openTEPES model can be found at `<https://opentepes.readthedocs.io/en/latest/index.html>`_, which presents the mathematical formulation, input data and output results.
2. Try modifying the **TimeStep** in **oT_Data_Parameter_<case>.csv** and see their effect on results.
3. Using **0** or **1**, the optimization options can be activated or deactivated in **oT_Data_Option_<case>.csv**.
4. If you need a nice python editor, think about using `PyCharm <https://www.jetbrains.com/pycharm/>`_. It has many features including project management, etc.
5. We also suggest the use of `Gurobi <https://www.gurobi.com/academia/academic-program-and-licenses/>`_ (for Academics and Recent Graduates) as a solver to deal with MIP and LP problems instead of GLPK.

**Run the Tutorial**

It can be run in Binder:

.. image:: /../img/binder.png
   :scale: 30%
   :align: left
   :target: https://mybinder.org/v2/gh/IIT-EnergySystemModels/openTEPES-tutorial/HEAD
