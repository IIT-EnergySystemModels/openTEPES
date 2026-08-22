# Fitting AC power flow into the openTEPES architecture

Written before Phase 2, to settle how the AC model attaches to the rest of the code rather than
discovering it constraint by constraint. Companion to `AC_OPF_Implementation_Plan.md`.

---

## 1. The architecture as it stands

The package is six layers, and the split is clean:

| Layer | Modules | Job |
| --- | --- | --- |
| 1 Input | `InputSchema`, `InputSource`, `InputCSVSource`, `InputDuckDBSource`, `InMemorySource`, `InputData` | read tables into `dfs` / `par` |
| 2 Configure | `DataConfiguration` | turn `dfs` / `par` into Pyomo sets and parameters |
| 3 Variables | `SettingUpVariables` | declare every variable, once, globally |
| 4 Formulate | `ModelFormulationObjective`, `…Investment`, `…Electricity`, `…Hydro`, `…Hydrogen`, `…Heat` | declare constraints, per `(p, sc, st)` |
| 5 Solve | `ProblemSolving*` (11 modules) | solve, decompose, extract duals |
| 6 Output | `OutputResults*` (12 modules) | write results |

Two things about it are worth naming, because they decide the AC design.

**The input layer is genuinely extensible.** `TABLE_SPECS` in `openTEPES_InputSchema.py` is a single
catalogue that CSV, DuckDB and the in-memory backend all read. Phase 1 added two tables there and
needed no backend change at all — the DuckDB round-trip test passed on the new case first try.
Nothing else in the codebase is this clean.

**Everything above layer 2 dispatches by hand.** `StageIterativeSolving` is an if-ladder of eleven
formulation calls. `ProblemSolving` prints the investment cost summary from a block that is
duplicated verbatim for the two `NoRepetition` branches. `SettingUpVariables` is a single function
of 1,231 lines. Adding a sector means editing all of it.

The one exception is `OUTPUT_REGISTRY` in `openTEPES.py:78` — a tuple of
`(category, writer, extra_args, guard)` rows. It is the newest extension point and it is the right
shape. AC results should be one row in it.

## 2. Why AC is not another sector

Hydrogen, heat and hydro topology are **additive**. Each brings a new carrier, a new balance
equation at the node, a new pipe network, and new variables that nothing else reads. Their flags
touch about eleven files each, but every touch is an `if` that adds something.

AC is **substitutive**. It does not add a carrier; it replaces the physics of the one that is
already there. The same nodes, the same balance, the same lines, the same flows — computed
differently. So the interesting question is not "where do I add?" but "what am I about to break?"

Grepping for it gives a clear answer.

## 3. Three naming contracts that must not be broken

### 3.1 `eBalanceElec` is read by string in ten places

`collect_duals` stores every dual as `str(constraint.name) + str(index)`
(`openTEPES_ProblemSolvingDualExtraction.py:132`). Downstream code then reads it back by
reconstructing that string:

```python
mTEPES.pDuals[f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"]
```

That literal appears in `OutputResultsEconomic.py` (lines 99, 451, 454, 642, 654, 669, 673),
`OutputResultsSummary.py:96`, and `ProblemSolvingSectorDecomposition.py:378`. It carries the
locational marginal price, every generator and storage revenue figure, and the electrolyser
marginal that drives the Benders cut in the sector decomposition.

**Decision: the AC active-power balance keeps the name `eBalanceElec` and the index `(n, nd)`.**
Not `eBalanceElecAC`. The rule body branches on `pIndACPowerFlow`; the constraint identity does
not change. Ten call sites keep working, LMPs stay LMPs, and the sector decomposition does not
need to know the network is AC.

A new constraint `eBalanceReact` is genuinely additive and can be named freely.

### 3.2 `vFlowElec` is read in eight places as "the active power flow on the line"

`OutputResultsNetwork.py` (42, 156, 220, 261), `OutputResultsSummary.py` (227, 228, 294),
`OutputResultsEconomic.py` (414, 415). Line-flow tables, net position per area, the network map
hover text, energy in/out per node.

The reference implementation in openTEPES_PRO introduces `vPfr` / `vPto` and leaves `vFlowElec`
behind, which is why it also has to ship its own parallel copy of every output module —
`openTEPES_OutputResults_AC_BusInj.py` is 91 KB of largely duplicated reporting code.

**Decision: `vFlowElec[p,sc,n,ni,nf,cc]` keeps meaning the active power flow leaving `ni` towards
`nf`.** In DC that is the whole story. In AC it is the sending-end flow, and a new
`vFlowElecBck` holds the receiving-end flow. Eight call sites keep working and keep meaning the
right thing, and we do not fork the output layer.

New: `vFlowElecBck`, `vFlowReactFrw`, `vFlowReactBck`.

### 3.3 `vLineLosses` is half the losses, and `mTEPES.ll` gates every loss report

`vLineLosses` is documented as *half* line losses (`SettingUpVariables.py:369`) and
`OutputResultsNetwork.py:98` multiplies by 2 to report the whole. The set `mTEPES.ll` — lines with
a positive loss factor, when `pIndBinNetLosses` is on — gates the loss reporting in
`OutputResultsEconomic.py` (319, 416, 429, 485, 493), `OutputResultsSummary.py` (37, 229-231) and
the losses penalty in the objective (`ModelFormulationObjective.py:113-115`).

In AC mode losses are not a loss factor, they are `P_ij + P_ji`. Rather than write a separate AC
loss report:

**Decision: in AC mode, `mTEPES.ll` becomes `mTEPES.laa` (every AC line has real losses), and
`vLineLosses` is defined by an equality**

```
vLineLosses[ni,nf,cc] == 0.5 * (vFlowElec[ni,nf,cc] + vFlowElecBck[ni,nf,cc])
```

which preserves the half-losses convention exactly. Every existing loss table then reports true
AC losses with no change to any output module.

Two consequences to handle deliberately:

- `eLineLosses1` / `eLineLosses2` must be skipped when AC is on, or the loss-factor inequalities
  fight the equality above.
- `vTotalNCost` prices losses at `pEpsilonLosses = 1e-5` so the solver cannot leave the DC loss
  inequality slack (`ModelFormulationObjective.py:33, 115`). Under an equality there is no slack
  to squeeze, so that penalty is no longer doing a job and should be zero in AC mode. Leaving it
  in adds a small, undocumented bias to the objective.

## 4. What this buys

Following the three contracts, the output layer needs **one new module and one registry row**,
instead of the parallel universe openTEPES_PRO ended up with:

| | openTEPES_PRO approach | Contract-preserving approach |
| --- | --- | --- |
| Output modules | 2 new files, 194 KB, duplicating the DC reporting | 1 new file for voltage / reactive tables |
| `openTEPES.py` | separate dispatch branch | 1 row in `OUTPUT_REGISTRY`, 1 entry in `OUTPUT_CATEGORIES` |
| LMP / revenue code | reimplemented | untouched |
| Sector decomposition | untouched but unaware | works as-is |

## 5. Full extension inventory

Everything AC needs, across the whole package. Phase numbers refer to the implementation plan.

### Layer 1 — Input · done

| File | Change | Status |
| --- | --- | --- |
| `openTEPES_InputSchema.py` | 2 `TABLE_SPECS` rows, `Shunt` in `DEFAULT_IDX_COLS` | done |
| `openTEPES_InputData.py` | flag defaults, AC-only stem skip, `pRMinReactivePower`, call `ReadACInputData` | done |
| `openTEPES_InputDataAC.py` | new | done |
| `InputCSVSource` / `InputDuckDBSource` / `InMemorySource` | **none** — all spec-driven | verified |
| `_input_parity_test.py` | **none** — walks components generically | verified |

### Layer 2 — Configure

| File | Change | Phase |
| --- | --- | --- |
| `openTEPES_DataConfiguration.py` | call `ConfigureACData`, 2 indicator params | done |
| `openTEPES_DataConfiguration.py` | `ll := laa` when AC is on | 3 |
| `openTEPES_DataConfiguration.py` | widen the `g` filter so a zero-MW synchronous condenser survives | 5 |

### Layer 3 — Variables

| File | Change | Phase |
| --- | --- | --- |
| `openTEPES_SettingUpVariablesAC.py` | new: `vW`, `vWC`, `vWS`, `vFlowElecBck`, `vFlowReactFrw/Bck`, `vReactiveTotalOutput`, `vQShunt`, `vShuntInvest` | 2 |
| `openTEPES_SettingUpVariables.py` | one guarded call out to it; leave the other 1,231 lines alone | 2 |

### Layer 4 — Formulate

| File | Change | Phase |
| --- | --- | --- |
| `openTEPES_ModelFormulationAC.py` | new: flow equations, reactive balance, apparent-power limit, shunt injection, `eCPolar`/`eSPolar`, SOCP swap | 3-4 |
| `openTEPES_ModelFormulationElectricity.py` | `eBalanceElec` gains an AC branch; `eKirchhoff2ndLaw1/2` and `eLineLosses1/2` skip when AC | 3 |
| `openTEPES_ModelFormulationObjective.py` | `pEpsilonLosses` = 0 in AC mode; reactive ENS if modelled | 3 |
| `openTEPES_ModelFormulationInvestment.py` | shunt investment into `eTotalFElecCost` | 5 |
| `openTEPES_ProblemSolvingStageIter.py` | dispatch the AC formulation | 3 |

### Layer 5 — Solve

| File | Change | Phase |
| --- | --- | --- |
| `openTEPES_ProblemSolvingTuning.py` | **none for SOCP** — `Method=2` (barrier) and `MIPGap=0.01` are already right; ipopt needs its own path | 7 |
| `openTEPES_ProblemSolvingDualExtraction.py` | fix `vShuntInvest` alongside the other investment variables | 5 |
| `openTEPES_ProblemSolving.py` | shunt line in the cost summary — **in two places**, the block is duplicated | 5 |
| `openTEPES_ProblemSolvingSectorDecomposition.py` | **none**, given contract 3.1 | verified |
| `openTEPES_ProblemSolvingStageDecomposition.py`, `Benders`, `WarmSweep`, `Persistent`, `Resolve` | **none** | verified |

### Layer 6 — Output

| File | Change | Phase |
| --- | --- | --- |
| `openTEPES_OutputResultsAC.py` | new: voltage magnitude and angle, reactive flows, reactive marginal, cone violation | 6 |
| `openTEPES.py` | 1 `OUTPUT_CATEGORIES` entry, 1 `OUTPUT_REGISTRY` row | 6 |
| `openTEPES_OutputResultsNetwork.py` / `Economic` / `Summary` | **none**, given contracts 3.1-3.3 | — |

### Docs and tests

`doc/md/InputData.md`, `doc/md/MathematicalFormulation.md`, `doc/md/OutputResults.md`;
`tests/test_ac_input.py` (done), plus a formulation test and the MATPOWER cross-check.

**Total: 4 new modules, 8 edited, ~20 files untouched that a naive port would have forked.**

## 6. Should anything be refactored first?

Three candidates. My recommendation differs for each.

**`SettingUpVariables` (1,231 lines, one function) — do not refactor now.** It is the obvious
target, but splitting it is a large diff across code that every case depends on, and it would land
in the same branch as the AC model. If a case moves, nobody could say which change did it. Add the
AC variables as one guarded call into a new module and leave the rest.

**The formulation if-ladder in `StageIterativeSolving` — worth a small registry, and it pays for
itself here.** Eleven hardcoded calls, and AC adds branching to three of them. A
`FORMULATION_REGISTRY` shaped like `OUTPUT_REGISTRY` — `(name, fn, guard)` — turns the ladder into
data, makes AC one row, and gives the next sector the same. This is roughly a 30-line change and
it is the one refactor I would do inside this branch.

**The duplicated cost-summary block in `ProblemSolving.py` — worth fixing, but not here.** The two
`NoRepetition` branches print the same eleven lines with different index variables, so Phase 5 must
add the shunt cost twice. An `INVESTMENT_REGISTRY` of `(label, set, cost param, variable, index
set)` would collapse both branches, `eTotalICost`, and the `fix_for_duals` enumeration into one
list. But it touches working financial reporting, and an AC branch is the wrong place to risk that.
**Propose it as a separate PR after AC lands.**

## 7. What changes in the plan

Revisions to `AC_OPF_Implementation_Plan.md` Phase 2-3:

- No `vPfr` / `vPto`. Reuse `vFlowElec`, add `vFlowElecBck`.
- No `eBalanceElecAC`. `eBalanceElec` gains an AC branch and keeps its name.
- `vLineLosses` is kept and defined exactly; `ll` widens to `laa` in AC mode.
- The shunt reactive injection variable is `vQShunt`, indexed on the `psnsh` set Phase 1 already
  built.
- Voltage magnitude enters as `vW = |V|^2` bounded on `[VMin^2, VMax^2]`. There is no separate
  `vVoltage`; the square root belongs in the output layer, not in the model.

## 8. One risk this review did not remove

Contracts 3.1 and 3.2 keep the existing output code running, but "running" is not "correct". Two
reports will silently change meaning under AC and need checking in Phase 6:

- `PowerFlowIn` / `PowerFlowOut` per node (`OutputResultsSummary.py:227-228`) sum `vFlowElec` at
  both ends of the incoming lines. Under AC the incoming flow is `vFlowElecBck`, so the in-figure
  will be the sending-end value and miss the line losses. It is the same approximation the DC model
  already makes, but it should be stated, not inherited by accident.
- The network map colours lines by `vFlowElec` against `NTCFrw` (`OutputResultsNetwork.py:220`).
  Under AC the binding limit is apparent power, so a line at 100 % of its MVA rating can show well
  under 100 % utilisation. The map needs the apparent-power rating in AC mode.

---

# 9. What the other open-source models do

Checked against four codebases: PowerModels.jl (LANL, the reference for AC relaxations), Egret
(Sandia/ANL — the closest analogue, Python + Pyomo), PyPSA 1.2.4 and pandapower 3.5.4 (both read
from the local install, not from memory).

## 9.1 The composition pattern is unanimous

All three optimisation codebases separate **what to build** from **which physics to build it
with**, and none of them puts a formulation switch inside a constraint generator.

**PowerModels.jl** does it with Julia multiple dispatch. `build_opf` is written once and calls
`variable_bus_voltage(pm)`, `constraint_power_balance(pm, i)`, `constraint_ohms_yt_from(pm, i)`.
Each formulation type — `ACPPowerModel` (polar), `ACRPowerModel` (rectangular), `SOCWRPowerModel`
(W-space SOC), `QCRMPowerModel`, `DCPPowerModel`, `SOCBFPowerModel` (branch flow) — supplies its
own methods. The problem (OPF, PF, OTS, TNEP) is orthogonal to the formulation.

**Egret** — the most directly transplantable, since it is Pyomo — uses a library of `declare_*`
functions in `egret/model_library/transmission/branch.py`, composed by model files:

```
declare_eq_branch_power_btheta_approx(...)   # DC
declare_eq_branch_power(...)                 # AC
declare_var_c(), declare_var_s()             # the voltage products
declare_eq_c(), declare_eq_s()               # their defining equations
declare_ineq_soc(...)                        # the conic relaxation
```

Note `declare_var_c` / `declare_var_s` — Egret independently arrived at the same C/S voltage-product
structure we took from openTEPES_PRO, which is reassuring about the formulation choice.

**PyPSA** composes a flat sequence of `define_*` calls in `optimization/optimize.py:create_model`,
with option branching at the composition level (`if transmission_losses: … mode "secants" /
"tangents"`), never inside the builders.

**The lesson for openTEPES.** The existing rules test flags *inside* the rule —
`eKirchhoff2ndLaw1` opens with `if mTEPES.pIndBinSingleNode() or mTEPES.pIndPTDF() or …:
return Constraint.Skip`. Those are mutable-Param `__call__`s evaluated once per index. On NG2030
at 8,736 load levels × 163 lines that is 1.4 M evaluations of a value that cannot change during
the build.

**Decision: choose the rule function once, outside the rule.** This composes with contract 3.1
rather than fighting it — the constraint keeps the name `eBalanceElec`, only the rule bound to it
differs:

```python
rule = _eBalanceElecAC if mTEPES.pIndACPowerFlow() else _eBalanceElecDC
setattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=rule, ...))
```

The dual key is unchanged, ten call sites keep working, and the per-element flag test is gone.

## 9.2 The W-space variables belong to the bus pair, not the branch

The most valuable finding. PowerModels indexes the voltage-product variables on bus pairs:

```julia
wr = var(pm, nw)[:wr] = JuMP.@variable(pm.model, [bp in ids(pm, nw, :buspairs)], ...)
...
for (i,j) in ids(pm, n, :buspairs)
    _IM.relaxation_complex_product(pm.model, w[i], w[j], wr[(i,j)], wi[(i,j)])
end
```

This is right on physics, not just on size: `|Vi||Vj|cos(θi−θj)` is a property of the *pair of
buses*, so two parallel circuits between the same pair share one value. openTEPES indexes lines on
`(ni, nf, cc)`, so a per-branch `vWC` / `vWS` would create duplicate variables and — worse — let
the relaxation assign *different* voltage products to parallel circuits, which is physically
impossible and therefore a strictly weaker bound.

Counting the bundled cases, with a canonical (sorted) pair key:

| Case | AC branches | Canonical bus pairs | Reduction |
| --- | ---: | ---: | ---: |
| 9n | 12 | 12 | 0.0 % |
| RTS24 | 38 | 34 | 10.5 % |
| RTS-GMLC | 104 | 92 | 11.5 % |
| sSEP | 24 | 16 | 33.3 % |
| **NG2030** | **163** | **76** | **53.4 %** |

Per load level that is 53 % fewer second-order cones on the largest bundled case — the cone is the
expensive constraint in a MISOCP — and a tighter relaxation at the same time.

**One trap.** NG2030 has 26 bus pairs whose branches appear in *both* orientations, `(A,B)` and
`(B,A)`. The pair key must therefore be canonical (sorted), and each branch must carry its
orientation, because `vWS` is antisymmetric: `vWS(B,A) = −vWS(A,B)` while `vWC` is symmetric. A
naive `(ni,nf)` key would silently create two independent variables for one physical quantity.

**Decision: add a canonical bus-pair set `bp` and index `vWC` / `vWS` on it, with a per-branch
orientation sign.**

## 9.3 The branch pi-model, settled against PYPOWER

`pandapower/pypower/makeYbus.py:108-112` is the reference implementation everyone derives from:

```python
Ytt = Yst + Bct / 2
Yff = (Ysf + Bcf / 2) / (tap * conj(tap))
Yft = - Ysf / conj(tap)
Ytf = - Yst / tap
```

with `tap = ratio · e^{j·shift}`. Three confirmations and one gap:

* **`b_c/2` at each end** — the Phase 1 decision to treat `Susceptance` as the *total* charging
  susceptance and halve it in the constraints matches MATPOWER, PYPOWER, pandapower and PyPSA.
* **`tap²` on the from-side diagonal, `tap` on the off-diagonals** — the openTEPES_PRO algebra
  (`pLineTAP**2 * vW[ni]`, `pLineTAP * vWC`) is correct, which is worth saying plainly: only its
  computation of the tap *value* was broken, not the equations built from it.
* **The charging is divided by `tap²` too** on the from side. Easy to miss; included.
* **Gap: openTEPES has no phase-shift column.** With `shift = 0`, `Yft` and `Ytf` collapse to the
  same value, which is what the current Network table implies. A phase-shifting transformer cannot
  be represented. pandapower also carries an explicit `parallel` multiplier that openTEPES handles
  through the `cc` circuit index instead. Recorded as future work, not Phase 2.

## 9.4 What was deliberately not copied

* **PyPSA's tangent/secant loss cuts.** Sensible for a linear model that has no other way to price
  losses. Under the AC formulation losses come out of `vFlowElec + vFlowElecBck` exactly, so the
  cuts would be a worse approximation of something already available.
* **PowerModels' full formulation-type hierarchy.** Python has no multiple dispatch, and an
  abstract-base-class tower would be more machinery than two formulations justify. The registry in
  §9.1 plus Egret-style declare functions gets the same separation at a fraction of the weight.
* **pandapower's Ybus assembly.** It is built for a Newton-Raphson solve on a numeric matrix; an
  optimisation model needs the per-branch algebraic form.

## 9.5 Revised decisions carried into Phase 2

1. Canonical bus-pair set `bp`, with `vWC` / `vWS` indexed on it and a per-branch orientation sign.
2. Formulation chosen once at composition time; no flag tests inside Pyomo rules.
3. `FORMULATION_REGISTRY` in `StageIterativeSolving`, mirroring `OUTPUT_REGISTRY`.
4. Everything in §3 (the three naming contracts) stands unchanged.
