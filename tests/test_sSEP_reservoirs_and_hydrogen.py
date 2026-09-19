"""sSEP carries reservoirs and a hydrogen network, and this says what each of them actually does.

sSEP is solved by the parametrised suite, but only its total cost is checked. The reservoir system is
the only one of its kind among the shipped cases, and a change that stopped it being built would show
up as a shift in one number, and only if the shift were large enough to notice.

The hydrogen side turned out to be a different matter, and the last test records it. sSEP prices
unserved hydrogen at 300 EUR/tH2, while a tonne takes on the order of 50 MWh of electricity to make.
Not serving is therefore the cheaper answer everywhere, and the solve leaves all 425.6 tH2 of the
week's demand unserved and runs the electrolyzers at zero. The pipelines still carry flow, up to their 13.4 tH2/h
rating in most (pipe, hour) pairs, but with nothing produced and nothing delivered those are loop
flows that cancel at every node and cost nothing. Being free, they land wherever the solver leaves
them: the count of pipe-hours carrying flow moves from one run to the next, which is why it is not
asserted.

So the hydrogen coverage sSEP is credited with is construction only, not operation. Closing that
needs a data decision on the case: a penalty above the cost of making hydrogen, or a hydrogen source
unit. The test below fails the day that is done, which is the point of it.
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
def test_the_hydrogen_sector_is_built_but_makes_nothing(solved):
    """A gap written down, not a behaviour defended. Invert this test when the case is repriced."""
    assert solved.pIndHydrogen() == 1, "sSEP is the case that carries the hydrogen network"
    assert len(solved.pa) > 0, "no hydrogen pipeline was read"

    pConsumed = sum(solved.pDuration[p, sc, n]() * solved.vESSTotalCharge[p, sc, n, el]()
                    for p, sc, n in solved.psn for el in solved.el if (p, el) in solved.peh)
    pUnserved = sum(solved.pDuration[p, sc, n]() * solved.vH2NS[p, sc, n, nd]()
                    for p, sc, n in solved.psn for nd in solved.nd)
    pDemand   = sum(solved.pDuration[p, sc, n]() * solved.pDemandH2[p, sc, n, nd]
                    for p, sc, n in solved.psn for nd in solved.nd)

    assert pDemand > 0.0, "sSEP carries no hydrogen demand at all"
    assert pConsumed == pytest.approx(0.0, abs=1e-6), (
        f"the electrolyzers drew {pConsumed:.4f} GWh, so hydrogen is being made and this test is out of date")
    assert pUnserved == pytest.approx(pDemand, rel=1e-6), (
        f"{pDemand - pUnserved:.4f} tH2 of {pDemand:.4f} tH2 is now served, so this test is out of date")
