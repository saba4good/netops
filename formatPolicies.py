'''
2개의 파일 (policy, ip pair 리스트가 있는 파일 A, Security policies가 있는 파일 B)을 읽어들인다.
A format: policy name, ip pair list line by line
B format: Juniper FW shell 에서 'show security policies detail | no-more' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python formatPolicies.v.1.0.1.py [policy-ip list file A] [show security policies detail output file B]
- A 파일을 {policy name:[ip list]} dictionary 로 저장한다.
- B 파일을 한 라인씩 읽으면서 {policy name:[ip list]}를 검색해서 policy name이 있으면 policy의 source, destination, port 순으로 읽어서 list를 만든다.
- source, destination 리스트 중 dictionary 의 [ip list]와 중복되는 ip가 존재하면 [ip list]를 대신 파일에 저장한다.
- 나머지 list를 포맷하여 파일에 저장한다.
references:
- https://stackoverflow.com/questions/7427101/simple-argparse-example-wanted-1-argument-3-results
- https://stackoverflow.com/questions/20063/whats-the-best-way-to-parse-command-line-arguments

'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
#global variables
THIS_IS_POL='Policy:'  # Policy paragraph가 시작하는 것을 알 수 있는 구문 (모든 정책은 'Policy:'로 시작함)
THIS_IS_SIP='Source:'  # Source ip paragraph가 시작하는 것을 알 수 있는 구문
THIS_IS_DIP='Destination:'  # Destination ip paragraph가 시작하는 것을 알 수 있는 구문
OUTPUT_FILE='formatted-policies-output.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('policy_ip_pair_file', type=argparse.FileType('r'), required=True, help="a file with a list of policy name and ip pairs")
    parser.add_argument('policy_file', type=argparse.FileType('r'), required=True, help="log for 'show security policies detail | no-more'")
    
    args = parser.parse_args()
    #args.policy_file
    for line in args.policy_ip_pair_file:
        ####

    
    ips = [ip.rstrip('\n') for ip in args.indiv_ip_file]  # ip가 있는 파일에서 ip 를 list로 추출
    with args.policy_file as p_file, \
         open(OUTPUT_FILE, 'w') as r_file:
        for line in p_file:
            if (line.find(THIS_IS_POL) != -1): #if the line is a start of a policy
                the_policy = re.search(r'[:\s][_\-\w]+,',line) # Policy: 뒤에 나올 수 있는 정책 이름 추출 (delimiter= ':' or ' ' and ',')
            else:
                for ip in ips:
                    if (line.find(ip) != -1):
                        # candidates.append(the_policy)
                        if the_policy:
                            r_file.write("%s, %s\n" % (the_policy.group()[1:len(the_policy.group())-1], ip))
                            # https://stackoverflow.com/questions/47078585/python-f-write-is-not-taking-more-arguments
                            # print(the_policy.group()[1:len(the_policy.group())-1], ' , ', ip)
                        else:
                            print('Error: Policy name not found')
