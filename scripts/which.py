#!/usr/bin/python3

import os
import sys
import shutil

sys.stdout.write(os.path.abspath(shutil.which(sys.argv[1])))
