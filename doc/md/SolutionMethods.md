# Solution Methods

The **openTEPES** model can be solved using different solution methods, depending on the size of the problem and the available computational resources. The main solution methods are:

## Direct solution

The optimization problem can be solved directly using a commercial solver (e.g., Gurobi, CPLEX) or an open-source solver (e.g., CBC, GLPK). This method is suitable for small to medium-sized problems.
As a rule of thumb, a linear optimization problem requires **1 GB of memory for every 1 million rows**. For a mixed-integer linear optimization problem, the requirements are much higher, and they depend on the number of binary variables and the number of constraints that include them.

## Stage Benders decomposition

See also some Benders decomposition publications applied to TEP:

* S. Lumbreras, A. Ramos "How to Solve the Transmission Expansion Planning (TEP) Problem Faster: Acceleration Techniques Applied to Benders Decomposition" IET Generation, Transmission & Distribution 10: 2351-2359, Jul 2016 [10.1049/iet-gtd.2015.1075](https://dx.doi.org/10.1049/iet-gtd.2015.1075)

* S. Lumbreras, A. Ramos "Transmission Expansion Planning using an Efficient Version of Benders’ Decomposition. A Case Study" IEEE PowerTech. Grenoble, France. June 2013 [10.1109/PTC.2013.6652091](https://dx.doi.org/10.1109/PTC.2013.6652091)

Solves the complete model decomposed by stage Benders decomposition method (file `openTEPES_ProblemSolvingStageDecomposition`). The master problem determines the investment decisions and the subproblem the operation decisions. The subproblem is solved by stages (e.g., weeks or months).
The duration of the stage (weekly -168 h- or monthly -672 h- or trimonthly -2184 h- is what makes sense from a system operation point of view.
This value must be larger or equal than the shortest duration of any storage type (e.g., weekly).

Inventory levels of ESS at the end of every stage are fixed for the decomposition, i.e., consecutive stages are not tied between them.

Only DC candidate lines are allowed for keeping convexity in the subproblem with respect to this investment decision variable.

There are three possibilities for solving the decomposed problem (file `openTEPES_ProblemSolvingStageSolve`):

1. **In parallel**:  writes the LP file for the solver and sends the problems to a queue. Only works with serial solver manager factory.
2. **Sequentially**: writes the LP file for the solver and solves each stage sequentially.
3. **Sequentially**: loads in memory and solves each stage sequentially. It takes a lot of time to load the problem in memory.

## Sector Benders decomposition

Solve the electric sector and the hydrogen sector separately, using Benders decomposition method (file `openTEPES_ProblemSolvingSectorDecomposition`).
