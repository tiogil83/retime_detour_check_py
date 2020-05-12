# !/home/tools/continuum/Anaconda3-5.0.0.1/bin/python3
# !/usr/bin/python

# Import the required libs
import os
import re
import time
import pprint

def load_def_region_files(replace=0,ipo_dir=None):
    ##########################
    # default option values
    ##########################

    if ipo_dir is None:
        ipo_dir = os.getenv("IPO_DIR")
    
    if replace != 1:
        replace = 0
    else:
        replace = 1

    top = get_top()
    project = os.getenv("NV_PROJECT")

    print("# top : "+str(top)) 
    print("# start to load def/region files...")

    # load coff file 
    # common_dir = str(ipo_dir)+"/"+str(project)+"_top/control/" 
    # read_coff_xml(common_dir+"coff.xml", read_is.make_netlist) 

    all_refs_part    = get_refs_if("*", lambda ref : ref.is_partition())
    all_refs_chiplet = get_refs_if("*", lambda ref : ref.is_chiplet())
    all_refs_macro   = get_refs_if("*", lambda ref : ref.is_macro())

    # load macros def
    for ref_macro in all_refs_macro:
        # full_def
        macro_def_dir = str(ipo_dir)+"/macros/"+str(ref_macro)+"/control/"
        if os.path.exists(str(macro_def_dir)+str(ref_macro)+".def.gz"):
            read_def(str(macro_def_dir)+str(ref_macro)+".def.gz", read_is.make_netlist)
        elif os.path.exists(str(macro_def_dir)+str(ref_macro)+".def"):
            read_def(str(macro_def_dir)+str(ref_macro)+".def", read_is.make_netlist)
        else:
            # print("# no def file found for "+str(ref_macro)) 
            pass

    # load partition def and region
    for ref_part in all_refs_part:
        part_def_dir = str(ipo_dir)+"/"+str(ref_part)+"/control/"
        if os.path.exists(str(part_def_dir)+str(ref_part)+".hfp.pins.def"):
            read_def(str(part_def_dir)+str(ref_part)+".hfp.pins.def", read_is.make_netlist)
        elif os.path.exists(str(part_def_dir)+str(ref_part)+"_fp.def"):
            read_def(str(part_def_dir)+str(ref_part)+"_fp.def", read_is.make_netlist)
        else:
            print("# no def file found for "+str(ref_part))

        if os.path.exists(str(part_def_dir)+str(ref_part)+"_RETIME.tcl"):
            # read_tcl(str(part_def_dir)+str(ref_part)+"_RETIME.tcl")
            print(str(part_def_dir)+str(ref_part)+"_RETIME.tcl") 
        else:
            pass

        if os.path.exists(str(part_def_dir)+str(ref_part)+"_timing_region.tcl"):
            #read_tcl(str(part_def_dir)+str(ref_part)+"_timing_region.tcl")
            print(str(part_def_dir)+str(ref_part)+"_timing_region.tcl")
        else:
            pass
    
    # load chiplet def file        
    for ref_chiplet in all_refs_chiplet:
        chiplet_def_dir = str(ipo_dir)+"/"+str(ref_chiplet)+"/control/"
        if os.path.exists(str(chiplet_def_dir)+str(ref_chiplet)+".hfp.pins.def"):
            read_def(str(chiplet_def_dir)+str(ref_chiplet)+".hfp.pins.def", read_is.make_netlist)
        elif os.path.exists(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def"):
            read_def(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def", read_is.make_netlist)
        else:
            print("# no def file found for "+str(ref_chiplet))
        
