"""
SystemStatesExample_Benders_updated.py

Benders decomposition for a 1-unit, system‑states UC problem.
• Master: commitment (u_s), transitions (su, sd), fixed & startup/shutdown costs, + θ
• Subproblem: economic dispatch with unmet‑demand slack penalty → always feasible
• Recourse cut each iteration: θ >= dispatch_cost(u*)
"""

from pyomo.environ import *
from pyomo.opt import SolverFactory

# --- (1) DATA: system states, durations, net demands, transitions ---
states = [0, 1, 2, 3, 4, 5]
duration = {0: 1488, 1: 1426, 2: 1450, 3: 1413, 4: 1083, 5: 1900}
net_demand = {0: 2573.4, 1: 1500.6, 2: 2178.2, 3: 2023.7, 4: 1237.2, 5: 2902.1}
transition = {
    (0, 1): 200, (1, 2): 180, (2, 3): 170,
    (3, 4): 160, (4, 5): 150, (5, 0): 140
}

# --- (2) UNIT PARAMETERS ---
Pmin = 1000      # MW
Pmax = 3000      # MW
VarCost = 50     # €/MWh
StartupCost = 1000   # €
ShutdownCost = 800   # €
FixedCost = 200      # €/h committed

# --- (3) BENDERS CONFIG ---
max_iter = 15
tolerance = 1e-3
upper_bound = float('inf')
lower_bound = -float('inf')
benders_cuts = []   # each is (coeffs_dict, constant) but here we only use constant cuts

# Slack penalty for unmet demand (€/MWh)
penalty = 1e6

# --- (4) BENDERS LOOP ---
for iteration in range(1, max_iter+1):
    print(f"\n=== Benders Iteration {iteration} ===")
    # ---- Master Problem ----
    M = ConcreteModel()
    M.S = Set(initialize=states)
    M.T = Set(initialize=transition.keys(), dimen=2)

    # Decision vars
    M.u  = Var(M.S, within=Binary)
    M.su = Var(M.T, within=Binary)
    M.sd = Var(M.T, within=Binary)
    M.theta = Var(within=NonNegativeReals)

    # Objective: fixed + su/sd + θ
    def master_obj(m):
        cost_su = sum(StartupCost   * transition[t] * m.su[t] for t in m.T)
        cost_sd = sum(ShutdownCost  * transition[t] * m.sd[t] for t in m.T)
        cost_fix= sum(duration[s] * FixedCost    * m.u[s] for s in m.S)
        return cost_su + cost_sd + cost_fix + m.theta
    M.OBJ = Objective(rule=master_obj, sense=minimize)

    # Transition logic
    def link_rule(m, s1, s2):
        return m.u[s2] - m.u[s1] == m.su[(s1,s2)] - m.sd[(s1,s2)]
    M.trans = Constraint(M.T, rule=link_rule)

    # Force at least one on
    def at_least_one(m):
        return sum(m.u[s] for s in m.S) >= 1
    M.minOn = Constraint(rule=at_least_one)

    # Add all Benders cuts: here θ >= constant_cut
    for idx, (_, const) in enumerate(benders_cuts, start=1):
        setattr(M, f"cut_{idx}",
            Constraint(expr=M.theta >= const)
        )

    # Solve master
    SolverFactory('gurobi').solve(M, tee=False)
    u_sol = {s: int(round(value(M.u[s]))) for s in states}
    lower_bound = value(M.OBJ)
    print(" Master u* =", u_sol)
    print(f" Master obj (LB) = €{lower_bound:,.2f}")

    # ---- Subproblem: dispatch with slack penalty ----
    dispatch_cost = 0.0
    for s in states:
        nd = net_demand[s]
        dur = duration[s]
        if u_sol[s] == 0:
            # entirely unmet → penalty
            dispatch_cost += dur * penalty * nd
        else:
            # committed → attempt to serve
            if nd < Pmin:
                short = Pmin - nd
                dispatch_cost += dur*(VarCost * nd + penalty * short)
            elif nd > Pmax:
                ovf = nd - Pmax
                dispatch_cost += dur*(VarCost * Pmax + penalty * ovf)
            else:
                dispatch_cost += dur*(VarCost * nd)

    # Update UB
    candidate_UB = lower_bound - value(M.theta) + dispatch_cost
    upper_bound = min(upper_bound, candidate_UB)
    gap = abs(upper_bound - lower_bound)
    print(f" Subproblem recourse cost = €{dispatch_cost:,.2f}")
    print(f" Candidate UB = €{candidate_UB:,.2f}, Gap = €{gap:.2f}")

    # ---- Add Benders cut: θ >= dispatch_cost(u*) ----
    benders_cuts.append(({}, dispatch_cost))

    # Check convergence
    if gap <= tolerance:
        print(">>> Converged!")
        break

# --- (5) FINAL REPORT ---
print("\n=== FINAL RESULTS ===")
status = "optimal" if gap <= tolerance else "stopped"
print(" Status:        ", status)
print(" Iterations:    ", iteration)
print(" Lower bound:   €", round(lower_bound,2))
print(" Upper bound:   €", round(upper_bound,2))
print(" Final u*       ", u_sol)
