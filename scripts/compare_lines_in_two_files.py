"""
Objectives
----------
Get lines with certain strings from pair text files, i.e. Citrix ADC inspection log files,
and compare them to find if the two files have different config lines in them.

Takes
-----
a path to a directory that has running configs
a csv file that pairs two devices to compare their config lines

Returns
-------
file : csv format with comma delimiter
This file contains those lines that are different between the pairs.

Raises
------

Warning
-------

"""
#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path
import sys

##### global variables ########################################################
new_line = '\n'
file_extension = '.log'
#file_extension = '.conf'

config_group = {'service':{'pattern_to_extract':['add service ','bind service '], 'file_suffix':'.services'},
                'service_group':{'pattern_to_extract':['add serviceGroup','bind serviceGroup'], 'file_suffix':'.servicegrp'},
                'lb_vserver':{'pattern_to_extract':['add lb vserver','bind lb vserver'], 'file_suffix':'.lbvs'},
                'ssl_vserver':{'pattern_to_extract':['set ssl vserver','bind ssl vserver'], 'file_suffix':'.sslvs'},
                'ssl_profile':{'pattern_to_extract':['add ssl profile','bind ssl profile'], 'file_suffix':'.sslprofile'},
                'ssl_certkey':{'pattern_to_extract':['add ssl certKey','link ssl certKey'], 'file_suffix':'.sslkey'}
                }

class CmdLine:
    default_suffix = '.services'
    default_pairs = 'devices_in_pairs.csv'

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('dir_path', type=str, help="a path to the directory")
        parser.add_argument("-s", "--suffix", type=str, help = "a suffix string for the output files", required = False, default = self.default_suffix)
        parser.add_argument("-p", "--pairs", type=str, help = "a csv file with pair devices", required = False, default = self.default_pairs)
        self.args=parser.parse_args()
    def get_args(self):
        return self.args

def extract_lines(input_file, pattern_to_match: list, output_path):
    with open(input_file, 'r') as file, open(output_path, 'w', newline='') as output_file:
        # read the contents of the files into a sorted list, removing trailing newlines
        #file_lines = sorted(line for line in file if pattern_to_match in line)
        print("pattern to match : ", pattern_to_match)
        file_lines = sorted(line for line in file if any(x in line for x in pattern_to_match)) ### This needs to be sorted
        # write the unique lines to a text file
        output_file.writelines(file_lines)

def compare_lines(pair_files: list, file_path):
    no_line = ''
    different_lines = dict()
    different_lines['devices'] = (pair_files[0], pair_files[1])
    for section in config_group:
        file1 = Path(file_path, pair_files[0]+file_extension).with_suffix(config_group[section]['file_suffix'])
        file2 = Path(file_path, pair_files[1]+file_extension).with_suffix(config_group[section]['file_suffix'])
        
        file1_obj, file2_obj = open(file1, "r"), open(file2, "r")
        file1_data = file1_obj.read().split(new_line)
        file2_data = file2_obj.read().split(new_line)
        file1_obj.close
        file2_obj.close
        len_file1, len_file2 = len(file1_data), len(file2_data)
        i, j = 0, 0
        different_lines[section] = []
        while len_file1 - i - 1 > 0 or len_file2 - j - 1 > 0:
            if file1_data[i] < file2_data[j]:
                different_lines[section].append((file1_data[i], no_line))
                i += 1
            elif file1_data[i] > file2_data[j]:
                different_lines[section].append((no_line, file2_data[j]))
                j += 1
            else: ## when the two strings are the same
                i += 1
                j += 1
    output_file_path = Path(file_path, pair_files[0]+'_'+pair_files[1]).with_suffix('.compared')
    with open(output_file_path, 'w', newline='') as output_file:
        output_file.write(",".join(different_lines['devices']) + new_line)
        for section in config_group:
            for line in different_lines[section]:
                output_file.write(",".join(line) + new_line)

if __name__ == "__main__":
    cmdArgs = CmdLine().get_args()
    ######### Input file processing ############################################
    path = Path(cmdArgs.dir_path)
    if not (path.exists() and path.is_dir()):
        print(path, " isn't a path to a directory. You need a directory with text files.")
        sys.exit()
    #####################
    ## Create files in which the extracted lines should go
    #files = path.glob(file_extension) ## glob() creates a generator which can be read only once. 
    #https://stackoverflow.com/questions/42246819/loop-over-results-from-path-glob-pathlib
    output_path = Path.cwd()
    file_extension_pattern = '*' + file_extension
    print("file extension pattern: ", file_extension_pattern)
    for file in path.glob(file_extension_pattern):
        for section in config_group: ## This only returns keys in a dict.
            output_file = Path(output_path, file).with_suffix(config_group[section]['file_suffix'])
            extract_lines(file, config_group[section]['pattern_to_extract'], output_file)
    #####################
    ## Read in pair file names into a list
    with open(cmdArgs.pairs, 'r', newline='') as csv_file:
        pair_devices = csv.reader(csv_file)
        for pair in pair_devices:
            compare_lines(pair, path)
