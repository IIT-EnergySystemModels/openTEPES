"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)

A stochastic mixed-integer model of the joint generation, storage and transmission expansion problem, solved over a
chronological horizon with a DC or an AC representation of the electric network, and with the hydrogen, heat and
hydropower sectors optional alongside it.

Running a case
--------------
From the command line, through the ``openTEPES_Main`` console script::

    openTEPES_Main --dir /path/to/cases --case 9n --solver gurobi

``--dir``, ``--case`` and ``--solver`` locate the case and choose the solver; the case is a folder of ``oT_Data_*.csv``
and ``oT_Dict_*.csv`` files. Among the rest, ``--log`` turns on solver and formulation logging, ``--out`` and
``--result`` redirect and select the output, ``--gzip-large-csvs`` compresses the bulky result tables, ``--threads``
and ``--crossover`` reach the solver, ``--max-theta`` sets the nodal angle bound, and ``--option`` overrides any flag
of ``oT_Data_Option`` without editing the case.

From Python, through the function the console script calls::

    >>> from openTEPES import openTEPES_run
    >>> mTEPES = openTEPES_run("/path/to/cases", "9n", "gurobi", 0, 0)

``openTEPES_run`` returns the solved Pyomo model and writes the result tables into the case folder. ``out_path``,
``output_spec`` and ``output_format`` choose where they go, which of them are written, and whether they are written as
CSV, as DuckDB, or as both.

Attributes
----------
__version__ : str
    The model version, and the version the package publishes: ``pyproject.toml`` declares it dynamic and reads it from
    here, so this is the one place it is set.

The package re-exports the modules below, so every public name in them is reachable as ``openTEPES.<name>``. They are
imported in the order the model is built:

==================================  ===========================================================================
``openTEPES_Main``                  the command line, and ``main``
``openTEPES``                       ``openTEPES_run``, which reads, builds, solves and writes
``openTEPES_InputSchema``           the tables a case may carry and the shape of each
``openTEPES_Input*Source``          reading a case from CSV files or from DuckDB
``openTEPES_InputData``             reading the case into parameters
``openTEPES_DataConfiguration``     the sets and the derived quantities
``openTEPES_SettingUpVariables``    the variables and their bounds
``openTEPES_ModelFormulation*``     the objective, the investment decisions, and the electricity, hydro,
                                    hydrogen and heat constraints
``openTEPES_ProblemSolving*``       the solve, and the stage, Benders and sector decompositions
``openTEPES_OutputResults*``        the result tables, by subject
``openTEPES_ResultAggregate``       aggregation across the tables
==================================  ===========================================================================
"""
__version__ = "4.18.19"

from .openTEPES_Main                              import main
from .openTEPES                                   import *
from .openTEPES_InputSchema                       import *
from .openTEPES_InputSource                       import *
from .openTEPES_InputCSVSource                    import *
from .openTEPES_InputDuckDBSource                 import *
from .openTEPES_InputData                         import *
from .openTEPES_DataConfiguration                 import *
from .openTEPES_SettingUpVariables                import *
from .openTEPES_ModelFormulationObjective         import *
from .openTEPES_ModelFormulationInvestment        import *
from .openTEPES_ModelFormulationElectricity       import *
from .openTEPES_ModelFormulationHydro             import *
from .openTEPES_ModelFormulationHydrogen          import *
from .openTEPES_ModelFormulationHeat              import *
from .openTEPES_ProblemSolving                    import *
from .openTEPES_ProblemSolvingStageIter           import *
from .openTEPES_ProblemSolvingBenders             import *
from .openTEPES_ProblemSolvingStageDecomposition   import *
from .openTEPES_ProblemSolvingSectorDecomposition import *
from .openTEPES_OutputResultsSink                 import *
from .openTEPES_OutputResultsCommon               import *
from .openTEPES_OutputResultsRawDump              import *
from .openTEPES_OutputResultsInvestment           import *
from .openTEPES_OutputResultsGeneration           import *
from .openTEPES_OutputResultsStorage              import *
from .openTEPES_OutputResultsHydrogen             import *
from .openTEPES_OutputResultsHeat                 import *
from .openTEPES_OutputResultsNetwork              import *
from .openTEPES_OutputResultsEconomic             import *
from .openTEPES_OutputResultsSummary              import *
from .openTEPES_ResultAggregate                   import *
