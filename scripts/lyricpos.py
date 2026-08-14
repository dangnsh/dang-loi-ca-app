import pdfplumber, re, sys
NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
def decode_chord(t):
    t=t.replace('“4','sus4').replace('“','sus').replace('‹','m').replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','')
    return re.sub(r'[^\w/#+\(\)b]','',t)
def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))
pdf=sys.argv[1]; targets=sys.argv[2:]
with pdfplumber.open(pdf) as p:
    for page in p.pages:
        words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
        lines={}
        for w in words: lines.setdefault(round(w['top']),[]).append(w)
        for y in sorted(lines):
            ws=sorted(lines[y],key=lambda w:w['x0'])
            ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
            lyt=' '.join(w['text'] for w in ly)
            if lyt and re.search(r'[ăâđêôơưáàảãạ]', lyt, re.I):
                words_pos=[(w['text'], round(w['x0']), round(w['x0']+2.1*len(w['text']))) for w in ly]
                print(f" y{y:>3} LYR: {lyt!r}")
                print("      "+" | ".join(f"{t}@{x0}-{x1}" for t,x0,x1 in words_pos))
