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
#OUTPUT_COLUMNS='Host Name, Device IP, Interface IP, HSRP IP, VRRP IP, Svr VIP\n'
OUTPUT_COLUMNS='IP, Host Name, Host IP, Description\n'
SNMP_COMMUNITY='change_this_value_to_the_community_string'
SNMP_PORT=161
OID_SYS_DESC='.1.3.6.1.2.1.1.1'
OID_SYS_NAME='.1.3.6.1.2.1.1.5'
OID_INT_IP='.1.3.6.1.2.1.4.20.1.2'
OID_HSRP_IP='.1.3.6.1.4.1.9.9.106.1.2.1.1.11'
OID_VRRP_IP=''
OID_SVR_VIP=''

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

def snmp_getnext(a_device, oid=OID_SYS_NAME, display_errors=False):
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
def snmp_get_ip(a_device, oid=OID_INT_IP, display_errors=False):
    ipSet = set()
    snmpData = snmp_getnext(a_device, oid)
    for row in snmpData:
        ip = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+(?=\s)', str(row[0]))).group(0)
        try:
            ipSet.add(format(ipaddress.ip_address(ip)))
        except ValueError:
            pass
    return ipSet

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
    '''
    devTable = []
    for deviceIp in deviceIpSet:
        aNWDevice = (deviceIp, cmdArgs.CommunityString, SNMP_PORT)
        devTable.append(["" for i in range(LAST_INDEX+1)])
        #Host Name, Device IP, Interface IP, HSRP IP, VRRP IP, Svr VIP
        hostName = (re.search(r'[\w]+(?=\.)', snmp_getnext(aNWDevice)[0])).group(0)
        devTable[-1]=[hostName, deviceIp, snmp_get_ip(aNWDevice), snmp_get_ip(aNWDevice, OID_HSRP_IP), snmp_get_ip(aNWDevice, OID_VRRP_IP), snmp_get_ip(aNWDevice, OID_SVR_VIP)]
        #devTable[-1][IDX_HOST_IP] = deviceIp
        #devTable[-1][IDX_HOST] = snmp_getnext(aNWDevice)
        #devTable[-1][IDX_INT_IP] = snmp_get_ip(aNWDevice)
        #devTable[-1][IDX_HSRP_IP] = snmp_get_ip(aNWDevice, OID_HSRP_IP)
    print ("Table : ", devTable)
    '''
    output_file='device_ip-' + date.today().strftime('%Y%m%d') + '.csv'  # 결과 파일 이름
    with open(output_file, 'w') as out_file:
        out_file.write(OUTPUT_COLUMNS)
        devTable = []
        for deviceIp in deviceIpSet:
            aNWDevice = (deviceIp, cmdArgs.CommunityString, SNMP_PORT)
            #a IP, Host Name, Host IP, Description
            #a IP : Interface IP, HSRP IP, VRRP IP, Svr VIP
            hostName = (re.search(r'(?<=\=\s)[\w\-\_]+(?=\.)', str(snmp_getnext(aNWDevice)[0][0]))).group(0)
            intIpSet = snmp_get_ip(aNWDevice)
            for ip in intIpSet:
                out_file.write("%s, %s, %s, Interface IP\n" % (ip, hostName, deviceIp))
            hsrpIpSet = snmp_get_ip(aNWDevice, OID_HSRP_IP)
            for ip in hsrpIpSet:
                out_file.write("%s, %s, %s, HSRP IP\n" % (ip, hostName, deviceIp))
            vrrpIpSet = snmp_get_ip(aNWDevice, OID_VRRP_IP)
            for ip in vrrpIpSet:
                out_file.write("%s, %s, %s, VRRP IP\n" % (ip, hostName, deviceIp))
            vipSet = snmp_get_ip(aNWDevice, OID_SVR_VIP)
            for ip in vipSet:
                out_file.write("%s, %s, %s, Sever VIP\n" % (ip, hostName, deviceIp))