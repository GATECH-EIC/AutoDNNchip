# AutoDNNchip
This is a Python implementation of the conference paper **[AutoDNNchip: An Automated DNN Chip Predictor and Builder for Both FPGAs and ASICs](https://arxiv.org/abs/2001.03535)** at **[FPGA'20](http://isfpga.org/).**

Chip Predictor requirement: Python 3.6 (conda environment based on conda_env.yml).

AutoDNNchip Generated FPGA design requirement: [Xilinx Ultra96 FPGA](https://www.xilinx.com/products/boards-and-kits/1-vad4rl.html).


## Preparation

Add your hardware library to ./hw_libs.

## Generate a graph definition based on templates or from scratch

Change the hardware configuration files ./template_config and generate a graph based on graph templates. An example:
```
$ python main_def_graph_from_template.py --template systolic2x --template_config template_config/systolic2x_3.js --store graph_defs/systolic2x_3x3.graph
```
Or build a graph definition from scratch. An example:
```
$ python main_def_graph_from_scratch.py --store graph_defs/conv_eg.graph
```

## Run the cycle by cycle simulation of Chip Predictor based on graph definition
```
$ python main_sim_from_graph.py --graph_def graph_def_file | tee log_file
```
An example:
```
$ python main_sim_from_graph.py --graph_def graph_defs/conv_eg.graph | tee logs/conv_eg.log
```

## Run the optimized design on Ultra96 FPGA
We compare our optimized FPGA design with the champaign-winning design in [the 56th IEEE/ACM Design Automation Conference System Design Contest (DAC-SDC)](http://www.cse.cuhk.edu.hk/~byu/2019-DAC-SDC/index.html). To run the baseline design and our optimized design, first download the sampled [test images](https://1drv.ms/u/s!AkwSS-sbuRotg3IZkH_AjRExkZGL?e=8BdHxf), copy the ./optimized_ultra96 to your FPGA, then run:
```
$ sudo python3 main.py --option optimized
```
and
```
$ sudo python3 main.py --option baseline
```

## Publication

If you use this github repo, please cite our [FPGA'20 paper](https://arxiv.org/abs/2001.03535):
```
@article{xu2020autodnnchip,
  title={AutoDNNchip: An Automated DNN Chip Predictor and Builder for Both FPGAs and ASICs},
  author={Xu, Pengfei and Zhang, Xiaofan and Hao, Cong and Zhao, Yang and Zhang, Yongan and Wang, Yue and Li, Chaojian and Guan, Zetong and Chen, Deming and Lin, Yingyan},
  journal={Int'l Symp. on Field-Programmable Gate Arrays (FPGA)},
  year={2020}
}
```
## Acknowledgement
* The FPGA implementation is inspired by [SkyNet](https://github.com/TomG008/SkyNet).
