'''
2개의 파일 (ip 리스트가 있는 파일 A, Security policies가 있는 파일 B)을 읽어들인다.
A format: ip list line by line
B format: Juniper FW shell 에서 'show security policies detail' 명령어의 output을 텍스트로 저장한 파일
(putty 에서 읽을 수 있는 로그 파일 저장하면 됨.)
방법: 해당 파이선 프로그램과 A, B 파일을 모두 한 폴더 안에 넣어두고, 그 폴더에서 다음 명령으로 실행시킨다.
     python ip-finder-v.1.0.4.py [ip list file A] [show security policies detail output file B]

A 파일을 'ips'라는 list로 저장해두고, B 파일을 한 라인씩 읽으면서 ips를 검색해서 있으면 결과 파일에 저장한다.

'''
#!/usr/bin/env python3
import mmap
import argparse
import re              # regular expression
#global variables
THIS_IS_POL='Policy:'  # Policy paragraph가 시작하는 것을 알 수 있는 구문 (모든 정책은 'Policy:'로 시작함)
OUTPUT_FILE='ip-finder-output.txt'  # 결과 파일 이름

if __name__ == '__main__':
    # 이 프로그램을 실행할 때, 받아들일 arguments 2개
    parser = argparse.ArgumentParser()
    parser.add_argument('indiv_ip_file', type=argparse.FileType('r'))
    parser.add_argument('policy_file', type=argparse.FileType('r'))
    
    args = parser.parse_args()
    args.policy_file
    args.indiv_ip_file

    ips = [ip.rstrip('\n') for ip in args.indiv_ip_file]  # ip가 있는 파일에서 ip 를 list로 추출
    # candidates = []
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

