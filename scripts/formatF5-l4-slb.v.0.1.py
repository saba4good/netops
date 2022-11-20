'''
v.0.1:
- list 결과 파일만을 사용한다.
Objectives:
F5 L4 list 파일에서 현재 SLB 설정 현황을 csv 파일 포맷으로 만든다.
Output: OUTPUT_COLUMNS
Input:
'list' 명령어의 output을 텍스트로 저장한 파일
방법: 해당 파이선 프로그램과 input 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatF5-l4-slb.py [log file A]
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
## for slb method settings processing
DEFAULT_SLB_METHOD='round robin'
INIT_VALUE='-1'

FLAG_PERSIS=1
FLAG_POOL=2
FLAG_VIRT=3
FLAG_VR_PERSIS=4
FLAG_HOSTNAME=5
IDX_PL_SLB=0
IDX_PL_RIPS=1
IDX_PL_STATUS=3
PL_LAST_IDX=IDX_PL_STATUS

IDX_VIP=0
IDX_VPORT=1+IDX_VIP
IDX_RIP=1+IDX_VPORT
IDX_SLB_METHOD=1+IDX_RIP
IDX_PERSIS=1+IDX_SLB_METHOD
IDX_SVR_STATUS=1+IDX_PERSIS
IDX_VIRT=1+IDX_SVR_STATUS
LAST_IDX=IDX_VIRT ## 맨 마지막 순서인 인덱스명
OUTPUT_COLUMNS='Vip, Vport, Rip, SLB method, Persis. Timeout, Status, Virt'
#
if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 1개
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_file', type=argparse.FileType('r'), help="log for 'list'")

    args = parser.parse_args()
    #########################################################################
    ####### monitor - node - persistence - pool - fastl4 DSR - virtual ######
    ## monitor : vip, vport
    ## node : rip
    ## persistence : persistence timeout
    ## pool : slb_method, rip, (rport), status, (monitor)
    ## fastl4 DSR : idle timeout
    ## virtual : vip, vport, persistence, pool, fastl4, dsr
    ################ persistence - pool - virtual ###########################
    with args.cfg_file as cfg_file:
        which_section = INIT_VALUE
        persisProfiles = dict()
        poolProfiles = dict()
        settingsTable = []
        for line in cfg_file:
            match line.split():
                case ['ltm', 'persistence', persis_method, persis_id, '{']:
                    which_section = FLAG_PERSIS
                case ['ltm', 'pool', pool_id, '{']:
                    which_section = FLAG_POOL
                    poolProfiles[pool_id]=["" for i in range(PL_LAST_IDX+1)]
                case ['ltm', 'virtual', virt_id, '{']:
                    which_section = FLAG_VIRT
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = virt_id
                case ['address', ip]:
                    if which_section == FLAG_POOL:
                        if poolProfiles[pool_id][IDX_PL_RIPS] != '':
                            poolProfiles[pool_id][IDX_PL_RIPS] += ';'
                        poolProfiles[pool_id][IDX_PL_RIPS] += ip
                case ['state', status]:
                    if which_section == FLAG_POOL:
                        poolProfiles[pool_id][IDX_PL_RIPS] += ':' + status
                case ['destination', ip_port]:
                    if which_section == FLAG_VIRT:
                        settingsTable[-1][IDX_VIP] = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', ip_port)).group(0)
                        settingsTable[-1][IDX_VPORT] = (re.search(r'(?<=:)[\w]+', ip_port)).group(0)
                case ['pool', pool_id_used]:
                    if which_section == FLAG_VIRT:
                        settingsTable[-1][IDX_SLB_METHOD] = poolProfiles[pool_id_used][IDX_PL_SLB]
                        for rip_state in poolProfiles[pool_id_used][IDX_PL_RIPS].split(';'):
                            if settingsTable[-1][IDX_RIP] != '':
                                settingsTable.append(copy.deepcopy(settingsTable[-1]))
                            settingsTable[-1][IDX_RIP] = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', rip_state)).group(0)
                            settingsTable[-1][IDX_SVR_STATUS] = (re.search(r'(?<=:)[\w]+', rip_state)).group(0)
                case ['persist', '{']:
                    if which_section == FLAG_VIRT:
                        which_section = FLAG_VR_PERSIS
                case [opening, '{']:
                    if which_section == FLAG_VR_PERSIS:
                        which_section = FLAG_VIRT
                        settingsTable[-1][IDX_PERSIS] = persisProfiles[opening]
                case ['load-balancing-mode', slb_method]:
                    poolProfiles[pool_id][IDX_PL_SLB] = slb_method
                case ['timeout', time]:
                    if which_section == FLAG_PERSIS:
                        persisProfiles[persis_id] = time
                case ['}']:
                    if re.search(r'^}', line):
                        which_section =  INIT_VALUE
                case ['sys', 'global-settings', '{']:
                    which_section = FLAG_HOSTNAME
                case ['hostname', hostname_domain]:
                    hostname = hostname_domain

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
