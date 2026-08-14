import glob, json, re, sys
sys.path.insert(0,'/tmp/dlc/scripts'); import align_v5 as v5
CH=re.compile(r'\[[^\]]{1,15}\]')
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==5][0]
pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_005_*.pdf')[0]
# check raw lyric words in PDF text layer for hyphens
import pdfplumber
with pdfplumber.open(pdf) as p:
    for pi,pg in enumerate(p.pages[:2]):
        ws=pg.extract_words()
        hy=[w['text'] for w in ws if '-' in w['text']]
        print(f"page{pi} hyphenated:", hy[:10])
print("GOLDEN lines:")
print(v5.build_content(pdf, s['title'])[:800])
