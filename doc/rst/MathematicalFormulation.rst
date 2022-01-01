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
:math:`ω`       Scenario
:math:`p`       Period
:math:`n`       Load level
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

They are written in capital letters.

==================  ====================================================  =======
**Demand**                                                       
------------------  ----------------------------------------------------  -------
:math:`D^ω_{pni}`   Demand in each node                                   GW
:math:`PD_a`        Peak demand in each area                              GW
:math:`DUR_n`       Duration of each load level                           h
:math:`CENS`        Cost of energy not served. Value of Lost Load (VoLL)  €/MWh
==================  ====================================================  =======

==================  ====================================================  =======
**Scenarios**                                                       
------------------  ----------------------------------------------------  -------
:math:`P^ω`         Probability of each scenario                          p.u.
==================  ====================================================  =======

==========================================  ==================================================================  ====
**Operating reserves**                                         
------------------------------------------  ------------------------------------------------------------------  ----
:math:`URA, DRA`                            Upward and downward reserve activation                              p.u.
:math:`\underline{DtUR}, \overline{DtUR}`   Minimum and maximum ratios downward to upward operating reserves    p.u.
:math:`UR^ω_{pna}, DR^ω_{pna}`              Upward and downward operating reserves for each area                GW
==========================================  ==================================================================  ====

==============================  ========================================================  ====
**Adequacy system reserve margin**
------------------------------  --------------------------------------------------------  ----
:math:`RM_a`                    Adequacy system reserve margin for each area              p.u.
==============================  ========================================================  ====

==============================  ========================================================  ====
**System inertia**
------------------------------  --------------------------------------------------------  ----
:math:`SI^ω_{pna}`              System inertia for each area                              s
==============================  ========================================================  ====

=====================================================  ========================================================================================================  ============
**Generation system**   
-----------------------------------------------------  --------------------------------------------------------------------------------------------------------  ------------
:math:`CFG_g`                                          Annualized fixed cost of a candidate generator                                                            M€
:math:`A_g`                                            Availability of each generator for adequacy reserve margin                                                p.u.
:math:`\underline{GP}_g, \overline{GP}_g`              Rated minimum load and maximum output of a generator                                                      GW
:math:`\underline{GP}^w_{png}, \overline{GP}^w_{png}`  Minimum load and maximum output of a generator                                                            GW
:math:`\underline{GC}^w_{pne}, \overline{GC}^w_{pne}`  Minimum and maximum consumption of an ESS                                                                 GW
:math:`CF_g, CV_g`                                     Fixed (no load) and variable cost of a generator. Variable cost includes fuel, O&M and emission cost      €/h, €/MWh
:math:`CV_e`                                           Variable cost of an ESS when charging                                                                     €/MWh
:math:`RU_g, RD_g`                                     Ramp up/down of a non-renewable unit or maximum discharge/charge rate for ESS discharge/charge            MW/h
:math:`TU_t, TD_t`                                     Minimum uptime and downtime of a thermal unit                                                             h
:math:`CSU_g, CSD_g`                                   Startup and shutdown cost of a committed unit                                                             M€
:math:`\tau_e`                                         Storage cycle of the ESS (e.g., 1, 24, 168 h -for daily, weekly, monthly-)                                h
:math:`\rho_e`                                         Outflow cycle of the ESS (e.g., 1, 24, 168 h -for hourly, daily, weekly, monthly, yearly-)                h
:math:`GI_g`                                           Generator inertia                                                                                         s
:math:`EF_e`                                           Round-trip efficiency of the pump/turbine cycle of a hydro power plant or charge/discharge of a battery   p.u.
:math:`I^w_{pne}`                                      Capacity of an ESS (e.g., hydro power plant)                                                              GWh
:math:`EI^ω_{png}`                                     Energy inflows of an ESS (e.g., hydro power plant)                                                        GWh
:math:`EO^ω_{png}`                                     Energy outflows of an ESS (e.g., H2, EV, hydro power plant)                                               GWh
=====================================================  ========================================================================================================  ============

=========================================  =================================================================================================================  ====
**Transmission system**   
-----------------------------------------  -----------------------------------------------------------------------------------------------------------------  ----
:math:`CFT_{ijc}`                          Annualized fixed cost of a candidate transmission line                                                             M€    
:math:`\overline{F}_{ijc}`                 Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a transmission line      GW  
:math:`\overline{F}'_{ijc}`                Maximum flow used in the Kirchhoff's 2nd law constraint (e.g., disjunctive constraint for the candidate AC lines)  GW
:math:`L_{ijc}, X_{ijc}`                   Loss factor and reactance of a transmission line                                                                   p.u.
:math:`SON_{ijc}, SOF_{ijc}`               Minimum switch-on and switch-off state of a line                                                                   h
:math:`S_B`                                Base power                                                                                                         GW
=========================================  =================================================================================================================  ====

The net transfer capacity of a transmission line can be different in each direction. However, here it is presented as equal for simplicity.

Variables
---------

They are written in lower letters.

===================  ==================  ===
**Demand**                             
-------------------  ------------------  ---
:math:`ens^ω_{pni}`   Energy not served   GW
===================  ==================  ===

==========================================  ==========================================================================  =====
**Generation system**   
------------------------------------------  --------------------------------------------------------------------------  -----
:math:`icg_g`                               Candidate generator or ESS installed or not                                 {0,1}
:math:`gp^ω_{png}, gc^ω_{png}`              Generator output (discharge if an ESS) and consumption (charge if an ESS)   GW
:math:`go^ω_{png}`                          Generator outflows of an ESS                                                GW
:math:`p^ω_{png}`                           Generator output of the second block (i.e., above the minimum load)         GW
:math:`c^ω_{pne}`                           Generator charge                                                            GW
:math:`ur^ω_{png}, dr^ω_{png}`              Upward and downward operating reserves of a non-renewable generating unit   GW
:math:`ur'^ω_{pne}, dr'^ω_{pne}`            Upward and downward operating reserves of an ESS as a consumption unit      GW
:math:`i^ω_{pne}`                           ESS stored energy (inventory)                                               GWh
:math:`s^ω_{pne}`                           ESS spilled energy                                                          GWh
:math:`uc^ω_{png}, su^ω_{png}, sd^ω_{png}`  Commitment, startup and shutdown of generation unit per load level          {0,1}
:math:`uc'_g`                               Maximum commitment of a generation unit for all the load levels             {0,1}
==========================================  ==========================================================================  =====

======================================================  =================================================================  =====
**Transmission system** 
------------------------------------------------------  -----------------------------------------------------------------  -----
:math:`ict_{ijc}`                                       Candidate line installed or not                                    {0,1}
:math:`swt^ω_{pnijc}, son^ω_{pnijc}, sof^ω_{pnijc}`     Switching state, switch-on and switch-off of a line                {0,1}
:math:`f^ω_{pnijc}`                                     Flow through a line                                                GW
:math:`l^ω_{pnijc}`                                     Half ohmic losses of a line                                        GW
:math:`θ^ω_{pni}`                                       Voltage angle of a node                                            rad
======================================================  =================================================================  =====

Equations
---------

The names between parenthesis correspond to the names of the constraints in the code.

**Objective function**: minimization of total (investment and operation) cost for the scope of the model

Generation, storage and network investment cost [M€] (``eTotalFCost``)

:math:`\sum_g {CFG_g icg_g} + \sum_{ijc}{CFT_{ijc} ict_{ijc}} +`

Generation operation cost [M€] (``eTotalGCost``) (``eTotalECost``)

:math:`\sum_{ωpng}{[P^ω DUR_n (CV_g gp^ω_{png} + CF_g uc^ω_{png}) + CSU_g su^ω_{png} + CSD_g sd^ω_{png}]} +`

Variable consumption operation cost [M€] (``eTotalCCost``)

:math:`\sum_{ωpne}{P^ω DUR_n CV_e gc^ω_{pne}} +`

Reliability cost [M€] (``eTotalRCost``)

:math:`\sum_{ωpni}{P^ω DUR_n CENS ens^ω_{pni}}`

**Constraints**

**Generation operation**

Commitment decision bounded by investment decision for candidate committed units (all except the VRES units) [p.u.] (``eInstalGenComm``)

:math:`uc^ω_{png} \leq icg_g \quad \forall ωpng, g \in CG`

Output and consumption bounded by investment decision for candidate ESS [p.u.] (``eInstalGenCap``) (``eInstalConESS``)

:math:`\frac{gp^ω_{pne}}{\overline{GP}^w_{pne}} \leq icg_e \quad \forall ωpne, e \in CE`

:math:`\frac{gc^ω_{pne}}{\overline{GP}^w_{pne}} \leq icg_e \quad \forall ωpne, e \in CE`

Adequacy system reserve margin [p.u.] (``eAdequacyReserveMargin``)

:math:`\sum_{g \in a, EG} \overline{GP}_g A_g + \sum_{g \in a, CG} icg_g  \overline{GP}_g A_g \geq PD_a RM_a \quad \forall a`

Balance of generation and demand at each node with ohmic losses [GW] (``eBalance``)

:math:`\sum_{g \in i} gp^ω_{png} - \sum_{e \in i} gc^ω_{pne} + ens^ω_{pni} = D^ω_{pni} + \sum_{jc} l^ω_{pnijc} + \sum_{jc} l^ω_{pnjic} + \sum_{jc} f^ω_{pnijc} - \sum_{jc} f^ω_{pnjic} \quad \forall ωpni`

System inertia for each area [s] (``eSystemInertia``)

:math:`\sum_{g \in a} GI_g uc^ω_{png} \geq SI^ω_{pna} \quad \forall ωpna`

Upward and downward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] (``eOperReserveUp``) (``eOperReserveDw``)

:math:`\sum_{g \in a} ur^ω_{png} + \sum_{e \in a} ur'^ω_{pne} = UR^ω_{pna} \quad \forall ωpna`

:math:`\sum_{g \in a} dr^ω_{png} + \sum_{e \in a} dr'^ω_{pne} = DR^ω_{pna} \quad \forall ωpna`

Ratio between downward and upward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] (``eReserveMinRatioDwUp``) (``eReserveMaxRatioDwUp``) (``eRsrvMinRatioDwUpESS``) (``eRsrvMaxRatioDwUpESS``)

:math:`\underline{DtUR} ur^ω_{png} \leq dr^ω_{png} \leq \overline{DtUR} ur^ω_{png} \quad \forall ωpng`

:math:`\underline{DtUR} ur'^ω_{pne} \leq dr'^ω_{pne} \leq \overline{DtUR} ur'^ω_{pne} \quad \forall ωpne`

VRES units (i.e., those with linear variable cost equal to 0 and no storage capacity) do not contribute to the the operating reserves.

Operating reserves from ESS can only be provided if enough energy is available for producing [GW] (``eReserveUpIfEnergy``) (``eReserveDwIfEnergy``)

:math:`ur^ω_{pne} \leq \frac{      i^ω_{pne}}{DUR_n} \quad \forall ωpne`

:math:`dr^ω_{pne} \leq \frac{I^w_{pne} - i^ω_{pne}}{DUR_n} \quad \forall ωpne`

or for storing [GW] (``eESSReserveUpIfEnergy``) (``eESSReserveDwIfEnergy``)

:math:`ur'^ω_{pne} \leq \frac{I^w_{pne} - i^ω_{pne}}{DUR_n} \quad \forall ωpne`

:math:`dr'^ω_{pne} \leq \frac{      i^ω_{pne}}{DUR_n} \quad \forall ωpne`

ESS energy inventory (only for load levels multiple of 1, 24, 168 h depending on the ESS storage type) [GWh] (``eESSInventory``)

:math:`i^ω_{p,n-\frac{\tau_e}{\nu},e} + \sum_{n' = n-\frac{\tau_e}{\nu}}^{n} DUR_n' (EI^ω_{pn'e} - go^ω_{pn'e} - gp^ω_{pn'e} + EF_e gc^ω_{pn'e}) = i^ω_{pne} + s^ω_{pne} \quad \forall ωpne`

ESS outflows (only for load levels multiple of 1, 24, 168, 672, and 8736 h depending on the ESS outflow cycle) must be satisfied [GWh] (``eEnergyOutflows``)

:math:`\sum_{n' = n-\frac{\tau_e}{\rho_e}}^{n} go^ω_{pn'e} = EO^ω_{pne} \quad \forall ωpne`

Maximum and minimum output of the second block of a committed unit (all except the VRES units) [p.u.] (``eMaxOutput2ndBlock``) (``eMinOutput2ndBlock``)

* D.A. Tejada-Arango, S. Lumbreras, P. Sánchez-Martín, and A. Ramos "Which Unit-Commitment Formulation is Best? A Systematic Comparison" IEEE Transactions on Power Systems 35 (4): 2926-2936, Jul 2020 `10.1109/TPWRS.2019.2962024 <https://doi.org/10.1109/TPWRS.2019.2962024>`_

* C. Gentile, G. Morales-España, and A. Ramos "A tight MIP formulation of the unit commitment problem with start-up and shut-down constraints" EURO Journal on Computational Optimization 5 (1), 177-201, Mar 2017. `10.1007/s13675-016-0066-y <http://dx.doi.org/10.1007/s13675-016-0066-y>`_

* G. Morales-España, A. Ramos, and J. Garcia-Gonzalez "An MIP Formulation for Joint Market-Clearing of Energy and Reserves Based on Ramp Scheduling" IEEE Transactions on Power Systems 29 (1): 476-488, Jan 2014. `10.1109/TPWRS.2013.2259601 <http://dx.doi.org/10.1109/TPWRS.2013.2259601>`_

* G. Morales-España, J.M. Latorre, and A. Ramos "Tight and Compact MILP Formulation for the Thermal Unit Commitment Problem" IEEE Transactions on Power Systems 28 (4): 4897-4908, Nov 2013. `10.1109/TPWRS.2013.2251373 <http://dx.doi.org/10.1109/TPWRS.2013.2251373>`_

:math:`\frac{p^ω_{png} + ur^ω_{png}}{\overline{GP}^w_{png} - \underline{GP}^w_{png}} \leq uc^ω_{png} \quad \forall ωpng`

:math:`\frac{p^ω_{png} - dr^ω_{png}}{\overline{GP}^w_{png} - \underline{GP}^w_{png}} \geq 0          \quad \forall ωpng`

Maximum and minimum charge of an ESS [p.u.] (``eMaxCharge``) (``eMinCharge``)

:math:`\frac{c^ω_{pne} + dr'^ω_{pne}}{\overline{GC}^w_{pne} - \underline{GC}^w_{pne}} \leq 1 \quad \forall ωpne`

:math:`\frac{c^ω_{pne} - ur'^ω_{pne}}{\overline{GC}^w_{pne} - \underline{GC}^w_{pne}} \geq 0 \quad \forall ωpne`

Incompatibility between charge and discharge of an ESS [p.u.] (``eChargeDischarge``)

:math:`\frac{p^ω_{pne} + URA \: ur'^ω_{pne}}{\overline{GP}^w_{pne} - \underline{GP}^w_{pne}} + \frac{c^ω_{pne} + DRA \: dr'^ω_{pne}}{\overline{GC}^w_{pne} - \underline{GC}^w_{pne}} \leq 1 \quad \forall ωpne, e \in CE`

Total output of a committed unit (all except the VRES units) [GW] (``eTotalOutput``)

:math:`\frac{gp^ω_{png}}{\underline{GP}^w_{png}} = uc^ω_{png} + \frac{p^ω_{png} + URA \: ur^ω_{png} - DRA \: dr^ω_{png}}{\underline{GP}^w_{png}} \quad \forall ωpng`

Total charge of an ESS [GW] (``eESSTotalCharge``)

:math:`\frac{gc^ω_{pne}}{\underline{GC}^w_{pne}} = 1 + \frac{c^ω_{pne} + URA \: ur'^ω_{pne} - DRA \: dr'^ω_{pne}}{\underline{GC}^w_{pne}} \quad \forall ωpne, e \in CE`

Logical relation between commitment, startup and shutdown status of a committed unit (all except the VRES units) [p.u.] (``eUCStrShut``)

:math:`uc^ω_{png} - uc^ω_{p,n-\nu,g} = su^ω_{png} - sd^ω_{png} \quad \forall ωpng`

Maximum commitment of a committable unit (all except the VRES units) [p.u.] (``eMaxCommitment``)

:math:`uc^ω_{png} \leq uc'_g \quad \forall ωpng`

Maximum commitment of any unit [p.u.] (``eMaxCommitGen``)

:math:`\sum_{ωpn} \frac{gp^ω_{png}}{\overline{GP}_g} \leq uc'_g \quad \forall ωpng`

Mutually exclusive :math:`g` and :math:`g'` units (e.g., thermal, ESS, VRES units) [p.u.] (``eExclusiveGens``)

:math:`uc'_g + uc'_{g'} \leq 1 \quad \forall g, g'`

Initial commitment of the units is determined by the model based on the merit order loading, including the VRES and ESS units.

Maximum ramp up and ramp down for the second block of a non-renewable (thermal, hydro) unit [p.u.] (``eRampUp``) (``eRampDw``)

- P. Damcı-Kurt, S. Küçükyavuz, D. Rajan, and A. Atamtürk, “A polyhedral study of production ramping,” Math. Program., vol. 158, no. 1–2, pp. 175–205, Jul. 2016. `10.1007/s10107-015-0919-9 <https://doi.org/10.1007/s10107-015-0919-9>`_

:math:`\frac{- p^ω_{p,n-\nu,g} - dr^ω_{p,n-\nu,g} + p^ω_{png} + ur^ω_{png}}{DUR_n RU_g} \leq   uc^ω_{png}       - su^ω_{png} \quad \forall ωpng`

:math:`\frac{- p^ω_{p,n-\nu,g} + ur^ω_{p,n-\nu,g} + p^ω_{png} - dr^ω_{png}}{DUR_n RD_g} \geq - uc^ω_{p,n-\nu,g} + sd^ω_{png} \quad \forall ωpng`

Maximum ramp down and ramp up for the charge of an ESS [p.u.] (``eRampUpCharge``) (``eRampDwCharge``)

:math:`\frac{- c^ω_{p,n-\nu,e} - ur^ω_{p,n-\nu,e} + c^ω_{pne} + dr^ω_{pne}}{DUR_n RD_e} \leq   1 \quad \forall ωpne`

:math:`\frac{- c^ω_{p,n-\nu,e} + dr^ω_{p,n-\nu,e} + c^ω_{pne} - ur^ω_{pne}}{DUR_n RU_e} \geq - 1 \quad \forall ωpne`

Minimum up time and down time of thermal unit [h] (``eMinUpTime``) (``eMinDownTime``)

- D. Rajan and S. Takriti, “Minimum up/down polytopes of the unit commitment problem with start-up costs,” IBM, New York, Technical Report RC23628, 2005. https://pdfs.semanticscholar.org/b886/42e36b414d5929fed48593d0ac46ae3e2070.pdf

:math:`\sum_{n'=n+\nu-TU_t}^n su^ω_{pn't} \leq     uc^ω_{pnt} \quad \forall ωpnt`

:math:`\sum_{n'=n+\nu-TD_t}^n sd^ω_{pn't} \leq 1 - uc^ω_{pnt} \quad \forall ωpnt`

**Network operation**

Logical relation between transmission investment and switching {0,1} (``eLineStateCand``)

:math:`swt^{ω}_{pnijc} \leq ict_{ijc} \quad \forall ωpnijc, ijc \in CL`

Logical relation between switching state, switch-on and switch-off status of a line [p.u.] (``eSWOnOff``)

:math:`swt^ω_{pnijc} - swt^ω_{p,n-\nu,ijc} = son^ω_{pnijc} - sof^ω_{pnijc} \quad \forall ωpnijc`

The initial status of the lines is pre-defined as switched on.

Minimum switch-on and switch-off state of a line [h] (``eMinSwOnState``) (``eMinSwOffState``)

:math:`\sum_{n'=n+\nu-SON_{ijc}}^n son^ω_{pn'ijc} \leq     swt^ω_{pnijc} \quad \forall ωpnijc`

:math:`\sum_{n'=n+\nu-SOF_{ijc}}^n sof^ω_{pn'ijc} \leq 1 - swt^ω_{pnijc} \quad \forall ωpnijc`

Flow limit in transmission lines [p.u.] (``eNetCapacity1``) (``eNetCapacity2``)

:math:`- swt^{ω}_{pnijc} \leq \frac{f^ω_{pnijc}}{\overline{F}_{ijc}} \leq swt^{ω}_{pnijc} \quad \forall ωpnijc`

DC Power flow for existing and non-switchable, and candidate and switchable AC-type lines (Kirchhoff's second law) [rad] (``eKirchhoff2ndLaw1``) (``eKirchhoff2ndLaw2``)

:math:`\frac{f^ω_{pnijc}}{\overline{F}'_{ijc}} - (\theta^ω_{pni} - \theta^ω_{pnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} = 0 \quad \forall ωpnijc, ijc \in EL`

:math:`-1+swt^{ω}_{pnijc} \leq \frac{f^ω_{pnijc}}{\overline{F}'_{ijc}} - (\theta^ω_{pni} - \theta^ω_{pnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} \leq 1-swt^{ω}_{pnijc} \quad \forall ωpnijc, ijc \in CL`

Half ohmic losses are linearly approximated as a function of the flow [GW] (``eLineLosses1``) (``eLineLosses2``)

:math:`- \frac{L_{ijc}}{2} f^ω_{pnijc} \leq l^ω_{pnijc} \geq \frac{L_{ijc}}{2} f^ω_{pnijc} \quad \forall ωpnijc`

**Bounds on generation variables** [GW]

:math:`0 \leq gp^ω_{png} \leq \overline{GP}^w_{png}                           \quad \forall ωpng`

:math:`0 \leq qc^ω_{pne} \leq \overline{GP}^w_{pne}                           \quad \forall ωpne`

:math:`0 \leq ur^ω_{png} \leq \overline{GP}^w_{png} - \underline{GP}^w_{png}  \quad \forall ωpng`

:math:`0 \leq ur'^ω_{pne} \leq \overline{GC}^w_{pne} - \underline{GC}^w_{pne} \quad \forall ωpne`

:math:`0 \leq dr^ω_{png} \leq \overline{GP}^w_{png} - \underline{GP}^w_{png}  \quad \forall ωpng`

:math:`0 \leq dr'^ω_{pne} \leq \overline{GC}^w_{pne} - \underline{GC}^w_{pne} \quad \forall ωpne`

:math:`0 \leq  p^ω_{png} \leq \overline{GP}^w_{png} - \underline{GP}^w_{png}  \quad \forall ωpng`

:math:`0 \leq  c^ω_{pne} \leq \overline{GP}^w_{pne}                           \quad \forall ωpne`

:math:`0 \leq  i^ω_{pne} \leq I^w_{pne}                                       \quad \forall ωpne`

:math:`0 \leq  s^ω_{pne}                                                      \quad \forall ωpne`

:math:`0 \leq ens^ω_{pni} \leq D^ω_{pni}                                      \quad \forall ωpni`

**Bounds on network variables** [GW]

:math:`0 \leq l^ω_{pnijc} \leq \frac{L_{ijc}}{2} \overline{F}_{ijc}  \quad \forall ωpnijc`

:math:`- \overline{F}_{ijc} \leq f^ω_{pnijc} \leq \overline{F}_{ijc} \quad \forall ωpnijc, ijc \in EL`

Voltage angle of the reference node fixed to 0 for each scenario, period, and load level [rad]

:math:`\theta^ω_{pn,node_{ref}} = 0` 