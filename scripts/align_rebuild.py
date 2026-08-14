#!/usr/bin/env python3
"""Text-layer chord alignment (3-hop: chord.center -> nearest notehead -> nearest syllable).
Rebuilds ChordPro content from the PDF text layer with exact syllable anchoring.

Strategy per page: bottom-up. Lyric (Vietnamese) rows are staff terminators. For each lyric
row, the nearest chord row above it (and above the previous lyric) is that staff's chord row;
noteheads between the chord row and the lyric row belong to the staff. Chords map
chord.center -> nearest notehead (<=12px) -> nearest lyric word center (<=13px).

Top-of-page chord overview rows (many chords, no attached lyric) are dropped.
"""
import pdfplumber, re, sys, os, json, unicodedata

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)

def decode_chord(t):
    t=t.replace('“4','sus4').replace('“','sus').replace('‹','m').replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','').replace('(b5)','(b5)')
    return re.sub(r'[^\w/#+\(\)b]','',t)

def is_chord(w):
    d=decode_chord(w); return bool(d) and bool(CH.match(d))

def chord_center(w):
    # replicate reference: x0 + (3.5 + 4.7*len)/2
    return w['x0'] + (3.5 + 4.7*len(w['text']))/2

def word_center(w):
    return w['x0'] + 4.7*len(w['text'])/2

def has_viet(t): return bool(VIET.search(t))

def clean_lyric(t):
    t = re.sub(r'[™œÓ˙w‰j„ŠŒ%&]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def extract_rows(page):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.0)
    # cluster by y with tolerance ~3px
    bands = []
    for w in sorted(words, key=lambda w:w['top']):
        placed = False
        for b in bands:
            if abs(b['y'] - w['top']) <= 3:
                b['words'].append(w); placed=True; break
        if not placed:
            bands.append({'y': w['top'], 'words': [w]})
    bands.sort(key=lambda b:b['y'])
    return bands

def classify_row(words):
    ch=[w for w in words if is_chord(w['text'])]
    nt=[w for w in words if NOTE.match(w['text'])]
    ly=[w for w in words if not is_chord(w['text']) and not NOTE.match(w['text'])]
    lyt=' '.join(w['text'] for w in ly)
    return ch, nt, ly, lyt

def parse_pdf(pdf_path):
    staves=[]  # list of {'chords':[w], 'noteheads':[w], 'lyrics':[list of (words,text)] }
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            rows = extract_rows(page)
            # collect lyric rows (staff terminators) and notehead rows in order
            items=[]  # (y, type, payload)
            for b in rows:
                ch,nt,ly,lyt = classify_row(b['words'])
                if ch and not lyt and not nt and len(ch)>=2:
                    items.append((b['y'],'CHORD',ch))
                elif nt and not lyt and not ch:
                    items.append((b['y'],'NOTE',nt))
                elif lyt and has_viet(clean_lyric(lyt)) and not ch and not nt:
                    items.append((b['y'],'LYRIC',ly))
    # NOTE: simplified — real impl below reuses band log
    return staves

# -------- main: rebuild content for one song ----------
def rebuild(pdf_path, title):
    with pdfplumber.open(pdf_path) as pdf:
        all_pages=[]
        for page in pdf.pages:
            bands = extract_rows(page)
            seq=[]
            for b in bands:
                ch,nt,ly,lyt = classify_row(b['words'])
                typ=None; payload=None
                if ch and not lyt and not nt and len(ch)>=2:
                    typ='CHORD'; payload=ch
                elif nt and not lyt and not ch:
                    typ='NOTE'; payload=nt
                elif lyt and has_viet(clean_lyric(lyt)) and not ch and not nt:
                    typ='LYRIC'; payload=ly
                # skip header rows (no viet, no chords, notes-only garbage)
                if typ: seq.append((b['y'],typ,payload))
            all_pages.append(seq)
    # now chunk seq into staffs: a staff = from after previous LYRIC (or start) up to and incl a LYRIC
    staffs=[]
    cur={'chords':[], 'notes':[], 'lyrics':[]}
    for y,typ,payload in [it for pg in all_pages for it in pg]:
        if typ=='LYRIC':
            lyt=' '.join(w['text'] for w in payload)
            cur['lyrics'].append((payload, clean_lyric(lyt), y))
            staffs.append(cur); cur={'chords':[], 'notes':[], 'lyrics':[]}
        elif typ=='CHORD':
            cur['chords']=payload
        elif typ=='NOTE':
            cur['notes'].extend(payload)
    if cur['lyrics']: staffs.append(cur)
    # chords w/o any lyric (page summary) -> drop
    staffs=[s for s in staffs if s['lyrics']]
    # build section blocks
    v1,v2,chorus=[],[],[]
    v1c=v2c=0
    for s in staffs:
        chwords = sorted(s['chords'], key=lambda w:w['x0'])
        notes = s['notes']
        for lywords, lyt, y in s['lyrics']:
            # realign words to exact text (lyt may have cleaned chars, use words with centers)
            merged = merge_staff(chwords, notes, lywords, lyt)
            # section assignment
            l2 = lyt.strip()
            if re.match(r'^1[\.\s]', l2):
                v1.append(re.sub(r'^1[\.\s]+\s*','',merged)); v1c+=1
            elif re.match(r'^2[\.\s]', l2):
                v2.append(re.sub(r'^2[\.\s]+\s*','',merged)); v2c+=1
            elif re.match(r'(?i)^(đk|chorus|điệp)[\.\s:]', l2):
                chorus.append(merged)
            else:
                if len(s['lyrics'])>1 and s['lyrics'].index((lywords,lyt,y))==0:
                    v1.append(merged); v1c+=1
                elif len(s['lyrics'])>1:
                    v2.append(merged); v2c+=1
                else:
                    v1.append(merged); v1c+=1
    blocks=[]
    if v1: blocks.append("[Verse 1]\n"+"\n".join(v1))
    if v2: blocks.append("[Verse 2]\n"+"\n".join(v2))
    if chorus: blocks.append("[Chorus]\n"+"\n".join(chorus))
    return "\n\n".join(blocks)

def merge_staff(chwords, notes, lywords, lyt):
    """Place [Chord] tokens before lyrics using chord.center->notehead->word mapping and
    the count of chords present in the staff. Returned as ChordPro inline string (word level)."""
    # Build list of tokens (text, x0, center) for lyrics — target words
    targets=[]
    for w in lywords:
        t=w['text']
        if NOTE.match(t): continue
        if re.match(r'^[\d\s\.]+$', t): continue
        targets.append({'text':t,'x0':w['x0'],'center':word_center(w)})
    # Map each chord to nearest notehead then to nearest target
    placed=[]  # (target_index, chordname)
    for c in sorted(chwords, key=lambda w:w['x0']):
        cc=chord_center(c)
        # nearest notehead
        best_n=None; best_d=99
        for n in notes:
            d=abs(n['x0']-cc)
            if d<best_d: best_d=d; best_n=n
        note_x = best_n['x0'] if best_n else None
        # nearest target
        anchor=None; bd=99
        for ti,t in enumerate(targets):
            d=abs(t['center']- (note_x if note_x is not None else cc))
            if d<bd: bd=d; anchor=ti
        if bd<=13 and anchor is not None:
            placed.append((anchor, decode_chord(c['text'])))
    # dedupe same target (only first chord per word); sort by target index
    seen=set(); final=[]
    for ti,ch in sorted(placed, key=lambda p:p[0]):
        if ti in seen: continue
        seen.add(ti); final.append((ti,ch))
    # build output string word by word
    out_parts=[]; insert={ti:ch for ti,ch in final}
    for ti,t in enumerate(targets):
        if ti in insert:
            out_parts.append(f"[{insert[ti]}]{t['text']}")
        else:
            out_parts.append(t['text'])
    return ' '.join(out_parts)

if __name__=='__main__':
    pdf=sys.argv[1]; title=sys.argv[2] if len(sys.argv)>2 else ''
    print(rebuild(pdf,title))
