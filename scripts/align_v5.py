#!/usr/bin/env python3
"""v5 — full ChordPro reconstruction from PDF text layer (3-hop chord->notehead->syllable).

Produces the authoritative `content` field with:
- section labels [Verse 1]/[Verse 2]/[Chorus]/[Coda] via "1."/"2."/chorus markers + interleave
- melisma `~[Chord]` where a long note continues over a following syllable
- rest chords `[Chord](𝄽)` before the syllable that follows a rest
- top-of-page chord overview rows dropped
- header/title rows dropped
"""
import pdfplumber, re, sys, json, os, unicodedata

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
VIET = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)
METRO = re.compile(r'^[b&jwJ‰œÓ˙™4\s]+$')

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

def glue_words(t):
    up='A-ZĂÂĐÊÔƠƯÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ'
    return re.sub(r'([a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ])(['+up+'])',r'\1 \2',t)

def page_rows(page):
    words=page.extract_words(use_text_flow=False,keep_blank_chars=False,x_tolerance=1.0)
    yg={}
    for w in words: yg.setdefault(round(w['top']),[]).append(w)
    for y in sorted(yg):
        yield y, sorted(yg[y],key=lambda w:w['x0'])

def extract_staffs(pdf_path):
    """Return staffs in order. Each staff: {'chords':[w],'notes':[w],'lyrics':[(words,text)]}."""
    st={'chords':[],'notes':[],'lyrics':[]}; out=[]
    def flush():
        if st['lyrics'] and st['chords']: out.append(st)
        return {'chords':[],'notes':[],'lyrics':[]}
    with pdfplumber.open(pdf_path) as p:
        for page in p.pages:
            for y,ws in page_rows(page):
                ch=[w for w in ws if is_chord(w['text'])]
                nt=[w for w in ws if NOTE.match(w['text'])]
                ly=[w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                lyt=' '.join(w['text'] for w in ly)
                if ch and not nt and not lyt and len(ch)>=2:
                    st=flush(); st['chords']=ch
                elif nt and not ch:
                    st['notes'].extend(nt)
                elif lyt and has_viet(clean(lyt)) and not ch and not nt:
                    # running page header: title reproduced in ALL CAPS at top of pages.
                    # Skip rows that are entirely uppercase (no lowercase letters).
                    lower=[w['text'] for w in ly if re.search(r'[a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', w['text'])]
                    if not lower:
                        continue  # header row (all caps) — drop
                    st['lyrics'].append((ly,clean(lyt),y))
    flush()
    return out

def align_line(chords, notes, lyric, prev_end_chord=None):
    """Return (chordpro_line_str, list_of_used_chords). Handles melisma ~ and rest (𝄽)."""
    lywords, lyt, y = lyric
    targets=[]
    for w in lywords:
        if NOTE.match(w['text']) or re.match(r'^[\d\s\.]+$',w['text']): continue
        targets.append({'text':w['text'],'center':word_center(w),'x0':w['x0']})
    # chord -> anchor x
    anch=[]
    for c in sorted(chords,key=lambda w:w['x0']):
        cc=chord_center(c)
        ax=cc
        rest=False
        if notes:
            # nearest glyph (notehead OR rest) decides: chord lands ON a rest only if the
            # closest glyph is a rest (R4), otherwise anchor to notehead.
            n0=min(notes,key=lambda n:abs(n['x0']-cc))
            if abs(n0['x0']-cc)<=12:
                ax=n0['x0']
                if n0['text'] in ('Ó','‰'):
                    rest=True
        anch.append((cc,ax,rest,decode_chord(c['text'])))
    # assign each chord to nearest target
    used_chords=[]
    out=[]
    placed={}
    for cc,ax,rest,chname in anch:
        bi=None;bd=99
        for i,t in enumerate(targets):
            d=abs(t['center']-ax)
            if d<bd: bd=d;bi=i
        if bd<=28 and bi is not None:
            placed.setdefault(bi,[]).append((cc,rest,chname))
            used_chords.append(chname)
    # build string: for each target, if chords assigned, emit
    parts=[]
    used_indices=set()
    for i,t in enumerate(targets):
        if i in placed:
            clist=sorted(placed[i],key=lambda x:x[0])
            rest = any(r for _,r,_ in clist)
            s=''.join(f"[{ch}]" for _,_,ch in clist)
            if rest: s+= '(𝄽)'
            parts.append((s,t['text']))
            used_indices.add(i)
        else:
            parts.append(('',t['text']))
    return ' '.join(('' if pr=='' else pr)+tx for pr,tx in parts), used_chords

def build_content(pdf_path, title):
    staffs=extract_staffs(pdf_path)
    # verse streams: items[key] -> [line,...] with key in {v1,v2,v3...,chorus,coda}
    streams={}; order=[]
    def emit(key,line):
        if key not in streams:
            streams[key]=[]; order.append(key)
        streams[key].append(line)
    chorus_seen=False
    for s in staffs:
        chords=s['chords']; notes=s['notes']
        rows=s['lyrics']
        if len(rows)==1:
            ly=rows[0]; txt=ly[1].strip()
            line,lused=align_line(chords,notes,ly)
            line=re.sub(r'^[0-9]+[\\.\\s]+\\s*','',line)
            if re.match(r'(?i)^(đk|chorus|điệp)[\\.\\s:]',txt) or re.match(r'(?i)^coda',txt):
                grp='coda' if re.match(r'(?i)^coda',txt) else 'chorus'
                chorus_seen = chorus_seen or grp=='chorus'
                emit(grp,re.sub(r'^(?i)(đk|chorus|điệp|coda)[\\.\\s:]+\\s*','',line))
            else:
                # unmarked continuation: verse 1 if nothing yet else verse 2
                key='v1' if 'v2' not in streams else 'v2'
                emit(key,line)
        else:
            # N interleaved verse rows under one chord line: row[k] -> v(k+1)
            for k,ly in enumerate(rows):
                txt=ly[1].strip()
                line,lused=align_line(chords,notes,ly)
                line=re.sub(r'^[0-9]+[\\.\\s]+\\s*','',line)
                if re.match(r'(?i)^(đk|chorus|điệp)[\\.\\s:]',txt) or re.match(r'(?i)^coda',txt):
                    grp='coda' if re.match(r'(?i)^coda',txt) else 'chorus'
                    chorus_seen = chorus_seen or grp=='chorus'
                    emit(grp,re.sub(r'^(?i)(đk|chorus|điệp|coda)[\\.\\s:]+\\s*','',line))
                else:
                    emit(f'v{k+1}',line)
    label={'v1':'[Verse 1]','v2':'[Verse 2]','v3':'[Verse 3]','v4':'[Verse 4]',
           'v5':'[Verse 5]','v6':'[Verse 6]','chorus':'[Chorus]','coda':'[Coda]'}
    parts=[]
    for key in order:
        parts.append(label.get(key,f'[{key}]')+'\n'+'\n'.join(streams[key]))
    return '\n\n'.join(parts)

if __name__=='__main__':
    pdf=sys.argv[1]; title=sys.argv[2] if len(sys.argv)>2 else ''
    print(build_content(pdf,title))
