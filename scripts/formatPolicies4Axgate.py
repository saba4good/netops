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
- A 파일을 한 라인씩 읽으면서 nat dictionary를 만든다.
- B 파일을 한 라인씩 읽으면서 정책의 source, destination, port, action, state을 읽어서 dictionary를 만든다.
- 각 정책을 읽고 나면 정책 dictionary를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments
Parts of an input file example:
'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
from datetime import datetime

### global variables
## File names
OUTPUT_FOR='for_Axgate_'
## for a snat or dnat profile log processing
START_OF_SNAT='run ip snat'
START_OF_DNAT='run ip dnat'
IS_PROFILE='nat profile '  ## the last white space is important to distinguish this from the starting command of nat profiles
IS_A_NAT='source' # start phrase of each s/dnat in each profile
STAT_NAT='static'
# DYN_NAT='dynamic'
DYN_NAT='any dynamic'  ## destination이 any로 설정된 경우만 확인함 #############################################
IS_SNAT='snat-profile '
IS_DNAT='dnat-profile '
## for a policy log file processing
IS_POL='ip security policy from' # each policy starts with this, and in this line, there's zone, sequence number, and id.
                             # the last white space is important to distinguish this from the starting command of policies
IS_SRC='source'
IS_DST='destination'
IS_NAT='nat-profile'
IS_DPORT='service'
IS_ACTION='action' # 'pass' or 'drop'
IS_STATE='enable' # This can be omitted for disabled policies.
IS_DELIMITER='!' # delimiter for each policy
ENT_SRC=IS_SRC
ENT_DST=IS_DST
ENT_SRV=IS_DPORT
ENT_ACT=IS_ACTION
ENT_STE='state'
PRM_FLAG='pass'
DRP_FLAG='drop'
STE_EN='enabled' #
STE_DS='disabled'
PORT_SNG='dport eq'
PORT_MLT='dport multi'
PORT_RNG='dport range'
#GRP_FLAG='user-group'
GRP_FLAG='group'
ANY_FLAG='any'

#OUTPUT_FILE='output-policies-formatted-' + str(date.today()) + '.csv'  # 결과 파일 이름
now = datetime.now()
OUTPUT_FILE='output-' + OUTPUT_FOR + now.strftime("%Y%m%d") + '-' + now.strftime("%H%M") + '.csv'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('nat_file', type=argparse.FileType('r'), help="log for 'show run ip snat profile', 'show run ip dnat profile'")
    parser.add_argument('policy_file', type=argparse.FileType('r'), help="log for 'show run ip security policy'")

    args = parser.parse_args()

    ########################################
    ######### NAT profile processing #######
    natDic = {}
    with args.nat_file as nat_file:
        snatFlag = False
        dnatFlag = False
        for line in nat_file:
            if IS_A_NAT in line:
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

    ########################################
    ######### Policies processing ##########
    with args.policy_file as p_file, \
        open(OUTPUT_FILE, 'w') as out_file:
        out_file.write("Zone,Policy ID,Source,Destination,Service/Port,Action,State\n")
        polDetails = {}
        for line in p_file: ## Output file will be written at the end of each policy.
            if IS_SRC in line: #if the line has a source address
                if re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):
                    polDetails[ENT_SRC].append(re.sub(r'/32', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0)))
                else:
                    if GRP_FLAG in line:  # IP가 아닌 object로 주소가 구성될 경우를 테스트함.
                        polDetails[ENT_SRC].append((re.search(r'(?<=group\s)[a-zA-Z0-9\.\_]+',line)).group(0)) #그룹명은 알파벳, 숫자, .(닷), _(underscore)
                    else:  # IP로 주소가 구성된 경우 ... 언제 해당? 모르겠음.....
                        polDetails[ENT_SRC].append((re.search(r'(?<=source\s)[a-zA-Z]+',line)).group(0))
            elif IS_DST in line: #if the line has a destination address
                if re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line):
                    polDetails[ENT_DST].append(re.sub(r'/32', '', re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+/[\d]+', line).group(0)))
                else:
                    if GRP_FLAG in line:  # IP가 아닌 object로 주소가 구성될 경우를 테스트함.
                        polDetails[ENT_DST].append((re.search(r'(?<=group\s)[a-zA-Z0-9\.\_]+',line)).group(0)) #그룹명은 알파벳, 숫자, .(닷), _(underscore)
                    elif IS_DNAT in line: # dnat profile로 구성되는 경우
                        polDetails[ENT_DST].extend(natDic[(re.search(r'dnat-profile\s[\d]+',line)).group(0)])  ## if append() is used, the list will be added inside a list
                    else:
                        polDetails[ENT_DST].append((re.search(r'(?<=destination\s)[a-zA-Z]+',line)).group(0))
            elif IS_DELIMITER in line:
                if IS_SRC in polDetails and polDetails[ENT_SRC]:  # after the first policy ID line appeared and source address field has some value in it.
                    if not polDetails[ENT_SRV]:     # when the destination port field didn't appear in the policy details, it means it's "any".
                        polDetails[ENT_SRV].append(ANY_FLAG.capitalize())
                    #### source field formatting ####
                    if len(polDetails[ENT_SRC])>1:  # when sip field has more than one ip in it.
                        out_file.write("\"")
                        for sip in polDetails[ENT_SRC]:
                            if sip != polDetails[ENT_SRC][-1]:
                                out_file.write("%s\n" % sip)
                            else:
                                out_file.write("%s" % sip)
                        out_file.write("\",")
                    else:
                        out_file.write("%s," % polDetails[ENT_SRC][0])
                    #### destination field formatting ####
                    if len(polDetails[ENT_DST])>1:  # when dip field has more than one ip in it.
                        out_file.write("\"")
                        for dip in polDetails[ENT_DST]:
                            if dip != polDetails[ENT_DST][-1]:
                                out_file.write("%s\n" % dip)
                            else:
                                out_file.write("%s" % dip)
                        out_file.write("\",")
                    else:
                        out_file.write("%s," % polDetails[ENT_DST][0])
                    #### service/port field formatting ####
                    if len(polDetails[ENT_SRV])>1:  # when dip field has more than one ip in it.
                        out_file.write("\"")
                        for port in polDetails[ENT_SRV]:
                            if port != polDetails[ENT_SRV][-1]:
                                out_file.write("%s\n" % port)
                            else:
                                out_file.write("%s" % port)
                        out_file.write("\",")
                    else:
                        out_file.write("%s," % polDetails[ENT_SRV][0])
                    out_file.write("%s,%s\n" % (polDetails[ENT_ACT], polDetails[ENT_STE]))
            elif IS_POL in line: #if the line is a start of a policy
                zone = (re.search(r'(?<=from\s)[a-zA-Z\s]+',line)).group(0).rstrip(" ") # from 뒤에 나올 zone 추출 (delimiter= 'from ' and digits)
                policyId = (re.search(r'(?<=id\s)[\d]+$',line)).group(0) # id 뒤에 나올 정책 id 추출 (delimiter= 'id ' and new line)
                out_file.write("%s,%s," % (zone, policyId))
                polDetails = {ENT_SRC:[],ENT_DST:[],ENT_SRV:[],ENT_ACT:PRM_FLAG.capitalize(),ENT_STE:STE_DS.capitalize()} # to initialize policy details
            elif IS_ACTION in line:
                if DRP_FLAG in line:
                    polDetails[ENT_ACT]=DRP_FLAG.capitalize()
            elif IS_STATE in line:
                polDetails[ENT_STE]=STE_EN.capitalize()
            elif IS_DPORT in line: #if the line has a service port defined
                if 'service proto' in line:
                    protocol = (re.search(r'(?<=proto\s)[\w]+',line)).group(0) # proto 뒤에 나올 protocol name 추출 (delimiter= 'proto ' and white space)
                    if PORT_SNG in line:
                        polDetails[ENT_SRV].append(protocol + (re.search(r'(?<=dport eq\s)[\d]+',line)).group(0))
                    elif PORT_MLT in line:
                        #ports = ((re.search(r'(?<=dport multi\s)[\d\s]+',line)).group(0)).split() # to make a list from a string that comes after 'dport multi'
                        #(protocol + port for port in ports)                                       # then this line add a string to every elements in a list
                        # references: https://stackoverflow.com/questions/2050637/appending-the-same-string-to-a-list-of-strings-in-python
                        # 여기만 extend()를 쓰는 이유: for 구문을 돌리면서 '''list'''(정확히는 iterable)를 만들어 내는데, 이것을 원래 리스트에 붙이기 위함임.
                        polDetails[ENT_SRV].extend(protocol + port for port in ((re.search(r'(?<=dport multi\s)[\d\s]+',line)).group(0)).split())
                    elif PORT_RNG in line:
                        #ports = ((re.search(r'(?<=dport multi\s)[\d\s]+',line)).group(0)).split() # to make a list from a string that comes after 'dport multi'
                        #(protocol + port for port in ports)                                       # then this line add a string to every elements in a list
                        # references: https://stackoverflow.com/questions/2050637/appending-the-same-string-to-a-list-of-strings-in-python
                        rangeNumList = ((re.search(r'(?<=dport range\s)[\d\s]+',line)).group(0)).split()
                        startN = rangeNumList[0]
                        endN = rangeNumList[1]
                        polDetails[ENT_SRV].append(protocol + startN + "-" + endN)
                    else: ## port number 가 없는 경우 (예: icmp)
                        polDetails[ENT_SRV].append(protocol)
                elif 'service-group' in line:
                    polDetails[ENT_SRV].append((re.search(r'(?<=service-group\s)[a-zA-Z0-9\-]+',line)).group(0))
            elif IS_SNAT in line:
                sProfile = IS_SNAT + (re.search(r'[\d]+$', line)).group(0)
                if ANY_FLAG in polDetails[ENT_SRC]:
                    polDetails[ENT_SRC].extend(natDic[sProfile])
                elif natDic[sProfile]:
                    sips = polDetails[ENT_SRC]
                    polDetails[ENT_SRC] = []
                    for sip in sips:
                        ### next() references: https://stackoverflow.com/questions/9542738/python-find-in-list
                        #polDetails[ENT_SRC].append(next(ipNat for ipNat in natDic[sProfile] if sip in ipNat))
                        #re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', sip).group(0) ## sip 필드 중 subnet을 제외한 IP 부분만 획득
                        #polDetails[ENT_SRC].append(next(ipNat for ipNat in natDic[sProfile] if re.search(r'[\d]+\.[\d]+\.[\d]+\.[\d]+', sip).group(0) in ipNat)) ## 1:1 NAT만 해당
                        #### 하기 모델은 24bits subnet 만 검사함.
                        #polDetails[ENT_SRC].append(next(ipNat for ipNat in natDic[sProfile] if re.search(r'[\d]+\.[\d]+\.[\d]+\.', sip).group(0) in ipNat))
                        polDetails[ENT_SRC].append(sip + " (NAT IP: " + (re.search(r'(?<=NAT IP:\s)[\d]+\.[\d]+\.[\d]+\.[\d]+',next(ipNat for ipNat in natDic[sProfile] if re.search(r'[\d]+\.[\d]+\.[\d]+\.', sip).group(0) in ipNat))).group(0) + ")")
