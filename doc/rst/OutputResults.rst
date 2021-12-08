.. openTEPES documentation master file, created by Andres Ramos

Output Results
==============

A map of the transmission network and the energy share of different technologies is plotted (access to internet is required to download the underlying map).

.. image:: ../img/oT_Map_Network_sSEP.png
   :scale: 40%
   :align: center

.. image:: ../img/oT_Map_Network_MAF2030.png
   :scale: 40%
   :align: center

.. image:: ../img/oT_Plot_TechnologyEnergy_ES_MAF2030.png
   :scale: 6%
   :align: center

Besides, the csv files used for outputting the results are briefly described in the following items.

Investment
----------

File ``oT_Result_GenerationInvestment.csv``

============  ==========  ==============================================================
Identifier    Header      Description
============  ==========  ==============================================================
Generator     p.u.        Generation investment decision
============  ==========  ==============================================================

File ``oT_Result_NetworkInvestment.csv``

============  ==========  ==========  ======  ==========================================
Identifier    Identifier  Identifier  Header  Description
============  ==========  ==========  ======  ==========================================
Initial node  Final node  Circuit     p.u.    Network investment decision
============  ==========  ==========  ======  ==========================================

Generation operation
--------------------

File ``oT_Result_GenerationCommitment.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Commitment decision [p.u.]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationStartUp.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Startup decision [p.u.]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationShutDown.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Shutdown decision [p.u.]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationReserveUp.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Upward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationReserveDown.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Downward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationOutput.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Output (discharge in ESS) [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_RESCurtailment.csv``

============  ==========  ==========  ==============  ==========================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==========================================
Scenario      Period      Load level  VRES Generator  Curtailed power of VRES [MW]
============  ==========  ==========  ==============  ==========================================

File ``oT_Result_RESCurtailmentEnergy.csv``

============  ==========  ==========  ==============  ==========================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==========================================
Scenario      Period      Load level  VRES Generator  Curtailed energy of VRES [GWh]
============  ==========  ==========  ==============  ==========================================

File ``oT_Result_GenerationEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Energy (discharge in ESS) [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationEmission.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   CO2 emission [Mt CO2]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyOutput.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Output (discharge in ESS) [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_TechnologyCharge.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Consumption (charge in ESS) [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_RESTechnologyCurtailment.csv``

============  ==========  ==========  ==============  ==========================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==========================================
Scenario      Period      Load level  Technology      Curtailed power of VRES [MW]
============  ==========  ==========  ==============  ==========================================

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

File ``oT_Result_RESTechnologyEnergyCurtailment.csv``

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

File ``oT_Result_ESSChargeOutput.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Charged power in ESS [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSTechnologyOutput.csv``

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

File ``oT_Result_ESSChargeEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Charged energy in ESS [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSTechnologyEnergy.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (charge in ESS) [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSTechnologyEnergy_AreaName.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Energy (charge in ESS) per area [GWh]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSGenerationReserveUp.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Upward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSGenerationReserveDown.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Downward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSTechnologyReserveUp.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Upward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSTechnologyReserveDown.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Technology  Downward operating reserve [MW]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ESSInventory.csv``

============  ==========  ==========  =========  ==============================================================================================
Identifier    Identifier  Identifier  Header     Description
============  ==========  ==========  =========  ==============================================================================================
Scenario      Period      Load level  Generator  Stored energy (SoC in batteries, reservoir energy in pumped-hydro storage power plants) [GWh]
============  ==========  ==========  =========  ==============================================================================================

File ``oT_Result_ESSInventoryUtilization.csv``

============  ==========  ==========  =========  =================================================================
Identifier    Identifier  Identifier  Header     Description
============  ==========  ==========  =========  =================================================================
Scenario      Period      Load level  Generator  ESS utilization (i.e., ratio between usage and capacity) [p.u.]
============  ==========  ==========  =========  =================================================================

File ``oT_Result_ESSSpillage.csv``

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

============  ==========  ==========  ============  ============  =========  =======================
Identifier    Identifier  Identifier  Header        Header        Header     Description
============  ==========  ==========  ============  ============  =========  =======================
Scenario      Period      Load level  Initial node  Final node    Circuit    Voltage angle [rad]
============  ==========  ==========  ============  ============  =========  =======================

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

File ``oT_Result_GenerationOandMCost.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   O&M cost for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationOperationCost.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Operation cost for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeOperationCost.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Pump        Operation cost for the consumption [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_GenerationEmissionCost.csv``

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

File ``oT_Result_GenerationEnergyRevenue.csv``

============  ==========  ==========  ==========  ==========================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================
Scenario      Period      Load level  Generator   Operation revenues for the generation [M€]
============  ==========  ==========  ==========  ==========================================

File ``oT_Result_ChargeEnergyRevenue.csv``

============  ==========  ==========  ==============  ==================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==================================================
Scenario      Period      Load level  ESS Generator   Operation revenues for the consumption/charge [M€]
============  ==========  ==========  ==============  ==================================================

File ``oT_Result_OperatingReserveUpRevenue.csv``

============  ==========  ==========  ==========  ==========================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ==========================================================
Scenario      Period      Load level  Generator   Operation revenues from the upward operating reserve [M€]
============  ==========  ==========  ==========  ==========================================================

File ``oT_Result_ESSOperatingReserveUpRevenue.csv``

============  ==========  ==========  ==============  ==========================================================
Identifier    Identifier  Identifier  Header          Description
============  ==========  ==========  ==============  ==========================================================
Scenario      Period      Load level  ESS Generator   Operation revenues from the upward operating reserve [M€]
============  ==========  ==========  ==============  ==========================================================

File ``oT_Result_OperatingReserveDwRevenue.csv``

============  ==========  ==========  ==========  ===========================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ===========================================================
Scenario      Period      Load level  Generator   Operation revenues from the downward operating reserve [M€]
============  ==========  ==========  ==========  ===========================================================

File ``oT_Result_ESSOperatingReserveDwRevenue.csv``

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

File ``oT_Result_FlexibilityESSTechnology.csv``

============  ==========  ==========  ==========  ================================================
Identifier    Identifier  Identifier  Header      Description
============  ==========  ==========  ==========  ================================================
Scenario      Period      Load level  Technology  ESS Technology variation wrt its mean value [MW]
============  ==========  ==========  ==========  ================================================
