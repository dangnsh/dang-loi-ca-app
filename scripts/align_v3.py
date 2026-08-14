#!/usr/bin/env python3
"""Text-layer chord aligner v3 (3-hop). Validated to reproduce hand-curated DLC_001-005.

Staff model: CHORD row (top) -> NOTE rows (mid, possibly several y-lines) -> LYRIC row.
Groups rows by round(top) (tight, matches proven extract_v6). Drops top-of-page chord
overview rows (a chord row with no lyric attached, superseded by a nearer chord row).
"""
import pdfplumber, re, sys, json, unicodedata

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)
METRO = re.compile(r'^[b&jwJ‰œÓ˙™4\s]+$')  # time-sig / meter junk rows

def decode_chord(t):
    t=t.replace('“4','sus4').replace('“','sus').replace('‹','m').replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','')
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
    for y in sorted(yg):
        yield y, sorted(yg[y],key=lambda w:w['x0'])

def staffs(pdf_path):
    """Return staffs: {'chords':[w],'notes':[w],'lyrics':[(words,text)]}."""
    st=None; out=[]
    def emit():
        nonlocal st
        if st and st['lyrics'] and st['chords']: out.append(st)
        st={'chords':[],'notes':[],'lyrics':[]}
    with pdfplumber.open(pdf_path) as p:
        for page in p.pages:
            for y,ws in page_rows(page):
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                # skip meter/time rows
                if nt and not ch:
                    # note row (maybe mixed w/ meter junk); attach to current staff if any
                    # but if a lyric row came before it without a chord, this is its own metering
                    for w in ws:
                        if not NOTE.match(w['text']) and not METRO.match(w['text']) and not re.match(r'^[\d\.]+$',w['text']):
                            break
                    if st is None: st={'chords':[],'notes':[],'lyrics':[]}
                    st['notes'].extend(nt)
                    continue
                if ch and not nt:
                    # new staff; emit previous if it has lyric
                    emit()
                    st['chords']=ch
                    continue
                if lyt and has_viet(clean(lyt)) and not ch and not nt:
                    if st is None: st={'chords':[],'notes':[],'lyrics':[]}
                    st['lyrics'].append((ly,clean(lyt)))
                    continue
                # leftover rows: could be notes mixed with meter; ignore
    emit()
    return [s for s in out if s['lyrics'] and s['chords']]

def align_line(chords, notes, lyric):
    lywords, lyt = lyric
    targets=[]
    for w in lywords:
        if NOTE.match(w['text']): continue
        if re.match(r'^[\d\s\.]+$', w['text']): continue
        targets.append({'text':w['text'],'center':word_center(w)})
    placed=[]
    for c in sorted(chords,key=lambda w:w['x0']):
        cc=chord_center(c)
        if notes:
            nn=min(notes,key=lambda n:abs(n['x0']-cc))
            anchor_x= nn['x0'] if abs(nn['x0']-cc)<=12 else cc
        else:
            anchor_x=cc
        bi=None; bd=99
        for i,t in enumerate(targets):
            d=abs(t['center']-anchor_x)
            if d<bd: bd=d; bi=i
        # notehead-anchored nearest word; a chord over a REST anchors to the next word too,
        # so allow a generous band (resolves legacy PDF word-center offset).
        if bd<=28 and bi is not None:
            placed.append((bi, decode_chord(c['text'])))
    best={}
    for i,ch in sorted(placed,key=lambda p:p[0]):
        if i not in best: best[i]=ch
    return ' '.join(f"[{best[i]}]{t['text']}" if i in best else t['text'] for i,t in enumerate(targets))

if __name__=='__main__':
    pdf=sys.argv[1]
    for i,s in enumerate(staffs(pdf)):
        print(f"--- staff {i} chords={[decode_chord(c['text']) for c in s['chords']]} notes={len(s['notes'])}")
        for ly in s['lyrics']:
            print("  LYR:", align_line(s['chords'], s['notes'], ly))
