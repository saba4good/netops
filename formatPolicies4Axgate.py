'''
Objectives:
Axgate의 정책/snat/dnat 로그 파일에서 정책을 csv 파일 포맷으로 만든다.
Input:
2개의 파일 (snat/dnat 있는 파일 A, 정책 있는 파일 B)을 읽어들인다.
A format: 'show run ip snat profile', 'show run ip dnat profile' 명령어의 output을 텍스트로 저장한 파일 (run 부터의 명령어는 꼭 같아야 함.)
B format: 'show run ip security policy' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하고, 로그 파일을 나누어서 2개의 파일로 만든다.)
방법: 해당 파이선 프로그램과 A 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatPolicies4Axgate.v.1.0.1.py [snat/dnat log file A] [security policy log file B]
     e.g.) python formatPoliciesDis.v.0.0.1.py FW-nat.log FW-policy.log
- A 파일을 한 라인씩 읽으면서 snat dictionary 와 dnat dictionary를 만든다.
- B 파일을 한 라인씩 읽으면서 정책의 source, destination, port 순으로 읽어서 list를 만든다.
- 나머지 list를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of an input file example:
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
from datetime import date

### global variables
## snat or dnat profile log
START_OF_SNAT='run ip snat'
START_OF_DNAT='run ip dnat'
IS_PROFILE='nat profile '
IS_NAT='source' # start phrase of each s/dnat in each profile
STAT_NAT='static'
DYN_NAT='dynamic'
## for policies log file
THIS_IS_POL='ip security policy' # each policy starts with this, and in this line, there's zone, sequence number, and id.
THIS_IS_FROM='from '
THIS_IS_TO='to '
THIS_IS_SRC='source'
IS_SNAT='snat-profile '
THIS_IS_DST='destination'
IS_DNAT='dnat-profile '
THIS_IS_DPORT='service proto'
THIS_IS_ACTION='action' # 'pass' or 'drop'
SRC_FLAG='src'
DST_FLAG='dst'
EN_FLAG='enable' # this line is the last for each policy.

OUTPUT_FILE='output-policies-formatted-' + str(date.today()) + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('nat_file', type=argparse.FileType('r'), help="log for 'show run ip snat profile', 'show run ip dnat profile'")
    parser.add_argument('policy_file', type=argparse.FileType('r'), help="log for 'show run ip security policy'")

    args = parser.parse_args()

    natDic = {}  # leet-mock-0011.py 참조
    with args.nat_file as nat_file:
        snatFlag = False
        dnatFlag = False
        for line in nat_file:
            if IS_NAT in line:
                if dnatFlag == True:
                    if STAT_NAT in line:
                        natDic[profileId].append((re.search(r'(?<=static\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) + " (NAT IP: " + (re.search(r'(?<=destination\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) +")")
                    elif DYN_NAT in line:
                        natDic[profileId].append((re.search(r'(?<=dynamic\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) + " (NAT IP: " + (re.search(r'(?<=destination\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) +")")
                elif snatFlag == True:
                    if STAT_NAT in line:
                        natDic[profileId].append((re.search(r'(?<=source\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) + " (NAT IP: " + (re.search(r'(?<=static\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) +")")
                    elif DYN_NAT in line:
                        natDic[profileId].append((re.search(r'(?<=source\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) + " (NAT IP: " + (re.search(r'(?<=dynamic\s)[\d]+\.[\d]+\.[\d]+\.[\d]+', line)).group(0) +")")
            elif IS_PROFILE in line:
                if dnatFlag == True:
                    profileId = IS_DNAT + (re.search(r'[\d]+$', line)).group(0)
                    natDic[profileId] = []
                elif snatFlag == True:
                    profileId = IS_SNAT + (re.search(r'[\d]+$', line)).group(0)
                    natDic[profileId] = []
            elif START_OF_SNAT in line:
                snatFlag = True
                dnatFlag = False
            elif START_OF_DNAT in line:
                dnatFlag = True
                snatFlag = False
    print("nat: ", natDic)
    '''
    with args.policy_file as p_file, \
        open(OUTPUT_FILE, 'w') as out_file:
        skip = False
        k = 1
        out_file.write("No,Policy ID,Source,Destination,Service/Port,Action")
        for line in p_file: ## enumeration is for src/dst ips to be accumulated and written in the output file
            if THIS_IS_POL in line: #if the line is a start of a policy
                policy = (re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',') # Policy: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':' or ' ' and ',')
                if DSB_FLAG in line:
                    out_file.write("\n%d," % (k))
                    k += 1
                    nPorts = 0
                    skip = False
                else:
                    skip = True
            elif not skip:
                if FOLLOWING_IS_SRC in line:
                    out_file.write("%s," % (policy))
                    ipList = []
                elif FOLLOWING_IS_DST in line:
                    out_file.write("\"")
                    for idx, ip in enumerate(ipList):
                        if idx:
                            out_file.write("\n")
                        out_file.write("%s" % ip)
                    out_file.write("\",")
                    ipList = []
                elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):   #### This only searches for IPv4 addresses
                    ### https://stackoverflow.com/questions/1038824/how-do-i-remove-a-substring-from-the-end-of-a-string-in-python
                    ipTemp = re.sub(r'/32$', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0))
                    ipList.append(ipTemp)
                elif THIS_IS_PROTO in line:
                    if not nPorts: ## 파일에 한번만 쓰도록 하기 위하여.
                        out_file.write("\"")
                        for idx, ip in enumerate(ipList):
                            if idx:
                                out_file.write("\n")
                            out_file.write("%s" % ip)
                        out_file.write("\",")
                    out_file.write("%s" % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                elif THIS_IS_DPORT in line:
                    start = int((re.search(r'(?<=\[)[\d]+\-',line).group(0)).rstrip('-'))
                    end   = int((re.search(r'(?<=\-)[\d]+\]',line).group(0)).rstrip(']'))
                    nThisSrv = end - start
                    if not nThisSrv:
                        out_file.write("%d " % (start))
                    else:
                        out_file.write("%d~%d " % (start, end))
                    nPorts += 1 + nThisSrv
'''
