.. openTEPES documentation master file, created by Andres Ramos

Introduction
============
The *Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS* **(openTEPES)** determines the investment plans of new facilities (generators, ESS, and electric lines and hydrogen pipelines)
for supplying the forecasted demand at minimum cost. Its objective is to evaluate the future generation, storage, and electric and hydrogen network needs.
The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

The **openTEPES** model presents a decision support system for defining the integrated generation, storage, and transmission expansion plan (GEP+SEP+TEP) of a **large-scale electric system** at a tactical level (i.e., time horizons of 10-20 years),
defined as a set of **generation, storage, and electric and hydrogen networks dynamic investment decisions for multiple future years**. The user pre-defined the expansion candidates, so the model determines the optimal decisions among those specified by the user.

It determines automatically optimal expansion plans that satisfy simultaneously several attributes. Its main characteristics are:

- **Dynamic**: the scope of the model corresponds to several periods (years) at a long-term horizon, 2030, 2035 and 2040 for example.

  It represents hierarchically the different time scopes to take decisions in an electric system:
  
  - Load level: one hour, e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00

  The time division allows a user-defined flexible representation of the periods for evaluating the system operation. Moreover, it can be run with chronological periods of several consecutive hours (bi-hourly, tri-hourly resolution) to decrease the computational burden without losing accuracy. The model can be run with a single period (year) or with several periods (years) to allow the analysis of the system evolution. The time definition allows also to specify disconnected representative periods (e.g., days, weeks) to evaluate the system operation.
  The model can be run with a single period (year) or with several periods (years) to allow the analysis of the system evolution. The time definition can also specify disconnected representative periods (e.g., days, weeks) to evaluate the system operation.
  The period (year) must be represented by 8736 hours because several model concepts representing the system operation are based on weeks (168 hours) or months (made of 4 weeks, 672 hours).

- **Stochastic**: several stochastic parameters that can influence the optimal generation, storage, and transmission expansion decisions are considered. The model considers stochastic
  medium-term yearly uncertainties (scenarios) related to the system operation. These operation scenarios are associated with renewable energy sources, energy inflows and outflows, natural water inflows, operating reserves, inertia, and electricity and hydrogen demand.
  
The objective function incorporates the two main quantifiable costs: **generation, storage, and transmission investment cost (CAPEX)** and **expected variable operation costs (including generation, consumption, emission, and reliability costs) (system OPEX)**.
  
The model formulates a **two-stage stochastic optimization** problem, including generation, storage, and electric and hydrogen network binary investment/retirement decisions, generation operation decisions (commitment, startup, and shutdown decisions are also binary), and electric line-switching decisions.
The capacity expansion considers adequacy system reserve margin and minimum and maximum energy constraints.

The very detailed operation model is an electric **network-constrained unit commitment (NCUC)** based on a **tight and compact** formulation, including **operating reserves** with a
**DC power flow (DCPF)**, including electric **line switching** decisions. **Electric network ohmic losses** are considered proportional to the electric line flow. It considers different **energy storage systems (ESS)**, e.g., pumped-hydro storage,
battery, demand response, electric vehicles, solar thermal, alkaline water electrolyzer, etc. It allows analyzing the trade-off between the investment in generation/transmission/pipeline and the investment and/or use of storage capacity.

The model allows also a representation of the **hydro system** based on volume and water inflow data considering the water stream topology (hydro cascade basins). If they are not available it runs with an energy-based representation of the hydro system.

Also, it includes a representation of **Power to Hydrogen (P2H2)** by setting the **hydrogen demand** satisfied by the production of hydrogen with electrolyzers (consume electricity to produce hydrogen) and a **hydrogen network** to distribute it. If they are not available it runs with just the electric system.

The main results of the model can be structured in these topics:
  
- **Investment**: (generation, storage, hydro reservoirs, electric lines and hydrogen pipelines) investment decisions and cost
- **Operation**: unit commitment, startup, and shutdown of non-renewable units, unit output and aggregation by technologies (thermal, storage hydro, pumped-hydro storage, RES), RES curtailment, electric line and hydrogen pipeline flows, line ohmic losses, node voltage angles, upward and downward operating reserves, ESS inventory levels, hydro reservoir volumes, power and hydrogen not served
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC), stored energy value, water volume value
- **Economic**: operation, emission, and reliability costs and revenues from operation and operating reserves
- **Flexibility**: flexibility provided by demand, by the different generation and consumption technologies, and by power not served

Results are shown in csv files and graphical plots.

openTEPES is being used by `investors, market participants, system planners, and consultants <https://opentepes.readthedocs.io/en/latest/Projects.html>`_. A careful implementation has been done to avoid numerical problems by scaling parameters, variables and equations of the optimization problem allowing the model to be used for very large-scale cases, e.g., the European system with hourly detail.
For example, a European operation case study with hourly detail has reached 22 million constraints and 27 million variables of an LP problem. The mainland Spain operation case has reached 5 million constraints and 5 million variables (1.3 million binary).
