#!/usr/bin/env python3
"""v6 — structure-preserving chord realignment.

Keeps the existing content's lyrics, sections, //comments, {meta}, melisma `~`, verse
numbers, hyphens EXACTLY. Only re-anchors the [chord] tokens to the correct syllable using
the PDF text-layer (3-hop) ground truth.

Method per line:
1. Find the PDF aligned lyric row (word->chord anchors) that best matches this content line
   by normalized-word similarity.
2. Re-emit the line: walk its original words in order; for each content word, look up the
   chord anchored at the matching position in the PDF row and place [chord] before it.
3. If no PDF row is a good match, leave the line unchanged (safe).

It never inserts NEW chords beyond what the PDF anchors map onto existing words, and never
rewrites wording/structure/sections.
"""
import pdfplumber, re, sys, json, os, difflib, unicodedata

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)

def decode_chord(t):
    for a,b in [('“4','sus4'),('“','sus'),('‹','m'),('„Š7','maj7'),('„Š','maj'),('&','+'),('Œ',''),('„','')]:
        t=t.replace(a,b)
    return re.sub(r'[^\w/#+\(\)b]','',t)
def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))
def chord_center(w): return w['x0'] + (3.5+4.7*len(decode_chord(w['text'])))/2
def word_center(w): return w['x0'] + 4.7*len(w['text'])/2
def has_viet(t): return bool(VIET.search(t))
def clean(t): return re.sub(r'\s+',' ',re.sub(r'[™œÓ˙w‰j„ŠŒ%&]','',t)).strip()
def normword(s):
    s=unicodedata.normalize('NFC',s.lower())
    return re.sub(r'[^a-z0-9ăâđêôơư]','',s)

def page_rows(page):
    words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
    yg={}
    for w in words: yg.setdefault(round(w['top']),[]).append(w)
    return [sorted(yg[y],key=lambda w:w['x0']) for y in sorted(yg)]

def extract_pdf_rows(pdf_path):
    """Return flat list of aligned lyric rows: {'words':[(text,chord)], 'plain':[...]}."""
    rows=[]; st={'chords':[],'notes':[]}
    with pdfplumber.open(pdf_path) as p:
        for page in p.pages:
            for ws in page_rows(page):
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                if ch and not nt and not lyt and len(ch)>=2:
                    st={'chords':ch,'notes':[]}; continue
                if nt and not ch:
                    st['notes'].extend(nt); continue
                if lyt and has_viet(clean(lyt)) and not ch and not nt:
                    lower=[w['text'] for w in ly if re.search(r'[a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]',w['text'])]
                    if not lower: continue  # all-caps header
                    targets=[]
                    for w in ly:
                        if NOTE.match(w['text']) or re.match(r'^[\d\s\.]+$',w['text']): continue
                        targets.append({'text':w['text'],'center':word_center(w)})
                    placed={}
                    for c in sorted(st['chords'],key=lambda w:w['x0']):
                        cc=chord_center(c); ax=cc
                        if st['notes']:
                            n0=min(st['notes'],key=lambda n:abs(n['x0']-cc))
                            if abs(n0['x0']-cc)<=12: ax=n0['x0']
                        bi=None;bd=99
                        for i,t in enumerate(targets):
                            d=abs(t['center']-ax)
                            if d<bd: bd=d;bi=i
                        if bd<=28 and bi is not None and bi not in placed:
                            placed[bi]=decode_chord(c['text'])
                    words=[(targets[i]['text'],placed.get(i)) for i in range(len(targets))]
                    rows.append({'words':words,'plain':[t for t,_ in words]})
                    st={'chords':[],'notes':[]}
    return rows

def best_pdf_row(line_words_norm, pdf_rows):
    line=' '.join(line_words_norm)
    best=None; br=-1.0
    for r in pdf_rows:
        rn=' '.join(normword(x) for x in r['plain'])
        ratio=difflib.SequenceMatcher(None,line,rn).ratio()
        if ratio>br: br=ratio; best=r
    return best, br

def realign_line(content_line, pdf_row):
    """Re-emit content_line with [chord] before correct words, matching pdf_row anchors by
    word sequence. Preserves all non-chord text (punctuation, ~, hyphens, numbers, spaces)."""
    if '[' not in content_line: return content_line
    # strip existing chords to get bare text (keeps ~ , . - etc.)
    bare=re.sub(r'\[[^\]]*\]','',content_line)
    # words of bare text in order
    cwords=re.findall(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+', bare)
    cnorm=[normword(w) for w in cwords]
    pws=pdf_row['words']; pnorm=[normword(t) for t,_ in pws]
    # greedy alignment content->pdf
    idx=[]; pi=0
    for cn in cnorm:
        found=False
        for j in range(pi,len(pnorm)):
            if pnorm[j]==cn:
                idx.append(j); pi=j+1; found=True; break
        if not found: idx.append(None)
    # build output by scanning bare text, emitting chord before each matched word occurrence
    out=''; tok=0; i=0
    pat=r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+'
    def match(m):
        nonlocal tok
        pdi=idx[tok] if tok<len(idx) else None
        tok+=1
        ch=pws[pdi][1] if pdi is not None else None
        return f"[{ch}]{m.group(0)}" if ch else m.group(0)
    return re.sub(pat, match, bare)

def rebuild(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    if not pdf: return None,None
    pdf_rows=extract_pdf_rows(pdf)
    out=[]
    changed=False
    for line in s['content'].split('\n'):
        ls=line.strip()
        # only realign singable lines that contain [chord]
        if '[' in line and not (ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]):
            cwords=re.findall(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+', line)
            cnorm=[normword(w) for w in cwords]
            row,ratio=best_pdf_row(cnorm,pdf_rows)
            if row and ratio>0.6:
                new=realign_line(line,row)
                if new!=line: changed=True
                out.append(new)
            else:
                out.append(line)
        else:
            out.append(line)
    return '\n'.join(out), changed

if __name__=='__main__':
    for num in [int(x) for x in sys.argv[1:]]:
        new,ch=rebuild(num)
        print(f"===== DLC {num} (changed={ch}) =====")
        print(new)
