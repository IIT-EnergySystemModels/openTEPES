"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 09, 2026

openTEPES.openTEPES_SettingUpVariables — creates the decision variables and their bounds, fixes the generators' commitment, relaxes or forbids investment conditions, zeroes out epsilon values, and screens for infeasibilities. Runs after DataConfiguration.
"""
from __future__ import annotations

import time
import math
import pandas        as pd
from   collections   import defaultdict
from   pyomo.environ import Set, Param, Var, Binary, NonNegativeReals, NonNegativeIntegers, Reals, UnitInterval, Block, Boolean


# @profile
def SettingUpVariables(OptModel, mTEPES):

    StartTime = time.time()

    # @profile
    def CreateVariables(mTEPES, OptModel) -> None:
        '''
        Create all mTEPES variables.

        This function takes an mTEPES instance with all parameters and sets created and adds variables to it.

        Parameters:
            mTEPES: The instance of mTEPES.

        Returns:
            None: Variables are added directly to the mTEPES object.
        '''
        #%% variables
        OptModel.vTotalSCost               = Var(              within=NonNegativeReals, doc='total system                         cost      [MEUR]')
        OptModel.vTotalICost               = Var(              within=NonNegativeReals, doc='total system investment              cost      [MEUR]')
        OptModel.vTotalFElecCost           = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed elec              cost      [MEUR]')
        OptModel.vTotalGCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable generation  operation cost      [MEUR]')
        OptModel.vTotalCCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total variable consumption operation cost      [MEUR]')
        OptModel.vTotalECost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system emission                cost      [MEUR]')
        OptModel.vTotalRElecCost           = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability elec        cost      [MEUR]')
        OptModel.vTotalNCost               = Var(mTEPES.psn,   within=NonNegativeReals, doc='total network loss penalty operation cost      [MEUR]')
        OptModel.vTotalEmissionArea        = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                         [MtCO2]')
        OptModel.vTotalECostArea           = Var(mTEPES.psnar, within=NonNegativeReals, doc='total   area emission                cost      [MEUR]')
        OptModel.vTotalRESEnergyArea       = Var(mTEPES.psnar, within=NonNegativeReals, doc='        RES energy                              [GWh]')

        OptModel.vTotalOutput              = Var(mTEPES.psng , within=NonNegativeReals, doc='total output of the unit                         [GW]')
        OptModel.vOutput2ndBlock           = Var(mTEPES.psnnr, within=NonNegativeReals, doc='second block of the unit                         [GW]')
        OptModel.vReserveUp                = Var(mTEPES.psnnr, within=NonNegativeReals, doc='up   operating reserve                           [GW]')
        OptModel.vReserveDown              = Var(mTEPES.psnnr, within=NonNegativeReals, doc='down operating reserve                           [GW]')
        OptModel.vEnergyInflows            = Var(mTEPES.psnec, within=NonNegativeReals, doc='unscheduled inflows  of candidate ESS units      [GW]')
        OptModel.vEnergyOutflows           = Var(mTEPES.psnes, within=NonNegativeReals, doc='scheduled   outflows of all       ESS units      [GW]')
        OptModel.vESSInventory             = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS inventory                                   [GWh]')
        OptModel.vESSSpillage              = Var(mTEPES.psnes, within=NonNegativeReals, doc='ESS spillage                                    [GWh]')
        OptModel.vIniInventory             = Var(mTEPES.psnec, within=NonNegativeReals, doc='initial inventory for ESS candidate             [GWh]')

        if mTEPES.pIndRampReserves:
            OptModel.vRampReserveUp        = Var(mTEPES.psnnr, within=NonNegativeReals, doc='ramp up   reserve of the unit                  [GW/h]')
            OptModel.vRampReserveDw        = Var(mTEPES.psnnr, within=NonNegativeReals, doc='ramp down reserve of the unit                  [GW/h]')

        if mTEPES.pIndReserveActivation:
            OptModel.vReserveUpEnergy      = Var(mTEPES.psnnr, within=NonNegativeReals, doc='up   reserve activation of the unit              [GW]')
            OptModel.vReserveDownEnergy    = Var(mTEPES.psnnr, within=NonNegativeReals, doc='down reserve activation of the unit              [GW]')

        OptModel.vESSTotalCharge           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS total charge power                           [GW]')
        OptModel.vCharge2ndBlock           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS       charge power                           [GW]')
        OptModel.vESSReserveUp             = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS up   operating reserve                       [GW]')
        OptModel.vESSReserveDown           = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS down operating reserve                       [GW]')
        OptModel.vENS                      = Var(mTEPES.psnnd, within=NonNegativeReals, doc='energy not served in node                        [GW]')

        if mTEPES.pIndReserveActivation:
            OptModel.vESSReserveUpEnergy   = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS up   reserve activation of the unit          [GW]')
            OptModel.vESSReserveDownEnergy = Var(mTEPES.psneh, within=NonNegativeReals, doc='ESS down reserve activation of the unit          [GW]')

        if mTEPES.pIndHydroTopology:
            OptModel.vTotalFHydroCost      = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed hydro             cost      [MEUR]')
            OptModel.vHydroInflows         = Var(mTEPES.psnrc, within=NonNegativeReals, doc='unscheduled inflows  of candidate hydro units  [m3/s]')
            OptModel.vHydroOutflows        = Var(mTEPES.psnrs, within=NonNegativeReals, doc='scheduled   outflows of all       hydro units  [m3/s]')
            OptModel.vReservoirVolume      = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir volume                                [hm3]')
            OptModel.vReservoirSpillage    = Var(mTEPES.psnrs, within=NonNegativeReals, doc='Reservoir spillage                              [hm3]')

        if mTEPES.pIndHydrogen:
            OptModel.vTotalFH2Cost         = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed H2                cost      [MEUR]')
            OptModel.vTotalRH2Cost         = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability H2          cost      [MEUR]')

        if mTEPES.pIndHeat:
            OptModel.vTotalFHeatCost       = Var(mTEPES.p,     within=NonNegativeReals, doc='total system fixed heat              cost      [MEUR]')
            OptModel.vTotalRHeatCost       = Var(mTEPES.psn,   within=NonNegativeReals, doc='total system reliability heat        cost      [MEUR]')
            OptModel.vTotalOutputHeat      = Var(mTEPES.psng , within=NonNegativeReals, doc='total heat output of the boiler unit             [GW]')
            [OptModel.vTotalOutputHeat[p,sc,n,ch].setub(mTEPES.pMaxPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
            [OptModel.vTotalOutputHeat[p,sc,n,ch].setlb(mTEPES.pMinPowerHeat[p,sc,n,ch]) for p,sc,n,ch in mTEPES.psnch]
            # only boilers are forced to produce at their minimum heat power. CHPs are not forced to produce at their minimum heat power, they are committed or not to produce electricity

        if mTEPES.pIndBinGenInvest() != 1:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=UnitInterval,     doc='generation       investment decision exists in a year [0,1]')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=UnitInterval,     doc='generation       investment decision done   in a year [0,1]')
        else:
            OptModel.vGenerationInvest     = Var(mTEPES.peb,   within=Binary,           doc='generation       investment decision exists in a year {0,1}')
            OptModel.vGenerationInvPer     = Var(mTEPES.peb,   within=Binary,           doc='generation       investment decision done   in a year {0,1}')

        if mTEPES.pIndBinGenRetire() != 1:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=UnitInterval,     doc='generation       retirement decision exists in a year [0,1]')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=UnitInterval,     doc='generation       retirement decision exists in a year [0,1]')
        else:
            OptModel.vGenerationRetire     = Var(mTEPES.pgd,   within=Binary,           doc='generation       retirement decision exists in a year {0,1}')
            OptModel.vGenerationRetPer     = Var(mTEPES.pgd,   within=Binary,           doc='generation       retirement decision exists in a year {0,1}')

        if mTEPES.pIndBinNetElecInvest() != 1:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=UnitInterval,     doc='electric network investment decision exists in a year [0,1]')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=UnitInterval,     doc='electric network investment decision exists in a year [0,1]')
        else:
            OptModel.vNetworkInvest        = Var(mTEPES.plc,   within=Binary,           doc='electric network investment decision exists in a year {0,1}')
            OptModel.vNetworkInvPer        = Var(mTEPES.plc,   within=Binary,           doc='electric network investment decision exists in a year {0,1}')

        if mTEPES.pIndHydroTopology:
            if mTEPES.pIndBinRsrInvest() != 1:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=UnitInterval,     doc='reservoir        investment decision exists in a year [0,1]')
            else:
                OptModel.vReservoirInvest  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')
                OptModel.vReservoirInvPer  = Var(mTEPES.prc,   within=Binary,           doc='reservoir        investment decision exists in a year {0,1}')

        if mTEPES.pIndHydrogen:
            if mTEPES.pIndBinNetH2Invest() != 1:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=UnitInterval,     doc='hydrogen network investment decision exists in a year [0,1]')
            else:
                OptModel.vH2PipeInvest     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')
                OptModel.vH2PipeInvPer     = Var(mTEPES.ppc,   within=Binary,           doc='hydrogen network investment decision exists in a year {0,1}')

        if mTEPES.pIndHeat:
            if mTEPES.pIndBinGenInvest() != 1:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=UnitInterval, doc='generation       investment decision exists in a year [0,1]')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=UnitInterval, doc='generation       investment decision done   in a year [0,1]')
            else:
                OptModel.vGenerationInvestHeat = Var(mTEPES.pbc,   within=Binary,       doc='generation       investment decision exists in a year {0,1}')
                OptModel.vGenerationInvPerHeat = Var(mTEPES.pbc,   within=Binary,       doc='generation       investment decision done   in a year {0,1}')
            if mTEPES.pIndBinNetHeatInvest() != 1:
                OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=UnitInterval, doc='heat network investment decision exists in a year [0,1]'    )
                OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=UnitInterval, doc='heat network investment decision exists in a year [0,1]'    )
            else:
                OptModel.vHeatPipeInvest       = Var(mTEPES.phc,   within=Binary,       doc='heat network investment decision exists in a year {0,1}'    )
                OptModel.vHeatPipeInvPer       = Var(mTEPES.phc,   within=Binary,       doc='heat network investment decision exists in a year {0,1}'    )

        if mTEPES.pIndBinGenOperat() == 0:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='commitment      of the unit                                    [0,1]')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='startup         of the unit                                    [0,1]')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='shutdown        of the unit                                    [0,1]')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='stable    state of the unit                                    [0,1]')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp up   state of the unit                                    [0,1]')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=UnitInterval,     initialize=0.0, doc='ramp down state of the unit                                    [0,1]')

            OptModel.vMaxCommitmentYearly     = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=UnitInterval, initialize=0.0, doc='maximum commitment             of the unit yearly [0,1]')
            OptModel.vMaxCommitmentConsYearly = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=UnitInterval, initialize=0.0, doc='maximum consumption commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly     = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=UnitInterval, initialize=0.0, doc='maximum commitment             of the unit hourly [0,1]')

            if mTEPES.pIndHydroTopology:
                OptModel.vCommitmentCons   = Var(mTEPES.psnh,  within=UnitInterval,     doc='consumption commitment of the unit                                             [0,1]')

        else:
            OptModel.vCommitment           = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='commitment      of the unit                              {0,1}')
            OptModel.vStartUp              = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='startup         of the unit                              {0,1}')
            OptModel.vShutDown             = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='shutdown        of the unit                              {0,1}')
            OptModel.vStableState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='stable    state of the unit                              {0,1}')
            OptModel.vRampUpState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp up   state of the unit                              {0,1}')
            OptModel.vRampDwState          = Var(mTEPES.psnnr, within=Binary,           initialize=0  , doc='ramp down state of the unit                              {0,1}')

            OptModel.vMaxCommitmentYearly     = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=Binary, initialize=0.0, doc='maximum commitment             of the unit yearly [0,1]')
            OptModel.vMaxCommitmentConsYearly = Var(mTEPES.psnr ,mTEPES.ExclusiveGroupsYearly, within=Binary, initialize=0.0, doc='maximum consumption commitment of the unit yearly [0,1]')
            OptModel.vMaxCommitmentHourly     = Var(mTEPES.psnnr,mTEPES.ExclusiveGroupsHourly, within=Binary, initialize=0.0, doc='maximum commitment             of the unit hourly [0,1]')
            if mTEPES.pIndHydroTopology:
                OptModel.vCommitmentCons   = Var(mTEPES.psnh,  within=Binary,           doc='consumption commitment of the unit                    {0,1}')

        if mTEPES.pIndBinLineCommit() == 0:
            OptModel.vLineCommit           = Var(mTEPES.psnla, within=UnitInterval,     doc='line switching      of the electric line              [0,1]')
        else:
            OptModel.vLineCommit           = Var(mTEPES.psnla, within=Binary,           doc='line switching      of the electric line              {0,1}')

        if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
            if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineCommit() == 0:
                OptModel.vLineOnState      = Var(mTEPES.psnla, within=UnitInterval,     doc='switching on  state of the electric line              [0,1]')
                OptModel.vLineOffState     = Var(mTEPES.psnla, within=UnitInterval,     doc='switching off state of the electric line              [0,1]')
            else:
                OptModel.vLineOnState      = Var(mTEPES.psnla, within=Binary,           doc='switching on  state of the electric line              {0,1}')
                OptModel.vLineOffState     = Var(mTEPES.psnla, within=Binary,           doc='switching off state of the electric line              {0,1}')

    CreateVariables(mTEPES, mTEPES)
    # assign lower and upper bounds to variables
    # @profile
    def setVariableBounds(mTEPES, OptModel) -> None:
        '''
        Set upper/lower bounds.

        This function takes an mTEPES instance and adds lower/upper bounds to variables which are limited by a parameter.

        Parameters:
            mTEPES: The instance of mTEPES

        Returns:
            None: Changes are performed directly on the model
        '''

        [OptModel.vTotalOutput   [p,sc,n,g ].setub(mTEPES.pMaxPowerElec     [p,sc,n,g ]  ) for p,sc,n,g  in mTEPES.psng ]
        [OptModel.vTotalOutput   [p,sc,n,re].setlb(mTEPES.pMinPowerElec     [p,sc,n,re]  ) for p,sc,n,re in mTEPES.psnre]
        [OptModel.vOutput2ndBlock[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
        [OptModel.vReserveUp     [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
        [OptModel.vReserveDown   [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock [p,sc,n,nr]  ) for p,sc,n,nr in mTEPES.psnnr]
        [OptModel.vEnergyInflows [p,sc,n,ec].setub(mTEPES.pEnergyInflows    [p,sc,n,ec]()) for p,sc,n,ec in mTEPES.psnec]
        [OptModel.vEnergyOutflows[p,sc,n,es].setub(mTEPES.pMaxCapacity      [p,sc,n,es]  ) for p,sc,n,es in mTEPES.psnes]
        [OptModel.vESSInventory  [p,sc,n,es].setlb(mTEPES.pMinStorage       [p,sc,n,es]  ) for p,sc,n,es in mTEPES.psnes]
        [OptModel.vESSInventory  [p,sc,n,es].setub(mTEPES.pMaxStorage       [p,sc,n,es]()) for p,sc,n,es in mTEPES.psnes]
        [OptModel.vIniInventory  [p,sc,n,ec].setlb(mTEPES.pMinStorage       [p,sc,n,ec]  ) for p,sc,n,ec in mTEPES.psnec]
        [OptModel.vIniInventory  [p,sc,n,ec].setub(mTEPES.pMaxStorage       [p,sc,n,ec]()) for p,sc,n,ec in mTEPES.psnec]

        if mTEPES.pIndRampReserves:
            [OptModel.vRampReserveUp[p,sc,n,nr].setub(min(mTEPES.pMaxPower2ndBlock[p,sc,n,nr], mTEPES.pRampUp[nr])) if mTEPES.pRampUp[nr] else OptModel.vRampReserveUp[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]
            [OptModel.vRampReserveDw[p,sc,n,nr].setub(min(mTEPES.pMaxPower2ndBlock[p,sc,n,nr], mTEPES.pRampDw[nr])) if mTEPES.pRampUp[nr] else OptModel.vRampReserveDw[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]

        if mTEPES.pIndReserveActivation:
            [OptModel.vReserveUpEnergy  [p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]
            [OptModel.vReserveDownEnergy[p,sc,n,nr].setub(mTEPES.pMaxPower2ndBlock[p,sc,n,nr]) for p,sc,n,nr in mTEPES.psnnr]

        [OptModel.vESSTotalCharge[p,sc,n,eh].setub(mTEPES.pMaxCharge        [p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vCharge2ndBlock[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveUp  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vESSReserveDown[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]  ) for p,sc,n,eh in mTEPES.psneh]
        [OptModel.vENS           [p,sc,n,nd].setub(mTEPES.pDemandElecPos    [p,sc,n,nd]  ) for p,sc,n,nd in mTEPES.psnnd]

        if mTEPES.pIndReserveActivation:
            [OptModel.vESSReserveUpEnergy  [p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]
            [OptModel.vESSReserveDownEnergy[p,sc,n,eh].setub(mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]) for p,sc,n,eh in mTEPES.psneh]

        if mTEPES.pIndHydroTopology:
            [OptModel.vHydroInflows   [p,sc,n,rc].setub(mTEPES.pHydroInflows[p,sc,n,rc]()) for p,sc,n,rc in mTEPES.psnrc]
            [OptModel.vHydroOutflows  [p,sc,n,rs].setub(mTEPES.pMaxOutflows [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setlb(mTEPES.pMinVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]
            [OptModel.vReservoirVolume[p,sc,n,rs].setub(mTEPES.pMaxVolume   [p,sc,n,rs]  ) for p,sc,n,rs in mTEPES.psnrs]

    setVariableBounds(mTEPES, mTEPES)

    nFixedVariables = 0

    # @profile
    def RelaxBinaryInvestmentConditions(mTEPES, OptModel) -> int:
        '''
        Relax binary investment variables.

        This function takes an mTEPES instance, relaxes binary investment conditions and calculates the number of variables fixed in the process.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The number of fixed variables.
        '''

        nFixedVariables = 0

        # relax binary condition in generation, boiler, and electric network investment decisions
        for p,eb in mTEPES.peb:
            if mTEPES.pIndBinGenInvest() == 2 or (mTEPES.pIndBinGenInvest() == 1 and mTEPES.pIndBinUnitInvest[eb] == 0):
                OptModel.vGenerationInvest    [p,eb      ].domain = UnitInterval
            if mTEPES.pIndBinGenInvest() == 2:
                OptModel.vGenerationInvest    [p,eb      ].fix(0)
                nFixedVariables += 1

        # relax binary condition in generation retirement decisions
        for p,gd in mTEPES.pgd:
            if mTEPES.pIndBinGenRetire() == 2 or (mTEPES.pIndBinGenRetire() == 1 and mTEPES.pIndBinUnitRetire[gd] == 0):
                OptModel.vGenerationRetire    [p,gd      ].domain = UnitInterval
            if mTEPES.pIndBinGenRetire() == 2:
                OptModel.vGenerationRetire    [p,gd      ].fix(0)
                nFixedVariables += 1

        for p,ni,nf,cc in mTEPES.plc:
            if mTEPES.pIndBinNetElecInvest() == 2 or (mTEPES.pIndBinNetElecInvest() == 1 and mTEPES.pIndBinLineInvest[ni,nf,cc] == 0):
                OptModel.vNetworkInvest       [p,ni,nf,cc].domain = UnitInterval
                OptModel.vNetworkInvPer       [p,ni,nf,cc].domain = UnitInterval
            if mTEPES.pIndBinNetElecInvest() == 2:
                OptModel.vNetworkInvest       [p,ni,nf,cc].fix(0)
                OptModel.vNetworkInvPer       [p,ni,nf,cc].fix(0)
                nFixedVariables += 1

        # relax binary condition in reservoir investment decisions
        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if mTEPES.pIndBinRsrInvest() == 2 or (mTEPES.pIndBinRsrInvest() == 1 and mTEPES.pIndBinRsrvInvest[rc] == 0):
                    OptModel.vReservoirInvest [p,rc      ].domain = UnitInterval
                if mTEPES.pIndBinRsrInvest() == 2:
                    OptModel.vReservoirInvest [p,rc      ].fix(0)
                    nFixedVariables += 1

        # relax binary condition in hydrogen network investment decisions
        if mTEPES.pIndHydrogen:
            for p,ni,nf,cc in mTEPES.ppc:
                if mTEPES.pIndBinNetH2Invest() == 2 or (mTEPES.pIndBinNetH2Invest() == 1 and mTEPES.pIndBinH2PipeInvest[ni,nf,cc] == 0):
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetH2Invest() == 2:
                    OptModel.vH2PipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedVariables += 1

        if mTEPES.pIndHeat:
            # relax binary condition in heat network investment decisions
            for p,ni,nf,cc in mTEPES.phc:
                if mTEPES.pIndBinNetHeatInvest() == 2 or (mTEPES.pIndBinNetHeatInvest() == 1 and mTEPES.pIndBinHeatPipeInvest[ni,nf,cc] == 0):
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].domain = UnitInterval
                if mTEPES.pIndBinNetHeatInvest() == 2:
                    OptModel.vHeatPipeInvest  [p,ni,nf,cc].fix(0)
                    nFixedVariables += 1

        for p,sc,n,nr in mTEPES.psnnr:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vCommitment [p,sc,n,nr].domain = UnitInterval
                OptModel.vStartUp    [p,sc,n,nr].domain = UnitInterval
                OptModel.vShutDown   [p,sc,n,nr].domain = UnitInterval
            # fix variables for units that don't have minimum stable time
            if mTEPES.pStableTime[nr] == 0.0 or mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0.0:
                OptModel.vStableState[p,sc,n,nr].fix(0)
                OptModel.vStableState[p,sc,n,nr].domain = UnitInterval
                OptModel.vRampDwState[p,sc,n,nr].fix(0)
                OptModel.vRampDwState[p,sc,n,nr].domain = UnitInterval
                OptModel.vRampUpState[p,sc,n,nr].fix(0)
                OptModel.vRampUpState[p,sc,n,nr].domain = UnitInterval
                nFixedVariables += 3

        for p,sc,nr,  group in mTEPES.ps*mTEPES.ExclusiveGeneratorsYearly*mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vMaxCommitmentYearly    [p,sc,nr,group].domain = UnitInterval
                OptModel.vMaxCommitmentConsYearly[p,sc,nr,group].domain = UnitInterval
        for p,sc,n,nr,group in mTEPES.psn*mTEPES.ExclusiveGeneratorsHourly*mTEPES.ExclusiveGroups:
            if mTEPES.pIndBinUnitCommit[nr] == 0:
                OptModel.vMaxCommitmentHourly[p,sc,n,nr,group].domain = UnitInterval
        if mTEPES.pIndHydroTopology:
            for p,sc,n,h in mTEPES.psnh:
                if mTEPES.pIndBinUnitCommit[h] == 0 or mTEPES.pMaxCharge[p,sc,n,h] == 0.0:
                    OptModel.vCommitmentCons[p,sc,n,h].domain = UnitInterval
                if mTEPES.pMaxCharge[p,sc,n,h] == 0.0:
                    OptModel.vCommitmentCons[p,sc,n,h].fix(0)
                    nFixedVariables += 1

        return nFixedVariables

    # call the relaxing variables function and add its output to nFixedVariables
    nFixedBinaries = RelaxBinaryInvestmentConditions(mTEPES, mTEPES)
    nFixedVariables += nFixedBinaries

    # @profile
    def CreateFlowVariables(mTEPES,OptModel) -> int:
        #TODO use a more descriptive name for nFixedVariables
        '''
                Create electricity, hydrogen and heat-flow-related variables.

                This function takes an mTEPES instance and adds the variables necessary to model power, hydrogen and heat flows in a network.

                Parameters:
                    mTEPES: The instance of mTEPES.
                    OptModel:

                Returns:
                    int: The number of line commitment variables fixed
                '''

        nFixedVariables = 0
        # existing lines are always committed if no switching decision is modeled
        for p,sc,n,ni,nf,cc in mTEPES.psnle:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
                OptModel.vLineCommit[p,sc,n,ni,nf,cc].fix(1)
                OptModel.vLineCommit[p,sc,n,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1

        # no on/off state for lines if no switching decision is modeled
        if sum(mTEPES.pIndBinLineSwitch[:,:,:]):
             for p,sc,n,ni,nf,cc in mTEPES.psnla:
                 if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 0:
                     OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0)
                     OptModel.vLineOnState [p,sc,n,ni,nf,cc].domain = UnitInterval
                     OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0)
                     OptModel.vLineOffState[p,sc,n,ni,nf,cc].domain = UnitInterval
                     nFixedVariables += 2

        OptModel.vLineLosses = Var(mTEPES.psnll, within=NonNegativeReals, doc='half line losses [GW]')
        OptModel.vFlowElec   = Var(mTEPES.psnla, within=Reals,            doc='electric flow    [GW]')
        OptModel.vTheta      = Var(mTEPES.psnnd, within=Reals,            doc='voltage angle   [rad]')

        if mTEPES.pIndVarTTC:
            # lines with TTC and TTCBck = 0 are disconnected and the flow is fixed to 0
            sPSNLA = [(p,sc,n,ni,nf,cc) for p,sc,n,ni,nf,cc in mTEPES.psnla if mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] == 0.0 and mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc] == 0.0]
            if len(sPSNLA):
                [OptModel.vFlowElec[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in sPSNLA]
                nFixedVariables += sum(                    1  for p,sc,n,ni,nf,cc in sPSNLA)

        if mTEPES.pIndPTDF:
            OptModel.vNetPosition = Var(mTEPES.psnnd, within=Reals, doc='net position in node [GW]')

        if mTEPES.pIndBinSingleNode() == 0:
            [OptModel.vLineLosses[p,sc,n,ni,nf,cc].setub(0.5*mTEPES.pLineLossFactor[ni,nf,cc]*mTEPES.pLineNTCMax[ni,nf,cc]) for p,sc,n,ni,nf,cc in mTEPES.psnll]
            [OptModel.vFlowElec  [p,sc,n,ni,nf,cc].setlb(-mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]                              ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
            [OptModel.vFlowElec  [p,sc,n,ni,nf,cc].setub( mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]                              ) for p,sc,n,ni,nf,cc in mTEPES.psnla]
        else:
            [OptModel.vLineLosses[p,sc,n,ni,nf,cc].fix(0.0                                                                ) for p,sc,n,ni,nf,cc in mTEPES.psnll]
            nFixedVariables += sum(                    1                                                                    for p,sc,n,ni,nf,cc in mTEPES.psnll)
        [OptModel.vTheta         [p,sc,n,nd      ].setlb(-mTEPES.pMaxTheta [p,sc,n,nd      ]()                            ) for p,sc,n,nd       in mTEPES.psnnd]
        [OptModel.vTheta         [p,sc,n,nd      ].setub( mTEPES.pMaxTheta [p,sc,n,nd      ]()                            ) for p,sc,n,nd       in mTEPES.psnnd]

        if mTEPES.pIndHydrogen:
            OptModel.vFlowH2 = Var(mTEPES.psnpa, within=Reals,            doc='pipeline flow               [tH2]')
            OptModel.vH2NS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='hydrogen not served in node [tH2]')
            OptModel.vH2Exc  = Var(mTEPES.psnnd, within=NonNegativeReals, doc='hydrogen excess     in node [tH2]')
            [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setlb(-mTEPES.pH2PipeNTCBck[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
            [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].setub( mTEPES.pH2PipeNTCFrw[ni,nf,cc])                           for p,sc,n,ni,nf,cc in mTEPES.psnpa]
            [OptModel.vH2NS    [p,sc,n,nd      ].setub(mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandH2Abs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]

        if mTEPES.pIndHeat:
            OptModel.vFlowHeat = Var(mTEPES.psnha, within=Reals,            doc='heat pipe flow          [GW]')
            OptModel.vHeatNS   = Var(mTEPES.psnnd, within=NonNegativeReals, doc='heat not served in node [GW]')
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setlb(-mTEPES.pHeatPipeNTCBck[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].setub( mTEPES.pHeatPipeNTCFrw[ni,nf,cc])                            for p,sc,n,ni,nf,cc in mTEPES.psnha]
            [OptModel.vHeatNS  [p,sc,n,nd      ].setub( mTEPES.pDuration[p,sc,n]()*mTEPES.pDemandHeatAbs[p,sc,n,nd]) for p,sc,n,nd       in mTEPES.psnnd]
        return nFixedVariables

    nFixedLineCommitments = CreateFlowVariables(mTEPES, mTEPES)
    nFixedVariables += nFixedLineCommitments

    # @profile
    def FixGeneratorsCommitment(mTEPES, OptModel) -> int:
        '''
            Fix commitment variables.

            This function takes an mTEPES instance and fixes commitment-related variables for must run units, ESS units and units with no minimum power.

            Parameters:
                mTEPES: The instance of mTEPES.
                OptModel:

            Returns:
                int: The number of commitment variables fixed.
            '''
        nFixedVariables = 0

        # must-run units must produce at least their minimum output
        sPSNG = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if mTEPES.pMustRun[g] and g not in mTEPES.gc]
        [OptModel.vTotalOutput[p,sc,n,g].setlb(mTEPES.pMinPowerElec[p,sc,n,g]) for p,sc,n,g in sPSNG]

        # if no max power, no total output
        sPSNG = [(p,sc,n,g) for p,sc,n,g in mTEPES.psng if mTEPES.pMaxPowerElec[p,sc,n,g] == 0.0]
        [OptModel.vTotalOutput[p,sc,n,g].fix(0.0) for p,sc,n,g in sPSNG]
        nFixedVariables += sum(                1  for p,sc,n,g in sPSNG)

        for p,sc,n,nr in mTEPES.psnnr:
            # must-run existing units or units with no minimum power or units with variable min power > 0, or ESS existing units are always committed and must produce at least their minimum output
            # not applicable to mutually exclusive units
            if   len(mTEPES.ExclusiveGroups) == 0:
                if ((mTEPES.pMustRun[nr] and nr not in mTEPES.gc) or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or mTEPES.pVariableMinPowerElec[p,sc,n,nr] > 0.0 or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                    nFixedVariables += 3
            # If there are mutually exclusive groups do not fix variables from ESS in mutually exclusive groups
            elif len(mTEPES.ExclusiveGroups) >  0 and nr not in mTEPES.ExclusiveGenerators:
                if (mTEPES.pMustRun[nr] or (mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,nr] == 0.0) or nr in mTEPES.es) and nr not in mTEPES.ec and nr not in mTEPES.h:
                    OptModel.vCommitment    [p,sc,n,nr].fix(1)
                    OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                    OptModel.vStartUp       [p,sc,n,nr].fix(0)
                    OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                    OptModel.vShutDown      [p,sc,n,nr].fix(0)
                    OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                    nFixedVariables += 3

            # if min and max power coincide there are neither second block, nor operating reserve, nor ramp reserve
            if  mTEPES.pMaxPower2ndBlock[p,sc,n,nr] ==  0.0:
                OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                # fix the must-run existing units and their output
                if mTEPES.pMustRun[nr] and nr not in mTEPES.gc:
                    OptModel.vTotalOutput[p,sc,n,nr].fix(mTEPES.pMinPowerElec[p,sc,n,nr])
                    nFixedVariables += 1
                if mTEPES.pIndRampReserves:
                    if mTEPES.pRampUp[nr] == 0.0:
                        OptModel.vRampReserveUp[p,sc,n,nr].fix(0.0)
                        OptModel.vRampReserveDw[p,sc,n,nr].fix(0.0)
                        nFixedVariables += 2

            if  mTEPES.pIndOperReserveGen[nr] or mTEPES.pMaxPower2ndBlock [p,sc,n,nr] == 0.0:
                OptModel.vReserveUp  [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown[p,sc,n,nr].fix(0.0)
                nFixedVariables += 2
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 2

        # total energy inflows per storage
        pTotalEnergyInflows = pd.Series([sum(mTEPES.pEnergyInflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,sc,n,es) in mTEPES.psnes) for es in mTEPES.es], index=mTEPES.es)
        pTotalMaxCharge     = pd.Series([sum(mTEPES.pMaxCharge[p,sc,n,es]       for p,sc,n in mTEPES.psn if (p,sc,n,es) in mTEPES.psnes) for es in mTEPES.es], index=mTEPES.es)
        mTEPES.pTotalEnergyInflows = Param(mTEPES.es, initialize=pTotalEnergyInflows.to_dict(), within=NonNegativeReals, doc='Total energy outflows')
        mTEPES.pTotalMaxCharge     = Param(mTEPES.es, initialize=pTotalMaxCharge.to_dict(),     within=NonNegativeReals, doc='Total maximum charge' )

        for p,sc,n,es in mTEPES.psnes:
            # ESS with no charge capacity
            if  mTEPES.pMaxCharge        [p,sc,n,es] ==  0.0:
                OptModel.vESSTotalCharge [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            # ESS with no charge capacity and no inflows can't produce
            if  mTEPES.pTotalMaxCharge[es] == 0.0 and mTEPES.pTotalEnergyInflows[es] == 0.0:
                OptModel.vTotalOutput    [p,sc,n,es].fix(0.0)
                OptModel.vOutput2ndBlock [p,sc,n,es].fix(0.0)
                OptModel.vReserveUp      [p,sc,n,es].fix(0.0)
                OptModel.vReserveDown    [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage    [p,sc,n,es].fix(0.0)
                OptModel.vESSInventory   [p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
                nFixedVariables += 6
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,es].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 2
            if  mTEPES.pMaxCharge2ndBlock[p,sc,n,es] ==  0.0:
                OptModel.vCharge2ndBlock [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
            if  mTEPES.pIndOperReserveCon[es] or mTEPES.pMaxCharge2ndBlock[p,sc,n,es] == 0.0:
                OptModel.vESSReserveUp   [p,sc,n,es].fix(0.0)
                OptModel.vESSReserveDown [p,sc,n,es].fix(0.0)
                nFixedVariables += 2
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy  [p,sc,n,es].fix(0.0)
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 2
            if  mTEPES.pMaxStorage       [p,sc,n,es]() == 0.0:
                OptModel.vESSInventory   [p,sc,n,es].fix( 0.0)
                nFixedVariables += 1

        if mTEPES.pIndHydroTopology:
            for p,sc,n,h in mTEPES.psnh:
                # ESS with no charge capacity or not storage capacity can't charge
                if  mTEPES.pMaxCharge        [p,sc,n,h ] ==  0.0:
                    OptModel.vESSTotalCharge [p,sc,n,h ].fix(0.0)
                    OptModel.vCommitmentCons [p,sc,n,h ].fix(0  )
                    OptModel.vCommitmentCons [p,sc,n,h ].domain = UnitInterval
                    nFixedVariables += 2
                if  mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] ==  0.0:
                    OptModel.vCharge2ndBlock [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 1
                if  mTEPES.pIndOperReserveCon[h ] or mTEPES.pMaxCharge2ndBlock[p,sc,n,h ] == 0.0:
                    OptModel.vESSReserveUp   [p,sc,n,h ].fix(0.0)
                    OptModel.vESSReserveDown [p,sc,n,h ].fix(0.0)
                    nFixedVariables += 2
                    if mTEPES.pIndReserveActivation:
                        OptModel.vESSReserveUpEnergy  [p,sc,n,h ].fix(0.0)
                        OptModel.vESSReserveDownEnergy[p,sc,n,h ].fix(0.0)
                        nFixedVariables += 2
        return nFixedVariables
    nFixedGeneratorCommits = FixGeneratorsCommitment(mTEPES, mTEPES)
    nFixedVariables       += nFixedGeneratorCommits
    # thermal, ESS, and RES units ordered by increasing variable operation cost, excluding reactive generating units
    if mTEPES.tq:
        mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.sq])
    else:
        if mTEPES.pIndHydroTopology:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__)])
        else:
            mTEPES.go = Set(initialize=[g for g in sorted(mTEPES.pRatedLinearVarCost, key=mTEPES.pRatedLinearVarCost.__getitem__) if g not in mTEPES.h])

    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)
    n2a = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
    e2a = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
    o2a = defaultdict(list)
    for ar,go in mTEPES.ar*mTEPES.go:
        if (ar,go) in mTEPES.a2g:
            o2a[ar].append(go)

    # nodes to area (d2a)
    d2a = defaultdict(list)
    for ar,nd in mTEPES.ar*mTEPES.nd:
        if (nd,ar) in mTEPES.ndar:
            d2a[ar].append(nd)

    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if st == stt and mTEPES.pStageWeight[stt] and sum(1 for  p,sc,st,nn  in mTEPES.s2n)])
        mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                                                      (p,sc,st,nn) in mTEPES.s2n ])

        if mTEPES.n:
            # determine the first load level of each stage
            n1 = (p,sc,mTEPES.n.first())
            # commit the units of each area and their output at the first load level of each stage
            for ar in mTEPES.ar:
                pSystemOutput = 0.0
                for nr in n2a[ar]:
                    if mTEPES.pMustRun[nr] == 1 and (p,nr) in mTEPES.pnr and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd]() for nd in d2a[ar]):
                        mTEPES.pInitialOutput[n1,nr] = mTEPES.pMaxPowerElec [n1,nr]
                        mTEPES.pInitialUC    [n1,nr] = 1
                        pSystemOutput               += mTEPES.pInitialOutput[n1,nr]()

                # determine the initially committed units and their output at the first load level of each period, scenario, and stage
                for go in o2a[ar]:
                    if mTEPES.pMustRun[go] == 0 and (p,go) in mTEPES.pg and pSystemOutput < sum(mTEPES.pDemandElec[n1,nd]() for nd in d2a[ar]):
                        if go in mTEPES.re:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMaxPowerElec [n1,go]
                        else:
                            mTEPES.pInitialOutput[n1,go] = mTEPES.pMinPowerElec [n1,go]
                        mTEPES.pInitialUC[n1,go]         = 1
                        pSystemOutput                   += mTEPES.pInitialOutput[n1,go]()

            # determine the initially committed lines
            for la in mTEPES.la:
                if (p,la) in mTEPES.pla:
                    if la in mTEPES.lc:
                        mTEPES.pInitialSwitch[n1,la] = 0
                    else:
                        mTEPES.pInitialSwitch[n1,la] = 1

            # fixing the ESS inventory at the last load level of the stage for every period and scenario if between storage limits
            for es in mTEPES.es:
                if es not in mTEPES.ec and (p,es) in mTEPES.pes:
                    OptModel.vESSInventory[p,sc,mTEPES.n.last(),es].fix(mTEPES.pIniInventory[p,sc,mTEPES.n.last(),es])

            if mTEPES.pIndHydroTopology:
                # fixing the reservoir volume at the last load level of the stage for every period and scenario if between storage limits
                for rs in mTEPES.rs:
                    if rs not in mTEPES.rn:
                        OptModel.vReservoirVolume[p,sc,mTEPES.n.last(),rs].fix(mTEPES.pIniVolume[p,sc,mTEPES.n.last(),rs]())

    # activate all the periods, scenarios, and load levels again
    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.st = Set(doc='stages',      initialize=[stt for stt in mTEPES.stt if mTEPES.pStageWeight[stt] and sum(1 for                    (p,sc,stt,nn) in mTEPES.s2n)])
    mTEPES.n  = Set(doc='load levels', initialize=[nn  for nn  in mTEPES.nn  if                              sum(1 for st in mTEPES.st if (p,sc,st, nn) in mTEPES.s2n)])

    # fixing the ESS inventory at the end of the following pStorageTimeStep (daily, weekly, monthly) if between storage limits, i.e.,
    # for daily ESS is fixed at the end of the week, for weekly ESS is fixed at the end of the month, for monthly ESS is fixed at the end of the year
    # for p,sc,n,es in mTEPES.psnes:
    #     if es not in mTEPES.ec:
    #         if mTEPES.pStorageType[es] == 'Hourly'  and mTEPES.n.ord(n) % int(  24/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Weekly'  and mTEPES.n.ord(n) % int( 672/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1
    #         if mTEPES.pStorageType[es] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
    #             OptModel.vESSInventory[p,sc,n,es].fix(mTEPES.pIniInventory[p,sc,n,es])
    #             nFixedVariables += 1

    # if mTEPES.pIndHydroTopology:
        # fixing the reservoir volume at the end of the following pReservoirTimeStep (daily, weekly, monthly) if between storage limits, i.e.,
        # for daily reservoir is fixed at the end of the week, for weekly reservoir is fixed at the end of the month, for monthly reservoir is fixed at the end of the year
        # for p,sc,n,rs in mTEPES.psnrs:
        #     if rs not in mTEPES.rn:
        #         if mTEPES.pReservoirType[rs] == 'Hourly'  and mTEPES.n.ord(n) % int(  24/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Daily'   and mTEPES.n.ord(n) % int( 168/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Weekly'  and mTEPES.n.ord(n) % int( 672/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1
        #         if mTEPES.pReservoirType[rs] == 'Monthly' and mTEPES.n.ord(n) % int(8736/mTEPES.pTimeStep()) == 0:
        #             OptModel.vReservoirVolume[p,sc,n,rs].fix(mTEPES.pIniVolume[p,sc,n,rs]())
        #             nFixedVariables += 1

    for p,sc,n,ec in mTEPES.psnec:
        if mTEPES.pEnergyInflows        [p,sc,n,ec]() == 0.0:
            OptModel.vEnergyInflows     [p,sc,n,ec].fix (0.0)
            nFixedVariables += 1

    # if no operating reserve is required, no variables are needed
    for p,sc,n,ar,nr in mTEPES.psn*mTEPES.ar*mTEPES.nr:
        if nr in n2a[ar] and (p,sc,n,nr) in mTEPES.psnnr:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 1
    for p,sc,n,ar,es in mTEPES.psn*mTEPES.ar*mTEPES.es:
        if es in e2a[ar] and (p,sc,n,es) in mTEPES.psnes:
            if mTEPES.pOperReserveUp    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1
            if mTEPES.pOperReserveDw    [p,sc,n,ar] ==  0.0:
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                nFixedVariables += 1
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    # if no operating reserve activation is required, no variables are needed
    for p,sc,n in mTEPES.psn:
        if mTEPES.pIndReserveActivation and sum(mTEPES.pOperReserveUpEnergy[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
            for nr in mTEPES.nr:
                if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    nFixedVariables += 1
            for eh in mTEPES.eh:
                if (mTEPES.pIndOperReserveGen[eh] == 0 or mTEPES.pIndOperReserveCon[eh] == 0) and (p,eh) in mTEPES.peh:
                    OptModel.vESSReserveUpEnergy  [p,sc,n,eh].fix(0.0)
                    nFixedVariables += 1
        if mTEPES.pIndReserveActivation and sum(mTEPES.pOperReserveDwEnergy[p,sc,n,ar] for ar in mTEPES.ar) == 0.0:
            for nr in mTEPES.nr:
                if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr:
                   OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                   nFixedVariables += 1
            for eh in mTEPES.eh:
                if (mTEPES.pIndOperReserveGen[eh] == 0 or mTEPES.pIndOperReserveCon[eh] == 0) and (p,eh) in mTEPES.peh:
                    OptModel.vESSReserveDownEnergy[p,sc,n,eh].fix(0.0)
                    nFixedVariables += 1

    # if there are no energy outflows, no variable is needed
    for es in mTEPES.es:
        if sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
            for p,sc,n in mTEPES.psn:
                if (p,es) in mTEPES.pes:
                    OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                    nFixedVariables += 1

    if mTEPES.pIndHydroTopology:
        # if there are no hydro outflows, no variable is needed
        for rs in mTEPES.rs:
            if sum(mTEPES.pHydroOutflows[p,sc,n,rs]() for p,sc,n in mTEPES.psn if (p,rs) in mTEPES.prs) == 0.0:
                for p,sc,n in mTEPES.psn:
                    if (p,rs) in mTEPES.prs:
                        OptModel.vHydroOutflows[p,sc,n,rs].fix(0.0)
                        nFixedVariables += 1

    # fixing the voltage angle of the reference node for each scenario, period, and load level
    if mTEPES.pIndBinSingleNode() == 0:
        for p,sc,n in mTEPES.psn:
            OptModel.vTheta[p,sc,n,mTEPES.rf.first()].fix(0.0)
            nFixedVariables += 1

    # fixing the ENS in nodes with no demand
    for p,sc,n,nd in mTEPES.psnnd:
        if mTEPES.pDemandElec[p,sc,n,nd]() <=  0.0:
            OptModel.vENS    [p,sc,n,nd].fix(0.0)
            nFixedVariables += 1

    if mTEPES.pIndHydrogen:
        # fixing the H2 ENS in nodes with no hydrogen demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandH2[p,sc,n,nd] ==  0.0:
                OptModel.vH2NS [p,sc,n,nd].fix(0.0)
                nFixedVariables += 1

    if mTEPES.pIndHeat:
        # fixing the heat ENS in nodes with no heat demand
        for p,sc,n,nd in mTEPES.psnnd:
            if mTEPES.pDemandHeat[p,sc,n,nd] ==  0.0:
                OptModel.vHeatNS [p,sc,n,nd].fix(0.0)
                nFixedVariables += 1

    # @profile
    def AvoidForbiddenInstallationsAndRetirements(mTEPES, OptModel) -> int:
        '''
        Fix installations/retirements forbidden by period.

        This function takes an mTEPES instance and fixes all installation and retirement variables to 0 if they are not allowed in the corresponding period.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:

        Returns:
            int: The number of variables fixed.
        '''
        nFixedVariables = 0
        # do not install/retire power plants and lines if not allowed in this period
        for p,eb in mTEPES.peb:
            if mTEPES.pElecGenPeriodIni[eb] > p:
                OptModel.vGenerationInvest[p,eb].fix(0)
                OptModel.vGenerationInvest[p,eb].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecGenPeriodIni[eb] > p or mTEPES.pElecGenPeriodFin[eb] < p:
                OptModel.vGenerationInvPer[p,eb].fix(0)
                OptModel.vGenerationInvPer[p,eb].domain = UnitInterval
                nFixedVariables += 1

        for p,gd in mTEPES.pgd:
            if mTEPES.pElecGenPeriodIni[gd] > p:
                OptModel.vGenerationRetire[p,gd].fix(0)
                OptModel.vGenerationRetire[p,gd].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecGenPeriodIni[gd] > p or mTEPES.pElecGenPeriodFin[gd] < p:
                OptModel.vGenerationRetPer[p,gd].fix(0)
                OptModel.vGenerationRetPer[p,gd].domain = UnitInterval
                nFixedVariables += 1

        for p,ni,nf,cc in mTEPES.plc:
            if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p:
                OptModel.vNetworkInvest[p,ni,nf,cc].fix(0)
                OptModel.vNetworkInvest[p,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1
            if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p or mTEPES.pElecNetPeriodFin[ni,nf,cc] < p:
                OptModel.vNetworkInvPer[p,ni,nf,cc].fix(0)
                OptModel.vNetworkInvPer[p,ni,nf,cc].domain = UnitInterval
                nFixedVariables += 1

        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if mTEPES.pRsrPeriodIni[rc] > p:
                    OptModel.vReservoirInvest[p,rc].fix(0)
                    OptModel.vReservoirInvest[p,rc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pRsrPeriodIni[rc] > p or mTEPES.pRsrPeriodFin[rc] < p:
                    OptModel.vReservoirInvPer[p,rc].fix(0)
                    OptModel.vReservoirInvPer[p,rc].domain = UnitInterval
                    nFixedVariables += 1

        if mTEPES.pIndHydrogen:
            for p,ni,nf,cc in mTEPES.ppc:
                if mTEPES.pH2PipePeriodIni[ni,nf,cc] > p:
                    OptModel.vH2PipeInvest[p,ni,nf,cc].fix(0)
                    OptModel.vH2PipeInvest[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pH2PipePeriodIni[ni,nf,cc] > p or mTEPES.pH2PipePeriodFin[ni,nf,cc] < p:
                    OptModel.vH2PipeInvPer[p,ni,nf,cc].fix(0)
                    OptModel.vH2PipeInvPer[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1

        if mTEPES.pIndHeat:
            for p,ni,nf,cc in mTEPES.phc:
                if mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p:
                    OptModel.vHeatPipeInvest[p,ni,nf,cc].fix(0)
                    OptModel.vHeatPipeInvest[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1
                if mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p:
                    OptModel.vHeatPipeInvPer[p,ni,nf,cc].fix(0)
                    OptModel.vHeatPipeInvPer[p,ni,nf,cc].domain = UnitInterval
                    nFixedVariables += 1

        # remove power plants and lines not installed in this period
        for p,g in mTEPES.pg:
            if g not in mTEPES.eb and mTEPES.pElecGenPeriodIni[g ] > p or mTEPES.pElecGenPeriodFin[g ] < p:
                for sc,n in mTEPES.sc*mTEPES.n:
                    OptModel.vTotalOutput[p,sc,n,g].fix(0.0)
                    nFixedVariables += 1

        for p,sc,nr in mTEPES.psnr:
            if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p or mTEPES.pElecGenPeriodFin[nr] < p:
                for group in mTEPES.ExclusiveGroupsYearly:
                    OptModel.vMaxCommitmentYearly[p,sc,nr,group].fix(0)
                    OptModel.vMaxCommitmentYearly[p,sc,nr,group].domain = UnitInterval
                    nFixedVariables += 1
        for p,sc,n,nr in mTEPES.psnnr:
            if nr not in mTEPES.eb and mTEPES.pElecGenPeriodIni[nr] > p or mTEPES.pElecGenPeriodFin[nr] < p:
                OptModel.vOutput2ndBlock[p,sc,n,nr].fix(0.0)
                OptModel.vReserveUp     [p,sc,n,nr].fix(0.0)
                OptModel.vReserveDown   [p,sc,n,nr].fix(0.0)
                if mTEPES.pIndReserveActivation:
                    OptModel.vReserveUpEnergy  [p,sc,n,nr].fix(0.0)
                    OptModel.vReserveDownEnergy[p,sc,n,nr].fix(0.0)
                    nFixedVariables += 2
                OptModel.vCommitment    [p,sc,n,nr].fix(0  )
                OptModel.vCommitment    [p,sc,n,nr].domain = UnitInterval
                OptModel.vStartUp       [p,sc,n,nr].fix(0  )
                OptModel.vStartUp       [p,sc,n,nr].domain = UnitInterval
                OptModel.vShutDown      [p,sc,n,nr].fix(0  )
                OptModel.vShutDown      [p,sc,n,nr].domain = UnitInterval
                nFixedVariables += 6

        for p,sc,n,es in mTEPES.psnes:
            if es not in mTEPES.ec and mTEPES.pElecGenPeriodIni[es] > p or mTEPES.pElecGenPeriodFin[es] < p:
                OptModel.vEnergyOutflows[p,sc,n,es].fix(0.0)
                OptModel.vESSInventory  [p,sc,n,es].fix(0.0)
                OptModel.vESSSpillage   [p,sc,n,es].fix(0.0)
                OptModel.vESSTotalCharge[p,sc,n,es].fix(0.0)
                OptModel.vCharge2ndBlock[p,sc,n,es].fix(0.0)
                OptModel.vESSReserveUp  [p,sc,n,es].fix(0.0)
                OptModel.vESSReserveDown[p,sc,n,es].fix(0.0)
                if mTEPES.pIndReserveActivation:
                    OptModel.vESSReserveUpEnergy  [p,sc,n,es].fix(0.0)
                    OptModel.vESSReserveDownEnergy[p,sc,n,es].fix(0.0)
                    nFixedVariables += 2
                mTEPES.pIniInventory    [p,sc,n,es] =   0.0
                mTEPES.pEnergyInflows   [p,sc,n,es] =   0.0
                nFixedVariables += 7

        if mTEPES.pIndHydroTopology:
            for p,sc,n,rs in mTEPES.psnrs:
                if rs not in mTEPES.rn and mTEPES.pRsrPeriodIni[rs] > p or mTEPES.pRsrPeriodFin[rs] < p:
                    OptModel.vHydroOutflows         [p,sc,n,rs].fix(0.0)
                    OptModel.vReservoirVolume       [p,sc,n,rs].fix(0.0)
                    OptModel.vReservoirSpillage     [p,sc,n,rs].fix(0.0)
                    mTEPES.pIniVolume               [p,sc,n,rs] =   0.0
                    mTEPES.pHydroInflows            [p,sc,n,rs] =   0.0
                    nFixedVariables += 3
                    for h in mTEPES.h:
                        if (rs,h) in mTEPES.r2h:
                            OptModel.vESSTotalCharge[p,sc,n,h ].fix(0.0)
                            OptModel.vCharge2ndBlock[p,sc,n,h ].fix(0.0)
                            OptModel.vESSReserveUp  [p,sc,n,h ].fix(0.0)
                            OptModel.vESSReserveDown[p,sc,n,h ].fix(0.0)
                            nFixedVariables += 4
                            if mTEPES.pIndReserveActivation:
                                OptModel.vESSReserveUpEnergy  [p,sc,n,h ].fix(0.0)
                                OptModel.vESSReserveDownEnergy[p,sc,n,h ].fix(0.0)
                                nFixedVariables += 2
        return nFixedVariables

    nFixedInstallationsAndRetirements = AvoidForbiddenInstallationsAndRetirements(mTEPES, mTEPES)
    nFixedVariables += nFixedInstallationsAndRetirements

    for p,sc,n,ni,nf,cc in mTEPES.psnle:
        if mTEPES.pElecNetPeriodIni[ni,nf,cc] > p or mTEPES.pElecNetPeriodFin[ni,nf,cc] < p:
            OptModel.vLineCommit  [p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineCommit  [p,sc,n,ni,nf,cc].domain = UnitInterval
            OptModel.vLineOnState [p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineOnState [p,sc,n,ni,nf,cc].domain = UnitInterval
            OptModel.vLineOffState[p,sc,n,ni,nf,cc].fix(0)
            OptModel.vLineOffState[p,sc,n,ni,nf,cc].domain = UnitInterval
            nFixedVariables += 3

    [OptModel.vLineLosses  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p)]
    nFixedVariables     += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnll if (ni,nf,cc) not in mTEPES.lc and (mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p))

    [OptModel.vFlowElec    [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnle if                                  mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p]
    nFixedVariables     += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnle if                                  mTEPES.pElecNetPeriodIni [ni,nf,cc] > p or mTEPES.pElecNetPeriodFin [ni,nf,cc] < p)

    if mTEPES.pIndHydrogen:
        [OptModel.vFlowH2  [p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnpe if                                  mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p or mTEPES.pH2PipePeriodFin  [ni,nf,cc] < p]
        nFixedVariables += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnpe if                                  mTEPES.pH2PipePeriodIni  [ni,nf,cc] > p or mTEPES.pH2PipePeriodFin  [ni,nf,cc] < p)

    if mTEPES.pIndHeat:
        [OptModel.vFlowHeat[p,sc,n,ni,nf,cc].fix(0.0) for p,sc,n,ni,nf,cc in mTEPES.psnhe if                                  mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p]
        nFixedVariables += sum(                  1    for p,sc,n,ni,nf,cc in mTEPES.psnhe if                                  mTEPES.pHeatPipePeriodIni[ni,nf,cc] > p or mTEPES.pHeatPipePeriodFin[ni,nf,cc] < p)

    # tolerance to consider 0 an investment decision
    pEpsilon = 1e-4
    def SetToZero(mTEPES, OptModel, pEpsilon) -> None:
        '''
        Set small numbers to 0.

        This function takes an mTEPES instance and sets values under a certain threshold to be 0.

        Parameters:
            mTEPES: The instance of mTEPES.
            OptModel:
            pEpsilon: The threshold for considering a number 0.

        Returns:
            None: Changes are performed directly onto the model object.
        '''
        for p,eb in mTEPES.peb:
            if  mTEPES.pGenLoInvest[  eb]() <       pEpsilon:
                mTEPES.pGenLoInvest[  eb]   = 0
            if  mTEPES.pGenUpInvest[  eb]() <       pEpsilon:
                mTEPES.pGenUpInvest[  eb]   = 0
            if  mTEPES.pGenLoInvest[  eb]() > 1.0 - pEpsilon:
                mTEPES.pGenLoInvest[  eb]   = 1
            if  mTEPES.pGenUpInvest[  eb]() > 1.0 - pEpsilon:
                mTEPES.pGenUpInvest[  eb]   = 1
            if  mTEPES.pGenLoInvest[  eb]() >   mTEPES.pGenUpInvest[eb]():
                mTEPES.pGenLoInvest[  eb]   =   mTEPES.pGenUpInvest[eb]()
        [OptModel.vGenerationInvest[p,eb].setlb(mTEPES.pGenLoInvest[eb]()) for p,eb in mTEPES.peb]
        [OptModel.vGenerationInvest[p,eb].setub(mTEPES.pGenUpInvest[eb]()) for p,eb in mTEPES.peb]
        for p,gd in mTEPES.pgd:
            if  mTEPES.pGenLoRetire[  gd]() <       pEpsilon:
                mTEPES.pGenLoRetire[  gd]   = 0
            if  mTEPES.pGenUpRetire[  gd]() <       pEpsilon:
                mTEPES.pGenUpRetire[  gd]   = 0
            if  mTEPES.pGenLoRetire[  gd]() > 1.0 - pEpsilon:
                mTEPES.pGenLoRetire[  gd]   = 1
            if  mTEPES.pGenUpRetire[  gd]() > 1.0 - pEpsilon:
                mTEPES.pGenUpRetire[  gd]   = 1
            if  mTEPES.pGenLoRetire[  gd]() >   mTEPES.pGenUpRetire[gd]():
                mTEPES.pGenLoRetire[  gd]   =   mTEPES.pGenUpRetire[gd]()
        [OptModel.vGenerationRetire[p,gd].setlb(mTEPES.pGenLoRetire[gd]()) for p,gd in mTEPES.pgd]
        [OptModel.vGenerationRetire[p,gd].setub(mTEPES.pGenUpRetire[gd]()) for p,gd in mTEPES.pgd]
        for p,ni,nf,cc in mTEPES.plc:
            if  mTEPES.pNetLoInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pNetLoInvest[  ni,nf,cc]   = 0
            if  mTEPES.pNetUpInvest[  ni,nf,cc]() <       pEpsilon:
                mTEPES.pNetUpInvest[  ni,nf,cc]   = 0
            if  mTEPES.pNetLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pNetLoInvest[  ni,nf,cc]   = 1
            if  mTEPES.pNetUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                mTEPES.pNetUpInvest[  ni,nf,cc]   = 1
            if  mTEPES.pNetLoInvest[  ni,nf,cc]() >   mTEPES.pNetUpInvest[ni,nf,cc]():
                mTEPES.pNetLoInvest[  ni,nf,cc]   =   mTEPES.pNetUpInvest[ni,nf,cc]()
        [OptModel.vNetworkInvest   [p,ni,nf,cc].setlb(mTEPES.pNetLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.plc]
        [OptModel.vNetworkInvest   [p,ni,nf,cc].setub(mTEPES.pNetUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.plc]

        if mTEPES.pIndHydroTopology:
            for p,rc in mTEPES.prc:
                if  mTEPES.pRsrLoInvest[  rc]() <       pEpsilon:
                    mTEPES.pRsrLoInvest[  rc]   = 0
                if  mTEPES.pRsrUpInvest[  rc]() <       pEpsilon:
                    mTEPES.pRsrUpInvest[  rc]   = 0
                if  mTEPES.pRsrLoInvest[  rc]() > 1.0 - pEpsilon:
                    mTEPES.pRsrLoInvest[  rc]   = 1
                if  mTEPES.pRsrUpInvest[  rc]() > 1.0 - pEpsilon:
                    mTEPES.pRsrUpInvest[  rc]   = 1
                if  mTEPES.pRsrLoInvest[  rc]() >   mTEPES.pRsrUpInvest[rc]():
                    mTEPES.pRsrLoInvest[  rc]   =   mTEPES.pRsrUpInvest[rc]()
            [OptModel.vReservoirInvest [p,rc].setlb(mTEPES.pRsrLoInvest[rc]()) for p,rc in mTEPES.prc]
            [OptModel.vReservoirInvest [p,rc].setub(mTEPES.pRsrUpInvest[rc]()) for p,rc in mTEPES.prc]

        if mTEPES.pIndHydrogen:
            for p,ni,nf,cc in mTEPES.ppc:
                if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() <       pEpsilon:
                    mTEPES.pH2PipeLoInvest[  ni,nf,cc]   = 0
                if  mTEPES.pH2PipeUpInvest[  ni,nf,cc]() <       pEpsilon:
                    mTEPES.pH2PipeUpInvest[  ni,nf,cc]   = 0
                if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                    mTEPES.pH2PipeLoInvest[  ni,nf,cc]   = 1
                if  mTEPES.pH2PipeUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                    mTEPES.pH2PipeUpInvest[  ni,nf,cc]   = 1
                if  mTEPES.pH2PipeLoInvest[  ni,nf,cc]() >   mTEPES.pH2PipeUpInvest[ni,nf,cc]():
                    mTEPES.pH2PipeLoInvest[  ni,nf,cc]   =   mTEPES.pH2PipeUpInvest[ni,nf,cc]()
            [OptModel.vH2PipeInvest       [p,ni,nf,cc].setlb(mTEPES.pH2PipeLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.ppc]
            [OptModel.vH2PipeInvest       [p,ni,nf,cc].setub(mTEPES.pH2PipeUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.ppc]

        if mTEPES.pIndHeat:
            for p,ni,nf,cc in mTEPES.phc:
                if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() <       pEpsilon:
                    mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   = 0
                if  mTEPES.pHeatPipeUpInvest[  ni,nf,cc]() <       pEpsilon:
                    mTEPES.pHeatPipeUpInvest[  ni,nf,cc]   = 0
                if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                    mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   = 1
                if  mTEPES.pHeatPipeUpInvest[  ni,nf,cc]() > 1.0 - pEpsilon:
                    mTEPES.pHeatPipeUpInvest[  ni,nf,cc]   = 1
                if  mTEPES.pHeatPipeLoInvest[  ni,nf,cc]() >   mTEPES.pHeatPipeUpInvest[ni,nf,cc]():
                    mTEPES.pHeatPipeLoInvest[  ni,nf,cc]   =   mTEPES.pHeatPipeUpInvest[ni,nf,cc]()
            [OptModel.vHeatPipeInvest       [p,ni,nf,cc].setlb(mTEPES.pHeatPipeLoInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.phc]
            [OptModel.vHeatPipeInvest       [p,ni,nf,cc].setub(mTEPES.pHeatPipeUpInvest[ni,nf,cc]()) for p,ni,nf,cc in mTEPES.phc]

    SetToZero(mTEPES, OptModel, pEpsilon)

    # @profile
    def DetectInfeasibilities(mTEPES) -> None:
        '''
        Detect model infeasibilities.

        This function takes an mTEPES instance and checks for different infeasibilities.

        Parameters:
            mTEPES: The instance of mTEPES.

        Returns:
            None: Raises a ValueError when an infeasibility is found.
        '''

        if len(mTEPES.p ) == 0:
            raise ValueError('### No active periods in the case study'  )
        if len(mTEPES.sc) == 0:
            raise ValueError('### No active scenarios in the case study')
        if len(mTEPES.st) == 0:
            raise ValueError('### No active stages in the case study'   )

        # detecting infeasibility: sum of scenario probabilities must be 1 in each period
        # tolerance to consider 0 the difference between parameters
        pEpsilon = 1e-6
        for p in mTEPES.p:
            if abs(sum(mTEPES.pScenProb[p,sc]() for sc in mTEPES.sc if (p,sc) in mTEPES.ps)-1.0) > pEpsilon:
                raise ValueError(f'### Sum of scenario probabilities different from 1 in period {p}.')

        for es in mTEPES.es:
            # detecting infeasibility: total min ESS output greater than total inflows, total max ESS charge lower than total outflows, or no storage capacity for charging
            if sum(mTEPES.pMinPowerElec[p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -            sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) > 0.0:
                raise ValueError('### Total minimum output greater than total inflows for ESS unit ', es, ' by ', sum(mTEPES.pMinPowerElec  [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -    sum(mTEPES.pEnergyInflows [p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')
            if sum(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -            sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) < 0.0:
                raise ValueError('### Total maximum charge lower than total outflows for ESS unit ',  es, ' by ', sum(mTEPES.pMaxCharge     [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) -    sum(mTEPES.pEnergyOutflows[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')
            if max(mTEPES.pMaxCharge   [p,sc,n,es] for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) and          max(mTEPES.pMaxPowerElec  [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) and      max(mTEPES.pMaxStorage[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes) == 0.0:
                raise ValueError('### This ESS unit has no storage capacity for charging ',  es, ' ',             sum(mTEPES.pMaxCharge     [p,sc,n,es]   for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' MW ', sum(mTEPES.pMaxStorage[p,sc,n,es]() for p,sc,n in mTEPES.psn if (p,es) in mTEPES.pes), ' GWh')

        # detect inventory infeasibility
        for p,sc,n,es in mTEPES.ps*mTEPES.nesc:
            if (p,es) in mTEPES.pes:
                if mTEPES.pMaxCapacity[p,sc,n,es]:
                    if   mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pIniInventory[p,sc,n,es]()                                        + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])
                    elif mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
                        if mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es]() + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) < mTEPES.pMinStorage[p,sc,n,es]:
                            raise ValueError('### Inventory equation violation ', p, sc, n, es, mTEPES.pMaxStorage[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es]() + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - mTEPES.pMinPowerElec[p,sc,n2,es] + mTEPES.pEfficiency[es]*mTEPES.pMaxCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]), mTEPES.pMinStorage[p,sc,n,es])

        # detect minimum energy infeasibility
        for p,sc,n,g in mTEPES.ps*mTEPES.ngen:
            if (p,sc,g) in mTEPES.gm and (p,g) in mTEPES.pg:
                if sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) < 0.0:
                    raise ValueError('### Minimum energy violation ', p, sc, n, g, sum((mTEPES.pMaxPowerElec[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]))

        # detecting infeasibility: no capacity in the transmission network
        if sum(mTEPES.pLineNTCMax[:,:,:]) == 0.0:
            raise ValueError('### There is no capacity in the network. All the lines have NTC zero probably due to security factor equal to zero')

        # detecting reserve margin infeasibility
        for p,ar in mTEPES.p*mTEPES.ar:
            if     sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] if (p,g) in mTEPES.pg) < mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]():
                raise     ValueError('### Electricity reserve margin infeasibility ', p,ar, sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in mTEPES.g if (p,g) in mTEPES.pg and g in g2a[ar]), mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]())

            if mTEPES.pIndHeat:
                if sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] if (p,g) in mTEPES.pg) < mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
                    raise ValueError('### Heat reserve margin infeasibility ',        p,ar, sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in mTEPES.g if (p,g) in mTEPES.pg and g in g2a[ar]), mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMargin[p,ar]())

        for p,sc,ar in mTEPES.ps*mTEPES.ar:
            if mTEPES.pRESEnergy[p,ar]() > sum(mTEPES.pDemandElec[p,sc,n,nd]()*mTEPES.pLoadLevelDuration[p,sc,n]() for n,nd in mTEPES.n*d2a[ar] if (p,sc,n,nd) in mTEPES.psnnd):
                raise ValueError('### Minimum renewable energy requirement exceeds the demand ', p, sc, ar, mTEPES.pRESEnergy[p,ar](), sum(mTEPES.pDemandElec[p,sc,n,nd]() for n,nd in mTEPES.n*d2a[ar] if (p,sc,n,nd) in mTEPES.psnnd))

    DetectInfeasibilities(mTEPES)

    mTEPES.nFixedVariables    = Param(initialize=round(nFixedVariables), within=NonNegativeIntegers, doc='Number of fixed variables')

    mTEPES.IndependentPeriods = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages  = Param(mTEPES.pp, domain=Boolean, initialize=False, mutable=True)
    mTEPES.IndependentStages2 = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel           = Param(           domain=Boolean, initialize=False, mutable=True)
    mTEPES.Parallel           = True
    if (    (len(mTEPES.gc) == 0 or mTEPES.pIndBinGenInvest()     == 2)   # No candidates
        and (len(mTEPES.gd) == 0 or mTEPES.pIndBinGenRetire()     == 2)   # No retirements
        and (len(mTEPES.lc) == 0 or mTEPES.pIndBinNetElecInvest() == 2)): # No line candidates
        # Periods and scenarios are independent of each other
        mTEPES.IndependentPeriods = True
        for p in mTEPES.p:
            if (    (min([mTEPES.pEmission[p,ar] for ar in mTEPES.ar]) == math.inf or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr) == 0)  # No emissions
                and (max([mTEPES.pRESEnergy[p,ar]() for ar in mTEPES.ar]) == 0)):                                                                # No minimum RES requirements
            # Stages are independent from each other
                mTEPES.IndependentStages[p] = True
    if all(mTEPES.IndependentStages[p]() for p in mTEPES.pp):
        mTEPES.IndependentStages2 = True

    mTEPES.Period = Block(mTEPES.p)
    for p in mTEPES.Period:
        Period = mTEPES.Period[p]
        #TODO: Filter in some way that scenarios may not belong to periods
        # period2scenario = [stt for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p]
        Period.Scenario = Block(mTEPES.sc)
        Period.n        = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if pp == p])
        for sc in Period.Scenario:
            Scenario       = Period.Scenario[sc]
            Scenario.Stage = Block(Set(initialize=[stt for pp,scc,stt, nn in mTEPES.s2n if scc == sc and pp == p]))
            Scenario.n     = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if scc == sc and pp == p])

        # iterative model formulation for each stage of a year
            for st in Scenario.Stage:
                Stage    = Scenario.Stage[st]
                Stage.n  = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])
                Stage.n2 = Set(doc='load levels', initialize=[nn for pp, scc, stt, nn in mTEPES.s2n if stt == st and scc == sc and pp == p])

                # load levels multiple of cycles for each ESS/generator
                Stage.nesc = [(n,es) for n,es in Stage.n*mTEPES.es if Stage.n.ord(n) % mTEPES.pStorageTimeStep[es]  == 0]
                Stage.necc = [(n,ec) for n,ec in Stage.n*mTEPES.ec if Stage.n.ord(n) % mTEPES.pStorageTimeStep[ec]  == 0]
                Stage.neso = [(n,es) for n,es in Stage.n*mTEPES.es if Stage.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0]
                Stage.ngen = [(n,g ) for n,g  in Stage.n*mTEPES.g  if Stage.n.ord(n) % mTEPES.pEnergyTimeStep[g]    == 0]

                if mTEPES.pIndHydroTopology:
                    Stage.nhc      = [(n,h ) for n,h  in Stage.n*mTEPES.h  if Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h) == 0]
                    if sum(1 for h,rs in mTEPES.p2r):
                        Stage.np2c = [(n,h ) for n,h  in Stage.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) and Stage.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0]
                    else:
                        Stage.np2c = []
                    if sum(1 for rs,h in mTEPES.r2p):
                        Stage.npc  = [(n,h ) for n,h  in mTEPES.n*mTEPES.h  if sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) and mTEPES.n.ord(n) % sum(mTEPES.pReservoirTimeStep[rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p) == 0]
                    else:
                        Stage.npc  = []
                    Stage.nrsc     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) % mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrcc     = [(n,rs) for n,rs in Stage.n*mTEPES.rn if mTEPES.n.ord(n) % mTEPES.pReservoirTimeStep[rs] == 0]
                    Stage.nrso     = [(n,rs) for n,rs in Stage.n*mTEPES.rs if mTEPES.n.ord(n) % mTEPES.pWaterOutTimeStep [rs] == 0]

    SettingUpVariablesTime = time.time() - StartTime
    print('Setting up variables                   ... ', round(SettingUpVariablesTime), 's')
