import json, re, sys
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5

d=json.load(open('/tmp/dlc/src/data/songs.json'))
num=int(sys.argv[1])
s=[x for x in d if x['num']==num][0]
pdf=sys.argv[2]
new=v5.build_content(pdf, s['title'])
print("======= V5 NEW =======")
print(new)
print("\n======= CURRENT =======")
print(s['content'])
