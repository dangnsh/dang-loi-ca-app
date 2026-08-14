import sys, json, re, glob
d=json.load(open('/tmp/dlc/src/data/songs.json'))
DUP=re.compile(r'(\[[^\]]{1,15}\])\s*\1')         # adjacent identical chords
TRAILCH=re.compile(r'(\[[^\]]{1,15}\])+$')        # trailing chords at line end
# count songs (from current data) showing obvious noise patterns
dup_songs=[]; trail_songs=[]
for s in d:
    if s['num']<=5: continue
    c=s['content']
    if DUP.search(c): dup_songs.append(s['num'])
    if TRAILCH.search(c): trail_songs.append(s['num'])
print("songs with adjacent identical chords:", len(dup_songs), dup_songs[:40])
print("songs with trailing chord(s) at line end:", len(trail_songs))
