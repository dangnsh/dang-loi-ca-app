import sys, json, os
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v8 as v8
num=27
d=json.load(open('/tmp/dlc/src/data/songs.json'))
s=[x for x in d if x['num']==num][0]
pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
v1,v2,extra=v8.build_pdf_streams(pdf)
print("PDF V1 stream words:", [w for w,_ in v1])
print("PDF V1 chords     :", [c for _,c in v1])
print("PDF V2 has:", len(v2), "extra rows:", len(extra))
# content words
import re
contwords=re.findall(v8.WORDRE, s['content'])
print("CONTENT words:", contwords[:40])
print("n content words:", len(contwords))
