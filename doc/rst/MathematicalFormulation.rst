.. openTEPES documentation master file, created by Andres Ramos

Mathematical Formulation
========================
Here we present the mathematical formulation of the optimization problem solved by the **openTEPES** model. See also some TEP-related publications:

* E.F. Álvarez, J.C. López, L. Olmos, A. Ramos "An Optimal Expansion Planning of Power Systems Considering Cycle-Based AC Optimal Power Flow" Sustainable Energy, Grids and Networks, May 2024. `10.1016/j.segan.2024.101413 <https://doi.org/10.1016/j.segan.2024.101413>`_

* E.F. Álvarez, L. Olmos, A. Ramos, K. Antoniadou-Plytaria, D. Steen, and L.A. Tuan “Values and Impacts of Incorporating Local Flexibility Services in Transmission Expansion Planning” Electric Power Systems Research 212, July 2022. `10.1016/j.epsr.2022.108480 <https://doi.org/10.1016/j.epsr.2022.108480>`_

* A. Ramos, E. Quispe, S. Lumbreras "`OpenTEPES: Open-source Transmission and Generation Expansion Planning <https://www.sciencedirect.com/science/article/pii/S235271102200053X/pdfft?md5=ece8d3328c853a4795eda29acd2ad140&pid=1-s2.0-S235271102200053X-main.pdf>`_"
  *SoftwareX* 18: June 2022. `10.1016/j.softx.2022.101070 <https://doi.org/10.1016/j.softx.2022.101070>`_

* S. Lumbreras, H. Abdi, A. Ramos, and M. Moradi "Introduction: The Key Role of the Transmission Network" in the book S. Lumbreras, H. Abdi, A. Ramos (eds.) "Transmission Expansion Planning: The Network Challenges of the Energy Transition" Springer, 2020 ISBN 9783030494278 `10.1007/978-3-030-49428-5_1 <https://link.springer.com/chapter/10.1007/978-3-030-49428-5_1>`_

* S. Lumbreras, F. Banez-Chicharro, A. Ramos "Optimal Transmission Expansion Planning in Real-Sized Power Systems with High Renewable Penetration" Electric Power Systems Research 49, 76-88, Aug 2017 `10.1016/j.epsr.2017.04.020 <https://doi.org/10.1016/j.epsr.2017.04.020>`_

* S. Lumbreras, A. Ramos "The new challenges to transmission expansion planning. Survey of recent practice and literature review" Electric Power Systems Research 134: 19-29, May 2016 `10.1016/j.epsr.2015.10.013 <https://doi.org/10.1016/j.epsr.2015.10.013>`_

* Q. Ploussard, L. Olmos and A. Ramos "A search space reduction method for transmission expansion planning using an iterative refinement of the DC Load Flow model" IEEE Transactions on Power Systems 35 (1): 152-162, Jan 2020 `10.1109/TPWRS.2019.2930719 <https://doi.org/10.1109/TPWRS.2019.2930719>`_

* Q. Ploussard, L. Olmos and A. Ramos "An efficient network reduction method for transmission expansion planning using multicut problem and Kron" reduction IEEE Transactions on Power Systems 33 (6): 6120-6130, Nov 2018 `10.1109/TPWRS.2018.2842301 <https://doi.org/10.1109/TPWRS.2018.2842301>`_

* Q. Ploussard, L. Olmos and A. Ramos "An operational state aggregation technique for transmission expansion planning based on line benefits" IEEE Transactions on Power Systems 32 (4): 2744-2755, Oct 2017 `10.1109/TPWRS.2016.2614368 <https://doi.org/10.1109/TPWRS.2016.2614368>`_

Indices
-------
=======================  ===============================================================================================
:math:`p`                Period (e.g., year)
:math:`\omega`           Scenario
:math:`n`                Load level (e.g., hour)
:math:`g`                Generator (thermal or hydro unit or energy storage system)
:math:`t`                Thermal unit
:math:`e`                Energy Storage System (ESS)
:math:`h`                Hydropower or pumped-storage hydro plant (associated to a reservoir modeled in water units)
:math:`e',e''`           Reservoir (natural water inflows in m\ :sup:`3`/s and volume in hm\ :sup:`3`)
:math:`h \in up(e')`     Hydro or pumped-storage hydropower plant :math:`h` upstream of reservoir :math:`e'`
:math:`h \in dw(e')`     Hydro or pumped-storage hydropower plant :math:`h` downstream of reservoir :math:`e'`
:math:`e'' \in up(e')`   Reservoir :math:`e''` upstream of reservoir :math:`e'`
:math:`i, j`             Node
:math:`z`                Zone. Each node belongs to a zone :math:`i \in z`
:math:`a`                Area. Each zone belongs to an area :math:`z \in a`
:math:`r`                Region. Each area belongs to a region :math:`a \in r`
:math:`c`                Circuit
:math:`ijc`              Line (initial node, final node, circuit)
:math:`cy`               Electricity network cycle
:math:`CY`               Electricity network cycle basis
:math:`CLC`              AC candidate electricity transmission lines in a certain cycle
:math:`EG, CG`           Set of existing and candidate generators
:math:`EB, CB`           Set of existing and candidate fuel heaters
:math:`EE, CE`           Set of existing and candidate ESS
:math:`ER, CR`           Set of existing and candidate reservoirs
:math:`EL, CL`           Set of existing and non-switchable, and candidate and switchable electric transmission lines
:math:`EP, CP`           Set of existing and candidate pipelines
=======================  ===============================================================================================

Parameters
----------

They are written in **uppercase** letters.

==================  =======================================================  =======
**General**
------------------------------------------------------------------------------------
:math:`T`           Base period (year)                                       year
:math:`\nu`         Time step. Duration of the load levels (e.g., 2 h, 3 h)
:math:`\delta`      Annual discount rate                                     p.u.
:math:`WG^p`        Period (year) weight                                     p.u.
:math:`DF^p`        Discount factor for each period (year)                   p.u.
==================  =======================================================  =======

========================  ====================================================  =======
**Electricity demand**
---------------------------------------------------------------------------------------
:math:`D^p_{\omega ni}`   Electricity demand in each node                       GW
:math:`PD_{pa}`           Peak demand in each area                              GW
:math:`DUR^p_{\omega n}`             Duration of each load level                           h
:math:`CENS`              Cost of energy not served. Value of Lost Load (VoLL)  €/MWh
========================  ====================================================  =======

========================  ====================================================  =======
**Hydrogen demand**
---------------------------------------------------------------------------------------
:math:`DH^p_{\omega ni}`  Hydrogen demand in each node                          tH2
:math:`CHNS`              Cost of hydrogen not served                           €/tH2
========================  ====================================================  =======

=========================  ====================================================  =======
**Heat demand**
----------------------------------------------------------------------------------------
:math:`DHt^p_{\omega ni}`  Heat demand in each node                              GW
:math:`CHtNS`              Cost of heat not served                               €/MWh
=========================  ====================================================  =======

===========================  ====================================================  =======
**Scenarios**
------------------------------------------------------------------------------------------
:math:`P^p_{\omega}`         Probability of each scenario in each period           p.u.
===========================  ====================================================  =======

==========================================  ==================================================================  ====
**Operating reserves**
--------------------------------------------------------------------------------------------------------------------
:math:`URA, DRA`                            Upward and downward reserve activation                              p.u.
:math:`\underline{DtUR}, \overline{DtUR}`   Minimum and maximum ratios downward to upward operating reserves    p.u.
:math:`UR^p_{\omega na}, DR^p_{\omega na}`  Upward and downward operating reserves for each area                GW
==========================================  ==================================================================  ====

==================================  ================================================================  ====
**Adequacy system reserve margin**
----------------------------------------------------------------------------------------------------------
:math:`RM_{pa}`                     Minimum adequacy system reserve margin for each period and area   p.u.
==================================  ================================================================  ====

==================================  ================================================================  =====
**Maximum CO2 emission**
-----------------------------------------------------------------------------------------------------------
:math:`EL_{pa}`                     Maximum CO2 emission for each period, scenario, and area          MtCO2
==================================  ================================================================  =====

==================================  ================================================================  =====
**Minimum RES energy**
-----------------------------------------------------------------------------------------------------------
:math:`RL_{pa}`                     Minimum RES energy for each period, scenario, and area            GWh
==================================  ================================================================  =====

==============================  ========================================================  ====
**System inertia**
----------------------------------------------------------------------------------------------
:math:`SI^p_{\omega na}`        System inertia for each area                              s
==============================  ========================================================  ====

=================================================================  ========================================================================================================================  ================
**Generation system**
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------  ----------------
:math:`CFG_g`                                                      Annualized fixed cost of a candidate generator                                                                            M€/yr
:math:`CFR_g`                                                      Annualized fixed cost of a candidate generator to be retired                                                              M€/yr
:math:`A_g`                                                        Availability of each generator for adequacy reserve margin                                                                p.u.
:math:`\underline{GP}_g, \overline{GP}_g`                          Rated minimum load and maximum output of a generator                                                                      GW
:math:`\underline{GP}^p_{\omega ng}, \overline{GP}^p_{\omega ng}`  Minimum load and maximum output of a generator                                                                            GW
:math:`\underline{GC}^p_{\omega ne}, \overline{GC}^p_{\omega ne}`  Minimum and maximum consumption of an ESS                                                                                 GW
:math:`\underline{GH}_g, \overline{GH}_g`                          Rated minimum and maximum heat of a CHP or a fuel heater                                                                  GW
:math:`CF^p_{\omega ng}, CV^p_{\omega ng}`                         Fixed (no load) and variable cost of a generator. Variable cost includes fuel and O&M                                     €/h, €/MWh
:math:`CE^p_{\omega ng}`                                           Emission cost of a generator                                                                                              €/MWh
:math:`ER_g`                                                       Emission rate of a generator                                                                                              tCO2/MWh
:math:`CV_e`                                                       Variable cost of an ESS or pumped-storage hydropower plant when charging                                                  €/MWh
:math:`RU_g, RD_g`                                                 Ramp up/down of a non-renewable unit or maximum discharge/charge rate for ESS discharge/charge                            MW/h
:math:`TU_t, TD_t`                                                 Minimum uptime and downtime of a thermal unit                                                                             h
:math:`TS_t`                                                       Minimum stable time of a thermal unit                                                                                     h
:math:`ST_e`                                                       Maximum shift time of an ESS unit (in particular, for demand side management)                                             h
:math:`CSU_g, CSD_g`                                               Startup and shutdown cost of a committed unit                                                                             M€
:math:`\tau_e`                                                     Storage cycle of the ESS (e.g., 1, 24, 168, 8736 h -for daily, weekly, monthly, yearly-)                                  h
:math:`\rho_e`                                                     Outflow cycle of the ESS (e.g., 1, 24, 168, 8736 h -for hourly, daily, weekly, monthly, yearly-)                          h
:math:`\sigma_g`                                                   Energy cycle of the unit (e.g., 24, 168, 672, 8736 h -for daily, weekly, monthly, yearly-)                                h
:math:`GI_g`                                                       Generator inertia                                                                                                         s
:math:`EF_e`                                                       Round-trip efficiency of the pump/turbine cycle of a pumped-storage hydro plant or charge/discharge of a battery          p.u.
:math:`PF_h`                                                       Production function from water inflows to electricity                                                                     kWh/m\ :sup:`3`
:math:`PF'_e`                                                      Production function from electricity to hydrogen of an electrolyzer                                                       kWh/kgH2
:math:`PF''_e`                                                     Production function from electricity to heat of a heat pump or an electrical heater                                       kWh/kWh
:math:`PH''_g`                                                     Power to heat ratio for a CHP :math:`\frac{\overline{GP}_g - \underline{GP}_g}{\overline{GH}_g - \underline{GH}_g}`       kWh/kWh
:math:`\underline{I}^p_{\omega ne}, \overline{I}^p_{\omega ne}`    Minimum and maximum storage of an ESS (e.g., hydropower plant, closed-/open-loop pumped-storage hydro)                    GWh
:math:`I^p_{\omega e}`                                             Initial storage of an ESS (e.g., hydropower plant, closed-/open-loop pumped-storage hydro)                                GWh
:math:`\underline{E}^p_{\omega ne}, \overline{E}^p_{\omega ne}`    Minimum and maximum energy produced by a unit in an interval defined                                                      GW
:math:`EI^p_{\omega ne}`                                           Energy inflows of an ESS (e.g., hydropower plant)                                                                         GW
:math:`EO^p_{\omega ne}`                                           Energy outflows of an ESS (e.g., hydrogen, electric vehicle, hydropower plant, demand response)                           GW
=================================================================  ========================================================================================================================  ================

=====================================================================  =======================================================================================================  ================
**Hydropower system**
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
:math:`CFE_{e'}`                                                       Annualized fixed cost of a candidate reservoir                                                           M€/yr
:math:`\underline{I'}^p_{\omega ne'}, \overline{I'}^p_{\omega ne'}`    Minimum and maximum volume of a reservoir                                                                hm\ :sup:`3`
:math:`HI^p_{\omega ne'}`                                              Natural water inflows of a reservoir                                                                     m\ :sup:`3`/s
:math:`HO^p_{\omega ne'}`                                              Hydro outflows of a reservoir (e.g., irrigation)                                                         m\ :sup:`3`/s
=====================================================================  =======================================================================================================  ================

=========================================  =========================================================================================================================================  =====
**Electricity transmission system**
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
:math:`CFT_{ijc}`                          Annualized fixed cost of a candidate electricity transmission line                                                                         M€/yr
:math:`\overline{F}_{ijc}`                 Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a transmission line                              GW
:math:`\overline{F}'_{ijc}`                Maximum power flow used in the Kirchhoff's 2nd law constraint (e.g., disjunctive constraint for the candidate AC lines)                    GW
:math:`L_{ijc}`                            Loss factor of an electric transmission line                                                                                               p.u.
:math:`X_{ijc}`                            Reactance of an electric transmission line                                                                                                 p.u.
:math:`SON_{ijc}, SOF_{ijc}`               Minimum switch-on and switch-off state of a line                                                                                           h
:math:`S_B`                                Base power                                                                                                                                 GW
:math:`\overline{θ}'_{cy,i'j'c'}`          Maximum angle used in the cycle Kirchhoff's 2nd law constraint (i.e., disjunctive constraint for a cycle with some AC candidate lines)     rad
=========================================  =========================================================================================================================================  =====

The net transfer capacity of an electric transmission line can be different in each direction. However, here it is presented as equal for simplicity.

=========================================  =================================================================================================================  =====
**Hydrogen transmission system**
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
:math:`CFH_{ijc}`                          Annualized fixed cost of a candidate hydrogen transmission pipeline                                                M€/yr
:math:`\overline{FH}_{ijc}`                Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a pipeline               tH2
=========================================  =================================================================================================================  =====

The net transfer capacity of a hydrogen transmission pipeline can be different in each direction. However, here it is presented as equal for simplicity.

=========================================  =================================================================================================================  ======
**Heat transmission system**
--------------------------------------------------------------------------------------------------------------------------------------------------------------------
:math:`CFP_{ijc}`                          Annualized fixed cost of a candidate heat pipe                                                                     M€/yr
:math:`\overline{FP}_{ijc}`                Net transfer capacity (total transfer capacity multiplied by the security coefficient) of a heat pipe              GW
=========================================  =================================================================================================================  ======

The net transfer capacity of a heat pipe can be different in each direction. However, here it is presented as equal for simplicity.

Variables
---------

They are written in **lowercase** letters.

==========================  ==================  ===
**Electricity demand**
---------------------------------------------------
:math:`ens^p_{\omega ni}`   Energy not served   GW
==========================  ==================  ===

==========================  ===================  ===
**Hydrogen demand**
----------------------------------------------------
:math:`hns^p_{\omega ni}`   Hydrogen not served  tH2
==========================  ===================  ===

==========================  ===================  ===
**Heat demand**
----------------------------------------------------
:math:`htns^p_{\omega ni}`  Heat not served      GW
==========================  ===================  ===

===============================================================  ================================================================================================  ======
**Generation system**
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
:math:`icg^p_g`                                                  Candidate generator or ESS installed or not                                                       {0,1}
:math:`rcg^p_g`                                                  Candidate generator or ESS retired   or not                                                       {0,1}
:math:`gp^p_{\omega ng}, gc^p_{\omega ng}`                       Generator output (discharge if an ESS) and consumption (charge if an ESS)                         GW
:math:`go^p_{\omega ne}`                                         Generator outflows of an ESS                                                                      GW
:math:`p^p_{\omega ng}`                                          Generator output of the second block (i.e., above the minimum load)                               GW
:math:`c^p_{\omega ne}`                                          Generator charge                                                                                  GW
:math:`gh^p_{\omega ng}`                                         Heat output of a fuel heater                                                                      GW
:math:`ur^p_{\omega ng}, dr^p_{\omega ng}`                       Upward and downward operating reserves of a non-renewable generating unit                         GW
:math:`ur'^p_{\omega ne}, dr'^p_{\omega ne}`                     Upward and downward operating reserves of an ESS as a consumption unit                            GW
:math:`ei^p_{\omega ne}`                                         Variable energy inflows of a candidate ESS (e.g., hydropower plant)                               GW
:math:`i^p_{\omega ne}`                                          ESS stored energy (inventory, reservoir energy, state of charge)                                  GWh
:math:`s^p_{\omega ne}`                                          ESS spilled energy                                                                                GWh
:math:`uc^p_{\omega ng}, su^p_{\omega ng}, sd^p_{\omega ng}`     Commitment, startup, and shutdown of generation unit per load level                               {0,1}
:math:`rss^p_{\omega ng}, rsu^p_{\omega ng}, rsd^p_{\omega ng}`  Stable, ramp up, and ramp down states of generation unit with minimum stable time per load level  {0,1}
:math:`uc'_g`                                                    Maximum commitment of a generation unit for all the load levels                                   {0,1}
===============================================================  ================================================================================================  ======

======================================  ==========================================================================  ==============
**Hydropower system**
----------------------------------------------------------------------------------------------------------------------------------
:math:`icr^p_{e'}`                      Candidate reservoir installed or not                                        {0,1}
:math:`hi^p_{\omega ne'}`               Variable water inflows of a candidate reservoir (e.g., hydropower plant)    m\ :sup:`3`/s
:math:`ho^p_{\omega ne'}`               Hydro outflows of a reservoir                                               m\ :sup:`3`/s
:math:`i'^p_{\omega ne'}`               Reservoir volume                                                            hm\ :sup:`3`
:math:`s'^p_{\omega ne'}`               Reservoir spilled water                                                     hm\ :sup:`3`
======================================  ==========================================================================  ==============

========================================================================  =================================================================  =====
**Electricity transmission system**
--------------------------------------------------------------------------------------------------------------------------------------------------
:math:`ict^p_{ijc}`                                                       Candidate transmission installed or not                            {0,1}
:math:`swt^p_{\omega nijc}, son^p_{\omega nijc}, sof^p_{\omega nijc}`     Switching state, switch-on and switch-off of an electric line      {0,1}
:math:`f^p_{\omega nijc}`                                                 Power flow through an electric line                                GW
:math:`l^p_{\omega nijc}`                                                 Half ohmic losses of an electric line                              GW
:math:`\theta^p_{\omega ni}`                                              Voltage angle of a node                                            rad
========================================================================  =================================================================  =====

========================================================================  ==============================================================  =====
**Hydrogen transmission system**
-----------------------------------------------------------------------------------------------------------------------------------------------
:math:`ich^p_{ijc}`                                                       Candidate hydrogen pipeline installed or not                    {0,1}
:math:`fh^p_{\omega nijc}`                                                Hydrogen flow through a hydrogen pipeline                       tH2
========================================================================  ==============================================================  =====

========================================================================  ==============================================================  ======
**Heat transmission system**
------------------------------------------------------------------------------------------------------------------------------------------------
:math:`icp^p_{ijc}`                                                       Candidate heat pipe installed or not                            {0,1}
:math:`fp^p_{\omega nijc}`                                                Heat flow through a heat pipe                                   GW
========================================================================  ==============================================================  ======

Equations
---------

The names between parenthesis correspond to the names of the constraints in the code.

**Objective function**: minimization of total (investment and operation) cost for the multi-period scope of the model

Electricity, heat, and hydrogen generation, (energy and reservoir) storage and (electricity, hydrogen, and heat) network investment cost plus retirement cost [M€] «``eTotalFCost``» «``eTotalICost``»

:math:`\sum_{pg} DF^p CFG_g icg^p_g + \sum_{pg} DF^p CFR_g rcg^p_g + \sum_{pe'} DF^p CFE_{e'} icr^p_{e'} +`
:math:`\sum_{pijc} DF^p CFT_{ijc} ict^p_{ijc} + \sum_{pijc} DF^p CFH_{ijc} ich^p_{ijc} + \sum_{pijc} DF^p CFP_{ijc} icp^p_{ijc} +`

Electricity, heat, and hydrogen generation operation cost [M€] «``eTotalGCost``»

:math:`\sum_{p \omega ng} {[DF^p P^p_{\omega} DUR^p_{\omega n} (CV^p_{\omega ng} gp^p_{\omega ng} + CF^p_{\omega ng} uc^p_{\omega ng}) + DF^p CSU_g su^p_{\omega ng} + DF^p CSD_g sd^p_{\omega ng}]} +`

Generation emission cost [M€] «``eTotalECost``» «``eTotalECostArea``»

:math:`\sum_{p \omega ng} {DF^p P^p_{\omega} DUR^p_{\omega n} CE^p_{\omega ng} gp^p_{\omega ng}} +`

Variable consumption operation cost [M€] «``eTotalCCost``»

:math:`\sum_{p \omega ne}{DF^p P^p_{\omega} DUR^p_{\omega n} CV_e gc^p_{\omega ne}} +`

Electricity, hydrogen, and heat reliability cost [M€] «``eTotalRCost``»

:math:`\sum_{p \omega ni}{DF^p P^p_{\omega} DUR^p_{\omega n} CENS  ens^p_{\omega ni}} + \sum_{p \omega ni}{DF^p P^p_{\omega} DUR^p_{\omega n} CHNS  hns^p_{\omega ni}} + \sum_{p \omega ni}{DF^p P^p_{\omega} DUR^p_{\omega n} CHtNS htns^p_{\omega ni}}`

All the periodical (annual) costs of a period :math:`p` are updated considering that the period (e.g., 2030) is replicated for a number of years defined by its weight :math:`WG^p` (e.g., 5 times) and discounted to the base year :math:`T` (e.g., 2020) with this discount factor :math:`DF^p = \frac{(1+\delta)^{WG^p}-1}{\delta(1+\delta)^{WG^p-1+p-T}}`.

**Constraints**

**Generation and network investment and retirement**

Investment and retirement decisions in consecutive years «``eConsecutiveGenInvest``» «``eConsecutiveGenRetire``» «``eConsecutiveRsrInvest``» «``eConsecutiveNetInvest``» «``eConsecutiveNetH2Invest``» «``eConsecutiveNetHeatInvest``»

:math:`icg^{p-1}_g \leq icg^p_g \quad \forall pg, g \in CG`

:math:`rcg^{p-1}_g \leq rcg^p_g \quad \forall pg, g \in CG`

:math:`icr^{p-1}_{e'} \leq icr^p_{e'} \quad \forall pe', e' \in CR`

:math:`ict^{p-1}_{ijc} \leq ict^p_{ijc} \quad \forall pijc, ijc \in CL`

:math:`ich^{p-1}_{ijc} \leq ich^p_{ijc} \quad \forall pijc, ijc \in CH`

:math:`icp^{p-1}_{ijc} \leq icp^p_{ijc} \quad \forall pijc, ijc \in CP`

**Generation operation**

Commitment decision bounded by the investment decision for candidate committed units (all except the VRE units) [p.u.] «``eInstallGenComm``»

:math:`uc^p_{\omega ng} \leq icg^p_g \quad \forall p \omega ng, g \in CG`

Commitment decision bounded by the investment or retirement decision for candidate ESS [p.u.] «``eInstallESSComm``» «``eUninstallGenComm``»

:math:`uc^p_{\omega ne} \leq icg^p_e \quad \forall p \omega ne, e \in CE`

:math:`uc^p_{\omega ne} \leq 1-rcg^p_e \quad \forall p \omega ne, e \in CE`

Output and consumption bounded by investment or retirement decision for candidate ESS [p.u.] «``eInstallGenCap``» «``eUninstallGenCap``» «``eInstallConESS``»

:math:`\frac{gp^p_{\omega ng}}{\overline{GP}^p_{\omega ng}} \leq icg^p_g \quad \forall p \omega ng, g \in CG`

:math:`\frac{gp^p_{\omega ng}}{\overline{GP}^p_{\omega ng}} \leq 1 - rcg^p_g \quad \forall p \omega ng, g \in CG`

:math:`\frac{gc^p_{\omega ne}}{\overline{GP}^p_{\omega ne}} \leq icg^p_e \quad \forall p \omega ne, e \in CE`

Heat production with fuel heater bounded by investment decision for candidate fuel heater [p.u.] «``eInstallFHUCap``»

:math:`\frac{gh^p_{\omega ng}}{\overline{GH}^p_{\omega ng}} \leq icg^p_g \quad \forall p \omega ng, g \in CB`

Adequacy system reserve margin [p.u.] «``eAdequacyReserveMargin``»

:math:`\sum_{g \in a, EG} \overline{GP}_g A_g + \sum_{g \in a, CG} icg^p_g \overline{GP}_g A_g \geq PD_{pa} RM_{pa} \quad \forall pa`

Maximum CO2 emission [MtC02] «``eMaxSystemEmission``»

:math:`\sum_{ng} {DUR^p_{\omega n} CE^p_{\omega ng} gp^p_{\omega ng}} \leq EL_{pa} \quad \forall p \omega a`

Minimum RES energy [GW] «``eMinSystemRESEnergy``» «``eTotalRESEnergyArea``»

:math:`\frac{\sum_{ng} {DUR^p_{\omega n} gp^p_{\omega ng}}}{\sum_{n} {DUR^p_{\omega n}}} \geq \frac{RL_{pa}}{\sum_{n} {DUR^p_{\omega n}}}  \quad \forall p \omega a`

Balance of electricity generation and demand at each node with ohmic losses [GW] «``eBalanceElec``»

:math:`\sum_{g \in i} gp^p_{\omega ng} - \sum_{e \in i} gc^p_{\omega ne} + ens^p_{\omega ni} = D^p_{\omega ni} + \sum_{jc} l^p_{\omega nijc} + \sum_{jc} l^p_{\omega njic} + \sum_{jc} f^p_{\omega nijc} - \sum_{jc} f^p_{\omega njic} \quad \forall p \omega ni`

The sum of the inertia of the committed units must satisfy the system inertia for each area [s] «``eSystemInertia``»

:math:`\sum_{g \in a} GI_g uc^p_{\omega ng} \geq SI^p_{\omega na} \quad \forall p \omega na`

Upward and downward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] «``eOperReserveUp``» «``eOperReserveDw``»

:math:`\sum_{g \in a} ur^p_{\omega ng} + \sum_{e \in a} ur'^p_{\omega ne} = UR^p_{\omega na} \quad \forall p \omega na`

:math:`\sum_{g \in a} dr^p_{\omega ng} + \sum_{e \in a} dr'^p_{\omega ne} = DR^p_{\omega na} \quad \forall p \omega na`

Ratio between downward and upward operating reserves provided by non-renewable generators, and ESS when charging for each area [GW] «``eReserveMinRatioDwUp``» «``eReserveMaxRatioDwUp``» «``eRsrvMinRatioDwUpESS``» «``eRsrvMaxRatioDwUpESS``»

:math:`\underline{DtUR} \: ur^p_{\omega ng}  \leq dr^p_{\omega ng}  \leq \overline{DtUR} \: ur^p_{\omega ng}  \quad \forall p \omega ng`

:math:`\underline{DtUR} \: ur'^p_{\omega ne} \leq dr'^p_{\omega ne} \leq \overline{DtUR} \: ur'^p_{\omega ne} \quad \forall p \omega ne`

VRES units (i.e., those with linear variable cost equal to 0 and no storage capacity) do not contribute to the the operating reserves.

Operating reserves from ESS can only be provided if enough energy is available for producing [GW] «``eReserveUpIfEnergy``» «``eReserveDwIfEnergy``»

:math:`ur^p_{\omega ne} \leq \frac{                             i^p_{\omega ne}}{DUR^p_{\omega n}} \quad \forall p \omega ne`

:math:`dr^p_{\omega ne} \leq \frac{\overline{I}^p_{\omega ne} - i^p_{\omega ne}}{DUR^p_{\omega n}} \quad \forall p \omega ne`

or for storing [GW] «``eESSReserveUpIfEnergy``» «``eESSReserveDwIfEnergy``»

:math:`ur'^p_{\omega ne} \leq \frac{\overline{I}^p_{\omega ne} - i^p_{\omega ne}}{DUR^p_{\omega n}} \quad \forall p \omega ne`

:math:`dr'^p_{\omega ne} \leq \frac{                             i^p_{\omega ne}}{DUR^p_{\omega n}} \quad \forall p \omega ne`

Maximum and minimum relative inventory of ESS candidates (only for load levels multiple of 1, 24, 168, 8736 h depending on the ESS storage type) constrained by the ESS commitment decision times the maximum capacity [p.u.] «``eMaxInventory2Comm``» «``eMinInventory2Comm``»

:math:`\frac{i^p_{\omega ne}}{\overline{I}^p_{\omega ne}}  \leq uc^p_{\omega ne} \quad \forall p \omega ne, e \in CE`

:math:`\frac{i^p_{\omega ne}}{\underline{I}^p_{\omega ne}} \geq uc^p_{\omega ne} \quad \forall p \omega ne, e \in CE`

Energy inflows of ESS candidates (only for load levels multiple of 1, 24, 168, 8736 h depending on the ESS storage type) constrained by the ESS commitment decision times the energy inflows data [p.u.] «``eInflows2Comm``»

:math:`\frac{ei^p_{\omega ne}}{EI^p_{\omega ne}} \leq uc^p_{\omega ne} \quad \forall p \omega ne, e \in CE`

ESS energy inventory (only for load levels multiple of 1, 24, 168 h depending on the ESS storage type) [GWh] «``eESSInventory``»

:math:`i^p_{\omega,n-\frac{\tau_e}{\nu,e}} + \sum_{n' = n-\frac{\tau_e}{\nu}}^n DUR^p_{\omega n'} (EI^p_{\omega n'e} - go^p_{\omega n'e} - gp^p_{\omega n'e} + EF_e gc^p_{\omega n'e}) = i^p_{\omega ne} + s^p_{\omega ne} \quad \forall p \omega ne, e \in EE`

:math:`i^p_{\omega,n-\frac{\tau_e}{\nu,e}} + \sum_{n' = n-\frac{\tau_e}{\nu}}^n DUR^p_{\omega n'} (ei^p_{\omega n'e} - go^p_{\omega n'e} - gp^p_{\omega n'e} + EF_e gc^p_{\omega n'e}) = i^p_{\omega ne} + s^p_{\omega ne} \quad \forall p \omega ne, e \in CE`

The initial inventory of the ESS candidates divided by its initial storage :math:`I^p_{\omega e}` is equal to the final reservoir divide by its initial storage [p.u.] «``eIniFinInventory``».

:math:`\frac{i^p_{\omega,0,e}}{I^p_{\omega e}} = \frac{i^p_{\omega,N,e}}{I^p_{\omega e}} \quad \forall p \omega e, e \in CE`

The initial inventory of the ESS candidates divided by their initial storage :math:`I^p_{\omega e}` is fixed to the commitment decision [p.u.] «``eIniInventory``».

:math:`\frac{i^p_{\omega,0,e}}{I^p_{\omega e}} \leq uc^p_{\omega ne} \quad \forall p \omega ne, e \in CE`

Maximum shift time of stored energy [GWh]. It is thought to be applied to demand side management «``eMaxShiftTime``»

:math:`DUR^p_{\omega n} EF_e gc^p_{\omega ne} \leq \sum_{n' = n+1}^{n+\frac{ST_e}{\nu}} DUR^p_{\omega n'} gp^p_{\omega n'e} \quad \forall p \omega ne`

ESS outflows (only for load levels multiple of 1, 24, 168, 672, and 8736 h depending on the ESS outflow cycle) must be satisfied [GWh] «``eEnergyOutflows``»

:math:`\sum_{n' = n-\frac{\tau_e}{\rho_e}}^n (go^p_{\omega n'e} - EO^p_{\omega n'e}) DUR^p_{\omega n'} = 0 \quad \forall p \omega ne, n \in \rho_e`

Maximum and minimum energy production (only for load levels multiple of 24, 168, 672, 8736 h depending on the unit energy type) must be satisfied [GWh] «``eMaximumEnergy``»  «``eMinimumEnergy``»

:math:`\sum_{n' = n-\sigma_g}^n (gp^p_{\omega n'g} - \overline{E}^p_{\omega n'g})  DUR^p_{\omega n'} \leq 0 \quad \forall p \omega ng, n \in \sigma_g`

:math:`\sum_{n' = n-\sigma_g}^n (gp^p_{\omega n'g} - \underline{E}^p_{\omega n'g}) DUR^p_{\omega n'} \geq 0 \quad \forall p \omega ng, n \in \sigma_g`

Maximum and minimum output of the second block of a committed unit (all except the VRES units) [p.u.] «``eMaxOutput2ndBlock``» «``eMinOutput2ndBlock``»

* D.A. Tejada-Arango, S. Lumbreras, P. Sánchez-Martín, and A. Ramos "Which Unit-Commitment Formulation is Best? A Systematic Comparison" IEEE Transactions on Power Systems 35 (4): 2926-2936, Jul 2020 `10.1109/TPWRS.2019.2962024 <https://doi.org/10.1109/TPWRS.2019.2962024>`_

* C. Gentile, G. Morales-España, and A. Ramos "A tight MIP formulation of the unit commitment problem with start-up and shut-down constraints" EURO Journal on Computational Optimization 5 (1), 177-201, Mar 2017. `10.1007/s13675-016-0066-y <https://doi.org/10.1007/s13675-016-0066-y>`_

* G. Morales-España, A. Ramos, and J. Garcia-Gonzalez "An MIP Formulation for Joint Market-Clearing of Energy and Reserves Based on Ramp Scheduling" IEEE Transactions on Power Systems 29 (1): 476-488, Jan 2014. `10.1109/TPWRS.2013.2259601 <https://doi.org/10.1109/TPWRS.2013.2259601>`_

* G. Morales-España, J.M. Latorre, and A. Ramos "Tight and Compact MILP Formulation for the Thermal Unit Commitment Problem" IEEE Transactions on Power Systems 28 (4): 4897-4908, Nov 2013. `10.1109/TPWRS.2013.2251373 <https://doi.org/10.1109/TPWRS.2013.2251373>`_

:math:`\frac{p^p_{\omega ng} + ur^p_{\omega ng}}{\overline{GP}^p_{\omega ng} - \underline{GP}^p_{\omega ng}} \leq uc^p_{\omega ng} - su^p_{\omega ng} - sd^p_{\omega,n+\nu,g} \quad \forall p \omega ng`

:math:`p^p_{\omega ng} - dr^p_{\omega ng} \geq 0                \quad \forall p \omega ng`

Maximum and minimum charge of an ESS [p.u.] «``eMaxCharge``» «``eMinCharge``»

:math:`\frac{c^p_{\omega ne} + dr'^p_{\omega ne}}{\overline{GC}^p_{\omega ne} - \underline{GC}^p_{\omega ne}} \leq 1 \quad \forall p \omega ne`

:math:`c^p_{\omega ne} - ur'^p_{\omega ne} \geq 0 \quad \forall p \omega ne`

Incompatibility between charge and discharge of an ESS [p.u.] «``eChargeDischarge``»

:math:`\frac{p^p_{\omega ne} + URA \: ur'^p_{\omega ne}}{\overline{GP}^p_{\omega ne} - \underline{GP}^p_{\omega ne}} + \frac{c^p_{\omega ne} + DRA \: dr'^p_{\omega ne}}{\overline{GC}^p_{\omega ne} - \underline{GC}^p_{\omega ne}} \leq 1 \quad \forall p \omega ne, e \in EE, CE`

Total output of a committed unit (all except the VRES units) [GW] «``eTotalOutput``»

:math:`\frac{gp^p_{\omega ng}}{\underline{GP}^p_{\omega ng}} = uc^p_{\omega ng} + \frac{p^p_{\omega ng} + URA \: ur^p_{\omega ng} - DRA \: dr^p_{\omega ng}}{\underline{GP}^p_{\omega ng}} \quad \forall p \omega ng`

Total charge of an ESS [GW] «``eESSTotalCharge``»

:math:`\frac{gc^p_{\omega ne}}{\underline{GC}^p_{\omega ne}} = 1 + \frac{c^p_{\omega ne} + URA \: ur'^p_{\omega ne} - DRA \: dr'^p_{\omega ne}}{\underline{GC}^p_{\omega ne}} \quad \forall p \omega ne, e \in EE, CE`

Incompatibility between charge and outflows use of an ESS [p.u.] «``eChargeOutflows``»

:math:`\frac{go^p_{\omega ne} + c^p_{\omega ne}}{\overline{GC}^p_{\omega ne} - \underline{GC}^p_{\omega ne}} \leq 1 \quad \forall p \omega ne, e \in EE, CE`

Logical relation between commitment, startup and shutdown status of a committed unit (all except the VRES units) [p.u.] «``eUCStrShut``»

:math:`uc^p_{\omega ng} - uc^p_{\omega,n-\nu,g} = su^p_{\omega ng} - sd^p_{\omega ng} \quad \forall p \omega ng`

Logical relation between stable, ramp up, and ramp down states (units with stable time) [p.u.] «``eStableStates``»

:math:`rss^p_{\omega ng} + rsu^p_{\omega ng} + rsd^p_{\omega ng} = uc^p_{\omega ng} \quad \forall p \omega ng`

Maximum commitment of a committable unit (all except the VRES units) [p.u.] «``eMaxCommitment``»

:math:`uc^p_{\omega ng} \leq uc'_g \quad \forall p \omega ng`

Maximum commitment of any unit [p.u.] «``eMaxCommitGen``»

:math:`\sum_{p \omega n} \frac{gp^p_{\omega ng}}{\overline{GP}_g} \leq uc'_g \quad \forall p \omega ng`

Mutually exclusive :math:`g` and :math:`g'` units (e.g., thermal, ESS, VRES units) [p.u.] «``eExclusiveGens``»

:math:`uc'_g + uc'_{g'} \leq 1 \quad \forall g, g'`

Initial commitment of the units is determined by the model based on the merit order loading, including the VRES and ESS units.

Maximum ramp up and ramp down for the second block of a non-renewable (thermal, hydro) unit [p.u.] «``eRampUp``» «``eRampDw``»

* P. Damcı-Kurt, S. Küçükyavuz, D. Rajan, and A. Atamtürk, “A polyhedral study of production ramping,” Math. Program., vol. 158, no. 1–2, pp. 175–205, Jul. 2016. `10.1007/s10107-015-0919-9 <https://doi.org/10.1007/s10107-015-0919-9>`_

:math:`\frac{- p^p_{\omega,n-\nu,g} - dr^p_{\omega,n-\nu,g} + p^p_{\omega ng} + ur^p_{\omega ng}}{DUR^p_{\omega n} RU_g} \leq   uc^p_{\omega ng}      - su^p_{\omega ng} \quad \forall p \omega ng`

:math:`\frac{- p^p_{\omega,n-\nu,g} + ur^p_{\omega,n-\nu,g} + p^p_{\omega ng} - dr^p_{\omega ng}}{DUR^p_{\omega n} RD_g} \geq - uc^p_{\omega,n-\nu,g} + sd^p_{\omega ng} \quad \forall p \omega ng`

Maximum ramp down and ramp up for the charge of an ESS [p.u.] «``eRampUpCharge``» «``eRampDwCharge``»

:math:`\frac{- c^p_{\omega,n-\nu,e} - ur^p_{\omega,n-\nu,e} + c^p_{\omega ne} + dr^p_{\omega ne}}{DUR^p_{\omega n} RD_e} \leq   1 \quad \forall p \omega ne`

:math:`\frac{- c^p_{\omega,n-\nu,e} + dr^p_{\omega,n-\nu,e} + c^p_{\omega ne} - ur^p_{\omega ne}}{DUR^p_{\omega n} RU_e} \geq - 1 \quad \forall p \omega ne`

Detection of ramp up and ramp down state for the second block of a non-renewable (thermal) unit with minimum stable time [p.u.] «``eRampUpState``» «``eRampDwState``»

:math:`\frac{- p^p_{\omega,n-\nu,g} + p^p_{\omega ng}}{DUR^p_{\omega n} RU_g} \leq rsu^p_{\omega ng} - \epsilon \cdot rsd^p_{\omega ng} \quad \forall p \omega ng`

:math:`\frac{  p^p_{\omega,n-\nu,g} - p^p_{\omega ng}}{DUR^p_{\omega n} RD_g} \leq rsd^p_{\omega ng} - \epsilon \cdot rsu^p_{\omega ng} \quad \forall p \omega ng`

Minimum up time and down time of thermal unit [p.u.] «``eMinUpTime``» «``eMinDownTime``»

* D. Rajan and S. Takriti, “Minimum up/down polytopes of the unit commitment problem with start-up costs,” IBM, New York, Technical Report RC23628, 2005. https://pdfs.semanticscholar.org/b886/42e36b414d5929fed48593d0ac46ae3e2070.pdf

:math:`\sum_{n'=n+\nu-TU_t}^n su^p_{\omega n't} \leq     uc^p_{\omega nt} \quad \forall p \omega nt`

:math:`\sum_{n'=n+\nu-TD_t}^n sd^p_{\omega n't} \leq 1 - uc^p_{\omega nt} \quad \forall p \omega nt`

Minimum stable time of thermal unit [p.u.] «``eMinStableTime``»

:math:`rsu^p_{\omega nt} \leq 1 - rsd^p_{\omega n't} \quad \forall p \omega nn't, n' \in [n-TS_t,n-1]`

**Reservoir operation**

Maximum and minimum relative volume of reservoir candidates (only for load levels multiple of 1, 24, 168, 8736 h depending on the reservoir volume type) constrained by the hydro commitment decision times the maximum capacity [p.u.] «``eMaxVolume2Comm``» «``eMinVolume2Comm``»

:math:`\frac{i'^p_{\omega ne'}}{\overline{I'}^p_{\omega ne'}}  \leq \sum_{h \in dw(e')} uc^p_{\omega nh} \quad \forall p \omega ne', e' \in CR`

:math:`\frac{i'^p_{\omega ne'}}{\underline{I'}^p_{\omega ne'}} \geq \sum_{h \in dw(e')} uc^p_{\omega nh} \quad \forall p \omega ne', e' \in CR`

Operating reserves from a hydropower plant can only be provided if enough energy is available for turbining at the upstream reservoir [GW] «``eTrbReserveUpIfEnergy``» «``eTrbReserveDwIfEnergy``»

:math:`ur^p_{\omega nh} \leq \frac{\sum_{e' \in up(h)}                                i'^p_{\omega ne'}}{DUR^p_{\omega n}} \quad \forall p \omega nh`

:math:`dr^p_{\omega nh} \leq \frac{\sum_{e' \in up(h)} \overline{I'}^p_{\omega ne'} - i'^p_{\omega ne'}}{DUR^p_{\omega n}} \quad \forall p \omega nh`

or for pumping [GW] «``ePmpReserveUpIfEnergy``» «``ePmpReserveDwIfEnergy``»

:math:`ur'^p_{\omega nh} \leq \frac{\sum_{e' \in up(h)} \overline{I'}^p_{\omega ne'} - i'^p_{\omega ne'}}{DUR^p_{\omega n}} \quad \forall p \omega nh`

:math:`dr'^p_{\omega nh} \leq \frac{\sum_{e' \in up(h)}                                i'^p_{\omega ne'}}{DUR^p_{\omega n}} \quad \forall p \omega nh`

Water volume for each hydro reservoir (only for load levels multiple of 1, 24, 168 h depending on the reservoir storage type) [hm\ :sup:`3`] «``eHydroInventory``»

:math:`i'^p_{\omega,n-\frac{\tau_e'}{\nu,e'}} + \sum_{n' = n-\frac{\tau_e'}{\nu}}^n DUR^p_{\omega n'} (0.0036 HI^p_{\omega n'e'} - 0.0036 ho^p_{\omega n'e'} - \sum_{h \in dw(e')} gp^p_{\omega n'h} / PF_h + \sum_{h \in up(e')} gp^p_{\omega n'h} / PF_h +`
:math:`+ \sum_{h \in up(e')} EF_e' gc^p_{\omega n'h} / PF_h - \sum_{h \in dw(h)} EF_e' gc^p_{\omega n'h} / PF_h) = i'^p_{\omega ne'} + s'^p_{\omega ne'} - \sum_{e'' \in up(e')} s'^p_{\omega ne''} \quad \forall p \omega ne', e' \in ER`

:math:`i'^p_{\omega,n-\frac{\tau_e'}{\nu,e'}} + \sum_{n' = n-\frac{\tau_e'}{\nu}}^n DUR^p_{\omega n'} (0.0036 hi^p_{\omega n'e'} - 0.0036 ho^p_{\omega n'e'} - \sum_{h \in dw(e')} gp^p_{\omega n'h} / PF_h + \sum_{h \in up(e')} gp^p_{\omega n'h} / PF_h +`
:math:`+ \sum_{h \in up(e')} EF_e' gc^p_{\omega n'h} / PF_h - \sum_{h \in dw(h)} EF_e' gc^p_{\omega n'h} / PF_h) = i'^p_{\omega ne'} + s'^p_{\omega ne'} - \sum_{e'' \in up(e')} s'^p_{\omega ne''} \quad \forall p \omega ne', e' \in CR`

The initial volume of the hydro reservoir divided by its initial volume :math:`I^p_{\omega e'}` is equal to the final reservoir divide by its initial volume [p.u.] «``eIniFinVolume``».

:math:`\frac{i'^p_{\omega,0,e'}}{I^p_{\omega e'}} = \frac{i'^p_{\omega,N,e'}}{I^p_{\omega e'}} \quad \forall p \omega e', e' \in CE`

Hydro outflows (only for load levels multiple of 1, 24, 168, 672, and 8736 h depending on the ESS outflow cycle) must be satisfied [m\ :sup:`3`/s] «``eHydroOutflows``»

:math:`\sum_{n' = n-\frac{\tau_e'}{\rho_e'}}^n (ho^p_{\omega n'e'} - HO^p_{\omega n'e'}) DUR^p_{\omega n'} = 0 \quad \forall p \omega ne', n \in \rho_e'`

**Electricity network operation**

Logical relation between transmission investment and switching {0,1} «``eLineStateCand``»

:math:`swt^p_{\omega nijc} \leq ict^p_{ijc} \quad \forall p \omega nijc, ijc \in CL`

Logical relation between switching state, switch-on and switch-off status of a line [p.u.] «``eSWOnOff``»

:math:`swt^p_{\omega nijc} - swt^p_{\omega,n-\nu,ijc} = son^p_{\omega nijc} - sof^p_{\omega nijc} \quad \forall p \omega nijc`

The initial status of the lines is pre-defined as switched on.

Minimum switch-on and switch-off state of a line [h] «``eMinSwOnState``» «``eMinSwOffState``»

:math:`\sum_{n'=n+\nu-SON_{ijc}}^n son^p_{\omega n'ijc} \leq     swt^p_{\omega nijc} \quad \forall p \omega nijc`

:math:`\sum_{n'=n+\nu-SOF_{ijc}}^n sof^p_{\omega n'ijc} \leq 1 - swt^p_{\omega nijc} \quad \forall p \omega nijc`

Power flow limit in transmission lines [p.u.] «``eNetCapacity1``» «``eNetCapacity2``»

:math:`- swt^p_{\omega nijc} \leq \frac{f^p_{\omega nijc}}{\overline{F}_{ijc}} \leq swt^p_{\omega nijc} \quad \forall p \omega nijc`

DC Optimal power flow for existing and non-switchable, and candidate and switchable AC-type lines (Kirchhoff's second law) [rad] «``eKirchhoff2ndLaw1``» «``eKirchhoff2ndLaw2``»

:math:`\frac{f^p_{\omega nijc}}{\overline{F}'_{ijc}} - (\theta^p_{\omega ni} - \theta^p_{\omega nj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} = 0 \quad \forall p \omega nijc, ijc \in EL`

:math:`-1+swt^p_{\omega nijc} \leq \frac{f^p_{\omega nijc}}{\overline{F}'_{ijc}} - (\theta^p_{\omega ni} - \theta^p_{\omega nj})\frac{S_B}{X_{ijc}\overline{F}'_{ijc}} \leq 1-swt^p_{\omega nijc} \quad \forall p \omega nijc, ijc \in CL`

Half ohmic losses are linearly approximated as a function of the power flow [GW] «``eLineLosses1``» «``eLineLosses2``»

:math:`- \frac{L_{ijc}}{2} f^p_{\omega nijc} \leq l^p_{\omega nijc} \geq \frac{L_{ijc}}{2} f^p_{\omega nijc} \quad \forall p \omega nijc`

Cycle constraints for AC existing lines with DC optimal power flow formulation [rad] «``eCycleKirchhoff2ndLawCnd1``» «``eCycleKirchhoff2ndLawCnd2``».
See the cycle constraints for the AC power flow formulation in the following reference:

* E.F. Álvarez, J.C. López, L. Olmos, A. Ramos "An Optimal Expansion Planning of Power Systems Considering Cycle-Based AC Optimal Power Flow" Sustainable Energy, Grids and Networks, May 2024. `10.1016/j.segan.2024.101413 <https://doi.org/10.1016/j.segan.2024.101413>`_

Kirchhoff's second law is substituted by a cycle power flow formulation for cycles with only AC existing lines [rad]

:math:`\sum_{ijc \in cy} f_{ωpnijc} \frac{X_{ijc}}{S_B} = 0 \quad \forall ωpn,cy, cy \in CY`

and disjunctive constraints for cycles with some AC candidate line [rad]

:math:`-1+ict_{i'j'c'}  \leq \frac{\sum_{ijc \in cy} f_{ωpnijc} \frac{X_{ijc}}{S_B}}{\overline{θ}'_{cy,i'j'c'}} \leq 1-ict_{i'j'c'} \quad \forall ωpn,cy,i'j'c', cy \in CY, i'j'c' \in CLC`

Flows in AC existing parallel circuits are inversely proportional to their reactances [GW] «``eFlowParallelCandidate1``» «``eFlowParallelCandidate2``»

:math:`f_{ωpnijc} = \frac{X_{ijc'}}{X_{ijc}} f_{ωpnijc'} \quad \forall ωpnijcc', ijc \in EL, ijc' \in EL`

and disjunctive constraints in AC candidate parallel circuits are inversely proportional to their reactances [p.u.]

:math:`-1+ict_{ijc'} \leq \frac{f_{ωpnijc} - \frac{X_{ijc'}}{X_{ijc}} f_{ωpnijc'}}{\overline{F}_{ijc}} \leq 1-ict_{ijc'} \quad \forall ωpnijcc', ijc \in EL, ijc' \in CL`

Given that there are disjunctive constraints, which are only correct with binary AC investment variables, this cycle-based formulation must be used only with binary AC investment decisions.


**Hydrogen network operation**

Balance of hydrogen generation by electrolyzers, hydrogen consumption from hydrogen heater using it, and demand at each node [tH2] «``eBalanceH2``»

:math:`\sum_{e \in i} \frac{DUR^p_{\omega n}}{PF'_e} gc^p_{\omega ne} - \sum_{g \in i} gh^p_{\omega ng} + hns^p_{\omega ni} = DUR^p_{\omega n} DH^p_{\omega ni} + \sum_{jc} fh^p_{\omega nijc} - \sum_{jc} fh^p_{\omega njic} \quad \forall p \omega ni`

**Heat network operation**

Balance of heat generation produced by CHPs and fuel heaters respectively and demand at each node [GW] «``eBalanceHeat``»

:math:`\sum_{e \in i} \frac{DUR^p_{\omega n}}{PF''_e} gc^p_{\omega ne} + \sum_{g \in i} gh^p_{\omega ng} + htns^p_{\omega ni} = DUR^p_{\omega n} DF^p_{\omega ni} + \sum_{jc} fp^p_{\omega nijc} - \sum_{jc} fp^p_{\omega njic} \quad \forall p \omega ni`

**Bounds on generation and ESS variables** [GW]

:math:`0 \leq gp^p_{\omega ng}  \leq \overline{GP}^p_{\omega ng}                                   \quad \forall p \omega ng`

:math:`0 \leq go^p_{\omega ne}  \leq \max(\overline{GP}^p_{\omega ne},\overline{GC}^p_{\omega ne}) \quad \forall p \omega ne`

:math:`0 \leq gc^p_{\omega ne}  \leq \overline{GC}^p_{\omega ne}                                   \quad \forall p \omega ne`

:math:`\underline{GH}^p_{\omega ng} \leq gh^p_{\omega ng} \leq \overline{GH}^p_{\omega ng}         \quad \forall p \omega ng`

:math:`0 \leq ur^p_{\omega ng}  \leq \overline{GP}^p_{\omega ng} - \underline{GP}^p_{\omega ng}    \quad \forall p \omega ng`

:math:`0 \leq ur'^p_{\omega ne} \leq \overline{GC}^p_{\omega ne} - \underline{GC}^p_{\omega ne}    \quad \forall p \omega ne`

:math:`0 \leq dr^p_{\omega ng}  \leq \overline{GP}^p_{\omega ng} - \underline{GP}^p_{\omega ng}    \quad \forall p \omega ng`

:math:`0 \leq dr'^p_{\omega ne} \leq \overline{GC}^p_{\omega ne} - \underline{GC}^p_{\omega ne}    \quad \forall p \omega ne`

:math:`0 \leq  p^p_{\omega ng}  \leq \overline{GP}^p_{\omega ng} - \underline{GP}^p_{\omega ng}    \quad \forall p \omega ng`

:math:`0 \leq  c^p_{\omega ne}  \leq \overline{GC}^p_{\omega ne}                                   \quad \forall p \omega ne`

:math:`\underline{I}^p_{\omega ne} \leq  i^p_{\omega ne}  \leq \overline{I}^p_{\omega ne}          \quad \forall p \omega ne`

:math:`0 \leq  s^p_{\omega ne}                                                                     \quad \forall p \omega ne`

:math:`0 \leq ens^p_{\omega ni} \leq D^p_{\omega ni}                                               \quad \forall p \omega ni`

**Bounds on reservoir variables** [m\ :sup:`3`/s, hm\ :sup:`3`]

:math:`0 \leq ho^p_{\omega ne'} \leq \sum_{h \in dw(e')} \overline{GP}^p_{\omega nh} / PF_h   \quad \forall p \omega ne'`

:math:`\underline{I'}^p_{\omega ne'} \leq i'^p_{\omega ne'} \leq \overline{I'}^p_{\omega ne'} \quad \forall p \omega ne'`

:math:`0 \leq s'^p_{\omega ne'}                                                               \quad \forall p \omega ne'`

**Bounds on electricity network variables** [GW]

:math:`0 \leq l^p_{\omega nijc} \leq \frac{L_{ijc}}{2} \overline{F}_{ijc}  \quad \forall p \omega nijc`

:math:`- \overline{F}_{ijc} \leq f^p_{\omega nijc} \leq \overline{F}_{ijc} \quad \forall p \omega nijc, ijc \in EL`

Voltage angle of the reference node fixed to 0 for each scenario, period, and load level [rad]

:math:`\theta^p_{\omega n,node_{ref}} = 0`

**Bounds on hydrogen network variables** [tH2]

:math:`- \overline{FH}_{ijc} \leq fh^p_{\omega nijc} \leq \overline{FH}_{ijc} \quad \forall p \omega nijc, ijc \in EP`

**Bounds on heat network variables** [GW]

:math:`- \overline{FP}_{ijc} \leq fp^p_{\omega nijc} \leq \overline{FP}_{ijc} \quad \forall p \omega nijc, ijc \in EP`
