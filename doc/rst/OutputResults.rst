.. openTEPES documentation master file, created by Andres Ramos

Output Results
==============

A map of the transmission network and the energy share of different technologies is plotted (access to internet is required to download the underlying map).

.. image:: ../img/oT_Map_Network_sSEP.png
   :scale: 40%
   :align: center

|

.. image:: ../img/oT_Map_Network_MAF2030.png
   :scale: 60%
   :align: center

.. image:: ../img/oT_Plot_TechnologyEnergy_ES_MAF2030.png
   :scale: 6%
   :align: center

Besides, the csv files used for outputting the results are briefly described in the following items.

Investment
----------

File ``oT_Result_GenerationInvestment.csv``

============  ==========  ============================
Identifier    Header      Description
============  ==========  ============================
Generator     MW          Generation investment power
============  ==========  ============================

File ``oT_Result_GenerationRetirement.csv``

============  ==========  =============================
Identifier    Header      Description
============  ==========  =============================
Generator     MW          Generation retirement power
============  ==========  =============================

File ``oT_Result_TechnologyInvestment.csv``

============  ==========  ============================
Identifier    Header      Description
============  ==========  ============================
Generator     MW        Technology investment POWER
============  ==========  ============================

File ``oT_Result_TechnologyRetirement.csv``

============  ==========  ============================
Identifier    Header      Description
============  ==========  ============================
Generator     MW          Technology retirement power
============  ==========  ============================

File ``oT_Result_NetworkInvestment.csv``

============  ==========  ==========  ======  =============================
Identifier    Identifier  Identifier  Header  Description
============  ==========  ==========  ======  =============================
Initial node  Final node  Circuit     p.u.    Network investment decision
============  ==========  ==========  ======  =============================

File ``oT_Result_NetworkInvestment_MWkm.csv``

============  ==========  ==========  ======  ===========================
Identifier    Identifier  Identifier  Header  Description
============  ==========  ==========  ======  ===========================
Initial node  Final node  Circuit     MW-km   Network investment
============  ==========  ==========  ======  ===========================

Generation operation
--------------------

File ``oT_Result_GenerationCommitment.csv``

============  ==========  ==========  ==========  ===========================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===========================
Scenario      Period      Load level  Generator   Commitment decision [p.u.]
============  ==========  ==========  ==========  ===========================

File ``oT_Result_GenerationStartUp.csv``

============  ==========  ==========  ==========  ===========================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===========================
Scenario      Period      Load level  Generator   Startup decision [p.u.]
============  ==========  ==========  ==========  ===========================

File ``oT_Result_GenerationShutDown.csv``

============  ==========  ==========  ==========  ==========================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================
Scenario      Period      Load level  Generator   Shutdown decision [p.u.]
============  ==========  ==========  ==========  ==========================

File ``oT_Result_GenerationReserveUp.csv``

============  ==========  ==========  ==========  ===============================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===============================================
Scenario      Period      Load level  Generator   Upward operating reserve of each generator [MW]
============  ==========  ==========  ==========  ===============================================

File ``oT_Result_GenerationReserveDown.csv``

============  ==========  ==========  ==========  =================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================================
Scenario      Period      Load level  Generator   Downward operating reserve of each generator [MW]
============  ==========  ==========  ==========  =================================================

File ``oT_Result_GenerationOutput.csv``

============  ==========  ==========  ==========  ===================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===================================
Scenario      Period      Load level  Generator   Output (discharge in ESS) [MW]
============  ==========  ==========  ==========  ===================================

File ``oT_Result_GenerationSurplus.csv``

============  ==========  ==========  ==============  ===============================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================
Scenario      Period      Load level  Generator       Power surplus [MW]
============  ==========  ==========  ==============  ===============================

File ``oT_Result_GenerationRampUpSurplus.csv``

============  ==========  ==========  ==============  ===============================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================
Scenario      Period      Load level  Generator       Upward ramp surplus [MW]
============  ==========  ==========  ==============  ===============================

File ``oT_Result_GenerationRampDwSurplus.csv``

============  ==========  ==========  ==============  ===============================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================
Scenario      Period      Load level  Generator       Downward ramp surplus [MW]
============  ==========  ==========  ==============  ===============================

File ``oT_Result_Curtailment.csv``

============  ==========  ==========  ==============  ===============================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================
Scenario      Period      Load level  VRES Generator  Curtailed power of VRES [MW]
============  ==========  ==========  ==============  ===============================

File ``oT_Result_CurtailmentEnergy.csv``

============  ==========  ==========  ==============  ===============================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================
Scenario      Period      Load level  VRES Generator  Curtailed energy of VRES [GWh]
============  ==========  ==========  ==============  ===============================

File ``oT_Result_GenerationEnergy.csv``

============  ==========  ==========  ==========  =================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================
Scenario      Period      Load level  Generator   Energy (discharge in ESS) [GWh]
============  ==========  ==========  ==========  =================================

File ``oT_Result_GenerationEmission.csv``

============  ==========  ==========  ==========  =================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================
Scenario      Period      Load level  Generator   CO2 emission [Mt CO2]
============  ==========  ==========  ==========  =================================

File ``oT_Result_GenerationIncrementalEmission.csv``

============  ==========  ==========  ==============  ===============================================================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================================================================================
Scenario      Period      Load level  Generator       Emission rate of the generators with power surplus, except the ESS [tCO2/MWh]
============  ==========  ==========  ==============  ===============================================================================================

File ``oT_Result_TechnologyEmission.csv``

============  ==========  ==========  ==========  =================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================
Scenario      Period      Load level  Technology   CO2 emission [Mt CO2]
============  ==========  ==========  ==========  =================================

File ``oT_Result_TechnologyOutput.csv``

============  ==========  ==========  ==========  =================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================
Scenario      Period      Load level  Technology  Output (discharge in ESS) [MW]
============  ==========  ==========  ==========  =================================

File ``oT_Result_TechnologyCharge.csv``

============  ==========  ==========  ==========  =================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================
Scenario      Period      Load level  Technology  Consumption (charge in ESS) [MW]
============  ==========  ==========  ==========  =================================

File ``oT_Result_TechnologyCurtailmentEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Curtailed energy of VRES [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (discharge in ESS) [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyEnergy_AreaName.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (discharge in ESS) per area [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyCurtailmentEnergy.csv``

============  ==========  ==========  ===========  ==========================================
Identifier    Identifier  Identifier  Header       Description
============  ==========  ==========  ===========  ==========================================
Scenario      Period      Load level  Technology   Curtailed energy of VRES [GWh]
============  ==========  ==========  ===========  ==========================================

File ``oT_Result_TechnologyReserveUp.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Upward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyReserveDown.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Downward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

ESS operation
-------------

File ``oT_Result_GenerationOutflows.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Outflows power in ESS [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyOutflows.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Outflows power in ESS [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeOutput.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Charged power in ESS [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyOutputESS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Charged power in ESS [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationOutflowsEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Outflows energy in ESS [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyOutflowsEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (Outflows in ESS) [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Charged energy in ESS [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyEnergyESS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (charge in ESS) [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyEnergyESS_AreaName.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (charge in ESS) per area [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeReserveUp.csv``

============  ==========  ==========  ==========  =================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================================
Scenario      Period      Load level  Generator   Upward operating reserve of each pump/charge [MW]
============  ==========  ==========  ==========  =================================================

File ``oT_Result_ChargeReserveDown.csv``

============  ==========  ==========  ==========  ===================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===================================================
Scenario      Period      Load level  Generator   Downward operating reserve of each pump/charge [MW]
============  ==========  ==========  ==========  ===================================================

File ``oT_Result_TechnologyReserveUpESS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Upward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyReserveDownESS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Downward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_Inventory.csv``

============  ==========  ==========  =========  ==============================================================================================
Identifier    Identifier  Identifier  Header     Description
============  ==========  ==========  =========  ==============================================================================================
Scenario      Period      Load level  Generator  Stored energy (SoC in batteries, reservoir energy in pumped-hydro storage power plants) [GWh]
============  ==========  ==========  =========  ==============================================================================================

File ``oT_Result_InventoryUtilization.csv``

============  ==========  ==========  =========  =================================================================
Identifier    Identifier  Identifier  Header     Description
============  ==========  ==========  =========  =================================================================
Scenario      Period      Load level  Generator  ESS utilization (i.e., ratio between usage and capacity) [p.u.]
============  ==========  ==========  =========  =================================================================

File ``oT_Result_Spillage.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Spilled energy in ESS [GWh]
============  ==========  ==========  ==========  ==========================================

Network operation
-----------------

File ``oT_Result_NetworkCommitment.csv``

============  ==========  ==========  ============  ==========  =========  ==========================
Identifier    Identifier  Identifier  Header        Header      Header     Description
============  ==========  ==========  ============  ==========  =========  ==========================
Scenario      Period      Load level  Initial node  Final node  Circuit    Commitment decision [p.u.]
============  ==========  ==========  ============  ==========  =========  ==========================

File ``oT_Result_NetworkSwitchOn.csv``

============  ==========  ==========  ============  ==========  =========  ==========================
Identifier    Identifier  Identifier  Header        Header      Header     Description
============  ==========  ==========  ============  ==========  =========  ==========================
Scenario      Period      Load level  Initial node  Final node  Circuit    Switch on decision [p.u.]
============  ==========  ==========  ============  ==========  =========  ==========================

File ``oT_Result_NetworkSwitchOff.csv``

============  ==========  ==========  ============  ==========  =========  ==========================
Identifier    Identifier  Identifier  Header        Header      Header     Description
============  ==========  ==========  ============  ==========  =========  ==========================
Scenario      Period      Load level  Initial node  Final node  Circuit    Switch off decision [p.u.]
============  ==========  ==========  ============  ==========  =========  ==========================

File ``oT_Result_NetworkFlow.csv``

============  ==========  ==========  ============  ==========  =========  =======================
Identifier    Identifier  Identifier  Header        Header      Header      Description
============  ==========  ==========  ============  ==========  =========  =======================
Scenario      Period      Load level  Initial node  Final node  Circuit     Line flow [MW]
============  ==========  ==========  ============  ==========  =========  =======================

File ``oT_Result_NetworkUtilization.csv``

============  ==========  ==========  ============  ==========  ==========  ================================================================
Identifier    Identifier  Identifier  Header        Header      Header      Description
============  ==========  ==========  ============  ==========  ==========  ================================================================
Scenario      Period      Load level  Initial node  Final node  Circuit     Line utilization (i.e., ratio between flow and capacity) [p.u.]
============  ==========  ==========  ============  ==========  ==========  ================================================================

File ``oT_Result_NetworkLosses.csv``

============  ==========  ==========  ============  ==========  ==========  =======================
Identifier    Identifier  Identifier  Header        Header      Header      Description
============  ==========  ==========  ============  ==========  ==========  =======================
Scenario      Period      Load level  Initial node  Final node  Circuit     Line losses [MW]
============  ==========  ==========  ============  ==========  ==========  =======================

File ``oT_Result_NetworkAngle.csv``

============  ==========  ==========  =========  =======================
Identifier    Identifier  Identifier  Header     Description
============  ==========  ==========  =========  =======================
Scenario      Period      Load level  Node       Voltage angle [rad]
============  ==========  ==========  =========  =======================

File ``oT_Result_NetworkPNS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Node        Power not served by node [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_NetworkENS.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Node        Energy not served by node [GWh]
============  ==========  ==========  ==========  ==========================================

Marginal information
--------------------

File ``oT_Result_MarginalReserveMargin.csv``

============  ==========  ==========  ==========  =================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================================
Scenario      Period      Load level  Area        Marginal of the reserve margin [€/MW]
============  ==========  ==========  ==========  =================================================

File ``oT_Result_GenerationIncrementalVariableCost.csv``

============  ==========  ==========  ==============  ===============================================================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===============================================================================================
Scenario      Period      Load level  Generator       Variable cost (fuel+O&M+emission) of the generators with power surplus, except the ESS [€/MWh]
============  ==========  ==========  ==============  ===============================================================================================

File ``oT_Result_LSRMC.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Node        Locational Short-Mun Marginal Cost [€/MWh]
============  ==========  ==========  ==========  ==========================================

These marginal costs are obtained after fixing the binary and continuous investment decisions and the binary operation decisions to their optimal values.
Remember that binary decisions are not affected by marginal changes.

File ``oT_Result_WaterValue.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Generator   Energy inflow value [€/MWh]
============  ==========  ==========  ==========  ================================================

File ``oT_Result_MarginalOperatingReserveUp.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Area        Marginal of the upward operating reserve [€/MW]
============  ==========  ==========  ==========  ================================================

File ``oT_Result_MarginalOperatingReserveDown.csv``

============  ==========  ==========  ==========  =================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  =================================================
Scenario      Period      Load level  Area        Marginal of the downward operating reserve [€/MW]
============  ==========  ==========  ==========  =================================================

File ``oT_Result_NetworkInvestment_ReducedCost.csv``

============  ==========  ==========  =====================================================
Identifier    Identifier  Identifier  Description
============  ==========  ==========  =====================================================
Initial node  Final node  Circuit     Reduced costs of network investment decisions [M€]
============  ==========  ==========  =====================================================

File ``oT_Result_NetworkCommitment_ReducedCost.csv``

============  ==========  ==========  =====================================================
Identifier    Identifier  Identifier  Description
============  ==========  ==========  =====================================================
Initial node  Final node  Circuit     Reduced costs of network switching decisions [M€]
============  ==========  ==========  =====================================================

Economic
--------

File ``oT_Result_CostSummary.csv``

============  ==========================================
Identifier    Description
============  ==========================================
Cost type     Type of cost [M€]
============  ==========================================

File ``oT_Result_CostRecovery.csv``

============  ==========================================
Identifier    Description
============  ==========================================
Cost type     Revenues and costs of investments [M€]
============  ==========================================

File ``oT_Result_GenerationCostOandM.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   O&M cost for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationCostOperation.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Operation cost for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeCostOperation.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Pump        Operation cost for the consumption [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationCostOperReserve.csv``

============  ==========  ==========  ==========  ==============================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==============================================
Scenario      Period      Load level  Generator   Operation reserve cost for the generation [M€]
============  ==========  ==========  ==========  ==============================================

File ``oT_Result_GenerationCostEmission.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Emission cost for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ReliabilityCost.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Node        Reliability cost (cost of the ENS) [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_RevenueEnergyGeneration.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Operation revenues for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_RevenueEnergyCharge.csv``

============  ==========  ==========  ==============  ==================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==================================================
Scenario      Period      Load level  ESS Generator   Operation revenues for the consumption/charge [M€]
============  ==========  ==========  ==============  ==================================================

File ``oT_Result_RevenueOperatingReserveUp.csv``

============  ==========  ==========  ==========  ==========================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================================
Scenario      Period      Load level  Generator   Operation revenues from the upward operating reserve [M€]
============  ==========  ==========  ==========  ==========================================================

File ``oT_Result_RevenueOperatingReserveUpESS.csv``

============  ==========  ==========  ==============  ==========================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==========================================================
Scenario      Period      Load level  ESS Generator   Operation revenues from the upward operating reserve [M€]
============  ==========  ==========  ==============  ==========================================================

File ``oT_Result_RevenueOperatingReserveDw.csv``

============  ==========  ==========  ==========  ===========================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===========================================================
Scenario      Period      Load level  Generator   Operation revenues from the downward operating reserve [M€]
============  ==========  ==========  ==========  ===========================================================

File ``oT_Result_RevenueOperatingReserveDwESS.csv``

============  ==========  ==========  ==============  ===========================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ===========================================================
Scenario      Period      Load level  ESS Generator   Operation revenues from the downward operating reserve [M€]
============  ==========  ==========  ==============  ===========================================================

Flexibility
-----------

File ``oT_Result_FlexibilityDemand.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Demand      Demand variation wrt its mean value [MW]
============  ==========  ==========  ==========  ================================================

File ``oT_Result_FlexibilityPNS.csv``

============  ==========  ==========  ==========  ==================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==================================================
Scenario      Period      Load level  PNS         Power not served variation wrt its mean value [MW]
============  ==========  ==========  ==========  ==================================================

File ``oT_Result_FlexibilityTechnology.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Technology  Technology variation wrt its mean value [MW]
============  ==========  ==========  ==========  ================================================

File ``oT_Result_FlexibilityTechnologyESS.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Technology  ESS Technology variation wrt its mean value [MW]
============  ==========  ==========  ==========  ================================================
