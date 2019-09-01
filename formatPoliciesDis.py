'''
Input:
1개의 파일 (Security policies가 있는 파일 A)을 읽어들인다.
A format: Juniper FW shell 에서 'show security policies detail | no-more' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
방법: 해당 파이선 프로그램과 A 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatPoliciesDis.v.1.0.1.py [show security policies detail output file A]
     e.g.) python formatPoliciesDis.v.0.0.1.py FW-20190626.log
- A 파일을 한 라인씩 읽으면서 disabled되어 있으면 policy의 source, destination, port 순으로 읽어서 list를 만든다.
- 나머지 list를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of an input file example:
Policy: a_name_for_policy, action-type: permit, State: enabled, Index: 65, Scope Policy: 0
  Policy Type: Configured
  Sequence number: 1
  From zone: VDI, To zone: untrust
  Source addresses:
    h192.168.98.1: 192.168.98.1/32
    h192.168.98.2: 192.168.98.2/32
    object_name21: 192.168.98.3/32
  Destination addresses:
    h192.168.100.1: 192.168.100.1/32
    h192.168.100.2: 192.168.100.2/32
  Application: junos-service1
    IP protocol: udp, ALG: 0, Inactivity timeout: 60
      Source port range: [0-0]
      Destination port range: [181-182]
  Application: junos-service2
    IP protocol: tcp, ALG: 0, Inactivity timeout: 1800
      Source port range: [0-0]
      Destination port range: [49-49]
  Per policy TCP Options: SYN check: No, SEQ check: No
  Session log: at-create, at-close
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
from datetime import date

### global variables
THIS_IS_POL='Policy:'
THIS_IS_ACTION='action-type:'
THIS_IS_STATE='State:'
THIS_IS_FROM='From zone:'
THIS_IS_TO='To zone:'
FOLLOWING_IS_SRC='Source addresses:'
FOLLOWING_IS_DST='Destination addresses:'
THIS_IS_PROTO='IP protocol:'
THIS_IS_DPORT='Destination port range:'
SRC_FLAG='src'
DST_FLAG='dst'
DSB_FLAG='disabled'

#OUTPUT_FILE='output-policies-formatted-' + str(date.today()) + '.txt'  # 결과 파일 이름
OUTPUT_FILE='output-policies-formatted-' + str(date.today()) + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('policy_file', type=argparse.FileType('r'), help="log for 'show security policies detail | no-more'")

    args = parser.parse_args()

    with args.policy_file as p_file, \
        open(OUTPUT_FILE, 'w') as out_file:
        skip = False
        k = 1
        out_file.write("No,Policy Name,Source,Destination,Service/Port")
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
                    for ip in ipList:
                        out_file.write("%s " % ip)
                    out_file.write("\",")
                    ipList = []
                elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):   #### This only searches for IPv4 addresses
                    ### https://stackoverflow.com/questions/1038824/how-do-i-remove-a-substring-from-the-end-of-a-string-in-python
                    ipTemp = re.sub(r'/32$', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0))
                    ipList.append(ipTemp)
                elif THIS_IS_PROTO in line:
                    if not nPorts: ## 파일에 한번만 쓰도록 하기 위하여.
                        out_file.write("\"")
                        for ip in ipList:
                            out_file.write("%s " % ip)
                        out_file.write("\",")
                    out_file.write("%s " % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                elif THIS_IS_DPORT in line:
                    start = int((re.search(r'(?<=\[)[\d]+\-',line).group(0)).rstrip('-'))
                    end   = int((re.search(r'(?<=\-)[\d]+\]',line).group(0)).rstrip(']'))
                    nThisSrv = end - start
                    if not nThisSrv:
                        out_file.write("%d" % (start))
                    else:
                        out_file.write("%d~%d" % (start, end))
                    nPorts += 1 + nThisSrv
