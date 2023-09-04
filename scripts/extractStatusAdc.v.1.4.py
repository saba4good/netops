"""
Objectives
----------
Get the important status and configuration details from the Citrix ADC inspection log files.

Takes
-----
status_input_f : text file
    Commands output from Citrix ADC
dev_input : csv format
    List of appliacnes with IP and account details
    (Each device log files should be named with the device name listed in this file.)
fields_file : json format
    Field names for the output file and key phrase to search for the target values from the status input file.
    This file determines which numbers are to be selected as determinant

Returns
-------
file : csv format and json format
    Status details for each device.

Raises
------
IndexError

Warning
-------

"""
#!/usr/bin/env python3
import argparse
import time
import json, csv
import re

##### global variables ########################################################
dev_input = 'devices.csv'
dev_json = 'devices.json'
dev_key = 'Devices'
fields_file = 'fields.json' # The field titles in the output status file, Key words to find in the input log file
status_postfix = '.log'

target_for_search = 'Key Phrases'
sh_prompt = 'root@'
not_ok = 'Not Good'

def csv_to_json(csv_file, json_file, key_column):
    """
    Reads a csv file and turn it into a json file using a column as a key value.
    Credit: ChatGPT API course
    """
    # Read the CSV file
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    # Convert the list of dictionaries to a dictionary using the specified key column
    data = {row[key_column]: row for row in rows}

    # Write the dictionary to the JSON file
    with open(json_file, 'w') as file:
        json.dump(data, file, indent=4)

def grab_status_lines(device, fields, field_names, status_record, line_below=False):
    """
    Grab status lines from the input status file for one device and return it as a dictionary keyed with a device hostname.
    """
    status_input_f = device + status_postfix
    i = 0
    print("Input file name : ", status_input_f)
    with open(status_input_f, 'r') as status_in:
        for line in status_in:
            if line_below:
                ## When the target value should be in the line below the target phrase,
                ## check if the line below is a prompt or actual value.
                ## So the command prompt MUST contain the host name. Otherwise, this check fails.
                if device not in line:
                    status_record[field_names.pop(i)] = line.strip()
                else:
                    status_record[field_names.pop(i)] = 'None'
                line_below = False
            else:
                i = 0
                ## To accomdate different target phrases depending on the versions and chipsets, it's a list.
                ## Check all phrases in the list
                ## ref : https://stackoverflow.com/questions/2783969/compare-string-with-all-values-in-list
                while not any(target_phrase in line for target_phrase in fields[field_names[i]][target_for_search]):
                    i += 1
                    if i >= len(field_names):
                        #print("------------- before break ------------------")
                        #print("status before break : ", status_record)
                        break
                else:
                    target_phrase = next((t_p for t_p in fields[field_names[i]][target_for_search] if t_p in line), None)
                    if fields[field_names[i]]['No. of Lines from Key'] == "0":
                        status_record[field_names.pop(i)] = (line.split(target_phrase, 2)[-1]).strip()
                    else:
                        line_below = True
            try:
                field_names[0]
            except IndexError:
                #print("status when at the end of the line : ", status_record)
                return status_record
        return status_record

## to distinguish files, use seconds and micro seconds parts of timestamp
outputFileName = 'inspection_status-' + time.strftime("%Y%m%d") + '-' + str(time.time()).replace('.', '')[8:] + '.csv'
dataOutputFile = 'status_detail-' + time.strftime("%Y%m%d") + '-' + str(time.time()).replace('.', '')[8:] + '.json'

csv_to_json(dev_input, dev_json, dev_key)
with open(dev_json, 'r') as dev_in:
    devices = json.load(dev_in)
    
with open(fields_file, 'r') as fields_in:
    fields = json.load(fields_in)

print("Devices are read from", dev_json)
status_detail = dict()
## Starts the loop for devices
for device in devices.keys():
    status_detail[device] = dict.fromkeys(fields,'')
    field_names = list(fields.keys()) ## To pop each field once found. So index 0 is the field we're working on.
    print("Device : ", device)
    status_detail[device][field_names.pop(0)] = device
    status_detail[device][field_names.pop(0)] = devices[device][field_names[0]]  ## The right to the assignment symbol is called earlier than the left.
    ## Pop some fields that won't be comming from the raw input file.
    ## They will be separate fields in the output file after the values will be processed from the input file.
    ## https://stackoverflow.com/questions/176918/finding-the-index-of-an-item-in-a-list
    field_names.remove("FAN")
    field_names.remove("Service (Total)")
    field_names.remove("Vserver (Total)")
    field_names.remove("Logging")
    ###########################################
    ## Get the lines from input status file (this won't process anything specific to the each field)
    status_detail[device] = grab_status_lines(device, fields, field_names, status_detail[device])
    #print("Device detail : ", status_detail[device])
    ###########################################
    ## Process the output with detailed filters
    ## - NSIP
    status_detail[device]['NSIP'] = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', status_detail[device]['NSIP'])).group(0)
    ## - Interfaces disabled
    if status_detail[device]['Interface Dis.']:
        status_detail[device]['Interface Dis.'] = 'OK'
    ## - Model
    #status_detail[device]['Model'] = status_detail[device]['Model'].split()[0]
    status_detail[device]['Base Model'] = status_detail[device]['Base Model'].split()[0]
    status_detail[device]['Licensed Model'] = status_detail[device]['Licensed Model'].split()[0]
    ## - OS Version : '13.1: Build 24.38.nc'
    status_detail[device]['OS Version'] = (re.search(r'[\d]+\.[\d]+: Build [\d]+\.[\d]+', status_detail[device]['OS Version'])).group(0)
    ## - CPU FAN
    if int(status_detail[device]['CPU FAN 0']) <= 500 or int(status_detail[device]['CPU FAN 1']) <= 500 or int(status_detail[device]['FAN 1']) <= 500 or int(status_detail[device]['FAN 2']) <= 500:
        status_detail[device]['FAN'] = not_ok
    else:
        status_detail[device]['FAN'] = 'OK'
    ## - Service (Total)
    status_detail[device]['Service (Total)'] = int(status_detail[device]['Service (UP)']) + int(status_detail[device]['Service (Down)']) + int(status_detail[device]['Service (OutofService)'])
    ## - Vserver (Total)
    status_detail[device]['Vserver (Total)'] = int(status_detail[device]['Vserver (UP)']) + int(status_detail[device]['Vserver (Down)']) + int(status_detail[device]['Vserver (OutofService)'])
    ## - TCP CPS
    client_side, server_side = (re.search(r'[\d]+[\s]+[\d]+', status_detail[device]['TCP CPS'])).group(0).split()
    status_detail[device]['TCP CPS'] = int(client_side) + int(server_side)
    ## - TCP CC
    client_side, server_side = (re.search(r'[\d]+[\s]+[\d]+', status_detail[device]['TCP CC'])).group(0).split()
    status_detail[device]['TCP CC'] = 'Client: ' + client_side + ' / Server: ' + server_side
    ## - HTTP RPS
    status_detail[device]['HTTP RPS'] = (re.search(r'[\d]+[\s]+[\d]+', status_detail[device]['HTTP RPS'])).group(0).split()[1]
    ## - SSL TPS
    status_detail[device]['SSL TPS'] = (re.search(r'[\d]+[\s]+[\d]+', status_detail[device]['SSL TPS'])).group(0).split()[1]
    ## - SSL Crypto (Asym)
    try:
        #print("SSL Asym : ", status_detail[device]['SSL Crypto (Asym)'])
        status_detail[device]['SSL Crypto (Asym)'] = (re.search(r'[\d]+', status_detail[device]['SSL Crypto (Asym)'])).group(0)
        status_detail[device]['SSL Crypto (Sym)'] = (re.search(r'[\d]+', status_detail[device]['SSL Crypto (Sym)'])).group(0)
    except AttributeError:
        status_detail[device]['SSL Crypto (Asym)'] = "N/A"
        status_detail[device]['SSL Crypto (Sym)'] = "N/A"
    ## - Logging Alert
    if sh_prompt in status_detail[device]['Logging Alert']:
        status_detail[device]['Logging Alert'] = 'OK'
    ## - Logging Critical
    if sh_prompt in status_detail[device]['Logging Critical']:
        status_detail[device]['Logging Critical'] = 'OK'
    ## - Logging Warning
    if sh_prompt in status_detail[device]['Logging Warning']:
        status_detail[device]['Logging Warning'] = 'OK'
    ## - Logging
    if len({status_detail[device]['Logging Alert'], status_detail[device]['Logging Critical'], status_detail[device]['Logging Warning']}) == 1:
        status_detail[device]['Logging'] = 'OK'
    else:
        status_detail[device]['Logging'] = not_ok
with open(dataOutputFile, 'w') as json_f:
    json.dump(status_detail, json_f, indent=4)
print("output data file: ", dataOutputFile)
with open(outputFileName, 'w', newline='') as csv_f:
    status_writer = csv.writer(csv_f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    status_writer.writerow(field for field in fields.keys())
    for device in devices.keys():
        status_writer.writerow(status_detail[device].values())
print("output csv file: ", outputFileName)
## Transpose data in csv file
## https://stackoverflow.com/questions/4869189/how-to-transpose-a-dataset-in-a-csv-file
with open(outputFileName) as src, open('t_'+outputFileName, 'w', newline='') as fw:
    csv.writer(fw, delimiter=',').writerows(zip(*csv.reader(src, delimiter=',')))
