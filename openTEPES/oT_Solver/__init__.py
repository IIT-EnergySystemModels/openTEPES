"""
openTEPES.oT_Solver — Layer 5 of the layered-architecture restructure.

Single-solve primitives (5.a) and orchestration drivers (5.b) for openTEPES models, per RFC §3:

  Single-solve primitives (5.a)
  -----------------------------
  * ``Persistent``        ``appsi_gurobi`` / ``gurobi_persistent`` lifecycle (``ncall`` state machine,
                          ``set_instance`` / ``update_config`` toggles).
  * ``Tuning``            per-solver option presets (Gurobi / CPLEX / HiGHS / GAMS) for the initial solve
                          and for the warm-restart fix-and-resolve LP pass.
  * ``DualExtraction``    fix integers + investments → re-solve as LP → ``collect_duals`` into
                          ``mTEPES.pDuals`` for downstream ``MarginalResults`` / ``EconomicResults``.

  Orchestration drivers (5.b)
  ---------------------------
  * ``ProblemSolving``    per-stage solve orchestrator that composes the three primitives above.
  * ``Benders.lshaped``   classical L-shaped decomposition for transmission expansion. Master =
                          ``vNetworkInvest`` only; subproblem = the full openTEPES model with each candidate
                          investment pinned via an explicit equality constraint (mutable ``Param``) and the
                          dual read through ``mTEPES.dual`` Suffix.

Future PRs (per RFC §5) add ``Stage_iter.py`` (extracts the ``(p, sc, st)`` loop from ``openTEPES_run``),
``Resolve.py`` (Mode-C hot-swap re-solve), ``Decomposition/Sector.py`` (electricity ↔ H2 sector decomp), and
``Decomposition/Benders.py`` (stochastic Benders + sector Benders).
"""
from __future__ import annotations

from .Benders import lshaped
from .ProblemSolving import ProblemSolving

__all__ = ["lshaped", "ProblemSolving"]
