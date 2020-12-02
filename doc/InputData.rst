.. openTEPES documentation master file, created by Andres Ramos

Input Data
==========

Dictionaries. Sets
------------------
The dictionaries include all the possible elements of the corresponding sets included in the optimization problem

==========================  ===================================================================================================================
File                        Description
==========================  ===================================================================================================================
``oT_Dict_Scenario.csv``    Scenario. Short-term uncertainties (scenarios) (e.g., s001 to s100)
``oT_Dict_Period.csv``      Period (e.g., y2030)
``oT_Dict_LoadLevel.csv``   Load level (e.g., 2030-01-01T00:00:00+01:00 to 2030-12-30T23:00:00+01:00). Load levels with duration 0 are ignored
``oT_Dict_Generation.csv``  Generation units (thermal, ESS and variable)
``oT_Dict_Technology.csv``  Generation technologies
``oT_Dict_Storage.csv``     ESS type (daily < 12 h, weekly < 40 h, monthly > 60 h)
``oT_Dict_Node.csv``        Nodes
``oT_Dict_Zone.csv``        Zones
``oT_Dict_Area.csv``        Areas
``oT_Dict_Region.csv``      Regions
``oT_Dict_Circuit.csv``     Circuits
``oT_Dict_Line.csv``        Line type {AC, DC}
==========================  ===================================================================================================================

Geographical location of nodes, zones, areas, regions

============================  ============  ============================
File                          Dictionary    Description
============================  ============  ============================
``oT_Dict_NodeToZone.csv``    NodeToZone    Location of nodes at zones
``oT_Dict_ZoneToArea.csv``    ZoneToArea    Location of zones at areas
``oT_Dict_AreaToRegion.csv``  AreaToRegion  Location of areas at regions
============================  ============  ============================

Input files
-----------
This is the list of the input data files and their brief description.

=========================================  ==========================================================================================================
File                                       Description
=========================================  ==========================================================================================================
``oT_Data_Option.csv``                     Options of the **openTEPES** model
``oT_Data_Parameter.csv``                  General system parameters
``oT_Data_Scenario.csv``                   Short-term uncertainties
``oT_Data_NodeLocation.csv``               Node location in latitude and longitude
``oT_Data_Demand.csv``                     Demand
``oT_Data_OperatingReserveUp.csv``         Upward operating reserves (include aFRR, mFRR and RR for electricity balancing from ENTSO-E)
``oT_Data_OperatingReserveDown.csv``       Downward operating reserves (include aFRR, mFRR and RR for electricity balancing from ENTSO-E)
``oT_Data_Duration.csv``                   Duration of the load levels
``oT_Data_Generation.csv``                 Generation data
``oT_Data_MaximumStorage.csv``             Maximum storage of the ESS by load level
``oT_Data_MinimumStorage.csv``             Minimum storage of the ESS by load level
``oT_Data_Network.csv``                    Network data
``oT_Data_VariableMinGeneration.csv``      Variable minimum power generation by load level
``oT_Data_VariableMaxGeneration.csv``      Variable maximum power generation by load level
=========================================  ==========================================================================================================

Options
----------
A description of the options included in the file ``oT_Data_Option.csv`` follows:

================  ============================================================================
File              Description                                                                 
================  ============================================================================
IndBinGenInvest   Indicator of binary generation expansion decisions, 0 continuous - 1 binary 
IndBinNetInvest   Indicator of binary network    expansion decisions, 0 continuous - 1 binary 
IndBinGenOperat   Indicator of binary generation operation decisions, 0 continuous - 1 binary 
IndNetLosses      Indicator of network losses, 0 lossless - 1 ohmic losses                    
================  ============================================================================

Parameters
----------
A description of the system parameters included in the file ``oT_Data_Parameter.csv`` follows:

====================  =================================================================================================  ================
File                  Description                                                                              
====================  =================================================================================================  ================
ENSCost               Cost of energy not served. Cost of load curtailment. Value of Lost Load (VoLL)                     €/MWh   
PNSCost               Cost of power not served associated with the deficit in operating reserve by load level            €/MW   
CO2Cost               Cost of CO2 emissions                                                                              €/t CO2
UpReserveActivation   Upward reserve activation (proportion of upward operating reserve deployed to produce energy)      p.u.
DwReserveActivation   Downward reserve activation (proportion of downward operating reserve deployed to produce energy)  p.u.
Sbase                 Base power used in the DCLF                                                                        MW   
ReferenceNode         Reference node used in the DCLF      
TimeStep              Duration of the time step for the load levels (hourly, bi-hourly, trihourly, etc.).                h
====================  =================================================================================================  ================

A time step greater than one hour it is a convenient way to reduce the load levels of the time scope. The moving average of the demand, upward and downward operating reserves, variable generation and ESS energy inflows over
the time step load levels is assigned to active load levels (e.g., the mean value of the three hours is associated to the third hour in a trihourly time step).

Scenario
--------

A description of the data included in the file ``oT_Data_Scenario.csv`` follows:

==============  ============  ===========================  ====
Identifier      Header        Description
==============  ============  ===========================  ====
Scenario        Probability   Probability of the scenario  p.u.
==============  ============  ===========================  ====

Node location
-------------

A description of the data included in the file ``oT_Data_NodeLocation.csv`` follows:

==============  ============  ================  ==
Identifier      Header        Description
==============  ============  ================  ==
Node            Latitude      Node latitude     º
Node            Longitude     Node longitude    º
==============  ============  ================  ==

Demand
------

A description of the data included in the file ``oT_Data_Demand.csv`` follows:

==============  ==========  ==========  ======  ============================================  ==
Identifier      Identifier  Identifier  Header  Description
==============  ==========  ==========  ======  ============================================  ==
Scenario        Period      Load level  Node    Power demand of the node for each load level  MW
==============  ==========  ==========  ======  ============================================  ==

Internally, all the values below 1e-5 times the maximum system demand will be converted into 0 by the model.

Upward and downward operating reserves
--------------------------------------

A description of the data included in the files ``oT_Data_OperatingReserveUp.csv`` and ``oT_Data_OperatingReserveDown.csv`` follows:

==============  ==========  ==========  ======  ===================================================================  ==
Identifier      Identifier  Identifier  Header  Description
==============  ==========  ==========  ======  ===================================================================  ==
Scenario        Period      Load level  Area    Upward/downward operating reserves of the area for each load level   MW
==============  ==========  ==========  ======  ===================================================================  ==

Given that the operating reserves depend on the area, it can be sensible to assign an area as a country, for example.
These operating reserves must include Automatic Frequency Restoration Reserves (aFRR), Manual Frequency Restoration Reserves (mFRR) and Replacement Reserves (RR) for electricity balancing from ENTSO-E.

Internally, all the values below 1e-5 times the maximum system demand will be converted into 0 by the model.

Duration
--------

A description of the data included in the file ``oT_Data_Duration.csv`` follows:

==============  ==========  ==========  ========  ===================================================================  ==
Identifier      Identifier  Identifier  Header    Description
==============  ==========  ==========  ========  ===================================================================  ==
Scenario        Period      Load level  Duration  Duration of the load level. Load levels with duration 0 are ignored  h
==============  ==========  ==========  ========  ===================================================================  ==

It is a simple way to use isolated snapshots or representative days or just the first three months instead of all the hours of a year to simplify the optimization problem.

Generation
----------
A description of the data included for each generating unit in the file ``oT_Data_Generation.csv`` follows:

====================  =======================================================================================  ============================
Header                Description                                                                             
====================  =======================================================================================  ============================  
Node                  Location of the generator at the node                                                   
Technology            Technology of the generator (nuclear, coal, CCGT, OCGT, ESS, etc.)                       
StorageType           Storage type (daily, weekly, monthly, etc.)                                              Daily/Weekly/Monthly
MustRun               Must-run unit                                                                            Yes/No
MaximumPower          Maximum power output (discharge for ESS units)                                           MW
MinimumPower          Minimum power output                                                                     MW
MaximumReactivePower  Maximum reactive power output (discharge for ESS units) (not used in the plain version)  MW
MinimumReactivePower  Minimum reactive power output (not used in the plain version)                            MW
MaximumCharge         Maximum charge when storing energy the ESS unit                                          MW
InitialStorage        Initial energy stored at the first instant of the time scope                             GWh
MaximumStorage        Maximum energy that can be stored by the ESS unit                                        GWh
MinimumStorage        Minimum energy that can be stored by the ESS unit                                        GWh
Efficiency            Round-trip efficiency in the charge/discharge cycle                                      p.u.
EFOR                  Equivalent Forced Outage Rate                                                            p.u.
RampUp                Ramp up   rate                                                                           MW/h
RampDown              Ramp down rate                                                                           MW/h
UpTime                Minimum uptime                                                                           h
DownTime              Minimum downtime                                                                         h
FuelCost              Fuel cost                                                                                €/Mcal
LinearTerm            Linear term (slope) of the heat rate straight line                                       Mcal/MWh
ConstantTerm          Constant term (intercept) of the heat rate straight line                                 Mcal/h
OMVariableCost        O&M variable cost                                                                        €/MWh
StartUpCost           Startup  cost                                                                            M€
ShutDownCost          Shutdown cost                                                                            M€
CO2EmissionRate       CO2 emission rate                                                                        t CO2/MWh
FixedCost             Overnight investment (capital) cost                                                      M€
FixedChargeRate       Fixed charge rate to annualize the overnight investment cost                             p.u.
BinaryInvestment      Binary unit investment decision                                                          Yes/No
====================  =======================================================================================  ============================

EFOR is used to reduce the maximum and minimum power of the unit. For hydro units it can be used to reduce their maximum power by the head effect. It doesn't reduce the maximum charge.

Those generators or ESS with fixed cost > 0 are considered candidate and can be installed or not. A generator with linear variable costs > 0 is considered a thermal unit. If its maximum storage > 0 is considered an ESS.


Energy inflows
--------------

A description of the data included in the file ``oT_Data_EnergyInflows.csv`` follows:

==============  ==========  ==========  =========  =============================  ==
Identifier      Identifier  Identifier  Header     Description
==============  ==========  ==========  =========  =============================  ==
Scenario        Period      Load level  Generator  Energy inflows by load level   MW
==============  ==========  ==========  =========  =============================  ==

Internally, all the values below 1e-5 times the maximum system demand will be converted into 0 by the model.

Variable generation
-----------------------

A description of the data included in the files ``oT_Data_VariableMinGeneration.csv`` and ``oT_Data_VariableMaxGeneration.csv`` follows:

==============  ==========  ==========  =========  ===========================================================  ==
Identifier      Identifier  Identifier  Header     Description
==============  ==========  ==========  =========  ===========================================================  ==
Scenario        Period      Load level  Generator  Minimum/maximum power generation of the unit by load level   MW
==============  ==========  ==========  =========  ===========================================================  ==

To force a generator to produce 0 a lower value (e.g., 0.1 MW) strictly > 0, but not 0 (in which case the value will be ignored), must be introduced.

Internally, all the values below 1e-5 times the maximum system demand will be converted into 0 by the model.

Variable maximum and minimum storage
---------------------------------------------

A description of the data included in the files ``oT_Data_MaximumStorage.csv`` and ``oT_Data_MinimumStorage.csv`` follows:

==============  ==========  ==========  =========  ====================================================  ===
Identifier      Identifier  Identifier  Header     Description
==============  ==========  ==========  =========  ====================================================  ===
Scenario        Period      Load level  Generator  Maximum (minimum) storage of the ESS by load level    GWh
==============  ==========  ==========  =========  ====================================================  ===

All the generators must be defined as columns of these files.

Transmission network
--------------------

A description of the circuit (initial node, final node, circuit) data included in the file ``oT_Data_Network.csv`` follows:

=================  ============================================================================================  ======
Header             Description
=================  ============================================================================================  ======
LineType           Line type {AC, DC, Transformer, Converter}  
Voltage            Line voltage (e.g., 400, 220 kV, 220/400 kV if transformer). Used only for plotting purposes  kV
LossFactor         Transmission losses equal to the line flow times this factor                                  p.u.
Resistance         Resistance (not used in the plain version)                                                    p.u.
Reactance          Reactance. Lines must have a reactance different from 0 to be considered                      p.u.
Susceptance        Susceptance (not used in the plain version)                                                   p.u.
AngMax             Maximum angle difference (not used in the plain version)                                      º
AngMin             Minimum angle difference (not used in the plain version)                                      º
Tap                Tap changer (not used in the plain version)                                                   p.u.
Converter          Converter station (not used in the plain version)                                             Yes/No
TTC                Total transfer capacity (maximum permissible thermal load)                                    MW
SecurityFactor     Security factor to consider approximately N-1 contingencies. NTC = TTC x SecurityFactor       p.u.
FixedCost          Overnight investment (capital) cost                                                           M€
FixedChargeRate    Fixed charge rate to annualize the overnight investment cost                                  p.u.
BinaryInvestment   Binary line/circuit investment decision                                                       Yes/No
=================  ============================================================================================  ======

Those lines with fixed cost > 0 are considered candidate and can be installed or not.
