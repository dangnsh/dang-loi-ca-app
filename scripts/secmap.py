import json, re
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==280][0]
# show section map
lines=s['content'].splitlines()
cur=None
for i,l in enumerate(lines):
    m=re.match(r'^\[(.+)\]$',l.strip())
    if m: cur=m.group(1)
    elif l.strip(): print(f"{str(cur):18} | {l.strip()[:70]}")
