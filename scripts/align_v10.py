#!/usr/bin/env python3
"""v10 — golden base + current section-label reattachment.

golden (v5) gives correct chords+lyrics from PDF text layer. current content gives reliable
section labels ([Intro],[Verse N],[Chorus N]) + //meta. Rebuild: meta lines (from current)
then each current section in order, attaching its label to the golden lines whose normalized
lyric text matches. Preserves structure, fixes chords.
"""
import sys, json, os, glob, re
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5

CH = re.compile(r'\[[^\]]{1,15}\]')
SECTION = re.compile(r'^\s*\[([^\]]+)\]\s*$')

def normw(txt):
    t=re.sub(CH,'',txt); t=re.sub(r'\{.*?\}','',t)
    return re.findall(r"[\w\u00C0-\u1EF9]+", t.lower())

def parse_current(content):
    """return (meta_lines, sections) where sections = [(label, [lyric_lines])]"""
    meta=[]; sections=[]; cur_label=None; cur_lines=[]
    for ln in content.splitlines():
        ls=ln.strip()
        if not ls: continue
        if ls.startswith('//') or ls.startswith('{'):
            meta.append(ls); continue
        m=SECTION.match(ls)
        if m:
            if cur_lines: sections.append((cur_label,cur_lines))
            cur_label=m.group(1); cur_lines=[]; continue
        cur_lines.append(ls)
    if cur_lines: sections.append((cur_label,cur_lines))
    return meta,sections

def main(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')[0]
    golden=v5.build_content(pdf, s['title'])
    # golden lines (drop any section labels v5 emitted, we use current's)
    glines=[l for l in golden.splitlines() if l.strip() and not SECTION.match(l.strip())]

    meta,sections=parse_current(s['content'])
    used=[False]*len(glines)
    out=meta[:] if meta else []
    for label,lines in sections:
        out.append(f'[{label}]' if label else '')
        # normalized lyric words of this section (concatenated)
        sec_norm=[]
        for ln in lines:
            sec_norm+=normw(ln)
        if not sec_norm:
            # keep blank lines
            for ln in lines: out.append(ln)
            continue
        # find golden lines matching this section's words, greedy order
        taken=[]
        # score each unused golden line vs section by word overlap (weighted by order not needed)
        for li,l in enumerate(glines):
            if used[li]: continue
            lw=normw(l)
            if not lw: continue
            inter=len(set(lw)&set(sec_norm))
            r=inter/max(len(set(lw)),1)
            if r>=0.5:
                taken.append((li,l,r))
        # order taken by golden sequence index (musical order)
        taken.sort(key=lambda x:x[0])
        for li,l,r in taken[:len(lines)]:
            used[li]=True
            out.append(l)
    # any unclaimed golden lines -> append at end (don't lose lyrics)
    leftover=[l for li,l in enumerate(glines) if not used[li]]
    for l in leftover:
        out.append(l)
    return os.linesep.join(out)

if __name__=='__main__':
    print(main(int(sys.argv[1])))
