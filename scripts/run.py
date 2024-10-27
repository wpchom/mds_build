#!/usr/bin/python3

import sys
import subprocess

subprocess.run(' '.join([str(arg) for arg in sys.argv[1:]]), shell=True)
