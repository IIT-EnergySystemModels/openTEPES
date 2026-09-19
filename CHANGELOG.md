# Change Log

## [4.19.0rc] - 2026-09-18 Unreleased in PyPI

- [ADDED] write file of marginals of the system inertia constraint.
- [CHANGED] the continuous-integration workflow executes its automated checks concurrently, `-n auto` with one solver thread per process: on a
  ten-core machine the unit tier falls from 429 s to 193 s and the solve tier from 285 s to 114 s. flake8 moves to a job of its own, the unit matrix
  falls from nine combinations to seven, and the ipopt job requests ipopt alone from conda. No check is removed.
- [ADDED] automated checks for the four modelling options that no distributed case activates: line switching, operating reserve activation, ramp
  reserves, and the incompatibility between charging and energy outflows (issue #177). Two findings came out of writing them. The ramp reserve tables
  of sSEP are empty, so the requirement is zero at every load level and the constraint is skipped. And sSEP serves none of its hydrogen: at 300
  EUR/tH2, below the cost of the 50 MWh of electricity a tonne requires, all 425.6 tH2 of the week are unserved and the electrolyzers consume nothing.
  A check records that behaviour and fails once the case is repriced.
- [FIXED] change the H2 pipeline capacity and H2 flow from tH2 to tH2/h.
- [FIXED] a candidate hydrogen pipeline or heat pipe carries flow only once it is built, closing issue #183. The flow bounds followed the rating of
  every physical pipeline, candidate or not, so a cost-minimising model built none of it and used it in full, and the investment cost then read 0.0.
  `eNetCapacity1` and `eNetCapacity2` now bound the candidate flow by the capacity built, in per unit of the rating, as for a candidate circuit. On a
  one-week `sSEP` with its 15 hydrogen pipelines declared candidates and the expansion declined, a pipeline carried 13.4 tH2/h, its full rating, and
  now carries none. No distributed case defines a candidate pipeline, so no published result moves. Reported by Erik Alvarez.
- [CHANGED] the hydrogen module is written in rates, as the electricity module is. Every hydrogen variable holds tH2/h at a load level and only the
  inventory remains a stock in tH2; `eBalanceH2` carries no `pDuration`, and the duration enters `eH2Inventory` and the two cost terms through
  `pLoadLevelDuration`. Nothing moves on a case with one-hour load levels; on an aggregated case a flow is now the rate, not the tonnes moved over the
  load level. Three defects are corrected. The hydrogen price was multiplied by the stage weight, the dual of `eBalanceH2` being divided by the period
  probability alone: on `9nH2` aggregated to four-hour load levels at a stage weight of 13 it read 26.74 EUR/kgH2 against the 2.06 EUR/kgH2 the
  marginal electricity and the electrolyzer production function imply. The pipeline utilization on the network map compared an amount against a rate.
  And `vH2NS` at a busbar isolated from the hydrogen system was fixed to the demand rate while the variable held tonnes. The two flow columns of the
  hydrogen balance tables carried no stage weight, so on the 7-day `sSEP` a pipeline at its rating entered the yearly table at 53.6 tH2 beside a
  demand column of 74.9 tH2; both columns now carry `pLoadLevelDuration`. Asked for by Andres Ramos.
- [FIXED] the AC power flow residual check was skipped on every case carrying an HVDC scheme. `angles_available` required an angle at each node, and a node no
  AC branch touches has none; it now considers only the nodes an AC branch touches.
- [FIXED] the voltage-angle writer put an HVDC pole on the reference. It writes a blank where a node has no angle, not a zero.
- [FIXED] an AC run returned no duals. Gurobi withholds them on a quadratically constrained model unless `QCPDual` is set, so a case with no integer variable
  solved to optimality and then failed retrieving `Pi`; it is now set whenever the AC model is on.
- [ADDED] per-busbar voltage limits, through an optional `oT_Data_BusVoltage` table of `Node`, `VMin` and `VMax`, applied after the branch propagation so that a
  recorded setpoint wins over the band the impedances imply. Equal limits pin a busbar. AC-only, so no DC case is affected.
- [FIXED] the voltage-angle bound warning counted nodes whose angle nothing determines. A candidate line left unbuilt leaves its far node adrift and the
  solver parks its angle at a bound. Those nodes are now reported separately, not as a binding bound. Reported by Andres Ramos.
- [FIXED] writing the results failed on a case where every unit sits at its upper bound. The generation surplus table pivoted an empty frame and
  raised KeyError: 'level_0'. It is now skipped when there is no surplus, as the ramp surplus tables beside it already were.
- [FIXED] the voltage angle table reported a number for busbars that have no angle. A busbar no circuit acts on, an HVDC pole or the far end of a
  candidate circuit left unbuilt, is written `N/A`, not at whatever bound the solver left it. A synchronous area carrying no angle reference keeps its
  angles, which are real up to a common offset.

## [4.18.19] - 2026-09-16
- [FIXED] typo in openTEPES.py


## [4.18.18] - 2026-09-16

- [ADDED] the nodal voltage angle bound is configurable, through `--max-theta` or a setting outside the case files, and the candidate-circuit Big-M is
  derived from it. The bound was fixed in the code at `pi/2` and applies to the nodal angle, not to the difference across a circuit, so on a wide
  network with one angle reference it caps the angle accumulated out to the periphery and can bind while every circuit is well inside its own limit,
  clipping the DC optimal power flow silently. On an 84-busbar European case it was binding in 2462 (period, scenario, load level, busbar) entries.
  The Big-M in the candidate-circuit disjunction was a separate literal `pi`, valid only at the former bound; both now come from one call. With
  nothing set the behaviour is unchanged, and a value that is not a positive number is ignored with a warning. The near-binding warning reports the
  bound in radians and is skipped under the cycle formulation, whose `pBigMTheta` is built from the reactances and ratings around each cycle and needs
  no angle bound.

- [FIXED] the hydrogen source cost is annualised by the stage weight, as the reliability cost already was. `eTotalH2SrcCost` was the second term with
  no scaling, so a tonne from a reformer cost a stage weight less than the electricity to electrolyze the same tonne, and the model reformed in
  preference to building. No distributed case defines a hydrogen source. On an 84-busbar case at a weekly stage the plan moved, not only the cost:
  reforming from 80 % of supply to 65 %, electrolyzer capacity up 71 %, turbine halved.
- [FIXED] energy neutrality pinned a lossy storage unit idle. `eESSInventory` stores `sqrt(Efficiency)` of the energy taken and drains
  `output/sqrt(Efficiency)` to deliver, so a closed cycle gives output = Efficiency x charge, while neutrality required output = charge; below 100 %
  efficiency the only feasible point is zero. On `9n`, whose `ESS1` is 90 % efficient, charge and discharge came out at 0.0000 against 0.0629 and
  0.0566 without the constraint, and the cost rose because the system lost the arbitrage. The constraint now carries the losses, and a 90 % unit cycles again at output = 0.9 x charge. `EnergyNeutrality` is
  documented in `InputData.md`, where it did not appear; four automated checks now exercise it.

- [FIXED] a storage cycle longer than its stage is rejected, not dropped, closing issue #159. Enforcement requires the position of the load level to
  divide by the cycle length, so when none qualifies the constraint is built with no rows and the reported cost falls below the true one, 10.4 % low
  on the energy limit measured in the issue. The error names the unit, the period, the content of a stage and the two remedies. Seven cycles are
  covered. No distributed case is affected, the fault requiring a shortened horizon. `InputData.md` gives the shortest stage each period requires, and
  notes that `StorageType` records the state of charge one period more often than its name suggests.
- [ADDED] openTEPES reports when the storage cycle of a unit is shorter than its own column requested. The cycle is the shortest of the storage,
  outflows and energy periods, so a setting made for one feature moves another. On `9n` every unit resolves to one load level whatever `StorageType`
  states, that case carrying neither outflows nor energy bounds. Behaviour unchanged, and until now invisible.

- [ADDED] a `.gitattributes` giving `CHANGELOG.md` the union merge driver. Two branches that each add an entry conflicted on every merge, since both insert at
  the top of the same section while never overlapping, so the resolution was always to keep both. `union` does that on its own and is built into git, so no
  clone needs setting up.
- [ADDED] `RTS-GMLC_Oper` to the solve suite. It ships but no test solved it, so the operation-only path was covered on no case carrying commitment binaries.
  About 30 s and 1.1 GB under the 7-day fixture.
- [CHANGED] the note deferring `RTS-GMLC_6y` carries the measurement it requested. Reading and configuring the case costs 5.3 GB and 85 s before the
  solve, and solving it peaked at 11.4 GB without terminating in seven minutes; runners hold 16 GB, or 14 GB on macOS. The floor is reading six periods
  of full-year tables, not solving, so no shorter horizon helps: at this horizon the model is already small, 546 load levels. Coverage of that layout
  at this scale requires a smaller case distributed as data.

- [FIXED] `9nH2` requested 20 tH2/h at Node_1, five times the output of its 200 MW electrolyzer at 49.02 kWh/kgH2. Four fifths returned as hydrogen
  not served, so the penalty was the whole objective, 26,753 MEUR over seven days against 6.4 MEUR. Demand is now 2 tH2/h; 20 tH2/h would require 980
  MW, two thirds of the system peak. A new check confirms the demand is served.
- [ADDED] a test that solves `9nH2x`, which nothing solved before. It checks the case solves and its hydrogen balance closes. The hydrogen side is idle at a 41
  % round trip, but that is an economic outcome and is not pinned.
- [CHANGED] CI installs conda in one job instead of thirteen. Only the Linux solve job needs it, for ipopt; the rest wanted only `flake8` and `pytest`, which
  pip provides, and a failed conda setup was failing jobs that never reached a test. That job is now separate and named for it, and the shared setup is one
  composite action.
- [CHANGED] an in-progress CI run is superseded only on a pull request. A master run is the record for master.
- [ADDED] `9n_duckdb` to the bundled case list on the Download page, which completes it. Listed next to `9n`, and said to be the same inputs in a different
  container instead of a different system, which the name alone suggests.

- [ADDED] six missing cases to the distributed case list on the Download page. `9nH2` and `9nH2x` arrived with the hydrogen subsystem and neither was
  documented: `9nH2` carries the whole chain as separate units, an electrolyzer, a storage cavern and a hydrogen-fired turbine, against a hydrogen
  demand at one busbar, while `9nH2x` keeps the units, removes the demand and raises every thermal variable cost tenfold. The four this branch adds
  are `9n_AC`, `RTS-GMLC_AC`, `RTS-GMLC_AC_Oper` and `RTS-GMLC_Oper`.

- [CHANGED] `prototypes/ac_formulations/` is no longer part of the repository. It held the formulation study that selected the branch-flow cone over
  the piecewise-linear model, research apparatus and not model code, and its `reference.py` required pandapower, which openTEPES does not depend on.
  The one file the check suite uses, the MATPOWER reader behind the pglib-opf case118 benchmark, moves to `tests/pglib.py`, where it is a plain
  import. The study is kept with the AC design notes.

- [CHANGED] the `9n_H2` case is now `9n_ELZ`. Master gained a `9nH2` case for the hydrogen subsystem, and two names differing only by an underscore
  invite the wrong starting point. The old name was also inaccurate: the case carries no hydrogen demand and no hydrogen network, and the carrier is
  inactive. It represents two electrolyzers as the documented Electrolyzer (ELZ) unit type, with storage, electric energy outflows, and the hydrogen
  demand expressed as the electricity they must draw. Only the name changes, and the Download page entry now states what the case does.

- [FIXED] `IndHardZeroENS` forbade unserved energy and not the reactive shortfall, so an AC adequacy assessment answered half the question: the model
  remained feasible by purchasing reactive power it never sourced, at `pENSCost`, and reported itself adequate. `vQNSPos` is now fixed at zero
  alongside `vENS`. `vQNSNeg` is not. It is a surplus the system could not absorb, with no counterpart on the active side, and forbidding it would
  make the reactive balance a hard equality and turn light-load line charging into an infeasibility.

- [FIXED] a portfolio study could not exclude a candidate shunt compensator or synchronous condenser. `apply_investment_bounds` re-applies the
  investment bounds to a built model, but covered generating units, retirements and circuits alone, and the four reactive bound parameters were not
  declared mutable, so setting `pShuntUpInvest` to zero on a built model raised, and anything catching the error left the capacitor available with
  nothing to indicate it. The parameters are mutable and the function covers both reactive families, skipping them when their variables do not exist.

- [CHANGED] four AC checks requested gurobi and were skipped on every runner, the distributed licence being size limited. They use ipopt, which a
  runner holds: the condenser pair, the voltage-source converter and the angle guard. Five converter checks still request gurobi for the
  flow-direction binary, which a non-linear solver relaxes; those remain without runner coverage.
- [ADDED] automated checks for the synchronous condenser, which no distributed case carries. One builds an existing condenser and confirms it supplies
  reactive power inside its declared band; the other builds a candidate whose `InvestmentUp` is 0 and confirms it is buildable, the reading every
  other device family uses. A unit must be declared in `oT_Dict_Generation` and its technology in `oT_Dict_Technology`, not only added to the data
  table, or it never reaches the model.
- [FIXED] a case without AC power flow carried the AC current penalty variable. `vTotalNPenalty` was declared for every case and added to the
  objective unconditionally, while the constraint defining it is skipped when AC is inactive, so a DC model held one unconstrained column per load
  level priced in the objective. They optimise to zero, so the reported cost was correct, but they alter what the solver presolves. Both now exist
  only under `IndACPowerFlow = 1`.
- [FIXED] the cost summary gained two AC rows, `Investment Cost Reactive` and `AC Current Penalty (not in total)`, on every case including those with no AC
  power flow, where both were zero. A file that every case writes changed shape. The rows are written only when AC is on.
- [CHANGED] the README described the network model as DC power flow and the ohmic losses as proportional to the flow. Both are now conditional: an AC
  power flow is named as an alternative, inactive by default, the losses follow the exact relation under it, and the result topics list the voltage
  magnitudes, reactive flows, shunt injections and the reactive-power marginal.
- [ADDED] three single-line diagrams in the AC section of the mathematical formulation, drawn in the style of the existing hand-drawn figures: one AC
  branch with its tap, series impedance and charging susceptance; an HVDC link under both converter models with the reactive power and station losses
  at each terminal; and the capability disc of one terminal with the twelve tangent lines representing it. Symbols follow the notation table,
  parameters in blue and variables in red.
- [CHANGED] the AC work adds no new files. Reading and bound tightening sit in `openTEPES_InputData.py`, the network matrices and AC set-up in
  `openTEPES_DataConfiguration.py`, the AC variables in `openTEPES_SettingUpVariables.py`, the branch flow and bus injection formulations, the
  converter models and the restoration pass in `openTEPES_ModelFormulationElectricity.py`, and the AC results in `openTEPES_OutputResultsNetwork.py`.
  Seven modules became none. The function names and their callers are the same; only the file changes.
- [CHANGED] two AC result files are renamed to match their families. `NetworkReactiveNotServed` is `NetworkQNS`, matching `NetworkENS`, `NetworkPNS`
  and `NetworkHNS` and the variables `vQNSPos` and `vQNSNeg`. `NetworkUtilizationAC` is `NetworkElecUtilizationAC`, placing the carrier first as in
  `NetworkElecUtilization` and `NetworkHeatUtilization`. Neither name has been released.
- [CHANGED] the Linux solve job installs ipopt, so the AC formulations it could not reach are exercised. HiGHS cannot express a non-linear constraint,
  which left the second-order cone, the exact non-linear model and the AC restoration pass skipped on every runner, the cone being the default. A
  conic solver is not needed: the relaxation is convex, so a local optimum is the global one, and on the 9n case the two agree to 3e-07 relative.
  Linux only, the convergence of ipopt depending on how MUMPS was built. This confirms the paths build and solve; it does not stand in for a conic
  solver certifying the bound.
- [CHANGED] the test that checks the restoration pass closes the cone asked for gurobi, which no runner has a license for, so it was skipped everywhere and the
  pass had no CI coverage even after ipopt arrived. It uses ipopt now: the outer solve is the cone, which is convex, and the pass itself already ran on ipopt.
- [FIXED] the architecture diagram drew the Mode C arrow, from `resolve.py` back to `SettingUpVariables.py`, outside the page background, which
  stopped 45 px short of the canvas. The arrow is routed inside it and its rotated label removed, the sweep-modes panel carrying the same words. Its
  two corners were single quadratic curves spanning the whole segment, one bend sweeping 435 px and the other 27 px; they are now quarter turns of
  equal radius with straight runs between. The footer no longer runs off both edges.
- [CHANGED] the wording in the architecture diagram describes the design instead of asserting it: "single source of truth" becomes "column and type
  specs", "drop-in backend" becomes "same InputSource interface", and "cost: solve only (cheapest)" drops the judgement. The five planned boxes were
  checked against the code and remain planned: `parquet_source.py`, `mcda.py`, the district cooling and CCUS sector files, the sets-against-params
  split in `InputData`, and the `cli.py` / `run.py` split, whose work is done today by `openTEPES_Main.py` and `openTEPES.py`.
- [FIXED] the bus injection formulation in W space failed intermittently with the loop condition inactive. `vTheta` appears in no constraint there, so
  the solver sets some busbars and leaves others unset, and which ones varies between solves. The guard deciding whether a nodal voltage phasor can be
  formed returned on the first busbar it found, so whenever that busbar carried a value it reported the angles available and the residual check then
  built a phasor from `None` at a later busbar and raised `TypeError`. It now tests every busbar. This is what made `IndACPowerFlow = 2` with
  `IndACCycle = 0` fail once in every few passes of the check suite.
- [ADDED] HVDC converter station losses, set per case with `ConverterNoLoadLoss` and `ConverterMarginalLoss` in `oT_Data_Parameter`. Each terminal of
  a DC link carries a station, and each station is charged separately: the no-load part while the link is in service, as a fraction of the link
  rating, and the marginal part on the power the station carries in either direction. Both default to zero. Reported per link in
  `oT_Result_NetworkConverterLosses`, and read only when `IndACConverter` selects a converter model. Activating a loss also brings in the
  flow-direction binary the line-commutated model already uses, without which the model can inflate both halves of the link flow and discard surplus
  energy into a loss that does not exist.
- [CHANGED] the architecture diagram (`doc/img/openTEPES_architecture.svg` and the rendered `.png`) matches the code after the AC work. Layer 4 reads
  eight files instead of six, with a new `ELECTRICITY NETWORK — pick one` bracket under `…Electricity.py` holding the three interchangeable network
  models, labelled DC, BF and BIM; the middle box read AC, which is wrong beside BIM, bus injection being an AC model too. The functions keep their
  `AC` names, `NetworkACOperationModelFormulation` and `NetworkACCurrentModelFormulation` running for every AC mode. Layer 6 names the AC results
  inside `…Network.py`, and Layer 3 states which of its modules gain AC code when `IndACPowerFlow > 0`. No other layer changes.
- [ADDED] AC optimal power flow, activated with `IndACPowerFlow`. Branch flow model; the current definition is a second-order cone, a piecewise
  staircase or the exact non-linear equation (`IndACModelType`). Adds voltage and angle bound tightening, bus shunts, generating unit reactive
  capability and synchronous condensers. `IndACRestore` re-solves the network at the exact equations on ipopt to recover a physical operating point.
  New cases `9n_AC`, `RTS-GMLC_AC`, `RTS-GMLC_AC_Oper`, `RTS-GMLC_Oper`. Refused with cycle flow, single busbar, variable TTC and PTDF. Inactive by
  default.
- [FIXED] an HVDC converter was bounded separately in active and reactive power, so a station could hold both at their limits at once and deliver 17.6
  % more apparent power than its rating at the default power factor of 0.85. The rating now bounds the apparent power through a ring of tangent lines,
  so `IndACModelType = 1` remains a mixed-integer linear problem. The bound is loose by 3.5 % for a voltage-source converter and exact for a
  line-commutated one.
- [ADDED] HVDC converter models, `IndACConverter`: line-commutated draws reactive power at both terminals, voltage-source supplies or absorbs it within the
  converter rating. `ConverterPF` sets the power factor.
- [FIXED] the AC angle-to-flow relation used `x*P + r*Q`; it is `x*P - r*Q`. Branch flows were wrong by up to 38 MW and the recovered angles did not close
  around network loops.
- [FIXED] `IndACPowerFlow` is now read from `oT_Data_Parameter` as well as `oT_Data_Option`. A case that put the indicator in the wrong table built an AC model but
  skipped the reactive demand and shunt tables, and reported the result as solved.
- [ADDED] hourly on/off state for bus shunts, with a `Switchable` column in `oT_Data_BusShunt`. A bank can be opened at light load instead of wired in all year.
  `IndBinShuntSwitch` picks a discrete state, the default, or a relaxed one. Devices stay fixed unless marked, so existing cases are unchanged.
- [ADDED] stepped shunt banks, with a `Units` column in `oT_Data_BusShunt`. `Units = N` gives a bank of N identical units, so the model chooses how many are in
  service. Follows the VAR source model of Alvarez, Paredes and Rider, IET Generation, Transmission and Distribution 13(13), 2019. Units are chained to remove
  equivalent permutations. One unit by default.
- [ADDED] `--option Key=Value` overrides an entry of `oT_Data_Option` or `oT_Data_Parameter` for a single solve. Repeatable and comma-separated, so
  one case can be solved under several formulations without copying it; the distributed `9n` and `9n_AC` differ by two cells and are otherwise the
  same 34 MB. Activating the AC model this way also reads the AC-only input files, so an overridden solve reads what a case with the option set would.
- [ADDED] `IndCycleFlow`, `IndCompleteProblem`, `IndSectorDecomposition` and `IndSequentialSolving` can now be set from `oT_Data_Option`. They were fixed in the
  code, so no case could select them, and the four stage-solving strategies the model implements were all unreachable. `IndSequentialSolving` was also declared
  binary while its own code branches on four values. The defaults are the values that used to be in force.
- [FIXED] the AC design notes did not record the effect of the price on the branch current on the locational prices. It enters the objective and
  therefore the duals of the nodal balance, and the distortion moves prices relative to one another instead of shifting the level. Section 17 measures
  it: at the value formerly fixed in the code the largest movement in a nodal price was 140 EUR/MWh against a spread of 200, and at the value the RTS
  carry, by 1.53.
- [ADDED] `EpsilonCurrent` in `oT_Data_Parameter` sets the price on the AC branch current per case. It was fixed in the code, and the value required
  depends on the case: 1e-3 for `9n_AC` and 1e-6 for the RTS-GMLC cases and for pglib case118, a thousandfold spread. At 1e-3 the RTS cases carried a
  16 % dispatch distortion and reported a relaxed cost above the exact optimum. The distributed cases now carry calibrated values; a case that states
  nothing keeps the previous default.
- [CHANGED] the AC current penalty is priced into the objective and is no longer part of the reported system cost. It is a numerical device preventing
  the relaxation from purchasing voltage with current that is not present, not money, and on a 168-hour RTS-GMLC window it reached 14.43 MEUR of a
  60.00 MEUR reported total, a quarter of the figure. The solution is unchanged; `vTotalSCost` reports 45.56 MEUR for that case and the penalty is
  reported beside it.
- [FIXED] the AC design notes measured the RTS-GMLC network against DC on a system with no reactive compensation. The comparison, the horizon table and the
  relaxation tightness are measured again with the reactors: the DC model is unchanged to the digit, as it should be, and the AC one grows by exactly 3 rows per
  hour.
- [FIXED] the AC design notes reported that the exact model could not be solved on RTS-GMLC from a cold start. It can; the earlier attempt was made on
  a system without reactive compensation. Sections 13 and 14 are re-measured with the reactors in place and record the case definition, and a new
  section shows that the current penalty made the second-order cone appear tight.
- [CHANGED] the checks on incompatible options are made in one pass and reported together, instead of one at a time.
- [ADDED] `IndPTDF` is an explicit three-valued option: 0 inactive, 1 reads the factors from `oT_Data_VariablePTDF`, and 2 computes them from the
  reactances, so a case need no longer produce them in another tool and paste in a table openTEPES cannot check against its own network. The option
  was formerly implied by the presence of the table, which remains the default. Mode 2 is refused when the case carries candidate or switchable AC
  circuits, the factors belonging to one topology. On `9n` the computed factors reproduce the angle formulation flows exactly.
- [ADDED] an AC power flow residual check, written to `oT_Result_ACPowerFlowResidual` and reported on the console. It recomputes each branch flow from
  the busbar voltages and compares it with the flow the model reports, so a user can determine whether a solved case is physical, which formerly
  required pandapower. The relaxation gap answers a different question, saying whether the cone is tight and not whether the operating point is
  physical. On `9n_AC` the relaxed solution is about 68 MW from the series relation and the restored one within 0.00001 MW.
- [ADDED] the network matrices in `openTEPES_DataConfiguration.py`, which turn the branch data into the objects that need a view of the whole network: the
  susceptance matrices, the DC power transfer distribution factors, and the residual check above. DC links are excluded from all of them.
- [ADDED] the resolved configuration is printed at the start of every run: the network model in force, the AC settings, the reactive demand and shunt counts
  that reached the model, and the other active features. A case whose indicators do not say what the author intended now shows it before the solve, not after.
- [FIXED] the angle-difference band was built for the W-space formulation only, so `IndACPowerFlow = 3` ran with no band at all.
- [FIXED] the RTS-GMLC AC cases carried no shunt table, so the three 100 Mvar reactors on buses 106, 206 and 306 were missing and both ran with no reactive
  compensation. `RTS-GMLC_AC_Oper` falls from 61.65 to 60.00 MEUR; `RTS-GMLC_AC` is a full year and was not re-solved.

- [FIXED] error when fixing the line exchanges by assigning the same values with opposite signs in the variable TTC files
- [FIXED] plot of network maps
- [CHANGED] improve performance in some modules
- [CHANGED] modify OutputResultsGeneration to improve performance
- [FIXED] protect input data modules against a missing `openTEPES/cases/` folder, which was causing a `FileNotFoundError` on a fresh clone.
- [FIXED] fix small errors and typos in input data modules
- [FIXED] hydrogen-fired generators and hydrogen storage were absent from the hydrogen balance, so a turbine burned no fuel and a store was unconnected to
  supply and demand
- [FIXED] a hydrogen turbine was not charged for its fuel, its consumption being taken from the electricity side alone
- [ADDED] hydrogen supply without electricity, by reforming or import, through `MaximumProductionH2`, `ProductionCostH2` and `ProductionEmissionH2`
- [ADDED] hydrogen storage, through `MaximumStorageH2`, `MaximumChargeH2`, `InitialStorageH2` and `StorageTypeH2`, with an inventory returning to its initial
  level
- [CHANGED] a hydrogen-fired generator or a hydrogen boiler now brings the hydrogen carrier into the formulation, since either is charged for fuel in the
  hydrogen balance alone
- [ADDED] `H2ExcCost` in the parameter file, to price hydrogen in excess apart from hydrogen not served
- [ADDED] the solver version to the run status
- [CHANGED] document the hydrogen subsystem, with a diagram of the three carrier balances

## [4.18.17] - 2026-08-05

- [FIXED] many small errors detected with Claude Fable
- [FIXED]  fix typo for skipping the eReserveUpIfEnergy constraint condition and substitute list(mTEPES.n2) by n2list for performance improvement
- [CHANGED] the `9n_H2` case represents its two electrolyzers as the documentation defines the Electrolyzer (ELZ) unit type: a storage unit with
  electric energy outflows, a buffer of 1.512 GWh each, and a weekly outflow cycle. The hydrogen demand is expressed as the electricity the
  electrolyzers must draw to produce it, 0.3 tH2/h at 60 kWh/kgH2 giving 18 MW across the two units, so the hydrogen network is inactive here and
  `sSEP` retains that coverage. Formerly the electrolyzers had no storage and no outflows, so their inventory was pinned at zero and every unit of
  electricity consumed was written off as spillage, which carries no cost. Over a year the case costs 168.342 MEUR instead of 170.532, the
  electrolyzers being free to choose when to draw. Four automated checks added, and the 7-day expected cost moves to 242.89492215294186.
- [FIXED] skip the ESS downward-reserve energy constraint for units with no storage, and keep `pDemandElec` live in the electric balance, unbreaking master CI.
- [FIXED] fix some minor errors in model formulation
- [ADDED] `--warm-resolve` executes a Mode C study through one persistent Gurobi instance instead of re-exporting the model per overlay: the model is
  set up once and each overlay pushes only the constraints reading a swapped Param. Barrier by default, so costs match the non-persistent path, with a
  new parity check on 9n; the saving is the avoided re-export and grows with the length of the study. `--warm-resolve-simplex` adds warm dual simplex,
  time-capped with a barrier fallback, for small right-hand-side and bound studies only, being erratic on large or objective-side changes. Gurobi
  only, inactive by default.
- [FIXED] allow negative values of H2 demand to consider imports
- [FIXED] fix typo in technology consumption output
- [CHANGED] remove the investment decisions per year, just keeping the cumulative investment variables.
- [ADDED] a CI job that runs the tests with pandas pinned to the 2.x floor, since the lock pins pandas 3 and nothing else exercised the older end of
  `pandas>=2.2.2,<4` (issue #150).
- [CHANGED] pin `highspy==1.15.1` in the CI and Colab workflows, so a result is reproducible from the lock and a HiGHS release cannot fail an unrelated PR
  (issue #151).

- [FIXED] a Mode C study re-optimises the investment plan, closing issue #148. The solve fixes the plan to read the duals, and resolve released that,
  so a demand rise was met with unserved energy instead of new capacity and the cost was too high. resolve now calls unfix_for_duals first, with a
  check that the circuit investment moves under a demand overlay.
- [ADDED] resolve rejects an overlay the built model does not read live instead of swapping it silently. A misspelt name raises, as does a mutable
  Param the built model does not reference, whether captured as a constant or read only by a constraint skipped for the case. On 9n the adequacy and
  RES-energy constraints are skipped, no generation candidates being present, so an overlay of `pEFOR`, `pReserveMargin` or `pRESEnergy` raises.
- [FIXED] the output parity check now compares text labels correctly on pandas 3. pandas 2 turned a blank label into the text "None", but pandas 3 keeps it
  missing, and a missing value never equals itself, so two identical runs were reported as different.
- [CHANGED] allow pandas 3 and refresh the pinned dependencies. openTEPES now accepts `pandas>=2.2.2,<4`, and `requirements.lock` moves to pandas 3.0.3.
  streamlit moves to 1.59.2 in the same step, because streamlit 1.55 and older require pandas 2 and would otherwise block the upgrade.
- [FIXED] a blank cell in a text column now reads as NaN whichever backend the case comes from. The CSV reader gives NaN but DuckDB gives None, and limiting the
  NaN fill to numeric columns exposed the difference, which failed the CSV<->DuckDB round-trip tests.
- [FIXED] the input parity probe now compares text columns that contain blanks. It used `numpy.array_equal`, which reports an array holding NaN as different
  from itself.
- [ADDED] add some control for avoiding formulating eInstallGenCap
- [FIXED] validate CHP power ranges before building the power-to-heat ratio, raising a clear error instead of a division by zero, and warn on heat demand at a
  node with no heat generator or pipe
- [CHANGED] update InputData docs: the CSV<->DuckDB converter tools now exist (drop the "planned" note), with the bundled `9n` DuckDB example.
- [FIXED] fix syntactic errors in time Benders decomposition modules
- [FIXED] fix syntactic errors in openTEPES_ModelFormulationElectricity
- [CHANGED] change OutputResultsNetwork and OutputResultsEconomic for reducing execution time
- [FIXED] fix vNetworkInvPer at the same time that vNetworkInvest to avoid having vNetworkInvPer as binary variables when there are relaxed investments
- [ADDED] two figures on the multiple-runs page: a concept diagram of the three modes as a reuse matrix over the pipeline, and a Mode B flow diagram drawn
  against the shipped `openTEPES_Runner` / `openTEPES_Cases` API. Static images in `doc/img/`; no code change.
- [CHANGED] the sweep page is retitled "Multiple runs" and each mode gains its mechanics: backends and the status-JSON round trip for Modes A and B,
  the mutable-Param `store_values` hot swap and the non-persistent-solver requirement for Mode C. The Mode C note is corrected: the distributed
  `resolve` loop is serial and cross-platform, the fork copy-on-write belonging to the multiprocessing backend of Mode B.
- [ADDED] a "Solver interface: persistent vs non-persistent" section in SolutionMethods: the solver names taking the persistent Gurobi path (`appsi_gurobi` /
  `gurobi_persistent`) versus the non-persistent default, where reuse pays off (the stage loop and the Benders / dual re-solves), why Mode C must stay
  non-persistent, and examples.
- [ADDED] DuckDB data-management examples: querying a per-case `oT_Results_<case>.duckdb` and the swept `oT_Sweep.duckdb` in OutputResults, and inspecting a
  `.duckdb` input case in InputData (noting that openTEPES reads but does not yet create input DuckDB files).
- [ADDED] CSV<->DuckDB input converter tools (`scripts/openTEPES_DuckDB/`): `Tool_CSV_to_DuckDB` writes a CSV case to a `.duckdb`, `Tool_DuckDB_to_CSV` exports
  it back. Both are driven by `openTEPES_InputSchema` and reuse the DuckDB reader, so they cannot drift.
- [CHANGED] documentation: new Read the Docs page for parameter sweeps (Modes A/B/C via `openTEPES_Runner` + `openTEPES_Cases` and `resolve`). Document the
  `output_format` DuckDB result output and the `aggregate` sweep merger in OutputResults, the `.duckdb` input option and the integer form of the Yes/No indicators in
  InputData, and Benders decomposition in Characteristics. No model or behavior change.
- [ADDED] a CI `docs` job builds the Read the Docs site with warnings treated as errors, so a broken cross-reference or a missing toctree entry fails the PR;
  `conf.py` silences only the project's front-matter convention warning.
- [FIXED] continuous integration on the sector and stage Benders commit. `openTEPES_ProblemSolvingStageSolve.py` called the cycle-flow builders
  through an undefined `oTM` alias with undefined indicators, and now calls `NetworkCycles` and `CycleConstraints` directly, as the stage iterator
  does. `openTEPES_ProblemSolvingSectorDecomposition.py` and `openTEPES_ProblemSolvingStageDecomposition.py` use the same relative-import guard as the
  other split modules.
- [ADDED] added sector and stage Benders decomposition
- [CHANGED] if a thermal unit has a variable minimum generation > 0 in a load level it is considered committed in this load level
- [CHANGED] fix the energy activation variables if no operating reserve activation constraint is formulated in a time step
- [ADDED] Mode B in-memory overlay study (RFC §4.2): `openTEPES_Runner.run(mode="in-memory")` reads the baseline case once into a new
  `openTEPES_InMemorySource` and reuses it per case through an overlay, a data-table stem mapped to a scale factor, a callable or a replacement frame,
  so a parameter study pays the input reading once and rebuilds and solves per case. `openTEPES_run` gains `input_source=`; `InputSource` gains
  `list_dict_stems()`, implemented in `CSVSource` and `DuckDBSource`. Additive only: an identity overlay reproduces a direct solve on 9n.
- [FIXED] the twelve technology- and consumption-level operating-reserve result writers in `openTEPES_OutputResultsGeneration.py` used plain `to_csv`, so they
  bypassed the result sink and were missing from the DuckDB output. They now use `.oT.write` like every other writer, so the DuckDB file has one table per
  result CSV again (fixes `test_output_format_both_csv_parity`).
- [CHANGED] change names of the operating reserve file results
- [ADDED] DuckDB result output and a study merger (`openTEPES_OutputResultsSink.py` and `openTEPES_ResultAggregate.py`), the output-side counterpart
  of the DuckDB input source. `openTEPES_run` gains `output_format` (`"csv"` default, `"duckdb"`, `"both"`); with DuckDB active each case also writes
  one `oT_Results_<case>.duckdb`, one table per result, straight from the in-memory frame. A pandas `oT` accessor routes every writer through the
  sink, so a `"csv"` solve is byte-identical, verified on 9n, 9n_heat and 9n_H2. `aggregate(sources, out_path, to=...)` stacks the cases of a study
  into one long table per result with a leading `case` column.
- [FIXED] formulation of eOperReserveUpEnergy and eOperReserveDwEnergy constraints
- [FIXED] failure in plotting up and down operating reserve marginals when the constraint has not been formulated
- [ADDED] Mode A pre-build study runner (`openTEPES_Runner.py` and `openTEPES_Cases.py`): `run(cases, solver_name, backend=...)` solves many cases
  through `openTEPES_run`, one independent build and solve per case, over a `serial` (default), `multiprocessing` or `joblib` backend. A `Case` names
  one input source, a CSV directory or a `.duckdb` file, plus an optional output directory and label. The runner reads each
  `openTEPES_run_status_*.json` and returns one summary per case in input order, so nothing pickles the Pyomo model across workers; a case that raises
  is captured as `status="error"` instead of aborting the study. Additive only.
- [ADDED] add CSV output file TechnologyInvestment per area
- [CHANGED] change eOperReserveUpEnergy and eOperReserveDwEnergy to system-wide constraints, instead of area constraints
- [CHANGED] fix some errors in writing H2 and heat network output results
- [FIXED] `setup_solver` no longer crashes on Windows when an earlier in-process solve still holds the stale log file open.
- [FIXED] deprecated `datetime.utcnow()` replaced with timezone-aware UTC; emitted timestamp unchanged.
- [ADDED] Mode C post-build hot-swap re-solve (`openTEPES_ProblemSolvingResolve.py`): `resolve(OptModel, SolverName, overlays)` re-solves a built
  model once per parameter overlay without rebuilding, so a study reuses the single slow build, and `overlay_scaled` makes a scale-factor overlay.
  Overlays apply relative to the baseline, restored at the end. Only mutable Params hot-swap, so the operational set `pDemandElec`, `pENSCost`,
  `pLinearVarCost`, `pEFOR`, `pReserveMargin` and `pRESEnergy` is promoted to mutable; structural and topology Params stay immutable. No behaviour
  change: 9n solves bit-identical at 164.382043867 MEUR.
- [CHANGED] the 2900-line `openTEPES_InputData.py` is split into three modules at the package root, one per model-build step, the last of the three
  large-file splits. `openTEPES_InputData.py` keeps `InputData`, which reads the raw sets and parameters from the case source; the new
  `openTEPES_DataConfiguration.py` holds `DataConfiguration`, which builds the derived and instrumental sets and the option-driven branches; the new
  `openTEPES_SettingUpVariables.py` holds `SettingUpVariables`, which creates the decision variables and their bounds. `__init__.py` re-exports all
  three. A pure move, the three functions byte-identical and none calling another, so the whole solve suite passes at the same locked costs.
  Separating set construction from parameter construction inside `InputData` is function surgery and is left for its own change.
- [CHANGED] every distributed case is documented on the Download and Installation page (`doc/md/Download.md`). The list covers all ten cases under
  `openTEPES/cases/` instead of seven, adding `9n_PTDF` (the 9-busbar case solved with the PTDF network formulation instead of the angle-based DC
  power flow), `9n_heat` (coupled with a heat network) and `9n_H2` (coupled with a hydrogen network), and the `sSEP` entry notes its hydrogen network.
  Each entry states in one line what distinguishes the case.
- [CHANGED] the 1770-line `openTEPES_ModelFormulation.py` is split into six per-concern modules at the package root. The two cross-sector concerns are
  `openTEPES_ModelFormulationObjective.py` (the total-cost objective and the per-stage operation-cost accumulation) and
  `openTEPES_ModelFormulationInvestment.py` (the four investment builders plus the installed-capacity, adequacy-reserve-margin and emission limits).
  Each energy carrier then has its own module: `…Electricity.py` (demand balance, operating reserves and inertia, storage, unit commitment, ramping,
  line switching, DC network operation and the cycle constraints), `…Hydro.py`, `…Hydrogen.py` and `…Heat.py`. `__init__.py` re-exports all six. A
  pure move, the 19 builder functions byte-identical, so the whole solve suite passes at the same locked costs. Keeping each carrier in one file is
  the groundwork for selectable formulations chosen by which functions the stage driver calls.
- [CHANGED] update the architecture diagram (`doc/img/openTEPES_architecture.svg` and the rendered `.png`) to show the new
  `openTEPES_ProblemSolvingStageIter.py` as an implemented (green) box in the solver layer, alongside `ProblemSolving`, `Tuning`, `DualExtraction`, `Persistent`
  and `Benders`; `resolve.py` stays white as the one solver module still planned. The seven boxes are re-spaced to fit the layer's existing width — no other
  layer changes.
- [ADDED] an automated check (`tests/test_direct_run.py`) executing every `openTEPES_*.py` module as a script, through `runpy`, to confirm each still
  imports cleanly that way, which exercises the fallback of the relative-import guard. A normal `import openTEPES` only ever takes the relative path,
  so nothing checked the fallback, and a broken guard, a missing import or a circular import would surface only when a user executes the file
  directly. The check solves no model and excludes `openTEPES_Main.py`, which carries a real `__main__` block.
- [CHANGED] the per-stage solve loop moves out of `openTEPES_run` into a new module `openTEPES_ProblemSolvingStageIter.py`. The (period, scenario,
  stage) loop, which activates the load levels of one stage, builds that stage's operation constraints and calls `ProblemSolving`, now lives in
  `StageIterativeSolving`, together with the post-loop work restoring the sets, the constraints and the scenario probabilities. The two solve paths
  are unchanged. A pure move: the whole solve suite passes at the same locked costs, and case 9n gives 252.20132998 MEUR, matching to 13 significant
  figures, only the per-unit dispatch tables moving by the amount HiGHS already varies when it chooses among equally optimal storage schedules.
- [CHANGED] the 2800-line `openTEPES_OutputResults.py` is split into per-concern modules at the package root: `…Investment.py`, `…Generation.py`,
  `…Storage.py`, `…Hydrogen.py`, `…Heat.py`, `…Network.py`, `…Economic.py`, `…Summary.py` and `…RawDump.py`, with the shared pieces in `…Common.py`
  and `…MapCommon.py`. The dispatch order is still controlled by `OUTPUT_REGISTRY` in `openTEPES.py` and is unchanged. Verified bit-identical on case
  9n across all 87 result tables at 164.382043867 MEUR. Two cleanups made while moving: 34 no-op `"".join([f"..."])` wrappers removed, and
  `ESSOperationResults` no longer writes its inventory-utilization scaling back into `mTEPES.pMaxStorage`.
- [ADDED] a `9n_H2` example case, the hydrogen counterpart of `9n_heat`: the minimal 9-busbar electricity system plus two electrolyzers, hydrogen
  demand at three busbars and a hydrogen pipeline network. Added to the single-stage solve suite at an expected cost of 259.547 MEUR under the 7-day
  HiGHS fixture, verified deterministic across repeated solves, so the hydrogen result writer is exercised on a small case instead of only through
  `sSEP`. Output verified bit-identical for both CSV and DuckDB inputs.
- [FIXED] two operating-reserve guards in the marginal and economic results read a leaked loop variable. The down-reserve-marginal and
  up-reserve-revenue guards loop over storage units but checked `pIndOperReserveGen[nr]` and `pIndOperReserveCon[nr]`, `nr` surviving from the earlier
  loop that builds the area-to-unit map; they now check the loop's own `es`, matching the two sibling guards that were already correct. The
  down-reserve-revenue guard also read `pIndOperReserveGen[nr]` twice where its siblings read `Con`. On case 9n the result is unchanged.
- [CHANGED] the architecture diagram (`doc/img/openTEPES_architecture.svg`) matches the code. The former picture used the planned folder names (`io/`,
  `schema.py`, `solver/`, `solve.py`) and now shows the real flat module names with the five real solver modules, implemented modules shaded green and
  planned ones white, with a small legend. A rendered `doc/img/openTEPES_architecture.png` is committed and `README.md` points at it, so the diagram
  displays where SVG does not, such as the PyPI page. A short `doc/img/README.md` explains that the SVG is the hand-drawn source and how to regenerate
  the PNG.
- [FIXED] a binary investment problem, for example `IndBinNetInvest=1`, failed under HiGHS with `NoDualsError` on the first solve. `ProblemSolving`
  attaches the `dual` Suffix before the first solve only for a pure linear model, a mixed-integer problem having no duals, and recovers them later by
  fixing the integer variables and re-solving. The test deciding whether the model is linear also required each variable to hold a value, which none
  does before the first solve, so a model with binary investment variables was treated as linear, received the Suffix and failed. The test now
  considers only whether a variable is integer and unfixed. Unit commitment models were unaffected, their binaries holding starting values.
- [ADDED] an automated check (`test_binary_investment` in `tests/test_run.py`) for a binary investment decision, which no other check covered, every
  other case solving the investment variables as a continuous relaxation. It activates `IndBinNetInvest` for `9n`, so the single candidate circuit
  becomes a build-or-not decision; the cost, 254.337 MEUR, differs from the continuous 252.201 MEUR because the binary decision forces a full circuit.
  A companion fixture `case_7d_binary` solves the case from a private temporary copy, so its solver log files do not clash on Windows, applies the
  7-day truncation and overrides columns of the Option file.
- [CHANGED] the continuous-integration workflow is split into two jobs. A `fast` job executes the linter and the checks that solve no model, on all
  three operating systems and Python 3.11, 3.12 and 3.13, where import, packaging and version problems appear. A `solve` job executes the full model
  suite once per operating system on Python 3.12, the results being the same on every version. Checks that solve a model carry `@pytest.mark.solve`,
  registered in `pyproject.toml`. A per-check timeout and dependency caching for `uv` are added. No check is removed.
- [ADDED] a tool confirming that two solves produce the same result files: `openTEPES/_output_parity_test.py`, with checks in
  `tests/test_output_parity.py`, the output-side counterpart of `_input_parity_test.py`. A snapshot is taken of every `oT_Result_*.csv` written
  and two snapshots are compared, numbers within a small tolerance and text labels exactly. Its purpose is safe refactoring of the output code: a
  change reorganising it should still write identical result files, and this tool proves it.
- [CHANGED] allow finding the case in the same folder or in the cases folder
- [FIXED] `openTEPES_Main.py` can be executed directly. As a script the file is `__main__` with an empty `__package__`, so the top-level relative
  import fails with `attempted relative import with no known parent package`. The import is wrapped in a `try`/`except ImportError` that puts the
  repository root on `sys.path` and retries as an absolute package import; the relative import remains the primary path, so installed behaviour is
  byte-for-byte identical and the fallback triggers only on direct execution. The same guard is applied to `openTEPES.py`, `openTEPES_InputData.py`,
  `openTEPES_InputSource.py`, `openTEPES_InputCSVSource.py`, `openTEPES_InputDuckDBSource.py` and `openTEPES_ProblemSolving.py`.
- [CHANGED] untrack accidentally committed per-run status sentinels (`openTEPES/cases/{9n,9n_heat,sSEP}/openTEPES_[Rr]un_[Ss]tatus_*.json`, test-case workspace
  pollution; removed from the index, kept on disk) and extend `.gitignore` with the `openTEPES_[Rr]un_[Ss]tatus_*.json` pattern — the existing
  `oT_Run_Status_*.json` rule matched neither the `openTEPES_` prefix nor the lower-case `run_status` variant.
- [ADDED] an architecture diagram in `README.md` (`doc/img/openTEPES_architecture.svg`), a visual summary of the six-layer package structure that PR
  #120, this pull request and the planned follow-on work build toward. Inserted before the "How to Cite" section under a new "Architecture" heading.
  The source diagram lives in the architecture RFC in the parent repository; the README embeds the rendered SVG only.
- [CHANGED] **BREAKING**: every distributed case study moves from `openTEPES/<case>/` to `openTEPES/cases/<case>/`. The nine cases `9n`, `9n7y`,
  `9n_PTDF`, `9n_heat`, `NG2030`, `RTS-GMLC`, `RTS-GMLC_6y`, `RTS24` and `sSEP` live under the new `cases/` folder, the set distributed on PyPI. The
  repository-root `cases/` folder, holding the larger study cases, is renamed `case_studies/` so the two no longer collide. **External users must
  update `openTEPES_run(DirName="<path>/openTEPES", CaseName="9n")` or `--dir <pkg>` to `<path>/openTEPES/cases`.** No compatibility shim.
- [CHANGED] the input-source layer of `openTEPES_InputSource.py` is split into four modules at the package root, pure pandas with no Pyomo dependency:
  `openTEPES_InputSchema.py` (the TABLE_SPECS catalog, the transform-kind constants and DEFAULT_IDX_COLS, used by every backend),
  `openTEPES_InputSource.py` (the `InputSource` interface, the `open_source()` factory and the post-read shape helpers), `openTEPES_InputCSVSource.py`
  and `openTEPES_InputDuckDBSource.py`, `duckdb` being imported lazily so CSV-only environments do not need it. The public names remain re-exported
  from the package top level. No behaviour change.
- [CHANGED] the solve suite in `tests/test_run.py` is extended. The single-stage 7-day fixture covers six cases instead of three, adding `9n_heat`
  (247.196 MEUR), `NG2030` (1041.342 MEUR) and `RTS-GMLC` (1091.094 MEUR). A new multi-stage fixture keeps the first 168 hours of each (Period,
  Scenario, Stage) group, leaving `StageWeight` as authored, and covers `9n7y` (9019.299 MEUR), giving the multi-stage rolling layout its first
  coverage. A third check validates classical L-shaped Benders on `9n` against the joint linear problem, relative error 5.78e-08. Costs are locked at
  7 significant figures and reproducibility verified to 13. `RTS24` is excluded, three identical solves having returned 1107.185, 1107.400 and
  1110.174. `RTS-GMLC_6y` is not yet parametrised, its multi-stage solve exceeding 10 minutes locally. Wall-clock over the whole matrix: single-stage block about 40 s, multi-stage 90 s, Benders 6 s.
- [CHANGED] `openTEPES_ProblemSolving.py` is split into four modules at the package root per RFC §3 Layer 5.a: `…Persistent.py` (the `appsi_gurobi`
  and `gurobi_persistent` lifecycle with the `ncall` state machine), `…Tuning.py` (per-solver option presets for Gurobi, CPLEX, HiGHS and GAMS),
  `…DualExtraction.py` (fix the integers and the continuous investments, re-solve as a linear problem, copy the duals into `mTEPES.pDuals`), and a
  slim `openTEPES_ProblemSolving.py` orchestrator composing the three. The public imports continue to work. No behaviour change; all 10 checks pass
  bit-identical to the state before the split.
- [ADDED] the solver layer of the RFC restructure, with `openTEPES_ProblemSolvingBenders.py`, a classical L-shaped decomposition driver for
  transmission expansion. The master holds the `vNetworkInvest` decisions for every candidate circuit; the subproblem is the full model with each
  decision pinned through an explicit equality against a mutable Param, whose dual gives the cut coefficient. On the distributed `9n` under the 7-day
  fixture the joint linear problem returns 252.201330 MEUR and the L-shaped method converges in 8 iterations to 252.201345 MEUR, relative error
  5.78e-08, in about 5 s under HiGHS. It also acts as a compatibility guard: every future refactor must keep `vNetworkInvest` separable as a master
  decision and the remainder usable as a linear subproblem with valid duals. Scope is deliberately minimal, one deterministic case, no multi-cut, no
  trust region, no binary investments. Implementation note: `Var.fix()` with the `rc` Suffix is not portable, HiGHS leaving `rc` empty.
- [ADDED] the `InputSource` abstraction (`openTEPES_InputSource.py`), so `openTEPES_run` accepts either a CSV case directory, the historical default
  with byte-identical behaviour, or a `.duckdb` file produced by an external ingest script. DuckDB reads stream through SQL straight into DataFrames,
  with no temporary files. The path selects the backend, and DuckDB is an optional, lazily imported dependency. A `TABLE_SPECS` catalog of 67 entries
  declares each input table once with its CSV stem, table name, transform kind and key columns. Verified bit-identical end to end, relative error
  below 1e-15, on 9n, sSEP and 9n_PTDF.
- [CHANGED] `pyomo.environ.DataPortal` is dropped from `InputData`. The 22 `dictSets.load(format='set')` sites collapse to
  `Set(initialize=df_to_set_values(source.read_dict(stem)))`, leaving pandas the only CSV parser in the path. `set_definitions` gains an explicit
  `ordered` entry, `SPECIAL_IDX_COLS` gives way to declarative `pk_cols` in `TABLE_SPECS`, and the conditional loaders become a declarative loop,
  absent tables still skipped silently and malformed ones now raising. `DataConfiguration` becomes `DataConfiguration(mTEPES, dfs=None, par=None)`
  with a fallback for compatibility, and 639 reach-into-model sites are swept to local `par[...]` and `dfs[...]`. CSV behaviour is invariant.
- [FIXED] the heat investment constraint `eTotalFHeatCost` referenced an undefined `vTotalHeatFCost`; the variable is `vTotalFHeatCost`. Dormant, no
  case in the tree carrying a candidate heat pipe, so `mTEPES.hc` is always empty and the `InvestmentHeatModelFormulation` call is gated. A
  self-contained regression check in `tests/test_heat_investment_typo.py` builds the minimum Pyomo state to exercise the formulation, with no case
  directory and no solver call.
- [ADDED] the `9n_heat` test case, the first in the tree exercising the heat carrier (`pIndHeat=1`). Three heat units, an air-source heat pump at COP
  3.0, a gas boiler at 92 % efficiency and a backpressure gas CHP at a power-to-heat ratio near 0.71, with two heat pipes across Node_2, Node_3 and
  Node_4 overlaid on the existing `9n` topology. Parameter values follow ECEMF, NECP and ERAA reference scenarios and are not a calibration. Under the
  7-day fixture HiGHS terminates optimal in 0.4 s at 247.19623713906074 MEUR, heat reliability cost zero, 10 503 constraints and 14 504 variables.
- [ADDED] opt-in `--gzip-large-csvs` / `--gzip-patterns` command-line options. After writing, every `oT_Result_*.csv` whose name (after the leading `oT_Result_`) starts
  with one of the configured prefixes is rewritten as `.csv.gz`. Default prefix set: `Generation, Consumption, Balance, MarketResults, Network`. Pandas reads
  `.csv.gz` transparently; Excel does not. Sentinel JSON gains `gzip_patterns`, `gzip_files`, `gzip_mb_saved`. Default behavior unchanged.
- [CHANGED] reorder output writers in `openTEPES_run` so small KPI/structural tables (`InvestmentResults`, `CostSummaryResults`, `OperationSummaryResults`,
  `ReliabilityResults`, `FlexibilityResults`) are written before bulky hourly tables (Generation, ESS, Network, Marginal, Economic). HTML map plots run last.
  Resilient to mid-output interruptions: headline numbers from every solved case survive a kill/timeout/disk-full. No behavioral change beyond write order.
- [CHANGED] the 14 dispatch blocks fixed in the code in `openTEPES_run` give way to a single `OUTPUT_REGISTRY` tuple at module top, each entry
  `(category_key, writer_fn, extra_args_keys, guard_fn)`, with a five-line dispatch loop. Registry order is dispatch order, preserving the previous
  headline, bulky and plot sequence. A pure refactor, with no behavioural, signature or argument change.
- [CHANGED] introduction of new optional files for the operating reserve activation as an alternative to the UpReserveActivation and DwReserveActivation
  parameters in Data_Parameter file
- [CHANGED] modify the change of the scenario probabilities to 1.0 if there are no investment decisions
- [FIXED] control of non-existing electrolyzer output in OutputResults module
- [FIXED] control of generator investments and retirements, and line investments in openTEPES.py
- [FIXED] write voltage angle only if existing in the optimization problem.
- [FIXED] fix Big-M coefficient for AC candidate disjunctive Kirchhoff voltage law (eKirchhoff2ndLaw1/2). DC and existing AC lines are unaffected.
- [ADDED] post-solve warning when the voltage-angle bound pMaxTheta = pi/2 is (nearly) binding.
- [CHANGED] changed the simplex strategy for highs and from appsi_highs to highs
- [CHANGED] changed the penalty for hydrogen surplus to 0.5 the cost of hydrogen not served
- [FIXED] fix case with multiple independent scenarios
- [CHANGED] updated usage of appsi_gurobi and gurobi_persistent solvers
- [CHANGED] detection of generators with minimum and maximum energy constraints

## [4.18.16] - 2026-04-10

- [CHANGED] add H2 network utilization in output results
- [FIXED] fix H2 and heat network map titles
- [CHANGED] clean up ProblemSolving module
- [FIXED] fix model formulation for some lines not available until certain year
- [CHANGED] introduced appsi_gurobi as solver
- [CHANGED] changed HiGHS options
- [CHANGED] detection of lines with same initial and final nodes
- [FIXED] fix computation of SRMC for hydrogen balance equation
- [CHANGED] added excess of hydrogen production penalized as hydrogen not served in the objective function

## [4.18.15] - 2026-02-23

- [CHANGED] cleanup model formulation, input data, and output results to improve readability and avoid unnecessary computations
- [CHANGED] separate H2 and heat constraints in functions to improve readability
- [FIXED] fix error in eKirchhoff2ndLaw1 and eKirchhoff2ndLaw2 to avoid formulating for nonexistent lines in a certain year
- [FIXED] fix eReserveUpIfEnergy and eReserveDwIfEnergy constraints
- [CHANGED] cleanup model formulation and input data to improve readability

## [4.18.14] - 2026-02-06

- [CHANGED] cleanup model formulation to avoid unnecessary computations and to improve readability
- [FIXED] error in output results for case RTS24
- [CHANGED] modify the generation inventory utilization for the candidate ESS to be wrt the invested storage capacity instead of the maximum storage capacity

## [4.18.13] - 2026-02-05

- [CHANGED] extensive use of a2g and t2g in input, model formulation, and output modules to avoid unnecessary computations and to improve readability
- [FIXED] errors in eMaxOutput2ndBlock and eMinOutput2ndBlock constraints when considering generators not available in some periods
- [CHANGED] detect lines with undefined nodes or circuits
- [CHANGED] detect technologies not declared in the technology dictionary
- [CHANGED] reduce interior point method tolerance for gurobi solver

## [4.18.12] - 2026-01-28

- [CHANGED] reduce computation time in output results

## [4.18.10] - 2026-01-25

- [CHANGED] avoid formulation of superfluous eTotalOutput constraints and fix additional vTotalOutput variable
- [FIXED] errors in writing results to duckdb database
- [CHANGED] clean up eMaxOutput2ndBlock and eMinOutput2ndBlock equations
- [FIXED] errors in eMaxOutput2ndBlock and eMinOutput2ndBlock equations
- [CHANGED] clean up some output results

## [4.18.9] - 2026-01-22

- [CHANGED] increase solution time limit for some solvers
- [FIXED] errors in OutputResults module for considering generators not available in some periods
- [CHANGED] add output results to DuckDB database

## [4.18.8] - 2026-01-19

- [CHANGED] detect error of ESS unit with maximum charge and no maximum storage
- [CHANGED] create output files for ramp revenues
- [CHANGED] modify eMaxOutput2ndBlock and eMinOutput2ndBlock to consider the ramp reserve provision
- [CHANGED] create eSystemRampUp and eSystemRampDw constraints to satisfy the system ramping capability
- [CHANGED] add the optional RampReserveUp and RampReserveDown input files to introduce ramping reserves per area
- [FIXED] add domain change for fixed binary variables to avoid failures in getting the duals
- [FIXED] fix the HiGHS behavior for getting dual variables
- [CHANGED] add the GenerationCapturedSRMC and ConsumptionCapturedSRMC output files
- [FIXED] control of load levels with 0 duration in psn and fix in OutputResults module
- [CHANGED] fix pandas warning in InputData module
- [CHANGED] added MarketResultsGenerationInvestment file
- [CHANGED] added LCOE and generation in the MarketResultsTechnologyInvestment file
- [CHANGED] added MarketResultsTechnologyInvestment file
- [CHANGED] added curtailment and emissions to MarketResultsGeneration file
- [CHANGED] reduce computation time in output results
- [CHANGED] generation time reduction in model formulation moving parameters out of the sums
- [FIXED] control of candidate generators not available in some periods in some investment constraints in model formulation and output results
- [FIXED] fix computation of LCOE.
- [FIXED] upper bound of line losses only if no single node option. With single node option losses are 0.

## [4.18.7] - 2025-11-22

- [CHANGED] extension to quarter of an hour resolution for the load levels
- [FIXED] fix TechnologyEmission outfile
- [CHANGED] modify names of some output results and avoid writing empty files
- [FIXED] fix eTotalECostArea constraint
- [CHANGED] introduce conditions to avoid formulating superfluous eMaximumEnergy and eMinimumEnergy constraints
- [FIXED] fix error in MarginalEmission output results
- [FIXED] control of transmission lines not available for all the periods
- [CHANGED] remove condition for load levels with duration 0 in ReserveXXIf constraints
- [FIXED] candidate must run unit behavior (i.e., committed if installed)
- [CHANGED] penalize network losses in the objective function to avoid losses with spillage/curtailment
- [FIXED] fix the computation of MWkm in output results
- [CHANGED] detection of minimum renewable energy requirement exceeds the demand
- [CHANGED] detection of all the lines have NTC zero probably due to security factor equal to zero
- [CHANGED] avoid formulating superfluous eMaxOutput2ndBlock and eMinOutput2ndBlock constraints
- [CHANGED] fix minimum stable time variables for units that don't have minimum stable time
- [CHANGED] remove parameter pRatedConstantVarCost
- [CHANGED] avoid formulating superfluous eTotalEmissionArea and eMinOutput2ndBlock constraints
- [CHANGED] no plots for no output results

## [4.18.6] - 2025-09-21

- [FIXED] fix bugs in InputData module
- [CHANGED] InputDate module refactored to split in several functions
- [FIXED] fix bug in Output Results computation of ramp surplus
- [FIXED] fix bug in Output Results when an Area has no non-RES generators
- [CHANGED] save all the output results in the mTEPES model object
- [FIXED] fix typo in BalancePerXXX output files
- [CHANGED] if the variable TTCFrw and TTBck are both very small (e.g., 0.000001), they are set to 0 and the line is considered open
- [FIXED] fix typo in TechnologySpillage output file
- [FIXED] fix typo in BalanceEnergy and MarketResultsGeneration output files

## [4.18.5] - 2025-06-23

- [CHANGED] add MarketResultsDemand and MarketResultsGeneration output files.
- [FIXED] Fix typo in reserve equations
- [CHANGED] change ESS inventory efficiency consideration from full value at consumption to square root at both consumption and generation.
- [FIXED] fix operating reserve constraints for ESSs and hydropower plants regarding if there is enough energy/water
- [CHANGED] add the ability to choose if an ESS provides reserves as a generator or a consumer independently
- [CHANGED] avoid formulation of superfluous vHydroOutflows variables
- [FIXED] fix error when displaying network losses by transmission line
- [FIXED] fix bug when a set of mutually exclusive generators has no generators
- [FIXED] fix bug when variable TTC is used and there are lines with reactance equal to 0
- [CHANGED] introduce variable TTC forward and backward for the transmission lines
- [CHANGED] add hourly mutually exclusive generators, generators can now be part of several mutually exclusive groups, exclusivity now applies to consumption
  too
- [FIXED] change from titleside to title_side in output results to adapt to the latest plotly version
- [CHANGED] add logfile for GAMS solver
- [FIXED] fix error in the cost summary per area files
- [FIXED] fix some errors in the output results
- [FIXED] don't initialize some variables
- [FIXED] don't fixed or count variables that have no value
- [CHANGED] change len(xxx) to xxx

## [4.18.4] - 2025-04-08

- [CHANGED] introduction of commitment for hydro units modeled in water units
- [FIXED] allow solving periods with no investment decisions independently in a multiyear case
- [FIXED] fix GenerationCostOperatingReserve output file
- [FIXED] deactivate constraints when solving for each period and scenario
- [FIXED] avoid solving all the periods and scenarios simultaneously if not needed
- [CHANGED] added GenerationConsumptionRatio output file
- [FIXED] error in some terms of the operation costs
- [FIXED] error in CostRecovery output file

## [4.18.3] - 2025-03-18

- [FIXED] error in pumping signs of the HydroInventory constraint
- [CHANGED] introduce operation costs in CostRecovery output file
- [CHANGED] avoid the introduction of all the nodes in demand and operating reserve input files
- [FIXED] add revenues of ESS generation and consumption operating reserves
- [CHANGED] change sign of the consumption energy and operating reserve revenues
- [FIXED] typo when computing charge revenues in output results
- [CHANGED] detection of units with no energy inflows and no consumption power
- [FIXED] avoid formulation of superfluous ramp or inventory constraints for ESS with no energy inflows and no consumption power
- [FIXED] don't formulate operating reserve constraints for ESS with no energy inflows and no consumption power
- [FIXED] detection of the first time step for each period, scenario, and stage
- [FIXED] decision on the unit commitment at the initial hour done by area instead of by system
- [FIXED] contribution of the operating reserve activation of a consumption unit to eChargeDischarge and eESSTotalCharge constraints
- [CHANGED] avoid warning when updating mTEPES.na
- [FIXED] typo in output results
- [FIXED] control of duration 0 in load levels if there is no period weight or scenario probability
- [CHANGED] default values when there are no StorageType, OutflowsType, or EnergyType to 1 instead of 8736
- [FIXED] minimum up/down time constraints
- [FIXED] units of the operating reserve constraint marginals
- [CHANGED] epsilon in eRampUpState/eRampDwState constraints moved to numerator

## [4.18.2] - 2025-01-31

- [FIXED] fix condition when ignoring investment decisions
- [FIXED] typo in emission condition
- [CHANGED] fixed emission limit calculation
- [CHANGED] detect no weights in periods and stages and abort the run
- [CHANGED] define GAMS (capital letters) as a solver
- [FIXED] fix error in eRampDw constraint
- [CHANGED] add FlexibilityNetwork output file

## [4.18.1] - 2024-12-19

- [CHANGED] add area in MarginalIncrementalVariableCost, MarginalIncrementalGenerator and GenerationIncrementalEmission output files
- [FIXED] fix error in eAdequacyReserveMarginHeat
- [FIXED] some epsilon for heat were wrong
- [CHANGED] add reserve margin for heat demand (new CSV file, and modifications related to it in input data, model formulation and output results)
- [CHANGED] computing pDemandHeatPeak in InputData
- [CHANGED] refactoring the energy to heat conversion

## [4.18.0] - 2024-12-04

- [CHANGED] in this version no need to introduce all the generators as headings of the variable max/min data files
- [FIXED] all the cases have been updated to this new version
- [FIXED] to improve model robustness the first cells of the heading row of all the Data files are filled with correct headers. These changes are mandatory for
  this new version.
- [FIXED] first column of Parameter and Option files dropped
- [FIXED] minor changes in output results

## [4.17.9] - 2024-11-19

- [FIXED] fix error in network map
- [FIXED] fix error in computing cost recovery
- [FIXED] fix error in computing pDemandElecPeak in InputData
- [CHANGED] keep the model in memory
- [CHANGED] default values of minimum output results
- [CHANGED] concatenation of strings

## [4.17.8] - 2024-10-30

- [FIXED] fix control of second block capacity extremely small (1e-17)
- [FIXED] fix formulation of the minimum stable time constraints
- [CHANGED] name of the solver log file
- [FIXED] fix some typos in output results
- [FIXED] writing of the GenerationSurplusHeat file
- [FIXED] computation of pMaxPowerHeat
- [FIXED] computation of net demand per node in output results
- [CHANGED] if no ending year is given in the input data, the last year is considered year 3000
- [CHANGED] control of invalid electric lines, hydrogen lines, and heat pipelines
- [CHANGED] added colum of MEUR/year in cost summary files
- [CHANGED] added information regarding detected infeasibilities
- [FIXED] lower bound only for VRE units
- [FIXED] computation of curtailment in the output results for generation candidates

## [4.17.7] - 2024-09-20

- [CHANGED] redefinition of all sets, removing the order of the elements, and the lambda function to filter the elements

-[CHANGED] enabling assert of the objective function in the test run

## [4.17.5] - 2024-09-18

- [FIXED] avoid degeneracy when ordering generating units by increasing variable costs

## [4.17.4] - 2024-09-12

- [FIXED] avoid considering the hydro units as marginal incremental generators
- [CHANGED] split generation and consumption in ESS technologies
- [FIXED] fix error when solving by stages
- [FIXED] fix error in writing investment output results
- [CHANGED] introduce outflow incompatibility column in Data_Generation file

## [4.17.3] - 2024-07-19

- [CHANGED] introduce hourly outflows
- [FIXED] control of units not available in some years
- [FIXED] change when computing pStorageTotalEnergyInflows
- [FIXED] fixed writing reserve margin dual variables
- [FIXED] fixed creation of pyomo parameters stacking original data
- [FIXED] fixed disregarding load levels for timestep > 1 for many periods
- [CHANGED] restructured source code of InputData module
- [FIXED] fixed typo in stable state equation
- [FIXED] detection of electricity, heat and H2 lines/pipelines
- [CHANGED] introduced formulation of the minimum stable time constraints
- [CHANGED] add case RTS-GMLS expansion planning for 6 years with representative weeks
- [CHANGED] add case 9n expansion planning for 7 years with representative weeks
- [FIXED] control some divisions by zero due to pDuration
- [CHANGED] declare pDuration as NonNegativeIntegers

## [4.17.2] - 2024-05-30

- [FIXED] fix some heat output files
- [CHANGED] define chp as all the heat producers
- [FIXED] fix some investment output files
- [FIXED] fix some emission output files
- [CHANGED] considering emissions from heat generators

## [4.17.1] - 2024-05-21

- [CHANGED] add the NG2030 case study
- [CHANGED] time reduction in some output results
- [FIXED] fix errors in heat generator investments
- [FIXED] fix errors and add some heat results
- [CHANGED] add some heat generation output files
- [FIXED] fix error in heat boilers
- [CHANGED] introduction of cycle equations for DC power flow
- [CHANGED] fix error in writing the duals in output results

## [4.17.0] - 2024-05-10

- [CHANGED] add period and stage in Duration file to allow different durations for each stage in each period and scenario

## [4.16.1] - 2024-05-08

- [CHANGED] add some CPLEX options

## [4.16.0] - 2024-04-30

- [FIXED] delete eTotalNCost and vTotalNCost
- [CHANGED] delete investment and commitment reduced costs files
- [CHANGED] case saved as a pickle file
- [FIXED] fix computation of incremental variable cost of generators with surplus
- [FIXED] typo in pPeriodWeight definition
- [FIXED] typo in heat network flow magnitudes
- [CHANGED] introduced StableTime in Data_Generation file for nuclear unit operation
- [FIXED] introduce boiler expansion constraint eInstallBoiCap
- [CHANGED] introduced ProductionFunctionH2ToHeat in Data_Generation file for boilers that produce heat with hydrogen
- [CHANGED] changed ProductionFunction to ProductionFunctionHydro in Data_Generation file
- [FIXED] fix binary variables to obtain dual variables only those of the corresponding period and scenario
- [FIXED] initial equal to final inventory in candidate ESS or reservoir
- [CHANGED] introduction of boilers to produce heat
- [FIXED] control of max power greater than min power
- [FIXED] delete pMacCapacity in some inventory constraints
- [FIXED] fix several errors in hydro reservoir modeling
- [FIXED] fix several errors in heat modeling
- [CHANGED] avoid some computations is converting small parameters to 0
- [CHANGED] add curtailment in summary generation file
- [CHANGED] introduction of HiGHS options and as default solver
- [CHANGED] introduction of StableTime in Data_Generation for nuclear units
- [CHANGED] introduction of MinimumPowerHeat/MaximumPowerHeat in Data_Generation for CHP units
- [CHANGED] inventories/reservoir volumes are no longer fixed to their initial value at the end of every storage type cycle

## [4.15.8] - 2024-03-12

- [FIXED] check calls of mutable parameters
- [FIXED] change sign of water/energy values
- [FIXED] fix sign of dual variable of equality constraints
- [FIXED] fix some errors in cases with no renewables
- [CHANGED] fix some future warnings in output results

## [4.15.7] - 2024-02-27

- [FIXED] fix variable fuel cost and variable emission cost
- [FIXED] fix typo en H2 and heat balance equations
- [CHANGED] tighten formulation of second charge/discharge block
- [CHANGED] added a epsilon penalty in the o.f. to ohmic losses to avoid losses with spillage/curtailment
- [FIXED] initialization of the set of load levels up to the current stage
- [CHANGED] if initial inventory is out of bounds, fix it to the closest bound
- [CHANGED] detect reserve margin feasibility
- [CHANGED] reserve margin constraint is not formulated if there are no candidate generation units
- [CHANGED] time reduction in outputting results
- [CHANGED] add a small tolerance to avoid pumping/charging with curtailment/spillage
- [FIXED] clean up output results module
- [FIXED] change in the system inertia constraint
- [FIXED] introduction of line availability in electricity, H2, and heat balance equations
- [CHANGED] split total generation in different technologies in balance results
- [FIXED] introduction of line availability in electricity, H2, and heat balance equations
- [CHANGED] not all the stages must have the same duration
- [FIXED] computation of fixed costs for several years
- [FIXED] change some performance issues in ESS operation results
- [CHANGED] flexibility to consider generating units not for all the periods
- [FIXED] introduce initial inventory as a variable for ESS candidates
- [CHANGED] clean up of dynamic sets to avoid the use of static sets
- [FIXED] typo in dual variable of reserve margin constraint
- [FIXED] include minimum reservoir volume
- [FIXED] modify the condition to delete set na
- [FIXED] don't fix the storage of ESS candidates to its initial storage in any cycle
- [FIXED] fix the initial storage of ESS candidates to its maximum storage
- [FIXED] fix error in system emission constraint
- [CHANGED] clean up of s2n in formulation
- [FIXED] consistency of heat units
- [FIXED] fix error for stages with duration 0
- [CHANGED] add minimum RES energy in Data_RESEnergy file to consider minimum RES energy production
- [CHANGED] scale eMinSystemRESEnergy to GW instead of GWh
- [CHANGED] add MarginalRESEnergy output file to consider the marginal RES energy production

## [4.15.6] - 2024-01-25

- [CHANGED] some typos

## [4.15.5] - 2024-01-25

- [FIXED] fix error in output results with multiple
- [CHANGED] add column ProductionFunctionHeat in Data_Generation file to consider heat production of generators
- [CHANGED] add column HTNSCost in Data_Parameter file to consider heat not served cost
- [CHANGED] add column IndBinNetHeatInvest in Data_Option file to consider binary or not heat network investment decisions

## [4.15.4] - 2024-01-18

- [FIXED] fix error when some scenarios have prob 0

## [4.15.3] - 2024-01-16

- [CHANGED] move the computation of storage total energy inflows to reduce computation time
- [CHANGED] avoid the use of last in computing duals

## [4.15.2] - 2024-01-15

- [FIXED] allow solving just one period out of several defined
- [CHANGED] split variable definition and bound assignment
- [CHANGED] simplify the dual variables computation

## [4.15.1] - 2023-12-27

- [CHANGED] avoid some future warnings in output results

## [4.15.0] - 2023-12-27

- [CHANGED] introduce the variable emission cost file

## [4.14.12] - 2023-12-20

- [CHANGED] allow the use of GAMS as a solver
- [CHANGED] avoid formulation of adequacy constraints if already satisfied with existing capacity

## [4.14.11] - 2023-12-09

- [FIXED] fix error associated to the period probability in the objective function
- [FIXED] fix error in considering initial and final period for investment or retirement decisions

## [4.14.10] - 2023-12-01

- [FIXED] change the name and delete some duplicated result output files

## [4.14.9] - 2023-11-24

- [FIXED] values 0 of availability not changed to 1

## [4.14.8] - 2023-11-03

- [FIXED] declare StageWeight and LoadLevelWeight as NonNegativeReals
- [FIXED] fix in eHydroInventory constraint the conversion constant 0.0036

## [4.14.7] - 2023-10-26

- [FIXED] fix the condition to solve the complete problem

## [4.14.6] - 2023-10-22

- [FIXED] fix some pandas warnings

## [4.14.5] - 2023-10-20

- [FIXED] if there are system emission constraints no stage run can be done

## [4.14.4] - 2023-10-15

- [FIXED] check that the duration of all the stages is equal
- [FIXED] cycles of ESS and hydro reservoirs can't exceed the duration of the stage

## [4.14.3] - 2023-10-05

- [FIXED] fix the reservoir volumes at the end of the period and for every water cycle
- [FIXED] change the meaning of weekly storage/reservoir type by fixing the inventory/volume at the end of the month to the initial one

## [4.14.2] - 2023-09-23

- [CHANGED] avoid the use of max in bounds definition
- [FIXED] fixed some errors associated to ESS and hydropower plants

## [4.14.1] - 2023-09-19

- [FIXED] fixed some errors associated to hydropower plants parameters/variables
- [FIXED] fixed solving of the investment decision problem and computation of dual variables when there are many scenarios
- [FIXED] fixed computation of efficiency parameter of water reservoir and ESS units
- [FIXED] fixed computation of the hydro units water cycle
- [FIXED] fixed formulation of the maximum CO2 emission constraint

## [4.14.0] - 2023-09-13

- [CHANGED] added emission file to introduce the maximum system emission
- [CHANGED] added the maximum CO2 emission constraint, eMaxSystemEmission, and the resulting MarginalEmission file
- [CHANGED] include period (year) in the adequacy reserve margin file, ReserveMargin

## [4.13.0] - 2023-08-24

- [CHANGED] added the hydrogen demand and network, DemandHydrogen and NetworkHydrogen input files
- [CHANGED] added IndBinNetH2Invest in Option file to relax hydrogen network investment decisions. This is needed to keep compatibility with previous cases
- [CHANGED] added HNSCost (hydrogen not served cost) in Parameter file. This is needed to keep compatibility with previous cases
- [CHANGED] added production function of electrolyzers in Generation file to model hydrogen production. This is needed to keep compatibility with previous cases
- [CHANGED] added eConsecutiveRsrInvest and eConsecutiveNet2Invest constraints
- [CHANGED] added eBalanceH2 constraints

## [4.12.1] - 2023-08-22

- [FIXED] fix indices of the dual variables of the adequacy constraints in output results
- [CHANGED] added writing of the dual variables of the reservoir volume constraints in output results
- [FIXED] fix error in problem solving when there are no candidate hydro reservoirs
- [FIXED] fix error in units of water values in output results

## [4.12.0] - 2023-08-08

- [CHANGED] added eMaxVolume2Comm and eMinVolume2Comm constraints
- [CHANGED] added eTrbReserveUpIfEnergy, eTrbReserveDwIfEnergy, ePmpReserveUpIfEnergy, and ePmpReserveDwIfEnergy constraints
- [CHANGED] added IndBinRsrInvest in Option file to relax reservoir investment decisions. This is needed to keep compatibility with previous cases
- [CHANGED] added production function of hydropower plants in Generation file to be modeled in water units instead of energy units. This is needed to keep
  compatibility with previous cases
- [CHANGED] added dictionaries of hydro basin topology in water units (Dict_Reservoir, Dict_ReservoirToHydro, Dict_HydroToReservoir,
  Dict_ReservoirToPumpedHydro, Dict_PumpedHydroToReservoir, Dict_ReservoirToReservoir)
- [CHANGED] added data for water hydro inflows and outflows (Data_HydroInflows, Data_HydroOutflows)
- [CHANGED] added data for reservoirs (Data_Reservoir, Data_VariableMaxVolume, oT_Data_VariableMinVolume)

## [4.11.14] - 2023-07-08

- [FIXED] simplify input data and fix division by zero in output results
- [FIXED] several fixes in input data, model formulation, problem solving, and output results modules
- [FIXED] fix output of investment results
- [FIXED] reorganize the balance equation to avoid negative dual variables
- [CHANGED] NetworkCommitment file only if needed
- [CHANGED] Computation of problem size
- [FIXED] fixed vMaxCommitment in input data
- [FIXED] fixed vLineOnState and vLineOffState in input data for all the lines
- [CHANGED] add problem size in log file

## [4.11.13] - 2023-06-18

- [FIXED] fixed error in marginals of adequacy constraints
- [FIXED] fixed error in output results

## [4.11.12] - 2023-06-12

- [FIXED] fixed error in writing technology emission file of output results

## [4.11.11] - 2023-06-08

- [CHANGED] performance issues in input data and model formulation

## [4.11.10] - 2023-06-06

- [CHANGED] performance issues in input data
- [CHANGED] clean up the scaling of the output results

## [4.11.9] - 2023-05-30

- [CHANGED] avoid the repeated computation of modulo function with n
- [FIXED] fix error in output results
- [FIXED] fix computation of MarginalIncrementalGenerator output file

## [4.11.8] - 2023-05-29

- [CHANGED] introduce some dictionaries to avoid unnecessary computations
- [CHANGED] change name mTEPES.r to mTEPES.re
- [CHANGED] simplify some set combinations to reduce computation time

## [4.11.7] - 2023-05-17

- [CHANGED] reorganizing the ifs in model formulation

## [4.11.6] - 2023-05-15

- [CHANGED] adapt figures to altair 5.0.0

## [4.11.5] - 2023-05-13

- [CHANGED] fix some typos

## [4.11.3] - 2023-04-11

- [CHANGED] change the logical parameters to binary parameters
- [CHANGED] get dual variables for each solved problem

## [4.11.2] - 2023-04-07

- [CHANGED] avoid formulation of period/scenario not solved

## [4.11.1] - 2023-03-31

- [FIXED] reorganize the problem solving by period
- [FIXED] split formulation by period and scenario

## [4.11.0] - 2023-03-28

- [CHANGED] if no investment decisions all the scenarios with probability > 0 area solved sequentially
- [CHANGED] new VariableFuelCost input data file

## [4.10.6] - 2023-03-21

- [FIXED] fix a typo in the generation unit investment file

## [4.10.5] - 2023-03-17

- [FIXED] fix a typo in the generation unit investment file
- [FIXED] fix a typo in the name of the technology energy plot
- [FIXED] fix a typo in generation operation output results

## [4.10.4] - 2023-03-15

- [CHANGED] allow negative CO2 emission rate for biomass units

## [4.10.3] - 2023-03-10

- [CHANGED] introduce incompatibility constraint between charge and outflows use

## [4.10.2] - 2023-03-09

- [CHANGED] introduce incompatibility constraint between charge and outflows use
- [CHANGED] introduce conditions to avoid doing unnecessary computations in input data
- [CHANGED] introduce indicators to allow selecting output results

## [4.10.1] - 2023-02-27

- [FIXED] typo in writing ESS operation results
- [FIXED] typo in control of minimum energy infeasibility

## [4.10.0] - 2023-02-15

- [CHANGED] introduce control of minimum energy infeasibility
- [CHANGED] scale eMaxInventory2Comm, eMinInventory2Comm, and eInflows2Comm constraints
- [FIXED] force time step cycle for ESS inventory scheduling to be integer
- [FIXED] eliminate production and operating reserve variables if there is no pumping capability and no natural inflows
- [FIXED] fix error in determining the storage cycle of every ESS unit (as the minimum value between storage type, outflows type, and energy type) only if
  values of outflows and energy are provided
- [CHANGED] new VariableMaxEnergy and VariableMinEnergy input data files to determine mandatory max or min energy in time interval defined by EnergyType column
  in Generation file

## [4.9.1] - 2023-01-18

- [CHANGED] new TechnologyConsumptionEnergy output file
- [CHANGED] change some column headings in some output files
- [FIXED] fix error in the values of MWkm output results

## [4.9.0] - 2023-01-12

- [FIXED] fix error when writing NetworkInvestment and NetworkInvestment_MWkm output files
- [CHANGED] fix inventory to the lower bound instead of 0 to avoid warnings
- [CHANGED] print infeasibilities to a file
- [CHANGED] if investment/retirement lower and upper bounds are close to 0 or 1, make them 0 or 1
- [CHANGED] add two new network energy flow files per area and total
- [CHANGED] add two new energy balance files per area and technology
- [FIXED] fix ESS inventory constraint to include ESS candidate and existing units
- [FIXED] fix constraint of energy inflows management for the case of candidate ESS units
- [FIXED] add StorageInvestment option in Generation file to link the storage capacity and inflows to the investment decision
- [FIXED] add constraints related to the previous option

## [4.8.5] - 2022-12-06

- [CHANGED] fix some warning on input data module
- [FIXED] fix relation between generation investment and total charge
- [FIXED] change some future warnings and fix generation investment for ESS

## [4.8.4] - 2022-12-01

- [CHANGED] scenario probabilities declared as float
- [FIXED] control of inventory at the end of each stage and initial inventory fixed, but only if they are between limits
- [FIXED] error in declaring the parameter scenario probabilities
- [FIXED] avoid writing results for areas with no generation nor demand
- [FIXED] fix some errors in the use of dynamic sets in output results and other modules
- [CHANGED] extensive use of dynamic sets in several modules
- [CHANGED] modify output results to avoid the dynamic activation of the load levels depending on the stage
- [CHANGED] modify input data and output results to clean up the use of aggregated sets
- [CHANGED] modify output results to reduce printing time

## [4.8.3] - 2022-11-07

- [FIXED] fix typo in assign duration 0 to load levels not being considered
- [CHANGED] added new output files

## [4.8.2] - 2022-10-27

- [FIXED] fix computation of the demand when there are negative demands
- [CHANGED] avoid a second run of the model if no binary variables are in it
- [CHANGED] improve the computation of some double sets
- [CHANGED] change names of output files from charge to consumption
- [FIXED] protect against division by zero in output results
- [FIXED] fix computation of ESS invested capacity when the unit has no power, but charge
- [CHANGED] change computation of node and line to area sets
- [FIXED] fix an error in balance between output of the ESS and outflows
- [FIXED] fix an error fixing values of storage with outflows
- [CHANGED] fix typo in error message about input data
- [CHANGED] add file for spillage by technology TechnologySpillage
- [FIXED] fix some errors in OutputResults
- [CHANGED] avoid formulation of storage variables and equations with no generation and consumption power
- [FIXED] fix error in output results
- [CHANGED] introduction of a base year in Data_Parameter file for all the economic parameters being affected by the discount rate
- [FIXED] fix error in eTotalTCost constraint
- [FIXED] fix some errors in output results

## [4.7.1] - 2022-08-01

- [CHANGED] modify the definition of vMaxCommitment
- [CHANGED] add some KPIs, LCOE and net demand in output results
- [FIXED] fix error in operation cost
- [FIXED] fix error in vMaxCommitment
- [FIXED] fix eInstalGenCap and eUninstalGenCap
- [FIXED] fix detection of ESS units with no inflows
- [CHANGED] introduction of lower and upper bounds in investment and retirement decisions for network and generation

## [4.6.1] - 2022-06-15

- [CHANGED] addition of two new result files for percentage of spillage by generator and technology
- [FIXED] fix error in outflows equation
- [FIXED] fix some typos in input data
- [FIXED] fix error related to initial and final periods
- [CHANGED] addition of two new result files for percentage of energy curtailed by generator and technology
- [FIXED] error in the ramp up equation for the charge onf an ESS (eRampUpCharge)
- [CHANGED] introduce generation/demand balance energy result
- [FIXED] error in the generation/demand balance file

## [4.6.0] - 2022-05-19

- [CHANGED] introduce generation/demand balance output result
- [CHANGED] allow scenarios defined with 0 probability
- [CHANGED] avoid division by 0 in network utilization
- [CHANGED] avoid values of BigM = 0.0
- [CHANGED] change modeling of negative reactances
- [CHANGED] introduce maximum shifting time for DSM

## [4.5.2] - 2022-04-25

- [CHANGED] combine load level weight and duration
- [CHANGED] combine period weight and probability
- [CHANGED] fix some typos in cost summary
- [CHANGED] introduce annual discount rate to move money along the time
- [FIXED] control of non-negative values of some input data
- [CHANGED] avoid fixing voltage angle for the reference node with single node option

## [4.5.1] - 2022-03-25

- [CHANGED] split the objective function and investment constraints in two scripts

## [4.5.0] - 2022-03-20

- [CHANGED] introduce initial and final period for each generator/line. The periods must be non-negative integers
- [CHANGED] define the scenario probability of each period.
- [CHANGED] introduce changes to allow multiperiod cases.
- [CHANGED] introduce some infeasibility detection.
- [CHANGED] additional control on definition of ESS units.
- [CHANGED] exchange the order of scenario and period to do dynamic expansion planning.

## [4.4.0] - 2022-03-11

- [CHANGED] introduce options for deactivating the up/down ramp constraints and the minimum up/down time constraints.
- [CHANGED] introduce a single-node option for running a case study as a single node (no network constraints).
- [CHANGED] new option value 2 for IndBinGenInvest, IndBinGenRetirement, IndBinNetInvest for ignoring the investment/retirement decisions.
- [CHANGED] re-group the generation operation constraints by topics in separate functions.
- [CHANGED] change some names of output results to organize them by topics.

## [4.3.7] - 2022-02-28

- [CHANGED] saving new results about incremental generator '[oT_Result_IncrementalGenerator]'+CaseName+'.csv'.
- [CHANGED] saving new results about incremental emission of generators with surplus '[oT_Result_GenerationIncrementalEmission]'+CaseName+'.csv'.
- [CHANGED] saving new results about generation ramp surplus in '[oT_Result_GenerationRampUpSurplus]'+CaseName+'.csv' and
  '[oT_Result_GenerationRampDwSurplus]'+CaseName+'.csv'.
- [CHANGED] saving new results about generation surplus in '[oT_Result_GenerationSurplus]'+CaseName+'.csv'.
- [CHANGED] saving new results about incremental variable cost of generators with surplus in '[oT_Result_GenerationIncrementalVariableCost]'+CaseName+'.csv'.

## [4.3.6] - 2022-02-09

- [CHANGED] change of domain of some p.u. parameters to UnitInterval and others to Reals
- [CHANGED] change output of units not contributing to operating reserves
- [CHANGED] change on the assessment of the termination condition

## [4.3.5] - 2022-01-29

- [FIXED] detect ESS that only pump/charge
- [FIXED] exclude contribution to operating reserves of units with NoOperatingReserves=yes
- [FIXED] fix computation of dual variables of operating reserves

## [4.3.4] - 2022-01-27

- [FIXED] fix computation of log console option

## [4.3.3] - 2022-01-25

- [CHANGED] Permanent presence of the solver log file
- [CHANGED] LP-file writing depends of the pIndLogConsole

## [4.3.2] - 2022-01-24

- [FIXED] Append function updated to cumulate all stages before plotting the LSRMC
- [CHANGED] Condition updated in ProblemSolving to use Gurobi or Mosek

## [4.3.2] - 2022-01-24 - release candidate

- [FIXED] Legend in nodes in the network map
- [CHANGED] Use of the CBC as a recommended solver instead of GLPK
- [CHANGED] Adding pIndLogConsole in openTEPES_ProblemSolving.py

## [4.3.1] - 2022-01-19

- [CHANGED] improved network map representation in html
- [CHANGED] console log as option in input data

## [4.3.0] - 2021-12-31

- [CHANGED] improved representation of operating reserves

## [4.2.4] - 2021-12-30

- [FIXED] inertia constraints
- [FIXED] typos in output results
- [CHANGED] introduce html plots based on Altair

## [4.2.3] - 2021-12-17

- [FIXED] plots associated to ESS technologies

## [4.2.2] - 2021-12-08

- [FIXED] assessment of the locational short-run marginal costs

## [4.2.1] - 2021-12-01

- [FIXED] assessment of the locational short-run marginal costs

## [4.2.0] - 2021-11-11

- [CHANGED] introduction of a retirement cost to allow retirement decisions
- [CHANGED] elimination of line switching states

## [4.1.3] - 2021-10-31

- [FIXED] Generalization of the maximum commitment and mutually exclusive constraints

## [4.1.2] - 2021-10-28

- [FIXED] Removing option when the solver is called in ProblemSolving

## [4.1.1] - 2021-10-27

- [FIXED] adding mutually exclusive formulation for ESS, add output results of reserve margin

## [4.1.0] - 2021-10-22

- [CHANGED] introduction of mutually exclusive generator in generation file
- [CHANGED] Using TimeStep of 4 instead of 2 in Cases 9n and sSEP to speed-up the packaging tests

## [3.1.5] - 2021-10-15

- [FIXED] fix magnitude of the emission output

## [3.1.4] - 2021-09-30

- [FIXED] fix initialization of synchronous condenser and shunt candidate

## [3.1.3] - 2021-09-10

- [FIXED] fix in some equations the activation of the operating reserves

## [3.1.2] - 2021-07-12

- [FIXED] fix typo in network investment constraint to include candidate lines

## [3.1.1] - 2021-07-08

- [FIXED] change location of lea and lca computation

## [3.1.0] - 2021-07-07

- [CHANGED] definition of switching stages with dictionary and data files to allow less granularity in switching decisions

## [2.6.5] - 2021-07-04

- [FIXED] typos in line switching equations and redefinition of lea and lca sets

## [2.6.4] - 2021-06-23

- [FIXED] typo in equation formulating the total output of a unit
- [CHANGED] introduce binary commitment option for each unit
- [CHANGED] introduce adequacy reserve margin for each area
- [CHANGED] introduce availability for each unit

## [2.6.3] - 2021-06-20

- [FIXED] typo in investment constraint in model formulation

## [2.6.2] - 2021-06-18

- [CHANGED] updated for pyomo 6.0
- [CHANGED] if not defined length computed as geographical distance

## [2.6.1] - 2021-06-14

- [CHANGED] line length added in network input file
- [FIXED] error in output results due to stage weight

## [2.6.0] - 2021-05-27

- [CHANGED] new inertia constraint for each area
- [FIXED] change column BinarySwitching by Switching in network data meaning that line is able to switch or not

## [2.5.3] - 2021-05-14

- [FIXED] fix output results of storage utilization

## [2.5.2] - 2021-05-11

- [CHANGED] new ESS inventory utilization result file
- [FIXED] protection against stage with no load levels

## [2.5.1] - 2021-05-07

- [FIXED] introduction of stage weight in the operation variable cost

## [2.5.0] - 2021-04-29

- [CHANGED] generalize the definition of stages to allow using representative stages (weeks, days, etc.)

## [2.4.2] - 2021-04-29

- [CHANGED] initialize shutdown variable
- [FIXED] fix error in conditions to formulate the relationship between UC, startup and shutdown

## [2.4.1] - 2021-04-28

- [CHANGED] very small parameters -> 0 depending on the area
- [CHANGED] avoid use of list if not needed

## [2.4.0] - 2021-04-24

- [CHANGED] new input files VariableMaxConsumption and VariableMinConsumption and MininmumCharge column in Generation file
- [CHANGED] change names of MaximumStorage (MinimumStorage) files to VariableMaxStorage (VariableMinStorage)

## [2.3.1] - 2021-04-23

- [CHANGED] avoid superfluous equations

## [2.3.0] - 2021-04-20

- [CHANGED] separate model data and optimization model

## [2.2.5] - 2021-04-18

- [FIXED] fix commitment, startup and shutdown decisions of hydro units
- [FIXED] output results of storage units
- [FIXED] detection of storage units

## [2.2.4] - 2021-04-10

- [FIXED] fix line switch off constraint

## [2.2.3] - 2021-04-07

- [FIXED] determine the commitment and output of generating units at the beginning of each stage

## [2.2.2] - 2021-04-05

- [CHANGED] remove a warning in InputData

## [2.2.1] - 2021-04-03

- [CHANGED] added three new output files for line commitment, switch on and off
- [CHANGED] added three four output files for ESS energy outflows
- [FIXED] fix writing flexibility files for ESS

## [2.2.0] - 2021-03-31

- [CHANGED] introduction of Power-to-X in ESS. Modifies the Generation file and introduces a new EnergyOutflows file
- [CHANGED] introduction of switching decision for transmission lines. Modifies the Option file and introduces a new column BinarySwitching in Network file

## [2.1.0] - 2021-03-18

- [CHANGED] using README.rst instead of README.md
- [CHANGED] split openTEPES_ModelFormulation.py in multiple functions related to investment and operating constraints
- [CHANGED] split openTEPES_OutputResults.py in multiple functions related to investment and operating variables

## [2.0.24] - 2021-03-08

- [FIXED] changed location of the shell openTEPES to sub folder openTEPES with all modules
- [FIXED] updated \_init\_.py

## [2.0.23] - 2021-03-08

- [CHANGED] included metadata in pyproject.toml and also requirements (only pyomo, matplotlib, numpy, pandas, and psutil.)
- [CHANGED] created a README.md file
