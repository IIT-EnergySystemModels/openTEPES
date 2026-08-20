"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_BoundTightening — shrink the AC voltage and angle bounds before the variables are declared.

This is not an optimisation to switch on later. The angle envelope that couples the branch flows to the voltage angles carries a slack of
``tan(theta_max/2) - theta_max/2`` per branch, which grows fast with the angle bound: at the +/-60 degrees RTS-GMLC ships, the slack is 3 degrees per
branch, so across a five-branch cycle the cyclic constraint has 15 degrees of room and barely binds.
See doc/design/AC_OPF_Prototype_Results.md section 4.

The tightening must be *valid*: it may only use inequalities the model already implies, so it cannot cut off the true optimum. Picking a smaller
number instead turns the relaxation into a restriction — at +/-30 degrees the RTS-GMLC objective rose 108% and at +/-20 degrees it went infeasible.

Two propagations, both derived from constraints already in the formulation.

**Angle, from the thermal limit.** The branch flow model gives ``|V_i||V_j| sin(theta_i - theta_j) = x*P - r*Q``. The apparent power through the
branch is limited, so by Cauchy-Schwarz ``|x*P - r*Q| <= Smax*sqrt(r^2+x^2) = Smax*z`` (the bound is the same either way). Dividing by the smallest the voltage product can be:

    |sin(theta_ij)| <= Smax * z / (Vmin_i * Vmin_j)      =>      |theta_ij| <= arcsin(min(1, Smax*z/(Vmin_i*Vmin_j)))

**Everything here is in per unit.** ``pLineSmax`` is in GVA and ``pSBase`` is the GVA base, so the rating has to be divided by ``pSBase`` before it
meets a per-unit impedance. Omitting that is invisible on a case whose base is 1 GVA and wrong by a factor of ten on one whose base is 100 MVA.

**The rating that the model actually implies.** The thermal limit is written on the current, ``l <= (Smax/Vmin)^2``, and the cone gives
``P^2 + Q^2 <= vW*l <= Vmax^2 * (Smax/Vmin)^2``. So the apparent power the model permits is ``Smax*Vmax/Vmin``, not ``Smax``. Using the smaller value
would tighten the angle bound by a further factor ``Vmax/Vmin`` with nothing implying it, which is exactly the kind of unjustified tightening this
module exists to avoid.

**Voltage, from the drop equation.** ``u_j = u_i - 2(r*P + x*Q) + z^2*l`` with the same bound on ``|r*P + x*Q|`` and ``0 <= l <= (Smax/Vmin)^2`` gives

    u_j >= u_i_min - 2*Smax*z        and        u_j <= u_i_max + 2*Smax*z + z^2*(Smax/Vmin)^2

Each incident branch yields a valid bound, so the tightest is the largest of the lower bounds and the smallest of the upper bounds. Sweeping to a
fixed point propagates the reference bus's fixed voltage outwards.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict

# The angle envelope divides by cos(t/2). At t = pi that is 6e-17, which turns the envelope coefficients into 1e16 and the LP into numerical
# nonsense. pi/2 keeps the worst divisor at cos(pi/4) = 0.707 and is already the default for a case that declares no limits.
MAX_ANGLE  = math.pi / 2
MAX_SWEEPS = 20
TOLERANCE  = 1e-6


def TightenACBounds(mTEPES, par, pIndLogConsole=0):
    """Compute tightened per-branch angle bounds and per-bus voltage bounds, and store them on ``par``.

    Writes ``par['pMaxAngleDiff']`` and ``par['pMinAngleDiff']`` (radians, per branch), ``par['pVMinBus']`` and ``par['pVMaxBus']`` (per unit, per bus).
    Returns a small dict of statistics for logging.
    """
    StartTime = time.time()

    branches = list(mTEPES.laa)
    vmin, vmax = par['pVMin'], par['pVMax']
    pSBase = par['pSBase']

    # --- angle bounds ------------------------------------------------------------------------------------------------------------------------------
    # The two sides are carried separately. Collapsing them to one symmetric band with min(|AngMin|, |AngMax|) cuts off range the case explicitly
    # permits: a branch declared -50 to +20 degrees would be solved at +/-20, losing 30 degrees on the negative side. This module's whole contract is
    # that it may only use inequalities the model already implies, so a tightening the data does not support does not belong here.
    pMaxAngleDiff, pMinAngleDiff, pTightened = {}, {}, 0
    for la in branches:
        z = math.sqrt(par['pLineR'][la] ** 2 + par['pLineX'][la] ** 2)
        # per unit, and at the largest apparent power the thermal limit together with the voltage band actually permits
        smax = par['pLineSmax'][la] / pSBase * vmax / vmin
        pTapF = par['pLineTapFactor'][la]
        # The declared values are used with their SIGNS. Taking abs() of each side misreads a one-sided band: a branch declared +5 to +30 degrees
        # would come out with a lower limit of -5, and one declared -30 to -5 with an upper limit of +5 — in both cases the band enforced is not the
        # band the case asked for. ConfigureACData has already checked AngMin < AngMax.
        pHi = min(par['pAngMax'][la],  MAX_ANGLE)
        pLo = max(par['pAngMin'][la], -MAX_ANGLE)
        if z <= 0.0 or smax <= 0.0:
            # No implied bound to apply — a branch with no impedance or no rating. The clamp above still matters here: the angle envelope divides by
            # cos(t/2), so a limit near pi would give cos(t/2) ~ 6e-17 and coefficients around 1e16, which no solver will handle.
            pMaxAngleDiff[la], pMinAngleDiff[la] = pHi, pLo
            continue
        # the sending-end voltage the impedance sees carries the tap, so the divisor is (Vmin_i/tau) * Vmin_j
        implied = math.asin(min(1.0, smax * z / (vmin * pTapF * vmin)))
        pMaxAngleDiff[la] = min(pHi,  implied)
        pMinAngleDiff[la] = max(pLo, -implied)
        if implied < min(pHi, -pLo) - TOLERANCE:
            pTightened += 1

    # --- voltage bounds ----------------------------------------------------------------------------------------------------------------------------
    # Only branches that are ALWAYS in service may propagate a voltage bound. eVoltageDropUp/Lo release the drop equation through a big-M on
    # vLineCommit when a candidate or switchable branch is out of service, so its drop equation is not something the model always implies — and this
    # module may only use what the model always implies. Propagating across a candidate line narrows the vW box of a node reachable only through it,
    # which can cut off the do-not-build plan.
    # mTEPES.lc (candidates) and mTEPES.ls (switchable) are already built by the time this runs and carry exactly this distinction. They are used in
    # preference to the par Series, whose index has been remapped by this point in DataConfiguration.
    # A branch also drops out of the model in periods outside its own commissioning window: SettingUpVariables fixes its vLineCommit to 0 and
    # eVoltageDropUp/Lo is skipped for it. pVMinBus and pVMaxBus are per bus and shared across every period, so a bound justified by a branch that
    # exists only from period 2 would still be imposed in period 1. Propagate only across branches that are in service in EVERY period.
    pFirst, pLast = mTEPES.p.first(), mTEPES.p.last()
    pReleasable = set(mTEPES.lc) | set(mTEPES.ls) | {
        la for la in branches
        if par['pElecNetPeriodIni'][la] > pFirst or par['pElecNetPeriodFin'][la] < pLast}
    incident = defaultdict(list)
    for la in branches:
        if la in pReleasable:
            continue
        ni, nf, cc = la
        incident[ni].append(la)
        incident[nf].append(la)

    lo = {nd: vmin ** 2 for nd in mTEPES.nd}
    hi = {nd: vmax ** 2 for nd in mTEPES.nd}
    # the reference bus voltage is the anchor the propagation spreads from
    ref = mTEPES.rf.first()
    lo[ref] = hi[ref] = par['pVNom'] ** 2

    pSweeps = 0
    for pSweeps in range(1, MAX_SWEEPS + 1):
        pMoved = 0.0
        for nd in mTEPES.nd:
            if nd == ref:
                continue
            pNewLo, pNewHi = lo[nd], hi[nd]
            for la in incident[nd]:
                z2 = par['pLineR'][la] ** 2 + par['pLineX'][la] ** 2
                z  = math.sqrt(z2)
                smax = par['pLineSmax'][la] / pSBase * vmax / vmin
                if smax <= 0.0:
                    continue
                pTapF   = par['pLineTapFactor'][la]
                pTap2   = pTapF ** 2
                pSpan   = 2.0 * smax * z
                pLossUb = z2 * (smax / (vmin * pTapF)) ** 2
                # The drop equation is w_j = w_i*f^2 - 2(rP+xQ) + z^2*l, with f = 1/tau. It is not symmetric once f differs from 1, so which end of
                # the branch this node sits on decides whether f^2 multiplies or divides.
                if la[0] == nd:                                     # nd sends: w_nd = (w_other + 2(rP+xQ) - z^2*l) / f^2
                    other  = la[1]
                    pNewLo = max(pNewLo, (lo[other] - pSpan - pLossUb) / pTap2)
                    pNewHi = min(pNewHi, (hi[other] + pSpan          ) / pTap2)
                else:                                               # nd receives: w_nd = w_other*f^2 - 2(rP+xQ) + z^2*l
                    other  = la[0]
                    pNewLo = max(pNewLo,  lo[other] * pTap2 - pSpan)
                    pNewHi = min(pNewHi,  hi[other] * pTap2 + pSpan + pLossUb)
            if pNewLo > pNewHi:          # the propagation crossed: the case is infeasible on these data
                raise ValueError(f'### Bound tightening: node {nd} has no feasible voltage range '
                                 f'([{math.sqrt(max(pNewLo,0)):.4f}, {math.sqrt(max(pNewHi,0)):.4f}] p.u.). '
                                 f'Check the line ratings and the voltage band.')
            pMoved = max(pMoved, abs(pNewLo - lo[nd]), abs(pNewHi - hi[nd]))
            lo[nd], hi[nd] = pNewLo, pNewHi
        if pMoved < TOLERANCE:
            break

    par['pMaxAngleDiff'] = pMaxAngleDiff
    par['pMinAngleDiff'] = pMinAngleDiff
    par['pVMinBus'] = {nd: math.sqrt(max(lo[nd], 0.0)) for nd in mTEPES.nd}
    par['pVMaxBus'] = {nd: math.sqrt(max(hi[nd], 0.0)) for nd in mTEPES.nd}

    pStats = {
        'branches':          len(branches),
        'angle_tightened':   pTightened,
        'angle_max_deg':     max((max(abs(pMaxAngleDiff[la]), abs(pMinAngleDiff[la])) for la in pMaxAngleDiff), default=0.0) * 180 / math.pi,
        'angle_median_deg':  (sorted(pMaxAngleDiff.values())[len(pMaxAngleDiff) // 2] * 180 / math.pi) if pMaxAngleDiff else 0.0,
        'voltage_sweeps':    pSweeps,
        'voltage_band_min':  min(par['pVMinBus'].values()),
        'voltage_band_max':  max(par['pVMaxBus'].values()),
        'seconds':           time.time() - StartTime,
    }

    print(f"Bound tightening                       ...  {pStats['angle_tightened']}/{pStats['branches']} branch angle bounds tightened, "
          f"median {pStats['angle_median_deg']:.2f} deg, max {pStats['angle_max_deg']:.2f} deg; "
          f"voltage {pStats['voltage_band_min']:.4f}-{pStats['voltage_band_max']:.4f} p.u. in {pStats['voltage_sweeps']} sweeps")
    return pStats
