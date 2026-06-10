"""
openTEPES.openTEPES_ModelFormulationHydro — hydropower reservoir operation: water balance, volume limits and outflows.
"""
from __future__ import annotations

import time
from collections import defaultdict
from pyomo.environ import Constraint, Set


def GenerationOperationModelFormulationReservoir(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Reservoir scheduling       constraints ****')

    StartTime = time.time()

    # area to generators (a2e)
    a2h = defaultdict(list)
    for ar,h in mTEPES.ar*mTEPES.h:
        if (ar,h) in mTEPES.a2g:
            a2h[h].append(ar)

    def eMaxVolume2Comm(OptModel,n,rc):
        if mTEPES.pIndBinRsrInvest[rc]() == 0 or (p,rc) not in mTEPES.prc or sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPowerElec[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) == 0.0 or mTEPES.pMaxVolume[p,sc,n,rc] == 0.0:
            return Constraint.Skip
        return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMaxVolume[p,sc,n,rc] <= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
    setattr(OptModel, f'eMaxVolume2Comm_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eMaxVolume2Comm, doc='Reservoir maximum volume limited by commitment [p.u.]'))

    if pIndLogConsole:
        print('eMaxVolume2Comm           ... ', len(getattr(OptModel, f'eMaxVolume2Comm_{p}_{sc}_{st}')), ' rows')

    def eMinVolume2Comm(OptModel,n,rc):
        if mTEPES.pIndBinRsrInvest[rc]() == 0 or (p,rc) not in mTEPES.prc or sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPowerElec[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) == 0.0 or mTEPES.pMinVolume[p,sc,n,rc] == 0.0:
            return Constraint.Skip
        return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMinVolume[p,sc,n,rc] >= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
    setattr(OptModel, f'eMinVolume2Comm_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eMinVolume2Comm, doc='Reservoir minimum volume limited by commitment [p.u.]'))

    if pIndLogConsole:
        print('eMinVolume2Comm           ... ', len(getattr(OptModel, f'eMinVolume2Comm_{p}_{sc}_{st}')), ' rows')

    def eTrbReserveUpIfUpstream(OptModel,n,h):
        # There must be enough water upstream of the turbine to produce all the possible offered power (scheduled + reserves)
        # Skip if generator is not available in the period or turbine cannot provide reserves or no reserves are demanded in the area where the turbine is located or turbine cannot generate at variable power
        if mTEPES.pIndOperReserveGen[h] or (p,h) not in mTEPES.ph or sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2h[h]) == 0.0 or mTEPES.pMaxPower2ndBlock [p,sc,n,h] == 0.0:
            return Constraint.Skip
        # Avoid division by 0 if turbine has no minimum power
        if mTEPES.pMinPowerElec[p,sc,n,h] == 0.0:
            return  OptModel.vOutput2ndBlock[p,sc,n,h] + OptModel.vReserveUp[p,sc,n,h]                                                                    <= sum(OptModel.vReservoirVolume[p,sc,n,rs] - mTEPES.pMinVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]()
        else:
            return (OptModel.vOutput2ndBlock[p,sc,n,h] + OptModel.vReserveUp[p,sc,n,h]) / mTEPES.pMinPowerElec[p,sc,n,h] + OptModel.vCommitment[p,sc,n,h] <= sum(OptModel.vReservoirVolume[p,sc,n,rs] - mTEPES.pMinVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinPowerElec[p,sc,n,h]
    setattr(OptModel, f'eTrbReserveUpIfUpstream_{p}_{sc}_{st}', Constraint(mTEPES.nhc, rule=eTrbReserveUpIfUpstream, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole:
        print('eTrbReserveUpIfUpstream   ... ', len(getattr(OptModel, f'eTrbReserveUpIfUpstream_{p}_{sc}_{st}')), ' rows')

    def eTrbReserveUpIfDownstream(OptModel,n,h):
        #There must be enough spare reservoir capacity downstream of a turbine to fit all the possible water (scheduled + reserves)
        # Skip if generator is not available in the period or turbine cannot provide reserves or no reserves are demanded in the area where the turbine is located or turbine cannot generate at variable power
        if mTEPES.pIndOperReserveGen[h] or (p,h) not in mTEPES.ph or sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2h[h]) == 0.0 or mTEPES.pMaxPower2ndBlock [p,sc,n,h] == 0.0:
            return Constraint.Skip
        # Avoid division by 0 if turbine has no minimum power
        if mTEPES.pMinPowerElec[p,sc,n,h] == 0.0:
            return  OptModel.vOutput2ndBlock[p,sc,n,h] + OptModel.vReserveUp[p,sc,n,h]                                                                    <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.h2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]()
        else:
            return (OptModel.vOutput2ndBlock[p,sc,n,h] + OptModel.vReserveUp[p,sc,n,h]) / mTEPES.pMinPowerElec[p,sc,n,h] + OptModel.vCommitment[p,sc,n,h] <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.h2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinPowerElec[p,sc,n,h]
    setattr(OptModel, f'eTrbReserveUpIfDownstream_{p}_{sc}_{st}', Constraint(mTEPES.nhc, rule=eTrbReserveUpIfDownstream, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole:
        print('eTrbReserveUpIfDownstream ... ', len(getattr(OptModel, f'eTrbReserveUpIfDownstream_{p}_{sc}_{st}')), ' rows')

    def ePmpReserveDwIfUpstream(OptModel,n,h):
        # There must be enough reservoir capacity upstream to store all the possible water (scheduled + reserves)
        # Skip if pump is not available in the period or pump cannot provide reserves or pump is not connected to any reservoir or no reserves are demanded in the area where the turbine is located or pump cannot consume at variable power
        if mTEPES.pIndOperReserveCon[h] or (p, h) not in mTEPES.ph or sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0 or sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2h[h]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,h] == 0.0:
            return Constraint.Skip
        # Avoid dividing by 0 if pump has no minimum charge
        if mTEPES.pMinCharge[p,sc,n,h] == 0.0:
            return  (OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]                                                                    ) * mTEPES.pEfficiency[h] <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]()
        else:
            return ((OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]) / mTEPES.pMinCharge[p,sc,n,h] + OptModel.vCommitmentCons[p,sc,n,h]) * mTEPES.pEfficiency[h] <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinCharge[p,sc,n,h]
    setattr(OptModel, f'ePmpReserveDwIfUpstream_{p}_{sc}_{st}', Constraint(mTEPES.npc, rule=ePmpReserveDwIfUpstream, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole:
        print('ePmpReserveDwIfUpstream   ... ', len(getattr(OptModel, f'ePmpReserveDwIfUpstream_{p}_{sc}_{st}')), ' rows')

    def ePmpReserveDwIfDownstream(OptModel, n, h):
        # There must be enough water downstream for the pump to draw from in case it needs to operate at the maximum capacity offered (scheduled + reserves)
        # Skip if pump is not available in the period or pump cannot provide reserves or pump is not connected to any reservoir orno reserves are demanded in the area where the turbine is located or pump cannot consume at variable power
        if mTEPES.pIndOperReserveCon[h] or (p, h) not in mTEPES.ph or sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0 or sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2h[h]) == 0.0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,h] == 0.0:
            return Constraint.Skip
        # Avoid dividing by 0 if pump has no minimum charge
        if mTEPES.pMinCharge[p,sc,n,h] == 0.0:
            return  (OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]                                                                    ) * mTEPES.pEfficiency[h] <= sum(OptModel.vReservoirVolume[p,sc,n,rs] - mTEPES.pMinVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]()
        else:
            return ((OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]) / mTEPES.pMinCharge[p,sc,n,h] + OptModel.vCommitmentCons[p,sc,n,h]) * mTEPES.pEfficiency[h] <= sum(OptModel.vReservoirVolume[p,sc,n,rs] - mTEPES.pMinVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinCharge[p,sc,n,h]
    setattr(OptModel, f'ePmpReserveDwIfDownstream_{p}_{sc}_{st}', Constraint(mTEPES.npc, rule=ePmpReserveDwIfDownstream, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole:
        print('ePmpReserveDwIfDownstream ... ', len(getattr(OptModel, f'ePmpReserveDwIfDownstream_{p}_{sc}_{st}')), ' rows')

    def eHydroInventory(OptModel,n,rs):
        if (p,rs) not in mTEPES.prs or (p,sc,st,n) not in mTEPES.s2n or sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r or (rs,h) in mTEPES.r2p or (h,rs) in mTEPES.p2r) == 0:
            return Constraint.Skip
        if   mTEPES.n.ord(n) == mTEPES.pReservoirTimeStep[rs]:
            if rs not in mTEPES.rn:
                return (mTEPES.pIniVolume[p,sc,n,rs]()                                                    + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pHydroInflows[p,sc,n2,rs]()*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            else:
                return (OptModel.vIniVolume[p,sc,n,rs]                                                    + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
        elif mTEPES.n.ord(n) >  mTEPES.pReservoirTimeStep[rs]:
            if rs not in mTEPES.rn:
                return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pReservoirTimeStep[rs]),rs] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pHydroInflows[p,sc,n2,rs]()*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            else:
                return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pReservoirTimeStep[rs]),rs] + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
        else:
            return Constraint.Skip
    setattr(OptModel, f'eHydroInventory_{p}_{sc}_{st}', Constraint(mTEPES.nrsc, rule=eHydroInventory, doc='Reservoir water inventory [hm3]'))

    if pIndLogConsole:
        print('eHydroInventory           ... ', len(getattr(OptModel, f'eHydroInventory_{p}_{sc}_{st}')), ' rows')

    def eIniFinVolume(OptModel,n,rs):
        if (p,rs) not in mTEPES.prs or (p,sc,st,n) not in mTEPES.s2n or mTEPES.n.ord(n) != mTEPES.pReservoirTimeStep[rs]:
            return Constraint.Skip
        return OptModel.vIniVolume[p,sc,n,rs] == OptModel.vHydroInventory[p,sc,mTEPES.n.last(),rs]
    setattr(OptModel, f'eIniFinVolume_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eIniFinVolume, doc='Initial equal to final volume for reservoir candidates [p.u.]'))

    if pIndLogConsole:
        print('eIniFinVolume             ... ', len(getattr(OptModel, f'eIniFinVolume_{p}_{sc}_{st}')), ' rows')

    def eHydroOutflows(OptModel,n,rs):
        if (p,sc,rs) not in mTEPES.ro:
            return Constraint.Skip
        return sum((OptModel.vHydroOutflows[p,sc,n2,rs] - mTEPES.pHydroOutflows[p,sc,n2,rs]())*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pWaterOutTimeStep[rs]:mTEPES.n.ord(n)]) == 0.0
    setattr(OptModel, f'eHydroOutflows_{p}_{sc}_{st}', Constraint(mTEPES.nrso, rule=eHydroOutflows, doc='hydro outflows of a reservoir [m3/s]'))

    if pIndLogConsole:
        print('eHydroOutflows            ... ', len(getattr(OptModel, f'eHydroOutflows_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating reservoir operation         ... ', round(GeneratingTime), 's')


# @profile
