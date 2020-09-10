# -*- coding: utf-8 -*-

"""
setup.py

Packaging stuff.

"""

from setuptools import find_packages, setup

from organizacion.aplicacion import __version__

setup(name='prueba_alex',
      author='Alejandro Rodriguez Gallego',
      author_email='argallego@comillas.edu',
      description='Ejemplo para Erik',
      entry_points={'console_scripts': ['prueba_alex=organizacion.aplicacion:run']},
      install_requires=[
          'pandas>=0.25',
          'numpy>=1.18',
          ],
      keywords='research prueba alex',
      license='private',
      long_description='Ejemplo para Erik',
      package_data={
          # any file in the resource package
          'organizacion.aplicacion.recursos': ['*']},
      packages=find_packages(),
      python_requires='>=3.8',
      url='https://alexrg.eu',
      version=__version__,
      zip_safe=False)
