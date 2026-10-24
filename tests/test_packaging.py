import tomllib
from pathlib import Path


def test_core_dependencies_exclude_ausankey():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as fh:
        project = tomllib.load(fh)["project"]

    assert all(not dependency.startswith("ausankey") for dependency in project["dependencies"])
