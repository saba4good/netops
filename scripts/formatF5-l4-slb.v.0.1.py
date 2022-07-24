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

## before real svr numbers in a config file
HOSTNAME_FINDER='sys global-settings'
FLAG_HOSTNAME=False
START_OF_SETTINGS='ltm global-settings'
START_OF_REALS='/c/slb/real'
START_OF_GROUPS='/c/slb/group'

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
OUTPUT_COLUMNS='Vip, Vport, Rip, Rports, SLB method, Health Check, Virt, Group No, RealSvr No, Misc., Description'
#
if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 1개
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_file', type=argparse.FileType('r'), help="log for 'list'")

    args = parser.parse_args()
    #########################################################################
    ######### Config file processing ########################################
    ######### health check : [profile_id, ip, ports, type, logexp] ##########
    ######### real  : [real No., rip, rports, description] ##################
    ######### group : [group No., slb method, [real No.s'], description ] ###
    ######### virt  : [virt No., vip, vport, group No., description ] #######
    with args.cfg_file as cfg_file:
        for line in cfg_file:

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
