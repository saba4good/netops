'''
v.0.1
Objectives:
각 NW 장비 IP list를 받아서, interface IP's, VRRP/HSRP IP's를 output으로 낸다.
SNMP oid를 사용할 예정
Output: OUTPUT_COLUMNS
Input: 장비 IP list file, snmp commnunity string
'''
#!/usr/bin/env python3
import argparse
import re              # regular expression
from datetime import date
import ipaddress
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto.rfc1902 import Integer, IpAddress, OctetString

##### global variables ########################################################
#OUTPUT_COLUMNS='Host Name, Device IP, Interface IP, HSRP IP, VRRP IP, Svr VIP\n'
OUTPUT_COLUMNS='IP Used, Host Name, Host IP, Description\n'
SNMP_COMMUNITY='change_this_value_to_the_community_string'
SNMP_PORT=161
OID_SYS_DESC='.1.3.6.1.2.1.1.1'
OID_SYS_NAME='.1.3.6.1.2.1.1.5'
OID_INT_IP='.1.3.6.1.2.1.4.20.1.2'
OID_HSRP_IP='.1.3.6.1.4.1.9.9.106.1.2.1.1.11'
OID_F5_VIP='.1.3.6.1.4.1.3375.2.2.10.1.2.1.3'
OID_ALTEON_VIP='.1.3.6.1.4.1.1872.2.5.3.1.6.3.1.3'
#OID_VRRP_IP='.1.3.6.1.4.1.1872.2.1.15.2.1.3'

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
        # row[0][0] : pysnmp.smi.rfc1902.ObjectIdentity
        # row[0][1] : pysnmp.proto.rfc1902.Integer or some other type
        # https://stackoverflow.com/questions/41890570/python-hex-ip-as-string-to=ddn-ip-string
        if re.search(r'(OctetString|IpAddress)', str(type(row[0][1]))):
            ip = IpAddress(row[0][1].asOctets()).prettyPrint()
        else:
            try:
                ip = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+$', str(row[0][0]))).group(0)
            except ValueError:
                ip = ''
        try:
            ipSet.add(format(ipaddress.ip_address(ip)))
        except ValueError:
            pass
    return ipSet

if __name__ == '__main__':
    cmdArgs = CmdLine().get_args()
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
    output_file='device_ip-' + date.today().strftime('%Y%m%d') + '.csv'  # 결과 파일 이름
    with open(output_file, 'w') as out_file:
        out_file.write(OUTPUT_COLUMNS)
        for deviceIp in deviceIpSet:
            aNWDevice = (deviceIp, cmdArgs.CommunityString, SNMP_PORT)
            #a IP, Host Name, Host IP, Description
            #a IP : Interface IP, HSRP IP, VRRP IP, Svr VIP
            #hostName = (re.search(r'(?<=\=\s)[\w\-\_]+(?=\.)', str(snmp_getnext(aNWDevice)[0][0]))).group(0)
            hostName = (re.search(r'[\w\-\_]+', str(snmp_getnext(aNWDevice)[0][0][1]))).group(0)
            intIpSet = snmp_get_ip(aNWDevice)
            for ip in intIpSet:
                out_file.write("%s, %s, %s, Interface IP\n" % (ip, hostName, deviceIp))
            # Cisco, Alteon, F5 (BIG-IP), Alcatel, Piolink, HPE, Dell
            vendorData = str(snmp_getnext(aNWDevice, OID_SYS_DESC)[0][0][1])
            print('vendorData: ', vendorData)
            match vendorData.split():
                case ['Cisco' as vendor, *rest]:
                    usage = 'HSRP'
                    oidToUse = OID_HSRP_IP
                case ['BIG-IP' as vendor, *rest]:
                    usage = 'VIP'
                    oidToUse = OID_F5_VIP
                case ['Alteon' as vendor, *rest]:
                    usage = 'VIP'
                    oidToUse = OID_ALTEON_VIP
                case _:
                    vendor = 'None'
            ipSet = snmp_get_ip(aNWDevice, oidToUse)
            for ip in ipSet:
                out_file.write("%s, %s, %s, %s\n" % (ip, hostName, deviceIp, usage))
