# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020
import time
import pandas as pd
# import matplotlib.pyplot as plt

def OutputResultsMat_AC(CaseName, mTEPES):

    print('Output results              ****')

    StartTime = time.time()

    #%% outputting the investment decisions
    if len(mTEPES.gc):
        OutputResults = pd.DataFrame.from_dict(mTEPES.vGenerationInvest.extract_values(), orient='index', columns=[str(mTEPES.vGenerationInvest)])
        OutputResults.index.names = ['Generator']
        OutputResults.to_csv('MatCases/oT_Result_GenerationInvestment_'+CaseName+'.csv', index=True, header=True)
    if len(mTEPES.lc):
        OutputResults = pd.DataFrame.from_dict(mTEPES.vNetworkInvest.extract_values(), orient='index', columns=[str(mTEPES.vNetworkInvest)])
        OutputResults.index = pd.MultiIndex.from_tuples(OutputResults.index)
        OutputResults.index.names = ['InitialNode','FinalNode','Circuit']
        pd.pivot_table(OutputResults, values=str(mTEPES.vNetworkInvest), index=['InitialNode','FinalNode'], columns=['Circuit'], fill_value=0).to_csv('MatCases/oT_Result_NetworkInvestment_'+CaseName+'.csv', sep=',')
    if len(mTEPES.shc):
        OutputResults = pd.DataFrame.from_dict(mTEPES.vShuntInvest.extract_values(), orient='index', columns=[str(mTEPES.vShuntInvest)])
        OutputResults.index.names = ['Shunt']
        OutputResults.to_csv('MatCases/oT_Result_ShuntInvestment_'+CaseName+'.csv', sep=',')

    #%% outputting the generation operation
    OutputResults = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,g]()*1e3                        for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g)))
    OutputResults.to_frame(name='MW ').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW ').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_GenerationOutput_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vReactiveTotalOutput[sc,p,n,tq]()*1e3               for sc,p,n,tq in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.tq], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)))
    OutputResults.to_frame(name='Mvar ').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='Mvar ').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ReactiveGenerationOutput_'+CaseName+'.csv', sep=',')

    if len(mTEPES.sq):
        OutputResults = pd.Series(data=[mTEPES.vSynchTotalOutput[sc,p,n,sq]()*1e3                        for sc,p,n,sq in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sq], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sq)))
        OutputResults.to_frame(name='Mvar ').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='Mvar ').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_SynchGenerationOutput_'+CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputResults = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-mTEPES.vTotalOutput[sc,p,n,r]())*1e3 for sc,p,n,r  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r )))
        OutputResults.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_RESCurtailment_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]                  for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g )))
    OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_GenerationEnergy_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,nr]()*mTEPES.pCO2EmissionCost[nr]*1e3     for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)))
    OutputResults.to_frame(name='tCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='tCO2').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_GenerationEmission_'+CaseName+'.csv', sep=',')

    #%% outputting the ESS operation
    if len(mTEPES.es):
        OutputResults = pd.Series(data=[mTEPES.vESSCharge   [sc,p,n,es]()*1e3                           for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)))
        OutputResults.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ESSChargeOutput_'+CaseName+'.csv', sep=',')

        OutputResults = pd.Series(data=[mTEPES.vESSCharge   [sc,p,n,es]()*mTEPES.pDuration[n]           for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)))
        OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ESSChargeEnergy_'+CaseName+'.csv', sep=',')

        OutputResults = pd.Series(data=[OutputResults[sc,p,n].filter(mTEPES.t2g[gt]).sum() for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt)))
        OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ESSTechnologyEnergy_'+CaseName+'.csv', sep=',')

        OutputResults = pd.Series(data=[mTEPES.vESSInventory[sc,p,n,es]()              for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)))
        OutputResults *= 1e3
        OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ESSInventory_'+CaseName+'.csv', sep=',')

        OutputResults = pd.Series(data=[mTEPES.vESSSpillage [sc,p,n,es]()              for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)))
        OutputResults *= 1e3
        OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_ESSSpillage_'+CaseName+'.csv', sep=',')

        OutputResults = pd.Series({Key:OptimalSolution.value*1e3 for Key,OptimalSolution in mTEPES.vESSCharge.items()})
        OutputResults = pd.Series(data=[OutputResults[sc,p,n].filter(mTEPES.t2g[gt]).sum() for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt)))
        OutputResults.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_TechnologyCharge_'+CaseName+'.csv', sep=',')

    # OutputResults = pd.Series({Key:OptimalSolution.value*1e3 for Key,OptimalSolution in mTEPES.vTotalOutput.items()})
    # OutputResults = pd.Series(data=[OutputResults[sc,p,n].filter(mTEPES.t2g[gt]).sum() for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt)))
    # OutputResults.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_TechnologyOutput_'+CaseName+'.csv', sep=',')

    # OutputResults = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n] for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g)))
    # OutputResults = pd.Series(data=[OutputResults[sc,p,n].filter(mTEPES.t2g[gt]).sum() for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt)))
    # OutputResults.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv('MatCases/oT_Result_TechnologyEnergy_'+CaseName+'.csv', sep=',')

    #%% outputting the network operation
    OutputResults = pd.Series(data=[mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ActiveNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[-1*(mTEPES.vP[sc,p,n,ni,nf,cc]())  for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ActiveNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ReactiveNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[-1*(mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]()) for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ReactiveNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vQ_shc[sc,p,n,sh]() for sc,p,n,sh in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sh], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sh)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','Shunt']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['Shunt'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ReactiveShuntInj_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ActiveNetworkLosses_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]() - mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ReactiveNetworkLosses_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[max((mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc])**2
                                        + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc]-mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]())**2,
                                        (mTEPES.vP[sc,p,n,ni,nf,cc]())**2+(mTEPES.vQ[sc,p,n,ni,nf,cc]()+mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]())**2)**.5/mTEPES.pLineSmax[ni,nf,cc].value*1e2
                                    for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_NetworkUtilization_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[((mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc])**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]())**2)**.5 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ApparentNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[((mTEPES.vP[sc,p,n,ni,nf,cc]())**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]())**2)**.5 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputResults *= 1e3
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_ApparentNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputResults = pd.Series(data=[(mTEPES.vVoltageMag_sqr[sc,p,n,ni]())**0.5 for sc,p,n,ni in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)))
    OutputResults.index.names = ['Scenario','Period','LoadLevel','Node']
    OutputResults = pd.pivot_table(OutputResults.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0)
    OutputResults.index.names = [None] * len(OutputResults.index.names)
    OutputResults.to_csv('MatCases/oT_Result_NetworkVoltage_'+CaseName+'.csv', sep=',')

    OutputResults = pd.DataFrame.from_dict(mTEPES.vTheta.extract_values(), orient='index', columns=[str(mTEPES.vTheta)])
    OutputResults.index = pd.MultiIndex.from_tuples(OutputResults.index)
    OutputResults.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(OutputResults, values=str(mTEPES.vTheta), index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).to_csv('MatCases/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputResults = pd.DataFrame.from_dict(mTEPES.vENS.extract_values(), orient='index', columns=[str(mTEPES.vENS)])
    # OutputResults *= 1e2
    OutputResults.index = pd.MultiIndex.from_tuples(OutputResults.index)
    OutputResults.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(OutputResults, values=str(mTEPES.vENS), index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).to_csv('MatCases/oT_Result_NetworkPNS_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing output results                ... ', round(WritingResultsTime), 's')