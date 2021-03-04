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
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="openTEPES",
    version="2.0.16",
    description="Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES)",
    scripts=["scripts/openTEPES_run.py"],
    author_email="andres.ramos@comillas.edu",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IIT-EnergySystemModels/openTEPES",
    install_requires=install_requires,
    extras_require={
        'interactive': ['glpk', 'cartopy'], },
    packages=["openTEPES"],
    include_package_data=True,
    package_data={'': ['openTEPES/9n/*.csv']},
)
