---
openTEPES documentation master file, created by Andres Ramos
---

# Parameter Sweeps

Many studies run the same model over many related cases — scenario ensembles, demand or fuel-cost sweeps, Monte-Carlo samples. **openTEPES** offers three modes for this, trading set-up cost for reuse, all driven by one orchestrator (`openTEPES_Runner.run`). A single-case sweep reproduces a direct `openTEPES_run`.

| Mode | What each worker repeats | Cost per case | When to use |
| ---- | ------------------------ | ------------- | ----------- |
| A — pre-build | read input + build + solve | full | cases that differ structurally, each in its own folder |
| B — in-memory overlay | build + solve (input read once) | build + solve | one baseline perturbed by a scale factor or a table patch |
| C — post-build hot-swap | solve only (built once) | solve | one built model re-solved over a range of parameter values |

## Mode A — pre-build sweep

Each case reads its own input source, builds its own model, solves, and writes its own results. It is the most general mode: the cases may differ in any way, since nothing is shared between them.

A `Case` names one input source (a CSV case directory **or** a `.duckdb` file) plus an optional output directory and label. Cases that share the same `(dir_name, case_name)` need distinct `out_path` values so their result writers do not collide.

```python
from openTEPES import openTEPES_Cases, openTEPES_Runner

cases = [
    openTEPES_Cases.Case("cases", "SE2035_low"),
    openTEPES_Cases.Case("cases", "SE2035_ref"),
    openTEPES_Cases.Case("cases", "SE2035_high"),
]

summary = openTEPES_Runner.run(cases, solver_name="gurobi",
                               mode="pre-build", backend="multiprocessing", n_workers=8)
```

`run` returns one summary dict per case, in input order; a case that raises is reported as `status="error"` rather than aborting the sweep. The `backend` is `"serial"` (default), `"multiprocessing"`, or `"joblib"`.

## Mode B — in-memory overlay

When every case starts from one baseline, reading the input for each is wasteful. In Mode B the baseline is read once into RAM (an `InMemorySource`) and each case re-uses it through an **overlay** before rebuilding. An overlay maps a data-table stem (e.g. `"Demand"`) to one of:

- a **scale factor** — multiply the whole table (`{"Demand": 1.05}`);
- a **`df -> df` callable** — an arbitrary transform of the table;
- a **replacement DataFrame** — swap the table outright.

```python
openTEPES_Runner.run(
    [openTEPES_Cases.Case("cases", "SE2035_base", out_path="out/d105", overlay={"Demand": 1.05}),
     openTEPES_Cases.Case("cases", "SE2035_base", out_path="out/d110", overlay={"Demand": 1.10})],
    solver_name="gurobi", mode="in-memory", backend="multiprocessing", n_workers=8)
```

The input is read once; each worker only rebuilds and solves. An identity overlay reproduces a direct run.

## Mode C — post-build hot-swap

The cheapest mode reuses a single built model — the slowest step on large cases — and only re-solves it, once per overlay. It is driven directly by `openTEPES_ProblemSolvingResolve.resolve`, not through `openTEPES_Runner`.

```python
from openTEPES.openTEPES_ProblemSolvingResolve import resolve, overlay_scaled

# OptModel is an already-built model (from openTEPES_run's build step)
results = resolve(OptModel, "gurobi",
                  overlays=[overlay_scaled(OptModel, "pDemandElec", 1.05),
                            overlay_scaled(OptModel, "pDemandElec", 1.10)])
```

Each overlay applies relative to the baseline, which is restored at the end. Only `mutable=True` Params hot-swap, so Mode C sweeps the operational set only — `pDemandElec`, `pENSCost`, `pLinearVarCost`, `pEFOR`, `pReserveMargin`, `pRESEnergy` — while structural and topology Params stay fixed; `overlay_scaled` builds a scale-factor overlay for one of them. Unix only (uses `fork`); Modes A and B cover all platforms.

## Collecting sweep results

`openTEPES_ResultAggregate.aggregate` stacks a sweep's cases into one long table per result, with a leading `case` column, reading either the per-case DuckDB files or the per-case CSV folders:

```python
from openTEPES.openTEPES_ResultAggregate import aggregate

aggregate(sources=["out/d105", "out/d110"], out_path="out/sweep", to="duckdb")
```

`openTEPES_Runner.run` can do this in one step with `aggregate_to=...`. Per-case DuckDB output keeps a sweep single-writer-safe (one database per case). See {doc}`OutputResults` for the `output_format` option that writes those per-case DuckDB files.
