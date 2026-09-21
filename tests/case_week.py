"""Shared helpers for tests that solve a bundled case over one representative week.

Several test modules need the same thing: a private copy of a shipped case, cut down to a week so it
solves in seconds, with a column or a file changed to switch on the feature under test. Each module
used to carry its own copy of that code. ``week_of_case`` is that code, written once.

A private copy is used rather than an in-place edit with a restore step, because a run that dies on a
timeout or a Ctrl-C never reaches the restore and leaves the shipped case truncated on disk.
"""
import os
import shutil

import numpy as np
import pandas as pd

CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openTEPES", "cases"))


def week_of_case(case_name, dest_root):
    """Copy a shipped case under ``dest_root`` and cut it to its first 168 hours.

    Duration is truncated to one week, the stage weight is set to 52 so that week still stands for a
    year, and the two annual limits are blanked -- the RES-energy requirement and the CO2 cap -- exactly as
    the 7-day fixtures in ``test_run.py`` do. Returns ``(case_dir, run_kwargs)``; the caller may edit any file in
    ``case_dir`` before passing ``run_kwargs`` to ``openTEPES_run``.

    Single-stage cases only. A case with several stages needs the per-stage truncation in
    ``test_run.py``, because a flat cut zeroes stages 2..N and crashes at ``pStorageTimeStep``.
    """
    dest_root = str(dest_root)
    case_dir = os.path.join(dest_root, case_name)
    shutil.copytree(os.path.join(CASES_DIR, case_name), case_dir,
                    ignore=shutil.ignore_patterns("openTEPES_*", "oT_Result_*", "oT_Plot_*", "*.html"))

    duration_csv = os.path.join(case_dir, f"oT_Data_Duration_{case_name}.csv")
    df = pd.read_csv(duration_csv, index_col=[0, 1, 2])
    df.iloc[168:, df.columns.get_loc("Duration")] = np.nan
    df.to_csv(duration_csv)

    res_energy_csv = os.path.join(case_dir, f"oT_Data_RESEnergy_{case_name}.csv")
    df = pd.read_csv(res_energy_csv, index_col=[0, 1])
    df["RESEnergy"] = df["RESEnergy"].astype(float)
    df["RESEnergy"] = np.nan
    df.to_csv(res_energy_csv)

    # The annual CO2 cap goes the same way, and for the same reason: a year of emissions held against one
    # week is decided by which week is chosen. sSEP is the only bundled case that sets one.
    emission_csv = os.path.join(case_dir, f"oT_Data_Emission_{case_name}.csv")
    df = pd.read_csv(emission_csv, index_col=[0, 1])
    df["CO2Emission"] = df["CO2Emission"].astype(float)
    df["CO2Emission"] = np.nan
    df.to_csv(emission_csv)

    stage_csv = os.path.join(case_dir, f"oT_Data_Stage_{case_name}.csv")
    df = pd.read_csv(stage_csv, index_col=[0])
    df.iloc[:, df.columns.get_loc("Weight")] = 52
    df.to_csv(stage_csv)

    run_kwargs = dict(DirName=dest_root, CaseName=case_name, SolverName="highs",
                      pIndLogConsole=0, pIndOutputResults=0)
    return case_dir, run_kwargs


def rows_of(mTEPES, prefix):
    """Count the rows of every constraint whose name starts with ``prefix``.

    The model names its constraints per period, scenario and stage, so a feature's constraint is a
    family such as ``eChargeOutflows_2030_sc01_st1`` rather than a single block.
    """
    import pyomo.environ as pyo

    return sum(len(c) for c in mTEPES.component_objects(pyo.Constraint) if c.name.startswith(prefix))
