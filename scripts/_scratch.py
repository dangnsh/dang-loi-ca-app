#!/usr/bin/env python3
"""Align chords to syllables in EXISTING lyric lines using PDF text-layer coordinates.

Strategy (regression-safe):
- Keep the current content's lyric text and [Verse]/[Chorus] section structure AS-IS.
- For each lyric line, strip its [chord] tokens -> plain lyric string.
- In the PDF page rows, find the lyric row whose text best matches this line (fuzzy, after
  normalization: spaces, punctuation, lowercase).
- From that staff's chord row + notehead rows, compute the 3-hop mapping and rebuild the line
  with [chord] inline before the correct word.
- If no good staff match, keep the original line untouched.

This only ever MOVES chords (or drops ones with no anchor); it never rewrites lyrics or
sections, so it cannot regress the already-good benchmark songs or break section badges.
"""
import pdfplumber, re, sys, json, unicodedata, difflib

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
def clean_lyric(t):
    return re.sub(r'\s+',' ',re.sub(r'[™œÓ˙w‰j„ŠŒ%&ﬂfi]','',t)).strip()

def norm(s):
    s=unicodedata.normalize('NFC',s.lower())
    s=re.sub(r'[^a-z0-9ăâđêôơư]','',s)
    return s

def extract_staffs(pdf_path):
    """Return list of staffs: {'chords':[w], 'notes':[w], 'lyrics':[(lywords,text)]} preserving order."""
    with pdfplumber.open(pdf_path) as pdf:
        seq=[]
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
                typ=None; pl=None
                if ch and not lyt and not nt and len(ch)>=2: typ,pl='CHORD',ch
                elif nt and not lyt and not ch: typ,pl='NOTE',nt
                elif lyt and has_viet(clean_lyric(lyt)) and not ch and not nt: typ,pl='LYRIC',ly
                if typ: seq.append(pl if typ=='CHORD' else nt if typ=='NOTE' else ly)
    staffs=[]; cur={'chords':[],'notes':[],'lyrics':[]}
    for pl in seq:
        if isinstance(pl[0],dict) and NOTE.match(pl[0]['text']) and len(pl)==1 and 'x0' in pl[0]:
            # note row
            cur['notes'].extend(pl)
        elif pl and 'y' not in str(pl[0]) and pl[0].get('text','').isalpha() or (pl and isinstance(pl[0],dict) and NOTE.match(pl[0]['text'])):
            # ambiguous — notes
            if pl and isinstance(pl[0],dict) and (NOTE.match(pl[0]['text']) or (not any(is_chord(w) for w in pl) and has_viet(' '.join(w['text'] for w in pl)))):
                pass
    return staffs
