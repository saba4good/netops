'''
2개의 파일 (ip 리스트가 있는 파일 A, Security policies가 있는 파일 B)을 읽어들인다.
A format: ip list line by line
B format: Fortigate FW shell 에서 'show firewall policy' 명령어의 output을 텍스트로 저장한 파일
C format: Fortigate FW shell 에서 'show firewall addrgrp' 명령어의 output을 텍스트로 저장한 파일
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python extractPolicies.v.1.0.5.py [ip list file A] [show firewall policy output file B]
A 파일을 'ips'라는 list로 저장해두고, B 파일을 한 라인씩 읽으면서 ips를 검색해서 있으면 결과 파일에 저장한다.

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
end

Parts of C file example:
FW-A (FWNAME) $ show firewall addrgrp
config firewall addrgrp
    edit "grp-what"
        set uuid 7dbf0bke-1686-51e6-9389-56e8b189fa99
        set member "h2.27.133.17" "h2.27.133.16" "h2.27.133.27"
    next
    edit "grp-example"
        set uuid 7dbf1do0-1686-51e6-a64b-258p4cf58ffz
        set member "h10.24.29.43" "h10.24.29.48" "h10.1.30.8" "h10.24.26.37"
    next
end
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
from datetime import datetime
### Global variables
THIS_IS_BEG_OF_BLOCK='edit'  # Policy/address group paragraph가 시작하는 것을 알 수 있는 구문
### https://stackoverflow.com/questions/32490629/getting-todays-date-in-yyyy-mm-dd-in-python
now = datetime.now()
POLICY_FILE_REV='policies-revised-' + now.strftime("%Y%m%d") + '-' + now.strftime("%H%M") + '.txt'  # IP range 를 개별 IP로 변환한 policies 파일 이름
OUTPUT_FILE='output-policy-ip-' + now.strftime("%Y%m%d") + '-' + now.strftime("%H%M") + '.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('indiv_ip_file', type=argparse.FileType('r', encoding='UTF-8'), help="a file with a list of IPs'")
    parser.add_argument('policy_file', type=argparse.FileType('r', encoding='UTF-8'), help="output for 'show firewall policy'")
    parser.add_argument('addrgrp_file', type=argparse.FileType('r', encoding='UTF-8'), help="output for 'show firewall addrgrp'")
    
    args = parser.parse_args()
    
    ## range로 묶여있는 ip를 개별 IP로 풀어서 policy file 다시 쓰기
    ## reference: https://stackoverflow.com/questions/49964998/getting-attributeerror-enter-when-using-csv-readeropen
    with args.policy_file as p_file, \
         open(POLICY_FILE_REV, 'w', encoding='UTF-8') as p_rev_file:
        for line in p_file:
            line_chg = line
            if re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+-[\d]+', line):
                ip_range = (re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+-[\d]+', line)).group(0)
                network  = (re.search(r'[\d]+\.[\d]+\.[\d]+', ip_range)).group(0)
                host_start = int((re.search(r'[\d]+-', ip_range)).group(0).replace('-',''))
                host_end  = int((re.search(r'-[\d]+', ip_range)).group(0).replace('-',''))
                indiv_ips_str = ''
                for host in range(host_start, host_end+1):
                    indiv_ips_str += ' "' + network + str(host) + '"'
                line_chg = line.replace(ip_range, indiv_ips_str)
            p_rev_file.write(line_chg)
    

    ips = [ip.rstrip('\n') for ip in args.indiv_ip_file]  # ip가 있는 파일에서 ip 를 list로 추출
    with open(POLICY_FILE_REV, 'r', encoding='UTF-8') as p_file, \
         args.addrgrp_file as g_file, \
         open(OUTPUT_FILE, 'w') as out_file:
        for line in g_file:
            if THIS_IS_BEG_OF_BLOCK in line: #if the line is a start of a address group
                grp_name = re.search(r'\".*\"',line)  # edit 뒤에 나올 수 있는 group 이름 추출 (delimiter= '"')
                if grp_name:
                    grp_name = re.search(r'\".*\"',line).group(0).replace('"', '')
                    #print("Group: %s\n" % grp_name)
                else:
                    grp_name = None
            elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line):  ## IPv4 정보가 있는 line인지 확인한다
                for ip in ips:
                    if ip in line:
                        if grp_name:
                            out_file.write("%s, %s\n" % (grp_name, ip))
                        else:
                            print('Error: Group name not found')
        for line in p_file:
            if THIS_IS_BEG_OF_BLOCK in line: #if the line is a start of a policy
                ### 1) re.search() returns an object; so to get a string found, use returned_object.group(0)
                ### reference: https://stackoverflow.com/questions/15340582/python-extract-pattern-matches
                ### 2) '(?<=...)' is a positive lookbehind assertion. 이것을 사용하려면 ...에 해당하는 string이 fixed length여야 한다.
                ### reference: https://docs.python.org/3/library/re.html
                policy_id = re.search(rf'(?<={THIS_IS_BEG_OF_BLOCK}[\s])[\d]+',line)  # edit 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ' ')
                if policy_id:
                    policy_id = (re.search(rf'(?<={THIS_IS_BEG_OF_BLOCK}[\s])[\d]+',line)).group(0)  # edit 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ' ')
                    print("ID: %s\n" % policy_id)
                else:
                    policy_id = None
            elif re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', line):  ## IPv4 정보가 있는 line인지 확인한다
                for ip in ips:
                    if ip in line:
                        if policy_id:
                            out_file.write("%s, %s\n" % (policy_id, ip))
                            # https://stackoverflow.com/questions/47078585/python-f-write-is-not-taking-more-arguments
                        else:
                            print('Error: Policy name not found')
