.. openTEPES documentation master file, created by Andres Ramos

Introduction
============
The *Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS* **(openTEPES)** determines the investment plans of new facilities (generators, ESS, and electric lines, hydrogen pipelines, and heat pipes)
to meet the forecasted demand at minimum cost. The objective is to evaluate the future generation, storage, and electric, hydrogen, and heat network needs.
The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

The **openTEPES** model represents a decision support system for defining the **integrated generation, storage, and transmission resource planning** (IRP, GEP+SEP+TEP) of a **large-scale electric system** at the tactical level (i.e., time horizons of 10-20 years),
defined as a set of **generation, storage, and (electricity, hydrogen, and heat) networks dynamic investment decisions for several future years**. The user pre-defines the expansion candidates, so the model determines the optimal decisions among those specified by the user.

It automatically determines optimal expansion plans that satisfy multiple attributes simultaneously. Its main features are:

- **Dynamic (perfect foresight)**: the scope of the model corresponds to several periods (years) on a long-term horizon, for example 2030, 2035 and 2040.

  It hierarchically represents the different time horizons for decision making in an electricity system:
  
  - Load level: one hour, e.g., 01-01 00:00:00+01:00 to 12-30 23:00:00+01:00

  Time division allows a user-defined flexible representation of time periods for evaluating system operation. It can also be run with chronological periods of several consecutive hours (two-hour, three-hour resolution) to reduce the computational burden without sacrificing accuracy.
  The model can be run with a single period (year) or with multiple periods (years) to allow analysis of system evolution.
  The time definition also allows the specification of disconnected representative periods (e.g., days, weeks) to evaluate system operation. The model can be run with a single period (year) or with multiple periods (years) to allow analysis of system evolution.
  The time definition can also specify unrelated representative periods (e.g., days, weeks) to evaluate system operation. The period (year) must be represented by 8736 hours because several model concepts representing the system operation are based on weeks (168 hours) or months (made of 4 weeks, 672 hours)

- **Stochastic**: several stochastic parameters are considered that can influence the optimal generation, storage and transmission expansion decisions. The model considers stochastic
  medium-term annual uncertainties (scenarios) related to the system operation. These operational scenarios are associated with renewable energy sources, energy inflows and outflows, natural water inflows, operating reserves, inertia, and electricity, hydrogen, and heat demand.
  
The objective function includes the two main quantifiable costs: the **investment costs for generation, storage, and transmission (CAPEX)** and the **expected variable operation costs (including generation, consumption, emissions, and reliability costs) (system OPEX)**.
  
The model formulates a **two-stage stochastic optimization** problem, including binary generation, storage, and electricity, hydrogen, and heat network investment/retirement decisions, generation operation decisions (commitment, startup, and shutdown decisions are also binary), and electric line-switching decisions.
Capacity expansion takes into account the adequacy system reserve margin and minimum and maximum energy constraints.

The highly detailed operation model is an electric **network-constrained unit commitment (NCUC)** based on a **tight and compact** formulation, including **operating reserves** with a
**DC power flow (DCPF)**, including electric **line-switching** decisions. The **ohmic losses of the electricity network** are considered proportional to the electric line flow. It considers different **energy storage systems (ESS)**, such us pumped-hydro storage,
battery, demand response, electric vehicles, solar thermal, electrolyzer, etc. It allows analysis of the trade-off between the investment in generation/transmission/pipeline and the investment and/or use of storage capacity.

The model also allows a representation of the **hydro system** based on volume and water inflow data considering the water stream topology (hydro cascade basins). If they are not available it runs with an energy-based representation of the hydro system.

Also, it includes a representation of **Power to Hydrogen (P2H2)** by setting the **hydrogen demand** satisfied by the production of hydrogen with electrolyzers (consume electricity to produce hydrogen) and a **hydrogen network** to distribute it.
Besides, it includes a representation of **Power to Heat (P2H)** by setting the **heat demand** satisfied by the production of heat with heat pumps or electric heater (consume electricity to produce heat) and a **heat network** to distribute it. If they are not available it runs with just the other energy carriers.

The main results of the model can be structured in these topics:
  
- **Investment**: (generation, storage, hydro reservoirs, electric lines, hydrogen pipelines, and heat pipes) investment decisions and cost
- **Operation**: unit commitment, startup, and shutdown of non-renewable units, unit output and aggregation by technologies (thermal, storage hydro, pumped-hydro storage, RES), RES curtailment, electric line, hydrogen pipeline, and heat pipe flows, line ohmic losses, node voltage angles, upward and downward operating reserves, ESS inventory levels, hydro reservoir volumes, power, hydrogen, and heat not served
- **Emissions**: CO2 emissions by unit
- **Marginal**: Locational Short-Run Marginal Costs (LSRMC), stored energy value, water volume value
- **Economic**: operation, emission, and reliability costs and revenues from operation and operating reserves
- **Flexibility**: flexibility provided by demand, by the different generation and consumption technologies, and by power not served

Results are shown in csv files and graphical plots.

openTEPES is being used by `investors, market participants, system planners, and consultants <https://opentepes.readthedocs.io/en/latest/Projects.html>`_. A careful implementation has been done to avoid numerical problems by scaling parameters, variables and equations of the optimization problem allowing the model to be used for very large-scale cases, e.g., the European system with hourly detail.
For example, a European operation case study with hourly detail has reached 39.7 million constraints and 34.7 million variables of an LP problem. The mainland Spain operation case has reached 5.2 million constraints and 6.8 million variables (1.3 million binary).
