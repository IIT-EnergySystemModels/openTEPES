---
openTEPES documentation master file, created by Andres Ramos
---

# Solution Methods

The **openTEPES** model can be solved using different solution methods, depending on the size of the problem and the available computational resources. The
solution method comprises the decomposition of the problem and the solver settings.

## Decomposition

### Complete problem

The optimization problem can be solved directly using a commercial solver (e.g., Gurobi, CPLEX) or an open-source solver (e.g., CBC, GLPK). This method is
suitable for small to medium-sized problems. As a rule of thumb, a linear optimization problem requires **1 GB of memory for every 1 million rows**. For a
mixed-integer linear optimization problem, the requirements are much higher, and they depend on the number of binary variables and the number of constraints
that include them.

### Stage Benders decomposition

See also some Benders decomposition publications applied to TEP:

* S. Lumbreras, A. Ramos "How to Solve the Transmission Expansion Planning (TEP) Problem Faster: Acceleration Techniques Applied to Benders Decomposition" IET
  Generation, Transmission & Distribution 10: 2351-2359, Jul 2016 [10.1049/iet-gtd.2015.1075](https://dx.doi.org/10.1049/iet-gtd.2015.1075)

* S. Lumbreras, A. Ramos "Transmission Expansion Planning using an Efficient Version of Benders’ Decomposition. A Case Study" IEEE PowerTech. Grenoble, France.
  June 2013 [10.1109/PTC.2013.6652091](https://dx.doi.org/10.1109/PTC.2013.6652091)

It solves the complete model, decomposed by the stage Benders decomposition method (file `openTEPES_ProblemSolvingStageDecomposition`). The master problem
determines the investment decisions and the subproblem the operation decisions. The subproblem is solved by stages (e.g., weeks or months). The duration of the
stage (weekly —168 h—, monthly —672 h—, or quarterly —2184 h—) is chosen based on what makes sense from a system operation point of view. This value must be
larger than or equal to the shortest duration of any storage type (e.g., weekly).

Inventory levels of ESS at the end of every stage are fixed for the decomposition, i.e., consecutive stages are not tied to each other.

Only DC candidate lines are allowed, in order to keep convexity in the subproblem with respect to this investment decision variable.

There are three possibilities for solving the decomposed problem (file `openTEPES_ProblemSolvingStageSolve`):

1. **In parallel**: writes the LP file for the solver and sends the problems to a queue. It only works with the serial solver manager factory.
2. **Sequentially (LP file)**: writes the LP file for the solver and solves each stage sequentially.
3. **Sequentially (in memory)**: loads the problem in memory and solves each stage sequentially. It takes a long time to load the problem in memory.

### Sector Benders decomposition

It solves the electric sector and the hydrogen sector separately, using the Benders decomposition method (file `openTEPES_ProblemSolvingSectorDecomposition`).

## Solver settings

### Solver interface: persistent vs non-persistent

The solver name (the `SolverName` argument of `openTEPES_run`, or the solver entered at the `openTEPES_Main` prompt) also selects the interface between Pyomo
and the solver.

**Non-persistent interface (default).** `gurobi`, `gurobi_direct`, `cplex`, `highs`, `gams`, `glpk`. Pyomo exports the complete model at every solve to a new
solver object (`SolverFactory(SolverName)`). This interface is available for every solver; the default is `highs`.

**Persistent interface (Gurobi only).** `appsi_gurobi` (APPSI, `pyomo.contrib.appsi`) or `gurobi_persistent` (the earlier interface). The solver instance is
attached to the model once (`set_instance`); later solves transfer only the modifications: variable bounds and, for `appsi_gurobi`, parameters and constraints.
Gurobi can restart from the previous basis when the same instance is re-solved with small changes, as in the sector Benders decomposition. Between stages the
constraints change, and the gain comes from avoiding the export of the model, not from the basis.

**Relevance for large cases.** A case involves many solves: one per `(period, scenario, stage)`, an LP re-solve with the integer and investment decisions fixed
to obtain the dual variables (LMPs), and the iterations of the Benders decompositions. For a large model solved with Gurobi, the persistent interface avoids the
export of the model at each solve; the plain `gurobi` name forgoes this gain. A single-stage LP, or any HiGHS solve, gains little from it.

**Non-persistent interface in Mode C.** The hot-swap re-solve (`resolve`, see {doc}`Sweeps`) exports the model with the current values of the mutable
parameters at every solve; hence, it requires a non-persistent solver name.

Examples:

```python
from openTEPES.openTEPES import openTEPES_run

# default: HiGHS, non-persistent
openTEPES_run("cases", "9n", "highs", 1, 0)

# persistent Gurobi (APPSI): one solver instance reused across the stage loop and the dual re-solve
openTEPES_run("cases", "9n", "appsi_gurobi", 1, 0)

# older persistent Gurobi interface
openTEPES_run("cases", "9n", "gurobi_persistent", 1, 0)
```

### LP algorithm

The LP algorithm is selected by openTEPES (file `openTEPES_ProblemSolvingTuning.py`), as shown in the figure; green boxes denote the barrier method.

```{image} ../img/SolverMethod.png
:alt: LP algorithm selected by openTEPES for each problem type and solver interface
:align: center
:width: 100%
```

* `gurobi`, `gurobi_direct`, `cplex` and `gams`: barrier method for every problem (`Method=2` for Gurobi, `LPMethod=4` for CPLEX).
* `appsi_gurobi` and `gurobi_persistent`: barrier method for the first solve of an instance, and automatic method (`Method=-1`) for the later solves of the same
  instance, i.e., the later periods and scenarios of an operation problem and the iterations of the sector Benders decomposition.
* `highs` and the remaining solvers: default settings of the solver.
* After a mixed-integer (MIP) solve, the LP with the integer and investment variables fixed is re-solved with the automatic method to obtain the dual variables
  (`Method=-1` for Gurobi, `LPMethod=0` for CPLEX).

The barrier method yields the same dual variables at every solve of the same problem. The automatic method of Gurobi runs the barrier and simplex methods
concurrently and returns the first solution; on a degenerate LP, whose duals are not unique, the duals may therefore change from one solve to the next.

The option `--crossover 0` omits the crossover after a Gurobi barrier solve, which reduces the solution time; at degenerate points, some duals then differ from
those of a basic solution.
