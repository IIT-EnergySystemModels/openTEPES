.. openTEPES documentation master file, created by Andres Ramos

Introduction
============
The *Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS* **(openTEPES)** determines investment plans for new facilities (generators, ESS, electric lines, hydrogen pipelines, and heat pipes) to meet forecasted demand at minimum cost.
The objective is to evaluate future needs for generation, storage, and electricity, hydrogen, and heat networks. The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

The **openTEPES** model represents a decision support system for defining the **integrated generation, storage, and transmission resource planning** (IRP, GEP+SEP+TEP) of a **large-scale electric system** at the tactical level (i.e., time horizons of 5-20 years),
defined as a set of **generation, storage, and (electricity, hydrogen, and heat) networks dynamic investment decisions for several future years**. It is a tool for energy system planners to support the energy transition towards a **decarbonized, reliable, and affordable energy system**.
The user predefines the expansion candidates, so the model determines the optimal decisions among them

It automatically determines optimal expansion plans that satisfy multiple attributes simultaneously. Its main features are:

- **Dynamic (perfect foresight)**: the scope of the model corresponds to several periods (years) on a long-term horizon, for example, 2030, 2035, and 2040.

  It hierarchically represents the different time horizons for decision-making in an electricity (hydrogen or heat) system:
  
- Load level: one hour, e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00, or **quarter of an hour**, e.g., 01-01 00:00:00+01:00 to 30-12 23:45:00+01:00
  The time division allows a user-defined flexible representation of the periods for evaluating the system operation. Moreover, it can be run with time intervals of several consecutive hours (bi-hourly or tri-hourly resolution,
  depending on the hourly or quarter-hour definition) to reduce computational burden without sacrificing accuracy. The model can be run with a single period (year) or several periods (years) to analyze the system’s evolution.
  The time definition also allows for specifying disconnected representative periods (e.g., days or weeks) to evaluate system operation. The period (year) must be represented by 8736 hours because several model features representing
  the system operation are based on weeks (168 hours) or lunar months (made of 4 weeks, 672 hours)

- **Stochastic**: several stochastic parameters are considered that can influence the optimal generation, storage, and transmission expansion decisions. The model considers stochastic
  medium-term annual uncertainties (scenarios) related to the system operation. These **operational scenarios** are associated with renewable energy sources, energy inflows and outflows, natural water inflows, operating reserves, ramp reserves, inertia, and electricity, hydrogen, and heat demand.
  
The objective function includes two main quantifiable costs: **investment costs for generation, storage, and transmission (CAPEX)** and **expected variable operation costs (including generation, consumption, emissions, and reliability costs) (system OPEX)**.
  
The model formulates a **two-stage stochastic optimization** problem that includes binary generation, storage, and electricity; hydrogen and heat network investment/retirement decisions; generation operation decisions (commitment, startup, and shutdown decisions are also binary); and electric line-switching decisions.
Capacity expansion considers the adequacy system reserve margin, maximum CO2 emissions, and minimum and maximum energy constraints.

The highly detailed operational model is an electric network-constrained unit commitment (NCUC) based on a tight, compact formulation that includes operating reserves and electric line-switching decisions via DC power flow (DCPF).
**Ohmic losses** in the electrical network are assumed to be proportional to the electrical line flow. It considers various **energy storage systems (ESS)**, including pumped-hydro storage, batteries, demand response, electric vehicles, solar thermal, and electrolyzers.

The model also allows a representation of the **hydro system** based on volume and water inflow data, considering the water stream topology (**hydro cascade basins**). If they are unavailable, it runs using an energy-based representation of the hydro system.

Also, it includes a **Power-to-Hydrogen (P2H2)** representation, with hydrogen demand satisfied by electrolyzer-produced hydrogen (electricity consumed to produce hydrogen) and a hydrogen network to distribute it. Besides, it includes a **Power-to-Heat (P2H)** representation,
with heat demand satisfied by heat pump or electric heater (electricity-consuming) production, and a heat network to distribute the heat. If they are unavailable, it runs on just the other energy carriers.
The main results of the model can be structured into these topics:
  
- **Investment**: (generation, storage, hydro reservoirs, electric lines, hydrogen pipelines, and heat pipes) investment decisions and cost
- **Operation**: unit commitment, startup, and shutdown of non-renewable units, unit output and aggregation by technologies (thermal, storage hydro, pumped-hydro storage, RES), RES curtailment, electric line, hydrogen pipeline, and heat pipe flows, line ohmic losses, node voltage angles, upward and downward operating reserves, upward and downward ramp reserves, ESS inventory levels, hydro reservoir volumes, power, hydrogen, and heat not served
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC), stored energy value, water volume value
- **Economic**: operation, emission, and reliability costs and revenues from operation, operating reserves, and ramp reserves
- **Flexibility**: flexibility provided by demand, by the different generation and consumption technologies, and by power not served

Results are shown in csv files and graphical plots.

openTEPES is being used by `investors, market participants, system planners, and consultants <https://opentepes.readthedocs.io/en/latest/Projects.html>`_. A careful implementation has been carried out to avoid numerical problems by scaling parameters, variables, and equations of the optimization problem, allowing the model to be used for very large-scale cases, e.g., the European system with hourly detail.
For example, a European operation case study with hourly detail has reached 39.7 million constraints and 34.7 million variables of an LP problem. The mainland Spain operation case has reached 5.2 million constraints and 6.8 million variables (1.3 million binary).
