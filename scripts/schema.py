import json
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==25][0]
print("KEYS:", list(s.keys()))
for k,v in s.items():
    if k!='content':
        print(f"  {k}: {str(v)[:80]}")
print("content first 200:", s['content'][:200])
