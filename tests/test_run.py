import argparse
import os
from openTEPES.openTEPES import openTEPES_run
import openTEPES
CASE = "9n"
parser = argparse.ArgumentParser(description='Introducing main parameters.')
parser.add_argument('--case', type=str, default=None)
parser.add_argument('--dir', type=str, default=None)
parser.add_argument('--solver', type=str, default=None)

DIR = os.path.dirname(openTEPES.__file__)
SOLVER = "glpk"


def main():
    args = parser.parse_args()
    if args.dir is None:
        args.dir = input("Input Dir Name (Default {}): ".format(DIR))
        if args.dir == "":
            args.dir = DIR
    if args.case is None:
        args.case = input("Input Case Name (Default {}): ".format(CASE))
        if args.case == "":
            args.case = CASE
    if args.solver is None:
        args.solver = input("Input Solver Name (Default {}): ".format(SOLVER))
        if args.solver == "":
            args.solver = SOLVER
    print(args.case)
    print(args.dir)
    print(args.solver)
    import sys
    print(sys.argv)
    print(args)
    openTEPES_run(args.dir, args.case, args.solver)
    sys.exit("Running Process Finished...")


if __name__ == "__main__":
    main()
