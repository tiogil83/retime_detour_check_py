# !/home/tools/continuum/Anaconda3-5.0.0.1/bin/python3
# !/usr/bin/python

import json
import os
import re
import gzip
import time
import multiprocessing
from joblib import Parallel, delayed
from math import inf

def generate_report(viol_file):
    # global vars
    global rule_json_data
    global rule_pipe_mapping
    global interf_json_data
    global unit_hier_mapping
    global noscan_port_mapping
    global merge_flop_mapping
    global noscan_port_mapping
    global all_neighbor_pars
    global all_thr_paths 

    rule_json_data = dict()
    rule_pipe_mapping = dict()
    interf_json_data = dict()
    unit_hier_mapping = dict()
    noscan_port_mapping = dict()
    merge_flop_mapping = dict()
    noscan_port_mapping = dict()
    all_neighbor_pars = dict()
    all_thr_paths = dict()

    # load region/def files
    if str(os.getenv("TS_VIEW")) != "ipo":
        load_def_region_files()    
    
    # load retime related files
    load_retime_files() 
    load_port_map_file() 
    get_unit_name_dict()

    if str(os.getenv("TS_VIEW")) == "noscan" or str(os.getenv("TS_VIEW")) == "feflat":
        get_all_neighbor_pars()
        get_all_thr_paths() 

    if str(os.getenv("TS_VIEW")) == "ipo":
        map_merged_flops() 
    
    if os.path.exists(viol_file):
        print("Loading "+str(viol_file))
        #read_timing_rep(viol_file) 
    else:
        raise Exception ("Can't Find Vioaltion File "+str(viol_file))

    vios = all_vios()
    global vio_num
    vio_num = vios.size()
    print("Violation Num : "+str(vio_num)) 

    # user-defined attribution
    user_defined_attrs = [
        'start_unit', 'end_unit',
        'start_par', 'end_par',
        'start_routeRule', 'end_routeRule',
        'man_distance',
    ]

    for user_defined_attr in user_defined_attrs:
        if str(user_defined_attr) in Vio.user_attr_list():
            pass
        else:
            Vio.create_user_attr(str(user_defined_attr))

    print("stime : "+str(time.asctime(time.localtime(time.time()))))
    for vio in vios:
        set_vios_attri(vio)
    # multi processing 
    #
    #num_cores = multiprocessing.cpu_count()
    #Parallel(n_jobs=16)(delayed(set_vios_attri)(vio) for vio in vios)
    #
    print("etime : "+str(time.asctime(time.localtime(time.time()))))
    
def set_vios_attri(vio):
    global vio_num
    with open ("./vio_info.txt", 'a') as vio_info:
        start_pin = str(vio.start_pin())
        end_pin = str(vio.end_pin())
        vio_id = str(vio.core_id())
        
        if int(vio_id) < 10000:
            if int(vio_id) % 1000 == 0:
                print("Processed "+str(vio_id)+" of "+str(vio_num))
        elif vio_id == vio_num :
            print ("Processed All the "+str(vio_num))
        else:
            if int(vio_id) % 10000 == 0:
                print("Processed "+str(vio_id)+" of "+str(vio_num))
             
        
        start_unit = mapPinUnit(str(start_pin))
        end_unit = mapPinUnit(str(end_pin))
        start_par = get_pin_partition(str(start_pin))
        end_par = get_pin_partition(str(end_pin))
        start_routeRule = get_rule_of_pin(str(start_pin))
        end_routeRule = get_rule_of_pin(str(end_pin))
        
        vio.set_user_attr(Vio_attr("start_unit"), start_unit)
        vio.set_user_attr(Vio_attr("end_unit"), end_unit)
        vio.set_user_attr(Vio_attr("start_par"), start_par)
        vio.set_user_attr(Vio_attr("end_par"), end_par)
        vio.set_user_attr(Vio_attr("start_routeRule"), start_routeRule)
        vio.set_user_attr(Vio_attr("end_routeRule"), end_routeRule)
        
        #print(str(vio_id))
        # set the not placed cells to parenct_cell centroid
        if get_pin(str(start_pin)).is_placed() is True:
            start_pin_xy = get_pin(str(start_pin)).xy()
        else:
            start_pin_xy = set_cell_to_centroid(str(get_pin(str(start_pin)).cell()))
        
        if get_pin(str(end_pin)).is_placed() is True:
            end_pin_xy = get_pin(str(end_pin)).xy()
        else:
            end_pin_xy = set_cell_to_centroid(str(get_pin(str(end_pin)).cell()))
        
        man_dist = str(start_pin_xy.xy_dist_to(end_pin_xy))
        vio.set_user_attr(Vio_attr("man_distance"), man_dist)
        
        vio_info.write(f'{vio_id} {start_pin} {end_pin} {start_unit} {end_unit} {start_routeRule} {end_routeRule} {start_pin_xy} {end_pin_xy} {man_dist}\n')


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

def get_unit_name_dict():
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

    #if unit_hier_mapping in globals(): 
    #    pass
    #else:
    #    get_unit_name_dict()

    for name in unit_hier_mapping.keys():
        match = re.match(name, pin) 
        if match:
            return(str(unit_hier_mapping[name]))

    return("NA")

def load_port_map_file():
    global noscan_port_mapping
    # default value for 2d dict
    # noscan_port_mapping = defaultdict(defaultdict) 
    noscan_port_mapping = dict()

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
                    addtodict2(noscan_port_mapping, par_ref, par_port, 1)
                else:
                    continue
        else:
            continue

def map_merged_flops():
    global merge_flop_mapping
    merge_flop_mapping = dict()
    
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
                                merge_flop_mapping[merge_flop_pin] = single_flop_pin
                        ref_pin_dict = dict()
                    elif re.match( r'b\'\s+(\S+): (\S+)\\n\'', str(line)):
                        match = re.match( r'b\'\s+(\S+): (\S+)\\n\'', str(line))
                        ref_pin_dict[str(match.group(1))] = str(match.group(2))
                    else:
                        pass
        else:
            print("No Merge Flop Mapping Found for "+str(par_ref))

def get_demerged_name(pin_name):
    global merge_flop_mapping

    if not merge_flop_mapping:
        map_merged_flops()

    pin = get_pin(pin_name, name_is.quiet) ;

    if pin.is_null():
        raise Exception ("Can't find pin "+str(pin_name))
    elif pin_name in merge_flop_mapping.keys():
        return(merge_flop_mapping[pin_name])        
    else:
        print("Not a merge flop "+str(pin_name))

def get_vio_sig_name(vio):
    global noscan_port_mapping
    # no pin list attr for violation yet
    # to fix
    return 1 

def get_rule_of_pin(pin_name):
    global rule_json_data
    global merge_flop_mapping
    global rule_pipe_mapping

    if not rule_json_data:
        load_retime_files()

    if not merge_flop_mapping:
        map_merged_flops()
    
    rule = "NA"

    pin = get_port(pin_name, name_is.quiet)
    if pin.is_port() is True and pin.is_null() is False:
        return(str(rule)) 
    else:
        pin = get_pin(pin_name, name_is.quiet)
        if pin.is_null() is True:
            raise Exception ("Can't find the pin "+str(pin_name))
        else:
            if pin_name in merge_flop_mapping.keys():
                pin_name = get_demerged_name(pin_name)
            else:
                pass

    if re.search(".*_retime_partition_*", pin_name):
        ret = re.search(".*_retime_partition_.*RT.*?_(\S+?)\/\S+\/\S+", pin_name)
        step = ret.group(1)
        for chiplet in rule_pipe_mapping.keys():
            for rule_name in rule_pipe_mapping[chiplet].keys():
                if step in rule_pipe_mapping[chiplet][rule_name].keys():
                    rule = rule_name
                    return(str(rule))
                else:
                    continue
        return(str(rule))
    else:
        return(str(rule))

def get_point_dist(sx, sy, ex, ey):
    dist = abs(ex - sx) + abs (ey - sy)
    return(dist)

def get_all_par_insts():
    all_par_insts = []
    all_refs_part = get_refs_if("*", lambda ref : ref.is_partition())
    for par_ref in all_refs_part:
        par_insts = get_cells_of(str(par_ref), name_is.hier)
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
# floyed-warshall
def get_all_thr_paths():
    global all_thr_paths
    global all_neighbor_pars

    all_thr_paths = dict()

    nxt = dict()
    dist = dict()

    edges = []
    for node in all_neighbor_pars.keys():
        for neighbour in all_neighbor_pars[node]:
            edges.append((node, neighbour))

    for i in all_neighbor_pars.keys():
        for j in all_neighbor_pars.keys():
            addtodict2(nxt, i, j, 0)
            if i == j:
                addtodict2(dist, i, j, 0)
            else:
                addtodict2(dist, i, j, inf)
    for u, v in edges:
        dist[u][v] = 1
        nxt[u][v] = v
    for k in all_neighbor_pars.keys():
        for i in all_neighbor_pars.keys():
            for j in all_neighbor_pars.keys():
                sum_ik_kj = dist[i][k] + dist[k][j]
                if dist[i][j] > sum_ik_kj:
                    dist[i][j] = sum_ik_kj
                    nxt[i][j] = nxt[i][k]
    for i in all_neighbor_pars.keys():
        for j in all_neighbor_pars.keys():
            path = [i]
            while path[-1] != j:
                path.append(nxt[path[-1]][j])
            addtodict2(all_thr_paths, str(i), str(j), path)

#def find_all_path(start_vertex, end_vertex, path=[]):
#    global all_neighbor_pars
#
#    path = path + [start_vertex]
#    if start_vertex == end_vertex:
#        return [path]
#    if start_vertex not in all_neighbor_pars:
#        return []
#    paths = []
#    for vertex in all_neighbor_pars[start_vertex]:
#        if vertex not in path:
#            extended_paths = find_all_path(vertex, end_vertex, path)
#            for p in extended_paths:
#                paths.append(p)
#    return paths
#

def get_pin_partition(pin_name):
    if get_port(pin_name, name_is.quiet).is_null() is False:
        return("PORT")

    cell = get_pin(pin_name).cell()
    if cell.base_ref().is_partition() is True:
        return(str(cell))
    else:
        par_cell = get_cell_partition(str(cell))
        return(str(par_cell))
    
def get_cell_partition(cell_name):
    if get_cell(cell_name).base_ref().is_partition() is True:
        return(str(cell_name))
    else:
        parent_cell = get_cell(cell_name).parent_cell()
        parent_ref = get_cell(cell_name).parent_ref() 
        if parent_ref.is_partition() is True:
            return(str(parent_cell))
        else:
            cell_name = parent_cell
            return(get_cell_partition(str(cell_name)))

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

    # set default macro size 10x10
    layout().set_default_size(10, 10)

    print("# top : "+str(top)) 
    print("# start to load def/region files...")

    # load coff file 
    # common_dir = str(ipo_dir)+"/"+str(project)+"_top/control/" 
    # read_coff_xml(common_dir+"coff.xml", read_is.make_netlist) 

    all_refs_part    = get_refs_if("*", lambda ref : ref.is_partition())
    all_refs_chiplet = get_refs_if("*", lambda ref : ref.is_chiplet())
    all_refs_macro   = get_refs_if("*", lambda ref : ref.is_macro())


    # to fix. load _fp def for noscan/feflat, load pin def for flat
    # load macros def
    for ref_macro in all_refs_macro:
        # full_def
        if os.getenv("TS_VIEW") == "ipo":
            pass
        else:
            macro_def_dir = str(ipo_dir)+"/macros/"+str(ref_macro)+"/control/"
            if os.path.exists(str(macro_def_dir)+str(ref_macro)+".def.gz"):
                read_def(str(macro_def_dir)+str(ref_macro)+".def.gz")
            elif os.path.exists(str(macro_def_dir)+str(ref_macro)+".def"):
                read_def(str(macro_def_dir)+str(ref_macro)+".def")
            else:
                pass

    # load partition def and region
    for ref_part in all_refs_part:
        part_def_dir = str(ipo_dir)+"/"+str(ref_part)+"/control/"
        if os.getenv("TS_VIEW") == "noscan" or os.getenv("TS_VIEW") == "feflat":
            if os.path.exists(str(part_def_dir)+str(ref_part)+"_fp.def"):
                read_def(str(part_def_dir)+str(ref_part)+"_fp.def")
            else:
                print("# no def file found for "+str(ref_part))

            if os.path.exists(str(part_def_dir)+str(ref_part)+"_RETIME.tcl"):
                #read_tcl(str(part_def_dir)+str(ref_part)+"_RETIME.tcl")
                print(str(part_def_dir)+str(ref_part)+"_RETIME.tcl")
            else:
                pass

            if os.path.exists(str(part_def_dir)+str(ref_part)+"_timing_region.tcl"):
                #read_tcl(str(part_def_dir)+str(ref_part)+"_timing_region.tcl")
                print(str(part_def_dir)+str(ref_part)+"_timing_region.tcl")
            else:
                pass

        elif os.getenv("TS_VIEW") == "flat":
            if os.path.exists(str(part_def_dir)+str(ref_part)+".hfp.pins.def"):
                read_def(str(part_def_dir)+str(ref_part)+".hfp.pins.def")
            elif os.path.exists(str(part_def_dir)+str(ref_part)+"_fp.def"):
                read_def(str(part_def_dir)+str(ref_part)+"_fp.def")
            else:
                print("# no def file found for "+str(ref_part))
        else:
            pass

    
    # load chiplet def file        
    for ref_chiplet in all_refs_chiplet:
        chiplet_def_dir = str(ipo_dir)+"/"+str(ref_chiplet)+"/control/"
        if os.getenv("TS_VIEW") == "noscan" or os.getenv("TS_VIEW") == "feflat":
            if os.path.exists(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def"):
                read_def(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def")
            else:
                print("# no def file found for "+str(ref_chiplet))
        elif os.getenv("TS_VIEW") == "flat":
            if os.path.exists(str(chiplet_def_dir)+str(ref_chiplet)+".hfp.pins.def"):
                read_def(str(chiplet_def_dir)+str(ref_chiplet)+".hfp.pins.def")
            elif os.path.exists(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def"):
                read_def(str(chiplet_def_dir)+str(ref_chiplet)+"_fp.def")
            else:
                print("# no def file found for "+str(ref_chiplet))
        

def set_cell_to_centroid(cell_name):
    parent_cell = str(get_cell(str(cell_name)).parent_cell())
    if get_cell(parent_cell).is_placed() is True:
        return(get_cell(parent_cell).centroid())
    else:
        return(set_cell_to_centroid(str(parent_cell)))
