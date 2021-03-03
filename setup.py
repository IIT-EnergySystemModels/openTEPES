from setuptools import setup, find_packages
#
# def local_scheme(version):
#     return ""
#
#
# setup(use_scm_version={"local_scheme": local_scheme})

install_requires = [
    "matplotlib>=3.2.1",
    "numpy>=1.18.2",
    "pandas>=1.0.3",
    "pyomo",
    "psutil",
]

setup(
    name="openTEPES",
    version="2.0.12",
    description="Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)",
    scripts=["scripts/openTEPES_run.py"],
    author_email="andres.ramos@comillas.edu",
    url="https://github.com/IIT-EnergySystemModels/openTEPES",
    install_requires=install_requires,
    extras_require={
        'interactive': ['glpk', 'cartopy'], },
    packages=["openTEPES"],
)
