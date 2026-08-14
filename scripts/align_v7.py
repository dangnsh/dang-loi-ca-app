#!/usr/bin/env python3
"""v7 — global word-sequence chord re-anchor (structure-preserving).

1. Build the authoritative word->chord map in strict PDF reading order (left->right across
   all staff/lyric rows). This is the ground truth of WHERE each chord belongs.
2. Flatten the CURRENT content's lyric words (strip chords) in order — the lyrics are
   already correct, only the chord POSITION is wrong.
3. Greedily sequence-align content words to pdf words (same song, same word stream), then
   re-insert [chord] before the correct content word.
4. Rebuild content line by line, preserving ALL non-chord text (sections, //meta, verse
   numbers, melisma ~, hyphens, punctuation).

Safe: it can only MOVE/REMOVE chord tokens relative to the current content; it never adds
new words, never rewrites sections or metadata, and never inserts chords on words the PDF
does not chord.
"""
import pdfplumber, re, sys, json, os, unicodedata

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

WORDRE=r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+'

def page_rows(page):
    words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
    yg={}
    for w in words: yg.setdefault(round(w['top']),[]).append(w)
    return [sorted(yg[y],key=lambda w:w['x0']) for y in sorted(yg)]

def pdf_chord_sequence(pdf_path):
    """Return ordered list of (word_text, chord_or_None) reflecting where PDF chords land.
    Preserves left->right order across all lyric rows (the song's musical word stream)."""
    seq=[]; st={'chords':[],'notes':[]}
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
                    if not lower: continue
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
                        if bd<=30 and bi is not None and bi not in placed:
                            placed[bi]=decode_chord(c['text'])
                    for i,t in enumerate(targets):
                        seq.append((t['text'], placed.get(i)))
                    st={'chords':[],'notes':[]}
    return seq

def realign(pdf_path, content):
    pdf_seq=pdf_chord_sequence(pdf_path)
    pnorm=[normword(w) for w,_ in pdf_seq]
    # gather content lyric lines (with chord) in order
    out=[]
    # We need to walk content words globally, assigning chord by matching to pdf_seq.
    # First collect all content lyric words in order across singable lines.
    content_lines=content.split('\n')
    lyric_groups=[]  # (index_in_content_lines, cwords_norm, cwords)
    for i,line in enumerate(content_lines):
        ls=line.strip()
        if '[' in line and not (ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]):
            bare=re.sub(r'\[[^\]]*\]','',line)
            cwords=re.findall(WORDRE,bare)
            lyric_groups.append((i,cwords))
        else:
            lyric_groups.append((i,None))
    # global greedy alignment of all content words to pdf words
    # build flat content word list
    flat=[]
    for i,cw in lyric_groups:
        if cw is not None:
            flat.extend((i,c) for c in cw)
    flatnorm=[normword(c) for _,c in flat]
    # align
    pdf_idx_for_content=[]  # aligns flat -> pdf index
    pi=0
    used_pdf=set()
    for fn in flatnorm:
        found=None
        for j in range(pi,len(pnorm)):
            if pnorm[j]==fn:
                found=j; pi=j+1; used_pdf.add(j); break
        pdf_idx_for_content.append(found)
    # Build per-line chord map: for each content word position, wanted chord
    # chord_for_flat[i] = chord
    chord_for_flat={}
    for k,(i,c) in enumerate(flat):
        p=pdf_idx_for_content[k]
        if p is not None:
            pch=pdf_seq[p][1]
            if pch: chord_for_flat[k]=pch
    # Now reconstruct each line: walk its words, count global position, emit chords.
    out_lines=[]
    flatpos=0
    for i,line in enumerate(content_lines):
        ls=line.strip()
        if '[' in line and not (ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]):
            bare=re.sub(r'\[[^\]]*\]','',line)
            cwords=re.findall(WORDRE,bare)
            start=flatpos; flatpos+=len(cwords)
            # build: for each word occurrence place chord
            wanted=[]
            for k in range(start,start+len(cwords)):
                wanted.append(chord_for_flat.get(k))
            # re-emit line
            it=iter(wanted)
            def repl(m):
                ch=next(it)
                return f"[{ch}]{m.group(0)}" if ch else m.group(0)
            out_lines.append(re.sub(WORDRE, repl, bare))
        else:
            out_lines.append(line)
    return '\n'.join(out_lines)

if __name__=='__main__':
    num=int(sys.argv[1])
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    print(realign(pdf, s['content']))
