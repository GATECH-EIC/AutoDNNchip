import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_lib import *
from inso_utils import *
__author__ = 'insomnia.px'

class inst(object):
    def __init__(self, name, att, power_lib):
        self.name = name
        self.att = att
        self.inst_tpye = power_lib.cls
        self.power = power_lib.get_power(att)
        self.busy_cycles = 0
        self.E = 0
    def rst(self):
        self.busy_cycles = 0
        self.E = 0
    def get_cycles_mem(self, num_dt, prec1, glb_freq, static_cycles=0):
        assert (self.inst_tpye=='memory')
        assert (isinstance(static_cycles, int))
        pw = str_tran(self.att['pw']).val
        freq = str_tran(self.att['freq']).val
        cycles_each = int(glb_freq/freq)
        return int(div_up(num_dt * prec1.bits, pw ) * cycles_each) + static_cycles
    def get_cycles_dp(self, num_dt, prec1, glb_freq, static_cycles=0):
        assert (isinstance(static_cycles, int))
        pw = str_tran(self.att['pw']).val
        freq = str_tran(self.att['freq']).val
        burst_len = str_tran(self.att['burst_len']).val
        cycles_each = int(glb_freq/freq)
        return int(div_up(num_dt * prec1.bits, pw) * cycles_each + static_cycles * div_up(num_dt * prec1.bits, pw * burst_len) )
    def get_cycles_comp(self, glb_freq, comp=1, static_cycles=0):
        assert (isinstance(static_cycles,int))
        assert (isinstance(comp, int))
        freq = str_tran(self.att['freq']).val
        cycles_each = int(glb_freq/freq)
        return int(comp* cycles_each) + static_cycles


