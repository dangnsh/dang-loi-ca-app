import sys
sys.path.insert(0,'/tmp/dlc/scripts')
from align_v2 import staffs, load_rows
pdf='/tmp/dlc/public/sheets/DLC_002_Bai_ca_dang_Chua.pdf'
# dump raw rows first 80
print("=== RAW ROWS ===")
for i,(typ,pl) in enumerate(load_rows(pdf)):
    if i>70: break
    if typ=='CHORD': print(f"{i:3d} CH  {[w['text'] for w in pl]}")
    elif typ=='NOTE': print(f"{i:3d} NT  {[ (w['text'],round(w['x0'])) for w in pl]}")
    else: print(f"{i:3d} LYR {pl[1][:40]!r}")
print("\n=== STAFFS ===")
for i,s in enumerate(staffs(pdf)):
    print(f"staff {i}: nchords={len(s['chords'])} nnotes={len(s['notes'])} nlyr={len(s['lyrics'])}")
    print("   notes x:", [round(n['x0']) for n in s['notes']])
    print("   chords :", [decode_chord(c['text']) for c in s['chords']])
    for ly in s['lyrics']: print("   LYR:",ly[1][:50])
