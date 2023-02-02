.. openTEPES documentation master file, created by Andres Ramos

Mathematical Formulation
========================
Here we present the mathematical formulation of the optimization problem solved by the **openTEPES** model. See also some TEP-related publications:

* S. Lumbreras, H. Abdi, A. Ramos, and M. Moradi "Introduction: The Key Role of the Transmission Network" in the book S. Lumbreras, H. Abdi, A. Ramos (eds.) "Transmission Expansion Planning: The Network Challenges of the Energy Transition" Springer, 2020 ISBN 9783030494278 `10.1007/978-3-030-49428-5_1 <https://link.springer.com/chapter/10.1007/978-3-030-49428-5_1>`_

* S. Lumbreras, F. Banez-Chicharro, A. Ramos "Optimal Transmission Expansion Planning in Real-Sized Power Systems with High Renewable Penetration" Electric Power Systems Research 49, 76-88, Aug 2017 `10.1016/j.epsr.2017.04.020 <http://doi.org/10.1016/j.epsr.2017.04.020>`_

* S. Lumbreras, A. Ramos "The new challenges to transmission expansion planning. Survey of recent practice and literature review" Electric Power Systems Research 134: 19-29, May 2016 `10.1016/j.epsr.2015.10.013 <http://dx.doi.org/10.1016/j.epsr.2015.10.013>`_

* Q. Ploussard, L. Olmos and A. Ramos "A search space reduction method for transmission expansion planning using an iterative refinement of the DC Load Flow model" IEEE Transactions on Power Systems 35 (1): 152-162, Jan 2020 `10.1109/TPWRS.2019.2930719 <http://dx.doi.org/10.1109/TPWRS.2019.2930719>`_

* Q. Ploussard, L. Olmos and A. Ramos "An efficient network reduction method for transmission expansion planning using multicut problem and Kron" reduction IEEE Transactions on Power Systems 33 (6): 6120-6130, Nov 2018 `10.1109/TPWRS.2018.2842301 <http://dx.doi.org/10.1109/TPWRS.2018.2842301>`_

* Q. Ploussard, L. Olmos and A. Ramos "An operational state aggregation technique for transmission expansion planning based on line benefits" IEEE Transactions on Power Systems 32 (4): 2744-2755, Oct 2017 `10.1109/TPWRS.2016.2614368 <http://dx.doi.org/10.1109/TPWRS.2016.2614368>`_

Indices
-------
==============  ========================================================================
:math:`p`       Period (e.g., year)
:math:`ω`       Scenario
:math:`n`       Load level (e.g., hour)
:math:`\nu`     Time step. Duration of each load level (e.g., 2 h, 3 h)
:math:`g`       Generator (thermal or hydro unit or energy storage system)
:math:`t`       Thermal unit
:math:`e`       Energy Storage System (ESS)
:math:`i, j`    Node
:math:`z`       Zone. Each node belongs to a zone :math:`i \in z`
:math:`a`       Area. Each zone belongs to an area :math:`z \in a`
:math:`r`       Region. Each area belongs to a region :math:`a \in r`
:math:`c`       Circuit
:math:`ijc`     Line (initial node, final node, circuit)
:math:`EG, CG`  Set of existing and candidate generators
:math:`EE, CE`  Set of existing and candidate ESS
:math:`EL, CL`  Set of existing and non-switchable, and candidate and switchable lines
==============  ========================================================================

Parameters
----------

They are written in **uppercase** letters.

==================  ====================================================  =======
**General**
------------------  ----------------------------------------------------  -------
:math:`\delta`      Annual discount rate                                  p.u.
:math:`\Omega`      Period (year) weight                                  p.u.
:math:`T`           Base period (year)                                    year
:math:`DF_p`        Discount factor for each period (year)                p.u.
==================  ====================================================  =======

==================  ====================================================  =======
**Demand**
------------------  ----------------------------------------------------  -------
:math:`D^p_{ωni}`   Demand in each node                                   GW
:math:`PD_a`        Peak demand in each area                              GW
:math:`DUR_n`       Duration of each load level                           h
:math:`CENS`        Cost of energy not served. Value of Lost Load (VoLL)  €/MWh
==================  ====================================================  =======

==================  ====================================================  =======
**Scenarios**
------------------  ----------------------------------------------------  -------
:math:`P^ω_p`         Probability of each scenario in each period           p.u.
==================  ====================================================  =======

==========================================  ==================================================================  ====
**Operating reserves**
------------------------------------------  ------------------------------------------------------------------  ----
:math:`URA, DRA`                            Upward and downward reserve activation                              p.u.
:math:`\underline{DtUR}, \overline{DtUR}`   Minimum and maximum ratios downward to upward operating reserves    p.u.
:math:`UR^p_{ωna}, DR^p_{ωna}`              Upward and downward operating reserves for each area                GW
==========================================  ==================================================================  ====

==============================  ========================================================  ====
**Adequacy system reserve margin**
------------------------------  --------------------------------------------------------  ----
:math:`RM_a`                    Adequacy system reserve margin for each area              p.u.
==============================  ========================================================  ====

==============================  ========================================================  ====
**System inertia**
------------------------------  --------------------------------------------------------  ----
:math:`SI^p_{ωna}`              System inertia for each area                              s
==============================  ========================================================  ====

=====================================================  ========================================================================================================================  ============
**Generation system**
-----------------------------------------------------  ------------------------------------------------------------------------------------------------------------------------  ------------
:math:`CFG_g`                                          Annualized fixed cost of a candidate generator                                                                            M€/yr
:math:`CFR_g`                                          Annualized fixed cost of a candidate generator to be retired                                                              M€/yr
:math:`A_g`                                            Availability of each generator for adequacy reserve margin                                                                p.u.
:math:`\underline{GP}_g, \overline{GP}_g`              Rated minimum load and maximum output of a generator                                                                      GW
:math:`\underline{GP}^p_{ωng}, \overline{GP}^p_{ωng}`  Minimum load and maximum output of a generator                                                                            GW
:math:`\underline{GC}^p_{ωne}, \overline{GC}^p_{ωne}`  Minimum and maximum consumption of an ESS                                                                                 GW
:math:`CF_g, CV_g`                                     Fixed (no load) and variable cost of a generator. Variable cost includes fuel and O&M                                     €/h, €/MWh
:math:`CE_g`                                           Emission cost of a generator                                                                                              €/MWh
:math:`CV_e`                                           Variable cost of an ESS when charging                                                                                     €/MWh
:math:`RU_g, RD_g`                                     Ramp up/down of a non-renewable unit or maximum discharge/charge rate for ESS discharge/charge                            MW/h
:math:`TU_t, TD_t`                                     Minimum uptime and downtime of a thermal unit                                                                             h
:math:`ST_e`                                           Maximum shift time of an ESS unit (in particular, for demand side management)                                             h
:math:`CSU_g, CSD_g`                                   Startup and shutdown cost of a committed unit                                                                             M€
:math:`\tau_e`                                         Storage cycle of the ESS (e.g., 1, 24, 168, 8736 h -for daily, weekly, monthly, yearly-)                                  h
:math:`\rho_e`                                         Outflow cycle of the ESS (e.g., 1, 24, 168, 8736 h -for hourly, daily, weekly, monthly, yearly-)                          h
:math:`\sigma_g`                                       Energy cycle of the unit (e.g., 24, 168, 672, 8736 h -for daily, weekly, monthly, yearly-)                                h
:math:`GI_g`                                           Generator inertia                                                                                                         s
:math:`EF_e`                                           Round-trip efficiency of the pump/turbine cycle of a pumped-storage hydro power plant or charge/discharge of a battery    p.u.
:math:`\underline{I}^p_{ωne}, \overline{I}^p_{ωne}`    Maximum and minimum capacity of an ESS (e.g., hydro power plant, closed-loop pumped-storage hydro)                        GWh
:math:`\underline{E}^p_{ωne}, \overline{E}^p_{ωne}`    Maximum and minimum energy produced by a unit in an interval defined                                                      GW
:math:`EI^p_{ωne}`                                     Energy inflows of an ESS (e.g., hydro power plant)                                                                        GW
:math:`EO^p_{ωne}`                                     Energy outflows of an ESS (e.g., H2, EV, hydro power plant)                                                               GW
=====================================================  ========================================================================================================================  ============

=========================================  =================================================================================================================  =====
**Transmission system**
-----------------------------------------  -----------------------------------------------------------------------------------------------------------------  -----
:math:`CFT_{ijc}`                          Annualized fixed cost of a candidate transmission line                                                             M€/yr
:math:`\overline{F}_{ijc}`                 Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a transmission line      GW
:math:`\overline{F}'_{ijc}`                Maximum flow used in the Kirchhoff's 2nd law constraint (e.g., disjunctive constraint for the candidate AC lines)  GW
:math:`L_{ijc}, X_{ijc}`                   Loss factor and reactance of a transmission line                                                                   p.u.
:math:`SON_{ijc}, SOF_{ijc}`               Minimum switch-on and switch-off state of a line                                                                   h
:math:`S_B`                                Base power                                                                                                         GW
=========================================  =================================================================================================================  =====

The net transfer capacity of a transmission line can be different in each direction. However, here it is presented as equal for simplicity.

Variables
---------

They are written in **lowercase** letters.

===================  ==================  ===
**Demand**
-------------------  ------------------  ---
:math:`ens^p_{ωni}`   Energy not served   GW
===================  ==================  ===

==========================================  ==============================================================================  =====
**Generation system**
------------------------------------------  ------------------------------------------------------------------------------  -----
:math:`icg_{pg}`                            Candidate generator or ESS installed or not                                     {0,1}
:math:`rcg_{pg}`                            Candidate generator or ESS retired   or not                                     {0,1}
:math:`gp^p_{ωng}, gc^p_{ωng}`              Generator output (discharge if an ESS) and consumption (charge if an ESS)       GW
:math:`go^p_{ωne}`                          Generator outflows of an ESS                                                    GW
:math:`p^p_{ωng}`                           Generator output of the second block (i.e., above the minimum load)             GW
:math:`c^p_{ωne}`                           Generator charge                                                                GW
:math:`ur^p_{ωng}, dr^p_{ωng}`              Upward and downward operating reserves of a non-renewable generating unit       GW
:math:`ur'^p_{ωne}, dr'^p_{ωne}`            Upward and downward operating reserves of an ESS as a consumption unit          GW
:math:`ei^p_{ωne}`                          Variable energy inflows of a candidate ESS (e.g., hydro power plant)            GW
:math:`i^p_{ωne}`                           ESS stored energy (inventory, reservoir energy, state of charge)                GWh
:math:`s^p_{ωne}`                           ESS spilled energy                                                              GWh
:math:`uc^p_{ωng}, su^p_{ωng}, sd^p_{ωng}`  Commitment, startup and shutdown of generation unit per load level              {0,1}
:math:`uc'_g`                               Maximum commitment of a generation unit for all the load levels                 {0,1}
==========================================  ==============================================================================  =====

======================================================  ==============================================================  =====
**Transmission system**
------------------------------------------------------  --------------------------------------------------------------  -----
:math:`ict_{pijc}`                                      Candidate line installed or not                                 {0,1}
:math:`swt^p_{ωnijc}, son^p_{ωnijc}, sof^p_{ωnijc}`     Switching state, switch-on and switch-off of a line             {0,1}
:math:`f^p_{ωnijc}`                                     Flow through a line                                             GW
:math:`l^p_{ωnijc}`                                     Half ohmic losses of a line                                     GW
:math:`θ^p_{ωni}`                                       Voltage angle of a node                                         rad
======================================================  ==============================================================  =====

Equations
---------

The names between parenthesis correspond to the names of the constraints in the code.

**Objective function**: minimization of total (investment and operation) cost for the multi-period scope of the model

Generation, storage and network investment cost plus retirement cost [M€] «``eTotalFCost``»

:math:`\sum_{pg} DF_p CFG_g icg_{pg} + \sum_{pg} DF_p CFR_g rcg_{pg} + \sum_{pijc} DF_p CFT_{ijc} ict_{pijc} +`

Generation operation cost [M€] «``eTotalGCost``»

:math:`\sum_{pωng} {[DF_p P^ω_p DUR_n (CV_g gp^p_{ωng} + CF_g uc^p_{ωng}) + DF_p CSU_g su^p_{ωng} + DF_p CSD_g sd^p_{ωng}]} +`

Generation emission cost [M€] «``eTotalECost``»

:math:`\sum_{pωng} {DF_p P^ω_p DUR_n CE_g gp^p_{ωng}} +`

Variable consumption operation cost [M€] «``eTotalCCost``»

:math:`\sum_{pωne}{DF_p P^ω_p DUR_n CV_e gc^p_{ωne}} +`

Reliability cost [M€] «``eTotalRCost``»

:math:`\sum_{pωni}{DF_p P^ω_p DUR_n CENS ens^p_{ωni}}`

All the periodical (annual) costs of a period :math:`p` are updated considering that the period (e.g., 2030) is replicated for a number of years defined by its weight :math:`\Omega` (e.g., 5 times) and discounted to the base year :math:`T` (e.g., 2020) with this discount factor :math:`DF_p = \frac{(1+\delta)^{\Omega}-1}{\delta(1+\delta)^{\Omega-1+p-T}}`.

**Constraints**

**Generation and network investment and retirement**

Investment and retirement decisions in consecutive years «``eConsecutiveGenInvest``» «``eConsecutiveGenRetire``» «``eConsecutiveNetInvest``»

:math:`icg_{p-1,g} \leq icg_{pg} \quad \forall pg, g \in CG`

:math:`rcg_{p-1,g} \leq rcg_{pg} \quad \forall pg, g \in CG`

:math:`ict_{p-1,ijc} \leq ict_{pijc} \quad \forall pijc, ijc \in CL`

**Generation operation**

Commitment decision bounded by the investment decision for candidate committed units (all except the VRE units) [p.u.] «``eInstalGenComm``»

:math:`uc^p_{ωng} \leq icg_{pg} \quad \forall pωng, g \in CG`

Commitment decision bounded by the investment decision for candidate ESS [p.u.] «``eInstalESSComm``»

:math:`uc^p_{ωne} \leq icg_{pe} \quad \forall pωne, e \in CE`

Output and consumption bounded by investment decision for candidate ESS [p.u.] «``eInstalGenCap``» «``eInstalConESS``»

:math:`\frac{gp^p_{ωne}}{\overline{GP}^p_{ωne}} \leq icg_{pe} \quad \forall pωne, e \in CE`

:math:`\frac{gc^p_{ωne}}{\overline{GP}^p_{ωne}} \leq icg_{pe} \quad \forall pωne, e \in CE`

Adequacy system reserve margin [p.u.] «``eAdequacyReserveMargin``»

:math:`\sum_{g \in a, EG} \overline{GP}_g A_g + \sum_{g \in a, CG} icg_{pg}  \overline{GP}_g A_g \geq PD_a RM_a \quad \forall pa`

Balance of generation and demand at each node with ohmic losses [GW] «``eBalance``»

:math:`\sum_{g \in i} gp^p_{ωng} - \sum_{e \in i} gc^p_{ωne} + ens^p_{ωni} = D^p_{ωni} + \sum_{jc} l^p_{ωnijc} + \sum_{jc} l^p_{ωnjic} + \sum_{jc} f^p_{ωnijc} - \sum_{jc} f^p_{ωnjic} \quad \forall pωni`

System inertia for each area [s] «``eSystemInertia``»

:math:`\sum_{g \in a} \frac{GI_g}{\overline{GP}_g} gp^p_{ωng} \geq SI^p_{ωna} \quad \forall pωna`

Upward and downward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] «``eOperReserveUp``» «``eOperReserveDw``»

:math:`\sum_{g \in a} ur^p_{ωng} + \sum_{e \in a} ur'^p_{ωne} = UR^p_{ωna} \quad \forall pωna`

:math:`\sum_{g \in a} dr^p_{ωng} + \sum_{e \in a} dr'^p_{ωne} = DR^p_{ωna} \quad \forall pωna`

Ratio between downward and upward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] «``eReserveMinRatioDwUp``» «``eReserveMaxRatioDwUp``» «``eRsrvMinRatioDwUpESS``» «``eRsrvMaxRatioDwUpESS``»

:math:`\underline{DtUR} \: ur^p_{ωng}  \leq dr^p_{ωng}  \leq \overline{DtUR} \: ur^p_{ωng}  \quad \forall pωng`

:math:`\underline{DtUR} \: ur'^p_{ωne} \leq dr'^p_{ωne} \leq \overline{DtUR} \: ur'^p_{ωne} \quad \forall pωne`

VRES units (i.e., those with linear variable cost equal to 0 and no storage capacity) do not contribute to the the operating reserves.

Operating reserves from ESS can only be provided if enough energy is available for producing [GW] «``eReserveUpIfEnergy``» «``eReserveDwIfEnergy``»

:math:`ur^p_{ωne} \leq \frac{            i^p_{ωne}}{DUR_n} \quad \forall pωne`

:math:`dr^p_{ωne} \leq \frac{I^p_{ωne} - i^p_{ωne}}{DUR_n} \quad \forall pωne`

or for storing [GW] «``eESSReserveUpIfEnergy``» «``eESSReserveDwIfEnergy``»

:math:`ur'^p_{ωne} \leq \frac{I^p_{ωne} - i^p_{ωne}}{DUR_n} \quad \forall pωne`

:math:`dr'^p_{ωne} \leq \frac{            i^p_{ωne}}{DUR_n} \quad \forall pωne`

Maximum and minimum inventory of ESS candidates (only for load levels multiple of 1, 24, 168, 8736 h depending on the ESS storage type) constrained by the ESS commitment decision times the maximum capacity [GWh] «``eMaxInventory2Comm``» «``eMinInventory2Comm``»

:math:`i^p_{ωne} <= uc^p_{ωne} \overline{I}^p_{ωne}   \quad \forall pωne, e \in CE`

:math:`i^p_{ωne} >= uc^p_{ωne} \underline{I}^p_{ωne}  \quad \forall pωne, e \in CE`

Energy inflows of ESS candidates (only for load levels multiple of 1, 24, 168, 8736 h depending on the ESS storage type) constrained by the ESS commitment decision times the inflows data [GWh] «``eInflows2Comm``»

:math:`ei^p_{ωne} <= uc^p_{ωne} EI^p_{ωne} \quad \forall pωne, e \in CE`

ESS energy inventory (only for load levels multiple of 1, 24, 168 h depending on the ESS storage type) [GWh] «``eESSInventory``»

:math:`i^p_{ω,n-\frac{\tau_e}{\nu},e} + \sum_{n' = n-\frac{\tau_e}{\nu}}^n DUR_n' (EI^p_{ωn'e} - go^p_{ωn'e} - gp^p_{ωn'e} + EF_e gc^p_{ωn'e}) = i^p_{ωne} + s^p_{ωne} \quad \forall pωne, e \in EE`

:math:`i^p_{ω,n-\frac{\tau_e}{\nu},e} + \sum_{n' = n-\frac{\tau_e}{\nu}}^n DUR_n' (ei^p_{ωn'e} - go^p_{ωn'e} - gp^p_{ωn'e} + EF_e gc^p_{ωn'e}) = i^p_{ωne} + s^p_{ωne} \quad \forall pωne, e \in CE`

Maximum shift time of stored energy [GWh]. It is thought to be applied to demand side management «``eMaxShiftTime``»

:math:`DUR_n EF_e gc^p_{ωne}) \leq \sum_{n' = n+1}^{n+\frac{ST_e}{\nu}} DUR_n' gp^p_{ωn'e}  \quad \forall pωne`

ESS outflows (only for load levels multiple of 1, 24, 168, 672, and 8736 h depending on the ESS outflow cycle) must be satisfied [GWh] «``eEnergyOutflows``»

:math:`\sum_{n' = n-\frac{\tau_e}{\rho_e}}^n go^p_{ωn'e} DUR_n' = \sum_{n' = n-\frac{\tau_e}{\rho_e}}^n EO^p_{ωn'e} DUR_n' \quad \forall pωne, n \in \rho_e`

Minimum and maximum energy production (only for load levels multiple of 24, 168, 672, 8736 h depending on the unit energy type) must be satisfied [GWh] «``eMinimumEnergy``»  «``eMaximumEnergy``»

:math:`\sum_{n' = n-\sigma_g^n} gp^p_{ωn'g} DUR_n' \leq \sum_{n' = n-\sigma_g^n} \overline{E}^p_{ωn'g} DUR_n' \quad \forall pωng`

:math:`\sum_{n' = n-\sigma_g^n} gp^p_{ωn'g} DUR_n' \geq \sum_{n' = n-\sigma_g^n} \underline{E}^p_{ωn'g} DUR_n' \quad \forall pωng`

Maximum and minimum output of the second block of a committed unit (all except the VRES units) [p.u.] «``eMaxOutput2ndBlock``» «``eMinOutput2ndBlock``»

* D.A. Tejada-Arango, S. Lumbreras, P. Sánchez-Martín, and A. Ramos "Which Unit-Commitment Formulation is Best? A Systematic Comparison" IEEE Transactions on Power Systems 35 (4): 2926-2936, Jul 2020 `10.1109/TPWRS.2019.2962024 <https://doi.org/10.1109/TPWRS.2019.2962024>`_

* C. Gentile, G. Morales-España, and A. Ramos "A tight MIP formulation of the unit commitment problem with start-up and shut-down constraints" EURO Journal on Computational Optimization 5 (1), 177-201, Mar 2017. `10.1007/s13675-016-0066-y <http://dx.doi.org/10.1007/s13675-016-0066-y>`_

* G. Morales-España, A. Ramos, and J. Garcia-Gonzalez "An MIP Formulation for Joint Market-Clearing of Energy and Reserves Based on Ramp Scheduling" IEEE Transactions on Power Systems 29 (1): 476-488, Jan 2014. `10.1109/TPWRS.2013.2259601 <http://dx.doi.org/10.1109/TPWRS.2013.2259601>`_

* G. Morales-España, J.M. Latorre, and A. Ramos "Tight and Compact MILP Formulation for the Thermal Unit Commitment Problem" IEEE Transactions on Power Systems 28 (4): 4897-4908, Nov 2013. `10.1109/TPWRS.2013.2251373 <http://dx.doi.org/10.1109/TPWRS.2013.2251373>`_

:math:`\frac{p^p_{ωng} + ur^p_{ωng}}{\overline{GP}^p_{ωng} - \underline{GP}^p_{ωng}} \leq uc^p_{ωng} \quad \forall pωng`

:math:`\frac{p^p_{ωng} - dr^p_{ωng}}{\overline{GP}^p_{ωng} - \underline{GP}^p_{ωng}} \geq 0          \quad \forall pωng`

Maximum and minimum charge of an ESS [p.u.] «``eMaxCharge``» «``eMinCharge``»

:math:`\frac{c^p_{ωne} + dr'^p_{ωne}}{\overline{GC}^p_{ωne} - \underline{GC}^p_{ωne}} \leq 1 \quad \forall pωne`

:math:`\frac{c^p_{ωne} - ur'^p_{ωne}}{\overline{GC}^p_{ωne} - \underline{GC}^p_{ωne}} \geq 0 \quad \forall pωne`

Incompatibility between charge and discharge of an ESS [p.u.] «``eChargeDischarge``»

:math:`\frac{p^p_{ωne} + URA \: ur'^p_{ωne}}{\overline{GP}^p_{ωne} - \underline{GP}^p_{ωne}} + \frac{c^p_{ωne} + DRA \: dr'^p_{ωne}}{\overline{GC}^p_{ωne} - \underline{GC}^p_{ωne}} \leq 1 \quad \forall pωne, e \in EE, CE`

Total output of a committed unit (all except the VRES units) [GW] «``eTotalOutput``»

:math:`\frac{gp^p_{ωng}}{\underline{GP}^p_{ωng}} = uc^p_{ωng} + \frac{p^p_{ωng} + URA \: ur^p_{ωng} - DRA \: dr^p_{ωng}}{\underline{GP}^p_{ωng}} \quad \forall pωng`

Total charge of an ESS [GW] «``eESSTotalCharge``»

:math:`\frac{gc^p_{ωne}}{\underline{GC}^p_{ωne}} = 1 + \frac{c^p_{ωne} + URA \: ur'^p_{ωne} - DRA \: dr'^p_{ωne}}{\underline{GC}^p_{ωne}} \quad \forall pωne, e \in EE, CE`

Logical relation between commitment, startup and shutdown status of a committed unit (all except the VRES units) [p.u.] «``eUCStrShut``»

:math:`uc^p_{ωng} - uc^p_{ω,n-\nu,g} = su^p_{ωng} - sd^p_{ωng} \quad \forall pωng`

Maximum commitment of a committable unit (all except the VRES units) [p.u.] «``eMaxCommitment``»

:math:`uc^p_{ωng} \leq uc'_g \quad \forall pωng`

Maximum commitment of any unit [p.u.] «``eMaxCommitGen``»

:math:`\sum_{pωn} \frac{gp^p_{ωng}}{\overline{GP}_g} \leq uc'_g \quad \forall pωng`

Mutually exclusive :math:`g` and :math:`g'` units (e.g., thermal, ESS, VRES units) [p.u.] «``eExclusiveGens``»

:math:`uc'_g + uc'_{g'} \leq 1 \quad \forall g, g'`

Initial commitment of the units is determined by the model based on the merit order loading, including the VRES and ESS units.

Maximum ramp up and ramp down for the second block of a non-renewable (thermal, hydro) unit [p.u.] «``eRampUp``» «``eRampDw``»

* P. Damcı-Kurt, S. Küçükyavuz, D. Rajan, and A. Atamtürk, “A polyhedral study of production ramping,” Math. Program., vol. 158, no. 1–2, pp. 175–205, Jul. 2016. `10.1007/s10107-015-0919-9 <https://doi.org/10.1007/s10107-015-0919-9>`_

:math:`\frac{- p^p_{ω,n-\nu,g} - dr^p_{ω,n-\nu,g} + p^p_{ωng} + ur^p_{ωng}}{DUR_n RU_g} \leq   uc^p_{ωng}       - su^p_{ωng} \quad \forall pωng`

:math:`\frac{- p^p_{ω,n-\nu,g} + ur^p_{ω,n-\nu,g} + p^p_{ωng} - dr^p_{ωng}}{DUR_n RD_g} \geq - uc^p_{ω,n-\nu,g} + sd^p_{ωng} \quad \forall pωng`

Maximum ramp down and ramp up for the charge of an ESS [p.u.] «``eRampUpCharge``» «``eRampDwCharge``»

:math:`\frac{- c^p_{ω,n-\nu,e} - ur^p_{ω,n-\nu,e} + c^p_{ωne} + dr^p_{ωne}}{DUR_n RD_e} \leq   1 \quad \forall pωne`

:math:`\frac{- c^p_{ω,n-\nu,e} + dr^p_{ω,n-\nu,e} + c^p_{ωne} - ur^p_{ωne}}{DUR_n RU_e} \geq - 1 \quad \forall pωne`

Minimum up time and down time of thermal unit [h] «``eMinUpTime``» «``eMinDownTime``»

* D. Rajan and S. Takriti, “Minimum up/down polytopes of the unit commitment problem with start-up costs,” IBM, New York, Technical Report RC23628, 2005. https://pdfs.semanticscholar.org/b886/42e36b414d5929fed48593d0ac46ae3e2070.pdf

:math:`\sum_{n'=n+\nu-TU_t}^n su^p_{ωn't} \leq     uc^p_{ωnt} \quad \forall pωnt`

:math:`\sum_{n'=n+\nu-TD_t}^n sd^p_{ωn't} \leq 1 - uc^p_{ωnt} \quad \forall pωnt`

**Network operation**

Logical relation between transmission investment and switching {0,1} «``eLineStateCand``»

:math:`swt^p_{ωnijc} \leq ict_{pijc} \quad \forall pωnijc, ijc \in CL`

Logical relation between switching state, switch-on and switch-off status of a line [p.u.] «``eSWOnOff``»

:math:`swt^p_{ωnijc} - swt^p_{ω,n-\nu,ijc} = son^p_{ωnijc} - sof^p_{ωnijc} \quad \forall pωnijc`

The initial status of the lines is pre-defined as switched on.

Minimum switch-on and switch-off state of a line [h] «``eMinSwOnState``» «``eMinSwOffState``»

:math:`\sum_{n'=n+\nu-SON_{ijc}}^n son^p_{ωn'ijc} \leq     swt^p_{ωnijc} \quad \forall pωnijc`

:math:`\sum_{n'=n+\nu-SOF_{ijc}}^n sof^p_{ωn'ijc} \leq 1 - swt^p_{ωnijc} \quad \forall pωnijc`

Flow limit in transmission lines [p.u.] «``eNetCapacity1``» «``eNetCapacity2``»

:math:`- swt^p_{ωnijc} \leq \frac{f^p_{ωnijc}}{\overline{F}_{ijc}} \leq swt^p_{ωnijc} \quad \forall pωnijc`

DC Power flow for existing and non-switchable, and candidate and switchable AC-type lines (Kirchhoff's second law) [rad] «``eKirchhoff2ndLaw1``» «``eKirchhoff2ndLaw2``»

:math:`\frac{f^p_{ωnijc}}{\overline{F}'_{ijc}} - (\theta^p_{ωni} - \theta^p_{ωnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} = 0 \quad \forall pωnijc, ijc \in EL`

:math:`-1+swt^p_{ωnijc} \leq \frac{f^p_{ωnijc}}{\overline{F}'_{ijc}} - (\theta^p_{ωni} - \theta^p_{ωnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} \leq 1-swt^p_{ωnijc} \quad \forall pωnijc, ijc \in CL`

Half ohmic losses are linearly approximated as a function of the flow [GW] «``eLineLosses1``» «``eLineLosses2``»

:math:`- \frac{L_{ijc}}{2} f^p_{ωnijc} \leq l^p_{ωnijc} \geq \frac{L_{ijc}}{2} f^p_{ωnijc} \quad \forall pωnijc`

**Bounds on generation variables** [GW]

:math:`0 \leq gp^p_{ωng}  \leq \overline{GP}^p_{ωng}                             \quad \forall pωng`

:math:`0 \leq go^p_{ωne}  \leq \max(\overline{GP}^p_{ωne},\overline{GC}^p_{ωne}) \quad \forall pωne`

:math:`0 \leq gc^p_{ωne}  \leq \overline{GC}^p_{ωne}                             \quad \forall pωne`

:math:`0 \leq ur^p_{ωng}  \leq \overline{GP}^p_{ωng} - \underline{GP}^p_{ωng}    \quad \forall pωng`

:math:`0 \leq ur'^p_{ωne} \leq \overline{GC}^p_{ωne} - \underline{GC}^p_{ωne}    \quad \forall pωne`

:math:`0 \leq dr^p_{ωng}  \leq \overline{GP}^p_{ωng} - \underline{GP}^p_{ωng}    \quad \forall pωng`

:math:`0 \leq dr'^p_{ωne} \leq \overline{GC}^p_{ωne} - \underline{GC}^p_{ωne}    \quad \forall pωne`

:math:`0 \leq  p^p_{ωng}  \leq \overline{GP}^p_{ωng} - \underline{GP}^p_{ωng}    \quad \forall pωng`

:math:`0 \leq  c^p_{ωne}  \leq \overline{GC}^p_{ωne}                             \quad \forall pωne`

:math:`\undrline{I}^p_{ωne} \leq  i^p_{ωne}  \leq \overline{I}^p_{ωne}           \quad \forall pωne`

:math:`0 \leq  s^p_{ωne}                                                         \quad \forall pωne`

:math:`0 \leq ens^p_{ωni} \leq D^p_{ωni}                                         \quad \forall pωni`

**Bounds on network variables** [GW]

:math:`0 \leq l^p_{ωnijc} \leq \frac{L_{ijc}}{2} \overline{F}_{ijc}  \quad \forall pωnijc`

:math:`- \overline{F}_{ijc} \leq f^p_{ωnijc} \leq \overline{F}_{ijc} \quad \forall pωnijc, ijc \in EL`

Voltage angle of the reference node fixed to 0 for each scenario, period, and load level [rad]

:math:`\theta^p_{ωn,node_{ref}} = 0`
