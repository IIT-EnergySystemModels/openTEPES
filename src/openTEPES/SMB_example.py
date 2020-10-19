import pyomo.environ as pyo

block_1 = pyo.Block()
block_1.x = pyo.Var(bounds=(0,3))
block_1.p = pyo.Param(initialize=5)

block_2 = pyo.Block()
block_2.x = pyo.Var(bounds=(2,5))
block_2.p = pyo.Param(initialize=-2)

block_3 = pyo.Block()
block_3.block_1 = block_1
block_3.block_2 = block_2

def expr(b):
    return b.block_1.x * b.block_1.p + b.block_2.x * b.block_2.p
block_3.expr = pyo.Expression(rule=expr)

model = pyo.ConcreteModel()
model.block_3 = block_3

def obj_expr(m):
    return m.block_3.expr
model.obj = pyo.Objective(rule=obj_expr)

opt = pyo.SolverFactory("glpk")
opt.solve(model)

print(pyo.value(model.block_3.block_1.x))
print(pyo.value(model.block_3.block_2.x))