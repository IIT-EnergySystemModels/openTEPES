.. openTEPES documentation master file, created by Andres Ramos

Introduction
============
The *Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS* **(openTEPES)** determines the investment plans of new facilities (generators, ESS, and lines)
for supplying the forecasted demand at minimum cost. Tactical planning is concerned with time horizons of 10-20 years. Its objective is to evaluate the future generation, storage, and network needs.
The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

The **openTEPES** model presents a decision support system for defining the integrated generation, storage, and transmission expansion plan (GEP+SEP+TEP) of a **large-scale electric system** at a tactical level,
defined as a set of generation, storage, and network investment decisions for future years. The expansion candidates are pre-defined by the user, so the model determines the optimal decisions among those specified by the user.

It determines automatically optimal expansion plans that satisfy simultaneously several attributes. Its main characteristics are:

- **Dynamic**: the scope of the model corresponds to several periods (years) at a long-term horizon, 2030 to 2040 for example.

  It represents hierarchically the different time scopes to take decisions in an electric system:
  
  - Load level: one hour, e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00

  The time division allows a user-defined flexible representation of the periods for evaluating the system operation. Moreover, it can be run with chronological periods of several consecutive hours (bi-hourly, tri-hourly resolution)
  to allow decreasing the computational burden without accuracy loss.

- **Stochastic**: several stochastic parameters that can influence the optimal generation, storage, and transmission expansion decisions are considered. The model considers stochastic
  medium-term yearly uncertainties (scenarios) related to the system operation. These operation scenarios are associated with renewable energy sources, energy inflows and outflows, operating reserves, inertia, and electricity demand.
  
The objective function incorporates the two main quantifiable costs: **generation, storage, and transmission investment cost (CAPEX)** and **expected variable operation costs (including generation, consumption, emission, and reliability costs) (system OPEX)**.
  
The model formulates a **two-stage stochastic optimization** problem including generation, storage, and network binary investment/retirement decisions, generation operation decisions (commitment, startup, and shutdown decisions are also binary) and line switching decisions.
The capacity expansion considers adequacy system reserve margin constraints.

The operation model is a **network constrained unit commitment (NCUC)** based on a **tight and compact** formulation including **operating reserves** with a
**DC power flow (DCPF)** including **line switching** decisions. **Network ohmic losses** are considered proportional to the line flow. It considers different **energy storage systems (ESS)**, e.g., pumped-hydro storage,
battery, etc. It allows analyzing the trade-off between the investment in generation/storage/transmission and the investment or use of storage capacity.

The main results of the model can be structured in these topics:
  
- **Investment**: investment decisions and cost
- **Operation**: unit commitment, startup, and shutdown of non-renewable units, unit output and aggregation by technologies (thermal, storage hydro, pumped-hydro storage, RES), RES curtailment, line flows, line ohmic losses, node voltage angles, upward and downward operating reserves, ESS inventory levels
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC), water energy value
- **Economic**: operation, emission, and reliability costs and revenues from operation and operating reserves
- **Flexibility**: flexibility provided by demand, by the different generation and consumption technologies, and by power not served

Results are shown in csv files and graphical plots.

A careful implementation has been done to avoid numerical problems by scaling parameters, variables and equations of the optimization problem allowing the model to be used for large-scale cases, e.g., the European system with hourly detail.
