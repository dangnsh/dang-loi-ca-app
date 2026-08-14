#!/usr/bin/env python3
"""Text-layer chord aligner v2 (3-hop). Rebuilds each lyric LINE by anchoring chords to
syllables via: chord.center -> nearest notehead(<=12px) -> nearest lyric word center(<=13px).

Staff model per stave:
  CHORD row  (one row, chords at x)
  NOTE rows  (noteheads at x, may span several y-lines)
  LYRIC row  (the sung words, at x)

Output: same lyric words + sections, but with [chord] inserted before the anchored word.
"""
import pdfplumber, re, sys, json, unicodedata

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)

def decode_chord(t):
    t=t.replace('“4','sus4').replace('“','sus').replace('‹','m').replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','')
    return re.sub(r'[^\w/#+\(\)b]','',t)
def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))
def chord_center(w): return w['x0'] + (3.5+4.7*len(w['text']))/2
def word_center(w): return w['x0'] + 4.7*len(w['text'])/2
def has_viet(t): return bool(VIET.search(t))
def clean(t): return re.sub(r'\s+',' ',re.sub(r'[™œÓ˙w‰j„ŠŒ%&]','',t)).strip()

def load_rows(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
            bands=[]
            for w in sorted(words,key=lambda w:w['top']):
                placed=False
                for b in bands:
                    if abs(b['y']-w['top'])<=3: b['words'].append(w); placed=True; break
                if not placed: bands.append({'y':w['top'],'words':[w]})
            bands.sort(key=lambda b:b['y'])
            for b in bands:
                ws=sorted(b['words'],key=lambda w:w['x0'])
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                if ch and not lyt and not nt and len(ch)>=2:
                    yield ('CHORD', ch)
                elif nt and not lyt and not ch:
                    yield ('NOTE', nt)
                elif lyt and has_viet(clean(lyt)) and not ch and not nt:
                    yield ('LYRIC', (ly, clean(lyt)))

def staffs(pdf_path):
    """Group rows into staffs. Each staff: chords list, notes list, lyrics list."""
    st=None; out=[]
    def emit():
        nonlocal st
        if st and st['lyrics']:
            out.append(st)
        st=None
    for typ, pl in load_rows(pdf_path):
        if typ=='CHORD':
            # new staff starts; if previous staff had chords but no lyric yet, it was an
            # overview -- drop. Otherwise close.
            emit()
            st={'chords':list(pl),'notes':[],'lyrics':[]}
        elif typ=='NOTE':
            if st is None: st={'chords':[],'notes':[],'lyrics':[]}
            st['notes'].extend(pl)
        elif typ=='LYRIC':
            if st is None: st={'chords':[],'notes':[],'lyrics':[]}
            st['lyrics'].append(pl)
    emit()
    return [s for s in out if s['lyrics'] and s['chords']]

def align_line(chords, notes, lyric):
    """Return the lyric row with [chord] inline before anchored words."""
    lywords, lyt = lyric
    targets=[]
    for w in lywords:
        if NOTE.match(w['text']): continue
        if re.match(r'^[\d\s\.]+$', w['text']): continue
        targets.append({'text':w['text'],'center':word_center(w),'idx':None})
    # map chords
    placed=[]
    for c in sorted(chords,key=lambda w:w['x0']):
        cc=chord_center(c)
        # nearest notehead
        if notes:
            nn=min(notes,key=lambda n:abs(n['x0']-cc))
            anchor_x= nn['x0'] if abs(nn['x0']-cc)<=12 else None
        else:
            anchor_x=cc
        if anchor_x is None: 
            # chord with no nearby note -> anchor to nearest word by chord center
            anchor_x=cc
        bi=None; bd=99
        for i,t in enumerate(targets):
            d=abs(t['center']-anchor_x)
            if d<bd: bd=d; bi=i
        if bd<=13 and bi is not None:
            placed.append((bi, decode_chord(c['text'])))
    # dedupe per word; keep first (override existing greedily by earliest x)
    best={}
    for i,ch in sorted(placed,key=lambda p:p[0]):
        if i not in best: best[i]=ch
    out=[]
    for i,t in enumerate(targets):
        out.append(f"[{best[i]}]{t['text']}" if i in best else t['text'])
    return ' '.join(out)

if __name__=='__main__':
    pdf=sys.argv[1]
    for i,s in enumerate(staffs(pdf)):
        print(f"--- staff {i} chords={[decode_chord(c['text']) for c in s['chords']]} — notes={len(s['notes'])}")
        for ly in s['lyrics']:
            print("  LYR:", align_line(s['chords'], s['notes'], ly))
