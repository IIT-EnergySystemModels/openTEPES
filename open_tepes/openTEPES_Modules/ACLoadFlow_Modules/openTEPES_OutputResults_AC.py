# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020

import time
import pandas as pd
import matplotlib.pyplot as plt


def OutputResults_AC(CaseName, mTEPES):
    print('Output results              ****')

    StartTime = time.time()

    # sub-functions
    def oT_make_dataframe(_var):
        return pd.DataFrame.from_dict(_var.extract_values(), orient='index', columns=[str(_var)])

    def oT_make_series(_var, _sets, _factor):
        return pd.Series(data=[_var[sc, p, n, i]()*_factor for sc, p, n, i in _sets],
                         index=pd.MultiIndex.from_tuples(list(_sets)))

    def oT_make_pivot_table(_file, _var, _idx, _col, _val, _mod):
        if _mod == 0:
            return pd.pivot_table(_file, values=str(_var), index=_idx, columns=[_col], fill_value=0)
        else:
            return pd.pivot_table(_file, values=_val, index=_idx, columns=[_col])

    def oT_write_csv(_file, _case, _name):
        return _file.to_csv(_case+_name+_case+'.csv', sep=',')

    # outputting the investment decisions
    if len(mTEPES.gc):
        OutputToFile = oT_make_dataframe(mTEPES.vGenerationInvest)
        OutputToFile.index.names = ['Generator']
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_GenerationInvestment_')

    if len(mTEPES.lc):
        OutputToFile = oT_make_dataframe(mTEPES.vNetworkInvest)
        OutputToFile.index = pd.MultiIndex.from_tuples(OutputToFile.index)
        OutputToFile.index.names = ['InitialNode', 'FinalNode', 'Circuit']
        OutputToFile = oT_make_pivot_table(OutputToFile, mTEPES.vNetworkInvest, ['InitialNode', 'FinalNode'],
                                           'Circuit', '', 0)
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_NetworkInvestment_')

    if len(mTEPES.shc):
        OutputToFile = oT_make_dataframe(mTEPES.vShuntInvest)
        OutputToFile.index.names = ['Shunt']
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_ShuntInvestment_')

    # outputting the generation operation
    OutputToFile = oT_make_series(mTEPES.vTotalOutput, mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g, 1e3)
    OutputToFile = OutputToFile.to_frame(name='MW').reset_index()
    OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0','level_1','level_2'], 'level_3', 'MW', 1)
    OutputToFile = OutputToFile.rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1)
    oT_write_csv(OutputToFile, CaseName, '/oT_Result_GenerationOutput_')

    OutputToFile = oT_make_series(mTEPES.vReactiveTotalOutput, mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.tq, 1e3)
    # OutputToFile = pd.Series(data=[mTEPES.vReactiveTotalOutput[sc,p,n,tq]()*1e3               for sc,p,n,tq in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.tq], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)))
    OutputToFile = OutputToFile.to_frame(name='Mvar').reset_index()
    OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'Mvar', 1)
    oT_write_csv(OutputToFile, CaseName, '/oT_Result_ReactiveGenerationOutput_')

    if len(mTEPES.gq):
        OutputToFile = oT_make_series(mTEPES.vSynchTotalOutput, mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.sq, 1e3)
        OutputToFile = OutputToFile.to_frame(name='Mvar').reset_index()
        OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0','level_1','level_2'], 'level_3', 'Mvar', 1)
        OutputToFile = OutputToFile.rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1)
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_SynchGenerationOutput_')

    if len(mTEPES.r):
        OutputToFile = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-mTEPES.vTotalOutput[sc,p,n,r]())*1e3 for sc,p,n,r  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r )))
        OutputToFile = OutputToFile.to_frame(name='MW').reset_index()
        OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'MW', 1)
        OutputToFile = OutputToFile.rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_RESCurtailment_')

    OutputToFile = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]                  for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g )))
    OutputToFile = OutputToFile.to_frame(name='GWh').reset_index()
    OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'GWh', 1)
    OutputToFile = OutputToFile.rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
    oT_write_csv(OutputToFile, CaseName, '/oT_Result_GenerationEnergy_')

    OutputToFile = pd.Series(data=[mTEPES.vTotalOutput[sc,p,n,nr]()*mTEPES.pDuration[n]*mTEPES.pCO2EmissionCost[nr]*1e-3/mTEPES.pCO2Cost     for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)))
    OutputToFile = OutputToFile.to_frame(name='tCO2').reset_index()
    OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'tCO2', 1)
    OutputToFile = OutputToFile.rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
    oT_write_csv(OutputToFile, CaseName, '/oT_Result_GenerationEmission_')

    # outputting the ESS operation
    if len(mTEPES.es):
        OutputToFile = oT_make_series(mTEPES.vESSTotalCharge, mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es, 1e3)
        OutputToFile = OutputToFile.to_frame(name='MW').reset_index()
        OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'MW', 1)
        OutputToFile = OutputToFile.rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_ESSChargeOutput_')

        OutputToFile = pd.Series(data=[sum(OutputToFile[es][sc, p, n] for es in mTEPES.es if (gt, es) in mTEPES.t2g) for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
        OutputToFile = OutputToFile.to_frame(name='MW').reset_index()
        OutputToFile = oT_make_pivot_table(OutputToFile, '', ['level_0', 'level_1', 'level_2'], 'level_3', 'MW', 1)
        OutputToFile = OutputToFile.rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1)
        oT_write_csv(OutputToFile, CaseName, '/oT_Result_ESSTechnologyOutput_')

        ESSTechnologyOutput     = -OutputToFile.loc[:, :, :, :]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput  = pd.Series([0.] * len(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt), index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
        for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt:
            NetESSTechnologyOutput[sc, p, n, gt] = MeanESSTechnologyOutput[gt] - ESSTechnologyOutput[sc, p, n, gt]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_FlexibilityESSTechnology_' + CaseName + '.csv', sep=',')

        OutputToFile = pd.Series(data=[-mTEPES.vESSTotalCharge[sc, p, n, es]() * mTEPES.pDuration[n] for sc, p, n, es in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es)))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_ESSChargeEnergy_' + CaseName + '.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc, p, n, es] for es in mTEPES.es if (gt, es) in mTEPES.t2g) * 1e3 for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_ESSTechnologyEnergy_' + CaseName + '.csv', sep=',')

        OutputToFile *= -1
        ESSTechnologyEnergy = OutputToFile.to_frame(name='GWh')

        ESSTechnologyEnergy['GWh'] = (ESSTechnologyEnergy['GWh'] / ESSTechnologyEnergy['GWh'].sum()) * 100
        ESSTechnologyEnergy.reset_index(level=3, inplace=True)
        ESSTechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=90,
                                                            figsize=(15, 10), autopct='%1.1f%%')
        plt.legend(title='Energy Consumption', loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        # plt.show()
        plt.savefig(CaseName + '/oT_Plot_ESSTechnologyEnergy_' + CaseName + '.png', bbox_inches=None, dpi=600)

        OutputToFile = pd.Series(data=[mTEPES.vESSInventory[sc, p, n, es]() for sc, p, n, es in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es],index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es)))
        OutputToFile = OutputToFile.fillna(0)
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_ESSInventory_' + CaseName + '.csv', sep=',')

        OutputToFile = pd.Series(data=[mTEPES.vESSSpillage[sc, p, n, es]() for sc, p, n, es in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es)))
        OutputToFile = OutputToFile.fillna(0)
        OutputToFile *= 1e3
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_ESSSpillage_' + CaseName + '.csv', sep=',')

        OutputToFile = pd.Series(data=[-mTEPES.vESSTotalCharge[sc, p, n, es]() * 1e3 for sc, p, n, es in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.es)))
        OutputToFile = pd.Series(data=[sum(OutputToFile[sc, p, n, es] for es in mTEPES.es if (gt, es) in mTEPES.t2g) for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_TechnologyCharge_' + CaseName + '.csv', sep=',')

    OutputToFile = pd.Series(data=[sum(mTEPES.vTotalOutput[sc, p, n, g]() for g in mTEPES.g if (gt, g) in mTEPES.t2g) * 1e3 for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_TechnologyOutput_' + CaseName + '.csv', sep=',')

    TechnologyOutput = OutputToFile.loc[:, :, :, :]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput = pd.Series([0.] * len(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt), index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
    for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt:
        NetTechnologyOutput[sc, p, n, gt] = TechnologyOutput[sc, p, n, gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='MW').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_FlexibilityTechnology_' + CaseName + '.csv', sep=',')

    MeanDemand = pd.Series(data=[sum(mTEPES.pDemand[sc, p, n, nd] for nd in mTEPES.nd) * 1e3 for sc, p, n in mTEPES.sc * mTEPES.p * mTEPES.n], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n))).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemand[sc, p, n, nd] for nd in mTEPES.nd) * 1e3 - MeanDemand for sc, p, n in mTEPES.sc * mTEPES.p * mTEPES.n], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n)))
    OutputToFile.to_frame(name='Demand').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2']).rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_FlexibilityDemand_' + CaseName + '.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.vTotalOutput[sc, p, n, g]() * mTEPES.pDuration[n] for sc, p, n, g in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.g], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.g)))
    OutputToFile = pd.Series(data=[sum(OutputToFile[sc, p, n, g] for g in mTEPES.g if (gt, g) in mTEPES.t2g) * 1e3 for sc, p, n, gt in mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt], index=pd.MultiIndex.from_tuples(list(mTEPES.sc * mTEPES.p * mTEPES.n * mTEPES.gt)))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0', 'level_1', 'level_2'], columns='level_3', values='GWh').rename_axis(['Scenario', 'Period', 'LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(CaseName + '/oT_Result_TechnologyEnergy_' + CaseName + '.csv', sep=',')

    TechnologyEnergy = OutputToFile.to_frame(name='GWh')

    TechnologyEnergy['GWh'] = (TechnologyEnergy['GWh'] / TechnologyEnergy['GWh'].sum()) * 100
    TechnologyEnergy.reset_index(level=3, inplace=True)

    TechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=-40, figsize=(15, 10), autopct='%1.1f%%', pctdistance=0.85)
    plt.legend(title='Energy Generation', loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))

    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)

    # plt.show()
    plt.savefig(CaseName + '/oT_Plot_TechnologyEnergy_' + CaseName + '.png', bbox_inches=None, dpi=600)

    #%% outputting the network operation
    OutputToFile = pd.Series(data=[mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ActiveNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[-1*(mTEPES.vP[sc,p,n,ni,nf,cc]())  for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ActiveNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ReactiveNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[-1*(mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]()) for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ReactiveNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.vQ_shc[sc,p,n,sh]() for sc,p,n,sh in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sh], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.sh)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','Shunt']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['Shunt'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ReactiveShuntInj_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ActiveNetworkLosses_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]() - mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ReactiveNetworkLosses_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[max((mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc])**2
                                        + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc]-mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]())**2,
                                        (mTEPES.vP[sc,p,n,ni,nf,cc]())**2+(mTEPES.vQ[sc,p,n,ni,nf,cc]()+mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]())**2)**.5/mTEPES.pLineSmax[ni,nf,cc].value*1e2
                                    for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_NetworkUtilization_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[((mTEPES.vP[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineR[ni,nf,cc])**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]()*mTEPES.pLineX[ni,nf,cc] - mTEPES.vQ_shl[sc,p,n,ni,ni,nf,cc]())**2)**.5 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ApparentNetworkFlow_FROM_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[((mTEPES.vP[sc,p,n,ni,nf,cc]())**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc]() + mTEPES.vQ_shl[sc,p,n,nf,ni,nf,cc]())**2)**.5 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0)
    OutputToFile *= 1e3
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_ApparentNetworkFlow_TO_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[(mTEPES.vVoltageMag_sqr[sc,p,n,ni]())**0.5 for sc,p,n,ni in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index= pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','Node']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(CaseName+'/oT_Result_NetworkVoltage_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.DataFrame.from_dict(mTEPES.vTheta.extract_values(), orient='index', columns=[str(mTEPES.vTheta)])
    OutputToFile.index = pd.MultiIndex.from_tuples(OutputToFile.index)
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivToFilee(OutputToFile, values=str(mTEPES.vTheta), index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).to_csv(CaseName+'/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.DataFrame.from_dict(mTEPES.vENS.extract_values(), orient='index', columns=[str(mTEPES.vENS)])
    OutputToFile.index = pd.MultiIndex.from_tuples(OutputToFile.index)
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','Node']
    pd.pivot_table(OutputToFile, values=str(mTEPES.vENS), index=['Scenario','Period','LoadLevel'], columns=['Node'], fill_value=0).to_csv(CaseName+'/oT_Result_NetworkPNS_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing output results                ... ', round(WritingResultsTime), 's')