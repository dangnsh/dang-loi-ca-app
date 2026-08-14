import json, re
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for n in [27,62]:
    s=[x for x in d if x['num']==n][0]
    print("="*50)
    print(f"DLC {n} — {s['title']}")
    lines=s['content'].splitlines()
    cur=None
    for l in lines:
        m=re.match(r'^\[(.+)\]$',l.strip())
        if m: cur=m.group(1)
        elif l.strip(): print(f"[{cur}] {l.strip()[:90]}")
