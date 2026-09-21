"""Every marginal price the economic results read has to be read under a guard.

`EconomicResults` writes a table of revenues from the duals of the operating reserve, ramp reserve
and adequacy constraints. A case that ends with no duals reaches that code all the same: the AC
restoration pass re-solves the network at the exact equations on a non-linear solver, which returns
no duals, and a mixed-integer case that is never re-solved as a linear problem has none either. The
module already computes `pHasDuals` for that reason, and each block is written to fall back to zero
revenue when it is false.

The guard is easy to lose, and losing it is silent until a case without duals is solved: a
re-indentation dropped it from five blocks and `KeyError` on `eOperReserveUp_2030_sc01_st1(...)` was
the first anyone heard of it. Reading the source is what catches that, so this check reads the
source: every subscript of `pDuals` must sit inside a condition that tests `pHasDuals`.
"""
import ast
import os

import pytest

MODULE = os.path.join(os.path.dirname(__file__), "..", "openTEPES", "openTEPES_OutputResultsEconomic.py")


def _tests_the_duals_are_there(node):
    """True when this condition names `pHasDuals` anywhere inside it."""
    return any(isinstance(n, ast.Name) and n.id == "pHasDuals" for n in ast.walk(node))


def _unguarded_dual_reads(path):
    """Every line reading `pDuals[...]` with no enclosing condition on `pHasDuals`."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        if not (isinstance(value, ast.Attribute) and value.attr == "pDuals"):
            continue

        guarded, walker = False, node
        while (walker := getattr(walker, "parent", None)) is not None:
            if isinstance(walker, ast.If) and _tests_the_duals_are_there(walker.test):
                guarded = True
                break
        if not guarded:
            yield node.lineno


@pytest.mark.parametrize("path", [MODULE])
def test_no_dual_is_read_without_the_guard(path):
    pLines = sorted(_unguarded_dual_reads(path))
    assert not pLines, (
        "these lines read a dual with no enclosing `pHasDuals` condition, so a case that ends with no "
        f"duals raises KeyError instead of writing zero revenue: {pLines}")
