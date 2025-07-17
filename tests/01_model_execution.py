from openTEPES.openTEPES import openTEPES_run
from pathlib import Path

import pandas as pd
import shutil

# Mapping of export capacity factors to labels
dict_factor_1 = {
    0.05: '5%', 0.1: '10%', 0.15: '15%', 0.2: '20%', 0.25: '25%',
    0.3: '30%', 0.35: '35%', 0.4: '40%', 0.45: '45%',
    0.5: '50%', 0.55: '55%', 0.6: '60%', 0.65: '65%', 0.7: '70%',
    0.75: '75%', 0.8: '80%', 0.85: '85%', 0.9: '90%', 0.95: '95%',
    1.0: '100%', 1.05: '105%', 1.1: '110%', 1.15: '115%', 1.2: '120%', 1.25: '125%',
    1.3: '130%', 1.35: '135%', 1.4: '140%', 1.45: '145%', 1.5: '150%',
    1.55: '155%', 1.6: '160%', 1.65: '165%', 1.7: '170%', 1.75: '175%',
    1.8: '180%', 1.85: '185%', 1.9: '190%', 1.95: '195%', 2.0: '200%',
}

# Factors and filenames
factor_1 = list(dict_factor_1.keys())  # export capacity multipliers

# Base directory setup
base_folder_name = "SE2025"
scenario_folder_name = "Scenarios_GridSecure"
base_dir = Path(r"C:\Users\erikal\OneDrive - RISE\Projects\P124390.AP05DP04.A2025_GridSecure\codes\cases")
source_dir = base_dir / base_folder_name

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
        pIndLogConsole='Yes',
        pIndOutputResults='Yes',
    )
    print("-Setting up test case...")  # Added print for console feedback
    return data

# executions for the scenarios
dict_obj = {}
dict_pri = {}
for factor in factor_1:
    folder_label = dict_factor_1[factor]
    case_name = f"{base_folder_name}_{folder_label}"
    print(f'-Running openTEPES for {case_name}...')
    try:
        case_data = setup_test_case(base_dir, scenario_folder_name, case_name)
        mTEPES = openTEPES_run(**case_data)
        print(f'--openTEPES run completed for {case_name} with factor {factor}')
        # extract the objective valus in a dictionary
        objective_values = mTEPES.vTotalSCost()
        dict_obj[factor] = objective_values
        # read csv "oT_Result_NetworkSRMC_{case_name}.csv"
        pri_file = base_dir / scenario_folder_name / case_name / f'oT_Result_NetworkSRMC_{case_name}.csv'
        if pri_file.exists():
            pri_df = pd.read_csv(pri_file, index_col=[0,1,2])
            # stack the columns
            pri_df = pri_df.stack().reset_index()
            pri_df.columns = ['Period', 'Scenario', 'LoadLevel', 'Node', 'Price']
            # set index to Period, Scenario, LoadLevel, Node
            pri_df.set_index(['Period', 'Scenario', 'LoadLevel', 'Node'], inplace=True)
            # store the total price in a dictionary
            dict_pri[factor] = pri_df
    except Exception as e:
        print(f"Error occurred while running openTEPES for {case_name}: {e}")
        raise
    print(f'--openTEPES run successful for {case_name} with factor {factor}')

print("All scenarios executed successfully.")
# make a plot using altair of the objective values
import altair as alt
# Convert the dictionary to a DataFrame
df_obj = pd.DataFrame(data=dict_obj.values(), index=dict_obj.keys()).reset_index()
df_obj.columns = ['Factor', 'Objective Value']
# Create an Altair chart with automatic y-axis scaling
min_val = df_obj['Objective Value'].min() - 0.1
max_val = df_obj['Objective Value'].max() + 0.1

chart = alt.Chart(df_obj).mark_circle(size=60).encode(
    x=alt.X('Factor:O', title='Export Capacity Factor', sort=None),
    y=alt.Y('Objective Value:Q', title='Objective Value', scale=alt.Scale(domain=[min_val, max_val])),
    color=alt.Color('Factor:O', legend=None).scale(scheme="magma", reverse=True),
    tooltip=['Factor', 'Objective Value']
).properties(
    title='Objective Values for Different Export Capacity Factors',
    width=400,
    height=400
)
# increase the font size of the axes and title
chart = chart.configure_axis(
    labelFontSize=12,
    titleFontSize=14,
).configure_title(
    fontSize=16
).configure_legend(
    labelFontSize=12,
    titleFontSize=14
)


# Save the chart as an HTML file
output_path = base_dir / scenario_folder_name / "objective_values_chart.html"
chart.save(output_path)
print(f"✅ Chart saved to: {output_path}")

# concatenate the price dataframes
df_pri = pd.concat(dict_pri.values(), keys=dict_pri.keys()).reset_index()
# rename the columns
df_pri.rename(columns={'level_0': 'Factor'}, inplace=True)
# select the Node "SE1", "SE2", "SE3", "SE4" from the Node column
df_pri_SE = df_pri[df_pri['Node'].isin(['SE1', 'SE2', 'SE3', 'SE4'])]
# make a distribution plot of the prices for each factor, and color by Node
chart_pri = alt.Chart(df_pri_SE).mark_circle(size=60).encode(
    x=alt.X('Factor:O', title='Export Capacity Factor', sort=None),
    y=alt.Y('Price:Q', title='Price'),
    color=alt.Color('Node:N', legend=alt.Legend(title="Node")),
    tooltip=['Factor', 'Node', 'Price']
).properties(
    title='Prices for Different Export Capacity Factors and Nodes'
)
# increase the font size of the axes and title
chart_pri = chart_pri.configure_axis(
    labelFontSize=12,
    titleFontSize=14
).configure_title(
    fontSize=16
)

# Save the price chart as an HTML file
output_path_pri = base_dir / scenario_folder_name / "price_distribution_chart.html"
chart_pri.save(output_path_pri)
print(f"✅ Price distribution chart saved to: {output_path_pri}")

# select the Node "SE4" from the Node column
df_pri_SE4 = df_pri[df_pri['Node'] == 'SE4']
# make a line plot of the prices for each factor, and color by LoadLevel
chart_pri_SE4 = alt.Chart(df_pri_SE4).mark_circle(size=60).encode(
    x=alt.X('LoadLevel:O', title='Load Level', sort=None),
    y=alt.Y('Price:Q', title='Price'),
    color=alt.Color('Factor:N', legend=alt.Legend(title="Export Capacity Factor")).scale(scheme="category20", reverse=True),
    tooltip=['LoadLevel', 'Factor', 'Price']
).properties(
    title='Prices for SE4 Node Across Different Export Capacity Factors and Load Levels'
)
# increase the font size of the axes and title
chart = chart.configure_axis(
    labelFontSize=12,
    titleFontSize=14,
).configure_title(
    fontSize=16
).configure_legend(
    labelFontSize=12,
    titleFontSize=14
)
# Save the SE4 price chart as an HTML file
output_path_pri_SE4 = base_dir / scenario_folder_name / "price_SE4_chart.html"
chart_pri_SE4.save(output_path_pri_SE4)
print(f"✅ SE4 price chart saved to: {output_path_pri_SE4}")
