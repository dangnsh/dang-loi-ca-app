import sys, json, glob, re
sys.path.insert(0,'/tmp/dlc/scripts'); import prod2
d=json.load(open('/tmp/dlc/src/data/songs.json'))
n=10
s=[x for x in d if x['num']==n][0]
print("=== NEW (prod2.build) ===")
new,_=prod2.build(n)
print(new)
print("\n=== PDF page0 raw (verse markers) ===")
import pdfplumber
pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{n:03d}_*.pdf')[0]
with pdfplumber.open(pdf) as p:
    txt=p.pages[0].extract_text() or ''
    print(txt[:600])
