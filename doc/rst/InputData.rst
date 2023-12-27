.. openTEPES documentation master file, created by Andres Ramos

Electric System Input Data
==========================

All the input files must be located in a folder with the name of the case study.

Acronyms
--------

==========  ====================================================================
Acronym     Description
==========  ====================================================================
AC          Alternating Current
aFRR        Automatic Frequency Restoration Reserve
AWE         Alkaline Water Electrolyzer
BESS        Battery Energy Storage System
CC          Capacity Credit
CCGT        Combined Cycle Gas Turbine
DC          Direct Current
DCPF        DC Power Flow
DR          Demand Response
DSM         Demand-Side Management
DSR         Demand-Side Response
EFOR        Equivalent Forced Outage Rate
ENS         Energy Not Served
ENTSO-E     European Network of Transmission System Operators for Electricity
ESS         Energy Storage System
EV          Electric Vehicle
mFRR        Manual Frequency Restoration Reserve
H2          Hydrogen
HNS         Hydrogen Not Served
NTC         Net Transfer Capacity
OCGT        Open Cycle Gas Turbine
PHS         Pumped-Hydro Storage
PNS         Power Not Served
PV          Photovoltaics
RES         Renewable Energy Source
TTC         Total Transfer Capacity
VOLL        Value of Lost Load
VRE         Variable Renewable Energy
VRES        Variable Renewable Energy Source
==========  ====================================================================

Dictionaries. Sets
------------------
The dictionaries include all the possible elements of the corresponding sets included in the optimization problem. **You can't use non-English characters (e.g., ó, º)**

=============================  ===================================================================================================================================================================================================================
File                           Description
=============================  ===================================================================================================================================================================================================================
``oT_Dict_Period.csv``         Period (e.g., 2030, 2035). **It must be a positive integer**
``oT_Dict_Scenario.csv``       Scenario. Short-term uncertainties (scenarios) (e.g., s001 to s100)
``oT_Dict_Stage.csv``          Stage
``oT_Dict_LoadLevel.csv``      Load level (e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00). Load levels with duration 0 are ignored. The period (year) must represented by 8736 load levels.
``oT_Dict_Generation.csv``     Generation units (thermal -nuclear, CCGT, OCGT, coal-, ESS -storage hydro modeled in energy or in water, pumped-hydro storage PHS, battery BESS, electric vehicle EV, demand response DR, alkaline water electrolyzer AWE, solar thermal- and VRE -wind onshore and offshore, solar PV, run-of-the-river hydro-)
``oT_Dict_Technology.csv``     Generation technologies. The technology order is used in the temporal result plot.
``oT_Dict_Storage.csv``        ESS storage type (daily < 12 h, weekly < 40 h, monthly > 60 h).
``oT_Dict_Node.csv``           Nodes. A node belongs to a zone.
``oT_Dict_Zone.csv``           Zones. A zone belongs to an area.
``oT_Dict_Area.csv``           Areas. An area belongs to a region. Long-term adequacy, inertia and operating reserves are associated to areas.
``oT_Dict_Region.csv``         Regions
``oT_Dict_Circuit.csv``        Circuits
``oT_Dict_Line.csv``           Line type (AC, DC)
=============================  ===================================================================================================================================================================================================================

Geographical location of nodes, zones, areas, regions.

============================  ============  ============================
File                          Dictionary    Description
============================  ============  ============================
``oT_Dict_NodeToZone.csv``    NodeToZone    Location of nodes at zones
``oT_Dict_ZoneToArea.csv``    ZoneToArea    Location of zones at areas
``oT_Dict_AreaToRegion.csv``  AreaToRegion  Location of areas at regions
============================  ============  ============================

See the hydro system section at the end of this page to know how to define the basin topology (connection among reservoir and hydropower plants). Some additional dictionaries and data files are needed.

Input files
-----------
This is the list of the input data files and their brief description.

=========================================  ================================================================================================================================
File                                       Description
=========================================  ================================================================================================================================
``oT_Data_Option.csv``                     Options of use of the **openTEPES** model
``oT_Data_Parameter.csv``                  General system parameters
``oT_Data_Period.csv``                     Weight of each period
``oT_Data_Scenario.csv``                   Short-term uncertainties
``oT_Data_Stage.csv``                      Weight of each stage
``oT_Data_ReserveMargin.csv``              Minimum adequacy reserve margin for each area and period
``oT_Data_Emission.csv``                   Maximum CO2 emission
``oT_Data_Duration.csv``                   Duration of the load levels
``oT_Data_Demand.csv``                     Electricity demand
``oT_Data_Inertia.csv``                    System inertia by area
``oT_Data_OperatingReserveUp.csv``         Upward   operating reserves (include aFRR and mFRR for electricity balancing from ENTSO-E)
``oT_Data_OperatingReserveDown.csv``       Downward operating reserves (include aFRR and mFRR for electricity balancing from ENTSO-E)
``oT_Data_Generation.csv``                 Generation data
``oT_Data_VariableMaxGeneration.csv``      Variable maximum power generation  by load level
``oT_Data_VariableMinGeneration.csv``      Variable minimum power generation  by load level
``oT_Data_VariableMaxConsumption.csv``     Variable maximum power consumption by load level
``oT_Data_VariableMinConsumption.csv``     Variable minimum power consumption by load level
``oT_Data_VariableFuelCost.csv``           Variable fuel cost by load level
``oT_Data_EnergyInflows.csv``              Energy inflows to an ESS by load level
``oT_Data_EnergyOutflows.csv``             Energy outflows from an ESS for Power-to-X (H2 production or EV mobility or water irrigation) by load level
``oT_Data_VariableMaxStorage.csv``         Maximum storage of the ESS by load level
``oT_Data_VariableMinStorage.csv``         Minimum storage of the ESS by load level
``oT_Data_VariableMaxEnergy.csv``          Maximum energy of the unit by load level (the energy will be accumulated and enforced for the interval defined by EnergyType)
``oT_Data_VariableMinEnergy.csv``          Minimum energy of the unit by load level (the energy will be accumulated and enforced for the interval defined by EnergyType)
``oT_Data_Network.csv``                    Electricity network data
``oT_Data_NodeLocation.csv``               Node location in latitude and longitude
=========================================  ================================================================================================================================

In any input file only the columns indicated in this document will be read. For example, you can add a column for comments or additional information as needed, but it will not read by the model.

Options
----------
A description of the options included in the file ``oT_Data_Option.csv`` follows:

===================  ==================================================================   ====================================================
File                 Description
===================  ==================================================================   ====================================================
IndBinGenInvest      Indicator of binary generation   expansion decisions                 {0 continuous, 1 binary, 2 ignore investments}
IndBinGenRetirement  Indicator of binary generation  retirement decisions                 {0 continuous, 1 binary, 2 ignore retirements}
IndBinRsrInvest      Indicator of binary reservoir    expansion decisions
                     (only used for reservoirs modeled with water units)                  {0 continuous, 1 binary, 2 ignore investments}
IndBinNetInvest      Indicator of binary electric network expansion decisions             {0 continuous, 1 binary, 2 ignore investments}
IndBinNetH2Invest    Indicator of binary hydrogen network expansion decisions             {0 continuous, 1 binary, 2 ignore investments}
IndBinGenOperat      Indicator of binary generation   operation decisions                 {0 continuous, 1 binary}
IndBinGenRamps       Indicator of activating or not the up/down ramp constraints          {0 no ramps,   1 ramp constraints}
IndBinGenMinTime     Indicator of activating or not the min up/down time constraints      {0 no min time constraints, 1 min time constraints}
IndBinSingleNode     Indicator of single node case study                                  {0 network,    1 single node}
IndBinLineCommit     Indicator of binary transmission switching decisions                 {0 continuous, 1 binary}
IndBinNetLosses      Indicator of network losses                                          {0 lossless,   1 ohmic losses}
===================  ==================================================================   ====================================================

If the investment decisions are ignored (IndBinGenInvest, IndBinGenRetirement, and IndBinNetInvest take value 2) or there are no investment decisions, all the scenarios with a probability > 0 are solved sequentially (assuming a probability 1) and the periods are considered with a weight 1.

Parameters
----------
A description of the system parameters included in the file ``oT_Data_Parameter.csv`` follows:

====================  =============================================================================================================  =========
File                  Description                                                                              
====================  =============================================================================================================  =========
ENSCost               Cost of energy not served (ENS). Cost of load curtailment. Value of Lost Load (VoLL)                           €/MWh
HNSCost               Cost of hydrogen not served (HNS)                                                                              €/kgH2
PNSCost               Cost of power not served (PNS) associated with the deficit in operating reserve by load level                  €/MW
CO2Cost               Cost of CO2 emissions                                                                                          €/tCO2
UpReserveActivation   Upward   reserve activation (proportion of upward   operating reserve deployed to produce energy)              p.u.
DwReserveActivation   Downward reserve activation (proportion of downward operating reserve deployed to produce energy)              p.u.
MinRatioDwUp          Minimum ratio downward to upward operating reserves                                                            p.u.
MaxRatioDwUp          Maximum ratio downward to upward operating reserves                                                            p.u.
Sbase                 Base power used in the DCPF                                                                                    MW
ReferenceNode         Reference node used in the DCPF
TimeStep              Duration of the time step for the load levels (hourly, bi-hourly, trihourly, etc.)                             h
EconomicBaseYear      Base year for economic parameters affected by the discount rate                                                year
AnnualDiscountRate    Annual discount rate                                                                                           p.u.
====================  =============================================================================================================  =========

A time step greater than one hour it is a convenient way to reduce the load levels of the time scope. The moving average of the demand, upward/downward operating reserves, variable generation/consumption/storage and ESS energy inflows/outflows
over the time step load levels is assigned to active load levels (e.g., the mean value of the three hours is associated to the third hour in a trihourly time step).

Period
------

A description of the data included in the file ``oT_Data_Period.csv`` follows:

==============  ============  =====================
Identifier      Header        Description
==============  ============  =====================
Period          Weight        Weight of each period
==============  ============  =====================

This weight allows the definition of equivalent (representative) years (e.g., year 2030 with a weight of 5 would represent years 2030-2034). Periods are not mathematically connected between them with operation constraints, i.e., no constraints link the operation
at different periods. However, they are linked by the investment decisions, i.e., investments made in a year remain installed for the rest of the years.

Scenario
--------

A description of the data included in the file ``oT_Data_Scenario.csv`` follows:

==============  ==============  ============  ===========================================  ====
Identifier      Identifier      Header        Description
==============  ==============  ============  ===========================================  ====
Period          Scenario        Probability   Probability of each scenario in each period  p.u.
==============  ==============  ============  ===========================================  ====

For example, the scenarios can be used for obtaining the GEP+SEP+TEP considering hydro energy/water inflows uncertainty represented by means of three scenarios (wet, dry and average), or two VRE scenarios (windy/cloudy and calm/sunny).
The sum of the probabilities of all the scenarios of a period must be 1.

Stage
-----

A description of the data included in the file ``oT_Data_Stage.csv`` follows:

==============  ============  =====================
Identifier      Header        Description
==============  ============  =====================
Scenario        Weight        Weight of each stage
==============  ============  =====================

This weight allows the definition of equivalent (representative) periods (e.g., one representative week with a weight of 52 or four representative weeks each one with a weight of 13).
Stages are not mathematically connected between them, i.e., no constraints link the operation at different stages. Consequently, the storage type can't exceed the duration of the stage (i.e., if the stage lasts for 168 hours the storage type can only be hourly or daily).

Adequacy reserve margin
-----------------------

A description of the data included in the file ``oT_Data_ReserveMargin.csv`` follows:

==============  ==============  =============  ==========================================================  ====
Identifier      Identifier      Header         Description
==============  ==============  =============  ==========================================================  ====
Period          Area            ReserveMargin  Minimum adequacy reserve margin for each period and area    p.u.
==============  ==============  =============  ==========================================================  ====

This parameter is only used for system generation expansion, not for the system operation. If no value is introduced for an area, the reserve margin is considered 0.

Maximum CO2 emission
--------------------

A description of the data included in the file ``oT_Data_Emission.csv`` follows:

==============  ==============  =============  ===========================================================  =====
Identifier      Identifier      Header         Description
==============  ==============  =============  ===========================================================  =====
Period          Area            CO2Emission    Maximum CO2 emission for each period, scenario, and area     MtCO2
==============  ==============  =============  ===========================================================  =====

This parameter is only used for system generation expansion, not for the system operation. If no value is introduced for an area, the CO2 emission limit is considered infinite.

Duration
--------

A description of the data included in the file ``oT_Data_Duration.csv`` follows:

==========  ===================================================================  ========
Header      Description
==========  ===================================================================  ========
LoadLevel   Load level                                                           datetime
Duration    Duration of the load level. Load levels with duration 0 are ignored  h
Stage       Assignment of the load level to a stage
==========  ===================================================================  ========

It is a simple way to use isolated snapshots or representative days or just the first three months instead of all the hours of a year to simplify the optimization problem. All the load levels must have the same duration.
The duration is not intended to change for the several load levels of an stage. Usually, duration is put as 1 hour or 0 if you want not to use the load levels after some hour of the year. The parameter time step must be used to collapse consecutive load levels into a single one for the optimization problem.

The stage duration as sum of the duration of all the load levels must be larger or equal than the shortest duration of any storage type or any outflows type or any energy type (all given in the generation data) and multiple of it.
Consecutive stages are not connected between them, i.e., no constraints link the operation at different stages. Consequently, the storage type can't exceed the duration of the stage (i.e., if the stage lasts for 168 hours the storage type can only be hourly or daily).
Consequently, the objective function with several stages must be a bit higher than in the case of a single stage.

The initial storage of the ESSs is also fixed at the beginning and end of each stage. For example, the initial storage level is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

Electricity demand
------------------

A description of the data included in the file ``oT_Data_Demand.csv`` follows:

==========  ==============  ==========  ======  ============================================  ==
Identifier  Identifier      Identifier  Header  Description
==========  ==============  ==========  ======  ============================================  ==
Period      Scenario        Load level  Node    Power demand of the node for each load level  MW
==========  ==============  ==========  ======  ============================================  ==

The electricity demand can be negative for the (transmission) nodes where there is (renewable) generation in lower voltage levels. This negative demand is equivalent to generate that power amount in this node.
Internally, all the values below if positive demand (or above if negative demand) 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

System inertia
--------------

A description of the data included in the files ``oT_Data_Inertia.csv`` follows:

==========  ==============  ==========  ======  ================================================  ==
Identifier  Identifier      Identifier  Header  Description
==========  ==============  ==========  ======  ================================================  ==
Period      Scenario        Load level  Area    System inertia of the area for each load level    s
==========  ==============  ==========  ======  ================================================  ==

Given that the system inertia depends on the area, it can be sensible to assign an area as a country, for example. The system inertia can be used for imposing a minimum synchronous power and, consequently, force the commitment of at least some rotating units.

Internally, all the values below 2.5e-5 times the maximum system electricity demand of each area will be converted into 0 by the model.

Upward and downward operating reserves
--------------------------------------

A description of the data included in the files ``oT_Data_OperatingReserveUp.csv`` and ``oT_Data_OperatingReserveDown.csv`` follows:

==========  ==============  ==========  ======  ===================================================================  ==
Identifier  Identifier      Identifier  Header  Description
==========  ==============  ==========  ======  ===================================================================  ==
Period      Scenario        Load level  Area    Upward/downward operating reserves of the area for each load level   MW
==========  ==============  ==========  ======  ===================================================================  ==

Given that the operating reserves depend on the area, it can be sensible to assign an area as a country, for example.
These operating reserves must include Automatic Frequency Restoration Reserves (aFRR) and Manual Frequency Restoration Reserves (mFRR) for electricity balancing from ENTSO-E.

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Generation
----------
A description of the data included for each generating unit in the file ``oT_Data_Generation.csv`` follows:

====================  ================================================================================================================================  ===================================
Header                Description
====================  ================================================================================================================================  ===================================
Node                  Name of the node where generator is located. If left empty, the generator is ignored
Technology            Technology of the generator (nuclear, coal, CCGT, OCGT, ESS, solar, wind, biomass, etc.)
MutuallyExclusive     Mutually exclusive generator. Only exclusion in one direction is needed
BinaryCommitment      Binary unit commitment decision                                                                                                   Yes/No
NoOperatingReserve    No contribution to operating reserve. Yes if the unit doesn't contribute to the operating reserve                                 Yes/No
StorageType           Storage type based on storage capacity (hourly, daily, weekly, monthly, yearly)                                                   Hourly/Daily/Weekly/Monthly/Yearly
OutflowsType          Outflows type based on the electricity demand extracted from the storage (daily, weekly, monthly, yearly)                         Daily/Weekly/Monthly/Yearly
EnergyType            Energy type based on the max/min energy to be produced by the unit (daily, weekly, monthly, yearly)                               Daily/Weekly/Monthly/Yearly
MustRun               Must-run unit                                                                                                                     Yes/No
InitialPeriod         Initial period (year) when the unit is installed or can be installed, if candidate                                                Year
FinalPeriod           Final   period (year) when the unit is installed or can be installed, if candidate                                                Year
MaximumPower          Maximum power output (generation/discharge for ESS units)                                                                         MW
MinimumPower          Minimum power output (i.e., minimum stable load in the case of a thermal power plant)                                             MW
MaximumReactivePower  Maximum reactive power output (discharge for ESS units) (not used in this version)                                                MW
MinimumReactivePower  Minimum reactive power output (not used in this version)                                                                          MW
MaximumCharge         Maximum consumption/charge when the ESS unit is storing energy                                                                    MW
MinimumCharge         Minimum consumption/charge when the ESS unit is storing energy                                                                    MW
InitialStorage        Initial energy stored at the first instant of the time scope                                                                      GWh
MaximumStorage        Maximum energy that can be stored by the ESS unit                                                                                 GWh
MinimumStorage        Minimum energy that can be stored by the ESS unit                                                                                 GWh
Efficiency            Round-trip efficiency of the pump/turbine cycle of a pumped-hydro storage power plant or charge/discharge of a battery            p.u.
ProductionFunction    Production function from water inflows to energy (only used for hydropower plants modeled with water units and basin topology)    kWh/m\ :sup:`3`
ProductionFunctionH2  Production function from energy to hydrogen (only used for electrolyzers)                                                         kWh/kgH2
Availability          Unit availability for area adequacy reserve margin (also called de-rating factor or capacity credit)                              p.u.
Inertia               Unit inertia constant                                                                                                             s
EFOR                  Equivalent Forced Outage Rate                                                                                                     p.u.
RampUp                Ramp up   rate for generating units or maximum discharge rate for ESS discharge                                                   MW/h
RampDown              Ramp down rate for generating units or maximum    charge rate for ESS    charge                                                   MW/h
UpTime                Minimum uptime                                                                                                                    h
DownTime              Minimum downtime                                                                                                                  h
ShiftTime             Maximum shift time                                                                                                                h
FuelCost              Fuel cost                                                                                                                         €/Mcal
LinearTerm            Linear term (slope) of the heat rate straight line                                                                                Mcal/MWh
ConstantTerm          Constant term (intercept) of the heat rate straight line                                                                          Mcal/h
OMVariableCost        Variable O&M cost                                                                                                                 €/MWh
OperReserveCost       Operating reserve cost                                                                                                            €/MW
StartUpCost           Startup  cost                                                                                                                     M€
ShutDownCost          Shutdown cost                                                                                                                     M€
CO2EmissionRate       CO2 emission rate. It can be negative for units absorbing CO2 emissions as biomass                                                tCO2/MWh
FixedInvestmentCost   Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                                   M€
FixedRetirementCost   Overnight retirement (capital -CAPEX- and fixed O&M -FOM-) cost                                                                   M€
FixedChargeRate       Fixed-charge rate to annualize the overnight investment cost                                                                      p.u.
StorageInvestment     Storage capacity and energy inflows linked to the investment decision                                                             Yes/No
BinaryInvestment      Binary unit investment decision                                                                                                   Yes/No
InvestmentLo          Lower bound of investment decision                                                                                                p.u.
InvestmentUp          Upper bound of investment decision                                                                                                p.u.
BinaryRetirement      Binary unit retirement decision                                                                                                   Yes/No
RetirementLo          Lower bound of retirement decision                                                                                                p.u.
RetirementUp          Upper bound of retirement decision                                                                                                p.u.
====================  ================================================================================================================================  ===================================

The model allways considers a month of 672 hours, i.e., 4 weeks, not calendar months. The model considers a year of 8736 hours, i.e., 52 weeks, not calendar years.

Daily *storage type* means that the ESS inventory is assessed every time step, for daily storage type it is assessed at the end of every hour, for weekly storage type it is assessed at the end of every day, monthly storage type is assessed at the end of every week, and yearly storage type is assessed at the end of every month.
*Outflows type* represents the interval when the energy extracted from the storage must be satisfied (for daily outflows type at the end of every day, i.e., the sum of the energy consumed must be equal to the sum of outflows for every day).
*Energy type* represents the interval when the minimum or maximum energy to be produced by a unit must be satisfied (for daily energy type at the end of every day, i.e., the sum of the energy generated by the unit must be lower/greater to the sum of max/min energy for every day).
The *storage cycle* is the minimum between the inventory assessment period (defined by the storage type), the outflows period (defined by the outflows type), and the energy period (defined by the energy type) (only if outflows or energy power values have been introduced).
It can be one time step, one day, one week, and one month, but it can't exceed the stage duration. For example, if the stage lasts for 168 hours the storage cycle can only be hourly or daily.
The ESS inventory level at the end of a larger storage cycle is fixed to its initial value, i.e., the inventory of a daily storage type (evaluated on a time step basis) is fixed at the end of the week,
the inventory of weekly storage is fixed at the end of the month, the inventory of monthly storage is fixed at the end of the year, only if the initial inventory lies between the storage limits.

The initial storage of the ESSs is also fixed at the beginning and end of each stage, only if the initial inventory lies between the storage limits. For example, the initial storage level is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

A generator with operation cost (sum of the fuel and emission cost, excluding O&M cost) > 0 is considered a non-renewable unit. If the unit has no operation cost and its maximum storage = 0,
it is considered a renewable unit. If its maximum storage is > 0, with or without operation cost, is considered an ESS.

Must-run non-renewable units are always committed, i.e., their commitment decision is equal to 1. All must-run units are forced to produce at least their minimum output.

EFOR is used to reduce the maximum and minimum power of the unit. For hydropower plants it can be used to reduce their maximum power by the water head effect. It does not reduce the maximum charge.

Those generators or ESS with fixed cost > 0 are considered candidate and can be installed or not.

Maximum and minimum storage is considered proportional to the invested capacity for the candidate ESS units if StorageInvestment is activated.

If lower and upper bounds of investment/retirement decisions are very close (with a difference < 1e-3) to 0 or 1 are converted into 0 and 1.

Variable maximum and minimum generation
---------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxGeneration.csv`` and ``oT_Data_VariableMinGeneration.csv`` follows:

==========  ==============  ==========  =========  ============================================================  ==
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  ============================================================  ==
Period      Scenario        Load level  Generator  Maximum (minimum) power generation of the unit by load level  MW
==========  ==============  ==========  =========  ============================================================  ==

This information can be used for considering scheduled outages or weather-dependent operating capacity.

To force a generator to produce 0 a lower value (e.g., 0.1 MW) strictly > 0, but not 0 (in which case the value will be ignored), must be introduced. This is needed to limit the solar production at night, for example.
It can be used also for upper-bounding and/or lower-bounding the output of any generator (e.g., run-of-the-river hydro, wind).

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable maximum and minimum consumption
----------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxConsumption.csv`` and ``oT_Data_VariableMinConsumption.csv`` follows:

==========  ==============  ==========  =========  =============================================================  ==
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =============================================================  ==
Period      Scenario        Load level  Generator  Maximum (minimum) power consumption of the unit by load level  MW
==========  ==============  ==========  =========  =============================================================  ==

To force a ESS to consume 0 a lower value (e.g., 0.1 MW) strictly > 0, but not 0 (in which case the value will be ignored), must be introduced.
It can be used also for upper-bounding and/or lower-bounding the consumption of any ESS (e.g., pumped-hydro storage, battery).

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable fuel cost
------------------

A description of the data included in the file ``oT_Data_VariableFuelCost.csv`` follows:

==========  ==============  ==========  =========  =============================  ======
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =============================  ======
Period      Scenario        Load level  Generator  Variable fuel cost             €/Mcal
==========  ==============  ==========  =========  =============================  ======

All the generators must be defined as columns of these files.

Internally, all the values below 1e-4 will be converted into 0 by the model.

Fuel cost affects the linear and constant terms of the heat rate, expressed in Mcal/MWh and Mcal/h respectively.

Variable emission cost
----------------------

A description of the data included in the file ``oT_Data_VariableEmissionCost.csv`` follows:

==========  ==============  ==========  =========  =============================  ======
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =============================  ======
Period      Scenario        Load level  Generator  Variable emission cost         €/tCO2
==========  ==============  ==========  =========  =============================  ======

All the generators must be defined as columns of these files.

Internally, all the values below 1e-4 will be converted into 0 by the model.

Energy inflows
--------------

A description of the data included in the file ``oT_Data_EnergyInflows.csv`` follows:

==========  ==============  ==========  =========  =============================  =====
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =============================  =====
Period      Scenario        Load level  Generator  Energy inflows by load level   MWh/h
==========  ==============  ==========  =========  =============================  =====

All the generators must be defined as columns of these files.

If you have daily energy inflows data just input the daily amount at the first hour of every day if the ESS have daily or weekly storage capacity.

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Energy inflows are considered proportional to the invested capacity for the candidate ESS units if StorageInvestment is activated.

Energy outflows
---------------

A description of the data included in the file ``oT_Data_EnergyOutflows.csv`` follows:

==========  ==============  ==========  =========  =============================  =====
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =============================  =====
Period      Scenario        Load level  Generator  Energy outflows by load level  MWh/h
==========  ==============  ==========  =========  =============================  =====

All the generators must be defined as columns of these files.

These energy outflows can be used to represent the energy extracted from an ESS to produce H2 from electrolyzers, to move EV or as hydro outflows for irrigation.
The use of these outflows is incompatible with the charge of the ESS within the same time step (as the discharge of a battery is incompatible with the charge in the same hour).

If you have daily/weekly/monthly/yearly outflows data, you can just input the daily/weekly/monthly/yearly amount at the first hour of every day/week/month/year.

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable maximum and minimum storage
------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxStorage.csv`` and ``oT_Data_VariableMinStorage.csv`` follows:

==========  ==============  ==========  =========  ====================================================  ===
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  ====================================================  ===
Period      Scenario        Load level  Generator  Maximum (minimum) storage of the ESS by load level    GWh
==========  ==============  ==========  =========  ====================================================  ===

All the generators must be defined as columns of these files.

For example, these data can be used for defining the operating guide (rule) curves for the ESS.

Variable maximum and minimum energy
-----------------------------------

A description of the data included in the files ``oT_Data_VariableMaxEnergy.csv`` and ``oT_Data_VariableMinEnergy.csv`` follows:

==========  ==============  ==========  =========  ====================================================  ===
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  ====================================================  ===
Period      Scenario        Load level  Generator  Maximum (minimum) energy of the unit by load level    MW
==========  ==============  ==========  =========  ====================================================  ===

All the generators must be defined as columns of these files.

For example, these data can be used for defining the minimum and/or maximum energy to be produced on a daily/weekly/monthly/yearly basis (depending on the EnergyType).

Electricity transmission network
--------------------------------

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_Network.csv`` follows:

===================  ===============================================================================================================  ======
Header               Description
===================  ===============================================================================================================  ======
LineType             Line type {AC, DC, Transformer, Converter}
Switching            The transmission line is able to switch on/off                                                                   Yes/No
InitialPeriod        Initial period (year) when the unit is installed or can be installed, if candidate                               Year
FinalPeriod          Final   period (year) when the unit is installed or can be installed, if candidate                               Year
Voltage              Line voltage (e.g., 400, 220 kV, 220/400 kV if transformer). Used only for plotting purposes                     kV
Length               Line length (only used for reporting purposes). If not defined, computed as 1.1 times the geographical distance  km
LossFactor           Transmission losses equal to the line flow times this factor                                                     p.u.
Resistance           Resistance (not used in this version)                                                                            p.u.
Reactance            Reactance. Lines must have a reactance different from 0 to be considered                                         p.u.
Susceptance          Susceptance (not used in this version)                                                                           p.u.
AngMax               Maximum angle difference (not used in this version)                                                              º
AngMin               Minimum angle difference (not used in this version)                                                              º
Tap                  Tap changer (not used in this version)                                                                           p.u.
Converter            Converter station (not used in this version)                                                                     Yes/No
TTC                  Total transfer capacity (maximum permissible thermal load) in forward  direction. Static line rating             MW
TTCBck               Total transfer capacity (maximum permissible thermal load) in backward direction. Static line rating             MW
SecurityFactor       Security factor to consider approximately N-1 contingencies. NTC = TTC x SecurityFactor                          p.u.
FixedInvestmentCost  Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                  M€
FixedChargeRate      Fixed-charge rate to annualize the overnight investment cost                                                     p.u.
BinaryInvestment     Binary line/circuit investment decision                                                                          Yes/No
InvestmentLo         Lower bound of investment decision                                                                               p.u.
InvestmentUp         Upper bound of investment decision                                                                               p.u.
SwOnTime             Minimum switch-on time                                                                                           h
SwOffTime            Minimum switch-off time                                                                                          h
===================  ===============================================================================================================  ======

Depending on the voltage lines are plotted with different colors (orange < 200 kV, 200 < green < 350 kV, 350 < red < 500 kV, 500 < orange < 700 kV, blue > 700 kV).

If there is no data for TTCBck, i.e., TTCBck is left empty or is equal to 0, it is substituted by the TTC in the code. Internally, all the TTC and TTCBck values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Reactance can take a negative value as a result of the approximation of three-winding transformers. No Kirchhoff's second law disjunctive constraint is formulated for a circuit with negative reactance.

Those lines with fixed cost > 0 are considered candidate and can be installed or not.

If lower and upper bounds of investment decisions are very close (with a difference < 1e-3) to 0 or 1 are converted into 0 and 1.

Node location
-------------

A description of the data included in the file ``oT_Data_NodeLocation.csv`` follows:

==============  ============  ================  ==
Identifier      Header        Description
==============  ============  ================  ==
Node            Latitude      Node latitude     º
Node            Longitude     Node longitude    º
==============  ============  ================  ==

Hydro System Input Data
=======================

These input files are specifically introduced for allowing a representation of the hydro system based on volume and water inflow data considering the water stream topology (hydro cascade basins). If they are not available, the model runs with an energy-based representation of the hydro system.

Dictionaries. Sets
------------------
The dictionaries include all the possible elements of the corresponding sets included in the optimization problem. **You can't use non-English characters (e.g., ó, º)**

=============================  ===============
File                           Description
=============================  ===============
``oT_Dict_Reservoir.csv``      Reservoirs
=============================  ===============

The information contained in these input files determines the topology of the hydro basins and how water flows along the different
hydropower and pumped-hydro power plants and reservoirs. These relations follow the water downstream direction.

=======================================  ======================  ===========================================================================================
File                                     Dictionary              Description
=======================================  ======================  ===========================================================================================
``oT_Dict_ReservoirToHydro.csv``         ReservoirToHydro        Reservoir upstream of hydro power plant (i.e., hydro takes the water from the reservoir)
``oT_Dict_HydroToReservoir.csv``         HydroToReservoir        Hydro power plant upstream of reservoir (i.e., hydro releases the water to the reservoir)
``oT_Dict_ReservoirToPumpedHydro.csv``   ReservoirToPumpedHydro  Reservoir upstream of pumped-hydro power plant (i.e., pump-hydro pumps from the reservoir)
``oT_Dict_PumpedHydroToReservoir.csv``   PumpedHydroToReservoir  Pumped-hydro power plant upstream of reservoir (i.e., pump-hydro pumps to the reservoir)
``oT_Dict_ReservoirToReservoir.csv``     ReservoirToReservoir    Reservoir upstream of reservoir (i.e., reservoir one spills the water to reservoir two)
=======================================  ======================  ===========================================================================================

Hydro inflows
-------------

A description of the data included in the file ``oT_Data_HydroInflows.csv`` follows:

==========  ==============  ==========  =========  ====================================  ==============
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  ====================================  ==============
Period      Scenario        Load level  Reservoir  Natural water inflows by load level   m\ :sup:`3`/s
==========  ==============  ==========  =========  ====================================  ==============

All the reservoirs must be defined as columns of these files.

If you have daily natural hydro inflows data just input the daily amount at the first hour of every day if the reservoir have daily or weekly storage capacity.

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Hydro outflows
--------------

A description of the data included in the file ``oT_Data_HydroOutflows.csv`` follows:

==========  ==============  ==========  =========  ===================================================  =============
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  ===================================================  =============
Period      Scenario        Load level  Reservoir  Water outflows by load level (e.g., for irrigation   m\ :sup:`3`/s
==========  ==============  ==========  =========  ===================================================  =============

All the reservoirs must be defined as columns of these files.

These water outflows can be used to represent the hydro outflows for irrigation.

If you have daily/weekly/monthly/yearly water outflows data, you can just input the daily/weekly/monthly/yearly amount at the first hour of every day/week/month/year.

Internally, all the values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Reservoir
---------

A description of the data included in the file ``oT_Data_Reservoir.csv`` follows:

====================  ======================================================================================================================  ===================================
Header                Description
====================  ======================================================================================================================  ===================================
StorageType           Reservoir storage type based on reservoir storage capacity (hourly, daily, weekly, monthly, yearly)                     Hourly/Daily/Weekly/Monthly/Yearly
OutflowsType          Water outflows type based on the water extracted from the reservoir (daily, weekly, monthly, yearly)                    Daily/Weekly/Monthly/Yearly
InitialStorage        Initial volume stored at the first instant of the time scope                                                            hm\ :sup:`3`
MaximumStorage        Maximum volume that can be stored by the hydro reservoir                                                                hm\ :sup:`3`
MinimumStorage        Minimum volume that can be stored by the hydro reservoir                                                                hm\ :sup:`3`
BinaryInvestment      Binary reservoir investment decision                                                                                    Yes/No
FixedInvestmentCost   Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                         M€
FixedChargeRate       Fixed-charge rate to annualize the overnight investment cost                                                            p.u.
InitialPeriod         Initial period (year) when the unit is installed or can be installed, if candidate                                      Year
FinalPeriod           Final   period (year) when the unit is installed or can be installed, if candidate                                      Year
====================  ======================================================================================================================  ===================================

The model allways considers a month of 672 hours, i.e., 4 weeks, not calendar months. The model considers a year of 8736 hours, i.e., 52 weeks, not calendar years.

Daily *storage type* means that the ESS inventory is assessed every time step, for weekly storage type it is assessed at the end of every day, monthly storage type is assessed at the end of every week, and yearly storage type is assessed at the end of every month.
*Outflows type* represents the interval when the water extracted from the reservoir must be satisfied (for daily outflows type at the end of every day, i.e., the sum of the water consumed must be equal to the sum of water outflows for every day).
The *storage cycle* is the minimum between the inventory assessment period (defined by the storage type), the outflows period (defined by the outflows type), and the energy period (defined by the energy type) (only if outflows or energy power values have been introduced).
It can be one time step, one day, one week, and one month, but it can't exceed the stage duration. For example, if the stage lasts for 168 hours the storage cycle can only be hourly or daily.
The reservoir volume level at the end of a larger storage cycle is fixed to its initial value, i.e., the volume of a daily storage type (evaluated on a time step basis) is fixed at the end of the week,
the volume of weekly storage is fixed at the end of the month, the volume of monthly storage is fixed at the end of the year, only if the initial inventory lies between the storage limits.

The initial reservoir volume is also fixed at the beginning and end of each stage, only if the initial volume lies between the reservoir storage limits. For example, the initial volume is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

Variable maximum and minimum reservoir volume
---------------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxVolume.csv`` and ``oT_Data_VariableMinVolume.csv`` follows:

==========  ==============  ==========  =========  =================================================  ==============
Identifier  Identifier      Identifier  Header     Description
==========  ==============  ==========  =========  =================================================  ==============
Period      Scenario        Load level  Reservoir  Maximum (minimum) reservoir volume by load level   hm\ :sup:`3`
==========  ==============  ==========  =========  =================================================  ==============

All the reservoirs must be defined as columns of these files.

For example, these data can be used for defining the operating guide (rule) curves for the hydro reservoirs.

Hydrogen System Input Data
==========================

These input files are specifically introduced for allowing a representation of the hydrogen energy vector to supply hydrogen demand produced with electricity through the hydrogen network.

=========================================  ================================================================================================================================
File                                       Description
=========================================  ================================================================================================================================
``oT_Data_DemandHydrogen.csv``             Hydrogen demand
``oT_Data_NetworkHydrogen.csv``            Hydrogen pipeline network data
=========================================  ================================================================================================================================

Hydrogen demand
---------------

A description of the data included in the file ``oT_Data_DemandHydrogen.csv`` follows:

==========  ==============  ==========  ======  ===============================================  =====
Identifier  Identifier      Identifier  Header  Description
==========  ==============  ==========  ======  ===============================================  =====
Period      Scenario        Load level  Node    Hydrogen demand of the node for each load level  tH2/h
==========  ==============  ==========  ======  ===============================================  =====

Internally, all the values below if positive demand (or above if negative demand) 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Hydrogen transmission pipeline network
--------------------------------------

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_NetworkHydrogen.csv`` follows:

===================  ===================================================================================================================  ======
Header               Description
===================  ===================================================================================================================  ======
InitialPeriod        Initial period (year) when the unit is installed or can be installed, if candidate                                   Year
FinalPeriod          Final   period (year) when the unit is installed or can be installed, if candidate                                   Year
Length               Pipeline length (only used for reporting purposes). If not defined, computed as 1.1 times the geographical distance  km
TTC                  Total transfer capacity (maximum permissible thermal load) in forward  direction. Static pipeline rating             tH2
TTCBck               Total transfer capacity (maximum permissible thermal load) in backward direction. Static pipeline rating             tH2
SecurityFactor       Security factor to consider approximately N-1 contingencies. NTC = TTC x SecurityFactor                              p.u.
FixedInvestmentCost  Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                      M€
FixedChargeRate      Fixed-charge rate to annualize the overnight investment cost                                                         p.u.
BinaryInvestment     Binary pipeline investment decision                                                                                  Yes/No
InvestmentLo         Lower bound of investment decision                                                                                   p.u.
InvestmentUp         Upper bound of investment decision                                                                                   p.u.
===================  ===================================================================================================================  ======

If there is no data for TTCBck, i.e., TTCBck is left empty or is equal to 0, it is substituted by the TTC in the code. Internally, all the TTC and TTCBck values below 2.5e-5 times the maximum system demand of each area will be converted into 0 by the model.

Those pipelines with fixed cost > 0 are considered candidate and can be installed or not.

If lower and upper bounds of investment decisions are very close (with a difference < 1e-3) to 0 or 1 are converted into 0 and 1.
