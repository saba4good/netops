'''
This is to verify hosts and its IP address in a DNS A record
Input file: domain name, host name, IP address
예제:
 * 추가 할 호스트 , IP
1)도메인 : ez.com
추가 할 호스트 , IP
호스트 : fast IP :192.231.44.170
호스트 : m.fast IP :192.231.44.170
2)도메인 : tree.com
추가 할 호스트 , IP
호스트 : fast IP :192.231.44.210
사용방법: 해당 파이선 프로그램과 input 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python verifyARecord.py [input file ] [CSR ID]
예제:
λ python verifyARecord.py test02.txt 617893
domains:    ['fast.ez.com', 'm.fast.ez.com', 'fast.tree.com']
IPs:        ['192.231.44.170', '192.231.44.170', '192.231.44.210']
권한 없는 응답:
권한 없는 응답:
권한 없는 응답:
Verification result:  {'fast.ez.com': True, 'm.fast.ez.com': True, 'fast.tree.com': True}
'''
#!/usr/bin/env python3
import argparse        # commandline arguments
import re              # regular expression
import dns.resolver    # to use this library, the package has to be installed  'sudo apt install python3-dnspython'
#from datetime import date
from subprocess import check_output  ### to use windows command https://stackoverflow.com/questions/14894993/running-windows-shell-commands-with-python
### Global variables
THIS_IS_ROOT='도메인'  # domain paragraph가 시작하는 것을 알 수 있는 구문
### https://stackoverflow.com/questions/32490629/getting-todays-date-in-yyyy-mm-dd-in-python
#OUTPUT_FILE='output-nslookup-' + str(date.today()) + '.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    #parser.add_argument('dns_req_file', type=argparse.FileType('r', encoding='UTF-8'))
    parser.add_argument('dns_req_file', type=argparse.FileType('r'))
    parser.add_argument('csr_id', type=str, nargs='?', default='000000')  ### nargs='?' make the argument optional with a default value
    args = parser.parse_args()

    ### https://stackoverflow.com/questions/4033723/how-do-i-access-command-line-arguments-in-python
    outfile = 'CSR-' + args.csr_id + '-output-nslookup.txt'  # 결과 파일 이름

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
                theRoot = (re.search(r'(?<=[:\s])[\.0-9a-zA-Z]+',line)).group(0)  # 도메인 뒤에 나올 수 있는 domain name 추출 (pattern: alphabets or dot)
                #print("the root: ", theRoot)
            elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line):  ## IPv4 정보가 있는 line인지 확인한다
                if theRoot in re.search(r'(?<=[:\s])[\.\-0-9a-zA-Z]+',line).group(0):  ## 요청 파일의 host name 필드에 도메인 네임이 함께 있는지를 테스트한다.
                    domains.append(re.search(r'(?<=[:\s])[\.\-0-9a-zA-Z]+',line).group(0))  ## 예시: 호스트: blog.ez.com
                else:
                    domains.append(re.search(r'(?<=[:\s])[\.\-0-9a-zA-Z]+',line).group(0) + "." + theRoot)
                ipMappingList.append(re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line).group(0))

    print("domains:   ", domains)
    print("IPs:       ", ipMappingList)

    ipMappedList = []
    with open(outfile, 'w') as r_file:
        for domain in domains:
            ### https://stackoverflow.com/questions/13842116/how-do-we-get-txt-cname-and-soa-records-from-dnspython
            ### https://stackoverflow.com/questions/3898363/set-specific-dns-server-using-dns-resolver-pythondns
            print("domain: ", domain)
            ### https://stackoverflow.com/questions/9245067/is-it-reasonable-in-python-to-check-for-a-specific-type-of-exception-using-isins
            try:
                answer = dns.resolver.query(domain, "A")
                for data in answer:
                    r_file.write("\nnslookup %s\n%s" % (domain, data.address))
                    ipMappedList.append(data.address)
            except dns.resolver.NXDOMAIN:
                r_file.write("\nnslookup %s" % (domain))
                r_file.write("\nNo such domain %s\n" % (domain))
    #print("IPs mapped: ", ipMappedList)
    verification = dict()
    for idx, ipMapped in enumerate(ipMappedList):
        if ipMapped == ipMappingList[idx]:
            verification[domains[idx]] = True
        else:
            verification[domains[idx]] = False
    print("Verification result: ", verification)
