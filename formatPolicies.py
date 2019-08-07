'''
2개의 파일 (policy, ip pair 리스트가 있는 파일 A, Security policies가 있는 파일 B)을 읽어들인다.
A format: policy name, ip pair list line by line
B format: Juniper FW shell 에서 'show security policies detail | no-more' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatPolicies.v.1.0.1.py [policy-ip pair list file A] [show security policies detail output file B]
     e.g.) python formatPolicies.v.0.0.1.py output-policy-IP-2019-07-08.txt FW-20190626.log
- A 파일을 {policy name:[ip list]} dictionary 로 저장한다.
- B 파일을 한 라인씩 읽으면서 {policy name:[ip list]}를 검색해서 policy name이 있으면 policy의 source, destination, port 순으로 읽어서 list를 만든다.
- source, destination 리스트 중 dictionary 의 [ip list]와 중복되는 ip가 존재하면 [ip list]를 대신 파일에 저장한다.
- 나머지 list를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of B file example:
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
THIS_IS_FROM='From zone:'
THIS_IS_TO='To zone:'
FOLLOWING_IS_SRC='Source addresses:'
FOLLOWING_IS_DST='Destination addresses:'
THIS_IS_PROTO='IP protocol:'
THIS_IS_DPORT='Destination port range:'
SRC_FLAG='src'
DST_FLAG='dst'

OUTPUT_FILE='output-policies-formatted-' + str(date.today()) + '.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('pair_file', type=argparse.FileType('r'), help="a file with a list of policy name and ip pairs")
    parser.add_argument('policy_file', type=argparse.FileType('r'), help="log for 'show security policies detail | no-more'")

    args = parser.parse_args()

    policyIPsPair = dict()
    prevPol = ''
    with args.pair_file as pairs:
        for line in pairs:
            # https://stackoverflow.com/questions/15340582/python-extract-pattern-matches
            thePolicy = (re.search(r'[_\-\w]+,',line)).group(0).rstrip(',') # 정책 이름 추출 (delimiter= before ',')
            theIP     = (re.search(r'(?<=,\s)[\d]+\.[\d]+\.[\d]+\.[\d]+',line)).group(0) # IP 추출 (delimiter= after ',') ## https://docs.python.org/3/library/re.html
            print(thePolicy+": "+theIP+";")
            if thePolicy == prevPol:
                policyIPsPair[thePolicy].append(theIP)
            else:
                policyIPsPair[thePolicy] = [theIP]
                prevPol = thePolicy

    with args.policy_file as p_file, \
        open(OUTPUT_FILE, 'w') as out_file:
        skip = False
        k = 1
        for line in p_file: ## enumeration is for src/dst ips to be accumulated and written in the output file
            if THIS_IS_POL in line: #if the line is a start of a policy
                policy = (re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',') # Policy: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':' or ' ' and ',')
                if policy in policyIPsPair:
                    out_file.write("\n%d) " % (k))
                    k += 1
                    nPorts = 0
                    skip = False
                else:
                    skip = True
            elif not skip:
                if THIS_IS_FROM in line:
                    out_file.write("%s->" % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                    regexTemp = re.escape(THIS_IS_TO) + r'\s[_\-\w]+'
                    out_file.write("%s 구간 %s\n" % ((re.search(regexTemp,line)).group(0).replace(THIS_IS_TO + ' ', ''), policy))
                elif FOLLOWING_IS_SRC in line:
                    out_file.write("- SIP: \n")
                    ipList = []
                elif FOLLOWING_IS_DST in line:
                    ############## To write SRC IP list into an output file #################
                    ### WARNING: 삭제 예정인 ip가 src 와 dst에서 각각 있다면 아래 검사는 실패한다.
                    ###          따라서 요청된 ip가 여러 구간(VDI, trust, untrust 등등)에 걸쳐 있지 않도록 주의한다.
                    if set(policyIPsPair[policy]).issubset(set(ipList)):
                        for ip in policyIPsPair[policy]:
                            out_file.write("%s  (삭제)\n" % ip)
                    else:
                        for ip in ipList:
                            out_file.write("%s\n" % ip)
                    ####################################
                    out_file.write("- DIP: \n")
                    ipList = []
                elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):   #### This only searches for IPv4 addresses
                    ### https://stackoverflow.com/questions/1038824/how-do-i-remove-a-substring-from-the-end-of-a-string-in-python
                    ipTemp = re.sub(r'/32$', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0))
                    ipList.append(ipTemp)
                elif THIS_IS_PROTO in line:
                    if not nPorts: ## 파일에 한번만 쓰도록 하기 위하여.
                        ############## To write DST IP list into an output file #################
                        ### WARNING: 삭제 예정인 ip가 src 와 dst에서 각각 있다면 아래 검사는 실패한다.
                        ###          따라서 요청된 ip가 여러 구간(VDI, trust, untrust 등등)에 걸쳐 있지 않도록 주의한다.
                        if set(policyIPsPair[policy]).issubset(set(ipList)):
                            for ip in policyIPsPair[policy]:
                                out_file.write("%s  (삭제)\n" % ip)
                        else:
                            for ip in ipList:
                                out_file.write("%s\n" % ip)
                        ####################################
                        out_file.write("- PORT: \n")
                    out_file.write("%s " % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                elif THIS_IS_DPORT in line:
                    start = int((re.search(r'(?<=\[)[\d]+\-',line).group(0)).rstrip('-'))
                    end   = int((re.search(r'(?<=\-)[\d]+\]',line).group(0)).rstrip(']'))
                    nThisSrv = end - start
                    if not nThisSrv:
                        out_file.write("%d\n" % (start))
                    else:
                        out_file.write("%d~%d\n" % (start, end))
                    nPorts += 1 + nThisSrv
