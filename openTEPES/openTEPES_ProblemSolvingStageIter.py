"""
openTEPES.openTEPES_ProblemSolvingStageIter — stage-by-stage formulate-and-solve driver.

``StageIterativeSolving`` runs the model's per-stage loop: for every ``(period, scenario, stage)`` it activates
only that stage's load levels, builds the operation constraints for the stage, and calls ``ProblemSolving`` once
the stage's part of the model is in place. Two solve paths are preserved exactly as they were inside
``openTEPES_run``:

  * **no expansion / no system limits** — each scenario is solved on its own as a deterministic operation model
    (``pScenProb`` is set to 1.0 for that single scenario, the solve runs, then its constraints are deactivated);
  * **with expansion decisions or a system emission / RES-energy limit** — one joint stochastic solve is run at
    the last ``(period, scenario)`` over all stages, using the input scenario probabilities.

After the loop it rebuilds the full stage / load-level sets, reactivates every constraint, and restores the
scenario probabilities so the output writers report the intended (per-scenario sum, or expected-value) cost.

This is a pure move out of ``openTEPES_run`` — the loop body is unchanged, so results are identical. It sets up
the seam that later orchestration drivers (Mode C re-solve, sector / Benders decomposition) build on.
"""
from __future__ import annotations

import math
import os
import time

import pyomo.environ as pyo
from   pyomo.environ import Set

# Support running this file directly (e.g. VS Code "Run Python File"), where __package__ is empty and the
# relative imports below have no parent package; fall back to absolute package imports in that case.
try:
    from .openTEPES_ModelFormulation import GenerationOperationModelFormulationObjFunct, GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from .openTEPES_ProblemSolving   import ProblemSolving
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_ModelFormulation import GenerationOperationModelFormulationObjFunct, GenerationOperationElecModelFormulationInvestment, GenerationOperationHeatModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationReservoir, NetworkH2OperationModelFormulation, NetworkHeatOperationModelFormulation, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation, NetworkCycles, CycleConstraints
    from openTEPES.openTEPES_ProblemSolving   import ProblemSolving


def StageIterativeSolving(mTEPES, DirName, CaseName, SolverName, pIndLogConsole, _path, pIndCycleFlow):
    """Run the per-stage formulate-and-solve loop in place on ``mTEPES``.

    ``mTEPES`` must already carry the objective, the investment constraints, ``First_st`` / ``Last_st`` and an
    initialised ``pDuals`` dict (all set up by ``openTEPES_run`` before this call). ``_path`` is the case path
    used for optional LP-file dumps; ``pIndCycleFlow`` toggles the cycle-flow network formulation.
    """
    # initialize the set of load levels up to the current stage
    mTEPES.na = Set(initialize=[])

    # iterative model formulation for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:

        # control for not repeating the stages in case of several ones
        mTEPES.NoRepetition = 0

        # activate only load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt if mTEPES.pStageWeight[stt] and sum(1 for (p,sc,st,nn) in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                     (p,sc,st,nn) in mTEPES.s2n ])
        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                     (p,sc,st,nn) in mTEPES.s2n ])

        # load levels multiple of cycles for each ESS/generator
        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
        if mTEPES.pIndHydroTopology:
            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
            if sum(1 for h,rs in mTEPES.p2r):
                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
            else:
                mTEPES.np2c = []
            if sum(1 for rs,h in mTEPES.r2p):
                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
            else:
                mTEPES.npc = []
            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

        if mTEPES.st:

            # load levels up to the current stage for emission and RES energy constraints
            # if (p != mTEPES.p.first() or sc != mTEPES.sc.first()) and st == mTEPES.First_st:
            #     mTEPES.del_component(mTEPES.na)
            if st == mTEPES.First_st:
                mTEPES.del_component(mTEPES.na)
                mTEPES.na = Set(initialize=mTEPES.n)
            else:
                temp_na = mTEPES.na | mTEPES.n  # Create a temporary set
                mTEPES.del_component(mTEPES.na)  # Delete the existing set to avoid overwriting
                mTEPES.na = Set(initialize=temp_na)  # Assign the new set

            print(f'Period {p}, Scenario {sc}, Stage {st}')

            # operation model objective function and constraints by stage
            GenerationOperationModelFormulationObjFunct          (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationElecModelFormulationInvestment    (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHeat:
                GenerationOperationHeatModelFormulationInvestment(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationDemand            (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationStorage           (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydroTopology:
                GenerationOperationModelFormulationReservoir     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHydrogen:
                NetworkH2OperationModelFormulation               (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            if mTEPES.pIndHeat:
                NetworkHeatOperationModelFormulation             (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationCommitment        (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            GenerationOperationModelFormulationRampMinTime       (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkSwitchingModelFormulation                     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            NetworkOperationModelFormulation                     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
            # introduce cycle flow formulations
            if pIndCycleFlow:
                if st == mTEPES.First_st:
                    NetworkCycles                                (        mTEPES, pIndLogConsole           )
                CycleConstraints                                 (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

            # No generator investments and no generator retirements, and no line investments
            if (    (sum(1 for pp,eb       in mTEPES.peb if pp <= p) == 0 or mTEPES.pIndBinGenInvest()     == 2)
                and (sum(1 for pp,gd       in mTEPES.pgd if pp <= p) == 0 or mTEPES.pIndBinGenRetire()     == 2)
                and (sum(1 for pp,rc       in mTEPES.prc if pp <= p) == 0 or mTEPES.pIndBinRsrInvest()     == 2)
                and (sum(1 for pp,ni,nf,cc in mTEPES.plc if pp <= p) == 0 or mTEPES.pIndBinNetElecInvest() == 2)
                and (sum(1 for pp,ni,nf,cc in mTEPES.ppc if pp <= p) == 0 or mTEPES.pIndBinNetH2Invest()   == 2)
                and (sum(1 for pp,ni,nf,cc in mTEPES.phc if pp <= p) == 0 or mTEPES.pIndBinNetHeatInvest() == 2)):

                # No minimum RES requirements and no emission limit
                if (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) == 0 and (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)):

                    if (p,sc) == mTEPES.ps.last() and st == mTEPES.Last_st and mTEPES.NoRepetition == 0:
                        mTEPES.NoRepetition = 1

                    # Writing LP file
                    if pIndLogConsole:
                        StartTime         = time.time()
                        mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                        WritingLPFileTime = time.time() - StartTime
                        StartTime         = time.time()
                        print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                    # there are no expansion decisions, or they are ignored (it is an operation model), or there are no system emission nor minimum RES constraints
                    mTEPES.pScenProb[p,sc] = 1.0
                    ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                    mTEPES.pScenProb[p,sc] = 0.0

                    # deactivate the constraints of the previous period and scenario
                    for c in mTEPES.component_objects(pyo.Constraint, active=True):
                        if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                            c.deactivate()

                # Minimum RES requirements or emission limit
                elif (max([mTEPES.pRESEnergy[p,ar] for ar in mTEPES.ar]) > 0 or (min([mTEPES.pEmission [p,ar] for ar in mTEPES.ar]) < math.inf and sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) > 0)):

                    if st == mTEPES.Last_st and mTEPES.NoRepetition == 0:

                        if (p,sc) == mTEPES.ps.last():
                            mTEPES.NoRepetition = 1

                        mTEPES.del_component(mTEPES.st)
                        mTEPES.del_component(mTEPES.n )
                        mTEPES.del_component(mTEPES.n2)
                        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
                        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
                        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

                        # load levels multiple of cycles for each ESS/generator
                        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
                        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
                        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
                        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
                        if mTEPES.pIndHydroTopology:
                            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                            if sum(1 for h,rs in mTEPES.p2r):
                                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                            else:
                                mTEPES.np2c = []
                            if sum(1 for rs,h in mTEPES.r2p):
                                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                            else:
                                mTEPES.npc  = []
                            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

                        # Writing an LP file
                        if pIndLogConsole:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        mTEPES.pScenProb[p,sc] = 1.0
                        # there are system emission or RES requirement constraints
                        ProblemSolving           (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                        # if pIndSectorDecomposition and len(mTEPES.psnel):
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        #     SectorDecomposition(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st   )
                        # else:
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, mTEPES.p.ord(p)*mTEPES.sc.ord(sc)*mTEPES.st.ord(st))
                        mTEPES.pScenProb[p,sc] = 0.0

                        # deactivate the constraints of the previous period and scenario
                        for c in mTEPES.component_objects(pyo.Constraint, active=True):
                            if c.name.find(str(p)) != -1 and c.name.find(str(sc)) != -1:
                                c.deactivate()

            # generator investments or generator retirements, or line investments
            elif (  (sum(1 for pp,eb       in mTEPES.peb if pp <= p) > 0 and mTEPES.pIndBinGenInvest()     < 2)
                 or (sum(1 for pp,gd       in mTEPES.pgd if pp <= p) > 0 and mTEPES.pIndBinGenRetire()     < 2)
                 or (sum(1 for pp,rc       in mTEPES.prc if pp <= p) > 0 and mTEPES.pIndBinRsrInvest()     < 2)
                 or (sum(1 for pp,ni,nf,cc in mTEPES.plc if pp <= p) > 0 and mTEPES.pIndBinNetElecInvest() < 2)
                 or (sum(1 for pp,ni,nf,cc in mTEPES.ppc if pp <= p) > 0 and mTEPES.pIndBinNetH2Invest()   < 2)
                 or (sum(1 for pp,ni,nf,cc in mTEPES.phc if pp <= p) > 0 and mTEPES.pIndBinNetHeatInvest() < 2)):

                    if (p,sc) == mTEPES.ps.last() and st == mTEPES.Last_st and mTEPES.NoRepetition == 0:
                        mTEPES.NoRepetition = 1

                        mTEPES.del_component(mTEPES.st)
                        mTEPES.del_component(mTEPES.n )
                        mTEPES.del_component(mTEPES.n2)
                        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
                        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
                        mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

                        # load levels multiple of cycles for each ESS/generator
                        mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
                        mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
                        mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
                        mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
                        if mTEPES.pIndHydroTopology:
                            mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                            if sum(1 for h,rs in mTEPES.p2r):
                                mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                            else:
                                mTEPES.np2c = []
                            if sum(1 for rs,h in mTEPES.r2p):
                                mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                            else:
                                mTEPES.npc  = []
                            mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
                            mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

                        # Writing an LP file
                        if pIndLogConsole:
                            StartTime         = time.time()
                            mTEPES.write(f'{_path}/openTEPES_{CaseName}_{p}_{sc}_{st}.lp', io_options={'symbolic_solver_labels': True})
                            WritingLPFileTime = time.time() - StartTime
                            StartTime         = time.time()
                            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

                        # there are investment decisions (it is an expansion and operation model), or there are system emission constraints
                        ProblemSolving           (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        # if pIndSectorDecomposition and len(mTEPES.psnel):
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)
                        #     SectorDecomposition(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st   )
                        # else:
                        #     ProblemSolving     (DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc, st, 1)

    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                                    p,sc,stt,nn  in mTEPES.s2n)])
    mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])
    mTEPES.n2 = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for p,sc,st in mTEPES.ps*mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

    # load levels multiple of cycles for each ESS/generator
    mTEPES.nesc         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [es] == 0]
    mTEPES.necc         = [(n,ec) for n,ec in mTEPES.n*mTEPES.ec if mTEPES.n.ord(n) %     mTEPES.pStorageTimeStep [ec] == 0]
    mTEPES.neso         = [(n,es) for n,es in mTEPES.n*mTEPES.es if mTEPES.n.ord(n) %     mTEPES.pOutflowsTimeStep[es] == 0]
    mTEPES.ngen         = [(n,g ) for n,g  in mTEPES.n*mTEPES.g  if mTEPES.n.ord(n) %     mTEPES.pEnergyTimeStep  [g ] == 0]
    if mTEPES.pIndHydroTopology:
        mTEPES.nhc      = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
        if sum(1 for h,rs in mTEPES.p2r):
            mTEPES.np2c = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
        else:
            mTEPES.np2c = []
        if sum(1 for rs,h in mTEPES.r2p):
            mTEPES.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
        else:
            mTEPES.npc  = []
        mTEPES.nrsc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrcc     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rn if mTEPES.n.ord(n) %     mTEPES.pReservoirTimeStep[rs] == 0]
        mTEPES.nrso     = [(n,rs) for n,rs in mTEPES.n*mTEPES.rs if mTEPES.n.ord(n) %     mTEPES.pWaterOutTimeStep [rs] == 0]

    # activate the constraints of all the periods and scenarios
    for c in mTEPES.component_objects(pyo.Constraint):
        c.activate()

    # Output convention follows the two intended modes:
    #   - Case 2 (no expansion decisions): the per-scenario solve loop above
    #     used pScenProb=1.0 for each scenario individually. Reset all
    #     probabilities to 1.0 so cost-summary writers aggregate the
    #     independent deterministic solves as a sum.
    #   - Case 1 (with expansion decisions): the joint solve at the last
    #     (p,sc) used the input probabilities to minimise probability-
    #     weighted expected cost. Preserve those probabilities so the
    #     output reports that same expected cost — otherwise the writers
    #     would over-count by ~N_scenarios.
    _hasExpansion = (
            (sum(1 for _ in mTEPES.peb) > 0 and mTEPES.pIndBinGenInvest()     < 2)
        or  (sum(1 for _ in mTEPES.pgd) > 0 and mTEPES.pIndBinGenRetire()     < 2)
        or  (sum(1 for _ in mTEPES.prc) > 0 and mTEPES.pIndBinRsrInvest()     < 2)
        or  (sum(1 for _ in mTEPES.plc) > 0 and mTEPES.pIndBinNetElecInvest() < 2)
        or  (sum(1 for _ in mTEPES.ppc) > 0 and mTEPES.pIndBinNetH2Invest()   < 2)
        or  (sum(1 for _ in mTEPES.phc) > 0 and mTEPES.pIndBinNetHeatInvest() < 2)
    )
    if not _hasExpansion:
        # assign probability 1 to all the periods and scenarios
        for p,sc in mTEPES.ps:
            mTEPES.pScenProb[p,sc] = 1.0
