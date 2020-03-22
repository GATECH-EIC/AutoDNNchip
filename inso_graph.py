import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_utils import *
from inso_inst import *
from inso_edge import *
from inso_node import *

__author__ = 'insomnia.px'

class comp_graph(object):
    def __init__(self, config_json, inst_dic, edge_dic, node_dic, graph_in, graph_out):
        self.inst_dic = inst_dic
        self.node_dic = node_dic
        self.edge_dic = edge_dic
        self.graph_in = graph_in
        self.graph_out = graph_out
        self.node_queue = list(self.node_dic.keys())
        self.inst_list = list(self.inst_dic.keys())
        self.config_json = config_json
        self.set_glb_clk(str_tran(config_json['glb_freq']).val)
    def sw_graph_gen(self):# generate dictionary to do better query
        graph_inv = {}
        for n1 in self.node_dic:
            eins = self.node_dic[n1].in_edges_dic
            eouts = self.node_dic[n1].out_edges_dic
            for dname in eins:
                ein = eins[dname]
                if ein not in graph_inv:
                    graph_inv[ein] = (None, n1)
                else:
                    graph_inv[ein] = (graph_inv[ein][0], n1)
            for dname in eouts:
                eout = eouts[dname]
                if eout not in graph_inv:
                    graph_inv[eout] = (n1, None)
                else:
                    graph_inv[eout] = (n1, graph_inv[eout][1])
        graph = {}
        for es in graph_inv:
            graph[graph_inv[es]] = es
        self.graph = graph
        self.graph_inv = graph_inv
    def hw_graph_gen(self):# generate the hw architecture graph
        next_inst={}
        prev_inst={}
        try:
            graph = self.graph
        except:
            self.sw_graph_gen()
            graph = self.graph
        for npair in graph:
            if (npair[0]!=None and npair[1]!=None):
                i1 = list(self.node_dic[npair[0]].inst_req.items())[-1][0]
                i2 = list(self.node_dic[npair[1]].inst_req.items())[0][0]
                self.add_val_to_dic_list(key_name=i1, dic=next_inst, val=i2)
                self.add_val_to_dic_list(key_name=i2, dic=prev_inst, val=i1)
            else:
                continue
        for n1 in self.node_dic:
            dic1 = self.node_dic[n1].inst_req
            if (len(dic1)<=1):
                continue
            for i in range(len(dic1)-1):
                i3 = list(dic1.items())[i][0]
                i4 = list(dic1.items())[i+1][0]
                assert(i3!=i4)
                self.add_val_to_dic_list(key_name=i3, dic=next_inst, val=i4)
                self.add_val_to_dic_list(key_name=i4, dic=prev_inst, val=i3)
        self.next_inst=next_inst
        self.prev_inst=prev_inst
    def mpdict_gen(self):# generate the dict for task-to-hw mapping
        mp_dict = {}
        for n1 in self.node_dic:
            for i1 in list(self.node_dic[n1].inst_req.items()):
                self.add_val_to_dic_list(key_name=i1[0], dic=mp_dict, val=n1)
        self.mp_dict = mp_dict
    def is_inedge(self, e1, n1):
        ret = False
        for dname in self.node_dic[n1].in_edges_dic:
            if self.node_dic[n1].in_edges_dic[dname].name == e1:
                ret = True
        return ret
    def is_outedge(self, e1, n1):
        ret = False
        for dname in self.node_dic[n1].out_edges_dic:
            if self.node_dic[n1].out_edges_dic[dname] == e1:
                ret = True
        return ret
    def add_val_to_dic_list(self, key_name, dic, val):
        if key_name not in dic:
            dic[key_name] = [val]
        elif key_name in dic and val not in dic[key_name]:
            dic[key_name].append(val)
        else:
            pass
    def add_list_to_dic_list(self, key_name, dic, val_list):
        for val in val_list:
            self.add_val_to_dic_list(key_name=key_name, dic=dic, val=val)
    def set_glb_clk(self, glb_freq):
        self.glb_freq = glb_freq
        for key in self.inst_dic:
            assert (is_factor(big=self.glb_freq, small=str_tran(self.inst_dic[key].att['freq']).val ))
    def get_cycles_mem(self, num_dt, prec1, inst1, static_cycles=0):
        assert (isinstance(static_cycles, int))
        pw = str_tran(inst1.att['pw']).val
        freq = str_tran(inst1.att['freq']).val
        cycles_each = int(self.glb_freq/freq)
        return int(div_up(num_dt * prec1.bits, pw ) * cycles_each) + static_cycles
    def get_cycles_dp(self, num_dt, prec1, inst1, static_cycles=0):
        assert (isinstance(static_cycles, int))
        pw = str_tran(inst1.att['pw']).val
        freq = str_tran(inst1.att['freq']).val
        burst_len = str_tran(inst1.att['burst_len']).val
        cycles_each = int(self.glb_freq/freq)
        return int(div_up(num_dt * prec1.bits, pw) * cycles_each + static_cycles * div_up(num_dt * prec1.bits, pw * burst_len) )
    def get_cycles_comp(self, inst1, comp=1, static_cycles=0):
        assert (isinstance(static_cycles,int))
        assert (isinstance(comp, int))
        freq = str_tran(inst1.att['freq']).val
        cycles_each = int(self.glb_freq/freq)
        return int(comp* cycles_each) + static_cycles
    def sim_inter_ip_pipeline(self,sim_cycles=float('inf')):
        self.free_inst_list = copy.deepcopy(self.inst_list)
        for name in self.free_inst_list:
            self.inst_dic[name].rst()
        self.frozen_free_inst_list = []
        self.frozen_exec_list = []
        cycle = 0
        stop = False
        while cycle < sim_cycles+1 and not stop:
            if self.node_queue==[]:
                stop = True            
            print ('\n'+'-'*60+'cycle: '+str(cycle)+'-'*60)
            print ('ip_nodes remaining: '+str(len(self.node_queue)))
            for each in self.frozen_exec_list:
                each.unfrozen(edge_dic=self.edge_dic)
            self.frozen_exec_list = []
            self.free_inst_list += self.frozen_free_inst_list
            self.frozen_free_inst_list = []
            self.sim_one_cycle()
            cycle += 1
        self.lat = cycle-1
    def sim_one_cycle(self):
        node_queue_this_cycle = copy.deepcopy(self.node_queue)
        for name in node_queue_this_cycle:
            ret = self.node_dic[name].sim(glb_freq=self.glb_freq,
                                          inst_dic=self.inst_dic,
                                          edge_dic=self.edge_dic,
                                          free_inst_list=self.free_inst_list,
                                          frozen_free_inst_list=self.frozen_free_inst_list,
                                          frozen_exec_list = self.frozen_exec_list)
            if ret == 'done':
                if 'ret' in self.node_dic[name].out_edges_dic:
                    print ('generated output edge (ret matrix): '+ self.node_dic[name].out_edges_dic['ret'] + '=' + str(self.edge_dic[self.node_dic[name].out_edges_dic['ret']].val))
                print ('remove done ip_node: '+ name + '\n')
                self.node_queue.remove(name)
    def post_sim_log(self):
        E1 = 0
        E2 = 0
        for n1 in self.node_dic:
            E1 += self.node_dic[n1].E
        for i1 in self.inst_dic:
            print ('busy cycles of '+i1+': '+str(self.inst_dic[i1].busy_cycles))
        for i1 in self.inst_dic:
            print ('energy of '+ i1 + ': '+str(self.inst_dic[i1].E))
            E2 += self.inst_dic[i1].E
        print ('Latency(cycles): '+str(self.lat))
        print ('Latency(s): '+str(float(self.lat)/self.glb_freq))
        print ('Energy(J): '+ str(E1)+ ' '+str(E2))
    def connect_to(self, graph2): # connect two graphs to be a larger graph, there must be no overlap between the inst_dict of the two graph
        assert (self.glb_freq == graph2.glb_freq)
        config_json_new = copy.deepcopy(self.config_json)
        config_json_new.update(graph2.config_json)
        inst_dic_new = copy.deepcopy(self.inst_dic)
        inst_dic_new.update(graph2.inst_dic)
        assert (len(self.inst_dic) + len(graph2.inst_dic) == len(inst_dic_new))
        edge_dic_new = copy.deepcopy(self.edge_dic)
        edge_dic_new.update(graph2.edge_dic)
        cnt1 = len(self.edge_dic) + len(graph2.edge_dic) - len(edge_dic_new)
        node_dic_new = copy.deepcopy(self.node_dic)
        node_dic_new.update(graph2.node_dic)
        graph_in_new = self.graph_in + graph2.graph_in
        graph_out_new = self.graph_out + graph2.graph_out
        cnt2 = 0
        for each in self.graph_out:
            if each in graph2.graph_in:
                cnt2 += 1
                graph_in_new.remove(each)
                graph_out_new.remove(each)
                edge_dic_new[each].ready = False
                edge_dic_new[each].val = None
        assert (cnt2 == cnt1)
        new_graph = comp_graph(config_json = config_json_new,
                               inst_dic =  inst_dic_new,
                               edge_dic = edge_dic_new,
                               node_dic = node_dic_new,
                               graph_in = graph_in_new,
                               graph_out = graph_out_new)
        return new_graph