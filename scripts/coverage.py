import sys, json, re, glob
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v10 as v10
CH=re.compile(r'\[[^\]]{1,15}\]')
def words(t):
    t=re.sub(r'\{.*?\}','',t)
    return re.findall(r"[\w\u00C0-\u1EF9]+", re.sub(CH,'',t).lower())
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for num in [int(x) for x in sys.argv[1:]]:
    s=[x for x in d if x['num']==num][0]
    new=v10.main(num)
    cw=words(s['content']); nw=words(new)
    sset=set(cw)
    missing=[w for w in cw if w not in set(nw)]
    # content words that vanished
    print(f"DLC {num}: cur={len(cw)} new={len(nw)} missing={len(set(cw)-set(nw))} {sorted(set(cw)-set(nw))[:8]}")
