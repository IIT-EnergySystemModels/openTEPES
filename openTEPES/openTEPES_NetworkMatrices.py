"""Network matrices derived from the branch data, and the physics checks that use them.

One place that turns ``oT_Data_Network`` into the objects that need a view of the whole network rather than one branch at a
time. Two consumers today:

  * ``ptdf`` builds the DC power transfer distribution factors, so a case can run flow-based coupling without the user
    computing them in another tool and pasting in a table openTEPES cannot check against its own reactances.
  * ``branch_residuals`` recomputes each AC branch flow from the bus voltages and compares it with the flow the model
    reports, so a user can tell whether a solved case satisfies the AC equations.

They share the branch enumeration, which is the reason this is one module and not two. Assembling it twice would let the
two copies disagree about which branches are in service, what a tap means, or whether a DC link belongs in a Kirchhoff
network.

**DC links are excluded everywhere here.** A point-to-point DC link carries what its converters are told to carry, so it
does not obey Kirchhoff's voltage law and has no place in a susceptance matrix.

**The B matrix uses 1/x and ignores the tap on purpose.** It has to reproduce what the model's own angle formulation
does, which is ``(theta_i - theta_j) / pLineX`` with no tap factor. Introducing the tap here would make the derived PTDF
disagree with the very constraint it replaces. The AC formulations do carry the tap; the DC one does not, and this
follows the DC one because that is what PTDF stands in for.
"""
from __future__ import annotations

import cmath
import math


def _val(pParam, pKey):
    """Read a Pyomo Param entry whether or not it is mutable."""
    pEntry = pParam[pKey]
    return float(pEntry() if callable(pEntry) else pEntry)


def ac_branches(mTEPES, p):
    """The AC branches in service in period ``p``.

    Returns a list of ``(la, r, x, bsh, tap)`` with ``la`` the ``(ni, nf, cc)`` key.
    """
    # mTEPES.laa is lea | lca, the model's own AC line set, so the DC links are already out. Deciding it here from the
    # line type again would be a second opinion on the same question and could disagree with the rest of the model.
    pOut = []
    for la in mTEPES.laa:
        if (p,) + tuple(la) not in mTEPES.pla:
            continue
        # the tap and the charging susceptance are AC-only inputs: a DC case reaches this function through the PTDF path
        # and carries neither, so both fall back to their neutral values rather than raising.
        pBsh = _val(mTEPES.pLineBsh,       la) if hasattr(mTEPES, 'pLineBsh')       else 0.0
        pTap = _val(mTEPES.pLineTapFactor, la) if hasattr(mTEPES, 'pLineTapFactor') else 1.0
        pOut.append((la, _val(mTEPES.pLineR, la), _val(mTEPES.pLineX, la), pBsh, pTap))
    return pOut


def b_matrices(mTEPES, p):
    """``(Bbus, Bf, nodes, index)`` for the DC network of period ``p``.

    ``Bbus`` is the nodal susceptance matrix and ``Bf`` maps bus angles to branch flows, both on ``1/x``.
    """
    import numpy as np

    pNodes  = list(mTEPES.nd)
    pIndex  = {nd: i for i, nd in enumerate(pNodes)}
    pBranch = ac_branches(mTEPES, p)
    nb, nl  = len(pNodes), len(pBranch)

    pBbus = np.zeros((nb, nb))
    pBf   = np.zeros((nl, nb))
    for l, (la, _, x, _, _) in enumerate(pBranch):
        i, j = pIndex[la[0]], pIndex[la[1]]
        y = 1.0 / x
        pBbus[i, i] += y
        pBbus[j, j] += y
        pBbus[i, j] -= y
        pBbus[j, i] -= y
        pBf[l, i]   += y
        pBf[l, j]   -= y
    return pBbus, pBf, [la for la, _, _, _, _ in pBranch], pIndex


def ptdf(mTEPES, p, pTolerance=1e-10, pSlack=None):
    """Power transfer distribution factors for period ``p``, as ``{(ni, nf, cc, nd): value}``.

    ``PTDF = Bf * inv(Bbus)`` with the reference node's row and column removed and its column left at zero. Entries
    below ``pTolerance`` are dropped: they contribute nothing to the flow and keeping them would store a dense
    branches-by-nodes block for no gain.

    The factors depend on the reference node; the FLOWS they produce do not, as long as the net positions sum to zero.
    """
    import numpy as np

    pBbus, pBf, pBranches, pIndex = b_matrices(mTEPES, p)
    # The reference is carried as the single member of rf. It is an argument as well so the slack-independence of the
    # FLOWS can be tested: the factors change with the reference, the flows a balanced injection produces do not.
    pSlack = str(mTEPES.rf.first()) if pSlack is None else str(pSlack)
    if pSlack not in pIndex:
        raise ValueError(f'ReferenceNode {pSlack} is not a node of the system, so the PTDF has no reference')

    pKeep = [i for i in range(len(pIndex)) if i != pIndex[pSlack]]
    if not pKeep:
        return {}
    # A singular reduced Bbus means the AC network is not connected once the reference is removed, which PTDF cannot
    # represent: an island with no path to the reference has no distribution factor.
    try:
        pInv = np.linalg.inv(pBbus[np.ix_(pKeep, pKeep)])
    except np.linalg.LinAlgError as e:
        raise ValueError('the AC network is singular with the reference node removed, so PTDF cannot be formed. '
                         'This normally means the AC network is split into islands.') from e

    pFull = np.zeros((len(pBranches), len(pIndex)))
    pFull[np.ix_(range(len(pBranches)), pKeep)] = pBf[:, pKeep] @ pInv

    pNodes = list(mTEPES.nd)
    return {(la[0], la[1], la[2], nd): float(pFull[l, i])
            for l, la in enumerate(pBranches)
            for i, nd in enumerate(pNodes)
            if abs(pFull[l, i]) > pTolerance}


def angles_available(mTEPES, OptModel, p, sc, n):
    """Whether a nodal voltage PHASOR can be formed at all for this solution.

    In W space the angle lives in arg(W_ij), which is a per-branch quantity: unless IndACCycle ties it to a node
    potential, vTheta is declared but appears in no constraint and the solver leaves it unset. There is then no nodal
    phasor to recompute a flow from, and the residual check below has nothing to say. Branch flow and the rectangular
    formulation both carry the phasor and are unaffected.
    """
    if hasattr(OptModel, 'vVre'):
        return True
    # EVERY node, not the first one. vTheta is unconstrained here, so the solver is free to leave some nodes set and others unset, and it does. Testing
    # only the first node reports the angles available whenever that one happens to carry a value, and _voltage then builds a phasor from None at a
    # later node. That is an intermittent crash, because which nodes come back set varies between solvers and between runs of the same solver.
    pAny = False
    for nd in mTEPES.nd:
        if (p,sc,n,nd) in mTEPES.psnnd:
            pAny = True
            if OptModel.vTheta[p,sc,n,nd].value is None:
                return False
    return pAny


def _voltage(mTEPES, OptModel, p, sc, n, nd):
    """The complex bus voltage, from whichever representation the active formulation uses."""
    if hasattr(OptModel, 'vVre'):                                  # rectangular: the parts are the variables
        return complex(OptModel.vVre[p,sc,n,nd](), OptModel.vVim[p,sc,n,nd]())
    pMag = math.sqrt(max(OptModel.vW[p,sc,n,nd](), 0.0))
    return cmath.rect(pMag, OptModel.vTheta[p,sc,n,nd]())


def branch_residuals(mTEPES, OptModel, p, sc, n):
    """Worst mismatch, in MW and Mvar, between the reported branch flows and the ones the bus voltages imply.

    The comparison is the SERIES relation, ``S_ij = V_i conj((V_i - V_j) y)``, with the tap applied to the sending
    voltage. The charging susceptance is deliberately left out: it is not part of the series flow the model reports,
    and adding it here would make a correct solution look wrong.

    The flows are recomputed from the VOLTAGES rather than read from the model's flow variables. Deriving them from the
    flow variables would compare the flow equations with themselves and pass by construction.
    """
    pSBase = mTEPES.pSBase()
    wP = wQ = 0.0
    for la, r, x, _, tap in ac_branches(mTEPES, p):
        if (p,sc,n) + tuple(la) not in mTEPES.psnla:
            continue
        pVi = _voltage(mTEPES, OptModel, p, sc, n, la[0]) * tap
        pVj = _voltage(mTEPES, OptModel, p, sc, n, la[1])
        pSij = pVi * ((pVi - pVj) / complex(r, x)).conjugate()
        wP = max(wP, abs(pSij.real - OptModel.vFlowElec    [(p,sc,n) + tuple(la)]() / pSBase) * pSBase * 1e3)
        wQ = max(wQ, abs(pSij.imag - OptModel.vFlowReactFrw[(p,sc,n) + tuple(la)]() / pSBase) * pSBase * 1e3)
    return wP, wQ
