# Does the AC model work with the sweeps and the decompositions?

Audit of the AC branch against openTEPES's parallel run modes and its four decomposition paths. Sixth in
the series.

Short answer: **the sweeps are fine, three of the four decompositions are fine, and Benders has a real
caveat that is not new but that AC makes easier to hit.** Two reporting defects were found and fixed.

---

## 1. Why most of it works without being asked to

Almost every module in the solving layer enumerates the model generically rather than naming variables:

```
openTEPES_ProblemSolving.py:64              component_data_objects(Var, active=True)
openTEPES_ProblemSolvingDualExtraction.py   component_data_objects(Var) / component_objects(Constraint)
openTEPES_ProblemSolvingPersistent.py       component_data_objects(Var)
openTEPES_ProblemSolvingResolve.py          component_data_objects(Objective / Constraint)
openTEPES_ProblemSolvingWarmSweep.py        component_data_objects(Constraint)
openTEPES_ProblemSolvingStageIter.py        component_objects(Constraint)
```

New variables and constraints are therefore picked up automatically. This is the same property that made
the naming contracts of the architecture review pay off: `vW`, `vCurr`, `eBalanceReact` and the rest need
no registration anywhere.

## 2. Sweeps

| Mode | Mechanism | AC status |
| --- | --- | --- |
| A, pre-build | one process per case, serial / `multiprocessing` / `joblib` | **works** — each worker builds its own model |
| B, in-memory | baseline read once, `InMemorySource` + overlay, forked workers share frames copy-on-write | **works** — `materialize` iterates `list_data_stems()`, so `ReactiveDemand` and `BusShunt` are captured like any other table |
| C, re-solve | swap mutable `Param` values in a built model, no rebuild | **works**, with one trap below |

**Mode B note.** `materialize` captures every stem regardless of the option flags, so a DC run in Mode B
reads the reactive demand it will not use. The skip added in `InputData` only applies on the direct read
path. This costs memory, not correctness, and only when a DC case carries AC tables.

**Mode C trap, worth documenting for users.** `resolve` swaps mutable parameters by name and
`_live_mutable_params` rejects an overlay it cannot see, so a `pReactiveDemand` overlay works — the
parameter is declared mutable. But the obvious call

```python
overlay_scaled(model, "pDemandElec", 1.10)      # +10 % demand
```

scales the **active** demand only and silently changes the power factor at every node. Under DC that call
means what it says; under AC it does not. A sweep over demand should scale both, and the module docstring
already warns about build-derived dependents in the same spirit.

## 3. Decompositions

| Path | Complicating variable | AC status |
| --- | --- | --- |
| Stage decomposition | stage-linking state | **works** — generic |
| Sector decomposition | H2 / electricity coupling, reads `eBalanceElec` dual by string | **works** — the dual key was preserved on purpose (architecture review §3.1) |
| Warm sweep / persistent | re-pushes constraints touching a swapped param | **works**, but see §4 |
| **Benders** | **`vNetworkInvest` only, hardcoded** | **caveat, see below** |

### Benders

`openTEPES_ProblemSolvingBenders.py` pins `vNetworkInvest[k] == benders_x[k]` in the subproblem and takes
the dual of that fixing constraint as the cut subgradient. The AC investment variables — `vShuntInvest`
and `vSynchInvest` — are not complicating variables, so they stay in the subproblem.

That is **not wrong in itself**: the shunt decision simply becomes part of the recourse, and
`∂(eTotalSCost)/∂(vNetworkInvest)` is still the right subgradient. The caveat is the one classical Benders
always has — **the cut is only a valid subgradient if the subproblem is convex.** When
`IndBinNetInvest = 1` the shunt investment is binary, so the subproblem becomes a MIP and the dual of the
fixing constraint is no longer a subgradient of the true value function.

**This exposure is not new.** `vGenerationInvest` is already binary in the subproblem under
`IndBinGenInvest = 1`, so the same objection already applies to a case with candidate generators. AC adds
one more way to reach it, on a variable a user may not think of as an investment. Recorded rather than
guarded, because guarding it would also have to refuse existing configurations that predate this branch.

If Benders is to be used with AC reactive investment, the shunt and condenser decisions belong in the
master alongside `vNetworkInvest`.

## 4. The one genuinely untested combination

**Persistent solver with a second-order cone.** `openTEPES_ProblemSolvingPersistent.py` uses
`gurobi_persistent`, which adds and removes constraints incrementally. Pyomo's persistent interface does
handle quadratic constraints, but this branch has never exercised it: every AC solve so far has gone
through the plain `gurobi` interface. Under `IndACModelType = 1`, the piecewise model is a pure MILP and
the question does not arise — which is another reason the linear formulation is the sensible default.

Marked as untested rather than broken. It needs a run before anyone relies on it.

## 5. Two defects found by this audit, both fixed

**The summary's total investment cost omitted reactive compensation.**
`openTEPES_OutputResultsSummary.py:60` gated `vTotalFElecCost` on
`len(gc) + len(gd) + len(lc)`, so a case whose only candidate is a shunt or a condenser reported a total
investment cost of zero while the objective charged for it. The gate now admits AC candidates, and a
`ReactiveInvestmentCost` component was added to the breakdown ratios.

**`fix_for_duals` did not pin the AC investments.** The binary sweep it performs catches only
non-continuous variables; `vShuntInvest` and `vSynchInvest` are continuous whenever their binary flag is
off, so the fix-and-resolve pass that produces the locational marginal prices was free to revise the very
plan it was meant to price. Both are now fixed alongside the other investment variables.

## 6. What this leaves open

* Persistent solver plus cone: untested (§4).
* Benders with AC reactive investment: valid but weaker cuts when the flag is binary (§3).
* Mode B reads AC tables it may not need (§2), a memory cost only.
* A demand sweep under AC should scale active and reactive demand together (§2). This is a documentation
  item for `doc/md/`, not a code change — deciding for the user which power factor they meant would be
  worse than telling them.
