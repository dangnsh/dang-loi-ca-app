#!/usr/bin/env python3
"""v9 — regression-safe structure-preserving hybrid.

Keep current content lines/meta/sections verbatim as the skeleton. For each lyric line,
if the golden (v5) line's chord tokens are ALIGNED with the same lyric words, replace the
line's chord tokens accordingly. If matching fails, keep the current line untouched so we
can never regress already-correct songs (#1-5).
"""
import sys, json, os, glob, re, difflib
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5

CH = re.compile(r'\[[^\]]{1,15}\]')

def lyric_of(line):
    """return normalized lyric words (chords stripped, punctuation dropped), and the raw lyric"""
    raw=re.sub(CH,'',line)
    raw=re.sub(r'\{.*?\}','',raw)
    return raw.strip()

def normw(line):
    raw=lyric_of(line)
    ws=re.findall(r"[\w\u00C0-\u1EF9]+", raw.lower())
    return ws

def split_tokens(line):
    """split content line into (chord, lyricword) alternating; returns list of lyric word tokens and chord-before-each."""
    toks=[]; i=0; cur_chord=None
    while i < len(line):
        c=CH.match(line,i)
        if c:
            cur_chord=c.group(0); i=c.end(); continue
        # read a char run (word / punct / space)
        j=i
        while j<len(line) and not CH.match(line,j):
            j+=1
        seg=line[i:j]; i=j
        toks.append((cur_chord,seg))
        # chord applies to next word
        cur_chord=None
    return toks

def realign(line, gline):
    """Return line with chord tokens repositioned to match golden line's chord->word mapping.
    Strategy: for each word in this line, find corresponding word in golden line; if that golden
    word has a chord, attach it. Keep hyphens/punct from this line. Words not found keep no chord."""
    pltoks=split_tokens(line)
    p_words=[t[1] for t in pltoks if t[1].strip() and not t[1].strip()=='-']
    g_raw=lyric_of(gline)
    g_words=re.findall(r"[\w\u00C0-\u1EF9\-]+", g_raw)
    g_toks=split_tokens(gline)
    # build golden word->chord map (chord that precedes each lyric word incl hyphens)
    g_map={}
    cur=None
    for (ch,seg) in g_toks:
        if ch: cur=ch
        if seg.strip():
            key=seg.strip().lower()
            g_map.setdefault(key,cur)
    # now reconstruct word by word; simulate chords
    out=[]; wci=0
    # build list of actual word segments (including hyphen compounds) to assign chords
    segs=[t for t in pltoks]
    # first, word tokens with their normalized forms
    wi=0; res=[]; pending=''
    i=0
    # We'll rebuild: iterate pltoks, decide chord before each "wordy" segment.
    wordidx=0
    realwl=[t[1] for t in pltoks if t[1].strip() and t[1].strip()!='-']
    # normalize real words (strip hyphens into parts)
    # assign a chord to each real word by matching to golden words sequence position
    gnorm=normw(gline)
    # try simple: for each real word, look up g_map by lowercased stripped word
    for (ch,seg) in pltoks:
        if ch:  # current line already had a chord here; we keep position but will re-eval below
            pass
    return None  # not used

def main(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')[0]
    golden=v5.build_content(pdf, s['title'])
    glines=[l for l in golden.splitlines()]
    gchords=[]  # parallel list of chord-token strings per golden line
    for l in glines:
        gchords.append(''.join(CH.findall(l)))

    out=[]
    for line in s['content'].splitlines():
        ls=line.strip()
        if not ls or ls.startswith('//') or ls.startswith('{') or ls.startswith('['):
            out.append(line); continue
        # lyric line: find best golden line by normalized word match
        wn=normw(line)
        best=None; bestr=0
        for gl,gc in zip(glines,gchords):
            gw=normw(gl)
            if not gw: continue
            inter=len(set(wn)&set(gw)); union=len(set(wn)|set(gw))
            r=inter/union if union else 0
            if r>bestr: bestr=r; best=(gl,gc)
        if best and bestr>=0.5:
            # build from current lyric but golden chords
            newl=merge_chords(line,best[1])
            out.append(newl)
        else:
            out.append(line)
    result=os.linesep.join(out)
    # pretty: no trailing spaces
    return result

if __name__=='__main__':
    print(main(int(sys.argv[1])))
