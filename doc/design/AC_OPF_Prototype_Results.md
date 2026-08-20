# AC formulation prototypes: accuracy against CPU time

> **Re-measured 2026-08-19 after a code review found two critical bugs in the formulation these numbers were
> produced with.** The prototypes carried the same two defects as the model: the angle-envelope numerator `M` was
> sign-flipped, and the envelope divided by the wrong end of the voltage band for negative `M`, so the two bounds
> crossed and any reverse flow was infeasible. The bound tightening was separately 10x too tight on a 100 MVA base.
>
> **Two headline conclusions below did not survive and are struck through where they appear: the "+3.77 % from
> cyclic constraints" in §3, and the "the relaxation is not exact" of §9.** Both were artefacts of those bugs. The
> accuracy comparison of §2 and the scaling result of §8 do survive, with the caveats noted in each.
> §10 records the re-measurement.

Fourth in the series. Code in `prototypes/ac_formulations/`, run with `~/ai_research/.venv` (pandapower
3.5.4, Pyomo 6.10, Gurobi). Every prototype is a single-snapshot economic dispatch over the same
generators with the same objective, differing only in how it represents the network.

## 1. How accuracy is measured

Three numbers, and they are not interchangeable:

* **Optimality gap** — cost against the exact non-convex AC OPF, solved by pandapower's interior-point
  method. A relaxation lands below it; a restriction or approximation can land either side.
* **Physical error** — take the dispatch the formulation chose, run an *exact* Newton-Raphson AC power
  flow with it, and compare what the formulation predicted with what the network does. This is the error
  a planning study actually inherits, and it is not the optimality gap.
* **Cycle mismatch** — the sum of angle differences round each independent cycle, recovered *from the
  branch flows* via `sin θ_ij = M / (Vi Vj)`. This is a stricter test than reporting the mismatch on the
  model's own `θ` variables, because it asks whether the flows correspond to any consistent angles.

## 2. 9-bus case: 40 sampled load levels

`9n_AC`, 9 buses, 12 AC branches, 4 independent cycles, ~1531 MW peak. The exact AC OPF converged at
all 40 sampled load levels, so the optimality gaps here are trustworthy.

| formulation | gap % median | gap % worst | loss error median (MW) | loss error worst | cycle mismatch worst (°) | worst loading % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DC | −0.256 | 0.567 | −1.126 | 2.239 | 0.000 | 102.1 |
| **DC + 2 % loss factor** | **+6.021** | **9.743** | **+26.022** | **33.631** | 0.000 | 103.1 |
| BFM-SOCP, no cycles | −0.000 | 4.559 | +0.000 | 0.000 | 0.022 | 106.9 |
| BFM-SOCP + cycles [A] | −0.000 | 4.559 | +0.000 | 0.000 | 0.016 | 106.9 |
| BFM-LP + cycles [B], L=4 | +0.107 | 1.264 | +0.422 | 0.430 | 0.664 | 103.5 |
| BFM-LP + cycles [B], L=10 | +0.019 | 1.175 | +0.084 | 0.091 | 0.252 | 100.7 |
| BFM-LP + cycles [B], L=25 | +0.003 | 1.154 | +0.012 | 0.015 | 0.109 | 100.9 |

Four things stand out.

**The loss factor is far worse than no loss model at all.** `DC + 2 % loss factor` — the value shipped in
the 9n case — over-predicts losses by 26 MW at the median against a true 2.5 MW, and costs 6 % too much.
Plain DC, which predicts zero losses, is an order of magnitude closer on cost. `LossFactor` is a
per-case calibration constant, and a wrong one is actively harmful.

**The branch-flow SOCP is exact on losses.** Loss error 0.000 MW, and the conic gap
`u·l − P² − Q²` came out at 1e-8, i.e. the relaxation is tight on this network. Median optimality gap 0.

**The piecewise-linear model converges to the SOCP from the conservative side.** It over-estimates the
square, so it over-estimates current and under-uses the network, landing *above* the true cost. Going
L=4 → 10 → 25 cuts the loss error 0.42 → 0.08 → 0.01 MW with diminishing returns after L=10.

**Every formulation overloads something on replay.** Worst loading is 100.7 – 106.9 %, and the SOCP is
worst. The cause is faithful to paper [A]: its thermal constraint (7) is `l ≤ (S̄/V̲)²`, using the
*minimum* voltage. That is conservative in current but permissive in apparent power by a factor
`V̄/V̲ = 1.105`. Worth knowing before quoting a plan as thermally feasible.

**Cycle constraints did nothing here** — 4 cycles is too few and too weakly meshed to bind.

## 3. RTS-GMLC: where the cycle constraints earn their place

`RTS-GMLC_AC`, 73 buses, 120 AC branches, **36–48 independent cycles**, 8192 MW peak, 2.3 % losses.

**The reference is not trustworthy at this size.** pandapower's interior-point OPF converged at only
5 of 20 sampled load levels, and relaxing constraints sometimes *raised* the reported cost
(no thermal limits → 62 156; free reactive → 94 130), which is impossible at a true optimum. The
optimality-gap column is therefore omitted for this case; the physical error, the cycle mismatch, the
model size and the CPU times remain valid because they do not depend on the reference.

| formulation | cost | vars | cons | build s | solve s |
| --- | ---: | ---: | ---: | ---: | ---: |
| DC | 62 190 | 619 | 314 | 0.02 | 0.011 |
| DC + 2 % loss | 68 956 | 619 | 434 | 0.04 | 0.011 |
| BFM-SOCP, no cycles | 62 012 | 739 | 507 | 0.03 | 0.012 |
| **BFM-SOCP + cycles [A]** | **64 350** | 812 | 904 | 0.17 | **0.021** |
| BFM-LP + cycles [B], L=4 | 64 818 | 2 252 | 2 344 | 0.21 | 0.063 |
| BFM-LP + cycles [B], L=10 | 63 577 | 3 692 | 3 784 | 0.19 | 0.090 |
| BFM-LP + cycles [B], L=25 | 63 429 | 7 292 | 7 384 | 0.23 | 0.137 |

~~**The cyclic constraints raise the lower bound by 3.77 %** (62 012 → 64 350) for a 75 % increase in solve
time.~~ **Wrong — see §10.** With the envelope corrected and a *valid* angle bound, the cyclic constraints and the
envelope together move the objective by **exactly zero** on both cases. The 3.77 % was the over-tight bound and the
sign-broken envelope restricting the model, and a restriction that raises a lower bound is not a tightening.

**At snapshot scale the SOCP dominates the piecewise-linear model on both axes**: tighter *and*
4–6× faster, with a ninth of the variables. That is worth stating carefully, because it does **not**
contradict paper [B]: [B] linearises so the model can carry binaries over 8736 hours, where a MISOCP can
be far harder for a branch-and-bound solver than a MILP. The linearisation buys tractability in the
*integer* problem, not in the continuous relaxation. **That test is now in §8, and its answer is more
interesting than expected: the linearisation wins on commitment binaries and loses on investment
binaries.**

## 4. The dominant tightness knob is the angle bound, and it is not free

The angle envelope (16)–(17) has slack `tan(θ^m/2) − θ^m/2` per branch, which grows fast with the angle
bound. Sweeping `θ^m` on RTS-GMLC:

| θ^m | envelope slack per branch (°) | SOCP + cycles cost | vs no cycles | cycle mismatch worst (°) | solve s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 60° | 3.080 | 64 350 | +3.77 % | 14.30 | 0.021 |
| 45° | 1.233 | 72 158 | +16.36 % | 12.14 | 0.022 |
| 30° | 0.352 | 128 858 | +107.80 % | 6.14 | 0.034 |
| 20° | — | infeasible | — | — | — |

The envelope slack falls by an order of magnitude from 60° to 30°, and the bound tightens enormously.
But the jump to +107.8 % is not a better bound — it is the model ceasing to be a relaxation. An angle
bound of ±30° is a *physical restriction* the true optimum may violate, and by ±20° the problem is
infeasible outright.

**This is why paper [B] spends a section on bound tightening.** Shrinking `θ^m` and the voltage bounds is
what makes the cyclic constraints work, and it has to be done by a propagation procedure that provably
cannot cut off the true optimum (Coffrin, Hijazi & Van Hentenryck), never by picking a tighter number.
RTS-GMLC ships with ±60° on every branch, where the envelope has 3° of slack per branch — across a cycle
of five branches that is 15° of slack, and the recovered-angle mismatch of 14.3° says exactly that.

**Bound tightening is therefore not an optimisation to add later. It is a prerequisite.**

## 5. Three data defects found in shipped cases

Found while building the AC cases, all invisible to the DC model and all fatal to an AC one.

1. **RTS-GMLC stores `AngMin`/`AngMax` in radians** (±1.047) in columns `openTEPES_InputData.py:422-423`
   multiplies by π/180. Read as degrees they become ±1.05°, which would make any AC model infeasible.
2. **Sixteen RTS-GMLC transformers are labelled `LineType = 'DC'`** — 103-124, 109-111, 109-112, … all
   with x = 0.084, r = 0.002 and taps of 1.015/1.030, which is unmistakably the RTS 138/230 kV
   transformer data. Labelling them DC lets the DC model skip Kirchhoff's voltage law on them. Excluding
   them from an AC study splits RTS-GMLC into **three electrical islands**.
3. **The 9-bus case is not internally consistent in per unit**: SBase = 100 MVA against ~1500 MW of
   demand gives per-unit flows around 15, and an exact power flow collapses to 0.82 p.u. Corrected to
   SBase = 1000 MVA in `9n_AC`, which puts voltages at 0.99–1.00 and losses at a plausible level.

## 6. What this decides

* **Branch flow model, confirmed.** It reproduced the exact AC losses to 0.000 MW on the 9-bus case.
* **Cyclic constraints, confirmed** — but only on a properly meshed network, and only with valid bound
  tightening. Without tightening they buy 3.8 % on RTS-GMLC; the envelope's own slack is the binding
  limitation, not the constraint count.
* **Bound tightening is promoted from a later optimisation to a Phase 3 prerequisite.**
* **SOCP versus piecewise-linear is still open**, and this study cannot close it: the snapshot evidence
  favours SOCP on both accuracy and speed, while paper [B]'s argument lives in the mixed-integer,
  multi-period problem this harness does not yet build. That is the next experiment.
* **The thermal limit `l ≤ (S̄/V̲)²` is permissive by `V̄/V̲`.** Every prototype overloaded on replay.
  Worth an explicit decision rather than inheriting it.

## 7. Honest limitations

* Single snapshots, no unit commitment, no storage, no investment binaries — so nothing here speaks to
  the integer problem, which is where openTEPES actually lives.
* `9n_AC` reactive demand, line resistance and charging are synthetic (Q = 0.30 P, R = X/10, B = X);
  RTS-GMLC's are real except for the reactive demand (Q = 0.20 P) and generator reactive limits.
* Off-nominal transformer taps are dropped: the harness works in one per-unit system, so the RTS
  1.015/1.030 taps are set to 1. This affects all formulations equally but removes tap effects entirely.
* The exact AC OPF reference is reliable on 9 buses and unreliable on 73. A stronger reference (ipopt via
  PowerModels, or Gurobi's non-convex QCQP) is needed before any optimality gap on RTS-GMLC is quoted.

---

# 8. Multi-period with binaries: the experiment that was supposed to decide it

Harness: `prototypes/ac_formulations/multiperiod.py` (AC unit commitment on the branch flow model, with
start-up/shut-down logic, minimum up and down times, ramps, start-up costs, and optionally a build/no-build
binary per candidate branch) and `scaling.py`. Gurobi, 4 threads, 300 s limit, MIP gap 1e-4.

The hypothesis was straightforward: Gurobi handles a second-order cone inside a MIP by outer-approximating
it at nodes of the tree, so the cone is paid for repeatedly rather than once, whereas a MILP has no such
overhead. That should reverse the snapshot ordering and reverse it harder as the tree grows.

**It does — but only for one of the two kinds of binary, and the other kind reverses it back.**

## 8.1 Commitment binaries only (RTS-GMLC, 153 units)

| T | formulation | objective | vars | cons | bins | solve s | ratio |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | LP L=10 | 31 837 | 4 151 | 4 243 | 153 | 0.17 | 1.0 |
| 1 | SOCP | 32 537 | 1 271 | 1 363 | 153 | 0.24 | 1.4 |
| 2 | LP L=10 | 59 909 | 8 302 | 8 853 | 306 | 0.44 | 1.0 |
| 2 | SOCP | 61 245 | 2 542 | 3 093 | 306 | 0.94 | 2.1 |
| 4 | LP L=10 | 103 485 | 16 604 | 18 097 | 612 | 1.18 | 1.0 |
| 4 | SOCP | 105 908 | 5 084 | 6 577 | 612 | 2.39 | 2.0 |
| 8 | LP L=10 | 139 833 | 33 208 | 36 664 | 1 224 | 4.22 | 1.0 |
| 8 | **SOCP** | 142 990 | 10 168 | 13 624 | 1 224 | **11.72** | **2.8** |

The penalty grows with the horizon — 1.4× at one period to 2.8× at eight — which is the signature of the
cone being re-approximated deeper and deeper in the tree. Extrapolating that trend to 8736 periods is
exactly the argument for linearising, and it is the argument Alvarez et al. make.

On the 9-bus case the same sweep to T=24 showed no penalty at all (SOCP 0.5–1.9× the LP time, mostly
below 1.0). Twelve branches and fifteen units do not build a tree worth searching. **A formulation study
run only on a 9-bus system would have reached the opposite conclusion.**

## 8.2 Add investment binaries: the SOCP leads early, then loses anyway

Same case, plus a build/no-build binary on the 30 lowest-rated branches, shared across periods.

| T | formulation | objective | vars | bins | solve s | ratio | MIP gap |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | LP L=10 | 64 008 | 4 181 | 183 | 9.53 | 1.0 | 0.000 % |
| 1 | **SOCP** | 64 139 | 1 301 | 183 | **6.11** | **0.6** | 0.003 % |
| 2 | LP L=10 | 94 978 | 8 332 | 336 | 44.21 | 1.0 | 0.000 % |
| 2 | **SOCP** | 95 383 | 2 572 | 336 | **24.87** | **0.6** | 0.002 % |
| 4 | **LP L=10** | 141 385 | 16 634 | 642 | **166.64** | 1.0 | 0.000 % |
| 4 | SOCP | 142 861 | 5 114 | 642 | 230.19 | 1.4 | 0.001 % |
| 8 | LP L=10 | 178 459 | 33 238 | 1 254 | *300 s limit* | 1.0 | **1.756 %** |
| 8 | SOCP | 181 678 | 10 198 | 1 254 | *300 s limit* | 1.0 | **1.866 %** |

The SOCP is ahead at one and two periods — its model is 13× smaller, and with a hard network decision in
the tree that size advantage shows. But the lead does not survive: by four periods the ordering has flipped
back to the LP, and by eight neither closes inside 300 s, with the LP holding the slightly smaller gap.

**An earlier reading of this table, taken from the first two rows before the run finished, concluded that
the SOCP wins with investment binaries. That was premature and is wrong.** The horizon is what decides, and
past T=2 it decides for the linearisation in both settings.

## 8.3 What this actually decides

**The horizon decides, and past a couple of periods it decides for the piecewise-linear model in both
settings.**

* Commitment binaries, fixed network: the LP wins from T=2 and the margin compounds — 2.8× at T=8.
* Investment binaries as well: the SOCP leads at T=1–2, where its 13× smaller model tells, but loses from
  T=4 and neither formulation closes at T=8.

So the SOCP's advantage is confined to small numbers of representative periods. **Alvarez et al.'s choice
to linearise is the right one for the horizons openTEPES targets**, and this study now supports it rather
than merely failing to contradict it. The SOCP keeps a distinct role: it is the only variant returning a
valid bound, so it is what to quote a plan's optimality against, computed on a handful of snapshots.

Two honest caveats on the numbers above. First, **the objective values are not comparable as bounds
between the two**: they relax different things — the cone bounds `l` from below through `u`, while the
piecewise model drops `u` from the current equation entirely and over-estimates the square — so neither is
a bound on the other, and only the timings answer the scaling question. Second, T=8 is a long way from
8736; the trend is clear but the extrapolation is not measured.

**Consequence for openTEPES: build both.** That is not a hedge — it is what the evidence supports, and the
shared-equation structure of §3 makes the second formulation a small block rather than a second model. The
`FORMULATION_REGISTRY` already carries the dispatch. `IndACModelType` picks the point on the curve, and the
guidance to write into the documentation is the split above, not a single recommendation.

---

# 9. Phase 4 built: the relaxation looked inexact on 9n_AC — it was two bugs (superseded by §10)

Solving the complete model — Phase 3's shared block plus Phase 4's current definition — on `9n_AC` over four
load levels:

| `IndACModelType` | objective (MEUR) | losses, hour 1 | voltage band |
| --- | ---: | ---: | --- |
| 0 SOCP | 2.5453 | 19.08 MW (2.00 %) | 0.9803 – 1.0041 |
| 1 piecewise linear | 2.5459 | 19.13 MW (2.00 %) | 0.9773 – 1.0014 |

The SOCP sits below the piecewise model, which is the right ordering: a relaxation below a restriction.

**But the cone is loose.** Inspecting the branches, **seven of twelve had `vCurr` pinned at its thermal
upper bound while carrying almost no flow** — for instance `Node_7 → Node_8` at `l = 0.497` (its limit)
with `P = 0.0008 GW`, `Q = −0.011 Gvar`. The relaxation was reporting thermally saturated branches that
carry nothing.

**Why.** The current enters as an inequality — `P² + Q² ≤ vW·vCurr` — so nothing forces `vCurr` down to the
boundary. Normally the nodal balance does it, because a larger current is a larger loss and therefore more
generation. Two things defeat that here: the losses on those branches are served by zero-cost wind and solar
at `Node_4`, so the pressure vanishes; and a larger current actively *helps*, because `vCurr` enters the
voltage drop equation with a positive sign and props up the downstream voltage.

**Partial fix, applied.** A small explicit price on `vCurr` in `vTotalNCost`, the same device
`pEpsilonLosses` already provides for the DC loss inequality but applied to the variable that actually
carries the slack. It cut the loose branches from seven to four and the reported losses from 19.08 MW to
10.97 MW.

**It does not eliminate the problem, and it should not be tuned until it appears to.** The four survivors
form a cycle, `Node_4 → Node_9 → Node_8 → Node_6`, where propping the voltage round the loop still pays. A
penalty large enough to close that would distort the objective it is supposed to leave alone.

This is the known inexactness of the second-order cone branch-flow relaxation. It is exact under conditions
— no reverse flows, load over-satisfaction, a binding voltage upper bound — that a meshed transmission
network with zero-cost renewables does not meet. Two consequences that are now design decisions rather than
open questions:

1. **The Phase 7 NLP restoration is required, not optional.** It is the only thing that turns a relaxed
   solution into a physically realisable one.
2. **The cone gap `vW·vCurr − P² − Q²` must be a first-class reported diagnostic**, per branch and per load
   level, in Phase 6. A user reading a loss figure or a line loading needs to know whether the relaxation
   was tight where it mattered. On this case it was not, and nothing in the solver output would have said so.

An earlier note in `AC_OPF_Architecture_Review.md` said `pEpsilonLosses` should be **zero** under AC, on the
grounds that an equality leaves no slack to squeeze. That reasoning does not apply: under both the cone and
the piecewise staircase the current is bounded below, not fixed, so there is exactly such a slack and the
penalty is what squeezes it. **Keep the loss penalty under AC.**


---

# 10. Re-measurement after the code-review fixes

The prototype harness was corrected the same way the model was — `M = x·P + r·Q` with the sign stated, the envelope
divisor following the sign of `M` through a split into non-negative parts, and the valid bound tightening
(`S = Smax·Vmax/Vmin / pSBase`). The cyclic equation was also put behind its own switch, so for the first time the
envelope and the cyclic constraint could be measured apart.

## 10.1 The angle machinery buys nothing

| formulation | 9n_AC | RTS-GMLC_AC |
| --- | ---: | ---: |
| BFM-SOCP, no angle machinery at all | 18 784.1 | 62 011.7 |
| BFM-SOCP, angle envelope only | 18 784.1 | 62 011.7 |
| BFM-SOCP, envelope + cyclic equation | 18 784.1 | 62 011.7 |

Identical to the digit. Two separate things are going on, and they were previously confounded:

* **The cyclic equation is vacuous.** With `vTheta` an explicit variable, the sum of angle differences round a closed
  cycle telescopes to zero identically. The papers impose it because they *eliminate* the angles; this model does not.
* **The envelope does not bind** once the angle bound is the one the physics actually implies rather than one ten
  times tighter.

**Consequence for the design.** `vTheta`, the envelope, `vMPos`/`vMNeg` and the angle band currently cost variables
and constraints for no measured gain on either bundled case. They are still needed to *recover* angles for reporting,
and they may bind on a more stressed system — but they cannot be claimed to earn their place on this evidence, and
the plan should stop asserting that they do.

## 10.2 The relaxation gap was the bugs, not the relaxation

Re-run on the fixed model, same case and hour as §9:

| | before the fixes | after |
| --- | ---: | ---: |
| branches with `vCurr` pinned at its thermal bound | **7 of 12** | **0 of 12** |
| worst cone gap `vW·vCurr − P² − Q²` | 4.9e−01 | **2.6e−06** |
| reported losses | 19.08 MW | **1.92 MW** |

The cone is tight on every branch. §9 attributed this to the known inexactness of the SOC branch-flow relaxation on a
meshed network with zero-cost renewables. That was wrong: the broken envelope forced flows into the direction each
branch happened to be listed in, and the force-built shunt distorted the reactive side, and the model relieved both by
inflating current where it was cheap to do so.

Two things follow. The `pEpsilonCurrent` penalty added in response to §9 is treating a symptom that no longer exists
and should be reconsidered. And **"the Phase 7 NLP restoration is required, not optional" rested on this artefact** —
the restoration is still worth having, but the case for it is now the general one, not a measured failure here.

The cone-gap diagnostic itself stays. It is what surfaced this, and a user needs it whether or not the relaxation
happens to be tight on the day.

## 10.3 What survives unchanged

* **`DC + 2 % loss factor` is still the worst formulation tested** — +5.53 % against the true AC OPF on 9n_AC, against
  +0.29 % for plain DC which models no losses at all.
* **BFM-SOCP still returns a valid lower bound**, −2.77 %, with losses of 3.53 MW against a true 3.36 MW.
* **BFM-LP is still conservative**, +0.68 %, as an over-estimating restriction should be.

## 10.4 What has not been re-measured

* **The `θ^m` sweep of §4.** Those runs used the sign-broken envelope, where tightening the angle bound also tightened
  a constraint that was already wrongly excluding reverse flow. The +107.8 % at 30° and the infeasibility at 20° cannot
  be attributed to the bound alone, and the section should be treated as unmeasured until it is redone.
* **The overload figures of §2** (100.7–106.9 % loading on replay) came from the same broken prototype.
* **The multi-period scaling of §8.** Both formulations carried the same broken envelope, so the *relative* timings —
  which is all §8 claims — are probably unaffected, but the objective values in those tables are not trustworthy.

# 11. The current penalty is a modelling choice, not a tie-breaker

Reviews three and four both questioned `pEpsilonCurrent`, the small price the objective puts on `vCurr`. The first read
was that it existed to hide the two bugs of §9 and should go once they were fixed. That was wrong, and the way it was
wrong is worth recording, because the evidence for removing it was produced by the thing being removed: the relaxation
was tight on all twelve branches of 9n_AC, and it was tight *because* the penalty was there.

## 11.1 Why the model wants a current that is not there

`vCurr` enters as an inequality — a cone under `IndACModelType` 0, a staircase under 1 — so nothing pushes it down to
the boundary on its own. The nodal balance normally does the pushing, because more current means more loss means more
generation. The voltage drop works the other way:

    w_j = w_i - 2 (r P + x Q) + z^2 l

A larger `l` **raises** the downstream voltage. Where the extra loss is served by a zero-cost unit, the balance applies
no pressure at all and the relaxation buys voltage with current that does not exist. On 9n_AC at load level
`01-02 07:00`, branch `Node_4-Node_5` sits at its thermal bound, `vCurr = 0.448893` against its limit of `0.448900`,
while the physical value `(P^2+Q^2)/(w S^2)` is `0.089058`. Five times over, and the far-end voltage that comes with it
is not supported by any real flow.

## 11.2 The measurement

9n_AC, `IndACModelType` 0, everything else fixed:

| `pEpsilonCurrent` | relaxation gap | reported losses | generation |
|------------------:|----------------|----------------:|-----------:|
| 1e-6 | loose on 2 of 12, worst 0.802 | 0.54 % | 9,623,751 MWh |
| 1e-5 | loose on 2 of 12, worst 0.802 | 0.54 % | 9,623,757 MWh |
| 1e-4 | loose on 1 of 12, worst 0.178 | 0.54 % | 9,623,806 MWh |
| **1e-3** | **tight on all 12, worst 4.3e-07** | **0.84 %** | **9,652,689 MWh** |

It does not taper. Nothing below 1e-4 moves the gap at all, and the step from 1e-4 to 1e-3 both closes it and moves the
dispatch by about 29 GWh.

## 11.3 The trade-off, stated plainly

Both criticisms are right at the same time:

  * At 1e-3 the penalty is roughly an order of magnitude above the loss it stands in for on 9n_AC (`r ~ 0.002` p.u.,
    `pSBase` 1 GVA). It is therefore not a tie-breaker. It changes the dispatch, it inflates `vTotalNCost`, and it feeds
    through to the `eBalanceElec` duals that the marginal-results writer reports as locational prices.
  * Below 1e-4 the currents, the losses and the voltages on the affected branches are fiction.

The exact DC analogue — pricing the AC loss `r * vCurr * pSBase` at `pEpsilonLosses` — was tried and is far too weak
(about 2e-8). It fails because the DC loss inequality has no competing benefit pulling the other way, and the AC one
does.

1e-3 is kept, on the grounds that a solution whose currents are real is worth more than an undistorted one whose
voltages are not, and because `oT_Result_ACRelaxationGapSummary` reports per branch exactly when this has failed.

**Anyone reading marginal prices off an AC run should know this penalty is in them.** If undistorted duals matter more
than a tight cone for a particular study, lower it and read the gap report — that is a legitimate different choice, and
it is why the value sits in one place with this note attached.

## 11.4 Not yet measured

The sweep is 9n_AC only. RTS-GMLC has a smaller `pSBase`, so the ratio of penalty to physical loss is worse there, and
the same sweep should be run before anyone quotes RTS-GMLC marginal prices.

# 12. What AC costs against DC, measured on the same week

Section 11 left the CPU question open on a real network. Two cases were built to close it: `RTS-GMLC_Oper` and
`RTS-GMLC_AC_Oper`, the same 168 hours (the week containing the annual peak, 23-30 August, peak 10,212 MW) over the
same 73 buses and 120 branches, one under the DC network model and one under AC.

Note first that `RTS-GMLC_AC` carries **no candidates of any kind** — no generation, no network, no shunts. It is
already an operation-only case. What makes the full-year build 27.5 million rows is the 8,736 hour horizon, nothing
else. An earlier reading of this as an investment-loop problem was simply wrong.

## 12.1 Size and time

|                | rows    | columns | nonzeros  | wall  |
|----------------|--------:|--------:|----------:|------:|
| DC             |  98,343 | 123,227 |   423,978 |   8.9 s |
| AC (SOCP)      | 528,423 | 770,531 | 2,424,390 | 103.7 s |
| **AC / DC**    |  **5.4x** | **6.3x** | **5.7x** | **11.7x** |

The AC formulation writes 18 constraints per branch per hour where the DC one writes 7, and adds six variables per
branch plus two per bus, so a factor of five to six on size is structural rather than a defect. Time grows faster than
size, as expected for an interior point method on a larger and denser problem.

For scale, the full-year AC case is 27.5 million rows and 40 million columns, and a barrier solve had not finished
after nine hours. The matrix range is 1e-05 to 3e+02, so the model is well conditioned; the cost is size.

## 12.2 The relaxation is not tight on this network

More important than the timing:

    ### WARNING: the AC relaxation is not tight on 21 of 120 branches (worst 0.927 of Smax^2)

| branch | worst gap [p.u. of Smax^2] |
|--------|---------------------------:|
| Node_102 - Node_106 | 0.927 |
| Node_202 - Node_206 | 0.820 |
| Node_302 - Node_306 | 0.703 |
| Node_101 - Node_103 | 0.108 |
| Node_303 - Node_309 | 0.100 |

On 9n_AC the cone is tight on all twelve branches to 1e-07. On RTS-GMLC it is loose on 21 of 120, and on three of them
the slack is most of the branch rating. **The reported current, loss and loading on those branches are not supported by
the flows**, so they should not be read as physical.

The three worst are the same branch position in each of the three RTS areas, which points at the network structure
rather than at a data error in one place.

This is what the diagnostic exists for, and it is the argument for keeping it in the minimal output set: a user who
looked only at the voltages and currents would have no way to know that a sixth of the branches carry numbers that do
not mean what they appear to. It also tempers section 11 — the current penalty closes the gap on a nine-bus network and
does not close it here.

## 12.3 What has not been done

Phase 7, the restoration pass that would solve an exact AC power flow on the relaxed solution and report the true
values, is the answer to a loose cone and it has not been built. It needs ipopt. Until it exists, an AC run on a meshed
network should be read together with `oT_Result_ACRelaxationGapSummary`, branch by branch.
