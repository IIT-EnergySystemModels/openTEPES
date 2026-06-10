# openTEPES — Local Know-How

## Solver tuning for large-scale stochastic LPs (Gurobi)

When solving **large, degenerate joint stochastic LPs** (e.g. the Nordic H2-extended multi-scenario cases), the default `Crossover=-1` causes either infinite cycling or a blowup on a single bad pivot after barrier convergence. Apply the following Gurobi options in `openTEPES_ProblemSolving.py` before running:

```python
Solver.options['Method'        ] =  2   # barrier (already set for LP/stochastic branch)
Solver.options['Crossover'     ] =  0   # disable crossover; accept barrier interior point
Solver.options['ScaleFlag'     ] =  2   # aggressive scaling
Solver.options['BarHomogeneous'] =  1   # homogeneous barrier — more robust on degenerate problems
Solver.options['NumericFocus'  ] =  2   # medium numerical care
```

**Why Crossover=0 is acceptable:** Barrier converges to gap ~1e-9 (wall time ~50 min on the Nordic cases). Disabling crossover accepts the interior-point solution — primal/dual *objective* is exact, but the duals are interior-point estimates rather than vertex duals. `EconomicResults` uses these duals as locational marginal prices; the interior-point LMPs are within `MIPGap` tolerance of exact simplex LMPs.

**This change is NOT upstreamed** — it is specific to numerically challenging large-scale cases and should not be committed to the openTEPES repository.
