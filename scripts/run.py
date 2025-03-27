#!/usr/bin/python3

import os
import sys

sys.dont_write_bytecode = True

os.system(' '.join([str(arg) for arg in sys.argv[1:]]))
