#!/usr/bin/python3

import os
import sys
import shutil

sys.dont_write_bytecode = True

sys.stdout.write(os.path.abspath(shutil.which(sys.argv[1])))
