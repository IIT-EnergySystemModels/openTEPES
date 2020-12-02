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
==============  ========================================================
:math:`ω`       Scenario
:math:`p`       Period
:math:`n`       Load level
:math:`\nu`     Time step. Duration of each load level (e.g., 2 h, 3 h)
:math:`g`       Generator (thermal or hydro unit or ESS)
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
:math:`EL, CL`  Set of existing and candidate lines
==============  ========================================================

Parameters
----------

They are written in capital letters.

==================  ====================================================  =======
**Demand**                                                       
------------------  ----------------------------------------------------  -------
:math:`D_{ωpni}`    Demand in each node                                   GW
:math:`DUR_n`       Duration of each load level                           h
:math:`CENS`        Cost of energy not served. Value of Lost Load (VoLL)  €/MWh
==================  ====================================================  =======

==================  ====================================================  =======
**Scenarios**                                                       
------------------  ----------------------------------------------------  -------
:math:`P_ω`         Probability of each scenario                          p.u.
==================  ====================================================  =======

=============================  ========================================================  ====
**Operating reserves**                                         
-----------------------------  --------------------------------------------------------  ----
:math:`URA, DRA`               Upward and downward reserve activation                    p.u.
:math:`UR_{ωpna}, DR_{ωpna}`   Upward and downward operating reserves for each area      GW
=============================  ========================================================  ====

=========================================  ============================================================================================  ============
**Generation system**   
-----------------------------------------  --------------------------------------------------------------------------------------------  ------------
:math:`CFG_g`                              Annualized fixed cost of a candidate generator                                                M€ 
:math:`\underline{GP}_g, \overline{GP}_g`  Minimum load and maximum output of a generator                                                GW
:math:`\overline{GC}_e`                    Maximum consumption of an ESS                                                                 GW
:math:`CF_g, CV_g`                         Fixed and variable cost of a generator. Variable cost includes fuel, O&M and emission cost    €/h, €/MWh
:math:`CV_e`                               Variable cost of an ESS when charging                                                         €/MWh
:math:`RU_t, RD_t`                         Ramp up and ramp down of a thermal unit                                                       MW/h
:math:`TU_t, TD_t`                         Minimum uptime and downtime of a thermal unit                                                 h
:math:`CSU_g, CSD_g`                       Startup and shutdown cost of a committed unit                                                 M€
:math:`\tau_e`                             Characteristic duration of the ESS (e.g., 24 h, 168 h, 672 h -for daily, weekly, monthly-)    h
:math:`EF_e`                               Efficiency of the pump/turbine cycle of a hydro power plant or charge/discharge of a battery  p.u.
:math:`I_e`                                Capacity of an ESS (e.g., hydro power plant)                                                  TWh
:math:`EI_{ωpng}`                          Energy inflows of an ESS (e.g., hydro power plant)                                            TWh
=========================================  ============================================================================================  ============

=========================================  =================================================================================================================  ====
**Transmission system**   
-----------------------------------------  -----------------------------------------------------------------------------------------------------------------  ----
:math:`CFT_{ijc}`                          Annualized fixed cost of a candidate transmission line                                                             M€    
:math:`\overline{F}_{ijc}`                 Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a transmission line      GW  
:math:`\overline{F}'_{ijc}`                Maximum flow used in the Kirchhoff's 2nd law constraint (e.g., disjunctive constraint for the candidate AC lines)  GW
:math:`L_{ijc}, X_{ijc}`                   Loss factor and reactance of a transmission line                                                                   p.u.
:math:`S_B`                                Base power                                                                                                         GW
=========================================  =================================================================================================================  ====

Variables
---------

They are written in lower letters.

===================  ==================  ===
**Demand**                             
-------------------  ------------------  ---
:math:`ens_{ωpni}`   Energy not served   GW
===================  ==================  ===

=======================================  ==========================================================================  =====
**Generation system**   
---------------------------------------  --------------------------------------------------------------------------  -----
:math:`icg_g`                            Candidate generator or ESS installed or not                                 {0,1}
:math:`gp_{ωpng}, gc_{ωpng}`             Generator output (discharge if an ESS) and consumption (charge if an ESS)   GW
:math:`p_{ωpng}`                         Generator output of the second block (i.e., above the minimum load)         GW
:math:`c_{ωpne}`                         Generator charge                                                            GW
:math:`ur_{ωpng}, dr_{ωpng}`             Upward and downward operating reserves of a committed unit                  GW
:math:`ur_{ωpne}, dr_{ωpne}`             Upward and downward operating reserves of an ESS                            GW
:math:`i_{ωpne}`                         ESS stored energy (inventory)                                               TWh
:math:`s_{ωpne}`                         ESS spilled energy                                                          TWh
:math:`uc_{ωpng}, su_{ωpng}, sd_{ωpng}`  Commitment, startup and shutdown of generation unit per load level          {0,1}
=======================================  ==========================================================================  =====

========================  ================================  =====
**Transmission system** 
------------------------  --------------------------------  -----
:math:`ict_{ijc}`         Candidate line installed or not   {0,1}
:math:`f_{ωpnijc}`        Flow through a line               GW
:math:`l_{ωpnijc}`        Half ohmic losses of a line       GW
:math:`θ_{ωpni}`          Voltage angle of a node           rad
========================  ================================  =====

Equations
---------

**Objective function**: minimization of total (investment and operation) cost for the scope of the model

Generation, storage and network investment cost [M€]

:math:`\sum_g {CFG_g icg_g} + \sum_{ijc}{CFT_{ijc} ict_{ijc}}`

Generation operation cost [M€]

:math:`\sum_{ωpng}{[P_ω DUR_n (CV_g gp_{ωpng} + CF_g uc_{ωpng}) + CSU_g su_{ωpng} + CSD_g sd_{ωpng}]}`

Variable consumption operation cost [M€]

:math:`\sum_{ωpne}{[P_ω DUR_n (CV_e gc_{ωpne}]}`

Reliability cost [M€]

:math:`\sum_{ωpni}{P_ωDUR_n CENS ens_{ωpni}}`

**Constraints**

Commitment decision bounded by investment decision for candidate committed units (all except the VRES units) [p.u.]

:math:`uc_{ωpng} \leq icg_g \quad \forall ωpng, g \in CG`

Output and consumption bounded by investment decision for candidate ESS [p.u.]

:math:`\frac{gp_{ωpne}}{\overline{GP}_e} \leq icg_e \quad \forall ωpne, e \in CE`

:math:`\frac{gc_{ωpne}}{\overline{GC}_e} \leq icg_e \quad \forall ωpne, e \in CE`

Balance of generation and demand at each node with ohmic losses [GW]

:math:`\sum_{g \in i} gp_{ωpng} - \sum_{e \in i} gc_{ωpne} + ens_{ωpni} = D_{ωpni} +`
:math:`+ \sum_{jc} l_{ωpnijc} + \sum_{jc} l_{ωpnjic} + \sum_{jc} f_{ωpnijc} - \sum_{jc} f_{ωpnjic} \quad \forall ωpni`

Upward and downward operating reserves provided by generators and ESS for each area [GW]

:math:`\sum_{g \in a} ur_{ωpng} + \sum_{e \in a} ur_{ωpne} = UR_{ωpna} \quad \forall ωpna`

:math:`\sum_{g \in a} dr_{ωpng} + \sum_{e \in a} dr_{ωpne} = DR_{ωpna} \quad \forall ωpna`

VRES units (i.e., those with linear variable cost equal to 0 and no storage capacity) do not contribute to the the operating reserves.

ESS energy inventory (only for load levels multiple of 24, 168 or 672 h depending on the ESS type) [TWh]

:math:`i_{ωp,n-\tau_e,e} + \sum_{n' = n+\nu-\tau_e}^{n} DUR_n (EI_{ωpne} - gp_{ωpne} + EF_e gc_{ωpne}) = i_{ωpne} + s_{ωpne} \quad \forall ωpne`

Maximum and minimum output of the second block of a committed unit (all except the VRES units) [p.u.]

* D.A. Tejada-Arango, S. Lumbreras, P. Sánchez-Martín, and A. Ramos "Which Unit-Commitment Formulation is Best? A Systematic Comparison" IEEE Transactions on Power Systems 35 (4): 2926-2936, Jul 2020 `10.1109/TPWRS.2019.2962024 <https://doi.org/10.1109/TPWRS.2019.2962024>`_

* C. Gentile, G. Morales-España, and A. Ramos "A tight MIP formulation of the unit commitment problem with start-up and shut-down constraints" EURO Journal on Computational Optimization 5 (1), 177-201, Mar 2017. `10.1007/s13675-016-0066-y <http://dx.doi.org/10.1007/s13675-016-0066-y>`_

* G. Morales-España, A. Ramos, and J. Garcia-Gonzalez "An MIP Formulation for Joint Market-Clearing of Energy and Reserves Based on Ramp Scheduling" IEEE Transactions on Power Systems 29 (1): 476-488, Jan 2014. `10.1109/TPWRS.2013.2259601 <http://dx.doi.org/10.1109/TPWRS.2013.2259601>`_

* G. Morales-España, J.M. Latorre, and A. Ramos "Tight and Compact MILP Formulation for the Thermal Unit Commitment Problem" IEEE Transactions on Power Systems 28 (4): 4897-4908, Nov 2013. `10.1109/TPWRS.2013.2251373 <http://dx.doi.org/10.1109/TPWRS.2013.2251373>`_

:math:`\frac{p_{ωpng} + URA \: ur_{ωpng} + ur_{ωpng}}{\overline{GP}_g - \underline{GP}_g} \leq uc_{ωpng} \quad \forall ωpng`

:math:`\frac{p_{ωpng} - DRA \: dr_{ωpng} - dr_{ωpng}}{\overline{GP}_g - \underline{GP}_g} \geq 0         \quad \forall ωpng`

Maximum and minimum charge of an ESS [p.u.]

:math:`\frac{c_{ωpne} + URA \: dr_{ωpne} + dr_{ωpne}}{\overline{GC}_e} \leq 1 \quad \forall ωpne`

:math:`\frac{c_{ωpne} - DRA \: ur_{ωpne} - ur_{ωpne}}{\overline{GC}_e} \geq 0 \quad \forall ωpne`

Incompatibility between charge and discharge of an ESS [p.u.]

:math:`\frac{p_{ωpne} + URA \: ur_{ωpne} + ur_{ωpng}}{\overline{GP}_e - \underline{GP}_e} + \frac{c_{ωpne} + URA \: dr_{ωpne} + dr_{ωpne}}{\overline{GC}_e} \leq 1 \quad \forall ωpne, e \in CE`

Total output of a committed unit (all except the VRES units) [GW]

:math:`\frac{gp_{ωpng}}{\underline{GP}_g} = uc_{ωpng} + \frac{p_{ωpng} + URA \: ur_{ωpng} - DRA \: dr_{ωpng}}{\underline{GP}_g} \quad \forall ωpng`

Total charge of an ESS unit [GW]

:math:`gc_{ωpne} = c_{ωpne} + URA \: dr_{ωpne} - DRA \: ur_{ωpne} \quad \forall ωpne, e \in CE`

Logical relation between commitment, startup and shutdown status of committed unit (all except the VRES units) [p.u.]

:math:`uc_{ωpng} - uc_{ωp,n-\nu,g} = su_{ωpng} - sd_{ωpng} \quad \forall ωpng`

Initial commitment of the units is determined by the model based on the merit order loading, including the VRES and ESS units.

Maximum ramp up and ramp down for the second block of a thermal unit [p.u.]

- P. Damcı-Kurt, S. Küçükyavuz, D. Rajan, and A. Atamtürk, “A polyhedral study of production ramping,” Math. Program., vol. 158, no. 1–2, pp. 175–205, Jul. 2016. `10.1007/s10107-015-0919-9 <https://doi.org/10.1007/s10107-015-0919-9>`_

:math:`\frac{- p_{ωp,n-\nu,t} - URA \: ur_{ωp,n-\nu,t} + p_{ωpnt} + URA \: ur_{ωpnt} + ur_{ωpnt}}{DUR_n RU_t} \leq   uc_{ωpnt}       - su_{ωpnt} \quad \forall ωpnt`

:math:`\frac{- p_{ωp,n-\nu,t} + DRA \: dr_{ωp,n-\nu,t} + p_{ωpnt} - DRA \: dr_{ωpnt} - dr_{ωpnt}}{DUR_n RD_t} \geq - uc_{ωp,n-\nu,t} + sd_{ωpnt} \quad \forall ωpnt`

Minimum up time and down time of thermal unit [h]

- D. Rajan and S. Takriti, “Minimum up/down polytopes of the unit commitment problem with start-up costs,” IBM, New York, Technical Report RC23628, 2005. https://pdfs.semanticscholar.org/b886/42e36b414d5929fed48593d0ac46ae3e2070.pdf

:math:`\sum_{n'=n+\nu-TU_t}^n su_{ωpn't} \leq     uc_{ωpnt} \quad \forall ωpnt`

:math:`\sum_{n'=n+\nu-TD_t}^n sd_{ωpn't} \leq 1 - uc_{ωpnt} \quad \forall ωpnt`

Transfer capacity in candidate transmission lines [p.u.]

:math:`- ict_{ijc} \leq \frac{f_{ωpnijc}}{\overline{F}_{ijc}} \leq ict_{ijc} \quad \forall ωpnijc, ijc \in CL`

DC Power flow for existing and candidate AC-type lines (Kirchhoff's second law) [rad]

:math:`\frac{f_{ωpnijc}}{\overline{F}'_{ijc}} = (\theta_{ωpni} - \theta_{ωpnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} \quad \forall ωpnijc, ijc \in EL`

:math:`-1+ict_{ijc} \leq \frac{f_{ωpnijc}}{\overline{F}'_{ijc}} - (\theta_{ωpni} - \theta_{ωpnj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} \leq 1-ict_{ijc} \quad \forall ωpnijc, ijc \in CL`

Half ohmic losses are linearly approximated as a function of the flow [GW]

:math:`- \frac{L_{ijc}}{2} f_{ωpnijc} \leq l_{ωpnijc} \geq \frac{L_{ijc}}{2} f_{ωpnijc} \quad \forall ωpnijc`

Bounds on generation variables [GW]

:math:`0 \leq gp_{ωpng} \leq \overline{GP}_g                    \quad \forall ωpng`

:math:`0 \leq qc_{ωpne} \leq \overline{GC}_e                    \quad \forall ωpne`

:math:`0 \leq ur_{ωpng} \leq \overline{CP}_g - \underline{GP}_g \quad \forall ωpng`

:math:`0 \leq dr_{ωpng} \leq \overline{CP}_g - \underline{GP}_g \quad \forall ωpng`

:math:`0 \leq  p_{ωpng} \leq \overline{GP}_g - \underline{GP}_g \quad \forall ωpng`

:math:`0 \leq  c_{ωpne} \leq \overline{GC}_e                    \quad \forall ωpne`

:math:`0 \leq  i_{ωpne} \leq I_e                                \quad \forall ωpne`

:math:`0 \leq  s_{ωpne}                                         \quad \forall ωpne`

:math:`0 \leq ens_{ωpni} \leq D_{ωpni}                          \quad \forall ωpni`

Bounds on network variables [GW]

:math:`0 \leq l_{ωpnijc} \leq \frac{L_{ijc}}{2} \overline{F}_{ijc} \quad \forall ωpnijc`

:math:`- \overline{F}_{ijc} \leq f_{ωpnijc} \leq \overline{F}_{ijc} \quad \forall ωpnijc, ijc \in EL`

Voltage angle of the reference node fixed to 0 for each scenario, period, and load level [rad]

:math:`\theta_{ωpn,node_{ref}} = 0` 