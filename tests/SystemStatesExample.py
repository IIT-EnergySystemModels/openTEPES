from pyomo.environ import *
from pyomo.opt import SolverFactory

# ----- Data -----

states = [1, 2, 3, 4, 5, 6]

# Duration of each state in hours
duration = {1: 20, 2: 30, 3: 40, 4: 25, 5: 30, 6: 23}

# Net demand in each state (MW)
net_demand = {1: 80, 2: 60, 3: 70, 4: 50, 5: 65, 6: 75}

# Transition matrix (state_from, state_to): number of transitions
transition = {
    (1, 2): 5, (2, 3): 4, (3, 4): 3, (4, 5): 6, (5, 6): 5,
    (6, 1): 2  # simple loop
}

# Generator characteristics
Pmin = 30   # MW
Pmax = 100  # MW
VarCost = 50     # €/MWh
StartupCost = 1000  # €
ShutdownCost = 800  # €
FixedCost = 200     # €/h when committed

# ----- Model -----

model = ConcreteModel()

model.S = Set(initialize=states)
model.Trans = Set(initialize=transition.keys(), dimen=2)

# Decision variables
model.u = Var(model.S, within=Binary)  # commitment
model.p = Var(model.S, within=NonNegativeReals)  # production
model.su = Var(model.Trans, within=Binary)  # startup
model.sd = Var(model.Trans, within=Binary)  # shutdown

# Objective: minimize total cost
def obj_expression(m):
    prod_cost = sum(duration[s] * (VarCost * m.p[s] + FixedCost * m.u[s]) for s in m.S)
    su_cost = sum(StartupCost * transition[s] * m.su[s] for s in m.Trans)
    sd_cost = sum(ShutdownCost * transition[s] * m.sd[s] for s in m.Trans)
    return prod_cost + su_cost + sd_cost

model.obj = Objective(rule=obj_expression, sense=minimize)

# Power balance: generator must meet net demand
def power_balance(m, s):
    return m.p[s] == net_demand[s]

model.balance = Constraint(model.S, rule=power_balance)

# Generator limits
def prod_limit_upper(m, s):
    return m.p[s] <= m.u[s] * Pmax

def prod_limit_lower(m, s):
    return m.p[s] >= m.u[s] * Pmin

model.limit_upper = Constraint(model.S, rule=prod_limit_upper)
model.limit_lower = Constraint(model.S, rule=prod_limit_lower)

# Startup/shutdown logic via transitions
def startup_shutdown_link(m, s_from, s_to):
    return m.u[s_to] - m.u[s_from] == m.su[(s_from, s_to)] - m.sd[(s_from, s_to)]

model.startstop = Constraint(model.Trans, rule=startup_shutdown_link)

# ----- Solve -----

solver = SolverFactory('gurobi')
results = solver.solve(model, tee=True)

# ----- Output -----

print("\n=== Solution ===")
for s in states:
    print(f"State {s}: Committed = {value(model.u[s])}, Production = {value(model.p[s]):.2f} MW")

for s_from, s_to in transition:
    if value(model.su[(s_from, s_to)]) > 0.5 or value(model.sd[(s_from, s_to)]) > 0.5:
        print(f"Transition {s_from}->{s_to}: SU={value(model.su[(s_from, s_to)])}, SD={value(model.sd[(s_from, s_to)])}")
