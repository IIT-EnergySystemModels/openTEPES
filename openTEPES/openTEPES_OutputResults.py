"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 3, 2021
"""

import time
import os
import pandas as pd
from   collections   import defaultdict
import matplotlib.pyplot as plt
import pyomo.environ as pyo
from   pyomo.environ import Set


def InvestmentResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the investment decisions
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.gc):
        OutputToFile = pd.DataFrame.from_dict(OptModel.vGenerationInvest.extract_values(), orient='index', columns=[str(OptModel.vGenerationInvest)])
        OutputToFile.index.names = ['Generator']
        OutputToFile.to_csv(_path+'/oT_Result_GenerationInvestment_'+CaseName+'.csv', index=True, header=True)
    if len(mTEPES.lc):
        OutputToFile = pd.DataFrame.from_dict(OptModel.vNetworkInvest.extract_values(),    orient='index', columns=[str(OptModel.vNetworkInvest)])
        OutputToFile.index = pd.MultiIndex.from_tuples(OutputToFile.index)
        OutputToFile.index.names = ['InitialNode','FinalNode','Circuit']
        pd.pivot_table(OutputToFile, values=str(OptModel.vNetworkInvest), index=['InitialNode','FinalNode'], columns=['Circuit'], fill_value=0.0).to_csv(_path+'/oT_Result_NetworkInvestment_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing           investment results   ... ', round(WritingResultsTime), 's')


def GenerationOperationResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the generation operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[OptModel.vCommitment[sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationCommitment_'+CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vStartUp   [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationStartUp_'   +CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vShutDown  [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='p.u.').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='p.u.').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationShutDown_'  +CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        OutputToFile = pd.Series(data=[OptModel.vReserveUp     [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveUp_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveUp_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveUp  [sc,p,n,es]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSGenerationReserveUp_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSTechnologyReserveUp_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        OutputToFile = pd.Series(data=[OptModel.vReserveDown   [sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
        OutputToFile *= 1e3
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationReserveDown_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,nr] for nr in mTEPES.nr if (gt,nr) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyReserveDown_'+CaseName+'.csv', sep=',')

        if len(mTEPES.es):
            OutputToFile = pd.Series(data=[OptModel.vESSReserveDown[sc,p,n,es]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
            OutputToFile *= 1e3
            OutputToFile = OutputToFile.fillna(0.0)
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSGenerationReserveDown_'+CaseName+'.csv', sep=',')

            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSTechnologyReserveDown_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*1e3                                             for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
    OutputToFile.to_frame(name='MW ').reset_index().pivot_table(index=['level_0','level_1','level_2'],    columns='level_3', values='MW ').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutput_'   +CaseName+'.csv', sep=',')

    if len(mTEPES.r):
        OutputToFile = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-OptModel.vTotalOutput[sc,p,n,r]())*1e3            for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW'  ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RESCurtailment_'    +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[(mTEPES.pMaxPower[sc,p,n,r]-OptModel.vTotalOutput[sc,p,n,r]())*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RESCurtailmentEnergy_'    +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,r] for r in mTEPES.r if (gt,r) in mTEPES.t2g)         for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_RESTechnologyCurtailment_'+CaseName+'.csv', sep=',')

<<<<<<< HEAD
    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g ]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
=======
    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g ]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]()for sc,p,n,g  in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
>>>>>>> 66c396528af3c20431404330b283a0a60d86253e
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'],   columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEnergy_'  +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,nr]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]()*mTEPES.pCO2EmissionCost[nr]*1e-3/mTEPES.pCO2Cost() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='tCO2').reset_index().pivot_table(index=['level_0','level_1','level_2'],   columns='level_3', values='tCO2').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEmission_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutput_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
    OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,g] for g in mTEPES.g if (gt,g) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+CaseName+'.csv', sep=',')

    TechnologyEnergy = OutputToFile.to_frame(name='')
    TechnologyEnergy[''] = (TechnologyEnergy[''] / TechnologyEnergy[''].sum()) * 100
    TechnologyEnergy.reset_index(level=3, inplace=True)
    TechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=-40, figsize=(15, 10), autopct='%1.1f%%', pctdistance=0.85, title='Energy Generation', legend=False)
    # plt.legend(loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
    centre_circle = plt.Circle((0, 0), 0.60, fc='white')
    fg = plt.gcf()
    fg.gca().add_artist(centre_circle)
    # plt.show()
    plt.savefig(_path+'/oT_Plot_TechnologyEnergy_'+CaseName+'.png', bbox_inches=None, dpi=600)

    for ar in mTEPES.ar:
        if len(mTEPES.ar) > 1:
            OutputToFile = pd.Series(data=[OptModel.vTotalOutput[sc,p,n,g]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.g ))
            OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,g] for g in mTEPES.g if (ar,g) in mTEPES.a2g and (gt,g) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
            OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

            TechnologyEnergy = OutputToFile.to_frame(name='')
            TechnologyEnergy[''] = (TechnologyEnergy[''] / TechnologyEnergy[''].sum()) * 100
            TechnologyEnergy.reset_index(level=3, inplace=True)
            TechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=-40, figsize=(15, 10), autopct='%1.1f%%', pctdistance=0.85, title='Energy Generation in '+ar, legend=False)
            # plt.legend(loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
            centre_circle = plt.Circle((0, 0), 0.60, fc='white')
            fg = plt.gcf()
            fg.gca().add_artist(centre_circle)
            # plt.show()
            plt.savefig(_path+'/oT_Plot_TechnologyEnergy_'+ar+'_'+CaseName+'.png', bbox_inches=None, dpi=600)

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing generation operation results   ... ', round(WritingResultsTime), 's')


def ESSOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the ESS operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    if len(mTEPES.es):
        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [sc,p,n,es]()*1e3                 for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflows_' +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflows_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*1e3                 for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSChargeOutput_'    +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSTechnologyOutput_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vEnergyOutflows    [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyOutflowsEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSChargeEnergy_'    +CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSTechnologyEnergy_'+CaseName+'.csv', sep=',')

        OutputToFile *= -1
        ESSTechnologyEnergy = OutputToFile.to_frame(name='')
        ESSTechnologyEnergy[''] = (ESSTechnologyEnergy[''] / ESSTechnologyEnergy[''].sum()) * 100
        ESSTechnologyEnergy.reset_index(level=3, inplace=True)
        ESSTechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=90, figsize=(15, 10), autopct='%1.1f%%', title='ESS Energy Consumption', legend=False)
        # plt.legend(title='Energy Consumption', loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        centre_circle = plt.Circle((0, 0), 0.60, fc='white')
        fg = plt.gcf()
        fg.gca().add_artist(centre_circle)
        # plt.show()
        plt.savefig(_path+'/oT_Plot_ESSTechnologyEnergy_'+CaseName+'.png', bbox_inches=None, dpi=600)

        for ar in mTEPES.ar:
            if len(mTEPES.ar) > 1:
                OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge   [sc,p,n,es]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
                OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g and (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
                OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSTechnologyEnergy_'+ar+'_'+CaseName+'.csv', sep=',')

                OutputToFile *= -1
                ESSTechnologyEnergy = OutputToFile.to_frame(name='')
                ESSTechnologyEnergy[''] = (ESSTechnologyEnergy[''] / ESSTechnologyEnergy[''].sum()) * 100
                ESSTechnologyEnergy.reset_index(level=3, inplace=True)
                ESSTechnologyEnergy.groupby(['level_3']).sum().plot(kind='pie', subplots=True, shadow=False, startangle=90, figsize=(15, 10), autopct='%1.1f%%', title='ESS Energy Consumption in '+ar, legend=False)
                # plt.legend(title='Energy Consumption', loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
                centre_circle = plt.Circle((0, 0), 0.60, fc='white')
                fg = plt.gcf()
                fg.gca().add_artist(centre_circle)
                # plt.show()
                plt.savefig(_path+'/oT_Plot_ESSTechnologyEnergy_'+ar+'_'+CaseName+'.png', bbox_inches=None, dpi=600)

        OutputToFile = pd.Series(data=[OptModel.vESSInventory[sc,p,n,es]()                               for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSInventory_'+CaseName+'.csv', sep=',')

        # OutputToFile = pd.Series(data=[OptModel.vESSInventory[sc,p,n,es]()/mTEPES.pMaxStorage[sc,p,n,es] for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es if mTEPES.pMaxStorage[sc,p,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0], index=pd.MultiIndex.from_tuples(list(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)[mTEPES.pMaxStorage[sc,p,n,es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0]))
        # OutputToFile = OutputToFile.fillna(0.0)
        # OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSInventoryUtilization_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[OptModel.vESSSpillage [sc,p,n,es]()                               for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = OutputToFile.fillna(0.0)
        OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh', dropna=False).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSSpillage_'+CaseName+'.csv', sep=',')

        OutputToFile = pd.Series(data=[-OptModel.vESSTotalCharge[sc,p,n,es]()*1e3                        for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es],                                                                                       index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile = pd.Series(data=[sum(OutputToFile[sc,p,n,es] for es in mTEPES.es if (gt,es) in mTEPES.t2g) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
        OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_TechnologyCharge_'+CaseName+'.csv', sep=',')

        TechnologyCharge = OutputToFile.loc[:,:,:,:]

        for sc,p in mTEPES.sc*mTEPES.p:
            fig, fg = plt.subplots()
            fg.stackplot(range(len(mTEPES.n)),  TechnologyCharge.loc[sc,p,:,:].values.reshape(len(mTEPES.n),len(mTEPES.gt)).transpose().tolist(), labels=mTEPES.gt)
            # fg.stackplot(range(len(mTEPES.n)), -TechnologyCharge.loc[sc,p,:,:].values.reshape(len(mTEPES.n),len(mTEPES.gt)).transpose().tolist(), labels=list(mTEPES.gt))
            # fg.plot     (range(len(mTEPES.n)),  pDemand.sum(axis=1)*1e3, label='Demand', linewidth=0.2, color='k')
            fg.set(xlabel='Time Steps', ylabel='MW')
            plt.title(sc+' '+p)
            fg.tick_params(axis='x', rotation=90)
            fg.legend()
            plt.tight_layout()
            # plt.show()
            plt.savefig(_path+'/oT_Plot_TechnologyCharge_'+sc+'_'+p+'_'+CaseName+'.png', bbox_inches=None, dpi=600)

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing        ESS operation results   ... ', round(WritingResultsTime), 's')


def FlexibilityResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the flexibility
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,g]() for g in mTEPES.g if (gt,g) in mTEPES.t2g)*1e3 for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    TechnologyOutput     = OutputToFile.loc[:,:,:,:]
    MeanTechnologyOutput = OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
    NetTechnologyOutput  = pd.Series([0.0]*len(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt), index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt))
    for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt:
        NetTechnologyOutput[sc,p,n,gt] = TechnologyOutput[sc,p,n,gt] - MeanTechnologyOutput[gt]
    NetTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityTechnology_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        ESSTechnologies = [(sc,p,n,gt) for sc,p,n,gt in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.gt if sum(1 for es in mTEPES.es if (gt,es) in mTEPES.t2g)]
        OutputToFile = pd.Series(data=[sum(OptModel.vTotalOutput[sc,p,n,es]() for es in mTEPES.es if (gt,es) in mTEPES.t2g)*1e3 for sc,p,n,gt in ESSTechnologies], index=pd.MultiIndex.from_tuples(ESSTechnologies))
        ESSTechnologyOutput     = -OutputToFile.loc[:,:,:,:]
        MeanESSTechnologyOutput = -OutputToFile.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).mean()
        NetESSTechnologyOutput = pd.Series([0.0] * len(ESSTechnologies), index=pd.MultiIndex.from_tuples(ESSTechnologies))
        for sc,p,n,gt in ESSTechnologies:
            NetESSTechnologyOutput[sc,p,n,gt] = MeanESSTechnologyOutput[gt] - ESSTechnologyOutput[sc,p,n,gt]
        NetESSTechnologyOutput.to_frame(name='MW').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityESSTechnology_'+CaseName+'.csv', sep=',')

    MeanDemand   = pd.Series(data=[sum(mTEPES.pDemand[sc,p,n,nd] for nd in mTEPES.nd)*1e3              for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(mTEPES.pDemand[sc,p,n,nd] for nd in mTEPES.nd)*1e3 - MeanDemand for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n))
    OutputToFile.to_frame(name='Demand').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityDemand_'   +CaseName+'.csv', sep=',')

    MeanENS      = pd.Series(data=[sum(OptModel.vENS[sc,p,n,nd]() for nd in mTEPES.nd)*1e3           for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n)).mean()
    OutputToFile = pd.Series(data=[sum(OptModel.vENS[sc,p,n,nd]()*1e3 for nd in mTEPES.nd) - MeanENS for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n))
    OutputToFile.to_frame(name='PNS').reset_index().pivot_table(index=['level_0','level_1','level_2']).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_FlexibilityPNS_'   +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing          flexibility results   ... ', round(WritingResultsTime), 's')


def NetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the network operation
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[OptModel.vLineCommit  [sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkCommitment_'+CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOnState [sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOn_'  +CaseName+'.csv', sep=',')
    OutputToFile = pd.Series(data=[OptModel.vLineOffState[sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkSwitchOff_' +CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vFlow[sc,p,n,ni,nf,cc]()*1e3 for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='MW'), values='MW', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkFlow_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[abs(OptModel.vFlow[sc,p,n,ni,nf,cc]()/max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc])) for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.la))
    OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
    OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
    OutputToFile.index.names = [None] * len(OutputToFile.index.names)
    OutputToFile.to_csv(_path+'/oT_Result_NetworkUtilization_'+CaseName+'.csv', sep=',')

    if mTEPES.pIndNetLosses:
        OutputToFile = pd.Series(data=[OptModel.vLineLosses[sc,p,n,ni,nf,cc]() for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ll], index= pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ll))
        OutputToFile.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
        OutputToFile = pd.pivot_table(OutputToFile.to_frame(name='pu'), values='pu', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
        OutputToFile.index.names = [None] * len(OutputToFile.index.names)
        OutputToFile.to_csv(_path+'/oT_Result_NetworkLosses_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vTheta[sc,p,n,nd]()                   for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='rad').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='rad').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkAngle_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[sc,p,n,nd]()*1e3                 for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MW' ).reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MW' ).rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkPNS_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[OptModel.vENS[sc,p,n,nd]()*mTEPES.pDuration[n]*mTEPES.pLoadLevelWeight[n]() for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='GWh').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='GWh').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_NetworkENS_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing    network operation results   ... ', round(WritingResultsTime), 's')


def MarginalResults(DirName, CaseName, OptModel, mTEPES):
    #%% outputting the up operating reserve marginal
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    #%% outputting the LSRMC
    AppendData = []
    for st in mTEPES.st:
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n] for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd])], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eBalance_'+st)))
        AppendData.append(OutputToFile)
    mTEPES.del_component(mTEPES.n)
    mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
    AppendData = pd.concat(AppendData)
    AppendData.to_frame(name='LSRMC').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='LSRMC').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_LSRMC_'+CaseName+'.csv', sep=',')

    LSRMC = OutputToFile.loc[:,:]

    fig, fg = plt.subplots()
    for nd in mTEPES.nd:
        if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            fg.plot(range(len(LSRMC[:,:,:,nd])), LSRMC[:,:,:,nd], label=nd)
    fg.set(xlabel='Time Steps', ylabel='EUR/MWh')
    fg.set_ybound(lower=0, upper=100)
    plt.title('LSRMC')
    fg.tick_params(axis='x', rotation=90)
    fg.legend()
    plt.tight_layout()
    # plt.show()
    plt.savefig(_path+'/oT_Plot_LSRMC_'+CaseName+'.png', bbox_inches=None, dpi=600)

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveUp_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='UORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='UORM').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveUp_'+CaseName+'.csv', sep=',')

        MarginalUpOperatingReserve = OutputToFile.loc[:,:]

        fig, fg = plt.subplots()
        for ar in mTEPES.ar:
            if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n):
                fg.plot(range(len(MarginalUpOperatingReserve[:,:,:,ar])), MarginalUpOperatingReserve[:,:,:,ar], label=ar)
        fg.set(xlabel='Time Steps', ylabel='EUR/MW')
        fg.set_ybound(lower=0, upper=100)
        plt.title('Upward Operating Reserve Marginal')
        fg.tick_params(axis='x', rotation=90)
        fg.legend()
        plt.tight_layout()
        # plt.show()
        plt.savefig(_path+'/oT_Plot_MarginalOperatingReserveUpward_'+CaseName+'.png', bbox_inches=None, dpi=600)

    #%% outputting the down operating reserve marginal
    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g)], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eOperReserveDw_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='DORM').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='DORM').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_MarginalOperatingReserveDown_'+CaseName+'.csv', sep=',')

        MarginalDwOperatingReserve = OutputToFile.loc[:,:]

        fig, fg = plt.subplots()
        for ar in mTEPES.ar:
            if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n):
                fg.plot(range(len(MarginalDwOperatingReserve[:,:,:,ar])), MarginalDwOperatingReserve[:,:,:,ar], label=ar)
        fg.set(xlabel='Time Steps', ylabel='EUR/MW')
        fg.set_ybound(lower=0, upper=100)
        plt.title('Downward Operating Reserve Marginal')
        fg.tick_params(axis='x', rotation=90)
        fg.legend()
        plt.tight_layout()
        # plt.show()
        plt.savefig(_path+'/oT_Plot_MarginalOperatingReserveDownward_'+CaseName+'.png', bbox_inches=None, dpi=600)

    #%% outputting the water values
    if len(mTEPES.es):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eESSInventory_'+st)[sc,p,n,es]]*1e3/mTEPES.pScenProb[sc]/mTEPES.pDuration[n]/mTEPES.pLoadLevelWeight[n]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es if mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'eESSInventory_'+st)))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='WaterValue').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='WaterValue').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_WaterValue_'+CaseName+'.csv', sep=',')

        WaterValue = OutputToFile.loc[:,:]

        fig, fg = plt.subplots()
        for es in mTEPES.es:
            fg.plot(range(len(WaterValue[:,:,:,es])), WaterValue[:,:,:,es], label=es)
        fg.set(xlabel='Time Steps', ylabel='EUR/MWh')
        fg.set_ybound(lower=0, upper=100)
        plt.title('Water Value')
        fg.tick_params(axis='x', rotation=90)
        fg.legend()
        plt.tight_layout()
        # plt.show()
        plt.savefig(_path+'/oT_Plot_WaterValue_'+CaseName+'.png', bbox_inches=None, dpi=600)

    #%% Reduced cost for NetworkInvestment
    ReducedCostActivation = mTEPES.pIndBinGenInvest*len(mTEPES.gc) + mTEPES.pIndBinNetInvest*len(mTEPES.lc) + mTEPES.pIndBinGenOperat*len(mTEPES.nr) + mTEPES.pIndBinLineCommit*len(mTEPES.la)
    if len(mTEPES.lc) and not ReducedCostActivation:
        OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vNetworkInvest[ni,nf,cc]] for ni,nf,cc in mTEPES.lc], index=pd.MultiIndex.from_tuples(getattr(OptModel, 'vNetworkInvest')))
        OutputToFile.index.names = ['InitialNode', 'FinalNode', 'Circuit']
        OutputToFile.to_frame(name='p.u.').to_csv(_path + '/oT_Result_NetworkInvestment_ReducedCost_'+CaseName+'.csv', sep=',')

    # %% Reduced cost for NetworkCommitment
    mTEPES.las = Set(initialize=mTEPES.ni*mTEPES.nf*mTEPES.cc, ordered=False, doc='all real lines with switching decision', filter=lambda mTEPES,ni,nf,cc: (ni,nf,cc) in mTEPES.pLineX and mTEPES.pLineSwitching[ni,nf,cc])
    if len(mTEPES.las) and not ReducedCostActivation:
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.rc[OptModel.vLineCommit[sc,p,n,ni,nf,cc]] for sc,p,n,ni,nf,cc in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.las], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.las))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.index.names = ['Scenario','Period','LoadLevel','InitialNode','FinalNode','Circuit']
        AppendData = pd.pivot_table(AppendData.to_frame(name='p.u.'), values='p.u.', index=['Scenario','Period','LoadLevel'], columns=['InitialNode','FinalNode','Circuit'], fill_value=0.0)
        AppendData.index.names = [None] * len(AppendData.index.names)
        AppendData.to_csv(_path+'/oT_Result_NetworkCommitment_ReducedCost_' +CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime = time.time()
    print('Writing marginal information results   ... ', round(WritingResultsTime), 's')


def EconomicResults(DirName, CaseName, OptModel, mTEPES):
    # %% outputting the system costs and revenues
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    OutputToFile = pd.Series(data=[(mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pDuration[n] * mTEPES.pLinearVarCost  [nr] * OptModel.vTotalOutput[sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pDuration[n] * mTEPES.pConstantVarCost[nr] * OptModel.vCommitment [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pStartUpCost    [nr] * OptModel.vStartUp    [sc,p,n,nr]() +
                                    mTEPES.pScenProb[sc] * mTEPES.pLoadLevelWeight[n]()                       * mTEPES.pShutDownCost   [nr] * OptModel.vShutDown   [sc,p,n,nr]()) for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOperationCost_'   +CaseName+'.csv', sep=',')

    if len(mTEPES.r):
<<<<<<< HEAD
        OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pLinearOMCost [ r] * OptModel.vTotalOutput   [sc,p,n, r]() for sc,p,n, r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ))
=======
        OutputToFile = pd.Series(data=[(mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pLinearOMCost   [ r] * OptModel.vTotalOutput[sc,p,n, r]()) for sc,p,n, r in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.r ))
>>>>>>> 66c396528af3c20431404330b283a0a60d86253e
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationOandMCost_'   +CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pLinearVarCost[es] * OptModel.vESSTotalCharge[sc,p,n,es]() for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es))
        OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeOperationCost_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pCO2EmissionCost[nr] * OptModel.vTotalOutput[sc,p,n,nr]() for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEmissionCost_'+CaseName+'.csv', sep=',')

    OutputToFile = pd.Series(data=[mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLoadLevelWeight[n]() * mTEPES.pENSCost()           * OptModel.vENS        [sc,p,n,nd]() for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd))
    OutputToFile.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_3', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ReliabilityCost_'+CaseName+'.csv', sep=',')

    AppendData = []
    for st in mTEPES.st:
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
        if len(mTEPES.n):
            OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vTotalOutput[sc,p,n,g]() for sc,p,n,nd,g in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g], index=pd.MultiIndex.from_tuples(mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g))
        AppendData.append(OutputToFile)
    mTEPES.del_component(mTEPES.n)
    mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
    AppendData = pd.concat(AppendData)
    AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_GenerationEnergyRevenue_'+CaseName+'.csv', sep=',')

    if len(mTEPES.es):
        AppendData = []
        for st in mTEPES.st:
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
            if len(mTEPES.n):
                OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eBalance_'+st)[sc,p,n,nd]]/mTEPES.pScenProb[sc] * OptModel.vESSTotalCharge[sc,p,n,es]() for sc,p,n,nd,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,nd,es) for sc,p,n,nd,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.n2g if es in mTEPES.es]))
            AppendData.append(OutputToFile)
        mTEPES.del_component(mTEPES.n)
        mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
        AppendData = pd.concat(AppendData)
        AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ChargeEnergyRevenue_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        if len([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vReserveUp   [sc,p,n,nr]() for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_OperatingReserveUpRevenue_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveUp_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveUp[sc,p,n,es]() for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSOperatingReserveUpRevenue_'+CaseName+'.csv', sep=',')

    if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for sc,p,n,ar in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.ar):
        if len([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and nr in mTEPES.nr]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vReserveDown   [sc,p,n,nr]() for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and nr in mTEPES.nr], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,nr) for sc,p,n,ar,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and nr in mTEPES.nr]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_OperatingReserveDwRevenue_'+CaseName+'.csv', sep=',')
        if len([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveUp[sc,p,n,ar] and es in mTEPES.es]):
            AppendData = []
            for st in mTEPES.st:
                mTEPES.del_component(mTEPES.n)
                mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration and (st,nn) in mTEPES.s2n)
                if len(mTEPES.n):
                    OutputToFile = pd.Series(data=[OptModel.dual[getattr(OptModel, 'eOperReserveDw_'+st)[sc,p,n,ar]]*1e3/mTEPES.pScenProb[sc]*OptModel.vESSReserveDown[sc,p,n,es]() for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and es in mTEPES.es], index=pd.MultiIndex.from_tuples([(sc,p,n,ar,es) for sc,p,n,ar,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.a2g if mTEPES.pOperReserveDw[sc,p,n,ar] and es in mTEPES.es]))
                AppendData.append(OutputToFile)
            mTEPES.del_component(mTEPES.n)
            mTEPES.n = Set(initialize=mTEPES.nn, ordered=True, doc='load levels', filter=lambda mTEPES,nn: nn in mTEPES.pDuration)
            AppendData = pd.concat(AppendData)
            AppendData.to_frame(name='MEUR').reset_index().pivot_table(index=['level_0','level_1','level_2'], columns='level_4', values='MEUR').rename_axis(['Scenario','Period','LoadLevel'], axis=0).rename_axis([None], axis=1).to_csv(_path+'/oT_Result_ESSOperatingReserveDwRevenue_'+CaseName+'.csv', sep=',')

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing             economic results   ... ', round(WritingResultsTime), 's')


def NetworkMapResults(DirName, CaseName, OptModel, mTEPES):
    #%% plotting the network in a map
    _path = os.path.join(DirName, CaseName)
    StartTime = time.time()

    import cartopy.crs          as ccrs
    import cartopy.io.img_tiles as cimgt
    import cartopy.feature      as cfeature
    from matplotlib.transforms import offset_copy

    # Create a Stamen terrain background instance.
    stamen_terrain = cimgt.Stamen('terrain-background')

    fig = plt.figure()

    # Create a GeoAxes in the tile's projection.
    ax = fig.add_subplot(1, 1, 1, projection=stamen_terrain.crs)

    # Limit the extent of the map to a small longitude/latitude range.
    ax.set_extent((min(mTEPES.pNodeLon.values()) - 2, max(mTEPES.pNodeLon.values()) + 2,
                   min(mTEPES.pNodeLat.values()) - 2, max(mTEPES.pNodeLat.values()) + 2), crs=ccrs.Geodetic())

    ax.add_feature(cfeature.BORDERS, linewidth=1  )
    ax.add_feature(cfeature.STATES,  linewidth=0.1)
    # Add the Stamen data at zoom level 8.
    ax.add_image(stamen_terrain, 8)

    # Use the cartopy interface to create a matplotlib transform object
    # for the Geodetic coordinate system. We will use this along with
    # matplotlib's offset_copy function to define a coordinate system which
    # translates the text by 25 pixels to the left.
    geodetic_transform = ccrs.Geodetic()._as_mpl_transform(ax)
    text_transform = offset_copy(geodetic_transform, units='dots', x=-10)

    # node name
    for nd in mTEPES.nd:
        # plt.annotate(nd, [mTEPES.pNodeLon[nd], mTEPES.pNodeLat[nd]])
        # Add text 25 pixels to the left of each node.
        ax.text(mTEPES.pNodeLon[nd], mTEPES.pNodeLat[nd], nd, fontsize=8, verticalalignment='center', horizontalalignment='right', transform=text_transform, bbox=dict(facecolor='sandybrown', alpha=0.5, boxstyle='round'))

    #%% colors of the lines according to the ENTSO-E color code
    # existing lines
    for ni,nf,cc in mTEPES.le:
        if (ni,nf,cc) in mTEPES.lea:
            if mTEPES.pLineVoltage[ni,nf,cc] > 700 and mTEPES.pLineVoltage[ni,nf,cc] <= 900:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='blue'   , linewidth=2  , marker='o', linestyle='solid', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 500 and mTEPES.pLineVoltage[ni,nf,cc] <= 700:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='#ff8000', linewidth=2  , marker='o', linestyle='solid', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 350 and mTEPES.pLineVoltage[ni,nf,cc] <= 500:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='red'    , linewidth=1  , marker='o', linestyle='solid', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 290 and mTEPES.pLineVoltage[ni,nf,cc] <= 350:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='green'  , linewidth=0.4, marker='o', linestyle='solid', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 200 and mTEPES.pLineVoltage[ni,nf,cc] <= 290:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='green'  , linewidth=0.4, marker='o', linestyle='solid', transform=ccrs.PlateCarree())
            if                                         mTEPES.pLineVoltage[ni,nf,cc] <= 200:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='#ff6300', linewidth=0.4, marker='o', linestyle='solid', transform=ccrs.PlateCarree())
        else:
            ax.plot    ([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='magenta', linewidth=1  , marker='o', linestyle='solid', transform=ccrs.PlateCarree())
    # candidate lines
    for ni,nf,cc in mTEPES.lc:
        if (ni,nf,cc) in mTEPES.lca and OptModel.vNetworkInvest[ni,nf,cc]() > 0:
            if mTEPES.pLineVoltage[ni,nf,cc] > 700 and mTEPES.pLineVoltage[ni,nf,cc] <= 900:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='blue'   , linewidth=2  , marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 500 and mTEPES.pLineVoltage[ni,nf,cc] <= 700:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='#ff8000', linewidth=2  , marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 350 and mTEPES.pLineVoltage[ni,nf,cc] <= 500:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='red'    , linewidth=1  , marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 290 and mTEPES.pLineVoltage[ni,nf,cc] <= 350:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='green'  , linewidth=0.4, marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
            if mTEPES.pLineVoltage[ni,nf,cc] > 200 and mTEPES.pLineVoltage[ni,nf,cc] <= 290:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='green'  , linewidth=0.4, marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
            if                                         mTEPES.pLineVoltage[ni,nf,cc] <= 200:
                ax.plot([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='#ff6300', linewidth=0.4, marker='o', linestyle='dashed', transform=ccrs.PlateCarree())
        else:
            ax.plot    ([mTEPES.pNodeLon[ni], mTEPES.pNodeLon[nf]], [mTEPES.pNodeLat[ni], mTEPES.pNodeLat[nf]], color='magenta', linewidth=1  , marker='o', linestyle='dashed', transform=ccrs.PlateCarree())

    # # line NTC
    # for ni,nf,cc in mTEPES.la:
    #     ax.annotate(round(mTEPES.pLineNTC[ni,nf,cc]*1e3), [(mTEPES.pNodeLon[ni]+mTEPES.pNodeLon[nf])/2, (mTEPES.pNodeLat[ni]+mTEPES.pNodeLat[nf])/2])

    plt.title('Network Map')
    # # Place a legend to the right of this smaller subplot.
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    # plt.show()
    plt.savefig(_path+'/oT_Plot_MapNetwork_'+CaseName+'.png', bbox_inches=None, dpi=1200)

    PlottingNetMapsTime = time.time() - StartTime
    print('Plotting network maps                  ... ', round(PlottingNetMapsTime), 's')
