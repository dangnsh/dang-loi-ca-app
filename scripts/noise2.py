import sys, json, re, glob, os
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v10 as v10
import align_v5 as v5
d=json.load(open('/tmp/dlc/src/data/songs.json'))
DUP=re.compile(r'(\[[^\]]{1,15}\])\s*\1')
# count noise in raw golden build_content for all songs 6-300
dup=0; zero=0; ok=0; files=0
dup_examples=[]
CH=re.compile(r'\[[^\]]{1,15}\]')
for s in d:
    if s['num']<=5: continue
    pdfs=glob.glob(f'/tmp/dlc/public/sheets/DLC_{s["num"]:03d}_*.pdf')
    if not pdfs: continue
    files+=1
    try:
        g=v5.build_content(pdfs[0], s['title'])
    except Exception as e:
        print('ERR',s['num'],e); continue
    if DUP.search(g):
        dup+=1
        if len(dup_examples)<5:
            m=DUP.search(g); seg=g[max(0,m.start()-30):m.end()+30]
            dup_examples.append((s['num'],seg))
    if CH.findall(g)==[]: zero+=1
    else: ok+=1
print(f"files={files} with_dup={dup} zero_chords={zero} ok={ok}")
for n,seg in dup_examples:
    print('  DLC',n,':',seg.replace('\n',' | '))
