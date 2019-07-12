'''
This is to verify hosts and its IP address in a DNS A record
Input file: domain name, host name, IP address
예제:
 * 추가 할 호스트 , IP
1)도메인 : ezwel.com

추가 할 호스트 , IP
호스트 : fastbox IP :222.231.44.170
호스트 : m.fastbox IP :222.231.44.170

2)도메인 : weltree.com
추가 할 호스트 , IP
호스트 : fastbox IP :222.231.44.210

사용방법: 해당 파이선 프로그램과 input 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python verifyARecord.v.0.0.1.py [input file ]

'''
#!/usr/bin/env python3
import argparse        # commandline arguments
import re              # regular expression
from datetime import date
from subprocess import check_output  ### to use windows command https://stackoverflow.com/questions/14894993/running-windows-shell-commands-with-python
### Global variables
THIS_IS_ROOT='도메인'  # domain paragraph가 시작하는 것을 알 수 있는 구문
### https://stackoverflow.com/questions/32490629/getting-todays-date-in-yyyy-mm-dd-in-python
OUTPUT_FILE='output-nslookup-' + str(date.today()) + '.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('dns_req_file', type=argparse.FileType('r'))
    args = parser.parse_args()
    
    domains = []
    ipMappingList = []
    #with args.dns_req_file as requests, open(OUTPUT_FILE, 'w') as r_file:
    with args.dns_req_file as requests:
        for line in requests:
            if THIS_IS_ROOT in line: #if the line is a start of a new domain
                ### 1) re.search() returns an object; so to get a string found, use returned_object.group(0)
                ### reference: https://stackoverflow.com/questions/15340582/python-extract-pattern-matches
                ### 2) '(?<=...)' is a positive lookbehind assertion. 이것을 사용하려면 ...에 해당하는 string이 fixed length여야 한다.
                ### reference: https://docs.python.org/3/library/re.html
                theRoot = (re.search(r'(?<=[:\s])[\.a-zA-Z]+',line)).group(0)  # 도메인 뒤에 나올 수 있는 domain name 추출 (pattern: alphabets or dot)
                #print("the root: ", theRoot)
            elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line):  ## IPv4 정보가 있는 line인지 확인한다
                domains.append(re.search(r'(?<=[:\s])[\.a-zA-Z]+',line).group(0) + "." + theRoot)
                ipMappingList.append(re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line).group(0))
                
    print("domains:   ", domains)
    print("IPs:       ", ipMappingList)
    
    commands = ''
    ipMappedList = []
    with open(OUTPUT_FILE, 'w') as r_file:
        for domain in domains:
            commands = "nslookup " + domain
            ### https://stackoverflow.com/questions/14894993/running-windows-shell-commands-with-python
            ### cmd code page 확인하는 방법: D:\>chcp  https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/chcp
            ### https://thecoollife.tistory.com/18
            ### codepage 949 https://en.wikipedia.org/wiki/Unified_Hangul_Code
            lookupOutput = check_output(commands, shell=True).decode(encoding="CP949")
            r_file.write("%s\n%s" % (commands, lookupOutput))
            ### In multiline mode, ^ matches the position immediately following a newline and $ matches the position immediately preceding a newline.
            ### https://stackoverflow.com/questions/587345/regular-expression-matching-a-multiline-block-of-text
            ### https://stackoverflow.com/questions/33232729/how-to-search-for-the-last-occurrence-of-a-regular-expression-in-a-string-in-pyt
            ### https://docs.python.org/3/library/re.html#re.Match.group
            ipMappedList.append(re.search("(?s:.*)(?<=[:\s])([\d]+\.[\d]+\.[\d]+\.[\d]+)", lookupOutput).group(1))
            #ipMappedList.append(re.search(r'(?s:.*)(?-s:[\d]+\.[\d]+\.[\d]+\.[\d]+)', lookupOutput).group(0))
    #print("IPs mapped: ", ipMappedList)
    verification = dict()
    for idx, ipMapped in enumerate(ipMappedList):
        if ipMapped == ipMappingList[idx]:
            verification[domains[idx]] = True
        else:
            verification[domains[idx]] = False
    print("Verification result: ", verification)
