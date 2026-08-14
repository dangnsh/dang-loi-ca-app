#!/usr/bin/env python3
"""For each song, compare existing content chord placement vs text-layer reconstruction.
Produces a per-song diff summary: how many chords moved/added/removed.

The correct final artifact should PRESERVE existing lyrics+sections and only realign chords.
Here we compute a proxy: for each content LINE, strip chords -> plain words. Then we find the
matching PDF staff lyric row (fuzzy) and compare chord-anchored words.

For the first pass, we simply measure whether v3's reconstructed staff lines set of
(anchored_word, chord) pairs differs a lot from existing content's (word,chord) pairs.
"""
import json, sys, re, unicodedata
sys.path.insert(0,'/tmp/dlc/scripts')
from align_v3 import staffs, align_line, decode_chord

def norm(s):
    s=unicodedata.normalize('NFC',s.lower())
    return re.sub(r'[^a-z0-9ăâđêôơư]','',s)

def extract_pairs(line):
    # from a content line "[C]word1 [G]word2..." -> list of (word_norm, chord)
    out=[]
    # split on [chord]
    for m in re.finditer(r'\[([^\]]+)\]([^[]*)', line):
        ch=m.group(1); txt=m.group(2)
        for w in re.findall(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+', txt):
            if re.match(r'^[\d\.]+$',w): continue
            out.append((norm(w), ch))
    return out

def content_pairs(content):
    pairs=[]
    for line in content.split('\n'):
        t=line.strip()
        if t.startswith('[') and t.endswith(']') and '[' not in t[1:-1]: continue
        if t.startswith('//') or t.startswith('{'): continue
        if '[' in t:
            pairs.extend(extract_pairs(t))
    return pairs

def pdf_pairs(pdf):
    pairs={}
    for s in staffs(pdf):
        for ly in s['lyrics']:
            al=align_line(s['chords'],s['notes'],ly)
            for m in re.finditer(r'\[([^\]]+)\]([^[]*)', al):
                ch=m.group(1)
                txt=m.group(2)
                for w in re.findall(r'[A-Za-zĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]+', txt):
                    if re.match(r'^[\d\.]+$',w): continue
                    pairs.setdefault(norm(w),set()).add(decode_chord(ch))
    return pairs

def compare(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in __import__('os').listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    if not pdf: return None
    cp=content_pairs(s['content'])
    pp=pdf_pairs(pdf)
    cp_d={w:c for w,c in cp}
    # measure
    wc=set(cp_d); wp=set(pp)
    common=wc&wp
    agree=sum(1 for w in common if cp_d[w]==pp.get(w))
    moved=sum(1 for w in common if cp_d[w]!=pp.get(w))
    only_c=wc-wp; only_p=wp-wc
    return {'num':num,'title':s['title'],'content_chords':len(cp),'pdf_chords':len(pp),
            'agree':agree,'moved':moved,'only_content':len(only_c),'only_pdf':len(only_p)}

if __name__=='__main__':
    nums=[int(x) for x in sys.argv[1:]]
    for n in nums:
        r=compare(n)
        print(r)
