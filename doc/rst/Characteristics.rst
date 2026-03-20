.. openTEPES documentation master file, created by Andres Ramos

Characteristics
===============

- **Investment plans for new facilities** (generators, ESS, electric lines, hydrogen pipelines, and heat pipes) to meet forecasted demand at minimum cost.

    The objective is to evaluate future needs for generation, storage, and electricity, hydrogen, and heat networks. The main results are the guidelines for the future structure of the generation, storage, and transmission systems.

    It represents a decision support system for defining the **integrated generation, storage, and transmission resource planning** (IRP, GEP+SEP+TEP) of a **large-scale electric system** at the tactical level (i.e., time horizons of 5-20 years),
    defined as a set of **generation, storage, and (electricity, hydrogen, and heat) networks dynamic investment decisions for several future years**. It is a tool for energy system planners to support the energy transition towards a **decarbonized, reliable, and affordable energy system**.
    The user predefines the expansion candidates, so the model determines the optimal decisions among them.

- **Two-stage stochastic optimization** problem that includes binary generation, storage, and electricity; hydrogen and heat network investment/retirement decisions; generation operation decisions (commitment, startup, and shutdown decisions are also binary); and electric line-switching decisions.
  Capacity expansion considers the adequacy system reserve margin, maximum CO2 emissions, and minimum and maximum energy constraints.

    If no candidates are provided the model runs without expansion, so it can be used to evaluate the operation of the system in a given year or several years. The model can also be used to evaluate the expansion of just one of the energy carriers (generation and storage, electric lines, hydrogen pipelines, or heat pipes) by providing candidates for that carrier and not for the others.

- **Economic dispatch and network-constrained unit commitment (NCUC)** of the electric system

    Economic dispatch: determines the least-cost output of the available generators to meet electricity demand over a given period, usually assuming the units are already on.

    Network-constrained unit commitment (NCUC): extends this by also deciding which generators should be turned on or off over time, while respecting transmission network limits, generator operating constraints, and system security.

- **DC Power flow (DCPF)** representation of the electric network, including ohmic losses

    DC power flow (DCPF): is a linear approximation of the electric network that models active power flows using voltage angle differences, typically assuming fixed voltage magnitudes, small angle differences, and neglecting reactive power.
    The formulation can be extended by adding line-loss terms, usually approximated in a linear or piecewise-linear form, so that transmitted power is reduced by the resistive losses of the lines while preserving the tractability of the model.

- **Energy storage systems (ESS)**, including pumped-hydro storage, batteries, demand response, electric vehicles, solar thermal, and electrolyzers

    They are technologies that store energy in one form and release it later when needed. In electric power systems, ESS help balance supply and demand, improve reliability, provide flexibility, and support the integration of variable renewable energy sources. Common examples include batteries, pumped hydro storage, and hydrogen-based storage.

- **Hydro system basin**

    Detailed representation of the hydro system based on volume and water inflow data, considering the water stream topology (hydro cascade basins)

- **Power to Hydrogen (P2H2)** representation, with hydrogen demand satisfied by electrolyzer-produced hydrogen (electricity consumed to produce hydrogen) and a hydrogen network to distribute it

    It is the conversion of electrical energy into hydrogen, typically through electrolysis, where electricity is used to split water into hydrogen and oxygen. It allows surplus or low-cost electricity, especially from renewable sources, to be stored in the form of hydrogen, which can later be used as fuel, feedstock, or for power generation, thus increasing energy system flexibility and supporting sector coupling.

- **Power to heat (P2H)** representation, with heat demand satisfied by heat pump or electric heater (electricity-consuming) production, and a heat network to distribute the heat

    It is the conversion of electrical energy into thermal energy, typically through technologies such as electric boilers or heat pumps. It enables electricity, especially from renewable sources, to be used for heating purposes, improving system flexibility and supporting the integration of variable renewable generation.

- **Solver independence**

    Any solver can be used that supports linear and mixed-integer linear programming (LP and MILP), such as Gurobi, CPLEX, CBC, GLPK, and HiGHS. The model is implemented in Python using the Pyomo optimization modeling language, which provides a high-level interface for defining optimization problems and supports multiple solvers.
