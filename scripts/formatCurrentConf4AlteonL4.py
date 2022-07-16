'''
Objectives:
Alteon L4 로그 파일에서 현재 세팅을 csv 파일 포맷으로 만든다.
Input:
3개의 파일을 읽어들인다.
A format: '/cfg/dump' 명령어의 output을 텍스트로 저장한 파일
B format: '/stats/slb/dump' 명령어의 output을 텍스트로 저장한 파일
C format: '/cfg/slb/cur' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하고, 로그 파일을 나누어서 2개의 파일로 만든다.)
방법: 해당 파이선 프로그램과 A 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatCurrentConf4AlteonL4.v.1.0.1.py [log file A] [log file B]

- A 파일을 한 라인씩 읽으면서 dictonary 를 만든다.
"/c/slb/group" ... vport 라인의 시작: Vgroup No (key)
"metric" ... metric 라인의 시작(없을 수 있음): metric (value)

- B 파일을 한 라인씩 읽으면서 dictonary 를 만든다.
"Real server [\d]+ stats:" ... RealSvr No 라인의 시작: RealSvr No (key pair 중 하나)
"100.100.100.240                                0" ... No of Current Sessions (value pair 중 하나)
"Instance Health check: " ... Rport 라인의 시작: Rport, Status (key pair, value pair 각각)

- C 파일을 한 라인씩 읽으면서 테이블(list)를 만든다.
"Current virtual servers settings:" ... 이전까지는 볼 필요 없음.
"[0-9]+: IP4 " ... VIP 라인의 시작: Vindex, Vip
"action group, rport" ... vport 라인의 시작(한 vip 에 여러개 있을 수 있음): Vport, Rport, Vgroup No
"real servers:" ... real servers 라인 전에
"[0-9]+: [\d]+\.[\d]+\.[\d]+\.[\d]+" ... Real IP 라인의 시작: RealSvr No, Rip

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
## for virtual port group metric settings processing
DEFAULT_METRIC='leastConnections'
IS_VGRP='/c/slb/group'
IS_METRIC='metric'
INIT_VALUE='-1'

## for virtual port group stats processing
#IS_RSVR='Real server [\d]+ stats:'
#RealSvr No, Rport

## for virtual servers settings log processing
START_OF_SETTINGS='Current virtual servers settings:'
#IS_VIP='[0-9]+: IP4 '
IS_VPORT='action group, rport'
#IS_RIP='[0-9]+: [\d]+\.[\d]+\.[\d]+\.[\d]+'
# Output file의 column 순서 (0부터 시작함)
IDX_VIP=0
IDX_VINDEX=1
IDX_VPORT=2
IDX_VGROUP_NO=3
IDX_G_METRIC=4
IDX_RIP=5
IDX_RSVR_NO=6
IDX_RPORT=7
IDX_CURRSTAT=8
IDX_CURRSESS=9
LAST_IDX=IDX_CURRSESS ## 맨 마지막 순서인 인덱스명

# Tuple
I_CURRSESS = 0
I_CURRSTAT = 1

#
INIT_FLAG=-1
FLAG_VIP=1
FLAG_VPORT=2
FLAG_RIP=3


OUTPUT_FILE='output-l4-settings' + str(date.today()) + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 3개
    parser = argparse.ArgumentParser()
    parser.add_argument('metric_file', type=argparse.FileType('r'), help="log for '/cfg/dump'")
    parser.add_argument('stats_file', type=argparse.FileType('r'), help="log for '/stats/slb/dump'")
    parser.add_argument('slb_file', type=argparse.FileType('r'), help="log for '/cfg/slb/cur'")

    args = parser.parse_args()

    ########################################
    ######### Metric settings processing #######
    metrDic = {}
    vGroupNo = '0'
    with args.metric_file as metric_file:
        for line in metric_file:
            if IS_VGRP in line:
                try:
                    if metrDic[vGroupNo] == INIT_VALUE:  ### test if the privous virtual group is all set. (Alteon은 metric이 default인 경우, 해당 라인이 config에 없다. 따라서 다음 vgroup 에서 확인해줘야함.)
                        metrDic[vGroupNo] = DEFAULT_METRIC
                except KeyError:  ### when the key isn't in the dictonary
                    pass
                vGroupNo = (re.search(r'(?<=/c/slb/group\s)[\d]+', line)).group(0) ## extract the virtual group number from the line.
                metrDic[vGroupNo] = INIT_VALUE
            elif IS_METRIC in line:
                metrDic[vGroupNo] = (re.search(r'(?<=metric\s)[\w]+', line)).group(0)
        try:
            if metrDic[vGroupNo] == INIT_VALUE:
                metrDic[vGroupNo] = DEFAULT_METRIC
        except ValueError:
            pass
    #print ("metrDic = ", metrDic)
    ########################################
    ######### Current Stats processing #######
    statsDic = {}
    with args.stats_file as stats_file:
        for line in stats_file:
            if re.search(r'Real server [\d]+ stats:', line):
                rSvrNo = (re.search(r'(?<=Real server\s)[\d]+', line)).group(0) ## extract the real server number from the line.
            elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+[\s]+[\d]+', line):
                currSessions = (re.search(r'(?<=\s)[\d]+(?=\s)', line)).group(0) ## look-ahead와 look-behind를 쓰려면 character 갯수가 정해져야 하므로, 이렇게밖에 안됨. 다른 방법으로는 if test에서 쓰인 string을 전체 캡쳐하고 거기서 다시 추출하는 방법이 있겠음.
            elif re.search(r'Instance Health check:\s', line):
                rPort = (re.search(r'(?<=,\sport\s)[\w]+(?=,)', line)).group(0)
                currState = (re.search(r'(?<=,\s)[\w]+$', line)).group(0)
                #### 다른 파일에는 아래 포트의 경우, 포트 번호가 아닌 서비스명을 사용하므로 해당 내용을 변경해야 함.
                if rPort == '80':
                    rPort = 'http'
                elif rPort == '443':
                    rPort = 'https'
                statsDic[(rSvrNo, rPort)] = (currSessions, currState) ## I_CURRSESS = 0; I_CURRSTAT = 1
                #print("rSvrNo, rPort: ",rSvrNo, rPort)
                #print("currSessions, currState: ", statsDic[(rSvrNo, rPort)])
    #print ("statsDic = ", statsDic)
    ##############################################################################
    ######### The rest of SLB settings and output processing ##########
    with args.slb_file as r_file, \
        open(OUTPUT_FILE, 'w') as out_file:
        for line in r_file:
            if START_OF_SETTINGS in line:   ### 프로세싱 필요한 라인을 찾는다.
                break
        prevFlag = INIT_FLAG
        idx = 0
        settingsTable = []
        for line in r_file: ## Output file will be written at the end of each policy. ## 위에서 'break'된 라인 바로 이후부터 프로세싱함.
            if re.search(r'[\d]+\:\sIP4\s', line):
                settingsTable.append(["" for i in range(LAST_IDX+1)]) ## 새로운 데이터 row를 만든다.
                #### To see if there's anonmally
                '''
                difference = len(settingsTable) - idx
                if difference != 1:
                    print("***** NEW   ** Difference: ", difference, ", length of settingsTable: ", len(settingsTable), ", idx = ", idx)
                    print("      settingsTable[idx]:          ", settingsTable[idx])
                    print("      settingsTable[Last element]: ", settingsTable[-1])
                '''
                #################################
                settingsTable[-1][IDX_VINDEX] = (re.search(r'[\d]+(?=\:\sIP4\s)', line)).group(0)  ## 맨 마지막에 만들어진 데이터 row를 변경함.
                settingsTable[-1][IDX_VIP] = (re.search(r'(?<=\:\sIP4\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0)
                prevFlag = FLAG_VIP
            elif re.search(r'action group, rport', line):
                if prevFlag == FLAG_RIP:
                    settingsTable.append(copy.deepcopy(settingsTable[-1]))  ## 맨 마지막 데이터 row를 복사해서 새로운 데이터 row를 만든다.
                #### To see if there's anonmally
                '''
                difference = len(settingsTable) - idx
                if difference != 1:
                    print("***** VPORT ** Difference: ", difference, ", length of settingsTable: ", len(settingsTable), ", idx = ", idx)
                    print("      settingsTable[idx]:          ", settingsTable[idx])
                    print("      settingsTable[Last element]: ", settingsTable[-1])
                '''
                #################################
                settingsTable[-1][IDX_VPORT] = (re.search(r'[\w]+(?=\:\sredirect\s)', line)).group(0)
                settingsTable[-1][IDX_VGROUP_NO] = (re.search(r'(?<=,\sgroup\s)[\d]+', line)).group(0)
                settingsTable[-1][IDX_G_METRIC] = metrDic[settingsTable[-1][IDX_VGROUP_NO]]
                settingsTable[-1][IDX_RPORT] = (re.search(r'(?<=,\srport\s)[\w]+', line)).group(0)
                prevFlag = FLAG_VPORT
            elif re.search(r'[\d]+:\s[\d]+\.[\d]+\.[\d]+\.[\d]+', line):
                if prevFlag == FLAG_RIP:
                    ### https://www.geeksforgeeks.org/copy-python-deep-copy-shallow-copy/
                    settingsTable.append(copy.deepcopy(settingsTable[-1]))   ## deepcopy() 를 이용하지 않으면 call by reference 로 복사하여 새로운 것을 편집하면 예전 것도 변경됨.
                #### To see if there's anonmally
                '''
                difference = len(settingsTable) - idx
                if difference != 1:
                    print("***** RIP   ** Difference: ", difference, ", length of settingsTable: ", len(settingsTable), ", idx = ", idx)
                    print("      settingsTable[idx]:          ", settingsTable[idx])
                    print("      settingsTable[Last element]: ", settingsTable[-1])
                '''
                #################################
                settingsTable[-1][IDX_RSVR_NO] = (re.search(r'[\d]+(?=\:\s[\d])', line)).group(0)
                settingsTable[-1][IDX_RIP] = (re.search(r'(?<=[\d]\:\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) ## "re.error: look-behind requires fixed-width patter"로 인해 ":" 앞에 오는 숫자는 하나만 보는 걸로 수정함.
                #print("settingsTable: ", settingsTable[idx] )
                settingsTable[-1][IDX_CURRSTAT] = statsDic[(settingsTable[-1][IDX_RSVR_NO], settingsTable[-1][IDX_RPORT])][I_CURRSTAT]
                settingsTable[-1][IDX_CURRSESS] = statsDic[(settingsTable[-1][IDX_RSVR_NO], settingsTable[-1][IDX_RPORT])][I_CURRSESS]
                idx += 1
                prevFlag = FLAG_RIP

        out_file.write("Vip, Vindex, Vport, Group No, Metric, Rip, RealSvr No, Rport, Status, No. of Current Sessions\n")
        for row in settingsTable:
            for j, value in enumerate(row):
                out_file.write(value)
                if j != LAST_IDX:
                    out_file.write(", ")
                else:
                    out_file.write("\n")
