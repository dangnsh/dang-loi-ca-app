#!/usr/bin/env python3
"""Production re-aligner for songs 6-300 (uses align_prod.build_content with ĐK rule).

Preserves `//` credit comments, drops junk title/composer lines, fixes hyphens. #1-5 kept.
Usage: python3 scripts/prod2.py <start> <end> [--dry] [--show]
"""
import sys, json, os, glob, re
sys.path.insert(0,'/tmp/dlc/scripts')
import align_prod as v

CH=re.compile(r'\[[^\]]{1,15}\]')
KEEP=set(range(1,6))

def chordcount(s): return len(CH.findall(s))
def sections(s): return re.findall(r'^\[([^\]]+)\]$', s, re.M)
def extract_meta(content): return [l.strip() for l in content.splitlines() if l.strip().startswith('//')]

def hyphen_fix(s):
    return re.sub(r'(?<=[A-Za-zÀ-ỹ])\s*-\s*(?=[A-Za-zÀ-ỹ])','-',s)

def build(num):
    d=json.load(open('/tmp/dlc/src/data/songs.json'))
    s=[x for x in d if x['num']==num][0]
    pdfs=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')
    if not pdfs: return None,'NO PDF'
    meta=extract_meta(s['content'])
    gold=hyphen_fix(v.build_content(pdfs[0], s['title']))
    parts=[]
    for m in meta: parts.append(m)
    parts.append(''); parts.append(gold.strip())
    return '\n'.join(parts), None

def main():
    args=[a for a in sys.argv[1:]]
    dry='--dry' in args; show='--show' in args
    nums=[int(a) for a in args if a.isdigit()]
    if len(nums)!=2: print("need start end"); sys.exit(1)
    start,end=nums
    D='/tmp/dlc/src/data/songs.json'
    d=json.load(open(D))
    for num in range(start,end+1):
        if num in KEEP:
            print(f"DLC {num}: SKIP (verified curated)"); continue
        s=[x for x in d if x['num']==num]
        if not s: print(f"DLC {num}: not found"); continue
        s=s[0]
        new,err=build(num)
        if err: print(f"DLC {num}: ERROR {err}"); continue
        oc=chordcount(s['content']); nc=chordcount(new)
        osc,nsc=sections(s['content']),sections(new)
        flag=''
        if nc==0: flag+=' !!ZERO CHORDS!!'
        if not nsc: flag+=' !!NO SECTIONS!!'
        s['content']=new; s['chopro']=new
        print(f"DLC {num}: chords {oc}->{nc} | sec {osc}->{nsc}{flag}")
        if show:
            print('   '+(new.replace('\n',' | ')[:220]))
    if not dry:
        json.dump(d,open(D,'w'),ensure_ascii=False,indent=2)
    else:
        print("(dry run — not written)")

if __name__=='__main__': main()
