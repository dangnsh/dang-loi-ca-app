#!/usr/bin/env python3
"""v8 — per-section word-sequence chord re-anchor (structure-preserving).

The exact-word stream of each VERSE travels in the same left->right order in the PDF and in
the (already-correctly-structured) content — but PDF interleaves V1 and V2 rows on the same
staff, while content separates them into [Verse 1]/[Verse 2] blocks. So we align PER SECTION:

- [Verse 1]/odd-verse content words  <-> PDF's FIRST lyric-row words of each staff  (V1 stream)
- [Verse 2]/even-verse content words <-> PDF's SECOND lyric-row words               (V2 stream)
- [Chorus]/[Coda] content words       <-> PDF rows not consumed by any verse stream

For each matched content word we carry over the PDF's chord, then re-emit the line keeping
all its non-chord text (punctuation, numbers, hyphens, ~). Never touches sections/meta.
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

def staff_lyric_rows(pdf_path):
    """Return list of staffs; each staff = {'chords':[...],'notes':[...],'lyrics':[row,...]}
    where each row=(lywords, text). Keeps V1/V2 ordering as they appear (row[0]=V1,row[1]=V2)."""
    st={'chords':[],'notes':[],'lyrics':[]}; out=[]
    def flush():
        if st['lyrics'] and st['chords']: out.append(st)
        return {'chords':[],'notes':[],'lyrics':[]}
    with pdfplumber.open(pdf_path) as p:
        for page in p.pages:
            for ws in page_rows(page):
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                if ch and not nt and not lyt and len(ch)>=2:
                    st=flush(); st['chords']=ch
                elif nt and not ch:
                    st['notes'].extend(nt)
                elif lyt and has_viet(clean(lyt)) and not ch and not nt:
                    lower=[w['text'] for w in ly if re.search(r'[a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]',w['text'])]
                    if not lower: continue
                    st['lyrics'].append((ly,clean(lyt)))
    flush()
    return [s for s in out if s['lyrics'] and s['chords']]

def row_chords(st, row):
    """(text,chord) pairs for this row's lyric words using the staff's chords+notes."""
    lywords, lyt = row
    targets=[]
    for w in lywords:
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
    return [(t['text'], placed.get(i)) for i,t in enumerate(targets)]

def build_pdf_streams(pdf_path):
    """Return (v1_stream, v2_stream, extra_stream) each = [(word,chord)]. V1=first lyric row /
    staff, V2=second lyric row / staff; extras = chorus/coda/unpaired rows, in order."""
    staffs=staff_lyric_rows(pdf_path)
    v1=[];v2=[];extra=[]
    for st in staffs:
        rows=st['lyrics']
        for ri,row in enumerate(rows):
            pairs=row_chords(st,row)
            if len(rows)==1:
                extra.append(pairs)
            elif ri==0:
                v1.extend(pairs)
            else:
                v2.extend(pairs)
    return v1, v2, extra

def greedy_align(cnorm, pnorm, pseq):
    """Align content norm words to pdf norm words in order; return chord per content position."""
    res=[]; pi=0
    for cn in cnorm:
        found=None
        for j in range(pi,len(pnorm)):
            if pnorm[j]==cn:
                found=j; pi=j+1; break
        if found is not None:
            res.append(pseq[found][1])
        else:
            res.append(None)
    return res

def realign(pdf_path, content):
    v1,v2,extra=build_pdf_streams(pdf_path)
    v1n=[normword(w) for w,_ in v1]; v1seq=list(v1)
    v2n=[normword(w) for w,_ in v2]; v2seq=list(v2)
    exn=[normword(w) for w,_ in (x for lst in extra for x in lst)]; exseq=[x for lst in extra for x in lst]
    sections=[]  # list of (kind, [line_indexes])
    # parse content into sections
    out={}  # line_index -> new text
    cur_kind=None; cur_idx=[]; section_of_line={}
    lines=content.split('\n')
    for i,line in enumerate(lines):
        ls=line.strip()
        if ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]:
            cur_kind=ls[1:-1].lower()
            cur_idx=[]
        if '[' not in line: continue
        if ls.startswith('[') and ls.endswith(']') and '[' not in ls[1:-1]: continue
        # singable chord line belongs to current section
        section_of_line[i]=cur_kind
    # Gather per-kind lyric lines in order
    from collections import OrderedDict
    kind_lines=OrderedDict()
    for i in range(len(lines)):
        k=section_of_line.get(i)
        if k is None: continue
        kind_lines.setdefault(k,[]).append(i)
    # Determine which pdf stream each kind uses:
    #   kind contains '1' or 'câu 1' or is blank-first -> v1; '2' -> v2; chorus/coda -> extra
    flatpos=0
    # We'll assign chords per line globally but within each kind using the matching stream
    kind_used={}
    v1_used=v2_used=extra_used=False
    # map kinds to stream: verse1->v1, verse2->v2, chorus/coda/bridge->extra, else by parity
    mapped_kind={}
    for k in kind_lines:
        kl=k
        if 'chorus' in kl or 'điệp' in kl: mapped_kind[k]='extra'
        elif 'coda' in kl: mapped_kind[k]='extra'
        elif 'bridge' in kl: mapped_kind[k]='extra'
        elif 'verse 2' in kl or 'câu 2' in kl or '2' in kl: mapped_kind[k]='v2'
        else: mapped_kind[k]='v1'
    # Build stream selection: for all v1 kinds share the v1 stream, but each song usually 1 v1 block
    # We'll realign each kind independently against its stream's FULL word list (greedy from start).
    for k,idxs in kind_lines.items():
        stream = {'v1':(v1n,v1seq),'v2':(v2n,v2seq),'extra':(exn,exseq)}[mapped_kind[k]]
        sn, sseq = stream
        # collect this kind's lyric words in order (from the content lines)
        kind_cwords=[]  # (line_index, word_text)
        for i in idxs:
            bare=re.sub(r'\[[^\]]*\]','',lines[i])
            for w in re.findall(WORDRE,bare):
                kind_cwords.append((i,w))
        cnorm=[normword(w) for _,w in kind_cwords]
        chord_per_pos=greedy_align(cnorm, sn, sseq)
        # build per-line wanted chords
        line_wanted={}
        pos=0
        for i in idxs:
            bare=re.sub(r'\[[^\]]*\]','',lines[i])
            n=len(re.findall(WORDRE,bare))
            line_wanted[i]=chord_per_pos[pos:pos+n]
            pos+=n
        # re-emit each line
        for i in idxs:
            bare=re.sub(r'\[[^\]]*\]','',lines[i])
            it=iter(line_wanted[i])
            def repl(m):
                ch=next(it)
                return f"[{ch}]{m.group(0)}" if ch else m.group(0)
            out[i]=re.sub(WORDRE, repl, bare)
    result=[]
    for i,line in enumerate(lines):
        result.append(out.get(i,line))
    return '\n'.join(result)

if __name__=='__main__':
    num=int(sys.argv[1])
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    print(realign(pdf, s['content']))
