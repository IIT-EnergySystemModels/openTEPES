"""A candidate pipe carries flow only once it is bought, for hydrogen and for heat.

`vH2PipeInvest` reached the objective and the consecutive-period constraint and nothing else, and
`vHeatPipeInvest` reached the heat module not at all. The flow bounds come from the rating of every
real pipe, candidate or not, so the capacity of a candidate was available for nothing: buying it was
pure cost against no benefit, a cost-minimising model bought none of it, and used it in full. The
investment cost then reads 0.0, which looks like a plan that chose not to expand. Reported as
issue #183.

No case in the repository defines a candidate pipe, so the two fixtures below make one. Each turns
the pipes of a bundled case into candidates by giving them a fixed investment cost, which is the only
condition the defect needs.
"""
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from openTEPES.openTEPES import openTEPES_run

CASES = Path(__file__).resolve().parents[1] / "openTEPES" / "cases"


def _copy(case, tmp_path):
    dst = os.path.join(str(tmp_path), case)
    shutil.copytree(CASES / case, dst, ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))
    return dst


def _one_week(case_dir, case):
    """The truncation the other solve fixtures use: the first 168 hours, one stage standing in for the year."""
    duration = os.path.join(case_dir, f"oT_Data_Duration_{case}.csv")
    df = pd.read_csv(duration, index_col=[0, 1, 2])
    df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
    df.to_csv(duration)

    res_energy = os.path.join(case_dir, f"oT_Data_RESEnergy_{case}.csv")
    if os.path.exists(res_energy):
        df = pd.read_csv(res_energy, index_col=[0, 1])
        df["RESEnergy"] = np.nan
        df.to_csv(res_energy)

    stage = os.path.join(case_dir, f"oT_Data_Stage_{case}.csv")
    df = pd.read_csv(stage, index_col=[0])
    df.iloc[:, df.columns.get_loc("Weight")] = 52
    df.to_csv(stage)


def _make_candidates(case_dir, case, kind):
    """Turn every pipe of a case into a candidate, by giving it a fixed investment cost."""
    network = os.path.join(case_dir, f"oT_Data_Network{kind}_{case}.csv")
    df = pd.read_csv(network)
    df["FixedInvestmentCost"] = 10.0
    df["FixedChargeRate"] = 0.1
    df.to_csv(network, index=False)


def _decline_the_investment(case_dir, case, kind):
    """Set the network expansion indicator to 2, ignore investments, which fixes every decision at zero.

    An InvestmentUp of 0.0 cannot serve here: the model reads a zero upper bound as "not given" and
    replaces it by 1.0, for the pipes as for every other candidate.
    """
    option = os.path.join(case_dir, f"oT_Data_Option_{case}.csv")
    df = pd.read_csv(option)
    df[f"IndBinNet{kind}Invest"] = 2
    df.to_csv(option, index=False)


def _case(case, tmp_path, kind, candidates=False, declined=False):
    """The case over one week, its pipes left as they are or turned into candidates."""
    case_dir = _copy(case, tmp_path)
    _one_week(case_dir, case)
    if candidates:
        _make_candidates(case_dir, case, kind)
    if declined:
        _decline_the_investment(case_dir, case, "H2" if kind == "Hydrogen" else kind)
    return dict(DirName=str(tmp_path), CaseName=case, SolverName="highs", pIndLogConsole=0, pIndOutputResults=0)


def _worst_excess(mTEPES, flow, invest, frw, bck, psn_pipes, candidates):
    """The most any candidate pipe carries beyond the capacity bought for it."""
    pWorst = 0.0
    for p, sc, n, ni, nf, cc in psn_pipes:
        if (p, ni, nf, cc) not in candidates:
            continue
        pFlow = flow[p, sc, n, ni, nf, cc]() or 0.0
        pBought = invest[p, ni, nf, cc]() or 0.0
        pLimit = (frw[ni, nf, cc] if pFlow >= 0.0 else bck[ni, nf, cc]) * pBought
        pWorst = max(pWorst, abs(pFlow) - pLimit)
    return pWorst


@pytest.mark.solve
def test_a_candidate_hydrogen_pipe_carries_no_more_than_it_bought(tmp_path):
    """sSEP over a week, its 15 hydrogen pipes all candidates and free to buy."""
    mTEPES = openTEPES_run(**_case("sSEP", tmp_path, "Hydrogen", candidates=True))

    assert mTEPES.pc, "the fixture did not create any candidate hydrogen pipe"
    pWorst = _worst_excess(mTEPES, mTEPES.vFlowH2, mTEPES.vH2PipeInvest,
                           mTEPES.pH2PipeNTCFrw, mTEPES.pH2PipeNTCBck, mTEPES.psnpa, mTEPES.ppc)
    assert pWorst <= 1e-6, f"a candidate pipe carries {pWorst:.4f} tH2/h more than the capacity bought for it"


@pytest.mark.solve
def test_hydrogen_capacity_declined_is_not_used(tmp_path):
    """Capacity the case wants, and is not allowed to buy, stays unused.

    Two solves of the same week. In the first the pipes are as the case ships them, existing, and
    they carry hydrogen, which is what makes the second solve meaningful. In the second they are
    candidates and the case declines to expand, so nothing is bought. The flow has to be zero.
    Without the bound the second solve moves as much hydrogen as the first at an investment cost of
    exactly 0.0, which is the defect reported in #183.
    """
    pExisting = openTEPES_run(**_case("sSEP", tmp_path / "existing", "Hydrogen"))
    pWanted = max(abs(pExisting.vFlowH2[k]() or 0.0) for k in pExisting.psnpa)
    assert pWanted > 1e-6, "the hydrogen network carries nothing even when it is free, so this proves nothing"

    mTEPES = openTEPES_run(**_case("sSEP", tmp_path / "declined", "Hydrogen", candidates=True, declined=True))
    assert mTEPES.pc, "the fixture did not create any candidate hydrogen pipe"
    pUsed = max(abs(mTEPES.vFlowH2[k]() or 0.0) for k in mTEPES.psnpa)
    assert pUsed <= 1e-6, (
        f"a pipe that could not be bought carries {pUsed:.4f} tH2/h, against {pWanted:.4f} when it exists")


@pytest.mark.solve
def test_a_candidate_heat_pipe_carries_no_more_than_it_bought(tmp_path):
    """9n_heat over a week, both heat pipes candidates and free to buy."""
    mTEPES = openTEPES_run(**_case("9n_heat", tmp_path, "Heat", candidates=True))

    assert mTEPES.hc, "the fixture did not create any candidate heat pipe"
    pWorst = _worst_excess(mTEPES, mTEPES.vFlowHeat, mTEPES.vHeatPipeInvest,
                           mTEPES.pHeatPipeNTCFrw, mTEPES.pHeatPipeNTCBck, mTEPES.psnha, mTEPES.phc)
    assert pWorst <= 1e-6, f"a candidate heat pipe carries {pWorst:.4f} GW more than the capacity bought for it"


@pytest.mark.solve
def test_heat_capacity_declined_is_not_used(tmp_path):
    """The same two solves on the heat network."""
    pExisting = openTEPES_run(**_case("9n_heat", tmp_path / "existing", "Heat"))
    pWanted = max(abs(pExisting.vFlowHeat[k]() or 0.0) for k in pExisting.psnha)
    assert pWanted > 1e-6, "the heat network carries nothing even when it is free, so this proves nothing"

    mTEPES = openTEPES_run(**_case("9n_heat", tmp_path / "declined", "Heat", candidates=True, declined=True))
    assert mTEPES.hc, "the fixture did not create any candidate heat pipe"
    pUsed = max(abs(mTEPES.vFlowHeat[k]() or 0.0) for k in mTEPES.psnha)
    assert pUsed <= 1e-6, (
        f"a heat pipe that could not be bought carries {pUsed:.4f} GW, against {pWanted:.4f} when it exists")


def test_no_bundled_case_is_affected():
    """Every case in the repository has a fixed investment cost of zero on every pipe.

    The candidate sets are empty there, the two constraint blocks build no entries, and no shipped
    result moves. The pinned objective costs in test_run.py are the check that they do not.
    """
    pSeen = 0
    for _case in sorted(CASES.iterdir()):
        for _kind in ("Hydrogen", "Heat"):
            _f = _case / f"oT_Data_Network{_kind}_{_case.name}.csv"
            if not _f.exists():
                continue
            _df = pd.read_csv(_f)
            if "FixedInvestmentCost" not in _df.columns:
                continue
            pSeen += 1
            assert _df["FixedInvestmentCost"].fillna(0.0).eq(0.0).all(), (
                f"{_f.name} carries a candidate pipe, so this fix changes that case and its pinned cost"
            )
    assert pSeen > 0, "no hydrogen or heat network table found, so the check proves nothing"
