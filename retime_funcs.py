# !/home/tools/continuum/Anaconda3-5.0.0.1/bin/python3
# !/usr/bin/python

# Import the required libs

import json
import os
import re
import gzip
#from collections import defaultdict


def load_retime_files(): 
    global rule_json_data
    global rule_pipe_mapping
    global interf_json_data

    rule_json_data = dict()
    interf_json_data = dict()
    # initial value for 3d dict
    # rule_pipe_mapping = defaultdict(lambda : defaultdict(defaultdict))
    rule_pipe_mapping = dict()

    tot = os.path.abspath(os.popen("depth").read())
    
    project = os.getenv("NV_PROJECT")
    retime_json_dir = str(tot)+"/timing/"+str(project)+"/timing_scripts/workflow/retime_detour_support"

    if os.path.exists(str(retime_json_dir)+"/retime_pm2jason.pl"):
        os.system(str(retime_json_dir)+"/retime_pm2jason.pl")
    else:
        print("retime2json script "+str(retime_json_dir)+"/retime_pm2jason.pl not found.")
    
    if os.path.exists(str(retime_json_dir)+"/routeRules.json"):
        with open(str(retime_json_dir)+"/routeRules.json", 'r') as rule_json_file:
            rule_json_data = json.load(rule_json_file)
            # print(json.dumps(rule_json_data,indent=4,sort_keys=True))
    else:
        print("Rule Json Data "+str(retime_json_dir)+"/routeRules.json not found.")
    
    if os.path.exists(str(retime_json_dir)+"/interface.json"):
        with open (str(retime_json_dir)+"/interface.json", 'r') as interf_json_file:
            interf_json_data = json.load(interf_json_file)
            # print(json.dumps(interf_json_data,indent=4,sort_keys=True))
    else:
        print("Interface Json Data "+str(retime_json_dir)+"/interface.json not found.")

    for chiplet in rule_json_data.keys():
        for rule_name in rule_json_data[chiplet].keys():
            if rule_json_data[chiplet][rule_name]['pipeline_steps']:
                pipeline_steps_str = str(rule_json_data[chiplet][rule_name]['pipeline_steps'])
                for step in pipeline_steps_str.split(","):
                    addtodict3(rule_pipe_mapping, chiplet, rule_name, step, 1)
            else:
                pass
            if 'tap' in rule_json_data[chiplet][rule_name].keys():
                for tap_num in rule_json_data[chiplet][rule_name]['tap'].keys():
                    if rule_json_data[chiplet][rule_name]['tap'][tap_num]['pipeline_steps']:
                        pipeline_steps_str = str(rule_json_data[chiplet][rule_name]['tap'][tap_num]['pipeline_steps'])
                        for step in pipeline_steps_str.split(","):
                            #print(str(chiplet)+" "+str(rule_name)+" "+str(step))
                            addtodict3(rule_pipe_mapping, chiplet, rule_name, step, 1)
                    else:
                        pass    
            else:
                pass       

def addtodict2(thedict, key_a, key_b, val): 
    if key_a in thedict:
        thedict[key_a].update({key_b: val})
    else:
        thedict.update({key_a:{key_b: val}})

def addtodict3(thedict,key_a,key_b,key_c,val):
    if key_a in thedict:
        if key_b in thedict[key_a]:
            thedict[key_a][key_b].update({key_c:val})
        else:
            thedict[key_a].update({key_b:{key_c:val}})
    else:
        thedict.update({key_a:{key_b:{key_c:val}}})

def genUnitNameDict():
    global unit_hier_mapping
    unit_hier_mapping = dict() 
    
    env().chip_config().load_chip_config_hash() #load full chip_config

    all_units = env().chip_config().query_hash("{partitioning}{units}").getMapKeys()
    for unit_name in all_units:
        try:
            partitions = env().chip_config().query_hash("{partitioning}{units}").getMapValue(unit_name).getMapValue("partition").getMapKeys()
        except:
            continue
        else:
            for par_inst in partitions:
                unit_insts = env().chip_config().query_hash("{partitioning}{units}").getMapValue(unit_name).getMapValue("partition").getMapValue(par_inst).getValue().split(",")
                for unit_inst in unit_insts:
                    unit_inst_in_par = str(par_inst)+"/"+str(unit_inst)
                    unit_hier_mapping[str(unit_inst_in_par)] = str(unit_name)
                    #print(unit_hier_mapping[str(unit_inst_in_par)]+" "+unit_inst_in_par)

def mapPinUnit(pin):
    global unit_hier_mapping

    if not unit_hier_mapping: 
        genUnitNameDict()
    else:
        pass

    for name in unit_hier_mapping:
        match = re.match(name, pin) 
        if match:
            return unit_hier_mapping[name] 

def load_port_map_file():
    global M_noscan_port_mapping
    # default value for 2d dict
    # M_noscan_port_mapping = defaultdict(defaultdict) 
    M_noscan_port_mapping = dict()

    ipo_dir = os.getenv("IPO_DIR")
    chiplet_refs = get_refs_if("*", lambda ref : ref.is_chiplet())
    for chiplet_ref in chiplet_refs:
        noscan_map_file = str(ipo_dir)+"/"+str(chiplet_ref)+"/noscan_cfg/"+str(chiplet_ref)+".noscan.portmap"    
        if os.path.exists(noscan_map_file):
            print("Loading file "+str(noscan_map_file))
            try:
                noscan_map = open(noscan_map_file, 'r').readlines()
            except Exception as err:
                print("Can't open file "+str(noscan_map_file))
            for line in noscan_map:
                if re.search("^\w+", line):
                    [par_ref, par_port, unit_name, unit_inst, unit_port] = line.split()
                    par_port = re.sub("\\\\", "", par_port)
                    addtodict2(M_noscan_port_mapping, par_ref, par_port, 1)
                else:
                    continue
        else:
            continue

def map_merged_flops():
    global M_merge_flop_mapping
    M_merge_flop_mapping = dict()
    
    if str(os.getenv("TS_VIEW")) != "ipo":
        return() 

    par_refs = get_refs_if("*", lambda ref : ref.is_partition())
    #par_refs = ["GAFS0CE0"]
    ipo_dir = os.getenv("IPO_DIR") 
    ref_pin_dict = dict()
    
    for par_ref in par_refs:
        par_insts = get_cells_of(str(par_ref))
        ipo_num = get_ref(str(par_ref)).ipo_num()
        merge_mapping_file = str(ipo_dir)+"/"+str(par_ref)+"/netlists/"+str(par_ref)+".ipo"+str(ipo_num)+".multibitMapping.gz"
        if os.path.exists(merge_mapping_file):
            print("Loading Merge Flop Mapping "+str(merge_mapping_file)) 
            with gzip.open(merge_mapping_file, 'r') as fin:
                for line in fin:
                    if re.match( r'b\'- ', str(line)):
                        if re.match( r'b\'- (\S+):\\n\'', str(line)):
                            match = re.match( r'b\'- (\S+):\\n\'', str(line))
                        elif re.match( r'b\'- \? (\S+)\\n\'', str(line)):
                            match = re.match( r'b\'- \? (\S+)\\n\'', str(line))
                        else:
                            raise Exception ("Double check Merge flops "+str(line))
                        par_merge_flop = str(match.group(1))
                        ref_pin_dict = dict()
                    elif re.match( r'b\'\s+inst: ', str(line)):
                        match = re.match( r'b\'\s+inst: (\S+)\\n\'', str(line))
                        for par_inst in par_insts:
                            merge_flop = str(par_inst)+"/"+str(par_merge_flop)
                            single_flop = str(par_inst)+"/"+str(match.group(1))
                            for single_pin in ref_pin_dict:
                                merge_flop_pin = str(merge_flop)+"/"+str(ref_pin_dict[single_pin])
                                single_flop_pin = str(single_flop)+"/"+str(single_pin)
                                M_merge_flop_mapping[merge_flop_pin] = single_flop_pin
                        ref_pin_dict = dict()
                    elif re.match( r'b\'\s+(\S+): (\S+)\\n\'', str(line)):
                        match = re.match( r'b\'\s+(\S+): (\S+)\\n\'', str(line))
                        ref_pin_dict[str(match.group(1))] = str(match.group(2))
                    else:
                        pass
        else:
            print("No Merge Flop Mapping Found for "+str(par_ref))

def get_demerged_name(pin_name):
    global M_merge_flop_mapping

    if not M_merge_flop_mapping:
        map_merged_flops()

    pin = get_pin(pin_name, name_is.quiet) ;

    if pin.is_null():
        raise Exception ("Can't find pin "+str(pin_name))
    elif pin_name in M_merge_flop_mapping.keys():
        return(M_merge_flop_mapping[pin_name])        
    else:
        print("Not a merge flop "+str(pin_name))

def get_vio_sig_name(vio):
    global M_noscan_port_mapping
    # no pin list attr for violation yet
    # to fix
    return 1 

def get_rule_of_pin(pin_name):
    global rule_json_data
    global M_merge_flop_mapping
    global rule_pipe_mapping

    if not rule_json_data:
        load_retime_files()

    if not M_merge_flop_mapping:
        map_merged_flops()
    
    rule = "NA"

    pin = get_port(pin_name, name_is.quiet)
    if pin.is_port() is True and pin.is_null() is False:
        return(rule) 
    else:
        pin = get_pin(pin_name, name_is.quiet)
        if pin.is_null() is True:
            raise Exception ("Can't find the pin "+str(pin_name))
        else:
            if pin_name in M_merge_flop_mapping.keys():
                pin_name = get_demerged_name(pin_name)
            else:
                pass

    if re.search(".*_retime_partition_*", pin_name):
        ret = re.search(".*_retime_partition_.*RT.*?_(\S+?)\/\S+\/\S+", pin_name)
        step = ret.group(1)
        for chiplet in rule_pipe_mapping.keys():
            for rule_name in rule_pipe_mapping[chiplet].keys():
                if step in rule_pipe_mapping[chiplet][rule_name].keys():
                    return(rule_name)
                else:
                    continue
    else:
        return(rule)

def get_point_dist(sx, sy, ex, ey):
    dist = abs(ex - sx) + abs (ey - sy)
    return(dist)

def get_all_par_insts():
    all_par_insts = []
    all_refs_part = get_refs_if("*", lambda ref : ref.is_partition())
    for par_ref in all_refs_part:
        par_insts = get_cells_of(str(par_ref))
        for par_inst in par_insts:
            all_par_insts.append(str(par_inst))
    return(all_par_insts)

def get_neighbor_pars(par_inst):
    neighbor_pars = [] 
    par_bound_len = dict()
    neighbors = get_cell(par_inst).abutments_all()
    for abut_info in neighbors:
        if re.match("{"+str(par_inst)+"\s+\|\s+(\S+) \(.*\) at \[\((\S+) (\S+)\)->\((\S+) (\S+)\)\] \| \[.*", str(abut_info)): 
            ret = re.match("{"+str(par_inst)+"\s+\|\s+(\S+) \(.*\) at \[\((\S+) (\S+)\)->\((\S+) (\S+)\)\] \| \[.*", str(abut_info))
            par_name = ret.group(1)
            if get_cell(par_name, name_is.quiet).is_null() is False:
                bound_len = get_point_dist(float(ret.group(2)), float(ret.group(3)), float(ret.group(4)), float(ret.group(5)))
                if par_name in par_bound_len.keys():
                    par_bound_len[par_name] = par_bound_len[par_name] + bound_len
                else:
                    par_bound_len[par_name] = bound_len
        else:
            continue

    for par in par_bound_len.keys():
        if par_bound_len[par] > 200:
            neighbor_pars.append(par) 
        else:
            continue
    
    return neighbor_pars

def get_all_neighbor_pars():
    global all_neighbor_pars
    all_neighbor_pars = dict()

    all_par_insts = get_all_par_insts()
    for par_inst in all_par_insts:
        all_neighbor_pars[par_inst] = get_neighbor_pars(par_inst)  

# use Graph for get the shortest through path
def find_all_path(start_vertex, end_vertex, path=[]):
    global all_neighbor_pars

    path = path + [start_vertex]
    if start_vertex == end_vertex:
        return [path]
    if start_vertex not in all_neighbor_pars:
        return []
    paths = []
    for vertex in all_neighbor_pars[start_vertex]:
        if vertex not in path:
            extended_paths = find_all_path(vertex, end_vertex, path)
            for p in extended_paths:
                paths.append(p)
    return paths

def get_shortest_path(paths):
    min_len = ""
    min_path = []
    for path in paths:
        leng = len(path)
        if min_len:
            if leng < min_len:
                min_len = leng
                min_path = path
            else:
                continue
        else:
            min_len = leng
            min_path = path

    return(min_path)

def get_all_thr_paths():
    global all_neighbor_pars
    global all_thr_paths 

    all_thr_paths = dict()
    
    if not all_neighbor_pars:
        get_all_neighbor_pars() 

    all_par_insts = get_all_par_insts()

    for start_par in all_par_insts:
        for end_par in all_par_insts:
            full_paths = find_all_path(start_par, end_par)
            thr_path = get_shortest_path(full_paths)
            addtodict2(all_thr_paths, start_par, end_par, thr_path) 
