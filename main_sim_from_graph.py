import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_graph import *
__author__ = 'insomnia.px'

def sim():
    parser = argparse.ArgumentParser(description='simulate a graph (i.e., Fine-grained mode of Chip Predictor)')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--graph_def',
        default=None,
        help='one-for-all graph description'
    )
    args = parser.parse_args()

    graph_name = args.graph_def
    graph1 = pickle.load(open(graph_name, 'rb'))
    print ('\nWorkload visualization graph'+'-'*60 + '\n')
    graph1.sw_graph_gen()
    print (graph1.graph_in)
    print (graph1.graph_out)
    print_dict(graph1.graph)
    # print_dict(graph1.graph_inv)
    print ('\nHardware architecture graph (interconnection of IPs) '+'-'*60 + '\n')
    graph1.hw_graph_gen()
    print_dict(graph1.next_inst)
    # print_dict(graph1.prev_inst)
    print ('\nWorkload to architecture mapping dictionary '+'-'*60 + '\n')
    graph1.mpdict_gen()
    print_dict(graph1.mp_dict)
    # cycle-by-cycle simulation log
    print ('\nSimulation log '+'-'*60 + '\n')
    cycles = graph1.sim_inter_ip_pipeline()
    # graph1.sim_inter_ip_pipeline(sim_cycles=18)
    # post sim logs
    print ('\nPost simulation log '+'-'*60 + '\n')
    graph1.post_sim_log()


def main():
    sim()

if __name__=='__main__':
    main()