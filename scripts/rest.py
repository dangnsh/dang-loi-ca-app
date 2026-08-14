import pdfplumber, re
pdf='/tmp/dlc/public/sheets/DLC_001_An_Chua_day_day.pdf'
NOTE=re.compile(r'^[œ˙™Ó‰]+$')
with pdfplumber.open(pdf) as p:
    pg=p.pages[0]
    words=pg.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
    yg={}
    for w in words: yg.setdefault(round(w['top']),[]).append(w)
    for y in sorted(yg):
        if 90<=y<=175:
            ws=sorted(yg[y],key=lambda w:w['x0'])
            toks=[]
            for w in ws:
                tag='NT' if NOTE.match(w['text']) else 'W'
                toks.append(f"{w['text']}@{round(w['x0'])}")
            print(f"y={y:3d} {len(ws):2d}w: {' | '.join(toks)}")
