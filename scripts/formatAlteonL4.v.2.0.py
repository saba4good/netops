'''
v.2.0:
- /cfg/dump 파일만을 사용한다.
- requires python 3.10 for case statements
Objectives:
Alteon L4 로그 파일에서 현재 SLB 설정 현황을 csv 파일 포맷으로 만든다.
Output: OUTPUT_COLUMNS
Input:
'/cfg/dump' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하고, 로그 파일을 나누어서 2개의 파일로 만든다.)
방법: 해당 파이선 프로그램과 A 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatConfAlteonL4.v.2.0.py [log file A]
- input 파일을 한 라인씩 읽으면서 real 서버 up/down 현황 dictonary 를 만든다.
"Real server [\d]+ stats:" ... RealSvr No 라인의 시작: RealSvr No (key pair 중 하나)
"100.100.100.240                                0" ... No of Current Sessions (value pair 중 하나)
"Instance Health check: " ... Rport 라인의 시작: Rport, Status (key pair, value pair 각각)

references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of an input file example:
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
import copy
from datetime import date
from ipaddress import IPv4Network

##### global variables ########################################################
## for group slb method settings processing
DEFAULT_SLB_METHOD='leastConnections'
IS_SLB_METHOD='metric'
INIT_VALUE='-1'
DEFAULT_STD_MODE='Active-Active'
BACKUP_STD_MODE='Active-standby'

## before real svr numbers in a config file
HOSTNAME_FINDER='/c/sys/ssnmp'
FLAG_HOSTNAME=False
START_OF_SETTINGS='/c/slb/ssl'
START_OF_REALS='/c/slb/real'
START_OF_GROUPS='/c/slb/group'
IDX_HP_ID=0
IDX_HP_IP=1
IDX_HP_PORT=2
IDX_HP_TYPE=3
IDX_HP_LOGEXP=4
HP_LAST_IDX=IDX_HP_LOGEXP

IDX_RP_IP=0
IDX_RP_PORTS=1
IDX_RP_DESC=2
IDX_RP_HC=3
IDX_RP_HC_IP_PORT=4
RP_LAST_IDX=IDX_RP_HC_IP_PORT

IDX_GP_SLB=0
IDX_GP_RIDS=1
IDX_GP_DESC=2
IDX_GP_HC=3
IDX_GP_STDMODE=4
GP_LAST_IDX=IDX_GP_STDMODE

IDX_VIP=0
IDX_VPORT=1 + IDX_VIP
IDX_RIP=1 + IDX_VPORT
IDX_RPORTS=1 + IDX_RIP
IDX_STD_MODE=1 + IDX_RPORTS
IDX_SLB_METHOD=1 + IDX_STD_MODE
IDX_HEALTHCHECK=1 + IDX_SLB_METHOD
IDX_VIRT=1 + IDX_HEALTHCHECK
IDX_GROUP_NO=1 + IDX_VIRT
IDX_RSVR_NO=1 + IDX_GROUP_NO
IDX_PIP_SNAT=1 + IDX_RSVR_NO
IDX_PIP_SRC=1 + IDX_PIP_SNAT
IDX_LOC_MODE=1 + IDX_PIP_SRC
IDX_DESC=1 + IDX_LOC_MODE
LAST_IDX=IDX_DESC ## 맨 마지막 순서인 인덱스명
OUTPUT_COLUMNS='Vip, Vport, Rip, Rports, Standby Mode, SLB method, Health Check, Virt, Group No, RealSvr No, PIP SNAT Pool, PIP src, Location/Mode, Description\n'
#
INIT_FLAG=-1
FLAG_VIP=1
FLAG_VPORT=2
FLAG_RIP=3
FLAG_MULTI_RPORT=4
FLAG_PIP=5
FLAG_GROUP=6
FLAG_VIRT=7
#OUTPUT_FILE='output-l4-settings' + str(date.today()) + '.csv'  # 결과 파일 이름
if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_file', type=argparse.FileType('r'), help="log for '/cfg/dump'")

    args = parser.parse_args()
    #########################################################################
    ######### Config file processing ########################################
    ######### health check : [profile_id, ip, ports, type, logexp] ##########
    ######### real  : [real No., rip, rports, description] ##################
    ######### group : [group No., slb method, [real No.s'], description ] ###
    ######### virt  : [virt No., vip, vport, group No., description ] #######
    with args.cfg_file as cfg_file:
        for line in cfg_file:
            match line.split():
                case ['/*','Configuration','dump','taken', *cfg_date]:
                    break
        for line in cfg_file:
            match line.split():
                case ['/c/sys/ssnmp']:
                    FLAG_HOSTNAME = True
                case ['name', a_name]:
                    if FLAG_HOSTNAME:
                        hostname = (re.search(r'(?<=\").+(?=\")', a_name)).group(0)
                        FLAG_HOSTNAME = False
                case ['/c/slb/ssl']:
                    break
        ######### health check : [profile_id, ip, ports, type, logexp] ##########
        healthProfiles = dict()
        hcID = ''
        for line in cfg_file:
            match line.split():
                case ['/c/slb/advhc/health', hcID, hc_proto]:
                    healthProfiles[hcID]=["" for i in range(HP_LAST_IDX+1)]
                    healthProfiles[hcID][IDX_HP_TYPE] = hc_proto
                case ['dport', hc_dport]:
                    healthProfiles[hcID][IDX_HP_PORT] = hc_dport
                case ['dest', '4', hc_dip]:
                    healthProfiles[hcID][IDX_HP_IP] = hc_dip
                case ['logexp', hc_exp]:
                    healthProfiles[hcID][IDX_HP_LOGEXP] = (re.search(r'(?<=\").+(?=\")', hc_exp)).group(0)
                case ['/c/slb']:  ## health check 구문을 빠져나가면
                    break         ## for loop을 중단하여 cfg_file을 그만 읽는다.
        #print ('health check profiles : ', healthProfiles)
        ######### real  : [real No., rip, rports, description] ##################
        realProfiles = dict()
        realNo = ''
        groupProfiles = dict()
        groupNo = ''
        in_group_sec=INIT_FLAG ## to set a flag when in the group settings section
        for line in cfg_file:
            if START_OF_REALS in line:   ### 프로세싱 필요한 라인을 찾는다.
                realNo = (re.search(r'(?<=/c/slb/real\s)[\d]+', line)).group(0)
                realProfiles[realNo]=["" for i in range(RP_LAST_IDX+1)]
                hc_ip_ports = ''
                break
        for line in cfg_file:
            match line.split():
                case ['/c/slb/real', realNo]:
                    realProfiles[realNo]=["" for i in range(RP_LAST_IDX+1)]
                    hc_ip_ports = ''
                case ['rip', realIP]:
                    realProfiles[realNo][IDX_RP_IP] = realIP
                case ['name', realDesc]:
                    realProfiles[realNo][IDX_RP_DESC] = realDesc
                case ['health', hcName]:
                    realProfiles[realNo][IDX_RP_HC] = hcName
                    if healthProfiles[realProfiles[realNo][IDX_RP_HC]][IDX_HP_TYPE] == 'LOGEXP':
                        for hcProfile in healthProfiles[realProfiles[realNo][IDX_RP_HC]][IDX_HP_LOGEXP].split("&"):
                            try:
                                if healthProfiles[hcProfile]:
                                    if hc_ip_ports != '':
                                        hc_ip_ports += ';'
                                    hc_ip_ports += (healthProfiles[hcProfile][IDX_HP_IP] + ':' + healthProfiles[hcProfile][IDX_HP_PORT])
                            except KeyError:  ### when the key isn't in the dictonary
                                pass
                        realProfiles[realNo][IDX_RP_HC_IP_PORT] = hc_ip_ports
                case ['addport', realPorts]:
                    if realProfiles[realNo][IDX_RP_PORTS] != '':      ## real ports에 이미 값이 있으면
                        realProfiles[realNo][IDX_RP_PORTS] += ';'     ## 세미콜른을 붙여줘라
                    realProfiles[realNo][IDX_RP_PORTS] += (re.search(r'(?<=\s)[\d]+', line)).group(0)
                case ['/c/slb/group', groupNo]:
                    groupProfiles[groupNo]=["" for i in range(GP_LAST_IDX+1)]
                    in_group_sec=FLAG_GROUP  ## to set a flag when in the group settings section
                    break
        #print("real dict : ")
        #print("{:<8} {:<20} {:<12} {:<30} {:<20} {:<40}".format('rNo', 'rIP', 'rPorts', 'Desc', 'HC label', 'HC ports'))
        #for realSvrNo, realSvr in realProfiles.items():
        #    rip, rPorts, desc, hc_label, hc_ports = realSvr
        #    print("{:<8} {:<20} {:<12} {:<30} {:<20} {:<40}".format(realSvrNo, rip, rPorts, desc, hc_label, hc_ports))
        ######### group : [group No., slb method, [real No.s'], description ] ###
        if in_group_sec!=FLAG_GROUP:
            for line in cfg_file:
                if START_OF_GROUPS in line:   ### 프로세싱 필요한 라인을 찾는다.
                    groupNo = (re.search(r'(?<=/c/slb/group\s)[\d]+', line)).group(0)
                    groupProfiles[groupNo]=["" for i in range(GP_LAST_IDX+1)]
                    break
        settingsTable = []
        in_virt_sec=INIT_FLAG
        for line in cfg_file:
            match list(filter(None, re.split('[\s/]+', line))):
                case ['c','slb','group', groupNo]:
                    groupProfiles[groupNo]=["" for i in range(GP_LAST_IDX+1)]
                    groupProfiles[groupNo][IDX_GP_STDMODE]=DEFAULT_STD_MODE ## active-active or active-standby for servers
                case ['add', realActive]:
                    if groupProfiles[groupNo][IDX_GP_SLB] == '':
                        groupProfiles[groupNo][IDX_GP_SLB] = DEFAULT_SLB_METHOD ## 'metric' 구문이 없는 경우, default 값을 사용
                    if groupProfiles[groupNo][IDX_GP_RIDS] == '':      ## real rid에 값이 없으면
                        groupProfiles[groupNo][IDX_GP_RIDS] = []
                    groupProfiles[groupNo][IDX_GP_RIDS].append(realActive)
                case ['metric', slb_method]:
                    groupProfiles[groupNo][IDX_GP_SLB] = slb_method
                case ['name', groupDesc]:
                    groupProfiles[groupNo][IDX_GP_DESC] = (re.search(r'(?<=\").+(?=\")', groupDesc)).group(0)
                case ['backup', group_backup]:
                    if groupProfiles[groupNo][IDX_GP_SLB] == '':
                        groupProfiles[groupNo][IDX_GP_SLB] = DEFAULT_SLB_METHOD
                    if groupProfiles[groupNo][IDX_GP_RIDS] == '':      ## real rid에 값이 없으면
                        groupProfiles[groupNo][IDX_GP_RIDS] = []
                    groupProfiles[groupNo][IDX_GP_RIDS].append(group_backup)
                    groupProfiles[groupNo][IDX_GP_STDMODE]=BACKUP_STD_MODE
                case ['health', groupHc]:
                    groupProfiles[groupNo][IDX_GP_HC] = groupHc
                case ['c',*rest]:
                    if re.search(r'/c/slb/virt\s[\d]+', line):
                        settingsTable.append(["" for i in range(LAST_IDX+1)])
                        virtNo = (re.search(r'(?<=/c/slb/virt\s)[\d]+', line)).group(0)
                        settingsTable[-1][IDX_VIRT] = virtNo
                        in_virt_sec=FLAG_VIRT
                    break
        #print("Group dict : ")
        #print("{:<8} {:<20} {:<30} {:<30} {:<40}".format('gNo', 'slb', 'rNo', 'Desc', 'HC'))
        #for gNo, group in groupProfiles.items():
        #    slb, rno, desc, hc, stdmode = group
        #    print("{:<8} {:<20} {:<30} {:<30} {:<40}".format(gNo, slb, ';'.join(rno), desc, hc))
        ######### virt  : [virt No., vip, vport, group No., description ] #######
        prevFlag = INIT_FLAG
        vip = ''
        if in_virt_sec!=FLAG_VIRT:
            for line in cfg_file:
                if re.search(r'/c/slb/virt\s[\d]+', line):
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    virtNo = (re.search(r'(?<=/c/slb/virt\s)[\d]+', line)).group(0)
                    settingsTable[-1][IDX_VIRT] = virtNo
                    break
        ## for pip [(virt No., vport): [srcnet No., pip nat, src ip]]
        ## before writing into the output file, for loop settingsTable to fill in the PIP info
        snatFlag = 'False'
        for line in cfg_file:
            match list(filter(None, re.split('[\s/]+', line))):
                case ['c','slb','virt',virtNo]:
                    snatFlag = 'False'
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = virtNo
                case ['c','slb','virt',virtNo,'service',vPort,serviceName]:
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = virtNo
                    settingsTable[-1][IDX_VPORT] = vPort
                    settingsTable[-1][IDX_VIP] = vip
                    #settingsTable[-1][IDX_LOC_MODE] = 'Inline'
                case ['c','slb','virt',virtNo,'service',vPort,serviceName,'pip']:
                    prevFlag = FLAG_PIP
                case ['group', groupUsed]:
                    settingsTable[-1][IDX_GROUP_NO] = groupUsed
                case ['rport', rport] if snatFlag == 'False': ### turn virtual config into a row of the settingsTable
                    realSvrs = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_RIDS]
                    for realNo in realSvrs:
                        if settingsTable[-1][IDX_RSVR_NO] != '':                     ## real server no. 값이 이미 있으면
                            settingsTable.append(copy.deepcopy(settingsTable[-1]))   ## 테이블 마지막 레코드를 복붙해서 새로 row를 만들자. 단, deepcopy() 를 이용하지 않으면 call by reference 로 복사하여 새로운 것을 편집하면 예전 것도 변경됨.
                        settingsTable[-1][IDX_STD_MODE] = 'active'
                        if re.search(r'g[\d]+', realNo):
                            groupInGrp = (re.search(r'(?<=g)[\d]+', realNo)).group(0)
                            realNo = groupProfiles[groupInGrp][IDX_GP_RIDS][0] ### backup 용 real server가 여럿이면 여기 로직 변경해야 함.
                            settingsTable[-1][IDX_STD_MODE] = 'backup'
                        settingsTable[-1][IDX_RSVR_NO] = realNo
                        if groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB] == '':
                            settingsTable[-1][IDX_SLB_METHOD] = DEFAULT_SLB_METHOD ## 'metric' 구문이 없는 경우, default 값을 사용
                        settingsTable[-1][IDX_SLB_METHOD] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB]
                        settingsTable[-1][IDX_HEALTHCHECK] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_HC_IP_PORT]
                        settingsTable[-1][IDX_DESC] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_DESC]
                        settingsTable[-1][IDX_RIP] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_IP]
                        settingsTable[-1][IDX_RPORTS] = rport
                        if settingsTable[-1][IDX_RPORTS] == '0':   ## rport 0, 즉 multi port인 경우
                            settingsTable[-1][IDX_RPORTS] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_PORTS]
                case ['vip',vip]:
                    settingsTable[-1][IDX_VIP] = (re.search(r'(?<=vip\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
                    vip = settingsTable[-1][IDX_VIP]
                case ['vname',vname]:
                    settingsTable[-1][IDX_DESC] = (re.search(r'(?<=\").+(?=\")', vname)).group(0)
                case ['nonat', 'ena']:
                    settingsTable[-1][IDX_LOC_MODE] = 'DSR'
                case ['srcnet', nwclassUsed]:
                    snatFlag = 'True'
                    nwclassUsed = (re.search(r'(?<=\").+(?=\")', nwclassUsed)).group(0)
                    settingsTable[-1][IDX_PIP_SRC] = nwclassUsed
                case ['addr','v4',snat,snatMask,'persist',persisStatus]:
                    realSvrs = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_RIDS] #### This is repeated in rport case
                    for realNo in realSvrs:
                        if settingsTable[-1][IDX_RSVR_NO] != '':
                            settingsTable.append(copy.deepcopy(settingsTable[-1]))
                        settingsTable[-1][IDX_STD_MODE] = 'active'
                        if re.search(r'g[\d]+', realNo):
                            groupInGrp = (re.search(r'(?<=g)[\d]+', realNo)).group(0)
                            realNo = groupProfiles[groupInGrp][IDX_GP_RIDS][0]
                            settingsTable[-1][IDX_STD_MODE] = 'backup'
                        settingsTable[-1][IDX_RSVR_NO] = realNo
                        if groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB] == '':
                            settingsTable[-1][IDX_SLB_METHOD] = DEFAULT_SLB_METHOD
                        settingsTable[-1][IDX_SLB_METHOD] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB]
                        settingsTable[-1][IDX_HEALTHCHECK] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_HC_IP_PORT]
                        settingsTable[-1][IDX_DESC] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_DESC]
                        settingsTable[-1][IDX_RIP] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_IP]
                        settingsTable[-1][IDX_RPORTS] = rport
                        if settingsTable[-1][IDX_RPORTS] == '0':
                            settingsTable[-1][IDX_RPORTS] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_PORTS]
                        settingsTable[-1][IDX_PIP_SNAT] = IPv4Network(snat+'/'+snatMask).with_prefixlen #### except this line (이 라인 전까지 function으로 만들기.)
                        settingsTable[-1][IDX_PIP_SRC] = nwclassUsed
                case ['c','slb',*rest]|['c','l3',*rest]:
                    break
        srcnetProfiles = dict()
        for line in cfg_file:
            match list(filter(None, re.split('[\s/]+', line))):
                case ['c','slb','nwclss', nwclass]:
                    srcnetProfiles[nwclass]=''
                case ['net','subnet',subnet,mask,'include']:
                    if srcnetProfiles[nwclass] != '':      ## srcnet이 이미 있으면
                        srcnetProfiles[nwclass] += ';'
                    srcnetProfiles[nwclass] += IPv4Network(subnet+'/'+mask).with_prefixlen
                case ['c','slb','gslb' as rest]|['c','sys',*rest]:
                    break
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
