'''
2개의 파일 (policy, ip pair 리스트가 있는 파일 A, Security policies가 있는 파일 B)을 읽어들인다.
A format: policy id, ip pair list line by line
B format: Fortigate FW shell 에서 'show firewall policy' 명령어의 output을 텍스트로 저장한 파일
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
    edit 613
        set uuid 39cc2bc0-f5e4-51e6-f2ef-3e6248b08523
        set srcintf "DMZ"
        set dstintf "BACKBONE"
        set srcaddr "h2.27.133.207" "h2.27.133.206"
        set dstaddr "h10.243.17.17"
        set action accept
        set schedule "always"
        set service "tcp49"
        set logtraffic all
        set capture-packet enable
        set auto-asic-offload disable
        set comments "default rule"
    next
    edit 741
        set name "pol191101-0110"
        set uuid 3b8f06d6-b427-51e9-582f-309464493874
        set srcintf "Untrust"
        set dstintf "DMZ"
        set srcaddr "all"
        set dstaddr "h2.27.133.16"
        set action accept
        set schedule "always"
        set service "HTTP"
        set logtraffic all
        set auto-asic-offload disable
    next
    edit 549
        set name "pol160814-0110"
        set uuid 0b2bbd02-69e0-51e6-0dd0-ee5ca17bcf3d
        set srcintf "BACKBONE"
        set dstintf "DMZ"
        set srcaddr "h10.24.29.43" "h10.24.29.48" "h10.1.30.7" "h10.1.30.8" "h10.24.26.37"
        set dstaddr "h2.27.133.19" "h2.27.133.16"
        set action accept
        set schedule "always"
        set service "tcp7011" "tcp7411" "tcp7012" "tcp7412" "tcp7102" "tcp7422" "tcp7103" "tcp7423"
        set logtraffic all
        set comments "pol160814-0110"
    next
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
from datetime import datetime


### global variables
FOLLOWING_IS_POLICY='config firewall policy'
THIS_IS_POL='edit'
THIS_IS_POL_NAME='set name'
THIS_IS_POL_NAME_L='set comments'
THIS_IS_END_OF_POL='next'
THIS_IS_ACTION='set action'
THIS_IS_FROM='set srcintf'
THIS_IS_TO='set dstintf'
FOLLOWING_IS_SRC='set srcaddr'
FOLLOWING_IS_DST='set dstaddr'
#THIS_IS_PROTO='set service'
THIS_IS_DPORT='set service'
SRC_FLAG='src'
DST_FLAG='dst'

now = datetime.now()
OUTPUT_FILE='output-' + OUTPUT_FOR + now.strftime("%Y%m%d") + '-' + now.strftime("%H%M") + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('pair_file', type=argparse.FileType('r'), help="a file with a list of policy name and ip pairs")
    parser.add_argument('policy_file', type=argparse.FileType('r'), help="output for 'show firewall policy'")

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
        out_file.write("No,From,To,Policy Name,Source,Destination,Service/Port")

        for line in p_file: ## enumeration is for src/dst ips to be accumulated and written in the output file
            if THIS_IS_POL in line: #if the line is a start of a policy
                policy = (re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',') # Policy: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':' or ' ' and ',')
                if policy in policyIPsPair:
                    out_file.write("\r\n%d," % (k))
                    k += 1
                    nPorts = 0
                    skip = False
                else:
                    skip = True
            elif not skip:
                if THIS_IS_FROM in line:
                    out_file.write("%s," % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                    regexTemp = re.escape(THIS_IS_TO) + r'\s[_\-\w]+'
                    out_file.write("%s,%s," % ((re.search(regexTemp,line)).group(0).replace(THIS_IS_TO + ' ', ''), policy))
                elif FOLLOWING_IS_SRC in line:
                    out_file.write("\"")
                    ipList = []
                elif FOLLOWING_IS_DST in line:
                    ############## To write SRC IP list into an output file #################
                    ### WARNING: 삭제 예정인 ip가 src 와 dst에서 각각 있다면 아래 검사는 실패한다.
                    ###          따라서 요청된 ip가 여러 구간(VDI, trust, untrust 등등)에 걸쳐 있지 않도록 주의한다.
                    #out_file.write("\"") # 위에서 이미 처리
                    if set(policyIPsPair[policy]).issubset(set(ipList)):
                        for ip in policyIPsPair[policy]:
                            out_file.write("%s" % ip)
                    else:
                        for ip in ipList:
                            out_file.write("%s " % ip)
                    ####################################
                    out_file.write("\",")
                    ipList = []
                elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):   #### This only searches for IPv4 addresses
                    ### https://stackoverflow.com/questions/1038824/how-do-i-remove-a-substring-from-the-end-of-a-string-in-python
                    ipTemp = re.sub(r'/32$', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0))
                    ipList.append(ipTemp)
                elif THIS_IS_PROTO in line:  ## This line can be repeated within one policy.
                    if not nPorts: ## 파일에 한번만 쓰도록 하기 위하여.
                        ############## To write DST IP list into an output file #################
                        ### WARNING: 삭제 예정인 ip가 src 와 dst에서 각각 있다면 아래 검사는 실패한다.
                        ###          따라서 요청된 ip가 여러 구간(VDI, trust, untrust 등등)에 걸쳐 있지 않도록 주의한다.
                        out_file.write("\"")
                        if set(policyIPsPair[policy]).issubset(set(ipList)):
                            for ip in policyIPsPair[policy]:
                                out_file.write("%s" % ip)
                        else:
                            for ip in ipList:
                                out_file.write("%s " % ip)
                        ####################################
                        out_file.write("\",")
                    out_file.write("%s " % ((re.search(r'(?<=:\s)[_\-\w]+,',line)).group(0).rstrip(',')))
                elif THIS_IS_DPORT in line:
                    start = int((re.search(r'(?<=\[)[\d]+\-',line).group(0)).rstrip('-'))
                    end   = int((re.search(r'(?<=\-)[\d]+\]',line).group(0)).rstrip(']'))
                    nThisSrv = end - start
                    if not nThisSrv:
                        out_file.write("%d " % (start))
                    else:
                        out_file.write("%d~%d " % (start, end))
                    nPorts += 1 + nThisSrv
