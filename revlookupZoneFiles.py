'''
[Input]
2개의 파일을 읽어들인다.
A file: IPv4 list line by line
B file: 확인이 필요한 도메인의 zone file

[Output]
1개의 파일
Z file: IPv4, host name pair list
예시)
172.244.136.242,  web.cornflower.co.kr

[Howto]
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python revlookupZoneFiles.py [ip list file A] [zone file B]
     e.g.) python revlookupZoneFiles.v.0.0.1.py reqested-ips.txt zone.file
- A 파일을 {policy name:[ip list]} dictionary 로 저장한다.
- B 파일을 한 라인씩 읽으면서 {policy name:[ip list]}를 검색해서 policy name이 있으면 policy의 source, destination, port 순으로 읽어서 list를 만든다.
- source, destination 리스트 중 dictionary 의 [ip list]와 중복되는 ip가 존재하면 [ip list]를 대신 파일에 저장한다.
- 나머지 list를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of B file example:
;--------------------------------------------------
; DNS Resource Records(zone_name : cornflower.co.kr file_name : db-co.kr.cornflower)
;--------------------------------------------------
@ 		IN 		SOA 		intns.google.com. root.intns.google.com. (
 		2020060301      ;serial
 		10800           ;refresh
 		3600            ;retry
 		604800          ;expire
 		86400)          ;minimum 	;EndOfRR
  		IN 		A 		3.17.33.245  	;EndOfRR
  		IN 		NS 		intns.google.com. 	;EndOfRR
  		IN 		NS 		relay.google.com. 	;EndOfRR
  		IN 		MX 		100 	spam 	;EndOfRR
;--------------------------------------------------
;Deleted Resource Records
;//label 		IN 		A 		3.17.33.172  	;EndOfRR
;//sp 		IN 		A 		3.17.33.209  	;EndOfRR
;--------------------------------------------------
web 		IN 		A 		172.244.136.242  	;EndOfRR
aws 		IN 		A 		172.244.136.46  	;EndOfRR
'''
#!/usr/bin/env python3
import mmap            # to read a file and map it to memory
import argparse        # to take arguments and process them
import re              # regular expression
from datetime import datetime

### global variables
THIS_IS_DOMAIN='DNS Resource Records(zone_name'
THIS_IS_RR=';EndOfRR'
COMMENT_FLAG=';'


#OUTPUT_FILE='output-reverse-nslookup-' + str(date.today()) + '.csv'  # 결과 파일 이름
OUTPUT_FILE='zonefile-search-' + datetime.now().strftime("%Y%m%d-%H%M") + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('ip_list_file', type=argparse.FileType('r'), help="a file with a list of IPs to lookup")
    parser.add_argument('zone_file', type=argparse.FileType('r'), help="a zone file for a domain within which the lookup happens")

    args = parser.parse_args()

    ips = []
    with args.ip_list_file as ipList:
        for line in ipList:
            # https://stackoverflow.com/questions/15340582/python-extract-pattern-matches
            ips.append((re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+',line)).group(0)) # IP 추출 ## https://docs.python.org/3/library/re.html

    with args.zone_file as zone, \
        open(OUTPUT_FILE, 'w') as out_file:
        out_file.write("IP, Domain Host\n")
        for line in zone:
            if THIS_IS_DOMAIN in line: #if the line is a start of a policy
                domain = (re.search(r'(?<=zone_name\s:\s)[\-\.\w]+\s',line)).group(0).rstrip() # zone_name : 뒤에 나올 수 있는 domain name 추출 (delimiter= ':' or ' ')
            elif THIS_IS_RR in line:
                if COMMENT_FLAG not in line[0]:
                    ipLinkedMatch = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+',line)) # 아래 테스트 구문과 분리한 이유: AttributeError: 'NoneType' object has no attribute 'group'
                    if ipLinkedMatch:   # regex search에서 매칭되는 것을 찾지 못하면 'None' 값을 돌려준다.
                        ipLinked = ipLinkedMatch.group(0)
                        if ipLinked in ips:
                            subdomain = (re.search(r'[\-\.\w]+[\s]+(?=IN)',line))  # 아래 테스트 구문과 분리한 이유: AttributeError: 'NoneType' object has no attribute 'group'
                            if subdomain:   # regex search에서 매칭되는 것을 찾지 못하면 'None' 값을 돌려준다.
                                host = subdomain.group(0).rstrip() + '.' + domain
                            else:
                                host = domain
                            out_file.write("%s, %s\n" % (ipLinked, host))
