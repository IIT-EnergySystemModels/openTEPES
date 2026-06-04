"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Shared helpers for the network-map plots.

The hydrogen, heat, and electricity network maps each build a flow series and
each pick a single (period, scenario, load level) snapshot to draw. Those two
steps were identical across the three maps, so they live here. The rest of
each map (node and edge styling, demand and capacity scaling) is sector
specific and stays in its own module.
"""

import pandas as pd


def make_flow_series(var, sets, factor, membership):
    """Flow values for the lines in `membership`, scaled by `factor`.

    `p, sc, n` come from iterating `sets`, so this does not capture any
    enclosing scope and can live as a plain module function.
    """
    return pd.Series(data=[var[p,sc,n,ni,nf,cc]()*factor for p,sc,n,ni,nf,cc in sets if (p,ni,nf,cc) in membership], index=pd.Index(list(sets)))


def pick_snapshot(mTEPES):
    """Pick the (period, scenario, load level) to draw a network map for.

    Use the first period and load level. For the scenario, prefer the one
    whose probability is 1; if none is (e.g. a joint-with-expansion case
    that keeps non-uniform input probabilities), use the first scenario.
    """
    pEpsilon = 1e-6
    p = list(mTEPES.p)[0]
    n = list(mTEPES.n)[0]

    if len(mTEPES.sc) > 1:
        sc = None
        for scc in mTEPES.sc:
            if (p,scc) in mTEPES.ps:
                if abs(mTEPES.pScenProb[p,scc]() - 1.0) < pEpsilon:
                    sc = scc
        if sc is None:
            sc = next(iter(mTEPES.sc))
    else:
        sc = list(mTEPES.sc)[0]

    return p, sc, n
