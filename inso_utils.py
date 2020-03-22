import math
import numpy as np

def print_np(np_array, show_all=False):
    print (np_array.shape)
    print (np_array.size)
    if show_all:
        print (np_array)

def print_dict(dic1):
    print ('')
    for name in dic1:
        print (str(name)+': '+str(dic1[name]))

def is_factor(big, small):
    return float(big)/small == int(float(big)/small)

def div_up(a,b):
    return math.ceil(float(a)/b)

def div_down(a,b):
    return math.floor(float(a)/b)

class str_tran(object):
    def __init__(self, a):
        trans_dict= {'MHz':10**6, 'bit':1, 'KB':1024*8, 'MB':1024*1024*8, 'mul':1, 'nm':1, 'data':1}
        for key in trans_dict:
            if key in a:
                self.val = int(a.replace(key,''))*trans_dict[key]
                break
        self.raw = a
    def debug(self):
        print (self.raw+': '+ str(self.val))



def test_str_tran():
    a1 = str_tran('5MHz')
    a1.debug()
    a2 = str_tran('7bit')
    a2.debug()
    a3 = str_tran('28nm')
    a3.debug()
    a4 = str_tran('128mul')
    a4.debug()
    a6 = str_tran('10KB')
    a6.debug()
    a7 = str_tran('1MB')
    a7.debug()

    
def deque(lis1):
    a = lis1[0]
    lis1.remove(a)
    return a
