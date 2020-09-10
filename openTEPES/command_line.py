# -*- coding: utf-8 -*-

"""

command_line.py

command line parsing

"""

# external imports
import argparse

# internal imports
from organizacion.aplicacion import __version__


def run():
    """ main program """
    import openTEPES
    print(f'Ejemplo para Erik {__version__}')
    print()

    # # create the top-level parser and sub-parsers
    # parser = argparse.ArgumentParser(
    #     prog='prueba_alex',
    #     description='programa de prueba',
    #     epilog='Now it is your turn...\n')
    #
    # # top-level: --db
    # parser.add_argument(
    #     '--param', action='store',
    #     required=False, dest='parameter', default=None,
    #     help='parameter')
    #
    #
    # # parse argument list and call proper function
    # args = parser.parse_args()
    #
    #
    # print('PON AQUI TU CODIGO')
    #
    # # done
    # print(f'Program exits OK.')
