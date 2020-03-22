import argparse
import os
import sys
import copy
import pickle
import _thread
import json
__author__ = "insomnia.px"

#hw lib: memory, computation components, data path
class hw_lib(object):
    def __init__(self, js_name):
        self.sp = '_'
        with open(js_name) as js_file:
            self.raw_dt = json.load(js_file)
        self.set_hierarchy()
        if 'mem' in js_name:
            name = 'memory'
        elif 'comp_mul' in js_name:
            name = 'comp_mul'
        elif 'dpath' in js_name:
            name = 'dpath'
        else:
            print (js_name)
            raise
        self.cls = name
    def set_hierarchy(self):
        dt2 = {}
        for key, value in self.raw_dt.items():
            parts = key.split(self.sp)
            par = dt2
            new_key = parts.pop(0)
            while parts:
                par = par.setdefault(new_key,{})
                new_key = parts.pop(0)
            par[new_key] = value
        self.dt = dt2
    def get_power(self, att):
        if (self.cls=='memory'): # '28nm_128bit_8KB_1000MHz'
            return self.dt[att['tech']][att['pw']][att['vol']][att['freq']]
        elif (self.cls == 'comp_mul'): # '65nm_256mul_8bit_10bit_12bit_500MHz'
            return self.dt[att['tech']][att['num_mul']][att['prec_in1']][att['prec_in2']][att['prec_out']][att['freq']]
        elif (self.cls == 'dpath'): # '28nm_128bit_1bit_1000MHz'
            return self.dt[att['tech']][att['pw']][att['burst_len']][att['freq']]
        else:
            raise NameError('wrong class: '+self.cls+', the class of hw lib must be memory/comp/dpath')
            return 
