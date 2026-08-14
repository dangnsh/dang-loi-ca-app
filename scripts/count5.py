import sys, json, glob, re
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
CH=re.compile(r'\[[^\]]{1,15}\]')
def words(t):
    return re.findall(r"[\w\u00C0-\u1EF9]+", re.sub(CH,'',t).lower())
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for num in [1,2,3,4,5]:
    s=[x for x in d if x['num']==num][0]
    pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')[0]
    gold=v5.build_content(pdf, s['title'])
    gw=words(gold)
    # current words excluding section labels/meta/nums
    cw=words(s['content'])
    print(f"DLC {num}: golden={len(gw)} current={len(cw)}")
