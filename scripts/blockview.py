import pdfplumber, re, sys
NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
def decode_chord(t):
    t=t.replace('“4','sus4').replace('“','sus').replace('‹','m').replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','')
    return re.sub(r'[^\w/#+\(\)b]','',t)
def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))
pdf=sys.argv[1]
with pdfplumber.open(pdf) as p:
    for pi,page in enumerate(p.pages,1):
        words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
        lines={}
        for w in words:
            lines.setdefault(round(w['top']),[]).append(w)
        print(f"===== PAGE {pi} =====")
        for y in sorted(lines):
            ws=sorted(lines[y],key=lambda w:w['x0'])
            ch=[w for w in ws if is_chord(w['text'])]
            nt=[w for w in ws if NOTE.match(w['text'])]
            ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
            lyt=' '.join(w['text'] for w in ly)
            if not ch and not nt and not lyt: continue
            if ch:
                print(f" y{y:>3} CH : "+" | ".join(f"{w['text']}@{w['x0']:.0f}" for w in ch))
            elif nt:
                print(f" y{y:>3} NOTE: "+" | ".join(f"{w['text']}@{w['x0']:.0f}" for w in nt))
            else:
                print(f" y{y:>3} LYR: {lyt!r}")
