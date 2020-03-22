import argparse
import os
import sys
import copy
import pickle
import _thread
from inso_graph import *
__author__ = 'insomnia.px'


class systolic_vec_read(ip_node):
    def __init__(self, name, inst_req, in_edges_dic, out_edges_dic):
        ip_node.__init__(self, name, inst_req, in_edges_dic, out_edges_dic)
    def exec(self, edge_dic):
        if 'a' in self.out_edges_dic:
            assert 'a' in self.in_edges_dic
            assert 'b' not in self.in_edges_dic
            assert 'b' not in self.out_edges_dic
            name = 'a'
        if 'b' in self.out_edges_dic:
            assert 'b' in self.in_edges_dic
            assert 'a' not in self.in_edges_dic
            assert 'a' not in self.out_edges_dic
            name = 'b'
        edge_dic[self.out_edges_dic[name]].val = copy.deepcopy(edge_dic[self.in_edges_dic[name]].val)

class systolic_array_write(ip_node):
    def __init__(self, name, inst_req,in_edges_dic, out_edges_dic):
        ip_node.__init__(self, name, inst_req, in_edges_dic, out_edges_dic)
    def exec(self, edge_dic):
        edge_dic[self.out_edges_dic['ret']].val = copy.deepcopy(edge_dic[self.in_edges_dic['ret']].val)

class systolic_mac(ip_node):
    def __init__(self, name, inst_req, in_edges_dic, out_edges_dic):
        ip_node.__init__(self, name, inst_req, in_edges_dic, out_edges_dic)
    def exec(self, edge_dic):
        # input: a, b, ret, output: a, b, ret
        if 'a' in self.out_edges_dic:
            edge_dic[self.out_edges_dic['a']].val = copy.deepcopy(edge_dic[self.in_edges_dic['a']].val)
        if 'b' in self.out_edges_dic:
            edge_dic[self.out_edges_dic['b']].val = copy.deepcopy(edge_dic[self.in_edges_dic['b']].val)
        edge_dic[self.out_edges_dic['ret']].val = edge_dic[self.in_edges_dic['ret']].val + edge_dic[self.in_edges_dic['a']].val * edge_dic[self.in_edges_dic['b']].val

class systolic2x(comp_graph):
    def __init__(self, config_json, np_a, np_b): # nxn systolic array for 2nx2n GEMM, divide the 2nx2n output into 4 matrices: top left, top right, bottom left, bottom right
        n = config_json['size']
        inst_dic = {} # {inst_name: inst}
        edge_dic = {} # {edge_name: edge}
        node_dic = {} # {node_name: node}
        graph_in = [] # [edge_name]
        graph_out = [] # [edge_name]
        # configure the hardware libs
        lib1 = hw_lib('./hw_libs/mem_sram_eg.js')
        lib2 = hw_lib('./hw_libs/comp_mul_systolic_eg.js')
        lib3 = hw_lib('./hw_libs/dpath_noc_eg.js')
        # precision settings
        prec_a = fixed_prec(int_bits = config_json['prec_a_int'], frac_bits = config_json['prec_a_frac'], padding_bits = config_json['prec_a_padding'])
        prec_b = fixed_prec(int_bits = config_json['prec_b_int'], frac_bits = config_json['prec_b_frac'], padding_bits = config_json['prec_b_padding'])
        prec_ret = fixed_prec(int_bits = config_json['prec_ret_int'], frac_bits = config_json['prec_ret_frac'], padding_bits = config_json['prec_ret_padding'])
        # set up attributes to access the hardware library
        att_mem = {'tech':config_json['tech'], 'pw':config_json['pw'], 'vol':config_json['bank_vol'], 'freq':config_json['mem_freq']}
        att_mac = {'tech':config_json['tech'], 'num_mul': '1mul', 'prec_in1':str(prec_a.bits)+'bit', 'prec_in2':str(prec_b.bits)+'bit', 'prec_out':str(prec_ret.bits)+'bit', 'freq':config_json['mac_freq']}
        att_dp = {'tech':config_json['tech'], 'pw':config_json['pw'], 'burst_len':config_json['burst_len'], 'freq':config_json['dp_freq']}
        # initialize the hw ips / hw instances
        for i in range(n):
            for j in range(n):
                inst_dic['mac_inst_'+str(i)+'_'+str(j)] = inst(name='mac_inst_'+str(i)+'_'+str(j),
                                                               att=att_mac,
                                                               power_lib = lib2)
                inst_dic['arr_writer_' + str(i)+'_'+str(j)] = inst(name='arr_writer_' + str(i)+'_'+str(j),
                                                                   att=att_dp,
                                                                   power_lib = lib3)
                inst_dic['ret_buf_'+str(i)+'_'+str(j)] = inst(name='ret_buf_'+str(i)+'_'+str(j),
                                                              att = att_mem,
                                                              power_lib = lib1)
        for i in range(n):
            inst_dic['a_buf_'+str(i)] = inst(name='a_buf_'+str(i),
                                             att = att_mem, 
                                             power_lib = lib1) 
            inst_dic['row_reader_'+str(i)] = inst(name='row_reader_'+str(i),
                                                  att=att_dp, 
                                                  power_lib=lib3) 
            inst_dic['b_buf_'+str(i)] = inst(name='b_buf_'+str(i),
                                             att = att_mem,
                                             power_lib = lib1)
            inst_dic['col_reader_'+str(i)] = inst(name='col_reader_'+str(i),
                                                  att=att_dp,
                                                  power_lib=lib3)
        # calculate the inst_list for each node (data movement cycles and computation cycles)
        gbf = str_tran(config_json['glb_freq']).val
        cycles_mem = inst_dic['a_buf_0'].get_cycles_mem(num_dt=1, prec1=prec_a, glb_freq=gbf, static_cycles=0)
        cycles_dp = inst_dic['row_reader_0'].get_cycles_dp(num_dt=1, prec1=prec_a, glb_freq=gbf, static_cycles=0)
        cycles_comp = inst_dic['mac_inst_0_0'].get_cycles_comp(glb_freq=gbf, comp=1, static_cycles=0)
        # init nodes, edges
        for t in range(8*n):
            for i in range(n):
                if t < 2*n:# compute top left
                    rid = i
                    cid = i
                    t_shift = t
                elif t < 4*n:# compute top right
                    rid = i
                    cid = i+n
                    t_shift = t-2*n
                elif t < 6*n:# compute bottom left
                    rid = i+n
                    cid = i
                    t_shift = t-4*n
                else:# compute bottom right
                    rid = i+n
                    cid = i+n
                    t_shift = t-6*n
                row_rd_name = 'row_rd_'+str(i)+'_t'+str(t)
                edge_dic[row_rd_name + '_aout'] = tensor_edge(name=row_rd_name + '_aout',
                                                              addr=addr(data_name = 'a_matrix', np_val=np.array([rid*2*n+t_shift])),
                                                              prec=prec_a)
                edge_dic[row_rd_name + '_ain'] = tensor_edge(name=row_rd_name + '_ain',
                                                                   addr=addr(data_name = 'a_matrix', np_val=np.array([rid*2*n+t_shift])),
                                                                   prec=prec_a,
                                                                   np_val=np.array([np_a[rid*2*n + t_shift]]),
                                                                   ready=True)
                node_dic[row_rd_name] = systolic_vec_read(name=row_rd_name,
                                                          inst_req = OrderedDict({'a_buf_'+str(i):cycles_mem, 'row_reader_'+str(i):cycles_dp }),
                                                          in_edges_dic= {'a': row_rd_name + '_ain'},
                                                          out_edges_dic={'a': row_rd_name + '_aout'})
                graph_in.append(row_rd_name + '_ain')
                col_rd_name = 'col_rd_'+str(i)+'_t'+str(t)
                edge_dic[col_rd_name + '_bout'] = tensor_edge(name=col_rd_name + '_bout',
                                                              addr=addr(data_name = 'b_matrix', np_val=np.array([t_shift*2*n+cid])),
                                                              prec=prec_b)
                edge_dic[col_rd_name + '_bin'] = tensor_edge(name=col_rd_name + '_bin',
                                                             addr=addr(data_name = 'b_matrix', np_val=np.array([t_shift*2*n+cid])),
                                                             prec=prec_b,
                                                             np_val=np.array([np_b[t_shift*2*n + cid]]),
                                                             ready=True)
                node_dic[col_rd_name] = systolic_vec_read(name = col_rd_name,
                                                          inst_req = OrderedDict({'b_buf_'+str(i):cycles_mem, 'col_reader_'+str(i):cycles_dp }),
                                                          in_edges_dic= {'b': col_rd_name + '_bin'},
                                                          out_edges_dic={'b': col_rd_name + '_bout'})
                graph_in.append(col_rd_name + '_bin')
        for t in range(8*n):
            if (t%6==0 or t==8*n-1):
                print ('building the graph '+ str(float(t+1)/(8*n)*100)+'%')
            for i in range(n):
                for j in range(n):
                    if t < 2*n: # compute the top left
                        rid = i
                        cid = j
                        t_shift = t
                    elif t < 4*n: # compute the top right
                        rid = i
                        cid = j+n
                        t_shift = t-2*n
                    elif t < 6*n: # compute the bottom left
                        rid = i+n
                        cid = j
                        t_shift = t-4*n
                    else: # compute the bottom right
                        rid = i+n
                        cid = j+n
                        t_shift = t-6*n
                    mac_name = 'mac_'+str(i)+'_'+str(j)+'_t'+str(t)
                    edge_dic[mac_name+'_retout'] = tensor_edge(name=mac_name+'_retout',
                                                               addr=addr(data_name='ret_matrix', np_val=np.array([rid*2*n+cid])),
                                                               prec=prec_ret)
                    mac_out_edges = {'ret':mac_name+'_retout'}
                    if j < n-1:
                        edge_dic[mac_name + '_aout'] = tensor_edge(name=mac_name + '_aout',
                                                                   addr=addr(data_name='a_matrix', np_val=np.array([rid*2*n+t_shift])),
                                                                   prec=prec_a)
                        mac_out_edges['a'] = mac_name + '_aout'
                    if i < n-1:
                        edge_dic[mac_name+'_bout'] = tensor_edge(name=mac_name+'_bout',
                                                                 addr=addr(data_name='b_matrix', np_val=np.array([t_shift*2*n+cid])),
                                                                 prec=prec_b)
                        mac_out_edges['b'] = mac_name+'_bout'
                    if t==0 or t==2*n or t==4*n or t==6*n:
                        edge_dic[mac_name+'_retin'] = tensor_edge(name=mac_name+'_retin',
                                                                  addr=addr(data_name='ret_matrix', np_val=np.array([rid*2*n+cid])),
                                                                  prec=prec_ret,
                                                                  np_val=np.array([0]),
                                                                  ready=True)
                        ret_in = mac_name+'_retin'
                        graph_in.append(ret_in)
                    else:
                        ret_in = 'mac_'+str(i)+'_'+str(j)+'_t'+str(t-1)+'_retout'
                    if j==0:
                        a_in = 'row_rd_'+str(i)+'_t'+str(t)+'_aout'
                    else:
                        a_in = 'mac_'+str(i)+'_'+str(j-1)+'_t'+str(t) + '_aout'
                    if i==0:
                        b_in = 'col_rd_'+str(j)+'_t'+str(t)+'_bout'
                    else:
                        b_in = 'mac_'+str(i-1)+'_'+str(j)+'_t'+str(t) + '_bout'
                    node_dic[mac_name] = systolic_mac(name=mac_name,
                                                      inst_req = OrderedDict({'mac_inst_'+str(i)+'_'+str(j):cycles_comp}),
                                                      in_edges_dic={'a':a_in, 'b':b_in, 'ret':ret_in},
                                                      out_edges_dic=mac_out_edges)
                    wt_name = 'arr_wt_' + str(i) + '_'+ str(j)+'_t'+str(t)
                    if t==2*n-1 or t==4*n-1 or t==6*n-1 or t==8*n-1:
                        edge_dic[wt_name + '_retout'] = tensor_edge(name=wt_name + '_retout',
                                                                    addr=addr(data_name='ret_matrix',np_val=np.array([rid*2*n+cid])),
                                                                    prec=prec_ret)
                        node_dic[wt_name] = systolic_array_write(name=wt_name,
                                                                 inst_req = OrderedDict({'arr_writer_' + str(i)+'_'+str(j):cycles_dp, 'ret_buf_'+str(i)+'_'+str(j):cycles_mem}),
                                                                 in_edges_dic={'ret':mac_name+'_retout'},
                                                                 out_edges_dic={'ret':wt_name + '_retout'})
                        graph_out.append(wt_name + '_retout')
        self.np_a = np_a
        self.np_b = np_b
        self.n = n
        comp_graph.__init__(self, config_json, inst_dic, edge_dic, node_dic, graph_in, graph_out)
    def get_graphout(self):
        np_ret = np.zeros((2*self.n*2*self.n,))
        for name in self.edge_dic:
            if (name not in self.graph_out):
                continue
            if (not self.edge_dic[name].ready):
                continue
            np_ret[self.edge_dic[name].addr.val[0]] = self.edge_dic[name].val[0]
        return np_ret
    def sim_inter_ip_pipeline(self,sim_cycles=float('inf')):
        ret = comp_graph.sim_inter_ip_pipeline(self, sim_cycles)
        np_ret = self.get_graphout().reshape((2*self.n,2*self.n))
        print ('\ngenerated matrix output')
        print (np_ret)
        print ('\nexpected matrix output')
        print (self.np_a.reshape((2*self.n, 2*self.n)).dot(self.np_b.reshape((2*self.n,2*self.n))))
        return ret


class systolic1x(comp_graph):
    def __init__(self, config_json, np_a, np_b): # nxn systolic array for 2nx2n GEMM, divide the 2nx2n output into 4 matrices: top left, top right, bottom left, bottom right
        n = config_json['size']
        inst_dic = {} # {inst_name: inst}
        edge_dic = {} # {edge_name: edge}
        node_dic = {} # {node_name: node}
        graph_in = [] # [edge_name]
        graph_out = [] # [edge_name]
        # configure the hardware libs
        lib1 = hw_lib('./hw_libs/mem_sram_eg.js')
        lib2 = hw_lib('./hw_libs/comp_mul_systolic_eg.js')
        lib3 = hw_lib('./hw_libs/dpath_noc_eg.js')
        # precision settings
        prec_a = fixed_prec(int_bits = config_json['prec_a_int'], frac_bits = config_json['prec_a_frac'], padding_bits = config_json['prec_a_padding'])
        prec_b = fixed_prec(int_bits = config_json['prec_b_int'], frac_bits = config_json['prec_b_frac'], padding_bits = config_json['prec_b_padding'])
        prec_ret = fixed_prec(int_bits = config_json['prec_ret_int'], frac_bits = config_json['prec_ret_frac'], padding_bits = config_json['prec_ret_padding'])
        # set up attributes to access the hardware library
        att_mem = {'tech':config_json['tech'], 'pw':config_json['pw'], 'vol':config_json['bank_vol'], 'freq':config_json['mem_freq']}
        att_mac = {'tech':config_json['tech'], 'num_mul': '1mul', 'prec_in1':str(prec_a.bits)+'bit', 'prec_in2':str(prec_b.bits)+'bit', 'prec_out':str(prec_ret.bits)+'bit', 'freq':config_json['mac_freq']}
        att_dp = {'tech':config_json['tech'], 'pw':config_json['pw'], 'burst_len':config_json['burst_len'], 'freq':config_json['dp_freq']}
        # initialize the hw ips / hw instances
        for i in range(n):
            for j in range(n):
                inst_dic['mac_inst_'+str(i)+'_'+str(j)] = inst(name='mac_inst_'+str(i)+'_'+str(j),
                                                               att=att_mac,
                                                               power_lib = lib2)
                inst_dic['arr_writer_' + str(i)+'_'+str(j)] = inst(name='arr_writer_' + str(i)+'_'+str(j),
                                                                   att=att_dp,
                                                                   power_lib = lib3)
                inst_dic['ret_buf_'+str(i)+'_'+str(j)] = inst(name='ret_buf_'+str(i)+'_'+str(j),
                                                              att = att_mem,
                                                              power_lib = lib1)
        for i in range(n):
            inst_dic['a_buf_'+str(i)] = inst(name='a_buf_'+str(i),
                                             att = att_mem, 
                                             power_lib = lib1) 
            inst_dic['row_reader_'+str(i)] = inst(name='row_reader_'+str(i),
                                                  att=att_dp, 
                                                  power_lib=lib3) 
            inst_dic['b_buf_'+str(i)] = inst(name='b_buf_'+str(i),
                                             att = att_mem,
                                             power_lib = lib1)
            inst_dic['col_reader_'+str(i)] = inst(name='col_reader_'+str(i),
                                                  att=att_dp,
                                                  power_lib=lib3)
        # calculate the inst_list for each node (data movement cycles and computation cycles)
        gbf = str_tran(config_json['glb_freq']).val
        cycles_mem = inst_dic['a_buf_0'].get_cycles_mem(num_dt=1, prec1=prec_a, glb_freq=gbf, static_cycles=0)
        cycles_dp = inst_dic['row_reader_0'].get_cycles_dp(num_dt=1, prec1=prec_a, glb_freq=gbf, static_cycles=0)
        cycles_comp = inst_dic['mac_inst_0_0'].get_cycles_comp(glb_freq=gbf, comp=1, static_cycles=0)
        # init nodes, edges
        for t in range(n):
            for i in range(n):
                rid = i
                cid = i
                t_shift = t
                row_rd_name = 'row_rd_'+str(i)+'_t'+str(t)
                edge_dic[row_rd_name + '_aout'] = tensor_edge(name=row_rd_name + '_aout',
                                                              addr=addr(data_name = 'a_matrix', np_val=np.array([rid*n+t_shift])),
                                                              prec=prec_a)
                edge_dic[row_rd_name + '_ain'] = tensor_edge(name=row_rd_name + '_ain',
                                                                   addr=addr(data_name = 'a_matrix', np_val=np.array([rid*n+t_shift])),
                                                                   prec=prec_a,
                                                                   np_val=np.array([np_a[rid*n + t_shift]]),
                                                                   ready=True)
                node_dic[row_rd_name] = systolic_vec_read(name=row_rd_name,
                                                          inst_req = OrderedDict({'a_buf_'+str(i):cycles_mem, 'row_reader_'+str(i):cycles_dp }),
                                                          in_edges_dic= {'a': row_rd_name + '_ain'},
                                                          out_edges_dic={'a': row_rd_name + '_aout'})
                graph_in.append(row_rd_name + '_ain')
                col_rd_name = 'col_rd_'+str(i)+'_t'+str(t)
                edge_dic[col_rd_name + '_bout'] = tensor_edge(name=col_rd_name + '_bout',
                                                              addr=addr(data_name = 'b_matrix', np_val=np.array([t_shift*n+cid])),
                                                              prec=prec_b)
                edge_dic[col_rd_name + '_bin'] = tensor_edge(name=col_rd_name + '_bin',
                                                             addr=addr(data_name = 'b_matrix', np_val=np.array([t_shift*n+cid])),
                                                             prec=prec_b,
                                                             np_val=np.array([np_b[t_shift*n + cid]]),
                                                             ready=True)
                node_dic[col_rd_name] = systolic_vec_read(name = col_rd_name,
                                                          inst_req = OrderedDict({'b_buf_'+str(i):cycles_mem, 'col_reader_'+str(i):cycles_dp }),
                                                          in_edges_dic= {'b': col_rd_name + '_bin'},
                                                          out_edges_dic={'b': col_rd_name + '_bout'})
                graph_in.append(col_rd_name + '_bin')
        for t in range(n):
            if (t%3==0 or t==n-1):
                print ('building the graph '+ str(float(t+1)/(n)*100)+'%')
            for i in range(n):
                for j in range(n):
                    rid = i
                    cid = j
                    t_shift = t
                    mac_name = 'mac_'+str(i)+'_'+str(j)+'_t'+str(t)
                    edge_dic[mac_name+'_retout'] = tensor_edge(name=mac_name+'_retout',
                                                               addr=addr(data_name='ret_matrix', np_val=np.array([rid*n+cid])),
                                                               prec=prec_ret)
                    mac_out_edges = {'ret':mac_name+'_retout'}
                    if j < n-1:
                        edge_dic[mac_name + '_aout'] = tensor_edge(name=mac_name + '_aout',
                                                                   addr=addr(data_name='a_matrix', np_val=np.array([rid*n+t_shift])),
                                                                   prec=prec_a)
                        mac_out_edges['a'] = mac_name + '_aout'
                    if i < n-1:
                        edge_dic[mac_name+'_bout'] = tensor_edge(name=mac_name+'_bout',
                                                                 addr=addr(data_name='b_matrix', np_val=np.array([t_shift*n+cid])),
                                                                 prec=prec_b)
                        mac_out_edges['b'] = mac_name+'_bout'
                    if t==0:
                        edge_dic[mac_name+'_retin'] = tensor_edge(name=mac_name+'_retin',
                                                                  addr=addr(data_name='ret_matrix', np_val=np.array([rid*n+cid])),
                                                                  prec=prec_ret,
                                                                  np_val=np.array([0]),
                                                                  ready=True)
                        ret_in = mac_name+'_retin'
                        graph_in.append(ret_in)
                    else:
                        ret_in = 'mac_'+str(i)+'_'+str(j)+'_t'+str(t-1)+'_retout'
                    if j==0:
                        a_in = 'row_rd_'+str(i)+'_t'+str(t)+'_aout'
                    else:
                        a_in = 'mac_'+str(i)+'_'+str(j-1)+'_t'+str(t) + '_aout'
                    if i==0:
                        b_in = 'col_rd_'+str(j)+'_t'+str(t)+'_bout'
                    else:
                        b_in = 'mac_'+str(i-1)+'_'+str(j)+'_t'+str(t) + '_bout'
                    node_dic[mac_name] = systolic_mac(name=mac_name,
                                                      inst_req = OrderedDict({'mac_inst_'+str(i)+'_'+str(j):cycles_comp}),
                                                      in_edges_dic={'a':a_in, 'b':b_in, 'ret':ret_in},
                                                      out_edges_dic=mac_out_edges)
                    wt_name = 'arr_wt_' + str(i) + '_'+ str(j)+'_t'+str(t)
                    if t==n-1:
                        edge_dic[wt_name + '_retout'] = tensor_edge(name=wt_name + '_retout',
                                                                    addr=addr(data_name='ret_matrix',np_val=np.array([rid*n+cid])),
                                                                    prec=prec_ret)
                        node_dic[wt_name] = systolic_array_write(name=wt_name,
                                                                 inst_req = OrderedDict({'arr_writer_' + str(i)+'_'+str(j):cycles_dp, 'ret_buf_'+str(i)+'_'+str(j):cycles_mem}),
                                                                 in_edges_dic={'ret':mac_name+'_retout'},
                                                                 out_edges_dic={'ret':wt_name + '_retout'})
                        graph_out.append(wt_name + '_retout')
        self.np_a = np_a
        self.np_b = np_b
        self.n = n
        comp_graph.__init__(self, config_json, inst_dic, edge_dic, node_dic, graph_in, graph_out)
    def get_graphout(self):
        np_ret = np.zeros((self.n*self.n,))
        for name in self.edge_dic:
            if (name not in self.graph_out):
                continue
            if (not self.edge_dic[name].ready):
                continue
            np_ret[self.edge_dic[name].addr.val[0]] = self.edge_dic[name].val[0]
        return np_ret
    def sim_inter_ip_pipeline(self,sim_cycles=float('inf')):
        ret = comp_graph.sim_inter_ip_pipeline(self, sim_cycles)
        np_ret = self.get_graphout().reshape((self.n,self.n))
        print ('\ngenerated matrix output')
        print (np_ret)
        print ('\nexpected matrix output')
        print (self.np_a.reshape((self.n, self.n)).dot(self.np_b.reshape((self.n,self.n))))
        return ret
