'''
Objectives:
각 서버/호스트의 NIC MAC address를 받아, L2 장비 mac-address table과 비교하여 매핑시킨다.
Input:
2개의 파일 (각 Host의 MAC address가 있는 파일 A, 각 장비의 mac-table이 있는 파일 B)을 읽어들인다.
A format: hostname line, then mac address line (1라인에 1개 주소)
B format: 'sh mac address-table | exc CPU' 의 결과값
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python mapHost2Mac.py [file A] [file B]
'''
#!/usr/bin/env python3
import argparse
import re              # regular expression
from datetime import date
### Global variables
IS_HOSTNAME='hostname:'  # hostname이 있는 라인
### https://stackoverflow.com/questions/32490629/getting-todays-date-in-yyyy-mm-dd-in-python
OUTPUT_FILE='output-hostname-2-mac-' + str(date.today()) + '.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('hostname_mac_file', type=argparse.FileType('r'))
    parser.add_argument('mactable_file', type=argparse.FileType('r', encoding='UTF-8'))  ## error: UnicodeDecodeError: 'cp949' codec can't decode byte 0xec in position 0: illegal multibyte sequence

    args = parser.parse_args()

    with args.hostname_mac_file as hm_file:
        hMac = []
        for line in hm_file:
            if IS_HOSTNAME in line: #if the line is a start of mac addresses for a host
                theHost = (re.search(r'(?<=hostname:)[_\-\w]+',line)).group(0)  # hostname: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':')
            elif re.search(r'[\w][\w][\w][\w]\.[\w][\w][\w][\w]\.[\w][\w][\w][\w]', line):  ## MAC 정보가 있는 line인지 확인한다
                hMac.append([theHost, (re.search(r'[\w][\w][\w][\w]\.[\w][\w][\w][\w]\.[\w][\w][\w][\w]',line)).group(0).lower()])
    #print("Hostname-to-mac: \n", hMac)

    with args.mactable_file as mt_file, \
        open(OUTPUT_FILE, 'w') as o_file:
        for line in mt_file:
            for hm in hMac:
                if hm[1] in line:
                    #hm.extend([sw,vlan,port])
                    sw = (re.search(r'[\w]+\s',line)).group(0).rstrip()
                    vlan = (re.search(r'(?<=\s)[\d]+\s',line)).group(0).rstrip()
                    port = (re.search(r'(?<=\s)G[\w/]+',line)).group(0)
                    print("sw,vlan,port: ", sw,vlan,port)
                    o_file.write("%s,%s,%s,%s,%s\n" % (hm[0], hm[1], sw,vlan,port))
