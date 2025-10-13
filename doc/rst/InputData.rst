.. openTEPES documentation master file, created by Andres Ramos

Electric System Input Data
==========================

All the input files must be in a folder with the name of the case study.

Acronyms
--------

==========  ================================================================================================================================================================================================================================================
Acronym     Description
==========  ================================================================================================================================================================================================================================================
AC          Alternating Current
aFRR        Automatic Frequency Restoration Reserve (also secondary reserve) reserve provided within 5 minutes (Full Activation Time)
AWE         Alkaline Water Electrolyzer (consumes electricity to produce hydrogen)
BESS        Battery Energy Storage System
CC          Capacity Credit (contribution of a power generation resource—particularly variable renewable energy (VRE) like wind or solar—to meeting peak demand)
CCGT        Combined Cycle Gas Turbine
CHP         Combined Heat and Power. Cogeneration (produces electricity and heat simultaneously)
DC          Direct Current
DCPF        DC Optimal Power Flow
DR          Demand Response
DSM         Demand-Side Management (e.g., load shifting)
DSR         Demand-Side Response (e.g., interruptibility)
EB          Electric Boiler (Power to Heat: consumes electricity to produce heat)
EHU         Electrical Heating Unit (Power to Heat: consumes electricity to produce heat, e.g., heat pump, electric boiler)
EFOR        Equivalent Forced Outage Rate (probability that a generating unit will be unavailable due to forced outages during a given period)
ELCC        Effective Load-Carrying Capability. Amount of additional load that the power system can serve with the inclusion of the resource, while maintaining the same level of system reliability
ELZ         Electrolyzer (Power to Hydrogen: consumes electricity to produce hydrogen)
ENS         Energy Not Served
ENTSO-E     European Network of Transmission System Operators for Electricity
ESS         Energy Storage System
EV          Electric Vehicle
FCE         Firm Capacity Equivalent (amount of reliable, always-available generation capacity that would provide the same level of system reliability as the resource being evaluated)
FHU         Fuel Heating Unit (Fuel to Heat: consumes any fuel other than hydrogen to produce heat, e.g., biomass/natural gas/oil boiler)
GEP         Generation Expansion Planning
mFRR        Manual Frequency Restoration Reserve (also tertiary reserve) helps to restore the required grid frequency of 50 Hz. It must be fully deployable after 12.5 minutes and has a minimum duration period of 5 minutes
H2          Hydrogen
HHU         Hydrogen Heating unit (Hydrogen to Heat: consumes hydrogen to produce heat)
HNS         Hydrogen Not Served
HP          Heat Pump (Power to Heat: consumes electricity to produce heat)
HTNS        Heat Not Served
IRP         Integrated Resource Planning
NTC         Net Transfer Capacity (maximum power transfer between two nodes, zones, areas, or regions, considering the network constraints)
OCGT        Open Cycle Gas Turbine
PHS         Pumped-Hydro Storage
PNS         Power Not Served
PTDF        Power Transfer Distribution Factor (ratio of the change in flow on a transmission line to the change in power injection at a node)
PV          Photovoltaics
RES         Renewable Energy Source
SEP         Storage Expansion Planning
TEP         Transmission Expansion Planning
TTC         Total Transfer Capacity (maximum amount of electric power that can be transferred over the transmission network between two areas under ideal operating conditions, while maintaining system security as defined by operational standards)
VoLL        Value of Lost Load (maximum amount of money that a customer is willing to pay to avoid an interruption of 1 kWh of electricity supply). Common values are between 1000 and 10000 €/MWh
VRE         Variable Renewable Energy
VRES        Variable Renewable Energy Source (units with null linear variable cost and no storage capacity. Do not contribute to the operating reserves)
==========  ================================================================================================================================================================================================================================================

Dictionaries. Sets
------------------
The dictionaries include all the possible elements of the corresponding sets in the optimization problem. **You can't use non-English characters (e.g., ó, º)**

=============================  =========================================================================================================================================================================================================================================================================================================================
File                           Description
=============================  =========================================================================================================================================================================================================================================================================================================================
``oT_Dict_Period.csv``         Period (e.g., 2030, 2035). **It must be a positive integer**
``oT_Dict_Scenario.csv``       Scenario. Short-term uncertainties (scenarios) (e.g., s001 to s100, CY2025 to CY2030)
``oT_Dict_Stage.csv``          Stage
``oT_Dict_LoadLevel.csv``      Load level (e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00). If is a datetime format. Load levels with duration 0 are ignored. 8736 load levels must represent the period (year).
``oT_Dict_Generation.csv``     Generation units (thermal -nuclear, CCGT, OCGT, coal-, ESS -storage hydro modeled in energy or water, pumped-hydro storage PHS, battery BESS, electric vehicle EV, demand side management DSM, alkaline water electrolyzer AWE, solar thermal- and VRES -wind onshore and offshore, solar PV, run-of-the-river hydro-)
``oT_Dict_Technology.csv``     Generation technologies. The technology order is used in the temporal result plot.
``oT_Dict_Storage.csv``        ESS storage type (daily <12 h, weekly <40 h, monthly >60 h).
``oT_Dict_Node.csv``           Nodes. A node belongs to a defined zone. All the nodes must have a different name.
``oT_Dict_Zone.csv``           Zones. A zone belongs to a defined area. All the zones must have a different name.
``oT_Dict_Area.csv``           Areas. An area belongs to a defined region. All the areas must have a different name. Long-term adequacy, inertia, and operating reserves are associated with areas.
``oT_Dict_Region.csv``         Regions
``oT_Dict_Circuit.csv``        Circuits (e.g., ac1, ac2 for AC lines, dc1 for DC lines). All the circuits must have a different name.
``oT_Dict_Line.csv``           Line type (AC, DC)
=============================  =========================================================================================================================================================================================================================================================================================================================

Assignment of nodes to zones, zones to areas, and areas to regions.

============================  ============  ==============================
File                          Dictionary    Description
============================  ============  ==============================
``oT_Dict_NodeToZone.csv``    NodeToZone    Assignment of nodes at zones
``oT_Dict_ZoneToArea.csv``    ZoneToArea    Assignment of zones at areas
``oT_Dict_AreaToRegion.csv``  AreaToRegion  Assignment of areas at regions
============================  ============  ==============================

See the hydropower system section at the end of this page to learn how to define the basin topology (connection among reservoirs and hydropower plants). Some additional dictionaries and data files are needed.

Input files
-----------
This is the list of the input data files and their brief description.

=========================================  ==================================================================================================================================================================================
File                                       Description
=========================================  ==================================================================================================================================================================================
``oT_Data_Option.csv``                     Options of use of the **openTEPES** model
``oT_Data_Parameter.csv``                  General system parameters
``oT_Data_Period.csv``                     Weight of each period
``oT_Data_Scenario.csv``                   Short-term uncertainties
``oT_Data_Stage.csv``                      Weight of each stage
``oT_Data_ReserveMargin.csv``              Minimum adequacy reserve margin for each area and period
``oT_Data_Emission.csv``                   Maximum CO2 emissions of the electric system
``oT_Data_RESEnergy.csv``                  Minimum RES energy
``oT_Data_Duration.csv``                   Duration of the load levels
``oT_Data_Demand.csv``                     Electricity demand
``oT_Data_Inertia.csv``                    System inertia by area
``oT_Data_OperatingReserveUp.csv``         Upward   operating reserves (include aFRR and mFRR for electricity balancing from ENTSO-E)
``oT_Data_OperatingReserveDown.csv``       Downward operating reserves (include aFRR and mFRR for electricity balancing from ENTSO-E)
``oT_Data_Generation.csv``                 Generation (electricity and heat) data
``oT_Data_VariableMaxGeneration.csv``      Variable maximum power generation  by load level
``oT_Data_VariableMinGeneration.csv``      Variable minimum power generation  by load level
``oT_Data_VariableMaxConsumption.csv``     Variable maximum power consumption by load level
``oT_Data_VariableMinConsumption.csv``     Variable minimum power consumption by load level
``oT_Data_VariableFuelCost.csv``           Variable fuel cost by load level
``oT_Data_EnergyInflows.csv``              Energy inflows into an ESS by load level
``oT_Data_EnergyOutflows.csv``             Energy outflows from an ESS for Power-to-X (H2 production, EV mobility, heat production, or water irrigation) by load level
``oT_Data_VariableMaxStorage.csv``         Maximum amount of energy stored in the ESS (defined per load level)
``oT_Data_VariableMinStorage.csv``         Minimum amount of energy stored in the ESS (defined per load level)
``oT_Data_VariableMaxEnergy.csv``          Maximum amount of energy produced/consumed by the unit by time interval (the amount of energy considered corresponds to the aggregate over the interval defined by EnergyType)
``oT_Data_VariableMinEnergy.csv``          Minimum amount of energy produced/consumed by the unit by time interval (the amount of energy considered corresponds to the aggregate over the interval defined by EnergyType)
``oT_Data_Network.csv``                    Electricity network data
``oT_Data_VariableTTCFrw.csv``             Maximum electric transmission line TTC forward  flow (defined per load level) (optional file)
``oT_Data_VariableTTCBck.csv``             Maximum electric transmission line TTC backward flow (defined per load level) (optional file)
``oT_Data_NodeLocation.csv``               Node location in latitude and longitude
=========================================  ==================================================================================================================================================================================

Only the columns indicated in this document will be read in any input file. For example, you can add a column for comments or additional information as needed, but the model will not read it.

Options
----------
A description of the options included in the file ``oT_Data_Option.csv`` follows:

===================  ==================================================================   ====================================================
Item                 Description
===================  ==================================================================   ====================================================
IndBinGenInvest      Indicator of binary generation   expansion decisions                 {0 continuous, 1 binary, 2 ignore investments}
IndBinGenRetirement  Indicator of binary generation  retirement decisions                 {0 continuous, 1 binary, 2 ignore retirements}
IndBinRsrInvest      Indicator of binary reservoir    expansion decisions
                     (only used for reservoirs modeled with water units)                  {0 continuous, 1 binary, 2 ignore investments}
IndBinNetInvest      Indicator of binary electricity network expansion decisions          {0 continuous, 1 binary, 2 ignore investments}
IndBinNetH2Invest    Indicator of binary hydrogen network expansion decisions             {0 continuous, 1 binary, 2 ignore investments}
IndBinNetHeatInvest  Indicator of binary heat     network expansion decisions             {0 continuous, 1 binary, 2 ignore investments}
IndBinGenOperat      Indicator of binary generation   operation decisions                 {0 continuous, 1 binary}
IndBinGenRamps       Indicator of considering or not the up/down ramp constraints         {0 no ramps,   1 ramp constraints}
IndBinGenMinTime     Indicator of considering or not the min up/down time constraints     {0 no min time constraints, 1 min time constraints}
IndBinSingleNode     Indicator of single node case study                                  {0 network,    1 single node}
IndBinLineCommit     Indicator of binary transmission switching decisions                 {0 continuous, 1 binary}
IndBinNetLosses      Indicator of network losses                                          {0 lossless,   1 ohmic losses}
===================  ==================================================================   ====================================================

Suppose the investment decisions are ignored (IndBinGenInvest, IndBinGenRetirement, and IndBinNetInvest take value 2) or there are no investment decisions. In that case, all the scenarios with a probability >0 are solved sequentially (assuming a probability of 1), and the periods are considered with a weight of 1.

Parameters
----------
A description of the system parameters included in the file ``oT_Data_Parameter.csv`` follows:

====================  =============================================================================================================  =========
Item                  Description
====================  =============================================================================================================  =========
ENSCost               Cost of energy not served (ENS). Cost of load curtailment. Value of Lost Load (VoLL)                           €/MWh
HNSCost               Cost of hydrogen not served (HNS)                                                                              €/kgH2
HTNSCost              Cost of heat not served (HTNS)                                                                                 €/MWh
PNSCost               Cost of power not served (PNS) associated with the deficit in operating reserve by load level                  €/MW
CO2Cost               Cost of CO2 emissions                                                                                          €/tCO2
UpReserveActivation   Upward   reserve activation (proportion of upward   operating reserve deployed to produce energy, e.g., 0.3)   p.u.
DwReserveActivation   Downward reserve activation (proportion of downward operating reserve deployed to produce energy, e.g., 0.25)  p.u.
MinRatioDwUp          Minimum ratio downward to upward operating reserves                                                            p.u.
MaxRatioDwUp          Maximum ratio downward to upward operating reserves                                                            p.u.
Sbase                 Base power used in the DCPF                                                                                    MW
ReferenceNode         Reference node used in the DCPF
TimeStep              Duration of the time step for the load levels (hourly, bi-hourly, tri-hourly, etc.)                             h
EconomicBaseYear      Base year for economic parameters affected by the discount rate                                                year
AnnualDiscountRate    Annual discount rate                                                                                           p.u.
====================  =============================================================================================================  =========

A time step greater than one hour is a convenient way to reduce the load levels of the time scope. The moving average of the demand, upward/downward operating reserves, variable generation/consumption/storage, and ESS energy inflows/outflows
over the time step load levels is assigned to active load levels (e.g., the mean value of the three hours is associated with the third hour in a trihourly time step).

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
Identifiers                     Header        Description
==============================  ============  ===========================================  ====
Period          Scenario        Probability   Probability of each scenario in each period  p.u.
==============  ==============  ============  ===========================================  ====

For example, the scenarios can be used for obtaining the IRP (GEP+SEP+TEP) considering hydro energy/water inflows uncertainty represented using three scenarios (wet, dry, and average), or two VRES scenarios (windy/cloudy and calm/sunny).
The sum of the probabilities of all the period scenarios must be 1.

Stage
-----

A description of the data included in the file ``oT_Data_Stage.csv`` follows:

==============  ============  =====================
Identifier      Header        Description
==============  ============  =====================
Scenario        Weight        Weight of each stage
==============  ============  =====================

This weight defines equivalent (representative) periods (e.g., one representative week weighing 52 or four representative weeks, each weighing 13).
Stages are not mathematically connected, i.e., no constraints link the operation at different consecutive stages. Therefore, the storage type can't exceed the duration of the stage (i.e., if the stage lasts for 168 hours, the storage type can only be hourly or daily).
If there are no investment decisions or the investment decisions are ignored, all the periods, scenarios, and stages are solved independently.

Adequacy reserve margin
-----------------------

The adequacy reserve margin is the ratio between the available capacity and the maximum demand.
According to ENTSO-E, adequacy is defined as the ability of the electric system to supply the aggregate electrical demand and energy requirements of the customers at all times,
taking into account scheduled and reasonably expected unscheduled outages of system elements.
To determine the available capacity, the model uses the availability of the generating units times their maximum power. The availability can be computed as the ratio between the firm and installed capacity. Firm capacity
can be determined as the Firm Capacity Equivalent (FCE) or the Effective Load-Carrying Capability (ELCC).
A description of the data included in the file ``oT_Data_ReserveMargin.csv`` follows:

==============  ==============  =============  ==========================================================  ====
Identifiers                     Header         Description
==============================  =============  ==========================================================  ====
Period          Area            ReserveMargin  Minimum adequacy reserve margin for each period and area    p.u.
==============  ==============  =============  ==========================================================  ====

This parameter is only used for system generation expansion, not for system operation. If no value is introduced for an area, the reserve margin is considered 0.

Maximum CO2 emissions
---------------------

A description of the data included in the file ``oT_Data_Emission.csv`` follows:

==============  ==============  =============  ======================================================================  =====
Identifiers                     Header         Description
==============================  =============  ======================================================================  =====
Period          Area            CO2Emission    Maximum CO2 emissions of the electric system for each period and area   MtCO2
==============  ==============  =============  ======================================================================  =====

If no value is introduced for an area, the CO2 emission limit is considered infinite.

Minimum RES energy
------------------

It is like a Renewable Portfolio Standard (RPS).
A description of the data included in the file ``oT_Data_RESEnergy.csv`` follows:

==============  ==============  =============  ===========================================================  =====
Identifiers                     Header         Description
==============================  =============  ===========================================================  =====
Period          Area            RESEnergy      Minimum RES energy for each period and area                  GWh
==============  ==============  =============  ===========================================================  =====

If no value is introduced for an area, the RES energy limit is considered 0.

Duration
--------

A description of the data included in the file ``oT_Data_Duration.csv`` follows:

==========  ==============  ========== ==========  ===================================================================  ========
Identifiers                            Header      Description
====================================== ==========  ===================================================================  ========
Period      Scenario        LoadLevel  Duration    Duration of the load level. Load levels with duration 0 are ignored  h
                                       Stage       Assignment of the load level to a stage
==========  ==============  ========== ==========  ===================================================================  ========

It is a simple way to use isolated snapshots, representative days, or just the first three months instead of all the hours of a year to simplify the optimization problem. All the load levels must have the same duration.
The duration is not intended to change for several load levels of a stage. Usually, duration is 1 hour or 0 if you do not want to use the load levels after some hours of the year. The parameter time step must be used to collapse consecutive load levels into one for the optimization problem.

The stage duration, as the sum of the duration of all the load levels, must be larger than or equal to the shortest duration of any storage type, any outflow type, or any energy type (all given in the generation data), and a multiple of it.
Consecutive stages are not connected, i.e., no constraints link the operation at different stages. Consequently, the storage type can't exceed the duration of the stage (i.e., if the stage lasts for 168 hours, the storage type can only be hourly or daily).
Consequently, the objective function with several stages must be a bit higher than in the case of a single stage.

The initial storage of the ESSs is also fixed at the beginning and end of each stage. For example, the initial storage level is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

Electricity demand
------------------

A description of the data included in the file ``oT_Data_Demand.csv`` follows:

==========  ==============  ==========  ======  ============================================  ==
Identifiers                             Header  Description
======================================  ======  ============================================  ==
Period      Scenario        LoadLevel   Node    Power demand of the node for each load level  MW
==========  ==============  ==========  ======  ============================================  ==

The electricity demand can be negative for the (transmission) nodes with (renewable) generation at lower voltage levels. This negative demand is equivalent to generating that power amount in this node.
Internally, if positive demand (or above if negative demand) 1e-5 times the maximum system demand of each area, all the values below will be converted into 0 by the model.

System inertia
--------------

A description of the data included in the files ``oT_Data_Inertia.csv`` follows:

==========  ==============  ==========  ======  ================================================  ==
Identifiers                             Header  Description
======================================  ======  ================================================  ==
Period      Scenario        LoadLevel   Area    System inertia of the area for each load level    s
==========  ==============  ==========  ======  ================================================  ==

Given that the system inertia depends on the area, assigning an area as a country can be sensible. The system inertia can impose a minimum synchronous power and, consequently, force the commitment of at least some rotating units.
Each generating unit can contribute to the system inertia. The system inertia is the sum of the inertia of all the committed units in the area.

Internally, all the values below 1e-5 times the maximum system electricity demand of each area will be converted to 0 by the model.

Upward and downward operating reserves
--------------------------------------

A description of the data included in the files ``oT_Data_OperatingReserveUp.csv`` and ``oT_Data_OperatingReserveDown.csv`` follows:

==========  ==============  ==========  ======  ===================================================================  ==
Identifiers                                     Header  Description
======================================  ======  ===================================================================  ==
Period      Scenario        LoadLevel   Area    Upward/downward operating reserves of the area for each load level   MW
==========  ==============  ==========  ======  ===================================================================  ==

Given that the operating reserves depend on the area, assigning an area to a country can be sensible.
These operating reserves must include Automatic Frequency Restoration Reserves (aFRR) and Manual Frequency Restoration Reserves (mFRR) for electricity balancing from ENTSO-E.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Generation
----------
A description of the data included for each (electricity and heat) generating unit in the file ``oT_Data_Generation.csv`` follows:

==========================  ============================================================================================================================================================================================  ===================================
Header                      Description
==========================  ============================================================================================================================================================================================  ===================================
Generator                   Name of the generator. Each generator must have a unique name.
Node                        Name of the node where the generator is located. If left empty, the generator is ignored
Technology                  Technology of the generator (nuclear, coal, CCGT, OCGT, ESS, solar, wind, biomass, etc.)
MutuallyExclusive           List of mutually exclusive sets to which the generator belongs. Only one generator per set can be committed simultaneously. It is computationally demanding.
BinaryCommitment            Binary unit commitment decision                                                                                                                                                               Yes/No
NoOperatingReserve          No contribution to operating reserve. Yes, if the unit doesn't contribute to the operating reserve                                                                                            Yes/No
OutflowsIncompatibility     Outflows are incompatible with the charging process (e.g., electric vehicle). This is not the case of an electrolyzer                                                                         Yes/No
StorageType                 Represents the time period (hour, day, week, month, year) over which the requirement that aggregate electricity production must equal aggregate consumption is enforced                       Hourly/Daily/Weekly/Monthly/Yearly
OutflowsType                Represents the time period (hour, day, week, month, year) over which the specified amount of energy must be consumed/withdrawn from the storage unit                                          Hourly/Daily/Weekly/Monthly/Yearly
EnergyType                  Represents the time period (hour, day, week, month, year) over which the specified max/min amount of energy is to be produced by the unit                                                     Hourly/Daily/Weekly/Monthly/Yearly
MustRun                     Must-run unit                                                                                                                                                                                 Yes/No
InitialPeriod               Initial period (year) when the unit is installed or can be installed, if it is a candidate                                                                                                    Year
FinalPeriod                 Final   period (year) when the unit is installed or can be installed, if it is a candidate                                                                                                    Year
MaximumPower                Maximum power output of electricity (generation/discharge for ESS units)                                                                                                                      MW
MinimumPower                Minimum power output of electricity (i.e., minimum stable load in the case of a thermal power plant)                                                                                          MW
MaximumPowerHeat            Maximum heat output (heat produced by a CHP, at its maximum electric power, or by a fuel heater, which do not produce electric power)                                                         MW
MinimumPowerHeat            Minimum heat output (heat produced by a CHP, at its minimum electric power, or by a fuel heater, which do not produce electric power)                                                         MW
MaximumReactivePower        Maximum reactive power output (discharge for ESS units) (not used in this version)                                                                                                            MW
MinimumReactivePower        Minimum reactive power output (not used in this version)                                                                                                                                      MW
MaximumCharge               Maximum consumption/charge level when the ESS unit is storing energy                                                                                                                          MW
MinimumCharge               Minimum consumption/charge level when the ESS unit is storing energy                                                                                                                          MW
InitialStorage              Initial amount of energy stored at the first instant of the time scope                                                                                                                        GWh
MaximumStorage              Maximum amount of energy that can be stored by the ESS unit                                                                                                                                   GWh
MinimumStorage              Minimum amount of energy that can be stored by the ESS unit                                                                                                                                   GWh
Efficiency                  Round-trip efficiency of the pump/turbine cycle of a pumped-hydro storage power plant or charge/discharge of a battery                                                                        p.u.
ProductionFunctionHydro     Production function from water inflows (denominator) to electricity (numerator) (only used for hydropower plants modeled with water units and basin topology)                                 kWh/m\ :sup:`3`
ProductionFunctionH2        Production function from electricity (numerator) to hydrogen (denominator) (only used for electrolyzers)                                                                                      kWh/kgH2
ProductionFunctionHeat      Production function from electricity (numerator) to heat (denominator) (only used for heat pumps or electric boilers)                                                                         kWh/kWh
ProductionFunctionH2ToHeat  Production function from hydrogen (numerator) to heat (denominator) (only used for hydrogen heater, which produces heat by burning hydrogen)                                                  kgH2/kWh
Availability                Unit availability for area adequacy reserve margin (also called de-rating factor or capacity credit (CC) or Firm Capacity Equivalent (FCE) or the Effective Load-Carrying Capability (ELCC))  p.u.
Inertia                     Unit inertia constant                                                                                                                                                                         s
EFOR                        Equivalent Forced Outage Rate                                                                                                                                                                 p.u.
RampUp                      Maximum rate of increasing its output for generating units, or maximum rate of increasing its discharge rate or decreasing its charge rate for ESS units                                      MW/h
RampDown                    Maximum rate of decreasing its output for generating units, or maximum rate of increasing its charge rate or decreasing its discharge rate for ESS units                                      MW/h
UpTime                      Minimum uptime                                                                                                                                                                                h
DownTime                    Minimum downtime                                                                                                                                                                              h
StableTime                  Minimum stable time (intended for nuclear units to be at their minimum load, if lower than the rated capacity, during this time).
                            Power variations (ramp up/ramp down) below 1% are not considered for activating the minimum stable time                                                                                       h
ShiftTime                   Maximum shift time                                                                                                                                                                            h
FuelCost                    Fuel cost                                                                                                                                                                                     €/GJ
LinearTerm                  Linear   term (slope)     of the heat rate straight line                                                                                                                                      GJ/MWh
ConstantTerm                Constant term (intercept) of the heat rate straight line                                                                                                                                      GJ/h
OMVariableCost              Variable O&M cost                                                                                                                                                                             €/MWh
OperReserveCost             Operating reserve cost                                                                                                                                                                        €/MW
StartUpCost                 Startup  cost                                                                                                                                                                                 M€
ShutDownCost                Shutdown cost                                                                                                                                                                                 M€
CO2EmissionRate             CO2 emission rate. It can be negative for units absorbing CO2 emissions as biomass                                                                                                            tCO2/MWh
FixedInvestmentCost         Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                                                                                               M€
FixedRetirementCost         Overnight retirement (capital -CAPEX- and fixed O&M -FOM-) cost                                                                                                                               M€
FixedChargeRate             Fixed-charge rate to annualize the overnight investment cost. Proportion of annual payment to return the overnight investment cost                                                            p.u.
StorageInvestment           Storage capacity and energy inflows linked to the investment decision                                                                                                                         Yes/No
BinaryInvestment            Binary unit investment decision                                                                                                                                                               Yes/No
InvestmentLo                Lower bound of investment decision                                                                                                                                                            p.u.
InvestmentUp                Upper bound of investment decision                                                                                                                                                            p.u.
BinaryRetirement            Binary unit retirement decision                                                                                                                                                               Yes/No
RetirementLo                Lower bound of retirement decision                                                                                                                                                            p.u.
RetirementUp                Upper bound of retirement decision                                                                                                                                                            p.u.
==========================  ============================================================================================================================================================================================  ===================================

The main characteristics that define each type of generator are the following:

======================================  ===================================================================================================================================  ==========
Generator type                          Description                                                                                                                          Set name
======================================  ===================================================================================================================================  ==========
Generator                               It has MaximumPower or MaximumCharge or MaximumPowerHeat >0                                                                          *g*
Thermal                                 Fuel-based variable cost (fuel cost x linear term + CO2 emission cost) >0                                                            *t*
VRE                                     Fuel-based variable cost (fuel cost x linear term + CO2 emission cost) =0  and MaximumStorage =0.  It may have OMVariableCost >0     *re*
Non-renewable                           All the generators except the RESS                                                                                                   *nr*
ESS                                     It has MaximumCharge or MaximumStorage >0  or ProductionFunctionH2 or ProductionFunctionHeat >0  and ProductionFunctionHydro =0      *es*
Hydro power plant (energy)              ESS with ProductionFunctionHydro =0                                                                                                  *es*
Pumped-hydro storage (energy)           ESS with MaximumCharge >0                                                                                                            *es*
Battery (BESS), load shifting (DSM)     ESS with MaximumCharge >0  (usually, StorageType daily)                                                                              *es*
Electric vehicle (EV)                   ESS with electric energy outflows                                                                                                    *es*
Electrolyzer (ELZ)                      ESS with electric energy outflows and ProductionFunctionH2 >0  and ProductionFunctionHeat =0  and ProductionFunctionHydro =0         *el*
Heat pump or electric boiler            ESS with ProductionFunctionHeat >0  and ProductionFunctionH2 =0  and ProductionFunctionHydro =0                                      *hp*
CHP or fuel heating unit                It has RatedMaxPowerElec >0  and RatedMaxPowerHeat >0  and ProductionFunctionHeat =0                                                 *ch*
Fuel heating unit, fuel boiler          It has RatedMaxPowerElec =0  and RatedMaxPowerHeat >0  and ProductionFunctionHeat =0                                                 *bo*
Hydrogen heating unit                   Fuel heating unit with ProductionFunctionH2ToHeat >0                                                                                 *hh*
Hydro power plant (water)               It has ProductionFunctionHydro >0                                                                                                    *h*
======================================  ===================================================================================================================================  ==========

The model always considers a month of 672 hours, i.e., 4 weeks, not calendar months. The model assumes a year of 8736 hours, i.e., 52 weeks, not calendar years.

Daily *storage type* means the ESS inventory is assessed at every step. Daily storage type is assessed at the end of every hour, weekly storage type is assessed at the end of every day, monthly storage type is assessed at the end of every week, and the yearly storage type is evaluated at the end of every month.
*Outflows type* represents when the energy extracted from the storage must be satisfied (for daily outflows type at the end of every day, i.e., the sum of the energy consumed must be equal to the sum of outflows daily).
*Energy type* represents when the minimum or maximum energy to be produced by a unit must be satisfied (for daily energy type at the end of every day, i.e., the sum of the energy generated by the unit must be lower/greater than the sum of max/min energy for every day).
The *storage cycle* is the minimum between the inventory assessment period (defined by the storage type), the outflows period (defined by the outflows type), and the energy period (determined by the energy type) (only if outflows or energy power values have been introduced).
It can be one time step, day, week, or month, but it can't exceed the stage duration. For example, if the stage lasts 168 hours, the storage cycle can only be hourly or daily.

The initial storage of the ESSs is also fixed at the beginning and end of each stage, only if the initial inventory lies between the storage limits. For example, the initial storage level is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

A generator with operation cost (sum of the fuel and emission cost, excluding O&M cost) >0 is considered a non-renewable unit. If the unit has no operation cost and its maximum storage =0,
It is considered a renewable unit. If its maximum storage is >0, with or without operation cost, it is regarded as an ESS.

A very small variable O&M cost (not below 0.01 €/MWh, otherwise it will be converted to 0 by the model) for the ESS can be used to avoid pumping with avoided curtailment (at no cost) and afterwards discharged as spillage.

The startup cost of a generating unit refers to the expenses incurred when bringing a power generation unit online, from an idle state to a point where it can produce electricity.

Must-run non-renewable units are always committed, i.e., their commitment decision equals 1. All must-run units are forced to produce at least their minimum output.

EFOR is used to reduce the maximum and minimum power of the unit. For hydropower plants, it can be used to reduce their maximum power by the water head effect. It does not reduce the maximum charge.

Those generators or ESS with fixed cost >0  are considered candidates and can be installed.

Maximum, minimum, and initial storage values are considered proportional to the invested capacity for the candidate ESS units if StorageInvestment is activated.

A generator can belong to several mutually exclusive sets; their names must be separated by "\|" when inputted. So if Generator1 belongs to Set1 and Set2, the data entry should be "Set1\|Set2". If any of the generators in a group are installation candidates, it is assumed that exclusivity is yearly, so only one can be committed during the whole period. When all mutually exclusive generators in a set are installed and functioning, it is assumed that the exclusivity is hourly, and which generator is committed can change every LoadLevel.

A generator can be restricted to only be able to provide reserves while generating or while consuming. The NoOperatingReserve entry accepts two inputs separated by a "|". The first value corresponds to operating reserves while generating, and the second is operating reserves while consuming power. If only one value is entered, both values are considered the same. If no value is entered, both values are considered "No".

If the lower and upper bounds of investment/retirement decisions are very close (with a difference <1e-3) to 0 or 1, they are converted into 0 and 1.

Variable maximum and minimum generation
---------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxGeneration.csv`` and ``oT_Data_VariableMinGeneration.csv`` follows:

==========  ==============  ==========  =========  ============================================================  ==
Identifiers                             Header     Description
======================================  =========  ============================================================  ==
Period      Scenario        LoadLevel   Generator  Maximum (minimum) power generation of the unit by load level  MW
==========  ==============  ==========  =========  ============================================================  ==

Not all the generators must be defined as columns of these files, only those with values different from 0.

This information can be used to consider scheduled outages or weather-dependent operating capacity.

To force a generator to produce 0, a small value (e.g., 0.1 MW) strictly >0, but not 0 (in which case the value will be ignored), must be introduced. This is needed to limit the solar production at night, for example.
It can also be used for upper-bounding and/or lower-bounding the output of any generator (e.g., run-of-the-river hydro, wind).
If the user introduces a minimum generation value greater than the maximum, the model will adjust the minimum generation value to match the maximum.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable maximum and minimum consumption
----------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxConsumption.csv`` and ``oT_Data_VariableMinConsumption.csv`` follows:

==========  ==============  ==========  =========  =============================================================  ==
Identifiers                             Header     Description
======================================  =========  =============================================================  ==
Period      Scenario        LoadLevel   Generator  Maximum (minimum) power consumption of the unit by load level  MW
==========  ==============  ==========  =========  =============================================================  ==

Not all the generators must be defined as columns of these files, only those with values different from 0.

To force an ESS to consume 0 a value (e.g., 0.1 MW) strictly >0, but not 0 (in which case the value will be ignored), must be introduced.
It can also be used for upper-bounding and/or lower-bounding the consumption of any ESS (e.g., pumped-hydro storage, battery).
If the user introduces a maximum consumption value lower than the minimum consumption value, the model will adjust the minimum consumption value to match the maximum.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable fuel cost
------------------

A description of the data included in the file ``oT_Data_VariableFuelCost.csv`` follows:

==========  ==============  ==========  =========  =============================  ======
Identifiers                             Header     Description
======================================  =========  =============================  ======
Period      Scenario        LoadLevel   Generator  Variable fuel cost             €/GJ
==========  ==============  ==========  =========  =============================  ======

Not all the generators must be defined as columns of these files, only those with values different from 0.

Internally, all the values below 1e-4 will be converted into 0 by the model.

Fuel cost affects the linear and constant terms of the heat rate, expressed in GJ/MWh and GJ/h, respectively.

Variable emission cost
----------------------

A description of the data included in the file ``oT_Data_VariableEmissionCost.csv`` follows:

==========  ==============  ==========  =========  =============================  ======
Identifiers                             Header     Description
======================================  =========  =============================  ======
Period      Scenario        LoadLevel   Generator  Variable emission cost         €/tCO2
==========  ==============  ==========  =========  =============================  ======

Not all the generators must be defined as columns of these files, only those with values different from 0.

Internally, all the values below 1e-4 will be converted into 0 by the model.

Energy inflows
--------------

A description of the data included in the file ``oT_Data_EnergyInflows.csv`` follows:

==========  ==============  ==========  =========  =============================  =====
Identifiers                             Header     Description
======================================  =========  =============================  =====
Period      Scenario        LoadLevel   Generator  Energy inflows by load level   MWh/h
==========  ==============  ==========  =========  =============================  =====

Not all the generators must be defined as columns of these files, only those with values different from 0.

If you have daily energy inflow data, just input the daily amount during the first hour of every day to see if the ESS has daily or weekly storage capacity.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Energy inflows are considered proportional to the invested capacity for the candidate ESS units if StorageInvestment is activated.

Energy outflows
---------------

A description of the data included in the file ``oT_Data_EnergyOutflows.csv`` follows:

==========  ==============  ==========  =========  =============================  =====
Identifiers                             Header     Description
======================================  =========  =============================  =====
Period      Scenario        LoadLevel   Generator  Energy outflows by load level  MWh/h
==========  ==============  ==========  =========  =============================  =====

Not all the generators must be defined as columns of these files, only those with values different from 0.

These energy outflows can represent the electric energy extracted from an ESS to produce H2 from electrolyzers, move EVs, produce heat, or as hydro outflows for irrigation.
Using these outflows is incompatible with the charge of the ESS within the same time step (as the discharge of a battery is incompatible with the charge in the same hour).

If you have hourly/daily/weekly/monthly/yearly outflow data, you can just input the hourly/daily/weekly/monthly/yearly amount at the first hour of every day/week/month/year.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Variable maximum and minimum storage
------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxStorage.csv`` and ``oT_Data_VariableMinStorage.csv`` follows:

==========  ==============  ==========  =========  ====================================================  ===
Identifiers                             Header     Description
======================================  =========  ====================================================  ===
Period      Scenario        LoadLevel   Generator  Maximum (minimum) storage of the ESS by load level    GWh
==========  ==============  ==========  =========  ====================================================  ===

Not all the generators must be defined as columns of these files, only those with values different from 0.

It can also be used for upper-bounding and/or lower-bounding the storage of any generator (e.g., storage hydro).
If the user introduces a maximum storage value lower than the minimum, the model will adjust the minimum storage value to match the maximum.

For example, these data can define the operating guide (rule) curves for the ESS.

Variable maximum and minimum energy
-----------------------------------

A description of the data included in the files ``oT_Data_VariableMaxEnergy.csv`` and ``oT_Data_VariableMinEnergy.csv`` follows:

==========  ==============  ==========  =========  ====================================================  ===
Identifiers                             Header     Description
======================================  =========  ====================================================  ===
Period      Scenario        LoadLevel   Generator  Maximum (minimum) power of the unit by load level     MW
==========  ==============  ==========  =========  ====================================================  ===

Not all the generators must be defined as columns of these files, only those with values different from 0.

It can also be used for upper-bounding and/or lower-bounding the energy of any generator (e.g., storage hydro).
If the user introduces a maximum power value lower than the minimum, the model will adjust the minimum power value to match the maximum.

For example, these data can be used to define the minimum and/or maximum energy to be produced hourly, daily, weekly, monthly, or yearly (depending on the energy type).

Electricity transmission network
--------------------------------

**At least one electric transmission line connecting two nodes must be defined.**

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_Network.csv`` follows:

===================  ===============================================================================================================  ======
Header               Description
===================  ===============================================================================================================  ======
InitialNode          Name of the initial node of the transmission line
FinalNode            Name of the final node of the transmission line
Circuit              Name of the circuit (if there are several circuits between two nodes, they must have different names)
InitialNode          Name of the initial node of the transmission line
LineType             Line type {AC, DC, Transformer, Converter}
Switching            The transmission line can switch on/off                                                                          Yes/No
InitialPeriod        Initial period (year) when the unit is installed or can be installed, if candidate                               Year
FinalPeriod          Final   period (year) when the unit is installed or can be installed, if candidate                               Year
Voltage              Line voltage (e.g., 400, 220 kV, 220/400 kV if transformer). Used only for plotting purposes                     kV
Length               Line length (only used for reporting purposes). If not defined, computed as 1.1 times the geographical distance  km
LossFactor           Transmission losses equal to the line power flow times this factor                                               p.u.
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

The initial and final nodes are where the transmission line starts and ends, respectively. They must be different.

Depending on the voltage, lines are plotted with different colors (orange < 200 kV, 200 < green < 350 kV, 350 < red < 500 kV, 500 < orange < 700 kV, blue > 700 kV).

If there is no data for TTCBck, i.e., TTCBck is left empty or is equal to 0, the TTC substitutes it in the code. Internally, all the TTC and TTCBck values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Reactance can take a negative value due to the approximation of three-winding transformers. No Kirchhoff's second law disjunctive constraint is formulated for a circuit with negative reactance.

Those lines with fixed cost >0 are considered candidates and can be installed.

If the lower and upper bounds of investment decisions are very close (with a difference <1e-3) to 0 or 1, they are converted into 0 and 1.

Variable electric transmission line TTC forward and backward (optional files)
------------------------------------------------------------------------------

A description of the data included in the files ``oT_Data_VariableTTCFrw.csv`` and ``oT_Data_VariableTTCBck.csv`` follows:

==========  ==============  ==========  ============ ========== =======  ===============================================================================  ==
Identifiers                             Header                           Description
======================================  ===============================  ===============================================================================  ==
Period      Scenario        LoadLevel   Initial node Final node Circuit  Maximum TTC forward (backward) of an electric transmission line by load level    MW
==========  ==============  ==========  ============ ========== =======  ===============================================================================  ==

Not all the electric transmission lines must be defined as columns of these files, only those with values different from 0.

This information can be used to consider the transmission line's weather-dependent maximum capacity.

To force the flow of a transmission line to be 0, a small value (e.g., 0.1 MW) strictly >0, but not 0 (in which case the value will be ignored), must be introduced.
Suppose the user introduces a minimum transmission line capacity value that is greater than the maximum transmission line capacity value. In that case, the model will adjust the minimum transmission line capacity value to match the maximum.

If you want to force the flow of a transmission line to be equal to a value, introduce the same value (with opposite sign) in both files (e.g., 125 MW in ``oT_Data_VariableTTCFrw.csv`` and -125 MW in ``oT_Data_VariableTTCBck.csv``) or vice versa.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

If the variables TTCFrw and TTBck are both very small (e.g., 0.000001) for any time step, they are set to 0, and the line flow is forced to be 0, i.e., the line is disconnected.

Node location
-------------

At least two different nodes must be defined.

A description of the data included in the file ``oT_Data_NodeLocation.csv`` follows:

==============  ============  ================  ==
Identifier      Header        Description
==============  ============  ================  ==
Node            Latitude      Node latitude     º
Node            Longitude     Node longitude    º
==============  ============  ================  ==

Hydropower System Input Data
============================

These input files are introduced explicitly to allow a representation of the hydropower system based on volume and water inflow data, considering the water stream topology (hydro cascade basins). If they are unavailable, the model runs with an energy-based representation of the hydropower system.

Dictionaries. Sets
------------------
The dictionaries include all the possible elements of the corresponding sets in the optimization problem. **You can't use non-English characters (e.g., ó, º)**

=============================  ===============
File                           Description
=============================  ===============
``oT_Dict_Reservoir.csv``      Reservoirs
=============================  ===============

The information contained in these input files determines the topology of the hydro basins and how water flows along the different
hydropower and pumped-hydro power plants and reservoirs. These relations follow the water downstream direction.

=======================================  ======================  =============================================================================================
File                                     Dictionary              Description
=======================================  ======================  =============================================================================================
``oT_Dict_ReservoirToHydro.csv``         ReservoirToHydro        Reservoir upstream of hydropower plant (i.e., hydro takes the water from the reservoir)
``oT_Dict_HydroToReservoir.csv``         HydroToReservoir        Hydropower plant upstream of reservoir (i.e., hydro releases the water to the reservoir)
``oT_Dict_ReservoirToPumpedHydro.csv``   ReservoirToPumpedHydro  Reservoir upstream of pumped-hydro power plant (i.e., pumped-hydro pumps from the reservoir)
``oT_Dict_PumpedHydroToReservoir.csv``   PumpedHydroToReservoir  Pumped-hydro power plant upstream of reservoir (i.e., pumped-hydro pumps to the reservoir)
``oT_Dict_ReservoirToReservoir.csv``     ReservoirToReservoir    Reservoir upstream of reservoir (i.e., reservoir one spills the water to reservoir two)
=======================================  ======================  =============================================================================================

Natural water inflows
---------------------

A description of the data included in the file ``oT_Data_HydroInflows.csv`` follows:

==========  ==============  ==========  =========  ====================================  ==============
Identifiers                             Header     Description
======================================  =========  ====================================  ==============
Period      Scenario        LoadLevel   Reservoir  Natural water inflows by load level   m\ :sup:`3`/s
==========  ==============  ==========  =========  ====================================  ==============

All the reservoirs must be defined as columns in these files.

If you have daily natural water inflow data, just input the daily amount during the first hour of every day to see if the reservoir has daily or weekly storage capacity.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Natural water outflows
----------------------

A description of the data included in the file ``oT_Data_HydroOutflows.csv`` follows:

==========  ==============  ==========  =========  ===================================================  =============
Identifiers                             Header     Description
======================================  =========  ===================================================  =============
Period      Scenario        LoadLevel   Reservoir  Water outflows by load level (e.g., for irrigation   m\ :sup:`3`/s
==========  ==============  ==========  =========  ===================================================  =============

All the reservoirs must be defined as columns in these files.

These water outflows can be used to represent the water outflows for irrigation.

If you have hourly/daily/weekly/monthly/yearly water outflow data, you can just input the daily/weekly/monthly/yearly amount at the first hour of every day/week/month/year.

Internally, all the values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Reservoir
---------

A description of the data included in the file ``oT_Data_Reservoir.csv`` follows:

====================  ======================================================================================================================  ===================================
Header                Description
====================  ======================================================================================================================  ===================================
StorageType           Reservoir storage type based on reservoir storage capacity (hourly, daily, weekly, monthly, yearly)                     Hourly/Daily/Weekly/Monthly/Yearly
OutflowsType          Water outflows type based on the water extracted from the reservoir (daily, weekly, monthly, yearly)                    Daily/Weekly/Monthly/Yearly
InitialStorage        Initial volume stored at the first instant of the time scope                                                            hm\ :sup:`3`
MaximumStorage        Maximum volume that the hydro reservoir can store hm\ :sup:`3`
MinimumStorage        Minimum volume that the hydro reservoir can store hm\ :sup:`3`
BinaryInvestment      Binary reservoir investment decision                                                                                    Yes/No
FixedInvestmentCost   Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                         M€
FixedChargeRate       Fixed-charge rate to annualize the overnight investment cost                                                            p.u.
InitialPeriod         Initial period (year) when the unit is installed or can be installed, if candidate                                      Year
FinalPeriod           Final   period (year) when the unit is installed or can be installed, if the candidate                                      Year
====================  ======================================================================================================================  ===================================

The model always considers a month of 672 hours, i.e., 4 weeks, not calendar months. The model assumes a year of 8736 hours, i.e., 52 weeks, not calendar years.

Daily *storage type* means the ESS inventory is assessed every time step. For the daily storage type, it is evaluated at the end of every hour; for the weekly storage type, it is assessed at the end of every day; for the monthly storage type, it is evaluated at the end of every week; and yearly storage type is assessed at the end of every month.
*Outflows type* represents the interval when the energy extracted from the storage must be satisfied (for daily outflows type at the end of every day, i.e., the energy consumed must equal the sum of outflows for every day).
The *storage cycle* is the minimum between the inventory assessment period (defined by the storage type), the outflows period (determined by the outflows type), and the energy period (defined by the energy type) (only if outflows or energy power values have been introduced).
It can be one time step, day, week, and month, but it can't exceed the stage duration. For example, if the stage lasts 168 hours the storage cycle can only be hourly or daily.

The initial reservoir volume is also fixed at the beginning and end of each stage, only if the initial volume lies between the reservoir storage limits. For example, the initial volume is set for the hour 8736 in case of a single stage or for the hours 4368 and 4369
(end of the first stage and beginning of the second stage) in case of two stages, each with 4368 hours.

Variable maximum and minimum reservoir volume
---------------------------------------------

A description of the data included in the files ``oT_Data_VariableMaxVolume.csv`` and ``oT_Data_VariableMinVolume.csv`` follows:

==========  ==============  ==========  =========  =================================================  ==============
Identifiers                             Header     Description
======================================  =========  =================================================  ==============
Period      Scenario        LoadLevel   Reservoir  Maximum (minimum) reservoir volume by load level   hm\ :sup:`3`
==========  ==============  ==========  =========  =================================================  ==============

Not all the reservoirs must be defined as columns of these files, only those with values different from 0.

It can be used also for upper-bounding and/or lower-bounding the volume of any reservoir.
If the user introduces a maximum volume value that is lower than the minimum volume value, the model will adjust the minimum volume value to match the maximum.

For example, these data can be used to define the operating guide (rule) curves for the hydro reservoirs.

Hydrogen System Input Data
==========================

These input files are specifically introduced to allow a representation of the hydrogen energy vector to supply the hydrogen demand produced with electricity or by any other means through the hydrogen network.
If the hydrogen is only produced from electricity and there is no hydrogen transfer among nodes, the hydrogen demand can be represented by the energy outflows associated with the unit (i.e., electrolyzer).

=========================================  ==================================
File                                       Description
=========================================  ==================================
``oT_Data_DemandHydrogen.csv``             Hydrogen demand
``oT_Data_NetworkHydrogen.csv``            Hydrogen pipeline network data
=========================================  ==================================

Hydrogen demand
---------------

A description of the data included in the file ``oT_Data_DemandHydrogen.csv`` follows:

==========  ==============  ==========  ======  ===============================================  =====
Identifiers                             Header  Description
======================================  ======  ===============================================  =====
Period      Scenario        LoadLevel   Node    Hydrogen demand of the node for each load level  tH2/h
==========  ==============  ==========  ======  ===============================================  =====

Internally, all the values below if positive demand (or above if negative demand) 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Hydrogen transmission pipeline network
--------------------------------------

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_NetworkHydrogen.csv`` follows:

===================  ===================================================================================================================  ======
Header               Description
===================  ===================================================================================================================  ======
InitialPeriod        Initial period (year) when the unit is installed or can be installed, if candidate                                   Year
FinalPeriod          Final   period (year) when the unit is installed or can be installed, if candidate                                   Year
Length               Pipeline length (only used for reporting purposes). If not defined, computed as 1.1 times the geographical distance  km
TTC                  Total transfer capacity (maximum permissible hydrogen flow) in forward  direction. Static pipeline rating            tH2
TTCBck               Total transfer capacity (maximum permissible hydrogen flow) in backward direction. Static pipeline rating            tH2
SecurityFactor       Security factor to consider approximately N-1 contingencies. NTC = TTC x SecurityFactor                              p.u.
FixedInvestmentCost  Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                      M€
FixedChargeRate      Fixed-charge rate to annualize the overnight investment cost                                                         p.u.
BinaryInvestment     Binary pipeline investment decision                                                                                  Yes/No
InvestmentLo         Lower bound of investment decision                                                                                   p.u.
InvestmentUp         Upper bound of investment decision                                                                                   p.u.
===================  ===================================================================================================================  ======

The initial and final nodes are where the transmission line starts and ends. They must be different.

If there is no data for TTCBck, i.e., TTCBck is left empty or is equal to 0, the TTC substitutes it in the code. Internally, all the TTC and TTCBck values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Those pipelines with fixed costs>0  are considered candidates and can be installed.

If the lower and upper bounds of investment decisions are very close (with a difference <1e-3) to 0 or 1, they are converted into 0 and 1.

Heat System Input Data
======================

These input files are specifically introduced to allow a representation of the heat energy vector to supply heat demand produced with electricity or with any fuel through the heat network.
Suppose the heat is only produced from electricity without heat transfer among nodes. In that case, the heat demand can be represented by the energy outflows associated with the unit (i.e., heat pump or electric boiler).

===================================  ==============================
File                                 Description
===================================  ==============================
``oT_Data_ReserveMarginHeat.csv``    Heat reserve margin
``oT_Data_DemandHeat.csv``           Heat demand
``oT_Data_NetworkHeat.csv``          Heat pipeline network data
===================================  ==============================

Heat adequacy reserve margin
----------------------------

The adequacy reserve margin for heating is the ratio between the available capacity and the maximum demand. It is modeled as the adequacy reserve margin for electricity, considering the units' heat demand and heat capacity.
A description of the data included in the file ``oT_Data_ReserveMarginHeat.csv`` follows:

==============  ==============  =============  ===============================================================  ====
Identifiers                     Header         Description
==============  ==============  =============  ===============================================================  ====
Period          Area            ReserveMargin  Minimum heat adequacy reserve margin for each period and area    p.u.
==============  ==============  =============  ===============================================================  ====

This parameter is only used for system heating generation expansion, not for the system operation. If no value is introduced for an area, the reserve margin is considered 0.

Heat demand
-----------

A description of the data included in the file ``oT_Data_DemandHeat.csv`` follows:

==========  ==============  ==========  ======  ===============================================  ======
Identifiers                             Header  Description
======================================  ======  ===============================================  ======
Period      Scenario        LoadLevel   Node    Heat demand of the node for each load level      MW
==========  ==============  ==========  ======  ===============================================  ======

Internally, if positive demand (or above if negative demand) is 1e-5 times the maximum system demand of each area, all the values below will be converted into 0 by the model.

Heat transmission pipeline network
----------------------------------

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_NetworkHeat.csv`` follows:

===================  ===================================================================================================================  ======
Header               Description
===================  ===================================================================================================================  ======
InitialPeriod        Initial period (year) when the unit is installed or can be installed, if candidate                                   Year
FinalPeriod          Final   period (year) when the unit is installed or can be installed, if the candidate                                   Year
Length               Pipeline length (only used for reporting purposes). If not defined, computed as 1.1 times the geographical distance  km
TTC                  Total transfer capacity (maximum permissible heat flow) in forward  direction. Static pipeline rating                MW
TTCBck               Total transfer capacity (maximum permissible heat flow) in backward direction. Static pipeline rating                MW
SecurityFactor       Security factor to consider approximately N-1 contingencies. NTC = TTC x SecurityFactor                              p.u.
FixedInvestmentCost  Overnight investment (capital -CAPEX- and fixed O&M -FOM-) cost                                                      M€
FixedChargeRate      Fixed-charge rate to annualize the overnight investment cost                                                         p.u.
BinaryInvestment     Binary pipeline investment decision                                                                                  Yes/No
InvestmentLo         Lower bound of investment decision                                                                                   p.u.
InvestmentUp         Upper bound of investment decision                                                                                   p.u.
===================  ===================================================================================================================  ======

The initial and final nodes are where the transmission line starts and ends. They must be different.

If there is no data for TTCBck, i.e., TTCBck is left empty or is equal to 0, the TTC substitutes it in the code. Internally, all the TTC and TTCBck values below 1e-5 times the maximum system demand of each area will be converted into 0 by the model.

Those pipelines with fixed costs>0  are considered candidates and can be installed.

If the lower and upper bounds of investment decisions are very close (with a difference <1e-3) to 0 or 1, they are converted into 0 and 1.

Flow-Based Market Coupling Method
=================================

This input file is introduced explicitly to allow the flow-based market coupling method. If they are not available, the model runs with the DCOPF method.

===================================  ==========================================
File                                 Description
===================================  ==========================================
``oT_Data_VariablePTDF.csv``         Power transfer distribution factors (PTDF)
===================================  ==========================================

Variable power transfer distribution factors
--------------------------------------------

A description of the data included in the file ``oT_Data_VariablePTDF.csv`` follows:

==========  ==============  ==========  ============ ========== ======= ====  ===================================================  ====
Identifiers                             Header                                Description
======================================  ====================================  ===================================================  ====
Period      Scenario        LoadLevel   Initial node Final node Circuit Node  Power transfer distribution factors by load level    p.u.
==========  ==============  ==========  ============ ========== ======= ====  ===================================================  ====

Not all the transmission lines must be defined as columns of these files, only those with values different from 0.
