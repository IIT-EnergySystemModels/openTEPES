# 9n as a DuckDB input case

This folder holds `9n.duckdb`: the bundled `9n` case stored as a DuckDB input file instead of CSV folders. It is the
one `.duckdb` kept in the repository as a worked example, so the DuckDB input backend can be run out of the box.

## Run it

Point openTEPES at the `.duckdb` file (the case name inside it is `9n`):

```python
from openTEPES.openTEPES import openTEPES_run
openTEPES_run("openTEPES/cases/9n_duckdb", "9n.duckdb", SolverName="glpk")
```

Reading a `.duckdb` input needs the `duckdb` package (`pip install duckdb`). The results are identical to running the
CSV `9n` case — the DuckDB file is just a different container for the same inputs.

## How it was made

`9n.duckdb` is generated from the CSV case with the converter tool:

```bash
python scripts/openTEPES_DuckDB/Tool_CSV_to_DuckDB.py openTEPES/cases/9n --db openTEPES/cases/9n_duckdb/9n.duckdb
```

The reverse tool exports a `.duckdb` back to CSV:

```bash
python scripts/openTEPES_DuckDB/Tool_DuckDB_to_CSV.py openTEPES/cases/9n_duckdb/9n.duckdb --out openTEPES/cases/9n_from_db
```

## Note

Every other `.duckdb` is git-ignored, because a DuckDB case is a generated artefact — the CSV folders are the
versioned source. This one file is a deliberate exception (see the `.gitignore` entry) purely to ship a ready-to-run
example. Do not add more `.duckdb` files to the repository; generate them from CSV with the converter instead.
