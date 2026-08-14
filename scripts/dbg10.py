import json, re, glob, sys
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v5 as v5
import pdfplumber
n=10
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==n][0]
pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{n:03d}_*.pdf')[0]
gold=v5.build_content(pdf, s['title'])
print("=== GOLDEN FULL ===")
print(gold)
print("\n=== PDF PPAGE 0 raw text ===")
with pdfplumber.open(pdf) as p:
    print((p.pages[0].extract_text() or '')[:500])
