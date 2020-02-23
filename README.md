# AutoDNNchip

**AutoDNNchip is published as a conference paper at [FPGA'20].**

Python version: 3.7

---

## Preparation

First download the released executable files according to your OS from https://1drv.ms/u/s!AkwSS-sbuRotg2EVxwfYMUj5DD06?e=pZgRy0.

Then create the conda environment based on conda_env.yml.

## Generate a graph definition based on existing hardware architectures

```
$ ./def_graph_systolic --template systolic_template_name --size systolic_array_size
```

An example:
```
$ ./def_graph_systolic --template systolic2x --size 3
```
## Run the simulation of Chip Predictor based on graph definition
```
$ ./chip_predictor --graph_def graph_def_file | tee log_file
```
An example:
```
$ ./chip_predictor --graph_def graph_defs/systolic2x_3x3.graph | tee logs/systolic_3x3_6x6.log
```


