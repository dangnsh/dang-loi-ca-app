import json, re
d=json.load(open('/tmp/dlc/src/data/songs.json'))
# survey meta forms across songs 6-300
from collections import Counter
forms=Counter()
examples=[]
for s in d:
    if s['num']<=5: continue
    for l in s['content'].splitlines():
        ls=l.strip()
        if ls.startswith('//'):
            forms['//comment']+=1
            if len(examples)<5 and '//' in ls: examples.append((s['num'],ls))
        elif ls.startswith('{'):
            forms['{meta}']+=1
        elif ls and not ls.startswith('[') and not re.search(r'\[[^\]]{1,15}\]',ls):
            # non-lyric leading line w/o chord and w/o bracket
            forms['plainline']+=1
            if len(examples)<8: examples.append((s['num'],'PLAIN:'+ls[:60]))
print(forms)
for n,e in examples[:8]: print(n,e)
