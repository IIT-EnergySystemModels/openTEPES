"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 03, 2026

Raw parameter, variable, set, and constraint dump.

This module writes the full Pyomo model to a DuckDB file: every variable
with its bounds, every parameter value, every set's members, and every
indexed constraint's dual and bounds. It is the raw debugging dump used by
``OutputResultsParVarCon`` and is gated by ``pIndDumpRawResults`` in the run
driver, not by a CLI-selectable result category. The DuckDB-writing helpers
below have this dump as their only consumer, so they live here rather than in
the shared Common module.
"""

import time
import datetime
import os
import pandas            as     pd
import pyomo.environ     as     pyo
import duckdb

try:
    from .openTEPES_OutputResultsCommon import _outdir
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir


def _set_df(con, name: str, df: pd.DataFrame):
    """
    Insert a pandas DataFrame into an existing DuckDB table.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Open DuckDB connection.
    name : str
        Target table name.
    df : pandas.DataFrame
        DataFrame to insert into the target table.
    """
    con.cursor().execute(f"CREATE OR REPLACE TABLE '{name}' AS SELECT * FROM df;")


def _write_var_to_db(con, var, name):
    """
    Write a Pyomo Var's values and bounds to DuckDB.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Open DuckDB connection.
    var : pyomo.core.base.var.Var
        Pyomo variable (indexed or scalar).
    name : str
        Variable/table name to use in the database.
    """
    values = var.extract_values()
    s = pd.Series(values, index=values.keys())
    df = s.to_frame(name=name).reset_index()
    df = pd.concat(
        [
            df,
            pd.DataFrame([dict(upper_bound=var[index].ub, lower_bound=var[index].lb) for index in var]),
        ],
        axis=1,
    )
    _set_df(con, f'v_{name}', df)


def _write_param_to_db(con, param, name):
    """
    Write a Pyomo Param's values to DuckDB.

    Creates/inserts into a table named `{name}` with:
      - the Param index (via reset_index)
      - a column named `{name}` containing the Param value

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Open DuckDB connection.
    param : pyomo.core.base.param.Param
        Pyomo parameter (indexed or scalar).
    name : str
        Parameter/table name to use in the database.
    """
    values = param.extract_values()
    s = pd.Series(values, index=values.keys())
    df = s.to_frame(name=name).reset_index()
    _set_df(con, f'p_{name}', df)


def _write_set_to_db(con, set_, name):
    """
    Write a Pyomo Set's elements to DuckDB.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Open DuckDB connection.
    set_ : pyomo.core.base.set.Set
        Pyomo set.
    name : str
        Base name used to build the table name `s_{name}`.
    """
    from pyomo.common.sorting import sorted_robust

    if set_.is_indexed():
        rows = []
        for idx in sorted_robust(set_.keys()):
            for m in set_[idx].sorted_data():
                rows.append((idx, m))
        df = pd.DataFrame(rows, columns=["index", "member"])
    else:
        df = pd.DataFrame({"member": list(set_.sorted_data())})

    _set_df(con, f"s_{name}", df)


def _write_constraint_to_db(con, constraint, name, model):
    """
    Write an indexed Pyomo Constraint's duals and bounds to DuckDB.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Open DuckDB connection.
    constraint : pyomo.core.base.constraint.Constraint
        Pyomo constraint component (must be indexed; scalar constraints are skipped).
    name : str
        Constraint name used to build the table name `c_{name}`.
    model : pyomo.core.base.PyomoModel.ConcreteModel
        Model providing `pDuals` (mapping from constraint+index string to dual value).

    Notes
    -----
    Non-indexed constraints are ignored
    """
    if not constraint.is_indexed():
        return

    records = []
    for index in constraint:
        key = str(constraint.name) + str(index)
        records.append(
            dict(
                name=str(name),
                index=index,
                dual=model.pDuals.get(key),
                lower_bound=constraint[index].lb,
                upper_bound=constraint[index].ub,
            )
        )

    df = pd.DataFrame(records)
    _set_df(con, f'c_{name}', df.reset_index())


def write_model_to_db(model, filename):
    """
    Export Pyomo model components to a DuckDB database file.

    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
    filename : str
    """
    with duckdb.connect(filename) as con:
        model_vars = model.component_map(ctype=pyo.Var)
        for k in model_vars.keys():
            var = model_vars[k]
            name = var.getname()
            _write_var_to_db(con, var, name)

        model_params = model.component_map(ctype=pyo.Param)
        for k in model_params.keys():
            param = model_params[k]
            name = param.getname()
            _write_param_to_db(con, param, name)

        model_sets = model.component_map(ctype=pyo.Set)
        for k in model_sets.keys():
            s = model_sets[k]
            name = s.getname()
            _write_set_to_db(con, s, name)

        model_constraints = model.component_map(ctype=pyo.Constraint)
        for k in model_constraints.keys():
            constraint = model_constraints[k]
            name = k
            _write_constraint_to_db(con, constraint, name, model)


# write parameters, variables, and duals
# @profile
def OutputResultsParVarCon(DirName, CaseName, OptModel, mTEPES):
    # print('Writing pars, vars, and duals results  ... ', end='')
    # DirName = os.path.dirname(DirName)
    _path   = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # Load the model from the pickle file
    # dump_folder = f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/'
    # with open(dump_folder+f'/oT_Case_{CaseName}.pkl','rb') as f:
    #     OptModel = pickle.load(f)
    # output parameters, variables, and constraints

    # dump_folder = f'{_path}/CaseDumpFolder_{CaseName}_'+str(datetime.datetime.now().strftime('%Y%m%d'))+f'/'
    dump_folder = os.path.join(DirName, CaseName, f'CaseDumpFolder_{CaseName}_'+str(datetime.datetime.now().strftime('%Y%m%d')))
    if not os.path.exists(dump_folder):
        os.makedirs(dump_folder)
    DateName = str(datetime.datetime.now().strftime('%Y%m%d'))

    write_model_to_db(OptModel, f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}.duckdb')

    # Extract and write parameters from the case
    # with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Parameters.csv', 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(['Name', 'Index', 'Value'])
    #     for par in OptModel.component_objects(pyo.Param):
    #         par_object = getattr(OptModel, str(par))
    #         if par_object.is_indexed():
    #             for index in par_object:
    #                 if (isinstance(index, tuple) and par_object.mutable == False) or par_object.mutable == False:
    #                     writer.writerow([str(par), index, par_object[index]])
    #                 else:
    #                     writer.writerow([str(par), index, par_object[index].value])
    #         else:
    #             writer.writerow        ([str(par), 'NA',  par_object.value])
    #
    # # Extract and write variables
    # with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Variables.csv', 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(['Name', 'Index', 'Value', 'Lower Bound', 'Upper Bound'])
    #     for var in OptModel.component_objects(pyo.Var, active=True):
    #         var_object = getattr(OptModel, str(var))
    #         for index in var_object:
    #             writer.writerow([str(var), index, var_object[index].value, str(var_object[index].lb), str(var_object[index].ub)])
    #
    # # Extract and write dual variables
    # with open(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_Constraints.csv', 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(['Name', 'Index', 'Value', 'Lower Bound', 'Upper Bound'])
    #     for con in OptModel.component_objects(pyo.Constraint, active=True):
    #         con_object = getattr(OptModel, str(con))
    #         if con.is_indexed():
    #             for index in con_object:
    #                 writer.writerow([str(con), index, mTEPES.pDuals[str(con_object.name)+str(index)], str(con_object[index].lb), str(con_object[index].ub)])
    #                 # writer.writerow([str(con), index, OptModel.dual[con_object[index]], str(con_object[index].lb), str(con_object[index].ub)])

    # NameList = ['Parameters', 'Variables', 'Constraints']
    #
    # df  = {}
    # lst = {}
    # for name in NameList:
    #     df[f'{name}'] = pd.read_csv(f'{_path}/CaseDumpFolder_{CaseName}_{DateName}/oT_Case_{CaseName}_{name}.csv', index_col=[0,1])
    #     # df[f'{name}'].replace('inf',  '')
    #     # df[f'{name}'].replace('None', '')
    #     lst[f'{name}List'] = df[f'{name}'].index.get_level_values(0).unique().tolist()
    #
    # par = {}
    # for pn in NameList:
    #     for name in lst[f'{pn}List']:
    #         par[f'{name}'] = df[f'{pn}'].loc[f'{name}']
    #         if len(par[f'{name}'].index) > 1:
    #             contains_tuples = any('('   in i and ')' in i for i in par[f'{name}'].index)
    #             if contains_tuples:
    #                 # print(par[f'{name}'].index)
    #                 par[f'{name}'].index = pd.MultiIndex.from_tuples(par[f'{name}'].index.map(ast.literal_eval))

    WritingResultsTime = time.time() - StartTime
    StartTime          = time.time()
    print('Writing pars, vars, and duals results  ... ', round(WritingResultsTime), 's')
