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

*Re-measured after the angle-relation sign fix of section 16. Sizes are unchanged by that fix; the costs and the
tightness were taken again.*

> **Re-measured with the reactors in place.** Neither `RTS-GMLC_AC` nor `RTS-GMLC_AC_Oper` carried a shunt table until
> 21 August 2026, so every earlier figure here was taken on a system with no reactive compensation at all. Section 14.1
> shows what they change. The three month and full year rows of 12.1a are the exception: they were not re-solved,
> because they need 7 GB and 30 GB, and their sizes move by 3 rows per hour, which does not affect what they are used
> for.

`RTS-GMLC_Oper` and `RTS-GMLC_AC_Oper` are the same 168 hours (the week containing the annual peak, 23-30 August, peak
10,212 MW) over the same 73 buses and 120 branches, one under the DC network model and one under AC.

`RTS-GMLC_AC` carries **no candidates of any kind**. It is already an operation-only case, and what makes the full-year
build 27.5 million rows is the 8,736 hour horizon, nothing else.

## 12.1 Size and time

|             | rows     | columns  | wall     | total cost   |
|-------------|---------:|---------:|---------:|-------------:|
| DC          |   98,343 |  123,227 |   14.8 s | 36.5834 MEUR |
| AC (SOCP)   |  528,927 |  771,035 |  121.7 s | 59.9967 MEUR |
| **AC / DC** | **5.4x** | **6.3x** | **8.2x** |              |

The DC figures are unchanged to the digit by adding the reactors, which is the right answer: a shunt has no place in a
DC model and never reaches it. The AC model grew by exactly **504 rows and 504 columns**, which is 3 reactors over 168
hours. Wall times are indicative rather than comparable with the earlier run: this machine was doing other work.

## 12.1a How far the horizon goes, and what stops it

| horizon | rows | columns | barrier factor | wall | cone loose |
|---------|-----:|--------:|---------------:|-----:|-----------:|
| 1 day, 24 h     |     75,087 |    110,130 |          — |   11.4 s | 17 of 120 |
| 1 week, 168 h   |    528,927 |    771,035 |          — |  121.7 s | 31 of 120 |
| 1 month, 720 h  |  2,268,831 |  3,300,025 | **2.4 GB** | 1113.7 s | 43 of 120 |
| 3 months, 2184 h|  6,876,807 | 10,015,924 | **7.0 GB** | not re-solved | — |
| 1 year, 8736 h  | 27,509,055 | 40,048,784 | **30.0 GB**| not re-solved | — |

The first three rows are measured with the reactors: 24 and 168 hours from `RTS-GMLC_AC_Oper`, which is a 168 hour case,
and the month from `RTS-GMLC_AC` truncated, because the week case cannot supply a longer horizon. The bottom two rows
are the earlier figures, kept for their sizes, which the reactors move by 3 rows per hour and so do not change what the
rows are used for. They were not re-solved: they need 7 GB and 30 GB.

The 24 hour row does not match the one this table used to carry, 54,855 rows against 75,087 now. That row came from the
`RTS_SOC24` case which was not kept, the same case behind the withdrawn figures of sections 13 and 14. The rows above
name the case they come from so this does not happen again.

**Memory is linear in the horizon** and **the barrier is linear in rows**, both measured rather than assumed:

| horizon | rows | GB per Mrow | barrier s per Mrow |
|---------|-----:|------------:|-------------------:|
| 1 month  |  2.27M | 1.06 | 37.9 |
| 3 months |  6.88M | 1.02 | 37.1 |
| 1 year   | 27.51M | 1.09 | — |

Three months is 25.0% of the year's hours, 25.0% of its rows and 23.3% of its factor. The constraint matrix is
block-banded in time, so that is what should happen, and it makes the 30 GB estimate for the year a measurement rather
than an extrapolation.

The barrier surprise is that it does not degrade: 2.97x the time for 3.03x the rows, with the iteration count almost
flat at 73 then 79. Carrying that to the full year gives roughly 85 to 90 iterations and **about 17 minutes of
barrier**, provided the factor is resident. The 10 h cap is not the binding constraint; the 24 GB of RAM is.

**The full-year case is memory-bound, not hard.** Gurobi's own estimate for it is 4 seconds per barrier iteration; the
observed iterations took 500 to 1,400 seconds, about 150x slower, because a 30 GB factor does not fit the 24 GB machine
it ran on and the solve paged. It then hit openTEPES's 36,000 s limit at a barrier gap of 4.95e-09 — essentially
converged — and Pyomo reported `aborted`, which is the time limit and not a numerical failure. An earlier version of
this section read that as "it does not complete", which was wrong.

The month is the largest horizon that fits in 24 GB, and its barrier takes 86 seconds. The remaining 536 s of its wall
time is Pyomo building the model and writing results, not solving. On a machine with 40 GB or more the full year should
solve well inside the existing 10 h cap.

Note the last column: the share of branches where the cone is loose grows with the horizon, 9 of 120 over a day to 38
of 120 over a month. More hours means more lightly loaded branch-hours, which is where the relaxation goes slack.

The AC formulation writes 18 constraints per branch per hour where the DC one writes 7, and adds six variables per
branch plus two per bus, so a factor of five to six on size is structural. Time grows faster than size, as expected for
an interior point method on a larger and denser problem.

The matrix range is 1e-05 to 3e+02, so the model is well conditioned throughout; see 12.1a for what the horizon costs.

## 12.2 The relaxation is not tight on this network

Measured again with the reactors in place, over the 168 hour window:

| what was measured | loose branches | worst gap |
|-------------------|---------------:|----------:|
| before the reactors, current penalty on | 21 of 120 | 0.901 |
| **with the reactors, current penalty on** | **31 of 120** | **0.120** |
| with the reactors, current penalty off | 79 of 120 | 1.211 |

The reactors cut the worst gap by a factor of seven and left MORE branches marginally loose. Severity down, spread up:
compensating the system stops any one branch being badly wrong and leaves a larger number slightly wrong.

The third row is the one to read alongside section 13.1. The penalty charges the current, which pins the relaxation to
the cone boundary, so the first two rows measure the penalty as much as the network. With it off, two thirds of the
branches are loose.

The horizon matters too, and in the same direction as before the reactors: 17 of 120 over a day, 31 over a week, 43
over a month. More hours means more lightly loaded branch-hours, which is where the relaxation goes slack.

# 13. The exact model, and where it can and cannot be solved

*Re-measured with the reactors in place and the current penalty set to zero. The case is defined below so this can be
repeated: `9n_AC` and `RTS-GMLC_AC_Oper` cut to their first 24 load levels, `IndACPowerFlow = 1`, `IndACRestore = 0`,
the annual RES energy target zeroed because it does not survive truncation, and `AC_CURRENT_PENALTY = 0.0`. The earlier
version of this section named a case that was not kept, which is why its figures could only be withdrawn.*

ipopt 3.14.19 for the exact model, gurobi for the cone.

| case | model | solver | cone | wall | total cost |
|------|-------|--------|------|-----:|-----------:|
| 9n, 24 h  | SOCP  | gurobi | **loose on 8 of 12**, worst 1.110 |    2.2 s | 0.518023 MEUR |
| 9n, 24 h  | exact | ipopt  | tight, 2.32e-16                   |    3.0 s | 0.529997 MEUR |
| RTS, 24 h | SOCP  | gurobi | **loose on 5 of 120**, worst 0.560 |   10.5 s | 5.525900 MEUR |
| RTS, 24 h | exact | ipopt  | tight, 1.73e-16                   | 1212.1 s | 5.526068 MEUR |

**The exact model does solve on RTS.** ipopt reports `Optimal Solution Found`. The earlier reading, that it stopped at
"problem infeasible" from a cold start, was measured on a system with no reactive compensation at all; with the three
reactors in place it converges. It costs 1212 s against 10.5 s for the cone, a factor of 115, which is the real argument
against using it as the working model rather than any difficulty in solving it.

The relaxation gap is **2.26 % on 9n and 0.003 % on RTS**. The small case is the loose one, which is the opposite of
what section 12.2 concluded and of what intuition suggests. Twelve branches with a loose cone on 8 of them beat 120
branches with a loose cone on 5.

## 13.1 The current penalty is what makes the cone look tight

The same 9n case, the same 24 hours, changing only `AC_CURRENT_PENALTY`:

| penalty | SOCP | exact | cone |
|---------|-----:|------:|------|
| 0       | 0.518023 MEUR  | 0.529997 MEUR  | **loose on 8 of 12** |
| 1e-3    | 0.5462318 MEUR | 0.5462307 MEUR | tight on all 12, worst 4.8e-06 |

The penalty charges `vCurr`, and the cheapest `vCurr` consistent with the flows is the one on the cone boundary, so
charging for it pins the relaxation to that boundary. With the penalty on, the relaxed and exact costs agree to six
figures and the cone reports itself tight; with it off, the same case has a 2.26 % gap and a cone loose on two thirds of
its branches.

Since 4.18.18 the penalty is priced into the OBJECTIVE but is no longer part of `vTotalSCost`, so it steers the solve
without appearing in the reported cost. On the 168 hour window that moves the reported total from 59.9967 to 45.5634
MEUR; the objective, and therefore the solution, is unchanged. The tables above and in section 13 predate that split and
report the objective, penalty included.

**A tightness measured with the penalty on is measuring the penalty.** The earlier version of this section read the
agreement to seven figures as "where the cone is tight the relaxed answer is the AC answer". The agreement was real and
the reading was wrong: what it showed was the penalty doing its work, and the cost it reported carried the penalty too.

# 14. The restoration pass

`ACRestorationPass`, switched on with `IndACRestore = 1`. After the ordinary solve it holds the plan — commitment,
switching and every investment stay where the relaxed solve put them — swaps the relaxed current definition for the
exact equality and the angle envelope for the exact angle relation, and re-solves the network on ipopt.

On the 24 hour RTS-GMLC window of section 13, where the cone is loose on 5 of 120 branches:

| what | total cost |
|------|-----------:|
| SOCP, as reported                     | 5.525900 MEUR |
| **the same plan with exact physics**  | **5.556286 MEUR** |
| the true optimum, exact from a cold start | 5.526068 MEUR |

Three numbers rather than two, because they answer different questions. The relaxation understates its own plan by
**0.55 %**: that is the gap between the first two rows, and it is what the pass corrects. The relaxation gap proper is
0.003 %, the distance from the first row to the third. And the relaxed **plan** is 0.55 % worse than the best plan
available, because the pass holds the commitment the relaxed solve chose and only makes it physical.

The pass cost 265.5 s against 10.5 s for the relaxed solve alone, and 1212 s for the exact model from a cold start. It
is the cheaper of the two routes to a physical operating point.

## 14.1 What the missing reactors were doing

The RTS cases carried no shunt table, so the three 100 Mvar reactors on buses 106, 206 and 306 were absent from every
measurement above. A fresh 24 hour window cut from `RTS-GMLC_AC_Oper`, solved as an SOCP with and without them:

| 24 h window | SOCP | same plan, exact physics | understated by | cone |
|-------------|-----:|-------------------------:|---------------:|------|
| no reactors   | 8.4499 MEUR | 15.8607 MEUR | **88 %** | loose on 4 of 120, worst 0.853 |
| **reactors**  | **8.0639 MEUR** | **8.1629 MEUR** | **1.2 %** | **tight on all 120** |

**Most of the looseness on RTS was the missing reactive compensation, not the network.** With the reactors in place the
cone is tight on every branch and the relaxed cost is within 1.2 % of its own plan under exact physics. Section 12.2
read the loose cone as a property of this network; on a system carrying its own compensation it largely is not.

The same holds at 168 hours: `RTS-GMLC_AC_Oper` falls from 61.65 to 60.00 MEUR. The direction is what the physics asks
for. The 138 kV lines generate charging reactive, voltages sit against the 1.05 ceiling either way, and without the
reactors that surplus had to be absorbed by generators at a cost.

The old figures of sections 13 and 14 were never reproduced. The `RTS_SOC24` case they used was not kept, and a rebuilt
24 hour window gives 8.4499 MEUR and 4 loose branches where they recorded 15.3720 and 9 of 120, on what should be the
same hours of the same case. What differs has not been identified. Those sections have since been **re-derived from
scratch** on a case whose definition is written down, rather than restated, and the old numbers are gone rather than
corrected.

## 14.2 The four formulations, compared fairly

24 hour RTS-GMLC window, reactors in place, `AC_CURRENT_PENALTY` set to zero. The rectangular model is the reference:
it is the exact non-convex problem, so the two relaxations should sit at or below it.

| formulation                        | solver | cost (MEUR) | gap    | wall   | variables | constraints |
|------------------------------------|--------|------------:|-------:|-------:|----------:|------------:|
| branch flow, SOCP                  | gurobi |     5.52590 | 0.065% |  4.3 s |    66,363 |      57,807 |
| bus injection, W space, SOCP       | ipopt  |     5.52575 | 0.068% |  8.5 s |    75,003 |      49,167 |
| bus injection, W space, + tangent  | ipopt  |     5.52903 | 0.009% |  9.2 s |    75,003 |      52,047 |
| **bus injection, rectangular**     | ipopt  | **5.52951** |      — | 18.9 s |    66,987 |      42,279 |

**All four agree to within 0.07%.** Branch flow and bus injection in W space differ by 0.003%, which is Bose and Low's
equivalence showing up as a measurement rather than a citation. The tangent coupling closes most of what remains, at
about 8% more constraints and almost no extra time.

Branch flow is the fastest by a factor of two and the only one a linear-conic solver handles, at the cost of the most
constraints. Rectangular carries the fewest constraints and the most time, which is what an exact non-convex problem on
an interior-point solver should look like.

**Two corrections had to be made before this table meant anything.** Both inflated the apparent spread:

* The reactors were missing (section 14.1). Without them the relaxation is loose and the numbers move by tens of
  per cent.
* `AC_CURRENT_PENALTY` is charged on `vCurr`, which **only branch flow has**. With the default 1e-3 the same window
  gives 8.06 MEUR for branch flow against 5.53 for rectangular, and branch flow appears 46% worse than an exact model
  it should bound from below. That is the penalty, not the formulation. Any comparison across formulations has to zero
  it; any comparison of costs against another tool has to zero it too.

An earlier reading of the 8.06 against 5.53 was that the rectangular model must be missing constraints. It was not,
though the check did turn up a real gap: the angle-difference band was built for W space only, so rectangular ran with
no band at all. Fixing it changed neither this window nor the pglib case118 check, which the next section explains.

## 14.3 Why pglib case118 comes out below the published optimum

Section 15 reports 97,100 dollars per hour against a published 97,214, which is 0.117% BELOW a figure nothing should
beat. The cause is the **form of the thermal limit**, not a missing constraint.

openTEPES writes the limit on the CURRENT, `l <= (Smax/Vmin)^2`, so with the cone the apparent power it admits is
`Smax * V_i / Vmin`, which reaches `Smax * Vmax / Vmin` at the top of the voltage band. pglib imposes a flat
`|S| <= rateA`. On case118 the band is 0.94 to 1.06, so the allowance is 1.1277.

Two branches of our solution sit above their rating, and the worst is at exactly that allowance:

| branch | apparent power |
|--------|---------------:|
| N_100 - N_103 | **112.8 % of rating** |
| N_49 - N_69   | 107.0 % of rating |

112.8% against an allowance of 112.77% is the whole of it. Scaling every rating by `Vmin/Vmax`, which makes the admitted
apparent power `rateA * V_i / Vmax` and so never more than `rateA`, brackets the reference from the other side:

| ratings | objective | against the published 97,214 |
|---------|----------:|-----------------------------:|
| as given, current-based limit | 97,100 | -0.117 % |
| scaled by `Vmin/Vmax`         | 97,431 | +0.223 % |

The published value sits between the two, which is what a limit that is looser on one side and tighter on the other
should produce.

**Neither convention is wrong.** A thermal limit is a heating limit and heating follows the current, so writing it on
the current is the more physical of the two; a flat cap on apparent power is the more common. The point is only that the
two are not the same constraint, so an objective compared against pglib is not compared like for like unless the ratings
are adjusted. The SOC gap of section 15 is unaffected: it is measured between our own relaxed and exact solves, which
share the convention.

# 15. Validation against physics computed outside openTEPES

Every other check here compares the model against itself. The relaxation gap says the cone is closed; the envelope, the
band and the restoration all measure the model against its own definition of the relations they enforce. None of that
can detect a consistently wrong premise, and one had gone undetected through ten code reviews (section 16).

`prototypes/ac_formulations/validate.py` runs three checks on any solved AC case, cheapest first:

  * **branch residual** — the model's own branch flows against the textbook pi-model computed from its own voltages and
    angles. The formula is derived from scratch, so it depends on no openTEPES constraint.
  * **loop residual** — each branch's angle recovered from its own flows, summed around every independent cycle. The
    branch flow model works in `|V|^2`, `P`, `Q` and current; angles never appear in its core equations. On a radial
    network that is complete, on a meshed one the recovered angles must also close around every loop.
  * **power flow error** — the network rebuilt in pandapower from the same r, x, b and tap data, the setpoints
    openTEPES chose injected, and Newton-Raphson run. Other people's code, same inputs, same voltages or not.

## 15.1 Result on 9n_AC

| load level | dP [MW] | dQ [Mvar] | loop [rad] | dV [p.u.] | dAngle [rad] |
|------------|--------:|----------:|-----------:|----------:|-------------:|
| 01-01 01:00 | 0.00001 | 0.00006 | 4.3e-10 | **0.000000002** | **0.0** |
| 01-01 03:00 | 0.00001 | 0.00006 | 4.2e-10 | **0.000000002** | **0.0** |
| 01-01 05:00 | 0.00001 | 0.00006 | 4.1e-10 | **0.000000002** | **0.0** |

**The formulation is confirmed by an independent implementation**, with line charging, bus shunts and an HVDC candidate
all in play. This is the check that ten code reviews structurally could not perform.

## 15.2 Two traps in the validation itself, not the model

Both cost real time and both produced convincing wrong numbers:

**Use the susceptance actually in service, not the nameplate.** 9n_AC ships `Capacitor_1` as a candidate that the model
declines to build, so `vQShunt` is zero while `pBusBshb` still holds its 0.300 rating. Injecting the rating put 299
Mvar into the network that the solution never contained, and moved every bus voltage by 0.013 p.u. — which looked
exactly like a model error.

**HVDC links carry active power that must appear at both ends.** Leaving them out of the rebuilt network moves the
voltages too. It happened to change nothing on 9n_AC only because its DC candidate is not built.

A third false lead is worth recording: zeroing the line charging halved the voltage gap, which pointed hard at the
charging model. It was the shunt error interacting with it. An intermediate measurement that moves in the expected
direction is not evidence of the expected cause.

## 15.3 Result on RTS-GMLC, with real transformer taps

9n_AC has no off-nominal tap, so it cannot exercise the transformer path. RTS-GMLC does: 73 buses, 120 branches and 16
transformers at 1.015 and 1.03. Twelve hours of the peak week, restoration on:

| load level | dP [MW] | dQ [Mvar] | loop [rad] | dV [p.u.] | dAngle [rad] |
|------------|--------:|----------:|-----------:|----------:|-------------:|
| 08-23 02:00 | 0.00000 | 0.00000 | 7.6e-14 | **0.000000002** | 0.0 |
| 08-23 03:00 | 0.00000 | 0.00000 | 2.2e-13 | **0.000000002** | 1e-09 |
| 08-23 04:00 | 0.00000 | 0.00000 | 1.0e-12 | **0.000000002** | 1e-09 |

**The tap convention is confirmed against an independent transformer model.** `pLineTapFactor = 1/tau` applied to the
sending-end squared voltage matches what pandapower does with `vn_hv_kv = kv * tau`, on a meshed network with sixteen
of them. Until now that convention rested on a derivation and on `test_tap_reaches_the_voltage_drop`, which asserts the
same convention it was written from — it could not have caught an inverted tap.

Note the relaxation gap on this run: tight on all 120 branches at 3.61e-10, where the relaxed solve leaves 21 of 120
loose (section 12.2). That is the restoration pass doing its work on the case that needs it.

## 15.4 What is not yet covered

Both cases run here are single-period. Nothing has been validated across a multi-period build, where the investment
decisions and the period windows interact with the branch sets.

# 16. The angle relation had the wrong sign

The validation of section 15 first came back with the solutions not AC-realisable: the recovered angles missed closing
around the cycles by 0.634 degrees, which reads as a missing loop condition. That was the symptom. The cause was
simpler and worse: `eAngleEnvM` computed the envelope numerator as `x*P + r*Q`. It is a minus.

(Section 15 now reports the corrected model, so the failing numbers below are the historical ones.)

From `S_ij = V_i' conj((V_i' - V_j) y)` with `y = (r - jx)/z^2`:

    P = [(v_i^2 - v_i v_j cos th) r + (v_i v_j sin th) x] / z^2
    Q = [(v_i^2 - v_i v_j cos th) x - (v_i v_j sin th) r] / z^2

so `x P - r Q = (v_i v_j sin th)(x^2 + r^2)/z^2 = v_i v_j sin th`.

## 16.1 How it was found, and why nothing found it sooner

Comparing openTEPES's own branch flows against the textbook pi-model computed from openTEPES's own voltages and angles:

| | with `x P + r Q` | with `x P - r Q` |
|---|---:|---:|
| worst branch flow error | **38 MW / 3.3 Mvar** | **0.00001 MW / 0.00006 Mvar** |
| worst loop closure over 4 cycles | 0.634 deg | **6.1e-18 rad** |

Ten code reviews did not find it, and neither did the relaxation gap, the angle band, the envelope or the restoration
pass. Every one of those measures the model against **its own definition** of the relation. The error was only visible
against an equation derived independently. A self-consistency check cannot detect a consistently wrong premise.

The bad sign was also repeated in the module docstrings of `openTEPES_BoundTightening` and
`openTEPES_SettingUpVariablesAC`, so the comments agreed with the code and confirmed it to a reader.

## 16.2 What it changed

Fixed in `eAngleEnvM`, in the restoration's exact angle relation, and in the comments. Sections 12 to 14 were measured
again on the corrected model. The direction of every conclusion held; the magnitudes moved:

  * The loose cone on RTS is real: 21 of 120 branches before and after.
  * The relaxed plan understates its own cost by **57 %**, not 32 %.
  * The exact model no longer solves on RTS from a cold start, so there is no measured true optimum for that case.

## 16.3 Resolved

The Newton-Raphson gap that section 15 reported as open was in the validation script, not the model: it injected a
candidate shunt's nameplate rating for a device the model had declined to build. With that corrected the power flow
agrees to 2e-09 p.u. See section 15.2. `create_impedance` was suspected and was not the cause — rebuilding the lines
from explicit ohms changed the answer by nothing at all.
