.. openTEPES documentation master file, created by Andres Ramos

Download
========
The **openTEPES** has been developed using `Python 3.9.4 <https://www.python.org/>`_ and `Pyomo 6.0.1 <https://pyomo.readthedocs.io/en/stable/>`_ and it uses `Gurobi 9.1.2 <https://www.gurobi.com/products/gurobi-optimizer/>`_ as commercial MIP solver for which a free academic license is available.
It uses Pyomo so that it is independent of the preferred solver. You can alternatively use one of the free solvers `SCIP 7.0.3 <https://scip.zib.de/>`_, `GLPK 4.65 <https://www.gnu.org/software/glpk/>`_
and `CBC 2.10.5 <https://github.com/coin-or/Cbc>`_. List the serial solver interfaces under Pyomo with this call::

  pyomo help -s

Besides, it also requires the following packages:

- `Pandas <https://pandas.pydata.org/>`_ for inputting data and outputting results
- `psutil <https://pypi.org/project/psutil/>`_ for detecting the number of CPUs
- `Matplotlib <https://matplotlib.org/>`_, `Cartopy <https://scitools.org.uk/cartopy/docs/latest/#>`_ for plotting the network map

Cases
-----
Here, you have the input files of a small case study of `9 nodes <https://pascua.iit.comillas.edu/aramos/9n.zip>`_ and another one to a `small Spanish system <https://pascua.iit.comillas.edu/aramos/sSEP.zip>`_.

Code
----

The **openTEPES** code is provided under the `GNU General Public License <https://www.gnu.org/licenses/gpl-3.0.html>`_:

- the code can't become part of a closed-source commercial software product
- any future changes and improvements to the code remain free and open

Source code can be downloaded from `GitHub <https://github.com/IIT-EnergySystemModels/openTEPES>`_ or installed with `pip <https://pypi.org/project/openTEPES/>`_

This model is a work in progress and will be updated accordingly. If you want to subscribe to the **openTEPES** model updates send an email to andres.ramos@comillas.edu
