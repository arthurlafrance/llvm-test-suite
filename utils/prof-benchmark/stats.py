from collections import defaultdict
from pathlib import Path

import sys
import json
import numpy as np

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
    opt_levels = ['O3', 'Oz']
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

    data_dir = Path('data')
    data_dir.mkdir(parents=True, exist_ok=True)

    for metric in Metric.ALL:
        data_file = data_dir / f'{metric}.csv'

        with data_file.open('w') as f:
            f.write('Optimization Level,Base,LLVM,MIP\n')

            for opt_level in opt_levels:
                avgs = []

                for prof_method in prof_methods:
                    data = benchmarks[opt_level][prof_method][metric]
                    avg = np.average(data)
                    avgs.append(str(avg))
                
                data_str = ','.join(avgs)
                f.write(f'{opt_level},{data_str}\n')

    # how should csv data be formatted?
        # what will it be used for?
            # calculating stats by prof method, opt level, and metric (avg, min/max, etc)
            # plot avg per metric & prof method by opt level
            # basically all i need is the average of any given configuration of (opt level, prof method, metric)
        # format:
            # <prof method>,<opt level>,<metric>,values














