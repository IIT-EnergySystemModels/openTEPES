.. openTEPES documentation master file, created by Andres Ramos

Introduction
============
The *Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS* **(openTEPES)** determines the investment plans of new facilities (generators, ESS and lines)
for supplying the forecasted demand at minimum cost. Tactical planning is concerned with time horizons of 10-20 years. Its objective is to evaluate the future generation, storage and network needs.
The main results are the guidelines for the future structure of the generation and transmission systems.

The **openTEPES** model presents a decision support system for defining the generation and transmission expansion plan of a large-scale electric system at a tactical level,
defined as a set of generation and network investment decisions for future years. The expansion candidate, generators, ESS and lines, are pre-defined by the user, so the model determines
the optimal decisions among those specified by the user.

It determines automatically optimal expansion plans that satisfy simultaneously several attributes. Its main characteristics are:

- **Static**: the scope of the model corresponds to a single year at a long-term horizon, 2030 or 2040 for example.

  It represents hierarchically the different time scopes to take decisions in an electric system:
  
  - Period: one year
  - Load level: 2030-01-01T00:00:00+01:00 to 2030-12-30T23:00:00+01:00

  The time division allows a flexible representation of the periods for evaluating the system operation. Additionally, it can be run with chronological periods of several consecutive hours (bi-hourly, tri-hourly resolution)
  to allow decreasing the computational burden without accuracy loss.

- **Stochastic**: several stochastic parameters that can influence the optimal generation and transmission expansion decisions are considered. The model considers stochastic
  medium-term yearly uncertainties (scenarios) related to the system operation. These operation scenarios are associated with renewable energy sources and electricity demand.
  
The objective function incorporates the two main quantifiable costs: **generation and transmission investment cost (CAPEX)** and **expected variable operation costs (including generation emission and reliability costs) (system OPEX)**.
  
The model formulates a stochastic optimization problem including generation and network binary investment decisions and operation decisions (commitment, startup and shutdown decisions are also binary).

The operation model is a **network constrained unit commitment (NCUC)** based on a **tight and compact** formulation including operating reserves with a
**DC power flow (DCPF)**. Network ohmic losses are considered proportional to the line flow. It considers different **energy storage systems (ESS)**, e.g., pumped-storage hydro,
battery, etc. It allows analyzing the trade-off between the investment in generation/transmission and the investment or use of storage capacity. 

The main results of the model can be structured in these topics:
  
- **Investment**: investment decisions and cost
- **Operation**: the output of different units and aggregation by technologies (thermal, storage hydro, pumped-storage hydro, RES), RES curtailment, line flows, line ohmic losses, node voltage angles
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC)

A careful implementation has been done to avoid numerical problems by scaling parameters, variables and equations of the optimization problem allowing the model to be used for large-scale cases, e.g., the European system with hourly detail.