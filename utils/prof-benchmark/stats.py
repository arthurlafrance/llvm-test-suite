# what info needs to be displayed for the benchmarks?
    # comparative box plots of the 3 options (base, llvm, mip) at any given opt level (eg Oz)
    # line graph of avg of various metrics of the 3 options across different opt levels
    # stats about differences between options, eg "avg mip binary size was 30% less than llvm"

from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path
from matplotlib import pyplot as plt

import sys
import json
import numpy as np

# save to files in the following format within results/:
    # box plots: boxplots/box-<opt level>.png, eg boxplots/box-Oz.png for each opt level
    # line graphs: graphs/<metric>.png
    # stats text: stats.txt

class Metric:
    BIN_SIZE = 'bin_size'
    TEXT_SIZE = 'text_size'
    DATA_SIZE = 'data_size'
    INSTR_DATA_SIZE = 'instr_data_size'
    ADJUSTED_BIN_SIZE = 'adjusted_bin_size'
    ALL = [BIN_SIZE, TEXT_SIZE, DATA_SIZE, INSTR_DATA_SIZE, ADJUSTED_BIN_SIZE]

def get_default_filename(opt_level: str, prof_method: str) -> str:
    return f'./{opt_level}/results-{prof_method}.json'

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--format', '-f', help='the text format in which to show results', default='txt') # txt, json

    args = parser.parse_args()

    opt_levels = ['Os', 'Oz'] # ['O3', 'Os', 'Oz']
    prof_methods = ['base', 'llvm', 'mip']
    benchmarks = {}

    for opt_level in opt_levels:
        benchmarks[opt_level] = {}

        for prof_method in prof_methods:
            result_filename = get_default_filename(opt_level, prof_method)
            result_file = open(result_filename)
            result_json = json.load(result_file)['tests'] # get benchmark results

            bin_sizes = np.zeros((len(result_json),))
            text_sizes = np.zeros((len(result_json),))
            data_sizes = np.zeros((len(result_json),))
            instr_data_sizes = np.zeros((len(result_json),))
            adjusted_bin_sizes = np.zeros((len(result_json),))

            for i, test in enumerate(result_json):
                metrics = defaultdict(int, test['metrics'])

                total_bin_size = metrics['size']
                text_size = metrics['size.__text']
                data_size = metrics['size.__data']

                if prof_method == 'mip':
                    odrcovmap_size = metrics['size.__llvm_odrcovmap']
                    adjusted_bin_size = total_bin_size - odrcovmap_size

                    instr_data_size = metrics['size.__llvm_odrcovraw']
                else:
                    adjusted_bin_size = total_bin_size

                    if prof_method == 'llvm':
                        instr_data_size = metrics['size.__llvm_prf_cnts'] + metrics['size.__llvm_prf_data']  \
                                        + metrics['size.__llvm_prf_names'] + metrics['size.__llvm_prf_vals'] \
                                        + metrics['size.__llvm_prf_vnds']
                    else:
                        instr_data_size = 0

                bin_sizes[i] = total_bin_size
                text_sizes[i] = text_size
                data_sizes[i] = data_size
                instr_data_sizes[i] = instr_data_size
                adjusted_bin_sizes[i] = adjusted_bin_size

            benchmarks[opt_level][prof_method] = {
                Metric.BIN_SIZE : bin_sizes,
                Metric.TEXT_SIZE : text_sizes,
                Metric.DATA_SIZE : data_sizes,
                Metric.INSTR_DATA_SIZE : instr_data_sizes,
                Metric.ADJUSTED_BIN_SIZE : adjusted_bin_sizes,
            }

    results_dir = Path('results')
    results_dir.mkdir(parents=True, exist_ok=True)

    fmt = args.format

    outfile_path = results_dir / f'stats.{fmt}'
    avgs = { opt_level : { prof_method : {} for prof_method in prof_methods } for opt_level in opt_levels }

    with outfile_path.open(mode='w') as outfile:
        if fmt == 'txt':
            for metric in Metric.ALL:
                outfile.write(f'{metric}:\n')

                for opt_level in opt_levels:
                    outfile.write(f'\t{opt_level}:\n')

                    for prof_method in prof_methods:
                        outfile.write(f'\t\t{prof_method}:\n')

                        data = benchmarks[opt_level][prof_method][metric]

                        avg = np.average(data)
                        min_val = np.min(data)
                        max_val = np.max(data)
                        std = np.std(data)

                        avgs[opt_level][prof_method][metric] = avg
                        outfile.write(f'\t\t\tavg: {avg}\n\t\t\tstd: {std}\n\t\t\tmin: {min_val}\n\t\t\tmax: {max_val}\n')
        else: # fmt == 'json'
            # { metric : { opt_level : { prof_method : { statistic : value, ... }, ... }, ... }
            outfile.write('{ ')

            for metric in Metric.ALL:
                outfile.write(f'"{metric}" : {{ ')

                for opt_level in opt_levels:
                    outfile.write(f'"{opt_level}" : {{')

                    for prof_method in prof_methods:
                        outfile.write(f'"{prof_method}" : {{')

                        data = benchmarks[opt_level][prof_method][metric]

                        avg = np.average(data)
                        min_val = np.min(data)
                        max_val = np.max(data)
                        std = np.std(data)

                        avgs[opt_level][prof_method][metric] = avg
                        outfile.write(f'"avg" : {avg}, "std" : {std}, "min" : {min_val}, "max" : {max_val} }}, ')
                    outfile.write(' }, ')
                outfile.write(' }, ')
            outfile.write(' }')

    print(avgs)

    # line graphs, one per metric, avg only
    graphs_dir = results_dir / 'graphs'
    graphs_dir.mkdir(parents=True, exist_ok=True)
    
    for metric in Metric.ALL:
        # TODO: better formatting, including title & other stuff like legend
        plt.title(f'{metric} by Profile Type Across Optimization Levels (O3 -> Os -> Oz)')

        for prof_method in prof_methods:
            data = np.zeros((len(opt_levels),))

            for i, opt_level in enumerate(opt_levels):
                data[i] = avgs[opt_level][prof_method][metric]

            # print(metric, prof_method, opt_level, data)
            plt.plot(data, label=prof_method)

        # finish + save plot
        plt.legend()
        plt.savefig(graphs_dir / f'{metric}.png')
        plt.clf()

    # box plots, one per opt-level
