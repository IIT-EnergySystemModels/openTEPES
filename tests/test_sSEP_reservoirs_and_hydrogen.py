"""sSEP carries reservoirs, a hydrogen network and a candidate solar farm, and this checks all three.

sSEP is solved by the parametrised suite, but only its total cost is checked. The reservoir system and
the hydrogen chain are the only ones of their kind among the distributed cases, and a change that
stopped either being built would show up as a shift in one number, and only if the shift were large
enough to notice.

The hydrogen chain reached its present state by a detour worth recording. Solved with the annual CO2
cap of sSEP applied to the representative week, the case served none of its 425.62 tH2 and ran its
electrolyzers at zero, and that looked like a question of how unserved hydrogen is priced. It was not.
The cap was binding at 4.6 MtCO2, no unit in the case could be built, and 10.57 % of the electricity
demand went unserved, so electricity stood at its scarcity value and no hydrogen penalty below it
could compete. Two things followed: the fixtures stopped applying an annual limit to one week, and the
case gained a candidate solar farm, so that a binding cap is met by building rather than by shedding.
"""
import pytest

from openTEPES.openTEPES import openTEPES_run

from case_week import week_of_case, rows_of

CASE = "sSEP"


@pytest.fixture(scope="module")
def solved(tmp_path_factory):
    """One solve for every test here; sSEP takes about two seconds at this horizon."""
    _, run_kwargs = week_of_case(CASE, tmp_path_factory.mktemp(CASE))
    return openTEPES_run(**run_kwargs)


@pytest.mark.solve
def test_the_reservoir_system_is_built(solved):
    assert solved.pIndHydroTopology() == 1, "sSEP is the case that carries the hydro topology"
    assert len(solved.rs) > 0, "no reservoir was read"
    assert rows_of(solved, "eHydroInventory") > 0, "the reservoir volume balance was not built"


@pytest.mark.solve
def test_the_reservoirs_hold_water_and_move_it(solved):
    """Volumes stay inside their bounds, and at least one reservoir is not sitting still."""
    pMoved = 0
    for p, sc in solved.ps:
        pLevels = [n for p2, sc2, n in solved.psn if (p2, sc2) == (p, sc)]
        for rs in solved.rs:
            pVolumes = []
            for n in pLevels:
                pVolume = solved.vReservoirVolume[p, sc, n, rs]()
                assert solved.pMinVolume[p, sc, n, rs] - 1e-6 <= pVolume <= solved.pMaxVolume[p, sc, n, rs] + 1e-6, (
                    f"{rs} holds {pVolume:.4f} hm3 at {n}, outside its bounds")
                pVolumes.append(pVolume)
            if pVolumes and max(pVolumes) - min(pVolumes) > 1e-6:
                pMoved += 1
    assert pMoved > 0, "every reservoir kept the same volume all week, so the topology is decorative here"


@pytest.mark.solve
def test_the_hydro_units_generate(solved):
    pOutput = sum(solved.pDuration[p, sc, n]() * solved.vTotalOutput[p, sc, n, h]()
                  for p, sc, n in solved.psn for h in solved.h if (p, h) in solved.ph)
    assert pOutput > 0.0, "no hydro unit generated anything, so the reservoirs feed nothing"


@pytest.mark.solve
def test_the_hydrogen_chain_runs_and_serves_its_demand(solved):
    """Electrolyzers draw electricity, the pipelines are there, and no tonne goes unserved."""
    assert solved.pIndHydrogen() == 1, "sSEP is the case that carries the hydrogen network"
    assert len(solved.pa) > 0, "no hydrogen pipeline was read"

    pConsumed = sum(solved.pDuration[p, sc, n]() * solved.vESSTotalCharge[p, sc, n, el]()
                    for p, sc, n in solved.psn for el in solved.el if (p, el) in solved.peh)
    pUnserved = sum(solved.pDuration[p, sc, n]() * solved.vH2NS[p, sc, n, nd]()
                    for p, sc, n in solved.psn for nd in solved.nd)
    pDemand   = sum(solved.pDuration[p, sc, n]() * solved.pDemandH2[p, sc, n, nd]
                    for p, sc, n in solved.psn for nd in solved.nd)

    assert pDemand > 0.0, "sSEP carries no hydrogen demand at all"
    assert pUnserved <= 1e-6 * pDemand, f"{pUnserved:.4f} tH2 of {pDemand:.4f} tH2 went unserved"
    assert pConsumed > 0.0, "the electrolyzers drew nothing, so the demand was met from somewhere else"


@pytest.mark.solve
def test_the_electricity_demand_is_served_as_well(solved):
    """The hydrogen is not bought with unserved electricity, which is how the cap used to pay for it."""
    pUnserved = sum(solved.pDuration[p, sc, n]() * solved.vENS[p, sc, n, nd]()
                    for p, sc, n in solved.psn for nd in solved.nd)
    pDemand   = sum(solved.pDuration[p, sc, n]() * solved.pDemandElec[p, sc, n, nd]()
                    for p, sc, n in solved.psn for nd in solved.nd)
    assert pUnserved <= 1e-6 * pDemand, (
        f"{pUnserved:.4f} GWh of {pDemand:.4f} GWh went unserved, and sSEP has capacity to spare")


@pytest.mark.solve
def test_the_candidate_solar_farm_is_built(solved):
    """sSEP is the only distributed case with a candidate generating unit, and the optimum is interior."""
    assert len(solved.gc) > 0, "no candidate generating unit was read"

    pBuilt = {gc: solved.vGenerationInvest[p, gc]() for p in solved.p for gc in solved.gc if (p, gc) in solved.pgc}
    assert pBuilt, "the candidate reached no period"
    for gc, pShare in pBuilt.items():
        assert 0.0 < pShare < 1.0, (
            f"{gc} is built at {pShare:.4f} of its rating, so the decision sits on a bound and the case "
            "pins the bound instead of an optimum")
