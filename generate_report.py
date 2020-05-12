# !/home/tools/continuum/Anaconda3-5.0.0.1/bin/python3
# !/usr/bin/python

# Import the required libs
import load_def_region_files

def generate_report(retime_timing_rep):

    #load("/home/junw/py/load_def_region_files.py")
    
    load_def_region_files.load_def_region_files()
    print(retime_timing_rep)
