#!/usr/bin/python3

import os
import sys

command = ' '.join([str(arg) for arg in sys.argv[1:]])
os.system(command)
