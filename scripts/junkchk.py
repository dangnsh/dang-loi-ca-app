import json, re, glob, sys
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v5 as v5
CH=re.compile(r'\[[^\]]{1,15}\]')
def words(t):
    t=re.sub(r'\{.*?\}','',t)
    t=re.sub(r'//.*','',t)
    t=re.sub(r'^\s*\[[^\]]*\]\s*$','',t,flags=re.M)
    return re.findall(r"[\w\u00C0-\u1EF9]+", re.sub(CH,'',t).lower())
d=json.load(open('/tmp/dlc/src/data/songs.json'))
# inspect DLC 35 (has many drops) current content for junk
for n in [35,39]:
    s=[x for x in d if x['num']==n][0]
    print(f"==== DLC {n} current first 3 lines ====")
    for l in s['content'].splitlines()[:3]:
        print('   ',l[:140])
