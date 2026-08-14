import json, re, glob, sys
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v5 as v5
CH=re.compile(r'\[[^\]]{1,15}\]')
def words(t):
    t=re.sub(r'\{.*?\}','',t)
    t=re.sub(r'//.*','',t)                 # strip comments
    t=re.sub(r'^\s*\[[^\]]*\]\s*$','',t,flags=re.M)  # strip section-only lines
    return re.findall(r"[\w\u00C0-\u1EF9]+", re.sub(CH,'',t).lower())
d=json.load(open('/tmp/dlc/src/data/songs.json'))
reg={}; files=0
for s in d:
    if s['num']<=5: continue
    pdfs=glob.glob(f'/tmp/dlc/public/sheets/DLC_{s["num"]:03d}_*.pdf')
    if not pdfs: continue
    files+=1
    g=v5.build_content(pdfs[0], s['title'])
    cw=set(words(s['content'])); gw=set(words(g))
    missing=cw-gw
    if missing: reg[s['num']]=sorted(missing)[:8]
print(f"files={files} songs_with_dropped_words={len(reg)}")
big=[n for n,m in reg.items() if len(m)>2]
print("songs dropping >2 words:", len(big))
print("sample:", dict(list(reg.items())[:12]))
