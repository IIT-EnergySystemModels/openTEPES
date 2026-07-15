---
openTEPES documentation master file, created by Andres Ramos
---

# Download & Installation

The **openTEPES** model has been tested using the latest versions of [Python 3.13.7](https://www.python.org/) and [Pyomo 6.10.1](https://pyomo.readthedocs.io/en/stable/), and it uses [Gurobi 13.0.2](https://www.gurobi.com/products/gurobi-optimizer/) as a commercial MIP solver, for which a free academic license is available.
It uses Pyomo so that it is independent of the preferred solver. Alternatively, you can use one of the free solvers [HiGHS 1.15.1](https://pypi.org/project/highspy/), [SCIP 10.0.2](https://www.scipopt.org/index.php#download), [GLPK 5.0](https://www.gnu.org/software/glpk/),
or [CBC 2.10.13](https://github.com/coin-or/Cbc/releases). You can list the serial solver interfaces available under Pyomo with this call:

```
pyomo help -s
```

The Gurobi, HiGHS, SCIP, and GLPK solvers can be installed as packages:

```
conda install -c gurobi      gurobi
pip   install                highspy
conda install -c conda-forge pyscipopt
conda install                glpk
```

The openTEPES model can also be solved with [GAMS](https://www.gams.com/) and a valid [GAMS license](https://www.gams.com/buy_gams/) for a solver. The GAMS language is not included in the openTEPES package and must be installed separately.
This option is activated by calling the openTEPES model with the solver name 'gams'.

It also requires the following packages:

- [Pandas](https://pandas.pydata.org/) for reading input data and writing results
- [psutil](https://pypi.org/project/psutil/) for detecting the number of CPUs
- [Plotly](https://plotly.com/python/), [Altair](https://altair-viz.github.io/#), and [Colour](https://pypi.org/project/colour/) for plotting results and drawing the network map
- [NetworkX](https://networkx.org/) for representing the DC power flow formulation with cycle constraints

## Cases

Here are the input files for:

- a [static small case study of 9 nodes](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n), the minimal electricity example and the recommended starting point for building a new case,
- the same [9-node case solved with a PTDF network formulation](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n_PTDF), which uses power transfer distribution factors and total transfer capacities instead of the angle-based DC power flow,
- the same [9-node case coupled with a heat network](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n_heat), which adds heat demand and a heat pipe network on top of the electricity system,
- the same [9-node case coupled with a hydrogen network](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n_H2), which adds electrolyzers, hydrogen demand, and a hydrogen pipe network on top of the electricity system,
- a [dynamic (multiyear) small case study of 9 nodes](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n7y) with 13 representative weeks per year,
- another case, a [small Spanish system](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/sSEP), which also includes a hydrogen network,
- a [modified RTS24 case study](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/RTS24),
- the [static Reliability Test System Grid Modernization Lab Consortium (RTS-GMLC)](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/RTS-GMLC),
- a [dynamic (multiyear) Reliability Test System Grid Modernization Lab Consortium (RTS-GMLC)](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/RTS-GMLC_6y) with 13 representative weeks per year, and
- a [Nigeria 2030 case study](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/NG2030).

## Code

The **openTEPES** code is provided under the [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.en.html):

- the code cannot become part of a closed-source commercial software product
- any future changes and improvements to the code remain free and open

The source code can be downloaded from [GitHub](https://github.com/IIT-EnergySystemModels/openTEPES) or installed with [pip](https://pypi.org/project/openTEPES/).

This model is a work in progress and will be updated accordingly. If you want to subscribe to **openTEPES** model updates, send an email to [andres.ramos@comillas.edu](mailto:andres.ramos@comillas.edu).

(installation)=
## Installation

[Installation guide](https://pascua.iit.comillas.edu/aramos/openTEPES_installation.pdf).

There are two ways to get all the required packages under Windows. We recommend using the Python distribution [Miniconda](https://docs.anaconda.com/free/miniconda/index.html). If you don't want to use it or already have an existing Python installation, you can also download the required packages on your own.

**Miniconda (recommended)**

1. [Miniconda](https://docs.anaconda.com/free/miniconda/index.html). Choose the 64-bit installer if possible.

   1. During the installation procedure, keep both checkboxes "modify the PATH" and "register Python" selected! If only higher Python versions are available, you can switch to a specific Python version by typing `conda install python=<version>`
   2. **Remark:** if Anaconda or Miniconda was installed previously, please check that Python is registered in the environment variables.

2. **Packages and Solver**:

   1. Launch a new Anaconda prompt (or a terminal in any IDE)
   2. [HiGHS](https://pypi.org/project/highspy/) is our recommendation if you want a free and open-source solver.
   3. Install openTEPES via pip by running `pip install openTEPES`

Continue at {ref}`get-started`.

**GitHub Repository (the hard way)**

1. Clone the [openTEPES](https://github.com/IIT-EnergySystemModels/openTEPES.git) repository
2. Launch the Anaconda prompt (or a terminal in any IDE)
3. Navigate to the repository directory with `cd "C:\Users\<username>\...\openTEPES"`. (Note that the path is where the repository was cloned.)
4. Install openTEPES via pip by running `pip install .`

**Solvers**

**HiGHS**

The [HiGHS solver](https://pypi.org/project/highspy/) can also be used. It can be installed using: `pip install highspy`.

**Gurobi**

Another recommendation is the use of the [Gurobi solver](https://www.gurobi.com/). It is a commercial solver, but it is more powerful than open-source solvers for large-scale problems.
As a commercial solver, it needs a license, which is free of charge for academic use by signing up on the [Gurobi website](https://pages.gurobi.com/registration/). You can also ask for a 30-day [evaluation license](https://www.gurobi.com/downloads/request-an-evaluation-license/) to test the solver.
It can be installed using `conda install -c gurobi gurobi`, and then you can request an academic or commercial license. Activate the license on your computer using the `grbgetkey` command (you need to be in a university internet domain if you are installing an academic license).

**GLPK**

As an easy option for installation, there is the free and open-source [GLPK solver](https://www.gnu.org/software/glpk/). However, it can be very slow for large-scale problems. It can be installed using: `conda install glpk`.

**CBC**

The [CBC solver](https://github.com/coin-or/Cbc) is another free and open-source solver. For Windows users, the easiest way to install the CBC solver is to download the binaries from this [site](https://www.coin-or.org/download/binary/Cbc/) and copy the *cbc.exe* file into the "bin" directory of the Anaconda or Miniconda environment, which is on the PATH. Under Linux, it can be installed using: `conda install -c conda-forge coincbc`.

**Mosek**

Another alternative is the [Mosek solver](https://www.mosek.com/). Note that it is a commercial solver, and you need a license for it. Mosek is a good alternative for dealing with QP, SOCP, and SDP problems. You only need to run `conda install -c mosek mosek` for installation and then request a license (academic or commercial). You can apply for an academic license [here](https://www.mosek.com/products/academic-licenses/).
Mosek also provides a [license guide](https://docs.mosek.com/9.2/licensing/index.html). If you request an academic license, you will receive it by email and only need to place it in the path `C:\Users\<username>\mosek` on your computer.

**GAMS**

The openTEPES model can also be solved with [GAMS](https://www.gams.com/) and a valid [GAMS license](https://www.gams.com/buy_gams/) for a solver. The GAMS language is not included in the openTEPES package and must be installed separately.
This option is activated by calling the openTEPES model with the solver name 'gams'.

(get-started)=
## Get started

Developers

By cloning the [openTEPES repository](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master), you can create branches and propose pull requests. Any help will be greatly appreciated.

Users

If you are not planning on developing, please follow the instructions in {ref}`installation`.

Once installation is complete, openTEPES can be executed in test mode from a command prompt.
In the directory of your choice, open and execute the **openTEPES_run.py** script by using the following on the command prompt (Windows) or terminal (Linux). (Depending on your default Python version, you might need to call `python3` instead of `python`.):

> `openTEPES_Main`

You will then be asked for five parameters (case, dir, solver, results, and console log).

**Remark:** at this step, just press Enter for each input, and openTEPES will be executed with the default parameters.

After this, in a directory of your choice, make a copy of the [9n](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/9n) or [sSEP](https://github.com/IIT-EnergySystemModels/openTEPES/tree/master/openTEPES/cases/sSEP) case to create a new case of your choice, keeping the current format of the CSV files.
You can then run `openTEPES_Main` properly by entering the new case and the directory of your choice. Note that the solver is **glpk** by default, but it can be changed to any other solver that Pyomo supports (e.g., gurobi, highs).

Then, the **results** are written to the folder named after the case. The results contain plots and summary spreadsheets for multiple optimized energy scenarios, periods, and load levels, as well as the investment decisions.

**Note that** there is an alternative way to run the model: create a new script, **script.py**, and write the following:

> `from openTEPES.openTEPES import openTEPES_run`
>
> `openTEPES_run(<dir>, <case>, <solver>, <results>, <log>)`

A case can be a CSV directory or a single `.duckdb` file (see {doc}`InputData`). To run many related cases at once — scenario ensembles or sensitivity sweeps — see {doc}`Sweeps`.

**Run the Tutorial**

The tutorial can be run in Binder:

```{image} /../img/binder.png
:align: left
:scale: 30%
:target: https://mybinder.org/v2/gh/IIT-EnergySystemModels/openTEPES-tutorial/HEAD
```
