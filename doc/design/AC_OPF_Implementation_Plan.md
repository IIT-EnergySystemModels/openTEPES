# AC optimal power flow in openTEPES — implementation plan

Branch: `feature/ac-opf`

**Status: Phases 0–6 built. Under review — a code review on 2026-08-19 returned 12 findings, and the fixes are in
progress. Phase 7 needs ipopt, which is not installed here.**

This document was rewritten on 2026-08-19. The first version planned a bus-injection W-space model taken
from `openTEPES_PRO`. Reading the two reference papers changed that to a **branch flow model**, and running
prototypes changed the priority order. The history is in the companion documents; this one describes what is
actually being built.

| Document | What it settles |
| --- | --- |
| `AC_OPF_Architecture_Review.md` | how the AC model attaches to the rest of the package |
| `AC_OPF_Formulation_Choices.md` | which formulations to carry, and why not the others |
| `AC_OPF_Prototype_Results.md` | measured accuracy and CPU, on which the priorities rest |
| **this file** | the formulation being implemented, the phases, and what is left |

---

## 1. What is being built

A **branch flow AC optimal power flow**, following Chowdhury, Kamalasadan & Paudyal (*IEEE Trans. Power
Systems* 39(1):1032-1043, 2024) as embedded in expansion planning by Alvarez, López, Olmos & Ramos
(*SEGAN* 39:101413, 2024).

Variables, all per unit on `pSBase`:

| symbol | model name | meaning |
| --- | --- | --- |
| `u_i` | `vW[nd]` | squared voltage magnitude at the bus |
| `l_ij` | `vCurr[la]` | squared current magnitude through the branch |
| `P_ij` | `vFlowElec[la]` | active power entering the branch at `ni` — **the DC model's variable, unchanged** |
| `P_ji` | `vFlowElecBck[la]` | active power entering at `nf`; `P_ij + P_ji` is the loss |
| `Q_ij`, `Q_ji` | `vFlowReactFrw/Bck[la]` | the reactive counterparts |
| `θ_i` | `vTheta[nd]` | voltage angle, already declared by the DC model |

Constraints, numbered as in Chowdhury et al.:

```
(9)       u_j = u_i − 2(r·P + x·Q) + (r²+x²)·l                        voltage drop
(11)      generation − demand = Σ P_out + Σ P_in                       active balance   → eBalanceElec
(12)      the reactive counterpart, with line charging and shunts      reactive balance → eBalanceReact
(13)      l = (P² + Q²) / u                                            NON-CONVEX — Phase 4
(16)(17)  θ_ij bounded by an envelope linear in P and Q                angle envelope
(6a-c)    q_shunt = B_sh · u, disjunctive for candidates               shunt injection
(7)       l ≤ (Smax / Vmin)²                                           thermal limit
```

The angle-to-flow relation is written **`|V_i||V_j| sin(θ_ij) = x·P + r·Q`** with the sign given explicitly.
Deriving it through the admittance matrix invites an error: the off-diagonal entry carries the opposite sign
to the series admittance, and the two conventions differ by exactly a minus. The form above was checked
against an exact AC power flow — for a lossless branch it collapses to `θ = x·P`, matching DC power flow. It
holds for the **series** flow, which is what this model carries; the line charging is lumped at the buses.

Because `M = x·P + r·Q` is linear in the flows, the envelope (16)-(17) is linear. It is what ties the angles
to the flows, and with `vTheta` kept as an explicit variable it is the whole of Kirchhoff's voltage law.

**The cyclic constraint (15) is deliberately not built.** Chowdhury et al. and Alvarez et al. impose it because
they ELIMINATE the angles and write the cycle sums on the flows, for compactness. With explicit angles the sum
round any closed cycle telescopes to zero identically, so the constraint is `0 == 0` on every cycle and every
load level — it was built here at first and was exactly that. Eliminating `vTheta` in favour of the cycle form
is the natural next compactness step; until then there is nothing for a cyclic constraint to add.

`M` also needs care with its sign: the envelope divides it by the voltage product, and the extreme of that
quotient is at the small end of the voltage band when `M > 0` and the large end when `M < 0`. A single divisor
cannot serve both, so `M` is split into non-negative parts. Getting this wrong makes the two envelope bounds
cross and the model infeasible for any reverse flow, which is how it shipped first.

## 2. The three model types

`IndACModelType` in `oT_Data_Option`, all sharing every equation above and differing only in how (13) is
supplied:

| value | name | (13) becomes | class | role |
| --- | --- | --- | --- | --- |
| 0 | SOCP | `u_i + l ≥ ‖[2P, 2Q, u_i − l]‖₂` | MISOCP | the only variant returning a **valid bound** |
| 1 | piecewise linear | staircase on the square terms | **MILP** | **the workhorse** — the only one that scales to a full year |
| 2 | exact NLP | `l = (P² + Q²) / u` | NLP | validation pass with the binaries fixed |

Ordering follows the measurement, not preference. `AC_OPF_Prototype_Results.md` §8 found the SOCP ahead only
at one or two periods; from four periods the piecewise model wins, and by eight neither closes in 300 s. For
the horizons openTEPES targets the linearisation is the right default; the SOCP's distinct value is that it
is the only variant whose objective is a bound, so it is what to quote a plan's optimality against, computed
on a handful of snapshots.

**Not built, with reasons:** SDP (does not scale with binaries), the bus-injection SOCP (Bose & Low prove the
same bound as the branch-flow one), IVR, NFA, rectangular ACR. **Deferred:** QC as a tightening on the SOCP.

## 3. Bound tightening is part of the formulation, not an optimisation

`openTEPES_BoundTightening.py`, run before the variables are declared. Two propagations, each using only
inequalities the model already implies, so neither can cut off the true optimum:

* **Angle, from the thermal limit.** The model implies `P² + Q² ≤ (Smax·Vmax/Vmin)²` — the thermal limit is
  written on the current, `l ≤ (Smax/Vmin)²`, and the cone gives `P² + Q² ≤ vW·l`. Cauchy-Schwarz then gives
  `|x·P + r·Q| ≤ S·z`, so `|θ_ij| ≤ arcsin(min(1, S·z / Vmin²))` with `S = Smax·Vmax/Vmin / pSBase`. **Both the
  `/pSBase` and the `Vmax/Vmin` were missing at first**, which is what made the bound ten times too tight on a
  100 MVA base.
* **Voltage, from the drop equation**, swept to a fixed point outwards from the reference bus.

Measured effect:

| case | branches tightened | median bound | median envelope slack | worst-branch slack |
| --- | --- | ---: | --- | --- |
| `9n_AC` | 12/12, from ±30° | **2.36°** | 0.352° → 0.00017° (**2100×**) | 513× |
| `RTS-GMLC_AC` | 120/120, from ±60° | **17.23°** | 3.080° → 0.0655° (**47×**) | **3.5×** |

An earlier version of these figures — a 1.54° median on RTS-GMLC and a slack improvement of some three orders of
magnitude on both cases — was wrong. The tightening dropped the `/pSBase` conversion, so on a 100 MVA base it reported a
bound **ten times tighter than the model implies**: a restriction that could cut off the true optimum, which is exactly
what the module exists to avoid. It also used `Smax` where the model only implies `Smax·Vmax/Vmin`. Both are corrected
above. The tightening is still worth doing — 47× on the median branch — but it is not the transformation first claimed,
and on the worst branch of RTS-GMLC it is only 3.5×.

Validity checked on 9n against the true AC optimum: no branch violated the tightened bound. That check was run
against the earlier, over-tight version, so it is a weaker statement than it looks — the corrected bound is
strictly looser and therefore still valid, but the check should be re-run.

Arbitrarily tightening instead of deducing turns the relaxation into a restriction. Measured on RTS-GMLC,
forcing ±30° raised the objective 108 % and ±20° made it infeasible.

## 4. Phases

| Phase | Contents | Status |
| --- | --- | --- |
| 0 | Module scaffolding, `TABLE_SPECS` entries, option flags | **done** |
| 1 | Reactive demand, shunts, voltage limits, derived branch model | **done** |
| 2 | Branch-flow variables, bounds from the tightening | **done** |
| 3 | Shared network block, cycles, envelope, bound tightening | **done** |
| 4 | Equation (13): the cone and the piecewise linearisation | **done** |
| 5 | Shunt and synchronous-condenser investment | **done** |
| 6 | Results, including the relaxation-gap diagnostic | **done** |
| 7 | NLP validation pass | to do — needs ipopt |
| — | **Code-review findings** | **in progress** |

### Files as they stand

New: `openTEPES_InputDataAC.py`, `openTEPES_SettingUpVariablesAC.py`, `openTEPES_ModelFormulationAC.py`,
`openTEPES_BoundTightening.py`, `openTEPES_OutputResultsAC.py`.

Modified: `openTEPES.py` (cycle-flow guard), `openTEPES_InputSchema.py` (two tables),
`openTEPES_InputData.py` (flags, AC-only stem skip), `openTEPES_DataConfiguration.py` (call, indicators),
`openTEPES_SettingUpVariables.py` (one call), `openTEPES_ModelFormulationElectricity.py` (DC constraints
stand down under AC), `openTEPES_ProblemSolvingStageIter.py` (`FORMULATION_REGISTRY`).

Cases: `9n_AC`, `RTS-GMLC_AC`. Tests: `tests/test_ac_input.py`, 27 tests. Prototypes:
`prototypes/ac_formulations/`.

### Phase 5

The first task is not the investment logic. A synchronous condenser has `MaximumPower = 0`, so it falls out
of `mTEPES.g` (`openTEPES_DataConfiguration.py:60`) and hence out of `pg`; every `psn`-indexed set filters
through `pg`, so `psnsq` comes out empty for exactly the units it exists to hold. The `g` filter has to admit
a unit with `MaximumReactivePower > 0` first.

Also in Phase 5: `vShuntInvest` into `eTotalFElecCost`, into `fix_for_duals`, and into the cost summary in
`openTEPES_ProblemSolving.py` — **which is duplicated verbatim across the two `NoRepetition` branches**, so
the line has to be added twice until the registry refactor proposed in the architecture review lands.

### Phase 6

One new module plus one `OUTPUT_REGISTRY` row. Two existing reports change meaning under AC and need
checking: `PowerFlowIn`/`PowerFlowOut` per node miss the line losses on the incoming side, and the network
map colours lines against `NTCFrw` when the binding AC limit is apparent power.

The voltage magnitude is `√vW`. Under a piecewise-linear formulation `vW` is still the square — unlike the
LPAC variant considered earlier and dropped — so no formulation-dependent recovery is needed.

### Phase 7

Fix the binaries, re-solve with (13) exact, and report the cone violation and the cost difference. Needs
ipopt, which is **not installed** in either environment here.

## 5. Defects found and not carried over

**In `openTEPES_PRO`, the reference implementation:**

1. `pSBase` appears nowhere in its AC formulation, yet per-unit admittances multiply into a balance whose
   other terms are in GW. openTEPES reads `SBase` as `v * 1e-3`, so `pSBase` is already in GVA and the
   missing factor is plain `pSBase`.
2. **The tap changer is inverted twice.** For a real transformer the inversions cancel; for a blank `Tap` —
   the normal state of the column — the first divides by zero and the second returns 0.0, zeroing every
   mutual admittance term and silently disconnecting the branch.
3. `eReactivePowerFlow_To_LB` uses `<=` where it needs `>=`, so the lower bound is never enforced.
4. `pLineBsh / 20`, an unexplained magic number.

**In shipped openTEPES cases** — all invisible to the DC model, all fatal to an AC one:

5. **RTS-GMLC stores `AngMin`/`AngMax` in radians** (±1.047) in columns `openTEPES_InputData.py:422` converts
   from degrees. Read as degrees they become ±1.05°.
6. **Sixteen RTS-GMLC transformers are labelled `LineType = 'DC'`** — x = 0.084, r = 0.002, taps 1.015/1.030,
   unmistakably the RTS 138/230 kV transformer data. Excluding them splits the system into three islands.
7. **The 9-bus case is not per-unit consistent**: SBase = 100 MVA against ~1500 MW of demand puts per-unit
   flows near 15 and collapses an exact power flow to 0.82 p.u. `9n_AC` uses 1000 MVA.

**In openTEPES's handling of AC-relevant columns:**

8. A blank `AngMin`/`AngMax` pair fills to 0.0, which read literally pins every branch angle difference to
   zero. Treated as "not given" and opened to ±π/2 before tightening.

**In this work, found and fixed:**

9. `M` was written with the series admittance convention, giving `−(x·P + r·Q)` — negated. Now written
   explicitly and verified against an exact power flow.
10. `nx.minimum_cycle_basis` operates on the simple graph, so it collapses parallel circuits and misses the
    two-branch loop each extra circuit forms — 36 cycles found on RTS-GMLC where the topology implies 48.
    Without them two parallel circuits can carry flows implying different angle differences.
11. Reactive limits were indexed on `psn × gq` though they are rated values constant in time: 65,520 Param
    entries where 15 suffice on the 9-bus case.

## 6. Two decisions still open

**The thermal limit is permissive.** Equation (7) uses `Smax / Vmin`, which is conservative in current but
permissive by `Vmax/Vmin` in apparent power. Every prototype overloaded on replay, by 0.7 % to 6.9 %. Phase 3
uses the *tightened* per-bus minimum rather than the global one, which shrinks the gap but does not close it.
Either accept and document it, or add an explicit apparent-power constraint at both ends.

**Off-nominal transformer taps are not modelled.** `pLineTapFactor` is computed and stored but no constraint
reads it yet, and openTEPES has no phase-shift column at all, so a phase-shifting transformer cannot be
represented. Both belong in the branch equations when Phase 4 lands.
