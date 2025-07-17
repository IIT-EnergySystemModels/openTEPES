import os
import multiprocessing
import itertools
from functools import partial

from openTEPES.openTEPES import openTEPES_run
from pathlib             import Path

import pandas as pd
import shutil
import time

Start_time = time.time()

# Base directory setup
base_folder_name = "SE2025"
target_folder_name = "SE2025_Temporal"
parent_folder_name = "Dataset"
base_dir = Path(r"C:\Users\erikal\OneDrive - RISE\Projects\P124390.AP05DP04.A2025_GridSecure\codes\cases")
source_dir = base_dir / base_folder_name
target_dir = base_dir / parent_folder_name / target_folder_name

def setup_test_case(dir, folder, case):
    """
    Set up the test case by modifying the necessary CSV files and preparing input data.
    Returns the data required for running openTEPES.
    """
    source = dir/folder
    data = dict(
        DirName=source,
        CaseName=case,
        SolverName="gurobi",  # You can change the solver here
        pIndLogConsole='No',
        pIndOutputResults='No',
    )
    print("-Setting up test case...")  # Added print for console feedback
    return data

# set of lines
set_lines = [
    ('SE1', 'SE2', 'cc1'),
    ('SE2', 'SE3', 'cc1'),
    ('SE3', 'SE4', 'cc1'),
    ('SE1', 'FI', 'cc1'),
    ('SE1', 'NO4', 'cc1'),
    ('SE2', 'NO3', 'cc1'),
    ('SE2', 'NO4', 'cc1'),
    ('SE3', 'DK1', 'cc1'),
    ('SE3', 'FI', 'cc1'),
    ('SE3', 'NO1', 'cc1'),
    ('SE4', 'DE', 'cc1'),
    ('SE4', 'DK2', 'cc1'),
    ('SE4', 'LT', 'cc1'),
    ('SE4', 'PL', 'cc1'),
]

# Mapping of export capacity factors to labels
dict_factor_1 = {
    -2.00: '-200%', -1.95: '-195%', -1.90: '-190%', -1.85: '-185%', -1.80: '-180%',
    -1.75: '-175%', -1.70: '-170%', -1.65: '-165%', -1.60: '-160%', -1.55: '-155%',
    -1.50: '-150%', -1.45: '-145%', -1.40: '-140%', -1.35: '-135%', -1.30: '-130%',
    -1.25: '-125%', -1.20: '-120%', -1.15: '-115%', -1.10: '-110%', -1.05: '-105%',
    -1.00: '-100%', -0.95: '-95%' , -0.90: '-90%' , -0.85: '-85%' , -0.80: '-80%' ,
    -0.75: '-75%' , -0.70: '-70%' , -0.65: '-65%' , -0.60: '-60%' , -0.55: '-55%' ,
    -0.50: '-50%' , -0.45: '-45%' , -0.40: '-40%' , -0.35: '-35%' , -0.30: '-30%' ,
    -0.25: '-25%' , -0.20: '-20%' , -0.15: '-15%' , -0.10: '-10%' , -0.05: '-5%'  ,
     0.0: '0%',  # 0% is the base case
     0.05: '+5%'  ,  0.10: '+10%' ,  0.15: '+15%' ,  0.20: '+20%' ,  0.25: '+25%' ,
     0.30: '+30%' ,  0.35: '+35%' ,  0.40: '+40%' ,  0.45: '+45%' ,  0.50: '+50%' ,
     0.55: '+55%' ,  0.60: '+60%' ,  0.65: '+65%' ,  0.70: '+70%' ,  0.75: '+75%' ,
     0.80: '+80%' ,  0.85: '+85%' ,  0.90: '+90%' ,  0.95: '+95%' ,  1.00: '+100%',
     1.05: '+105%',  1.10: '+110%',  1.15: '+115%',  1.20: '+120%',  1.25: '+125%',
     1.30: '+130%',  1.35: '+135%',  1.40: '+140%',  1.45: '+145%',  1.50: '+150%',
     1.55: '+155%',  1.60: '+160%',  1.65: '+165%',  1.70: '+170%',  1.75: '+175%',
     1.80: '+180%',  1.85: '+185%',  1.90: '+190%',  1.95: '+195%',  2.00: '+200%',
}

df_duration = pd.read_csv(source_dir / f'oT_Data_Duration_{base_folder_name}.csv')

# Factors and filenames
factor_0 = list(set_lines)
factor_1 = list(dict_factor_1.keys())  # export capacity multipliers
# factor 2 is the load levels in the df_duration if the duration is 1
factor_2 = df_duration[df_duration['Duration'] == 1]['LoadLevel'].tolist()
factor_3 = [f'oT_Data_VariableTTCFrw_{base_folder_name}', f'oT_Data_VariableTTCBck_{base_folder_name}']

Total_iter = len(factor_0) * len(factor_1) * len(factor_2)

dict_TTC = {
    f'oT_Data_VariableTTCFrw_{base_folder_name}': [f'oT_Data_Demand_{base_folder_name}'],
    f'oT_Data_VariableTTCBck_{base_folder_name}': [f'oT_Data_VariableMaxEnergy_{base_folder_name}', f'oT_Data_VariableMinEnergy_{base_folder_name}'],
}

# Create directory if it doesn't exist
if not target_dir.exists():
    target_dir.mkdir(parents=True)
    print(f"-Created directory: {target_dir}")
else:
    print(f"-Directory already exists: {target_dir}")

# Copy all CSV files matching "oT_Data" or "oT_Dict"
for file in source_dir.glob("*.csv"):
    if "oT_Data" in file.name or "oT_Dict" in file.name:
        new_name = file.stem + f"_Temporal.csv"
        target_file = target_dir / new_name
        if not target_file.exists():
            shutil.copy2(file, target_file)
            print(f"--Copied: {file.name} → {target_dir}")
        else:
            print(f"--File already exists: {target_file}")


file_frw = source_dir / (f'oT_Data_VariableTTCFrw_{base_folder_name}.csv')
file_bck = source_dir / (f'oT_Data_VariableTTCBck_{base_folder_name}.csv')
file_dem = source_dir / (f'oT_Data_Demand_{base_folder_name}.csv')
file_max = source_dir / (f'oT_Data_VariableMaxEnergy_{base_folder_name}.csv')
file_min = source_dir / (f'oT_Data_VariableMinEnergy_{base_folder_name}.csv')

df_frw = pd.read_csv(file_frw, sep=',', encoding='utf-8', index_col=[0, 1, 2], header=[0, 1, 2])
df_bck = pd.read_csv(file_bck, sep=',', encoding='utf-8', index_col=[0, 1, 2], header=[0, 1, 2])
df_dem = pd.read_csv(file_dem, sep=',', encoding='utf-8', index_col=[0, 1, 2])
df_max = pd.read_csv(file_max, sep=',', encoding='utf-8', index_col=[0, 1, 2])
df_min = pd.read_csv(file_min, sep=',', encoding='utf-8', index_col=[0, 1, 2])

file_frw_mod = target_dir / (f'oT_Data_VariableTTCFrw_{target_folder_name}.csv')
file_bck_mod = target_dir / (f'oT_Data_VariableTTCBck_{target_folder_name}.csv')
file_dem_mod = target_dir / (f'oT_Data_Demand_{target_folder_name}.csv')
file_max_mod = target_dir / (f'oT_Data_VariableMaxEnergy_{target_folder_name}.csv')
file_min_mod = target_dir / (f'oT_Data_VariableMinEnergy_{target_folder_name}.csv')

# # define the dataframe that will store the marginal costs
# dict_obj = {}
df_marginal_costs = pd.DataFrame(columns=['BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable', 'Value'])

iter = 0

print(f"Total time before iteration: {time.time() - Start_time:.2f} seconds")

# Execution of the scenarios
for f0 in factor_0:
    for f1 in factor_1:
        for f2 in factor_2:
            Initial_time = time.time()
            print(f'Sequence for interconnector {f0} with factor {f1} and load level {f2}...')
            df_frw_mod = df_frw.copy()
            df_bck_mod = df_bck.copy()
            df_dem_mod = df_dem.copy()
            df_max_mod = df_max.copy()
            df_min_mod = df_min.copy()
            try:
                df = df_duration.copy()
                df.set_index(['Period', 'Scenario', 'LoadLevel'], inplace=True)

                df['Duration'] = 0  # Ensure 'Duration' is float
                df.loc[pd.IndexSlice[:, :, f2], 'Duration'] = 1
                print(f"Modified oT_Data_Duration for factor {f1} and load level {f2}")
                scenario_dir = target_dir  / (f'oT_Data_Duration_{target_folder_name}.csv')
                df.to_csv(scenario_dir, sep=',', encoding='utf-8', index=True)
            except Exception as e:
                print(f"-Error modifying oT_Data_Duration in {target_dir}: {e}")

            if file_frw.exists() and file_bck.exists():

                val_frw = df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0].values[0]
                val_bck = df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0].values[0]

                # Determine which value to use
                if val_frw != 1e-5:
                    ttc_source = 'Frw'
                    base_val = val_frw
                elif val_bck != 1e-5:
                    ttc_source = 'Bck'
                    base_val = val_bck
                else:
                    print(f"-Both Frw and Bck values are 1e-5 for {f0} at load level {f2}, skipping modification.")
                    ttc_source = None
                    base_val = None

                # Apply logic only based on the source of TTC and is base_val is not None
                if ttc_source == 'Frw':
                    if f1 < 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] = base_val * -f1
                        if 'SE' not in f0[1]:
                            df_dem_mod.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = 1e-5
                            df_max_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = base_val * -f1
                            df_min_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = base_val * -f1
                    elif f1 == 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        if 'SE' not in f0[1]:
                            df_dem_mod.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = 1e-5
                    elif f1 > 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] *= base_val * f1
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] *= 1e-5
                        if 'SE' not in f0[1]:
                            df_dem_mod.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] *= f1
                elif ttc_source == 'Bck':
                    if f1 < 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] = base_val * -f1
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        if 'SE' not in f0[1]:
                            df_dem_mod.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = base_val * -f1
                            df_max_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                            df_min_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                    elif f1 == 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
                        if 'SE' not in f0[1]:
                            df_max_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                            df_min_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                    elif f1 > 0:
                        df_frw_mod.loc[pd.IndexSlice[:, :, f2], f0] *= 1e-5
                        df_bck_mod.loc[pd.IndexSlice[:, :, f2], f0] *= base_val * f1
                        if 'SE' not in f0[1]:
                            df_max_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] *= f1
                            df_min_mod.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] *= f1
                else:
                    print(f"-No valid TTC source found for {f0} at load level {f2}, skipping modification.")
                    continue

                # Update the DataFrames with modified values
                df_frw_mod.to_csv(file_frw_mod, sep=',', encoding='utf-8', index=True)
                df_bck_mod.to_csv(file_bck_mod, sep=',', encoding='utf-8', index=True)
                df_dem_mod.to_csv(file_dem_mod, sep=',', encoding='utf-8', index=True)
                df_max_mod.to_csv(file_max_mod, sep=',', encoding='utf-8', index=True)
                df_min_mod.to_csv(file_min_mod, sep=',', encoding='utf-8', index=True)

                print(f"-Modified {f0} in {target_folder_name} for factor {f1} and load level {f2}")

            case_name = target_folder_name
            print(f'-Running openTEPES of {case_name} for interconnector {f0} with factor {f1} and load level {f2}...')
            try:
                # Create the case name based on the factors
                case_data = setup_test_case(base_dir, parent_folder_name, case_name)
                mTEPES = openTEPES_run(**case_data)
                print(f'--openTEPES run completed for {case_name} with factor {f1} and load level {f2}')
                # extract the objective values in df_marginal_costs
                objective_values = mTEPES.vTotalSCost()
                # store the objective values in df_marginal_costs
                new_row = {
                    'BiddingZoneFrom': f0[0],
                    'BiddingZoneTo': f0[1],
                    'Factor': dict_factor_1[f1],
                    'LoadLevel': f2,
                    'Zone': 'System',
                    'Variable': 'TotalCost',
                    'Value': objective_values
                }

                df_marginal_costs = pd.concat([df_marginal_costs, pd.DataFrame([new_row])], ignore_index=True)
                #
                print(f'--Objective value extracted for {case_name} with factor {f1} and load level {f2}: {objective_values}')

                # dict_obj[(f0, f1, f2)] = objective_values
                # read csv "oT_Result_NetworkSRMC_{case_name}.csv"
                pri_file = target_dir / f'oT_Result_NetworkSRMC_{case_name}.csv'
                if pri_file.exists():
                    pri_df = pd.read_csv(pri_file, index_col=[0, 1, 2])
                    # stack the columns
                    pri_df = pri_df.stack().reset_index()
                    pri_df.columns = ['Period', 'Scenario', 'LoadLevel', 'Node', 'Price']
                    pri_df['BiddingZoneFrom'] = f0[0]
                    pri_df['BiddingZoneTo'] = f0[1]
                    pri_df['Factor'] = dict_factor_1[f1]
                    pri_df['Variable'] = 'Price'
                    # rename columns "Node" to "Zone", "Price" to "Value"
                    pri_df.rename(columns={'Node': 'Zone', 'Price': 'Value'}, inplace=True)
                    # select columns
                    pri_df = pri_df[['BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable', 'Value']]
                    # concatenate the pri_df to df_marginal_costs
                    df_marginal_costs = pd.concat([df_marginal_costs, pri_df], ignore_index=True)
                    #
                    print(f'--Price data extracted for {case_name} with factor {f1} and load level {f2}')

            except Exception as e:
                print(f"-Error occurred while running openTEPES for {case_name} with factor {f1} and load level {f2}: {e}")

            # save the marginal costs to a csv file
            file_dataset_csv = base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.csv'
            if file_dataset_csv.exists():
                print(f"--File already exists: {file_dataset_csv}, appending data.")
                # Append to the existing file
                existing_df = pd.read_csv(file_dataset_csv)
                df_marginal_costs = pd.concat([existing_df, df_marginal_costs], ignore_index=True)
                # filter out duplicates based on 'BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable'
                df_marginal_costs = df_marginal_costs.drop_duplicates(subset=['BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable'])
                df_marginal_costs.to_csv(base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.csv', index=False)
            else:
                print(f"--Creating new file: {file_dataset_csv}")
                df_marginal_costs.to_csv(file_dataset_csv, index=False)

            file_dataset_parquet = base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.parquet'
            if file_dataset_parquet.exists():
                print(f"--File already exists: {file_dataset_parquet}, appending data.")
                # Append to the existing file
                existing_df = pd.read_parquet(file_dataset_parquet)
                df_marginal_costs = pd.concat([existing_df, df_marginal_costs], ignore_index=True)
                # filter out duplicates based on 'BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable'
                df_marginal_costs = df_marginal_costs.drop_duplicates(subset=['BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable'])
                df_marginal_costs.to_parquet(base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.parquet', index=False)
            else:
                print(f"--Creating new file: {file_dataset_parquet}")
                df_marginal_costs.to_parquet(file_dataset_parquet, index=False)

            iter += 1
            print(f"  -Progress: {iter}/{Total_iter} ({(iter / Total_iter) * 100:.2f}%)")
            print(f"  -Time taken for this iteration: {time.time() - Initial_time:.2f} seconds")

print(f"Total time taken: {time.time() - Start_time:.2f} seconds")
# end of the script
print("All scenarios executed successfully.")
