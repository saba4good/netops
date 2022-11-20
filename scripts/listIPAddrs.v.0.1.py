'''
v.0.1
Objectives:
각 NW 장비 IP list를 받아서, interface IP's, VRRP/HSRP IP's, routing table IP's를 output으로 낸다.
SNMP oid를 사용할 예정
Output: OUTPUT_COLUMNS
Input: 장비 IP list, snmp commnunity string
'''
#!/usr/bin/env python3
#import mmap
import argparse
import re              # regular expression
#import copy
from datetime import date
import ipaddress
#from ipaddress import IPv4Network
from pysnmp.entity.rfc3413.oneliner import cmdgen
#from pysnmp.proto.rfc1902 import Integer, IpAddress, OctetString

##### global variables ########################################################
OUTPUT_COLUMNS='Host Name, Device IP, Interface IP, HSRP IP, VRRP IP, Svr VIP\n'
SNMP_COMMUNITY='change_this_value_to_the_community_string'
SNMP_PORT=161
OID_INT_IP='.1.3.6.1.2.1.4.20.1.2'
OID_HSRP_IP='.1.3.6.1.4.1.9.9.106.1.2.1.1.11'

IDX_HOST=0
IDX_HOST_IP=1+IDX_HOST
IDX_INT_IP=1+IDX_HOST_IP
IDX_HSRP_IP=1+IDX_INT_IP
IDX_VRRP_IP=1+IDX_HSRP_IP
IDX_SVR_VIP=1+IDX_VRRP_IP
LAST_INDEX=IDX_SVR_VIP
#INIT_FLAG=-1
#FLAG_=1

class CmdLine:
    def __init__(self):
        parser = argparse.ArgumentParser()
        # 이 프로그램을 실행할 때, 받아들일 arguments 2개
        parser.add_argument('dev_ip_file', type=argparse.FileType('r'), help="Device IP list")
        parser.add_argument("-c", "--CommunityString", type=str, help = "Community string", required = False, default = SNMP_COMMUNITY)
        self.args=parser.parse_args()
    def get_args(self):
        return self.args

def snmp_get_oid(a_device, oid='.1.3.6.1.2.1.1.1.0', display_errors=False):
    '''
    Retrieve the given OID
    Default OID is MIB2, sysDescr
    a_device is a tuple = (a_host, community_string, snmp_port)
    ref : https://www.programcreek.com/python/example/105449/pysnmp.entity.rfc3413.oneliner.cmdgen.CommandGenerator
          example #15
    '''
    a_host, community_string, snmp_port = a_device
    snmp_target = (a_host, snmp_port)

    # Create a PYSNMP cmdgen object
    cmd_gen = cmdgen.CommandGenerator()

    (error_detected, error_status, error_index, snmp_data) = cmd_gen.nextCmd(
        cmdgen.CommunityData(community_string),
        cmdgen.UdpTransportTarget(snmp_target),
        oid,
        lookupNames=True, lookupValues=True
    )

    if not error_detected:
        return snmp_data
    else:
        if display_errors:
            print('ERROR DETECTED: ')
            print('    %-16s %-60s' % ('error_message', error_detected))
            print('    %-16s %-60s' % ('error_status', error_status))
            print('    %-16s %-60s' % ('error_index', error_index))
        return None

if __name__ == '__main__':
    cmdArgs = CmdLine().get_args()
    #########################################################################
    ######### IP file processing ############################################
    with cmdArgs.dev_ip_file as dev_ip_file:
        deviceIpSet = set()
        for line in dev_ip_file:
            ipaddr = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
            try:
                deviceIpSet.add(format(ipaddress.ip_address(ipaddr)))
            except ValueError:
                pass
    ######### Build a device list ###########################################
    devTable = []
    for deviceIp in deviceIpSet:
        devTable.append(["" for i in range(LAST_INDEX+1)])
        devTable[-1][IDX_HOST_IP] = deviceIp
        devTable[-1][IDX_HOST] = snmp_get_oid((deviceIp, cmdArgs.CommunityString, SNMP_PORT))
        snmpData = snmp_get_oid((deviceIp, cmdArgs.CommunityString, SNMP_PORT), OID_INT_IP)
        print("SNMP data : ", snmpData)
        #devTable[-1][IDX_INT_IP] = 
        #print ("host name : ", devTable[-1][IDX_HOST])
        
    '''
    #print ('srcnetProfiles : ', srcnetProfiles)
    ## settingsTable의 row에 PIP가 있으면 srcnet을 채워넣기.
    for row in settingsTable:
        if row[IDX_PIP_SRC] != '':
            row[IDX_PIP_SRC] = srcnetProfiles[row[IDX_PIP_SRC]]
    output_file=hostname + '-cfg-' + date.today().strftime('%Y%m%d') + '.csv'  # 결과 파일 이름
    with open(output_file, 'w') as out_file:
        out_file.write(OUTPUT_COLUMNS)
        for row in settingsTable:
            for j, value in enumerate(row):
                out_file.write(value)
                if j != LAST_IDX:
                    out_file.write(", ")
                else:
                    out_file.write("\n")
    '''
