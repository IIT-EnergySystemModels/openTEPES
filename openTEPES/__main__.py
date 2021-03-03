"""openTEPES - Transmission expansion planning model"""

import argparse
import os
import openTEPES

parser = argparse.ArgumentParser(description='Load initial parameters.')
parser.add_argument('--casename', dest='param1')
parser.add_argument('--dirname', dest='param2')
parser.add_argument('--solver', dest='param3')

args = parser.parse_args()

if __name__ == "__main__":
    _case_ = os.path.join(args.param2, args.param1)
    openTEPES.routine(_case_, args.param3)
