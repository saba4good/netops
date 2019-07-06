'''
[프로그램 사용법]
python ip-finder-v.x.x.x.py A-file B-file
e.g. 예를 들어 다음과 같이 명령어를 쳐준다. (단, A-file과 B-file 은 프로그램 파일과 같은 디렉토리에 있어야 한다.)
Users\A47905\Documents\Work\codes\Ezwel>python ip-finder-v.1.0.3.py Ezwel-2019-02-27-policy.log CSR-694945-ips.txt

[파일 설명]
2개의 파일 (Security policies가 있는 파일 A, ip 리스트가 있는 파일 B)을 읽어들인다.
A format: Juniper FW shell 에서 'show security policies detail | no-more' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
B format: ip list line by line
B 파일을 'ips'라는 list로 저장해두고, A 파일을 한 라인씩 읽으면서 ips를 검색해서 하나라도 있으면 candidates라는 리스트로 저장한다.

https://stackoverflow.com/questions/1347791/unicode-error-unicodeescape-codec-cant-decode-bytes-cannot-open-text-file

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
### global variables
THIS_IS_POL='Policy:'
THIS_IS_ACTION='action-type:'
THIS_IS_FROM='From zone:'
THIS_IS_TO='To zone:'
FOLLOWING_IS_SRC='Source addresses:'
FOLLOWING_IS_DST='Destination addresses:'
THIS_IS_PROTO='IP protocol:'
THIS_IS_DPORT='Destination port range:'
OUTPUT_FILE='policies-formatted-output.txt'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('policy_file', type=argparse.FileType('r'))
    parser.add_argument('pair_file', type=argparse.FileType('r'))

    args = parser.parse_args()
    
	policyIPsPair = dict()
	prevPol = ''
	with args.pair_file as pairs:
	    for line in pairs:
		    thePolicy = (re.search(r'[_\-\w]+,',line)).rstrip(',') # 정책 이름 추출 (delimiter= before ',')
			theIP     = (re.search(r',\s[_\-\w]+',line)).strip(', ') # IP 추출 (delimiter= after ',')
			print("'",thePolicy, "' : '", theIP, "'")
			if thePolicy == prevPol:
			    policyIPsPair[thePolicy].append(theIP)
			else:
			    policyIPsPair[thePolicy] = [theIP]
			    prevPol = thePolicy

    with args.policy_file as p_file, \
         open(OUTPUT_FILE, 'w') as out_file:
		skip = false
		k = 1
        for line in p_file:
            if THIS_IS_POL in line: #if the line is a start of a policy
                policy = (re.search(r':\s[_\-\w]+,',line)).strip(': ').rstrip(',') # Policy: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':' or ' ' and ',')
				if policy in policyIPsPair:
				    out_file.write("%d\) " % (k))
					k += 1
				    skip = false
				else:
				    skip = true
            elif not skip:
			    if THIS_IS_FROM in line:
				    out_file.write("%s->" % ((re.search(r':\s[_\-\w]+,',line)).strip(': ').rstrip(',')))
					regexTemp = re.escape(THIS_IS_TO) + r':\s[_\-\w]+'
					out_file.write("%s 구간" % ((re.search(regexTemp,line)).replace(THIS_IS_TO + ': ', '')))
				elif FOLLOWING_IS_SRC in line:
				    out_file.write("- SIP: \n")
				elif FOLLOWING_IS_DST in line:
				    out_file.write("- DIP: \n")
				elif re.search(r'[\d]+\.[\d]+\.[\d]+/[\d]+', line):   #### This only searches for IPv4 addresses
				    out_file.write("%s\n" % re.search(r'[\d]+\.[\d]+\.[\d]+/[\d]+', line))
				
				    
				    
                for ip in ips:
                    if (line.find(ip) != -1):
                        # candidates.append(the_policy)
                        if the_policy:
                            r_file.write("%s, %s\n" % (the_policy.group()[1:len(the_policy.group())-1], ip))
                            # https://stackoverflow.com/questions/47078585/python-f-write-is-not-taking-more-arguments
                            # print(the_policy.group()[1:len(the_policy.group())-1], ' , ', ip)
                        else:
                            print('Error: Policy name not found')

