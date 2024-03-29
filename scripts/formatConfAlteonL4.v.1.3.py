'''
v.1.3:
- /cfg/dump 파일만을 사용한다.
Objectives:
Alteon L4 로그 파일에서 현재 SLB 설정 현황을 csv 파일 포맷으로 만든다.
Output: OUTPUT_COLUMNS
Input:
'/cfg/dump' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하고, 로그 파일을 나누어서 2개의 파일로 만든다.)
방법: 해당 파이선 프로그램과 A 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatConfAlteonL4.v.1.3.py [log file A]
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

##### global variables ########################################################
## for group slb method settings processing
DEFAULT_SLB_METHOD='leastConnections'
IS_SLB_METHOD='metric'
INIT_VALUE='-1'

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
GP_LAST_IDX=IDX_GP_HC

IDX_VIP=0
IDX_VPORT=1 + IDX_VIP
IDX_RIP=1 + IDX_VPORT
IDX_RPORTS=1 + IDX_RIP
IDX_SLB_METHOD=1 + IDX_RPORTS
IDX_HEALTHCHECK=1 + IDX_SLB_METHOD
IDX_VIRT=1 + IDX_HEALTHCHECK
IDX_GROUP_NO=1 + IDX_VIRT
IDX_RSVR_NO=1 + IDX_GROUP_NO
IDX_NOTES=1 + IDX_RSVR_NO
IDX_DESC=1 + IDX_NOTES
LAST_IDX=IDX_DESC ## 맨 마지막 순서인 인덱스명
OUTPUT_COLUMNS='Vip, Vport, Rip, Rports, SLB method, Health Check, Virt, Group No, RealSvr No, Misc., Description\n'
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
            if HOSTNAME_FINDER in line:
                FLAG_HOSTNAME = True
            elif re.search(r'name', line) and FLAG_HOSTNAME:
                hostname = (re.search(r'(?<=\").+(?=\")', line)).group(0)
                FLAG_HOSTNAME = False
            elif START_OF_SETTINGS in line:   ### 프로세싱 필요한 라인을 찾는다.
                break
        ######### health check : [profile_id, ip, ports, type, logexp] ##########
        healthProfiles = dict()
        hcID = ''
        for line in cfg_file:
            if re.search(r'/c/slb/advhc/health\s[\w_]+', line):
                hcID = (re.search(r'(?<=/c/slb/advhc/health\s)[\w_]+', line)).group(0)
                healthProfiles[hcID]=["" for i in range(HP_LAST_IDX+1)]
                healthProfiles[hcID][IDX_HP_TYPE] = (re.search(r'[\w]+$', line)).group(0)
            elif re.search(r'dport\s[\d]+', line):
                healthProfiles[hcID][IDX_HP_PORT] = (re.search(r'(?<=dport\s)[\d]+', line)).group(0)
            elif re.search(r'dest\s[\d]+', line):
                healthProfiles[hcID][IDX_HP_IP] = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
            elif re.search(r'logexp\s\"', line):
                healthProfiles[hcID][IDX_HP_LOGEXP] = (re.search(r'(?<=\").+(?=\")', line)).group(0)
            elif re.search(r'/c/slb$', line): ## health check 구문을 빠져나가면
                break                         ## for loop을 중단하여 cfg_file을 그만 읽는다.
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
            if re.search(r'/c/slb/real\s[\d]+', line):
                realNo = (re.search(r'(?<=/c/slb/real\s)[\d]+', line)).group(0)
                realProfiles[realNo]=["" for i in range(RP_LAST_IDX+1)]
                hc_ip_ports = ''
            elif re.search(r'rip\s[\d]+\.[\d]+\.[\d]+\.[\d]+', line):
                realProfiles[realNo][IDX_RP_IP] = (re.search(r'(?<=rip\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
            elif re.search(r'name\s\"', line):
                realProfiles[realNo][IDX_RP_DESC] = (re.search(r'(?<=\").+(?=\")', line)).group(0)
            elif re.search(r'health\s[\w_]+', line):
                realProfiles[realNo][IDX_RP_HC] = (re.search(r'(?<=health\s)[\w_]+', line)).group(0)
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
            elif re.search(r'addport\s[\d]+', line):
                if realProfiles[realNo][IDX_RP_PORTS] != '':      ## real ports에 이미 값이 있으면
                    realProfiles[realNo][IDX_RP_PORTS] += ';'     ## 세미콜른을 붙여줘라
                realProfiles[realNo][IDX_RP_PORTS] += (re.search(r'(?<=\s)[\d]+', line)).group(0)
            elif re.search(r'/c/slb/', line) and not re.search(r'/real', line):
                if re.search(r'/c/slb/group', line):
                    groupNo = (re.search(r'(?<=/c/slb/group\s)[\d]+', line)).group(0)
                    groupProfiles[groupNo]=["" for i in range(GP_LAST_IDX+1)]
                    in_group_sec=FLAG_GROUP  ## to set a flag when in the group settings section
                break
        print("real dict : ")
        print("{:<8} {:<20} {:<12} {:<30} {:<20} {:<40}".format('rNo', 'rIP', 'rPorts', 'Desc', 'HC label', 'HC ports'))
        for realSvrNo, realSvr in realProfiles.items():
            rip, rPorts, desc, hc_label, hc_ports = realSvr
            print("{:<8} {:<20} {:<12} {:<30} {:<20} {:<40}".format(realSvrNo, rip, rPorts, desc, hc_label, hc_ports))
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
            if re.search(r'/c/slb/group\s[\d]+', line):
                groupNo = (re.search(r'(?<=/c/slb/group\s)[\d]+', line)).group(0)
                groupProfiles[groupNo]=["" for i in range(GP_LAST_IDX+1)]
            elif re.search(r'add\s[\d]+', line):
                if groupProfiles[groupNo][IDX_GP_SLB] == '':
                    groupProfiles[groupNo][IDX_GP_SLB] = DEFAULT_SLB_METHOD ## 'metric' 구문이 없는 경우, default 값을 사용
                if groupProfiles[groupNo][IDX_GP_RIDS] == '':      ## real rid에 값이 없으면
                    groupProfiles[groupNo][IDX_GP_RIDS] = []
                groupProfiles[groupNo][IDX_GP_RIDS].append((re.search(r'(?<=\s)[\d]+', line)).group(0))
            elif re.search(r'metric\s[\w]+', line):
                groupProfiles[groupNo][IDX_GP_SLB] = (re.search(r'(?<=metric\s)[\w]+', line)).group(0)
            elif re.search(r'name\s\"', line):
                groupProfiles[groupNo][IDX_GP_DESC] = (re.search(r'(?<=\").+(?=\")', line)).group(0)
            elif re.search(r'health\s[\w]+', line):
                groupProfiles[groupNo][IDX_GP_HC] = (re.search(r'(?<=health\s)[\w]+', line)).group(0)
            elif re.search(r'/c/slb/', line) and not re.search(r'/group', line):
                if re.search(r'/c/slb/virt\s[\d]+', line):
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = (re.search(r'(?<=/c/slb/virt\s)[\d]+', line)).group(0)
                    in_virt_sec=FLAG_VIRT
                break
        print("Group dict : ")
        print("{:<8} {:<20} {:<30} {:<30} {:<40}".format('gNo', 'slb', 'rNo', 'Desc', 'HC'))
        for gNo, group in groupProfiles.items():
            slb, rno, desc, hc = group
            print("{:<8} {:<20} {:<30} {:<30} {:<40}".format(gNo, slb, ';'.join(rno), desc, hc))
        ######### virt  : [virt No., vip, vport, group No., description ] #######
        prevFlag = INIT_FLAG
        vip = ''
        if in_virt_sec!=FLAG_VIRT:
            for line in cfg_file:
                if re.search(r'/c/slb/virt\s[\d]+', line):
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = (re.search(r'(?<=/c/slb/virt\s)[\d]+', line)).group(0)
                    break
        ## for pip [(virt No., vport): [srcnet No., pip nat, src ip]]
        ## before writing into the output file, for loop settingsTable to fill in the PIP info
        for line in cfg_file:
            if re.search(r'/c/slb/virt\s[\d]+', line):
                if not re.search(r'/pip$', line):
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = (re.search(r'(?<=/c/slb/virt\s)[\d]+', line)).group(0)
                    if re.search(r'service\s[\d]+', line):
                        settingsTable[-1][IDX_VPORT] = (re.search(r'(?<=service\s)[\d]+', line)).group(0)
                        settingsTable[-1][IDX_VIP] = vip
                else:
                    prevFlag = FLAG_PIP
            elif re.search(r'group\s[\d]+', line):
                settingsTable[-1][IDX_GROUP_NO] = (re.search(r'(?<=group\s)[\d]+', line)).group(0)
            elif re.search(r'rport\s[\d]+', line):
                realSvrs = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_RIDS]
                for realNo in realSvrs:
                    if settingsTable[-1][IDX_RSVR_NO] != '':                     ## real server no. 값이 이미 있으면
                        settingsTable.append(copy.deepcopy(settingsTable[-1]))   ## 테이블 마지막 레코드를 복붙해서 새로 row를 만들자. 단, deepcopy() 를 이용하지 않으면 call by reference 로 복사하여 새로운 것을 편집하면 예전 것도 변경됨.
                    settingsTable[-1][IDX_RSVR_NO] = realNo
                    if groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB] == '':
                        settingsTable[-1][IDX_SLB_METHOD] = DEFAULT_SLB_METHOD ## 'metric' 구문이 없는 경우, default 값을 사용
                    settingsTable[-1][IDX_SLB_METHOD] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_SLB]
                    settingsTable[-1][IDX_HEALTHCHECK] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_HC_IP_PORT]
                    settingsTable[-1][IDX_DESC] = groupProfiles[settingsTable[-1][IDX_GROUP_NO]][IDX_GP_DESC]
                    settingsTable[-1][IDX_RIP] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_IP]
                    settingsTable[-1][IDX_RPORTS] = (re.search(r'(?<=rport\s)[\d]+', line)).group(0)
                    if settingsTable[-1][IDX_RPORTS] == '0':   ## rport 0, 즉 multi port인 경우
                        settingsTable[-1][IDX_RPORTS] = realProfiles[settingsTable[-1][IDX_RSVR_NO]][IDX_RP_PORTS]
            elif re.search(r'vip\s[\d]+\.[\d]+\.[\d]+\.[\d]+', line):
                settingsTable[-1][IDX_VIP] = (re.search(r'(?<=vip\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
                vip = settingsTable[-1][IDX_VIP]
            elif re.search(r'vname\s\"', line):
                settingsTable[-1][IDX_DESC] = (re.search(r'(?<=\").+(?=\")', line)).group(0)
            elif re.search(r'addr\s', line):
                if prevFlag == FLAG_PIP:
                    settingsTable[-1][IDX_NOTES] = 'PIP NAT: ' + (re.search(r'(?<=v4\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
            elif (re.search(r'/c/slb/', line) or re.search(r'/c/l3/', line)) and not re.search(r'virt', line):
                break
            #print("settingsTable: ", settingsTable[idx] )

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
