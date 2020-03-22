import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_utils import *
__author__ = 'insomnia.px'


class tensor_edge(object):
    def __init__(self, name, addr, prec, np_val=None, ready=False):
        self.name = name
        self.prec = prec
        self.val = np_val
        self.addr = addr
        self.ready = ready
    def quantize(self):
        self.qval = None
        pass

class fixed_prec(object):
    def __init__(self, int_bits, frac_bits, padding_bits = 0):
        self.info = {'signed':1, 'int_bits':int_bits, 'frac_bits':frac_bits, 'padding_bits':padding_bits}
        self.bits = 1 + int_bits + frac_bits + padding_bits

class addr(object):
    def __init__(self, data_name, np_val):
        self.name = data_name
        self.val = np_val
    def debug(self):
        pass
