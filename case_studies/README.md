# Case studies

This folder holds two **study-specific case datasets**, each associated with a
published paper by E.F. Álvarez and co-authors. They are kept in the repository
so the results of those papers can be reproduced and inspected.

They are distinct from the cases in [`openTEPES/cases/`](../openTEPES/cases): those
are the small reference cases (`9n`, `sSEP`, `RTS24`, …) that ship with the PyPI
distribution, are documented on the QA/Download pages, and run in the automated
test suite. The case studies here are **larger, paper-specific, not packaged, and
not part of CI**.

## `Optimal-Power-Grid-Design/`

Transmission-expansion-planning case on a Reliability Test System (RTS) network at
a 2030 horizon (`RTS_S2P1_2030`), with AC-network detail (line reactance and
cables, bus shunts, reactive demand, inertia). It accompanies:

> E.F. Álvarez, J.C. López, L. Olmos, A. Ramos, "An Optimal Expansion Planning of
> Power Systems Considering Cycle-Based AC Optimal Power Flow", *Sustainable
> Energy, Grids and Networks*, May 2024.
> [10.1016/j.segan.2024.101413](https://doi.org/10.1016/j.segan.2024.101413)

## `TSO-DSO_coordination/`

TSO–DSO coordination case on the RTS24 network (`RTS24a`, with `CASE-A` and
`CASE-B` variants) that embeds distribution-level microgrids and local flexibility
resources alongside the transmission system. It accompanies:

> E.F. Álvarez, L. Olmos, A. Ramos, K. Antoniadou-Plytaria, D. Steen, L.A. Tuan,
> "Values and Impacts of Incorporating Local Flexibility Services in Transmission
> Expansion Planning", *Electric Power Systems Research* (PSCC 2022), 2022.
> [10.1016/j.epsr.2022.108480](https://doi.org/10.1016/j.epsr.2022.108480)

See [`doc/md/Papers.md`](../doc/md/Papers.md) for the full publication list and links.
