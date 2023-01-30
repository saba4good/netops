'''
v.0.1:
- config/bigip.conf 파일만을 사용한다.
Objectives:
F5 L4 list 파일에서 현재 SLB 설정 현황을 csv 파일 포맷으로 만든다.
Output: OUTPUT_COLUMNS
Input:
설정 파일인 config/bigip.conf 파일 (ucs 파일 백업에서도 확인 가능)
방법: 해당 파이선 프로그램과 input 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatF5-l4-bigipconf.py [log file A] [hostname]
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
from itertools import zip_longest
from datetime import date
##### global variables ########################################################
## for slb method settings processing
DEFAULT_SLB_METHOD='round robin'
PREFIX='/Common/'
INIT_VALUE='-1'

FLAG_PERSIS=1
FLAG_POOL=2
FLAG_VIRT=3
FLAG_VR_PERSIS=4
FLAG_HOSTNAME=5
FLAG_NAT=6

IDX_ND_IP=0
IDX_ND_MON=1
ND_LAST_IDX=IDX_ND_MON

IDX_PL_RIPS=0
IDX_PL_RMON=1
IDX_PL_SLB=2
PL_LAST_IDX=IDX_PL_SLB

IDX_VIP=0
IDX_VPORT=1+IDX_VIP
IDX_RIP=1+IDX_VPORT
IDX_SLB_METHOD=1+IDX_RIP
IDX_PERSIS=1+IDX_SLB_METHOD
IDX_HEALTH=1+IDX_PERSIS
IDX_PIP=1+IDX_HEALTH
IDX_VIRT=1+IDX_PIP
LAST_IDX=IDX_VIRT ## 맨 마지막 순서인 인덱스명
OUTPUT_COLUMNS='Vip, Vport, Rip, SLB method, Persis, Health Check, PIP SNAT Pool, Virt Name\n'
#
if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 1개
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_file', type=argparse.FileType('r'), help="log for 'list'")
    parser.add_argument('hostname', type=str, help="host name")

    args = parser.parse_args()
    #########################################################################
    ####### monitor - node - persistence - pool - fastl4 DSR - virtual ######
    ## monitor : vip, vport
    ## node : rip, monitor
    ## persistence : persistence timeout
    ## pool : slb_method, rip, (rport), (monitor)
    ## fastl4 DSR : idle timeout
    ## virtual : vip, vport, persistence, pool, fastl4, dsr
    ################ persistence - pool - virtual ###########################
    with args.cfg_file as cfg_file:
        for line in cfg_file:
            match line.split():
                case ['ltm','default-node-monitor','{']:
                    break
        ## create realProfiles dictionary from config file
        realProfiles = dict()
        which_section = INIT_VALUE
        poolProfiles = dict()
        for line in cfg_file:
            match line.split():
                case ['ltm', 'node', node_id, '{']:
                    realProfiles[node_id]=["" for i in range(ND_LAST_IDX+1)]
                case ['address', ip]:
                    realProfiles[node_id][IDX_ND_IP] = ip
                case ['monitor', monitor]:
                    realProfiles[node_id][IDX_ND_MON] = monitor.replace(PREFIX, '')
                case ['ltm', 'pool', pool_id, '{']:
                    which_section = FLAG_POOL
                    poolProfiles[pool_id]=["" for i in range(PL_LAST_IDX+1)]
                    poolProfiles[pool_id][IDX_PL_SLB] = DEFAULT_SLB_METHOD
                    break
        ## create poolProfiles/snatipProfiles/snatplProfiles dictionaries from config file
        snatipProfiles = dict()
        snatplProfiles = dict()
        settingsTable = []
        for line in cfg_file:
            match line.split():
                case ['ltm', 'pool', pool_id, '{']:
                    which_section = FLAG_POOL
                    poolProfiles[pool_id]=["" for i in range(PL_LAST_IDX+1)]
                    poolProfiles[pool_id][IDX_PL_SLB] = DEFAULT_SLB_METHOD
                case ['members', '{']:
                    pass
                case [member_rport, '{']:
                    if which_section == FLAG_POOL:
                        if poolProfiles[pool_id][IDX_PL_RIPS] != '':
                            poolProfiles[pool_id][IDX_PL_RIPS] += ';'
                        if poolProfiles[pool_id][IDX_PL_RMON] != '':
                            poolProfiles[pool_id][IDX_PL_RMON] += ';'
                        try:
                            member_id = member_rport.split(':')[0]
                        except ValueError:
                            print("error in ", member_rport)
                            continue
                        poolProfiles[pool_id][IDX_PL_RIPS] += realProfiles[member_id][IDX_ND_IP]
                        poolProfiles[pool_id][IDX_PL_RMON] += realProfiles[member_id][IDX_ND_MON]
                case ['address', ip]:
                    if which_section == FLAG_NAT:
                        snatipProfiles[snat_id] = ip
                case ['load-balancing-mode', slb_method]:
                    poolProfiles[pool_id][IDX_PL_SLB] = slb_method
                case ['}']:
                    if re.search(r'^}', line):
                        which_section =  INIT_VALUE
                case ['priority-group', priority]:
                    if poolProfiles[pool_id][IDX_PL_SLB] == DEFAULT_SLB_METHOD:
                        poolProfiles[pool_id][IDX_PL_SLB] = ''
                    else:
                        poolProfiles[pool_id][IDX_PL_SLB] += ';'
                    poolProfiles[pool_id][IDX_PL_SLB] += 'Priority('+ priority +')'
                case ['ltm', 'snat-translation', snat_id, '{']:
                    which_section = FLAG_NAT
                case ['ltm', 'snatpool', snatpool_id, '{']:
                    which_section = FLAG_NAT
                case [snat_member]:
                    try:
                        if snatplProfiles[snatpool_id] != '':
                            snatplProfiles[snatpool_id] += ';'
                        snatplProfiles[snatpool_id] += snatipProfiles[snat_member]
                    except KeyError:
                        continue
                case ['ltm', 'virtual', virt_id, '{']:
                    subsection = INIT_VALUE
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = virt_id.replace(PREFIX, '')
                    break
        ## create a settingsTable list from config file
        for line in cfg_file:
            match line.split():
                case ['ltm', 'virtual', virt_id, '{']:
                    subsection = INIT_VALUE
                    settingsTable.append(["" for i in range(LAST_IDX+1)])
                    settingsTable[-1][IDX_VIRT] = virt_id.replace(PREFIX, '')
                case ['destination', vip_port]:
                    (settingsTable[-1][IDX_VIP], settingsTable[-1][IDX_VPORT]) = (vip_port.replace(PREFIX, '')).split(':')
                case ['pool', pool_id_used]:
                    if subsection == FLAG_NAT:
                        settingsTable[-1][IDX_PIP] = pool_id_used.replace(PREFIX, '')
                    elif subsection == INIT_VALUE:
                        settingsTable[-1][IDX_SLB_METHOD] = poolProfiles[pool_id_used][IDX_PL_SLB]
                        for rip, rmon, rslb in zip_longest(poolProfiles[pool_id_used][IDX_PL_RIPS].split(';'), poolProfiles[pool_id_used][IDX_PL_RMON].split(';'), poolProfiles[pool_id_used][IDX_PL_SLB].split(';'), fillvalue=""):
                            if settingsTable[-1][IDX_RIP] != '':
                                settingsTable.append(copy.deepcopy(settingsTable[-1]))
                            settingsTable[-1][IDX_RIP] = rip
                            settingsTable[-1][IDX_HEALTH] = rmon
                            if rslb != '':
                                settingsTable[-1][IDX_SLB_METHOD] = rslb
                case ['persist', '{']:
                    subsection = FLAG_VR_PERSIS
                case ['source-address-translation', '{']: ## If NAT other than source NAT is used, it should be added in this line as well.
                    subsection = FLAG_NAT
                case [persis_id, '{']:    ## Any sections with one word other than the ones above this line won't work.
                    if subsection == FLAG_VR_PERSIS:
                        settingsTable[-1][IDX_PERSIS] = persis_id.replace(PREFIX, '')
                case ['}']:
                    subsection =  INIT_VALUE
                case ['ltm', 'virtual-address', vip_id, '{']:
                    break

    output_file=args.hostname + '-cfg-' + date.today().strftime('%Y%m%d') + '.csv'  # 결과 파일 이름
    with open(output_file, 'w') as out_file:
        out_file.write(OUTPUT_COLUMNS)
        for row in settingsTable:
            for j, value in enumerate(row):
                out_file.write(value)
                if j != LAST_IDX:
                    out_file.write(", ")
                else:
                    out_file.write("\n")
