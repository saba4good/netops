"""
Objectives
----------
Get Command outputs from the Citrix ADC shell.

Takes
-----
dev_file : json format
    List of appliacnes with IP and account details
    (Each device log files will be named with the device name listed in this file.)
cmd_file : json format
    Commands that will be executed in the Citrix ADC

Returns
-------
file : text file
    Status details for each device.

Raises
------

Warning
-------

"""
#!/usr/bin/env python3
import argparse
import paramiko, time, json

##### global variables ########################################################
max_buffer_default = 65535
sleep_time_default = 3
max_buffer_large = 262140000 ## for commands whose output runs a lot longer
sleep_time_long = 7
new_line = '\n'
dev_file = 'devices.json'
cmd_file = 'commands.json'

with open(dev_file, 'r') as dev_in:
    devices = json.load(dev_in)

with open(cmd_file, 'r') as cmd_in: 
    commands = json.load(cmd_in)

def clear_buffer(connection):
    if connection.recv_ready():
        return connection.recv(max_buffer_default)

print("Devices are read from", dev_file)
print("Commands are from", cmd_file, new_line)
dev_no = 0
# Starts the loop for devices
for device in devices.keys(): 
    ## to distinguish files, use seconds and micro seconds parts of timestamp
    outputFileName = device + '_' + str(time.time()).replace('.', '')[8:] + '.log'
    dev_no += 1
    print("Dev.", dev_no, ")", device, "(output file: ", outputFileName, ")")
    print("       via ", devices[device]['ip'], " with ", devices[device]['username'], ":", devices[device]['password'])
    connection = paramiko.SSHClient()
    connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connection.connect(devices[device]['ip'], username=devices[device]['username'], password=devices[device]['password'], look_for_keys=False, allow_agent=False)
    new_connection = connection.invoke_shell()
    print("Connected..")
    recv_bf = clear_buffer(new_connection)
    time.sleep(sleep_time_default)
    #new_connection.send("set prompt %h_%s" + new_line)
    ## to print out the command output without pause 'more' for citrix adc
    new_connection.send("set cli mode -page Off" + new_line)
    time.sleep(sleep_time_default)
    #recv_bf = clear_buffer(new_connection)
    recv_bf = new_connection.recv(max_buffer_default)
    with open(outputFileName, 'wb') as f:
        output = bytearray("Target : " + device + new_line, 'utf-8')
        f.write(output)
        f.write(recv_bf)
        cmd_no = 0
        for command in commands.keys():
            cmd_no += 1
            new_connection.send(command + new_line)
            print(dev_no, "-", cmd_no, ") ", command)
            ## if the length of output of the command is expected to be short, use less buffer and wait time.
            if commands[command] == "short":
                time.sleep(sleep_time_default)
                recv_bf = new_connection.recv(max_buffer_default)
            else:
                time.sleep(sleep_time_long)
                recv_bf = new_connection.recv(max_buffer_large)
            f.write(recv_bf)
            print("done.")
        new_connection.send("set cli mode -page On" + new_line)
        print("Commands all carried out..", new_line)
        time.sleep(sleep_time_default)
        recv_bf = new_connection.recv(max_buffer_default)
        f.write(recv_bf)
    new_connection.close()
    