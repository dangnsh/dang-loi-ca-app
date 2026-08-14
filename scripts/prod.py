#!/usr/bin/env python3
"""Production runner — regenerate content for songs 6-300 via v10 (golden chords + current
section labels). Songs 1-5 are NEVER touched (already verified correct).

Usage: python3 scripts/prod.py <start> <end> [--dry] [--show]
Updates src/data/songs.json in place; prints a per-song report (before/after chord counts,
section labels, any unmatched golden lines). --dry prints report without writing.
"""
import sys, json, os, glob, re
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v10 as v10

CH=re.compile(r'\[[^\]]{1,15}\]')
KEEP=set(range(1,6))  # never touch verified songs

def chordcount(s): return len(CH.findall(s))
def sections(s):
    return re.findall(r'^\[([^\]]+)\]$', s, re.M)

def hyphen_fix(s):
    # rejoin Vietnamese hyphenated compounds "Giê - xu", "Ha - lê - lu - gia"
    s=re.sub(r'\s*-\s*(?=\w)','-',s)
    # but preserve " - " used as standalone dash? leave as is
    return s

def main():
    args=[a for a in sys.argv[1:]]
    dry = '--dry' in args; show='--show' in args
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
        pdfs=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')
        if not pdfs: print(f"DLC {num}: NO PDF"); continue
        new=v10.main(num)  # regenerated content (no hyphen fix yet)
        new_c=chordcount(s['content']); new_n=chordcount(new)
        sc=sections(s['content']); ns=sections(new)
        new=hyphen_fix(new)
        s['content']=new
        flag=''
        if new_n==0: flag=' !!ZERO CHORDS!!'
        if not ns: flag+=' !!NO SECTIONS!!'
        print(f"DLC {num}: chords {new_c}->{new_n} | sec {sc}->{ns}{flag}")
        if show:
            print('  '+(new[:180].replace('\n',' | ')))
    if not dry:
        json.dump(d,open(D,'w'),ensure_ascii=False,indent=2)
    else:
        print("(dry run — not written)")

if __name__=='__main__': main()
