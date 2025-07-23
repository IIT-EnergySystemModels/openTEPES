from concurrent.futures  import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from itertools           import product
from pathlib             import Path
import os
import sys
# Add the root project folder to the Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from openTEPES import openTEPES as oT
from openTEPES import openTEPES_ModelFormulation as oT_MF
from pyomo.opt import check_optimal_termination

import pandas as pd
import shutil
import time

# ─── Configuration ─────────────────────────────────────────────────────────────

# Base directory setup
base_folder_name = "SE2025"
target_folder_name = "SE2025_Temporal"
parent_folder_name = "Dataset"
base_dir = Path(r"C:\Users\erikal\Downloads\GridSecure")
source_dir = base_dir / base_folder_name
target_dir = base_dir / parent_folder_name / target_folder_name

# set of lines
set_lines = [
    # ('SE1', 'SE2', 'cc1'),
    # ('SE2', 'SE3', 'cc1'),
    # ('SE3', 'SE4', 'cc1'),
    ('SE1', 'FI', 'cc1'),
    # ('SE1', 'NO4', 'cc1'),
    # ('SE2', 'NO3', 'cc1'),
    # ('SE2', 'NO4', 'cc1'),
    # ('SE3', 'DK1', 'cc1'),
    # ('SE3', 'FI', 'cc1'),
    # ('SE3', 'NO1', 'cc1'),
    # ('SE4', 'DE', 'cc1'),
    # ('SE4', 'DK2', 'cc1'),
    # ('SE4', 'LT', 'cc1'),
    # ('SE4', 'PL', 'cc1'),
]

# Mapping of export capacity factors to
# dict_factor_1 = {-1.00: '-100%'}
dict_factor_1 = {
    # -2.00: '-200%', -1.95: '-195%', -1.90: '-190%', -1.85: '-185%', -1.80: '-180%',
    # -1.75: '-175%', -1.70: '-170%', -1.65: '-165%', -1.60: '-160%', -1.55: '-155%',
    # -1.50: '-150%', -1.45: '-145%', -1.40: '-140%', -1.35: '-135%', -1.30: '-130%',
    # -1.25: '-125%', -1.20: '-120%', -1.15: '-115%', -1.10: '-110%', -1.05: '-105%',
    -1.00: '-100%', -0.95: '-95%' , -0.90: '-90%' , -0.85: '-85%' , -0.80: '-80%' ,
    -0.75: '-75%' , -0.70: '-70%' , -0.65: '-65%' , -0.60: '-60%' , -0.55: '-55%' ,
    -0.50: '-50%' , -0.45: '-45%' , -0.40: '-40%' , -0.35: '-35%' , -0.30: '-30%' ,
    -0.25: '-25%' , -0.20: '-20%' , -0.15: '-15%' , -0.10: '-10%' , -0.05: '-5%'  ,
     0.0: '0%',  # 0% is the base case
     0.05: '+5%'  ,  0.10: '+10%' ,  0.15: '+15%' ,  0.20: '+20%' ,  0.25: '+25%' ,
     0.30: '+30%' ,  0.35: '+35%' ,  0.40: '+40%' ,  0.45: '+45%' ,  0.50: '+50%' ,
     0.55: '+55%' ,  0.60: '+60%' ,  0.65: '+65%' ,  0.70: '+70%' ,  0.75: '+75%' ,
     0.80: '+80%' ,  0.85: '+85%' ,  0.90: '+90%' ,  0.95: '+95%' ,  1.00: '+100%',
     # 1.05: '+105%',  1.10: '+110%',  1.15: '+115%',  1.20: '+120%',  1.25: '+125%',
     # 1.30: '+130%',  1.35: '+135%',  1.40: '+140%',  1.45: '+145%',  1.50: '+150%',
     # 1.55: '+155%',  1.60: '+160%',  1.65: '+165%',  1.70: '+170%',  1.75: '+175%',
     # 1.80: '+180%',  1.85: '+185%',  1.90: '+190%',  1.95: '+195%',  2.00: '+200%',
}

df_duration = pd.read_csv(source_dir / f'oT_Data_Duration_{base_folder_name}.csv')

# Factors and filenames
factor_0 = list(set_lines)
factor_1 = list(dict_factor_1.keys())  # export capacity multipliers
factor_2 = df_duration[df_duration['Duration'] == 1]['LoadLevel'].tolist()
# # select the load levels from the duration file, from the position 1608 and 1775, and from the position 2448 to 2615
factor_2 = factor_2[1608:1776] + factor_2[2448:2616]

# # select the first 2000 load levels
# factor_2 = factor_2[:100]  # Limit to the first 2000 load levels for testing

def load_existing_combos(csv_path: Path) -> set[tuple]:
    """
    Reads the CSV at csv_path (if it exists) and returns a set of
    (BiddingZoneFrom, BiddingZoneTo, Factor, LoadLevel) tuples.
    """
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        iters = {
            (bf, bt, fac, lvl)
            for bf, bt, fac, lvl in zip(df['BiddingZoneFrom'], df['BiddingZoneTo'], df['Factor'], df['LoadLevel'])
        }
    else:
        print(f"Warning: {csv_path} does not exist. Returning an empty set.")
        iters = set()

    return iters


def compute_new_iterations(
        factor_0: list[tuple],
        factor_1: list,
        factor_2: list,
        existing_combos: set[tuple],
        factor_map: dict
) -> list[tuple]:
    """
    Yields only those (f0,f1,f2) triples whose
    (f0[0], f0[1], factor_map[f1], f2) key is NOT in existing_combos,
    and returns them sorted by (BiddingZoneFrom, BiddingZoneTo, Factor, LoadLevel).
    """
    # localize lookups
    emap = factor_map
    ex = existing_combos

    # filter via a generator, then sort exactly once
    new_iters = sorted(
        (
            (i0, i1, i2)
            for i0, i1, i2 in product(factor_0, factor_1, factor_2) if (i0[0], i0[1], emap[i1], i2) not in ex),
        key=lambda tpl: (tpl[0][0], tpl[0][1], emap[tpl[1]], tpl[2])
    )
    return new_iters


# --- usage ---------------------------------------------------

existent_csv    = (base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.csv')
existing_combos = load_existing_combos(existent_csv)
new_iters       = compute_new_iterations(factor_0, factor_1, factor_2, existing_combos, dict_factor_1)

print(f"Total iterations to run: {len(new_iters)}, which were not run from the total of {len(factor_0) * len(factor_1) * len(factor_2)} possible combinations.")

num_workers = 1

# ─── Per‐scenario worker function ────────────────────────────────────────────────

def run_scenario(args, model):
    """
    args: tuple (f0, f1, f2)
      - f0: (from_zone, to_zone, 'cc1')
      - f1: export-factor float
      - f2: load level
    Returns: a DataFrame of marginal costs for that scenario.
    """
    df_marginal_costs = pd.DataFrame(columns=['BiddingZoneFrom', 'BiddingZoneTo', 'Factor', 'LoadLevel', 'Zone', 'Variable', 'Value'])
    f0, f1, f2 = args
    print(f"Running scenario: {f0}, factor: {f1}, load level: {f2}")
    f2_new = str(f2).replace(" ", "-").replace(":", "-")

     # unique case name and folder
    factor_label = dict_factor_1[f1]


    # # Load data from scenario folder
    # source_files = scenario_files(source_dir, base_folder_name)

    df_frw = pd.read_csv(source_files['frw'],  index_col=[0,1,2], header=[0,1,2])
    df_bck = pd.read_csv(source_files['bck'],  index_col=[0,1,2], header=[0,1,2])
    df_dem = pd.read_csv(source_files['dem'],  index_col=[0,1,2])
    df_max = pd.read_csv(source_files['max'],  index_col=[0,1,2])
    df_min = pd.read_csv(source_files['min'],  index_col=[0,1,2])

    # Modify duration file
    df_dur = df_duration.set_index(['Period', 'Scenario', 'LoadLevel']).copy()
    df_dur['Duration'] = 0  # Ensure 'Duration' is float
    idx = pd.IndexSlice[:, :, f2]
    df_dur.loc[idx, 'Duration'] = 1.0  # Set duration for the specified load level
    df_dur.to_csv(scenario_dir / f'oT_Data_Duration_{case_name}.csv', sep=',', encoding='utf-8', index=True)

    # Modify the TTC values based on the factor and load level
    key = pd.IndexSlice[:, :, f2]
    val_frw = df_frw.loc[key, f0].values[0]
    val_bck = df_bck.loc[key, f0].values[0]

    # Determine which value to use
    if val_frw != 1e-5:
        ttc_source, base_val = 'Frw', val_frw
    elif val_bck != 1e-5:
        ttc_source, base_val = 'Bck', val_bck
    else:
        print(f"No TTC for {f0} at LL={f2}")
        ttc_source = None
        base_val = None

    # Apply logic only based on the source of TTC and is base_val is not None
    if ttc_source == 'Frw':
        if f1 < 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = base_val * -f1
            if 'SE' not in f0[1]:
                df_dem.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = 1e-5
                df_max.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = base_val * -f1
                df_min.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = base_val * -f1
        elif f1 == 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            if 'SE' not in f0[1]:
                df_dem.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = 1e-5
        elif f1 > 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = base_val * f1
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            if 'SE' not in f0[1]:
                df_dem.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] *= f1
    elif ttc_source == 'Bck':
        if f1 < 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = base_val * -f1
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            if 'SE' not in f0[1]:
                df_dem.loc[pd.IndexSlice[:, f0[1]], f'{f0[1]}'] = base_val * -f1
                df_max.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                df_min.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
        elif f1 == 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            if 'SE' not in f0[1]:
                df_max.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
                df_min.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] = 1e-5
        elif f1 > 0:
            df_frw.loc[pd.IndexSlice[:, :, f2], f0] = 1e-5
            df_bck.loc[pd.IndexSlice[:, :, f2], f0] = base_val * f1
            if 'SE' not in f0[1]:
                df_max.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] *= f1
                df_min.loc[pd.IndexSlice[:, :, f2], f'Gen_{f0[1]}'] *= f1
    else:
        print(f"-No valid TTC source found for {f0} at load level {f2}, skipping modification.")

    target_files = scenario_files(scenario_dir, case_name)

    # Update the DataFrames with modified values
    df_frw.to_csv(target_files['frw'], sep=',', encoding='utf-8', index=True)
    df_bck.to_csv(target_files['bck'], sep=',', encoding='utf-8', index=True)
    df_dem.to_csv(target_files['dem'], sep=',', encoding='utf-8', index=True)
    df_max.to_csv(target_files['max'], sep=',', encoding='utf-8', index=True)
    df_min.to_csv(target_files['min'], sep=',', encoding='utf-8', index=True)

    print(f"-Modified {f0} in {scenario_dir} for factor {f1} and load level {f2}")

    try:
        oT._configure_basic_components(base_dir, base_folder_name, model, pLog)
        oT_MF.TotalObjectiveFunction(mTEPES, mTEPES, pLog)
        oT_MF.InvestmentModelFormulation(mTEPES, mTEPES, pLog)
        # Prepare the openTEPES inputs
        mTEPES = openTEPES_run(
            DirName = target_dir,
            CaseName = case_name,
            SolverName = "gurobi",  # You can change the solver here
            pIndLogConsole = 'No',
            pIndOutputResults = 'No',
        )

        # Extract the objective values if the model was solved successfully
        print(f"*✅ Model {case_name} solved successfully.")

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

        # read csv "oT_Result_NetworkSRMC_{case_name}.csv"
        pri_file = scenario_dir / f'oT_Result_NetworkSRMC_{case_name}.csv'
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
        print(f"*❌ Error running openTEPES for {case_name}: {e}")

    # cleanup scenario directory
    try:
        shutil.rmtree(scenario_dir)
    except Exception as e:
        print(f"Error cleaning up scenario directory {scenario_dir}: {e}")

    print(f"Finished scenario: {f0}, factor: {f1}, load level: {f2}")

    return df_marginal_costs

# ─── Main parallel driver ───────────────────────────────────────────────────────

if __name__ == '__main__':
    t0 = time.time()
    # tasks = list(product(factor_0, factor_1, factor_2))
    tasks = new_iters

    all_results = []

    # ─── openTEPES run function ─────────────────────────────────────────────────
    pIndLogConsole = 'No'
    pIndOutputResults = 'No'
    idx = oT._initialize_indices()
    pOut, pLog = idx[pIndOutputResults], idx[pIndLogConsole]

    model_name = (
        'Open Generation, Storage, and Transmission Operation and Expansion Planning Model '
        'with RES and ESS (openTEPES) - Version 4.18.6 - July 22, 2025'
    )
    model = oT._build_model(model_name)
    with open(os.path.join(source_dir, f'openTEPES_version_{base_folder_name}.log'), 'w') as logf:
        print(model_name, file=logf)
    oT._reading_data(base_dir, base_folder_name, model, pLog)
    print(f"Model {model_name} initialized.")

    # with ProcessPoolExecutor(max_workers=num_workers) as executor:
    # with ProcessPoolExecutor() as executor:
    #     for df_part in executor.map(run_scenario, tasks):
    #         if not df_part.empty:
    #             all_results.append(df_part)

    with ThreadPoolExecutor(max_workers=num_workers) as exec:
        futures = {exec.submit(run_scenario, t): t for t in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                df_res = fut.result()
                all_results.append(df_res)
            except Exception as e:
                print(f"[Error] {futures[fut]}: {e}")
            if i % 100 == 0 or i == len(tasks):
                print(f"Completed {i}/{len(tasks)}")


    all_df = pd.concat(all_results, ignore_index=True)
    # append to master CSV
    master_csv = base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.csv'
    if master_csv.exists():
        existing = pd.read_csv(master_csv)
        combined = pd.concat([existing, all_df], ignore_index=True)
        combined.drop_duplicates(inplace=True)
        final_df = combined
    else:
        final_df = all_df

    # save
    final_df.to_csv(master_csv, index=False)
    final_df.to_parquet(
        base_dir / parent_folder_name / f'oT_Dataset_sensitivities_{target_folder_name}.parquet',
        index=False
    )

    # check if all tasks were completed, compute unique combinations in all_df
    unique_combinations = set(zip(all_df['BiddingZoneFrom'], all_df['BiddingZoneTo'], all_df['Factor'], all_df['LoadLevel']))
    total_combinations = set(tasks)
    total_tasks = len(total_combinations) + len(existing_combos)
    completed_tasks = len(unique_combinations)
    print(f"Percentage of completed tasks: {completed_tasks / total_tasks * 100:.2f}%")
    print(f"Finished in {time.time()-t0:.1f}s")
