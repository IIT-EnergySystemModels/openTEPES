import operator
import pandas as pd
from functools import reduce
from pyomo.opt import SolverFactory
from pyomo.environ import Suffix, value, Set, DataPortal, cos, sin
from openTEPES_NLP_PolarPowerFlow_AC import NLP_PolarPowerFlow_AC
from openTEPES_NLP_BFrPowerFlow_AC import NLP_BFrPowerFlow_AC

def NLPMat_run(CaseName, mTEPES):
    print('-----------------------------------------------------------')
    print('Validation of each load level in NLP load flow         ****')
    print('-----------------------------------------------------------')
    print('Data arrangement            ****')
    mTEPES.lci = Set(initialize=mTEPES.lc, ordered=False, doc='candidate lines installed ',
                     filter=lambda mTEPES, *lc: lc in mTEPES.lc and mTEPES.vNetworkInvest[lc]() > 0.01)
    mTEPES.shci = Set(initialize=mTEPES.shc, ordered=False, doc='candidate shunts installed',
                      filter=lambda mTEPES, *shc: shc in mTEPES.shc and mTEPES.vShuntInvest[shc]() > 0.01)

    mTEPES.lei = reduce(operator.or_, [mTEPES.le, mTEPES.lci])
    mTEPES.shei = reduce(operator.or_, [mTEPES.she, mTEPES.shci])
    data = DataPortal()

    print('Validation loop             ****')
    SolStatus = pd.DataFrame(index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n)), columns=['SolStatus'])
    vENS_Sol  = pd.DataFrame(index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)), columns=['vENS'])
    vVol_Sol  = pd.DataFrame(index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)), columns=['vVol'])
    vAng_Sol  = pd.DataFrame(index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)), columns=['vAng'])
    vLos_Sol  = pd.DataFrame(index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)), columns=['vLos'])
    for sc, p, n in mTEPES.sc * mTEPES.p * mTEPES.n:
        # %% Data selection for each scenario, period, and load level
        pPdf = pd.DataFrame(index=mTEPES.nd, columns=['pPdf'])
        pQdf = pd.DataFrame(index=mTEPES.nd, columns=['pQdf'])
        for nd in mTEPES.nd:
            pPdf['pPdf'][nd] = mTEPES.pDemand[sc, p, n, nd]
            pQdf['pQdf'][nd] = mTEPES.pReactiveDemand[sc, p, n, nd]
        data['pPdf'] = pPdf['pPdf'].to_dict()
        data['pQdf'] = pQdf['pQdf'].to_dict()

        # %% Importing the NLP model
        # import openTEPES_NLP_BFrPowerFlow_AC
        NLP_PolarPowerFlow_AC(CaseName, mTEPES)

        # %% Instance Creation
        instance = mTEPES_NLP.create_instance(data)

        # %% Fixing variables
        instance.vTheta[mTEPES.rf.first()].fix(0)
        for nd in mTEPES.nd:
            # instance.vENS[nd].fix(0)
            for g in mTEPES.g:
                if (nd, g) in mTEPES.n2g:
                    if nd == mTEPES.rf.first():
                        instance.vPger[g] = mTEPES.vTotalOutput[sc, p, n, g]()
                        instance.vVoltage[nd].fix((mTEPES.vVoltageMag_sqr[sc, p, n, nd]()) ** 0.5)
                        # instance.vVsqr[nd].fix(mTEPES.vVoltageMag_sqr[sc, p, n, nd]())
                    else:
                        instance.vPger[g].fix(mTEPES.vTotalOutput[sc, p, n, g]())
                        # instance.vPger[g] = mTEPES.vTotalOutput[sc, p, n, g]()
                        instance.vVoltage[nd].fix((mTEPES.vVoltageMag_sqr[sc, p, n, nd]()) ** 0.5)
                        # instance.vVsqr[nd].fix(mTEPES.vVoltageMag_sqr[sc, p, n, nd]())

        for es in mTEPES.es:
            instance.vESSCharge.fix(mTEPES.vESSCharge[sc, p, n, es]())

        # for nr in mTEPES.nr:
        #     instance.vQger[nr] = mTEPES.vReactiveTotalOutput[sc, p, n, nr]()

        # for sq in mTEPES.sq:
        #     instance.vSger[sq].fix(mTEPES.vSynchTotalOutput[sc, p, n, sq]())
        # %% Instance Printed
        # instance.pprint()
        # %% Solving the NLP model
        Solver = SolverFactory('ipopt')  # Solver selection
        instance.dual = Suffix(direction=Suffix.IMPORT)
        # %% Storing the results
        try:
            SolverResults = Solver.solve(instance, tee=True)  # tee=True muestra la salida del solver
            SolverResults.write()
        except:
            SolverResults['Solver'][0]['Termination condition'] = 'infeasible'

        # value(instance.pprint())
        print('Output Results              ****')
        SolStatus['SolStatus'][sc,p,n] = SolverResults['Solver'][0]['Termination condition']
        if SolverResults['Solver'][0]['Termination condition'] == 'infeasible':
            print(
                "------------------------------------------------------------------------------------------------------------")
            print(
                "-----------------------------------------------SUMMARY------------------------------------------------------")
            print('Scenario                              ... ', sc)
            print('Period                                ... ', p)
            print('Load level                            ... ', n)
            print(
                "------------------------------------------------------------------------------------------------------------")
            print('Termination condition                 ... ', SolverResults['Solver'][0]['Termination condition'])
            print(
                "------------------------------------------------------------------------------------------------------------")
            for nd in mTEPES.nd:
                vENS_Sol['vENS'][sc, p, n, nd] = 0
                vVol_Sol['vVol'][sc, p, n, nd] = 0
                vAng_Sol['vVol'][sc, p, n, nd] = 0
            for ni, nf, cc in mTEPES.la:
                vLos_Sol['vLos'][sc, p, n, ni, nf, cc] = 0
        else:
            # instance.display()
            ActiveNetworkLosses = pd.Series(
                data=[mTEPES.vCurrentFlow_sqr[sc, p, n, ni, nf, cc]() * mTEPES.pLineR[ni, nf, cc] for sc, p, n, ni, nf, cc
                      in
                      mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.la],
                index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.la)))
            ActiveNetworkLosses.index.names = ['Scenario', 'Period', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit']
            ActiveNetworkLosses = ActiveNetworkLosses.to_frame(name='pu').groupby(['Scenario', 'Period', 'LoadLevel']).sum()

            print(
                "------------------------------------------------------------------------------------------------------------")
            print(
                "-----------------------------------------------SUMMARY------------------------------------------------------")
            print('Scenario                              ... ', sc)
            print('Period                                ... ', p)
            print('Load level                            ... ', n)
            print(
                "------------------------------------------------------------------------------------------------------------")
            print('Termination condition                 ... ', SolverResults['Solver'][0]['Termination condition'])
            print(
                "------------------------------------------------------------------------------------------------------------")
            print('Active power losses in TEP model      ... ', ActiveNetworkLosses['pu'][sc, p, n])
            # print('Active power losses in NLP model      ... ', value(instance.eTotalTCost))
            # print('Active power losses in NLP model      ... ', sum(value(instance.vIsqr[ni, nf, cc])*instance.pLineR[ni, nf, cc] for ni, nf, cc in mTEPES.lei))
            print('Active Power Losses in NLP model      ... ', sum(instance.pLineG[ni,nf,cc]*(instance.pLineTAP[ni,nf,cc]**2 * value(instance.vVoltage[ni])**2 + value(instance.vVoltage[nf])**2 -
                                            2*instance.pLineTAP[ni,nf,cc]*value(instance.vVoltage[ni])*value(instance.vVoltage[nf])*cos(value(instance.vTheta[ni])-value(instance.vTheta[nf]))) for ni,nf,cc in mTEPES.lei))
            for nd in mTEPES.nd:
                vENS_Sol['vENS'][sc, p, n, nd] = instance.vENS[nd]()
                vVol_Sol['vVol'][sc, p, n, nd] = instance.vVoltage[nd]()
                # vVol_Sol['vVol'][sc, p, n, nd] = (instance.vVsqr[nd]())**0.5
                vAng_Sol['vAng'][sc, p, n, nd] = instance.vTheta[nd]()

            for ni,nf,cc in mTEPES.lei:
                vLos_Sol['vLos'][sc, p, n, ni, nf, cc] = (instance.pLineG[ni,nf,cc]*(instance.pLineTAP[ni,nf,cc]**2 * value(instance.vVoltage[ni])**2 + value(instance.vVoltage[nf])**2 - 2*instance.pLineTAP[ni,nf,cc]*value(instance.vVoltage[ni])*value(instance.vVoltage[nf])*cos(value(instance.vTheta[ni])-value(instance.vTheta[nf]))))*1e3

    vENS_Sol.fillna            (0, inplace=True)
    vVol_Sol.fillna            (0, inplace=True)
    vAng_Sol.fillna            (0, inplace=True)
    vLos_Sol.fillna            (0, inplace=True)
    SolStatus.index.names = ['Scenario','Period','LoadLevel']
    SolStatus.to_csv('MatCases/NLP_Result_Status_'+CaseName+'.csv', sep=',')

    vENS_Sol.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(vENS_Sol, index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).rename_axis([None,None,None], axis=0).to_csv('MatCases/NLP_Result_NetworkPNS_'+CaseName+'.csv', sep=',')

    vVol_Sol.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(vVol_Sol, index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).rename_axis([None,None,None], axis=0).to_csv('MatCases/NLP_Result_NetworkVoltage_'+CaseName+'.csv', sep=',')

    vAng_Sol.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(vAng_Sol, index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).rename_axis([None,None,None], axis=0).to_csv('MatCases/NLP_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    vLos_Sol.index.names = ['Scenario','Period','LoadLevel','From','To','Circuit']
    pd.pivot_table(vLos_Sol, index=['Scenario','Period','LoadLevel'], columns=['From', 'To', 'Circuit'], fill_value=0).rename_axis([None,None,None], axis=0).to_csv('MatCases/NLP_Result_NetworkAciveLosses_'+CaseName+'.csv', sep=',')