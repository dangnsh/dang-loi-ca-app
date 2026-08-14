import sys, json, glob, re
sys.path.insert(0,'/tmp/dlc/scripts'); import prod2
d=json.load(open('/tmp/dlc/src/data/songs.json'))
n=8
new,_=prod2.build(n)
print("=== DLC",n,"NEW ===")
print(new)
print("\n=== CURRENT (for reference) ===")
print(d[[x['num'] for x in d].index(n)]['content'][:700])
