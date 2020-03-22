import argparse
import os
import sys
import copy
import pickle
import _thread
from collections import OrderedDict
from inso_inst import *
from inso_edge import *
from inso_utils import *
__author__ = 'insomnia.px'

class ip_node(object):
    def __init__(self, name, inst_req, in_edges_dic, out_edges_dic):
        self.name = name
        self.inst_req = inst_req
        self.in_edges_dic = in_edges_dic
        self.out_edges_dic = out_edges_dic
        self.E = 0
        self.busy_cycles = 0
        self.idle_cycles_wait_input = 0
        self.idle_cycles_wait_inst = 0
        self.inst_using = None
    def free_inst(self, frozen_free_inst_list, freed_inst): # the freed inst is stored in the list, they are frozen (cannot be allocated) until next cycle
        assert freed_inst != None
        assert freed_inst not in frozen_free_inst_list
        frozen_free_inst_list.append(freed_inst)
    def exec(self):
        pass
    def unfrozen(self, edge_dic):
        for name in self.out_edges_dic:
            edge_dic[self.out_edges_dic[name]].ready = True
    def sim(self, glb_freq, inst_dic, edge_dic, free_inst_list, frozen_free_inst_list, frozen_exec_list):
        for each in self.inst_req:
            if self.inst_req[each] > 0:
                inst_req = each
                break
        input_ready = True
        for name in self.in_edges_dic:
            if not edge_dic[self.in_edges_dic[name]].ready:
                input_ready = False
                break
        inst_ready = inst_req == self.inst_using or inst_req in free_inst_list
        last_cycle = self.inst_req[inst_req]==1 and inst_req == list(self.inst_req.items())[-1][0]
        if input_ready and inst_ready:
            print ('\nexecuting: '+ self.name)
            if inst_req in free_inst_list:
                free_inst_list.remove(inst_req)
            self.inst_using = inst_req
            print ('using: '+ self.inst_using)
            self.E += float(inst_dic[inst_req].power)/glb_freq
            inst_dic[self.inst_using].E += float(inst_dic[inst_req].power)/glb_freq
            self.busy_cycles += 1
            inst_dic[self.inst_using].busy_cycles += 1
            self.inst_req[inst_req]-= 1
            if last_cycle:
                frozen_exec_list.append(self)
                self.free_inst(frozen_free_inst_list = frozen_free_inst_list, freed_inst = self.inst_using)
                self.exec(edge_dic)
                return 'done'
            elif self.inst_req[inst_req]==0: # switch to another inst next cycle
                self.free_inst(frozen_free_inst_list = frozen_free_inst_list, freed_inst = self.inst_using)
            else:
                pass
            return 'busy'
        else:
            self.inst_using = None
            if not inst_ready:
                self.idle_cycles_wait_inst += 1
                return 'wait_for_inst'
            if not input_ready:
                self.idle_cycles_wait_input += 1
                return 'wait_for_input'
    
class eg_dm(ip_node):
    def __init__(self, name, inst_req, in_edges_dic, out_edges_dic):
        ip_node.__init__(self, name, inst_req, in_edges_dic, out_edges_dic)
    def exec(self, edge_dic):
        for e1 in self.in_edges_dic:
            pass
        for e2 in self.out_edges_dic:
            pass
        edge_dic[self.out_edges_dic[e2]].val = copy.deepcopy(edge_dic[self.in_edges_dic[e1]].val)

class eg_conv(ip_node):
    def __init__(self, name, inst_req, in_edges_dic, out_edges_dic, chin, chout, osize, ksize, isize):
        self.chin = chin
        self.chout = chout
        self.osize = osize
        self.ksize = ksize
        self.isize = isize
        ip_node.__init__(self, name, inst_req, in_edges_dic, out_edges_dic)
    def exec(self, edge_dic):
        for rr in range(self.osize):
            for cc in range(self.osize):
                for co in range(self.chout):
                    oidx = co*self.osize*self.osize + rr * self.osize + cc
                    for kr in range(self.ksize):
                        for kc in range(self.ksize):
                            for ci in range(self.chin):
                                kidx = co * self.chin * self.ksize * self.ksize + ci * self.ksize * self.ksize + kr * self.ksize + kc
                                iidx = ci * self.isize * self.isize + (rr+kr) * self.isize + (cc+kc)
                                edge_dic[self.out_edges_dic['o']].val[oidx] += edge_dic[self.in_edges_dic['i']].val[iidx] * edge_dic[self.in_edges_dic['w']].val[kidx]