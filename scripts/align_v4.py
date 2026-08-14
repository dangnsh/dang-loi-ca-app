#!/usr/bin/env python3
"""v4 — regression-safe chord realignment.

Strategy:
1. Extract PDF lyric ROWS (with chord-anchored words from the 3-hop text-layer engine).
2. Flatten into a word->chord map carrying x-order so we can re-anchor.
3. Walk the EXISTING content line by line. For lyric lines:
     - strip [chord] tokens -> plain word list (keep punctuation)
     - find the best-matching PDF row (same lyrics) and its chord anchors
     - re-emit the line placing [chord] before the correct word.
4. Preserve sections, //meta, {title}, melisma ~[...] handling minimal: keep any chord that
   the current line already has if no better anchor found.
"""
import pdfplumber, re, sys, json, os, unicodedata, difflib

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)

def decode_chord(t):
    for a,b in [('“4','sus4'),('“','sus'),('‹','m'),('„Š7','maj7'),('„Š','maj'),('&','+'),('Œ',''),('„','')]:
        t=t.replace(a,b)
    return re.sub(r'[^\w/#+\(\)b]','',t)
def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))
def chord_center(w): return w['x0'] + (3.5+4.7*len(w['text']))/2
def word_center(w): return w['x0'] + 4.7*len(w['text'])/2
def has_viet(t): return bool(VIET.search(t))
def clean(t): return re.sub(r'\s+',' ',re.sub(r'[™œÓ˙w‰j„ŠŒ%&]','',t)).strip()

def page_rows(page):
    words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
    yg={}
    for w in words: yg.setdefault(round(w['top']),[]).append(w)
    return [sorted(yg[y],key=lambda w:w['x0']) for y in sorted(yg)]

def extract_aligned_rows(pdf_path):
    """Return list of dict-aligned lyric rows: {words:[(text,chord)], plain:[str]} in page order."""
    rows=[]
    with pdfplumber.open(pdf_path) as p:
        for page in p.pages:
            st={'chords':[],'notes':[]}
            for ws in page_rows(page):
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                if ch and not nt and not lyt and len(ch)>=2:
                    st={'chords':ch,'notes':[]}; continue
                if nt and not ch:
                    # only real note glyphs
                    st['notes'].extend(nt); continue
                if lyt and has_viet(clean(lyt)) and not ch and not nt:
                    # build anchored words
                    targets=[]
                    for w in ly:
                        if NOTE.match(w['text']) or re.match(r'^[\d\s\.]+$',w['text']): continue
                        targets.append({'text':w['text'],'center':word_center(w)})
                    placed={}
                    for c in sorted(st['chords'],key=lambda w:w['x0']):
                        cc=chord_center(c)
                        ax= cc
                        if st['notes']:
                            nn=min(st['notes'],key=lambda n:abs(n['x0']-cc))
                            if abs(nn['x0']-cc)<=12: ax=nn['x0']
                        bi=None;bd=99
                        for i,t in enumerate(targets):
                            d=abs(t['center']-ax)
                            if d<bd: bd=d;bi=i
                        if bd<=28 and bi is not None and bi not in placed:
                            placed[bi]=decode_chord(c['text'])
                    words=[(targets[i]['text'], placed.get(i)) for i in range(len(targets))]
                    rows.append({'words':words,'plain':[t for t,_ in words]})
                    st={'chords':[],'notes':[]}
    return rows

def norm(s):
    s=unicodedata.normalize('NFC',s.lower())
    return re.sub(r'[^a-z0-9ăâđêôơư]','',s)

def content_plain_words(text):
    return re.findall(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+', text)

def best_row(plain_words):
    """Find PDF aligned row whose plain text best matches this line's words."""
    line_norm=' '.join(norm(x) for x in plain_words)
    best=None;br=-1.0
    for r in rows_global:
        rnorm=' '.join(norm(x) for x in r['plain'])
        ratio=difflib.SequenceMatcher(None,line_norm,rnorm).ratio()
        if ratio>br: br=ratio;best=r
    return best,br

def realign_line(line, pdf_row):
    """Emit line with [chord] before correct words, matching to pdf_row's anchors by sequence."""
    # tokenize the content line into (word_or_text_chunk)
    # We rebuild: split line into words keeping punctuation and existing [chords].
    # Simpler: find words in order; pdf_row.words gives (text,chord) in order.
    # Walk content words; for each, if it matches the next pdf word, take its chord.
    ch=True if '[' in line else False
    if not ch: return line
    # extract content words in order
    cwords = re.findall(r'([A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+)', line)
    # pdf words
    pws=pdf_row['words']
    pnorm=[norm(t) for t,_ in pws]
    cnorm=[norm(w) for w in cwords]
    # greedy align
    pi=0; used=set()
    for i,cn in enumerate(cnorm):
        for j in range(pi,len(pnorm)):
            if pnorm[j]==cn:
                used.add(j); pi=j+1; break
    # map content word i -> pdf index
    idx=[]
    pi=0
    for i,cn in enumerate(cnorm):
        found=False
        for j in range(pi,len(pnorm)):
            if pnorm[j]==cn and j in used:
                idx.append(j); pi=j+1; found=True; break
        if not found:
            idx.append(None); 
    # rebuild by scanning original line char by char, emitting [chord] before word boundaries
    out=''
    tok=i=0
    # We'll reconstruct: for each content word occurrence in original text, place chord.
    # Use regex to split original into (prefix text) + (word) and attach chord before matched word.
    def repl(m):
        nonlocal tok
        pdi=idx[tok] if tok < len(idx) else None
        tok+=1
        chrd = pws[pdi][1] if pdi is not None else None
        return f"[{chrd}]{m.group(0)}" if chrd else m.group(0)
    # match words in order
    pat=re.compile(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+')
    # remove existing chords from the line first, tracking nothing else
    bare=re.sub(r'\[[^\]]*\]','',line)
    out=pat.sub(repl,bare)
    return out

rows_global=[]
def set_rows(r): 
    global rows_global; rows_global=r

def rebuild(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    if not pdf: return None
    global rows_global
    rows_global=extract_aligned_rows(pdf)
    out=[]
    for line in s['content'].split('\n'):
        ls=line.strip()
        if '[' in line and not (ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]):
            words=content_plain_words(line)
            row,ratio=best_row(words)
            if row and ratio>0.7:
                out.append(realign_line(line, row))
            else:
                out.append(line)  # no good match, keep original (safe)
        else:
            out.append(line)
    return '\n'.join(out), s['title']

if __name__=='__main__':
    for num in [int(x) for x in sys.argv[1:]]:
        new,title=rebuild(num)
        print(f"===== DLC {num} {title} =====")
        print(new)
