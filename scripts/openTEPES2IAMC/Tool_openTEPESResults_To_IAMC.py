"""Convert openTEPES result CSV files into IAMC-format CSV files.

The script expects this folder layout:

1. This script plus IAMC variable-definition files in the same directory.
2. One subfolder per case (e.g. ``WAPP``) containing
   ``oT_Result_<ResultName>_<CaseName>.csv`` files.

Configuration is done at the top-level constants:

- ``Model`` and ``Version`` define the IAMC ``model`` field.
- ``CaseName`` selects the case subfolder to process.
- ``ResultFiles`` defines how each openTEPES result is read.
- ``ResultDefinitions`` maps each result to the IAMC variable/unit metadata.

For each available result file, one IAMC CSV is written as:
``oT_IAMC_<ResultName>_<Model> <Version>_<CaseName>.csv``.
Missing result files are reported and skipped.
"""

# Developed by

#    Andres Ramos, Erik Alvarez, Francisco Labora, Sara Lumbreras
#    Instituto de Investigacion Tecnologica
#    Escuela Tecnica Superior de Ingenieria - ICAI
#    UNIVERSIDAD PONTIFICIA COMILLAS
#    Alberto Aguilera 23
#    28015 Madrid, Spain
#    Andres.Ramos@comillas.edu
#    Erik.Alvarez@comillas.edu
#    Francisco.Labora@comillas.edu
#    Sara.Lumbreras@comillas.edu
#    https://pascua.iit.comillas.edu/aramos/Ramos_CV.htm

from pathlib import Path

import pandas as pd

# Model and version these results correspond to (used for the IAMC "Model" field, e.g. "openTEPES 4.18.17").
Model = "openTEPES"
Version = "4.18.17"
ModelVersion = f"{Model} {Version}"

# Name of the case whose results are going to be converted to the IAMC format.
CaseName = "WAPP"

DataDir = Path(__file__).resolve().parent  # Folder that contains the CSV files (same folder as this script).
CaseDir = DataDir / CaseName               # Folder that holds the openTEPES results for the selected case (one folder per case, inside this script's directory).

# Mapping of a short key to each IAMC variable-definition CSV file name.
Files = {
    "generation":   "oT_IAMC_var_OD_PowerGeneration.csv",
    "system":       "oT_IAMC_var_OD_PowerSystem.csv",
    "transmission": "oT_IAMC_var_OD_PowerTransmission.csv",
}

# openTEPES result files to read for the selected case, with the header/index layout passed to pandas.read_csv.
# Network line-level results (flow/investment/losses) use a 3-level header (initial node/final node/circuit).
# Node/plant-level and other operational results use a single-level header.
ResultFiles = {
    "NetworkInvestmentPerUnit":       {"header": [0, 1, 2], "index_col": [0      ]},
    "NetworkFlowElecPerNode":         {"header": [0, 1, 2], "index_col": [0, 1, 2]},
    "NetworkLosses":                  {"header": [0, 1, 2], "index_col": [0, 1, 2]},
    "NetworkAngle":                   {"header": [0      ], "index_col": [0, 1, 2]},
    "NetworkPNS":                     {"header": [0      ], "index_col": [0, 1, 2]},
    "NetworkSRMC":                    {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationInvestment":           {"header": [0      ], "index_col": [0      ]},
    "GenerationCommitment":           {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationStartup":              {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationShutdown":             {"header": [0      ], "index_col": [0, 1, 2]},
    "Generation":                     {"header": [0      ], "index_col": [0, 1, 2]},
    "Consumption":                    {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationOperatingReserveUp":   {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationOperatingReserveDown": {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationInventory":            {"header": [0      ], "index_col": [0, 1, 2]},
    "GenerationSpillage":             {"header": [0      ], "index_col": [0, 1, 2]},
    "Demand":                         {"header": [0      ], "index_col": [0, 1, 2]},
}

# Additional openTEPES input files to convert to IAMC format.
# Demand has the same structure as operational results:
# index = Period, Scenario, LoadLevel and columns = nodes.
InputFiles = {
    "Demand": {
        "filename": f"oT_Data_Demand_{CaseName}.csv",
        "header": [0],
        "index_col": [0, 1, 2],
    },
    "Network": {
        "filename": f"oT_Data_Network_{CaseName}.csv",
    },
}

def ReadIAMCFiles() -> dict[str, pd.DataFrame]:
    """Load IAMC variable-definition CSV files as DataFrames.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary keyed by ``generation``, ``system``, and ``transmission``.
        Each table is indexed by the variable key (first CSV column) and
        contains at least ``Variable`` and ``Unit`` columns.

    Notes
    -----
    Files are decoded as cp1252 because they may include characters such as
    the euro sign. Index labels are stripped to avoid lookup failures caused
    by trailing whitespace.
    """
    DataFrames: dict[str, pd.DataFrame] = {}
    for Key, FileName in Files.items():
        df = pd.read_csv(DataDir / FileName, index_col=0, encoding="cp1252")
        df.index = df.index.str.strip()  # Strip stray whitespace from the index labels (e.g. "vENS ").
        DataFrames[Key] = df
    return DataFrames


def ReadCaseResults() -> dict[str, pd.DataFrame]:
    """Read the selected case's openTEPES result files.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary of loaded result tables keyed by result name.

    Notes
    -----
    File names follow ``oT_Result_<ResultName>_<CaseName>.csv``.
    Missing files are reported with a warning and skipped.
    """
    Results: dict[str, pd.DataFrame] = {}
    for Name, ReadOpts in ResultFiles.items():
        FilePath = CaseDir / f"oT_Result_{Name}_{CaseName}.csv"
        if not FilePath.is_file():
            print(f"WARNING: result file not found, skipping: {FilePath.name}")
            continue
        Results[Name] = pd.read_csv(FilePath, **ReadOpts)
    return Results

def ReadInputData() -> dict[str, pd.DataFrame]:
    """Read additional openTEPES input data files."""

    Inputs: dict[str, pd.DataFrame] = {}

    # Demand input (same structure as operational results)
    DemandFile = DataDir / CaseName / InputFiles["Demand"]["filename"]

    if DemandFile.is_file():
        Inputs["Demand"] = pd.read_csv(
            DemandFile,
            header=InputFiles["Demand"]["header"],
            index_col=InputFiles["Demand"]["index_col"],
        )
    else:
        print(f"WARNING: input file not found, skipping: {DemandFile.name}")

    # Network input
    NetworkFile = DataDir / CaseName / InputFiles["Network"]["filename"]

    if NetworkFile.is_file():
        Inputs["Network"] = pd.read_csv(NetworkFile)
    else:
        print(f"WARNING: input file not found, skipping: {NetworkFile.name}")

    return Inputs

# Definition row (variable name and unit) that each result maps to: (definition file key, row label in that file).
ResultDefinitions = {
    "NetworkInvestmentPerUnit":       ("transmission", "vNetworkInvest"),
    "NetworkFlowElecPerNode":         ("transmission", "vFlow"),
    "NetworkLosses":                  ("transmission", "vLineLosses"),
    "NetworkAngle":                   ("transmission", "vTheta"),
    "NetworkPNS":                     ("transmission", "vPNS"),
    "NetworkSRMC":                    ("transmission", "vSRMC"),
    "GenerationInvestment":           ("generation",   "vGenerationInvest"),
    "GenerationCommitment":           ("generation",   "vCommitment"),
    "GenerationStartup":              ("generation",   "vStartUp"),
    "GenerationShutdown":             ("generation",   "vShutDown"),
    "Generation":                     ("generation",   "vTotalOutput"),
    "Consumption":                    ("generation",   "vESSCharge"),
    "GenerationOperatingReserveUp":   ("generation",   "vReserveUp"),
    "GenerationOperatingReserveDown": ("generation",   "vReserveDown"),
    "GenerationInventory":            ("generation",   "vESSInventory"),
    "GenerationSpillage":             ("generation",   "vESSSpillage"),
    "Demand":                         ("system",       "Demand"),
}

# Additional openTEPES input files to convert to IAMC format.
# Demand has the same structure as operational results:
# index = Period, Scenario, LoadLevel and columns = nodes.
InputFiles = {
    "Demand": {
        "filename": f"oT_Data_Demand_{CaseName}.csv",
        "header": [0],
        "index_col": [0, 1, 2],
    },
    "Network": {
        "filename": f"oT_Data_Network_{CaseName}.csv",
    },
}

def WriteResultToIAMC(ResultName: str, df: pd.DataFrame, IAMCVars: dict[str, pd.DataFrame], OutputPath: Path | None = None) -> pd.DataFrame:
    """Convert one openTEPES result table to IAMC wide format and write it.

    Parameters
    ----------
    ResultName : str
        Result key defined in ``ResultFiles`` and ``ResultDefinitions``.
    df : pd.DataFrame
        Result table as read from the corresponding openTEPES CSV.
    IAMCVars : dict[str, pd.DataFrame]
        IAMC variable-definition tables loaded by :func:`ReadIAMCFiles`.
    OutputPath : Path | None, optional
        Destination file path. If omitted, a default output name is used.

    Returns
    -------
    pd.DataFrame
        IAMC table in wide format with identifier columns
        (model/scenario/region/variable/unit/subannual) and one column
        per period.

    Notes
    -----
    - Region uses ``InitialNode|FinalNode|Circuit`` for 3-level columns, or
      the node/plant name for single-level columns.
    - Scenario uses ``<CaseName>|<Scenario>`` when available, otherwise
      ``<CaseName>``.
    - Subannual uses ``LoadLevel`` when present, otherwise empty.
    - Variable and unit are taken from ``ResultDefinitions`` + IAMC metadata.
    """
    df = df.copy()
    DefinitionFile, DefinitionRow = ResultDefinitions[ResultName]
    VariableName = IAMCVars[DefinitionFile].loc[DefinitionRow, "Variable"]
    UnitName = IAMCVars[DefinitionFile].loc[DefinitionRow, "Unit"]
    VariableName = "" if pd.isna(VariableName) else VariableName  # Keep an empty definition (e.g. PNS) as an empty string.

    # Name the column levels so the melt produces readable field names: 3 levels -> transmission line, 1 level -> node.
    if df.columns.nlevels == 3:
        df.columns.names = ["InitialNode", "FinalNode", "Circuit"]
    else:
        df.columns.name = "Node"

    # Name the index levels: results are indexed either by (Period, Scenario, LoadLevel) or by Period only (e.g. investment).
    df.index.names = ["Period", "Scenario", "LoadLevel"] if df.index.nlevels == 3 else ["Period"]

    # Melt the wide table into long format (one row per node/line and, when present, time step).
    Long = df.stack(list(df.columns.names), future_stack=True).rename("Value").reset_index()

    # Region: "initial|final|circuit" for lines, or the plain node name for per-node results.
    Region = Long["InitialNode"] + "|" + Long["Circuit"] + ">" + Long["FinalNode"] + "|" + Long["Circuit"] if "InitialNode" in Long.columns else Long["Node"]
    # Scenario: prefix the case name; results without a Scenario level (e.g. investment) carry just the case name.
    Scenario = CaseName + "|" + Long["Scenario"] if "Scenario" in Long.columns else CaseName
    # Subannual: the LoadLevel time step when available, otherwise empty (e.g. investment has no time step).
    Subannual = Long["LoadLevel"] if "LoadLevel" in Long.columns else ""

    IAMC = pd.DataFrame({
        "model":     ModelVersion,
        "scenario":  Scenario,
        "region":    Region,
        "variable":  VariableName,
        "unit":      UnitName,
        "subannual": Subannual,
        "Period":    Long["Period"],
        "value":     Long["Value"],
    })

    # Pivot the Period out to columns so the value sits under a column headed by the period (year), following the IAMC wide format.
    IdColumns = ["model", "scenario", "region", "variable", "unit", "subannual"]
    IAMC = IAMC.pivot(index=IdColumns, columns="Period", values="value").reset_index()
    IAMC.columns.name = None

    if OutputPath is None:
        OutputPath = DataDir / f"oT_IAMC_{ResultName}_{ModelVersion}_{CaseName}.csv"
    IAMC.to_csv(OutputPath, index=False)
    print(f"Written {len(IAMC)} rows to {OutputPath.name}")
    return IAMC


def WriteNetworkParameterToIAMC(
    ParameterName: str,
    ColumnName: str,
    df: pd.DataFrame,
    IAMCVars: dict[str, pd.DataFrame],
    Period: int,
    OutputPath: Path | None = None,
) -> pd.DataFrame:
    """Convert transmission network parameters from oT_Data_Network to IAMC."""

    DefinitionFile = "transmission"

    VariableName = IAMCVars[DefinitionFile].loc[
        ParameterName, "Variable"
    ]

    UnitName = IAMCVars[DefinitionFile].loc[
        ParameterName, "Unit"
    ]

    IAMC = pd.DataFrame({
        "model": ModelVersion,
        "scenario": CaseName,
        "region": (
            df["InitialNode"]
            + "|"
            + df["Circuit"]
            + ">"
            + df["FinalNode"]
            + "|"
            + df["Circuit"]
        ),
        "variable": VariableName,
        "unit": UnitName,
        "subannual": "",
        "Period": Period,
        "value": df[ColumnName],
    })

    IAMC = IAMC.pivot(
        index=[
            "model",
            "scenario",
            "region",
            "variable",
            "unit",
            "subannual",
        ],
        columns="Period",
        values="value",
    ).reset_index()

    IAMC.columns.name = None

    if OutputPath is None:
        OutputPath = (
            DataDir /
            f"oT_IAMC_{ParameterName}_{ModelVersion}_{CaseName}.csv"
        )

    IAMC.to_csv(OutputPath, index=False)

    print(
        f"Written {len(IAMC)} rows to {OutputPath.name}"
    )

    return IAMC

if __name__ == "__main__":

    IAMCVars = ReadIAMCFiles()

    # Existing result conversion
    Results = ReadCaseResults()

    for Name, df in Results.items():
        IAMC = WriteResultToIAMC(Name, df, IAMCVars)
        print(IAMC.head(3).to_string(index=False))


    # New input-data conversion
    Inputs = ReadInputData()


    # Demand conversion
    if "Demand" in Inputs:
        IAMC = WriteResultToIAMC(
            "Demand",
            Inputs["Demand"],
            IAMCVars,
        )

        print(IAMC.head(3).to_string(index=False))


    # Network parameters conversion
    if "Network" in Inputs:

        Network = Inputs["Network"]

        for ParameterName, ColumnName in [
            ("TTC", "TTC"),
            ("Length", "Length"),
            ("FixedInvestmentCost", "FixedInvestmentCost"),
        ]:

            IAMC = WriteNetworkParameterToIAMC(
                ParameterName,
                ColumnName,
                Network,
                IAMCVars,
                Period=Inputs["Demand"].index.get_level_values("Period")[0],
            )

            print(IAMC.head(3).to_string(index=False))