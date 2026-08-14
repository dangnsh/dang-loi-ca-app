import sys, json, os, glob
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
d=json.load(open('/tmp/dlc/src/data/songs.json'))
num=int(sys.argv[1])
s=[x for x in d if x['num']==num][0]
pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')[0]
print("TITLE:", s.get('title'))
print("HAS META:", [l for l in s['content'].splitlines() if l.strip().startswith('//') or l.strip().startswith('{')])
print("="*40)
print("V5 GOLDEN:")
print(v5.build_content(pdf, s['title']))
print("="*40)
print("CURRENT META/SECTIONS:")
for l in s['content'].splitlines():
    ls=l.strip()
    if ls.startswith('//') or ls.startswith('{') or ls.startswith('['):
        print(repr(ls[:60]))
