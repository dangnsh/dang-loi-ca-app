import pdfplumber, re
NOTE = re.compile(r'^[œ˙™Ó‰]+$')
pdf='/tmp/dlc/public/sheets/DLC_002_Bai_ca_dang_Chua.pdf'
with pdfplumber.open(pdf) as p:
    for pi,page in enumerate(p.pages,1):
        if pi>1: break
        words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
        nn=[w for w in words if NOTE.match(w['text'])]
        print(f"page {pi}: total words={len(words)} note glyphs={len(nn)}")
        # show every word y 145-165 with its x
        for w in sorted([w for w in words if 140<=w['top']<=170], key=lambda w:(w['top'],w['x0'])):
            print(f"  y={w['top']:.0f} x={w['x0']:.0f} {w['text']!r}")
