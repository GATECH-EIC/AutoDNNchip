import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_graph import *
import json
__author__ = 'insomnia.px'


def def_conv():
    parser = argparse.ArgumentParser(description='Build a graph for 2D conv (stride=1, no padding) using chip predictor')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--store',
        default='',
        help='the store location of the graph definition'
    )
    args = parser.parse_args()
    chin = 16
    chout = 64
    ksize = 3
    isize = 4
    osize = isize - ksize + 1
    npi = np.random.random(size=(chin*isize*isize,) )
    npw = np.random.random(size=(chout*chin*ksize*ksize,) )
    npo = np.zeros((chout*osize*osize,) )
    #define hw libs, change jason file into your own depending on your targeted hardware
    lib1 = hw_lib('./hw_libs/mem_sram_eg.js')
    lib2 = hw_lib('./hw_libs/dpath_noc_eg.js')
    lib3 = hw_lib('./hw_libs/comp_mul_adtree_eg.js')
    #configurations
    inst_dic = {}
    node_dic = {}
    edge_dic = {}
    graph_in = []
    graph_out = []
    config_json = {'tech':'65nm', 'sram_pw':'8bit', 'ivol':'1KB', 'ovol':'1KB', 'wvol':'32KB', 'mul':'256mul', 'iprec':'16bit','wprec':'16bit','oprec':'16bit', 'glb_freq':'1000MHz'}
    #define hw ips
    inst_ibuf = inst(name='ibuf', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'], 'vol':config_json['ivol'], 'freq':config_json['glb_freq']}, power_lib=lib1)
    inst_obuf = inst(name='obuf', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'], 'vol':config_json['ovol'], 'freq':config_json['glb_freq']}, power_lib=lib1)
    inst_wbuf = inst(name='wbuf', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'], 'vol':config_json['wvol'], 'freq':config_json['glb_freq']}, power_lib=lib1)
    inst_inoc = inst(name='inoc', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'],'burst_len':'1data','freq':config_json['glb_freq']}, power_lib=lib2)
    inst_onoc = inst(name='onoc', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'],'burst_len':'1data','freq':config_json['glb_freq']}, power_lib=lib2)
    inst_wnoc = inst(name='wnoc', att={'tech':config_json['tech'], 'pw':config_json['sram_pw'],'burst_len':'1data','freq':config_json['glb_freq']}, power_lib=lib2)
    inst_pe = inst(name='pe', att={'tech':config_json['tech'], 'num_mul':config_json['mul'], 'prec_in1':config_json['iprec'], 'prec_in2':config_json['wprec'], 'prec_out':config_json['oprec'], 'freq':config_json['glb_freq']}, power_lib=lib3)
    #calculate cycles
    gbf = str_tran(config_json['glb_freq']).val
    preci = fixed_prec(int_bits=5,frac_bits=10,padding_bits=0)
    precw = fixed_prec(int_bits=5,frac_bits=10,padding_bits=0)
    preco = fixed_prec(int_bits=9,frac_bits=6,padding_bits=0)
    memi = inst_ibuf.get_cycles_mem(num_dt=chin*isize*isize, prec1=preci, glb_freq=gbf)
    dpi = inst_inoc.get_cycles_dp(num_dt=chin*isize*isize, prec1=preci, glb_freq=gbf)
    memw = inst_wbuf.get_cycles_mem(num_dt=chout*chin*ksize*ksize, prec1=precw, glb_freq=gbf)
    dpw = inst_wnoc.get_cycles_dp(num_dt=chout*chin*ksize*ksize, prec1=precw, glb_freq=gbf)
    memo = inst_obuf.get_cycles_mem(num_dt=chout*osize*osize, prec1=preco, glb_freq=gbf)
    dpo = inst_onoc.get_cycles_dp(num_dt=chout*osize*osize, prec1=preco, glb_freq=gbf)
    cycles_comp = inst_pe.get_cycles_comp(glb_freq=gbf, comp=int(chout*chin*osize*osize*ksize*ksize/str_tran(config_json['mul']).val) )
    #define edges
    ei_buf = tensor_edge(name='ei_buf', addr=addr(data_name='input', np_val=np.arange(chin*isize*isize)), prec=preci, np_val=npi, ready=True)
    ei_pe = tensor_edge(name='ei_pe', addr=addr(data_name='input', np_val=np.arange(chin*isize*isize)), prec=preci)
    ew_buf = tensor_edge(name='ew_buf', addr=addr(data_name='weight', np_val=np.arange(chout*chin*ksize*ksize)), prec=precw, np_val=npw, ready=True)
    ew_pe = tensor_edge(name='ew_pe', addr=addr(data_name='weight', np_val=np.arange(chout*chin*ksize*ksize)), prec=precw)
    eo_pe = tensor_edge(name='eo_pe', addr=addr(data_name='output', np_val=np.arange(chout*osize*osize)), prec=preco, np_val=np.zeros((chout*osize*osize,)))
    eo_buf = tensor_edge(name='eo_buf', addr=addr(data_name='output', np_val=np.arange(chout*osize*osize)), prec=preco)
    #define nodes
    readi = eg_dm(name='readi', inst_req=OrderedDict({'ibuf':memi, 'inoc':dpi}), in_edges_dic={'buf':'ei_buf'}, out_edges_dic={'pe':'ei_pe'})
    readw = eg_dm(name='readw', inst_req=OrderedDict({'wbuf':memw, 'wnoc':dpw}), in_edges_dic={'buf':'ew_buf'}, out_edges_dic={'pe':'ew_pe'})
    comp = eg_conv(name='comp', inst_req=OrderedDict({'pe':cycles_comp}), in_edges_dic={'i':'ei_pe','w':'ew_pe'}, out_edges_dic={'o':'eo_pe'}, chin=chin, chout=chout, osize=osize, ksize=ksize, isize=isize)
    writeo = eg_dm(name='writeo', inst_req=OrderedDict({'onoc':dpo, 'obuf':memo}), in_edges_dic={'pe':'eo_pe'}, out_edges_dic={'buf':'eo_buf'})
    #define graph1
    graph1 = comp_graph(config_json=config_json, inst_dic={'ibuf':inst_ibuf, 'inoc':inst_inoc}, edge_dic={'ei_buf':ei_buf, 'ei_pe':ei_pe}, node_dic={'readi':readi}, graph_in=['ei_buf'],graph_out=['ei_pe'])
    #define graph2
    graph2 = comp_graph(config_json=config_json, inst_dic={'wbuf':inst_wbuf, 'wnoc':inst_wnoc}, edge_dic={'ew_buf':ew_buf, 'ew_pe':ew_pe}, node_dic={'readw':readw}, graph_in=['ew_buf'],graph_out=['ew_pe'])
    #define graph3
    graph3 = comp_graph(config_json=config_json, inst_dic={'obuf':inst_obuf, 'onoc':inst_onoc, 'pe': inst_pe}, edge_dic={'ei_pe':ei_pe,'ew_pe':ew_pe,'eo_pe':eo_pe,'eo_buf':eo_buf}, node_dic={'comp':comp,'writeo':writeo}, graph_in=['ei_pe','ew_pe'], graph_out=['eo_buf'])
    #connect 3 graphs together
    graph = graph1.connect_to(graph2.connect_to(graph3))
    pickle.dump(graph, open(args.store, 'wb'))

def main():
    def_conv()

if __name__=='__main__':
    main()