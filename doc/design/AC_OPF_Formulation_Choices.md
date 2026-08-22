# Which AC formulations should openTEPES carry?

Written before Phase 3, because the answer changes how the flow equations are written. Third in the
series after `AC_OPF_Implementation_Plan.md` and `AC_OPF_Architecture_Review.md`.

> **Read §10 first.** Sections 1-9 were written before the two papers requested by the user were
> read. §10 records what those papers changed, including two conclusions below that are **wrong**:
> the dismissal of the branch flow model in §1 and §2, and the claim in §4 that cycle constraints do
> not transfer to AC. The rest still stands.

---

## 1. The design space

PowerModels.jl implements the widest set, and its taxonomy is the useful reference:

| Family | Members | Class | Bound? |
| --- | --- | --- | --- |
| Exact, non-convex | ACP (polar), ACR (rectangular), **ACT** (angle + W + voltage products, with a tangent constraint), IVR (current-voltage) | NLP / QCQP | no |
| Convex relaxation | **SOCWR** (Jabr, W-space), QCR / QCLS (quadratic-convex), SOCBF (branch flow), SDPWR, SparseSDPWRM | SOCP / SDP | **valid lower bound** |
| Approximation | **DCP** (what openTEPES has today), DCMP, DCPLL, NFA, BFA, **LPAC** | LP / QCP | no |

Two results from the literature prune this heavily.

**Bose & Low: the bus-injection and branch-flow models are equivalent, and so are their SOC
relaxations.** There is a bijection between the two feasible sets, so SOCBF (DistFlow) and SOCWR
(Jabr) give the *same* optimal value. Implementing DistFlow alongside SOCWR buys no bound quality —
only a second formulation to maintain. DistFlow is the natural form for radial distribution
feeders; openTEPES cases are meshed transmission.

**Radial versus meshed.** On a radial network every relaxation in the hierarchy collapses to the
same thing, so SOC is the right choice and nothing tighter is worth the cost. On a meshed network
SDP and chordal relaxations are strictly tighter than SOC — but an SDP with investment binaries is
not solvable at planning scale, so the tightening that is actually available to us is QC, not SDP.

## 2. What openTEPES specifically needs

Three requirements narrow the field further, and they are not the ones a pure OPF tool faces:

1. **Investment and switching binaries.** `vNetworkInvest`, `vGenerationInvest`, `vLineCommit`,
   and now `vShuntInvest`. So the formulation must survive inside a MIP.
2. **Duals for locational marginal prices.** `collect_duals` re-solves with binaries fixed and reads
   the dual of `eBalanceElec`. So the continuous relaxation must be one the solver can price.
3. **Full-year cases.** RTS-GMLC and NG2030 at hourly resolution. A formulation that cannot close
   in reasonable time on 8,736 load levels is a snapshot tool, not a planning tool.

Against those:

| Formulation | MIP-able | Duals | Full year | Verdict |
| --- | --- | --- | --- | --- |
| ACP / ACR (exact NLP) | no — ipopt cannot branch | no | no | **validator only**, binaries fixed |
| ACT (exact, tangent) | no | no | no | **validator only**, and it is the exact form of the tangent bounds below |
| SOCWR (Jabr) | yes, MISOCP in Gurobi | yes, after fixing | no | **primary** |
| QC | yes, MISOCP + linear cuts | yes | no | tightening switch on SOCWR, later |
| SDP | not at this scale | — | no | **skip** |
| SOCBF (DistFlow) | yes | yes | no | ~~skip~~ — **see §10.1: this dismissal was wrong for a MILP linearisation** |
| **LPAC** | **yes, MILP** | **yes** | **yes** | **second formulation, and the one that will actually run on a national case** |
| DCP | yes | yes | yes | the existing baseline |

## 3. The finding that changes Phase 3

LPAC looked like a separate formulation needing its own variables. It is not.

PowerModels' LPAC branch equation is

```
p_fr == (g+g_fr)/tm^2*(1.0 + 2*phi_fr)
      + (-g*tr+b*ti)/tm^2*(cs + phi_fr + phi_to)
      + (-b*tr-g*ti)/tm^2*(va_fr - va_to)
```

Put beside the exact W-space equation

```
P_ij = G*t^2*W_i - t*G*WC - t*B*WS
```

the two are **the same equation**. LPAC is the exact W-space branch equation under three
substitutions:

| | exact | LPAC linearisation |
| --- | --- | --- |
| `vW[i]` | \|V_i\|² | `1 + 2*phi_i` |
| `vWC` | \|V_i\|\|V_j\| cos(Δθ) | `cs + phi_i + phi_j` |
| `vWS` | \|V_i\|\|V_j\| sin(Δθ) | `Δθ` |

Since `vW = 1 + 2·phi` is affine in `phi`, the existing `vW` **is** the LPAC voltage variable; `phi`
never has to be declared. Substituting into the W-space definitions:

```
vWC == cs + (vW_i + vW_j)/2 - 1        with  cs <= piecewise-linear outer approximation of cos(Δθ)
vWS == vTheta_i - vTheta_j
```

Both are linear in variables Phase 2 already declared. `vTheta` is already there, and PowerModels
indexes its `cs` on bus pairs — the same set `mTEPES.bp` Phase 2 built.

**So the branch flow equations, the nodal balance, the apparent-power limit and the shunt
injections are written once and shared by every formulation. The formulations differ only in a
small block that defines what `vW`, `vWC`, `vWS` mean.** That is exactly Egret's split between
`declare_eq_branch_power` and `declare_eq_c` / `declare_eq_s` / `declare_ineq_soc`.

| `IndACModelType` | Name | Voltage-product block | Class |
| --- | --- | --- | --- |
| 0 | **SOCP** (Jabr) | `vW_i·vW_j >= vWC² + vWS²`, plus the tangent bounds of §4 | MISOCP |
| 1 | **LPAC** | `vWC == cs + (vW_i+vW_j)/2 − 1`, `cs <=` PWL cos envelope, `vWS == Δθ` | **MILP** |
| 2 | **NLP / ACT** | `vWC == √(vW_i·vW_j)·cos(Δθ)`, `vWS == √(vW_i·vW_j)·sin(Δθ)` | NLP, validator only |

A checkable consequence, verified numerically: **on a lossless branch at nominal voltage, LPAC
reduces exactly to DC power flow.** With `r = 0` and `phi = 0` the equation collapses to `P = Δθ/x`
to machine precision, and the error against the exact AC equation is 0.01 % at 2° and 4.7 % at 30°
— the expected small-angle behaviour. That gives Phase 3 a strong regression test: LPAC on a
zero-resistance network must reproduce the existing DC flows.

## 4. Cycle constraints: the question does not transfer

> **Superseded by §10.1.** The heading is wrong: cycle constraints *do* transfer, and are the
> subject of both requested papers. What survives is the narrower point that openTEPES's existing
> `CycleConstraints` code is DC-specific and cannot be reused verbatim, so the guard is still right.

openTEPES already has a cycle formulation (`pIndCycleFlow`, `NetworkCycles`, `CycleConstraints` in
`openTEPES_ModelFormulationElectricity.py:1094-1226`). It is worth being precise about what it is,
because the name invites a false analogy.

**What it is.** The DC formulation has two equivalent ways to impose Kirchhoff's voltage law:
carry `vTheta` and write `flow = Δθ/x` per branch, or eliminate `vTheta` and require
`Σ x·flow = 0` around each independent cycle. openTEPES implements the second and *deletes*
`eKirchhoff2ndLaw1/2` when it is switched on. It is a variable-elimination technique for the DC
model, not a physical addition. PyPSA uses the same cycle form as its only KVL.

**Why it does not carry over.** Under AC, `eKirchhoff2ndLaw1/2` are not built at all, so
`CycleConstraints` would try to delete constraints that do not exist. `pIndCycleFlow` and
`IndACPowerFlow` are mutually exclusive and the model should say so rather than fail obscurely.
*Implemented: `openTEPES.py` now raises a clear error if both are set.*

**The real AC analogue.** What a W-space relaxation genuinely loses is the loop condition: the
angle differences round a cycle must sum to zero. `vWC` and `vWS` on their own do not enforce it,
so a SOC solution on a meshed network may correspond to no consistent set of angles. The condition
is `Σ arctan(vWS/vWC) = 0` around each cycle — non-convex, so it cannot simply be added to the
relaxation. Three practical positions:

1. **Tangent bounds** (linear, cheap, weak): `vWS <= vWC·tan(θmax)` and `vWS >= vWC·tan(θmin)`.
   Valid, and they recover part of the consistency because `vTheta` is still in the model. This is
   what openTEPES_PRO does, and what Phase 4 will do.
2. **The ACT equality** (exact, non-convex): `vWS == vWC·tan(θ_i − θ_j)`. This is precisely
   PowerModels' ACT formulation — the exact model for meshed networks — and it is the natural form
   of the Phase 7 validator, since it reuses every variable already declared.
3. **Cycle-based valid inequalities on `vWC`/`vWS`** (Kocuk, Dey & Sun and successors). A real
   tightening, convex, and a sensible follow-on once SOCP is working. Not Phase 3.

The honest summary: **the tangent bounds are a partial substitute for the loop condition, not a
replacement, and that is why the NLP restoration in Phase 7 is required rather than optional.**

## 5. Polar, rectangular, or W-space?

W-space, and the reason is the binaries.

* **Polar (ACP)** carries `|V|` and `θ` with `cos`/`sin` of the angle difference. Trigonometric
  terms cannot be handed to Gurobi at all, so a polar model with investment binaries has no solver.
* **Rectangular (ACR)** carries `e`, `f` with `V = e + jf`, which removes the trigonometry and gives
  a QCQP — Gurobi can take it as a non-convex MIQCQP. But there is no relaxation hierarchy to step
  down to, `|V|²= e²+f²` reintroduces a non-convex equality, and the bound quality is not
  controllable.
* **W-space** makes every branch flow equation **linear in the decision variables**, which is what
  lets the same equations serve an LP, an SOCP and an NLP. The binaries enter through the existing
  big-M pattern with no bilinear products. It is also the only one of the three that yields a valid
  lower bound.

The one price: `vW` is the squared magnitude, so the voltage magnitude is `√vW` in SOCP/NLP mode but
`(1 + vW)/2` in LPAC mode, where `vW` is the linearisation `1 + 2φ` rather than a true square. The
output layer must know which formulation produced the solution. Recorded for Phase 6.

## 6. Recommendation

**Build two, plus a validator.**

* **`IndACModelType = 0`, SOCP (Jabr)** — the default. The only option that returns a valid bound,
  and the one to quote in a paper. For selected snapshots or a reduced set of representative load
  levels.
* **`IndACModelType = 1`, LPAC** — a MILP, so it inherits the existing solver settings, dual
  extraction and full-year scalability unchanged. This is what makes AC-aware planning usable on
  RTS-GMLC or NG2030 at all. Cheap to add because it shares every equation with SOCP.
* **`IndACModelType = 2`, NLP / ACT** — Phase 7 validator, binaries fixed, ipopt.

**Do not build**: SDP (does not scale with binaries), DistFlow / SOCBF (provably the same bound as
Jabr), IVR, NFA, rectangular ACR. **Defer**: QC as a tightening flag on SOCP once SOCP is working.

Renumbering note: Phase 1 shipped `IndACModelType` as 0 = SOCP, 1 = NLP. LPAC takes slot 1 and the
NLP validator moves to 2, so the numbering above is the one to implement.

## 7. What Phase 3 builds

Shared, written once, formulation-independent:

* `eBalanceElec` — the AC branch of the existing constraint, keeping its name
* `eBalanceReact` — the reactive counterpart
* `eFlowElecFrw/Bck`, `eFlowReactFrw/Bck` — the four branch equations in `vW`, `vWC`, `vWS`
* `eApparentPower` — `vFlowElec² + vFlowReactFrw² <= pLineSmax²` at both ends
* `eLineLossesAC` — `vLineLosses == 0.5·(vFlowElec + vFlowElecBck)`
* `eShuntQInjection`, `eReactiveOutput` bounds and the power-factor limits

Formulation-specific, one small block each: the voltage-product definitions of §3.

Phase 4 then becomes a matter of registering a different block, not rewriting the model.

## Sources

- [Equivalent relaxations of optimal power flow (Bose & Low)](https://arxiv.org/abs/1401.1876)
- [Branch Flow Model: Relaxations and Convexification, Part I (Farivar & Low)](https://arxiv.org/pdf/1204.4865)
- [PowerModels.jl formulation details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)
- [PowerModels.jl LPAC implementation](https://raw.githubusercontent.com/lanl-ansi/PowerModels.jl/master/src/form/lpac.jl)
- [Egret transmission model library](https://raw.githubusercontent.com/grid-parity-exchange/Egret/main/egret/model_library/transmission/branch.py)

---

# 10. Revision after reading the two requested papers

Two papers were checked. One is available in full locally, the other is not.

**[A] Chowdhury, Kamalasadan & Paudyal (2024).** "A Second-Order Cone Programming (SOCP) Based
Optimal Power Flow (OPF) Model With Cyclic Constraints for Power Transmission Systems."
*IEEE Transactions on Power Systems* 39(1), 1032-1043. DOI 10.1109/TPWRS.2023.3247891.
**Not obtained** — IEEE paywall, no preprint found. What is known comes from the abstract, the
author's 2023 UNC Charlotte dissertation abstract, and the use made of it in [B]: the model defines
a **convex envelope on the relative bus voltage angles** that satisfies the cyclic constraint for
any mesh, on a branch-flow SOCP-OPF, tested on IEEE 14, 57, 118, 500 and 2736-bus systems, and
reported to outperform NLP-OPF and SDP-OPF. **The actual constraint equations are not in hand.**

**[B] Alvarez, López, Olmos & Ramos (2024).** "An optimal expansion planning of power systems
considering cycle-based AC optimal power flow." *Sustainable Energy, Grids and Networks* 39,
101413. DOI 10.1016/j.segan.2024.101413. **Full text read** from
`~/resources/papers/capacity_expansion/`.

[B] takes the cycle constraints of [A], **linearises them**, and embeds them in integrated
expansion planning. Its cycle classification comes from Neumann & Brown, *Transmission expansion
planning using cycle flows* (e-Energy 2020) — which is the same reference openTEPES's own
`NetworkCycles` implements for the DC model.

## 10.1 Two conclusions in this document were wrong

**"Skip the branch flow model."** Wrong for this repository. The Bose & Low equivalence cited in
§1 is about the bound quality of the **SOC relaxation** of the two models, and on that point it
still holds. It says nothing about which model is better to **linearise into a MILP**, which is what
[B] does. In a MILP the branch flow model has concrete advantages: the squared current magnitude
`i²` is a natural variable, the thermal limit is the clean box `0 <= i²/(S̄/V̲)² <= 1` (eq. 7), and
the one non-convex equation `(f^P)² + (f^Q)² = v² i²` (eq. 4) takes a straightforward piecewise
linearisation. [B] is a branch-flow model, and it is the group's own published method.

**"Cycle constraints do not transfer to AC."** Wrong — that is the subject of both papers. What
survives is the narrower and still-correct point: openTEPES's *existing* `CycleConstraints` code is
DC-specific (it operates on `vFlowElec` with `pLineX` and deletes `eKirchhoff2ndLaw1/2`) and cannot
be reused verbatim, so the guard added in `openTEPES.py` is still right. But the *concept* transfers
directly, and openTEPES already carries most of the machinery [B] needs.

## 10.2 What [B] actually formulates

A linear branch-flow AC-OPF, MILP, over 8736 consecutive hours, with unit commitment, storage,
operating reserves, and investment in generation, storage, lines, **synchronous compensators and
capacitor banks**. Validated on **RTS-GMLC** — a case already bundled with openTEPES.

| | equation | note |
| --- | --- | --- |
| Active / reactive balance | (1a), (1b) | reactive balance includes lines, compensators, capacitor banks |
| Voltage magnitude drop | (2a)-(2c) | disjunctive for candidate lines |
| Voltage angle differences | (3a)-(3c) | **replaced by the cycle constraints** |
| Current flow | (4) | `(f^P)² + (f^Q)² = v² i²`, piecewise-linearised |
| Line reactive injection | (5) | |
| Capacitor banks | (6a)-(6c) | `q^shc = v² B^sh`, disjunctive for candidates |
| Current bounds | (7) | `0 <= i²/(S̄/V̲)² <= 1` |
| **Cycle constraints** | (8a)-(8e), (9a)-(9f) | angle differences as a directed linear combination over branches via the incidence matrix `H_ijc,k` |
| Bound tightening | §2.3 | Coffrin et al. propagation on `v²` and `θ` bounds |

The linearisation is `v² = 1.0` and `sin(Δθ) = Δθ` in the angle-difference equations — **the same
small-angle, flat-voltage step as LPAC in §3**, so the analysis there was consistent; the difference
is the variable space, not the approximation.

Two cycle sets, exactly openTEPES's existing split: `C_e` the cycle basis of the existing network,
`C_c` the cycle basis of the full network minus `C_e`. openTEPES already builds these as
`mTEPES.nce` / `mTEPES.ncd`, with `cye` / `cyc`, `ucte` / `uctc`, `lcac` and `pBigMTheta`
(`openTEPES_ModelFormulationElectricity.py:1094-1166`). A candidate cycle's constraints are enforced
only when at least one line is built on every branch of the cycle that has no existing line.

Reported results: omitting the AC-OPF raises total system cost by **7.10-9.57 %**, omitting unit
commitment by **6.29-8.39 %**; cycle constraints together with bound tightening cut solve time by
**17.67-27.21 %**.

## 10.3 What this does to Phase 2

Most of it survives, because the branch flow model and the bus-injection model share the node and
branch quantities:

| Phase 2 variable | Branch flow model | Verdict |
| --- | --- | --- |
| `vW` (psnnd) | `v²_ni` | **keep** — same quantity |
| `vFlowElec`, `vFlowElecBck` | `f^P` | **keep** |
| `vFlowReactFrw`, `vFlowReactBck` | `f^Q` | **keep** |
| `vTheta` (pre-existing) | `θ_ni` | **keep** |
| `vQShunt` (psnsh) | `q^shc`, capacitor banks | **keep** — Phase 1's shunt sets are what (6a)-(6c) need |
| `vReactiveTotalOutput` (psngq) | `q_ng` | **keep** |
| `vWC`, `vWS` (psnbp) | — | **drop**: these are bus-injection W-space and have no counterpart in a branch flow model |
| — | `i²_nijc`, squared current per branch | **add**, on `psnlaa` |
| — | piecewise-linearisation variables for (4) | **add** |

**The bus-pair finding of the architecture review §9.2 falls with `vWC`/`vWS`.** It was specifically
about indexing the voltage products, and a branch flow model has none. The 53 % cone reduction
measured on NG2030 does not apply to a branch-flow MILP. Everything else from that review stands
unchanged: the three naming contracts, the no-flag-tests-inside-rules rule, and the
`FORMULATION_REGISTRY`.

## 10.4 Recommendation

**Target [B] — the linear branch-flow, cycle-based AC-OPF — as the primary formulation**, for four
reasons that are specific to this repository rather than general:

1. It is a **MILP**, so it inherits the existing solver settings, dual extraction and the full-year
   scalability openTEPES cases need. The SOCP cannot close on 8736 hours.
2. It was **validated on RTS-GMLC**, which ships with openTEPES.
3. openTEPES **already has the cycle machinery** it depends on, from the same Neumann & Brown
   source.
4. It covers **capacitor banks and synchronous compensators**, which are exactly the `sh` / `shc`
   and `sq` / `sqc` sets Phase 1 built.

The bus-injection SOCP of §6 remains worth adding later as the rigorous lower bound to quote
against, but it is the second formulation, not the first.

**Blocking on [A].** [B] states that it only replaces the angle-difference constraints (3a)-(3c)
with the cycle constraints "taking as a reference the cycle constraints provided in [14]", and the
convex envelope on the relative bus voltage angles is [A]'s contribution. Equations (8) and (9) can
be read from [B], but the envelope's derivation and the validity argument are in [A]. Implementing
(8)-(9) without it means reproducing equations without understanding what makes them tight.
**The PDF of [A] is needed before Phase 3.**

---

# 11. Paper [A] read in full

Obtained 2026-08-19, filed at
`~/resources/papers/methods/[2024_IEEE TPS_Chowdhury] A second-order cone programming (SOCP) based optimal power flow (OPF) model with cyclic constraints for power transmission systems.pdf`.

It is a **branch flow model**, confirming §10. Variables: `u_i = |V_i|²`, `l_ij = |I_ij|²`,
`P_ij`, `Q_ij`, `θ_ij`.

| | equation | class |
| --- | --- | --- |
| Voltage drop | (9) `u_j = u_i − 2(r_ij P_ij + x_ij Q_ij) + (r_ij² + x_ij²) l_ij` | linear |
| Active balance | (11) `P_j^g − P_j^d = Σ_{k:j→k} P_jk − Σ_{i:i→j} (P_ij − r_ij l_ij) + g_j u_j` | linear |
| Reactive balance | (12) same with `x_ij l_ij`, `b_j u_j` | linear |
| Exact current | (13) `l_ij = (P_ij² + Q_ij²) / u_i` | **non-convex** |
| Conic relaxation | (14) `u_i + l_ij >= ‖[2P_ij, 2Q_ij, u_i − l_ij]‖₂` | **SOC** |
| Cyclic constraint | (15) `Σ_{cycle} θ_ij = 0` | linear |
| Angle-power link | (6) `V_i V_j sin θ_ij = M`, `M = (B_ij P_ij − G_ij Q_ij)/(G_ij² + B_ij²)` | `M` is **linear in P, Q** |
| **Angle envelope** | (16) `θ_ij >= M / (V̄_i V̄_j cos(θ^m/2)) − tan(θ^m/2) + θ^m/2`<br>(17) `θ_ij <= M / (V̲_i V̲_j cos(θ^m/2)) + tan(θ^m/2) − θ^m/2` | **linear** |

with `θ^m = max(|θ̲_ij|, |θ̄_ij|)`.

**The envelope is the answer to the gap §4 identified.** Appendix A derives it from the standard
polyhedral sine envelope (Molzahn et al. survey):

```
sin θ_ij <= cos(θ^m/2)·(θ_ij − θ^m/2) + sin(θ^m/2)
sin θ_ij >= cos(θ^m/2)·(θ_ij + θ^m/2) − sin(θ^m/2)
```

then substitutes `sin θ_ij = M / (V_i V_j)` from (6) and divides through. Because `M` is linear in
the branch flows, (16)-(17) tie `θ_ij` to `P_ij` and `Q_ij` **linearly**, which is what makes the
cyclic constraint (15) — itself linear in `θ_ij` — bite. So the whole angle-consistency apparatus is
SOC + linear: exactly the convex loop condition §4 said was unavailable. **§4's pessimism was
wrong, and this is why.**

Note: that same sine envelope is already in openTEPES_PRO as `eSN_R_upper_bound` /
`eSN_R_lower_bound`. PRO had the ingredient but not the link to a cyclic constraint.

Two implementation details worth carrying over:

* **Cycle selection.** Cycles come from an adjacency matrix, and **when a branch belongs to several
  meshes the shortest is used**. openTEPES uses `nx.cycle_basis`, which does not guarantee shortest
  cycles. Worth measuring — cycle length drives the density of (15).
* **Envelope width.** The paper's Table V studies the sensitivity of the solution to `θ^m`. It is a
  tightness knob, not a fixed constant, and belongs in the prototype sweep.

Tested with MOSEK on IEEE 14/57/118/2736-bus and a synthetic 500-bus, against MATPOWER's NLP and
SDP OPF; the SOCP solution is reported to match the SDP global optimum.

## 11.1 Consequence for the prototype study

Papers [A] and [B] are the same model at two points on the accuracy/cost curve: [A] keeps (14) as a
cone (SOCP, exact-ish, slower); [B] piecewise-linearises it (MILP, faster, approximate). That is
precisely the trade-off to measure, so the sweep is:

| # | Prototype | Non-convexity handling | Angle consistency | Class |
| --- | --- | --- | --- | --- |
| 1 | DC | — | KVL on θ | LP |
| 2 | DC + loss factor | fixed loss factor | KVL on θ | LP |
| 3 | BFM-SOCP, no cycles | cone (14) | none | SOCP |
| 4 | **BFM-SOCP + cycles** = [A] | cone (14) | (15)+(16)+(17) | SOCP |
| 5 | **BFM-LP + cycles** = [B] | piecewise linear | (15)+(16)+(17) | LP |
| 6 | BIM W-space SOCP (Jabr) | rotated cone | tangent bounds only | SOCP |
| 7 | LPAC | — | Δθ, PWL cos | LP |

Measured against a true AC OPF and a true AC power flow, on 9n_AC first, then the survivors on
RTS-GMLC.
