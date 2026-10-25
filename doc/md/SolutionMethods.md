---
openTEPES documentation master file, created by Andres Ramos
---

# Solution Methods

The **openTEPES** model can be solved using different solution methods, depending on the size of the problem and the available computational resources. The
solution method comprises two choices: the decomposition of the problem and the solver settings for each optimization problem.

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

The solver name you pass — the `SolverName` argument of `openTEPES_run`, or the solver you type at the `openTEPES_Main` prompt — also selects **how** Pyomo
talks to the solver across the many solves a single case performs.

**Non-persistent (the default).** `gurobi`, `gurobi_direct`, `cplex`, `highs`, `gams`, `glpk`. Pyomo writes the whole model to the solver on every solve, and
each solve builds a fresh solver handle (`SolverFactory(SolverName)`) — nothing is kept between solves. It is simple, works with every solver, and is the
default (`highs`).

**Persistent (Gurobi only).** `appsi_gurobi` (the APPSI interface, `pyomo.contrib.appsi`) or `gurobi_persistent` (the older interface). The solver instance is
attached to the model once and kept in memory: the first solve calls `set_instance`, and every later solve pushes only what changed — updated variable bounds,
and, for `appsi_gurobi`, new or updated parameters and constraints — instead of re-exporting the model. Gurobi can also restart from the previous basis when the
same instance is re-solved with small changes, as in the sector Benders decomposition. Between consecutive stages, however, the constraints change, and the gain
arises from avoiding the export of the model, not from the basis.

**Where it matters.** A single openTEPES case is rarely one solve. The stage loop solves the model once per `(period, scenario, stage)`, then fixes the integer
and investment decisions and re-solves the relaxed LP to recover the shadow prices (LMPs); the Benders drivers re-solve as they add cuts. On a large model,
re-exporting the full problem to the solver on each of these solves is a real cost, so a persistent Gurobi keeps the model resident and sends only the changes.
A single-stage LP — or any HiGHS run — has little to reuse, so non-persistent is the right choice.

**Mode C is always non-persistent.** The hot-swap re-solve (`resolve`, see {doc}`Sweeps`) re-exports the model from the mutable parameter values on every solve,
so it needs a plain solver name; a persistent handle would keep a stale copy of the model.

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

Only Gurobi has a persistent interface here, so its incremental-update speed-up applies only to `appsi_gurobi` / `gurobi_persistent`. If you run large
multi-stage or Benders cases on Gurobi with the plain `gurobi` name, you re-export the model on every solve and leave that speed-up unused.

### LP algorithm

The LP algorithm is selected by openTEPES (file `openTEPES_ProblemSolvingTuning.py`). The figure shows the algorithm for each problem type and solver interface;
green boxes denote the barrier method.

```{image} ../img/SolverMethod.png
:alt: LP algorithm selected by openTEPES for each problem type and solver interface
:align: center
:width: 100%
```

* `gurobi`, `gurobi_direct`, `cplex` and `gams` use the barrier method for every problem (`Method=2` for Gurobi, `LPMethod=4` for CPLEX).
* `appsi_gurobi` and `gurobi_persistent` use the barrier method for the first solve of a model instance and the automatic method (`Method=-1`) for every later
  solve of the same instance, i.e., the later periods and scenarios of an operation problem and the iterations of the sector Benders decomposition.
* With `highs`, HiGHS selects the algorithm itself; the remaining solvers use their default settings.
* After a mixed-integer (MIP) solve, the integer and investment variables are fixed, and the resulting LP is re-solved with the automatic method to obtain the
  dual variables (`Method=-1` for Gurobi, `LPMethod=0` for CPLEX).

The barrier method yields reproducible dual variables, i.e., the same duals whenever the same problem is solved. In contrast, for an LP the automatic method of
Gurobi runs the barrier and simplex methods concurrently and returns the first solution found. On a degenerate LP the dual solution is not unique; hence, the
duals depend on the method that finishes first and may change from one solve to the next.

The option `--crossover 0` omits the crossover step after a Gurobi barrier solve. The solution time decreases; however, at degenerate points some duals differ
from those of a basic solution.
