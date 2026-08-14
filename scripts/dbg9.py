import json, re, glob, sys
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v5 as v5, align_v10 as v10
import pdfplumber
n=9
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==n][0]
pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{n:03d}_*.pdf')[0]
print("=== CURRENT (first 600) ===")
print(s['content'][:600])
print("\n=== GOLDEN v5 (first 600) ===")
print(v5.build_content(pdf, s['title'])[:600])
print("\n=== PDF raw lyric-ish text page 0 ===")
with pdfplumber.open(pdf) as p:
    print((p.pages[0].extract_text() or '')[:400])
