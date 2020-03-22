import argparse
import os
import sys
import copy
import pickle
import _thread
# from inso_temp_skynet import *
from inso_temp_systolic import *
import json
__author__ = 'insomnia.px'


def def_graph():
    tmp_list = ['systolic2x', 'systolic1x']
    parser = argparse.ArgumentParser(description='Build a graph for chip predictor using exsiting architecture templates')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--template',
        default=None,
        help='use existing systolic template to define'
    )
    parser.add_argument(
        '--template_config',
        default='',
        help='json config file'
    )
    parser.add_argument(
        '--store',
        default='',
        help='the store location of the graph definition'
    )
    args = parser.parse_args()
    with open(args.template_config) as json_file:
        config_json = json.load(json_file)
    print (tmp_list)
    assert args.template in tmp_list
    if args.template == 'systolic2x':
        n = config_json['size']
        if (n > 32 ):
            print ('choose a size smaller than  33')
        print ('build graph for '+str(2*n)+'x'+str(2*n) + ' GEMM on ' +str(n)+'x'+str(n)+' systolic array')
        np_b = np.random.random(size=(2*n*2*n,) )
        np_a = np.random.random(size=(2*n*2*n,) )
        graph1 = systolic2x(config_json = config_json, np_a=np_a, np_b=np_b)
    elif args.template == 'systolic1x':
        n = config_json['size']
        if (n > 32 ):
            print ('choose a size smaller than  33')
        print ('build graph for '+str(n)+'x'+str(n) + ' GEMM on ' +str(n)+'x'+str(n)+' systolic array')
        np_b = np.random.random(size=(n*n,) )
        np_a = np.random.random(size=(n*n,) )
        graph1 = systolic1x(config_json = config_json, np_a=np_a, np_b=np_b)
    pickle.dump(graph1, open(args.store, 'wb'))



def main():
    def_graph()

if __name__=='__main__':
    main()