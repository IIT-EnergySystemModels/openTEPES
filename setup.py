from setuptools import setup
#
# def local_scheme(version):
#     return ""
#
#
# setup(use_scm_version={"local_scheme": local_scheme})

install_requires = [
    "PyYAML>=5.3.1",
    "colorama>=0.4.4",
    "gym>=0.17.1",
    "matplotlib>=3.2.1",
    "numpy>=1.18.2",
    "pandas>=1.0.3",
    "pyomo",
    "psutil",
    "glpk",
]

setup(
    name="openTEPES",
    version="2.0.6",
    description="Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)",
    scripts=glob.glob("openTEPES/openTEPES*.py"),
    author_email="andres.ramos@comillas.edu",
    url="https://github.com/IIT-EnergySystemModels/openTEPES",
    install_requires=install_requires,
    packages=["openTEPES"],
)
