import sys, time
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
t=time.time()
staffs=v5.extract_staffs('/tmp/dlc/public/sheets/DLC_002_Bai_ca_dang_Chua.pdf')
print("extract_staffs:", round(time.time()-t,2), "s, n_staffs=", len(staffs))
for s in staffs:
    print("  chords=",[v5.decode_chord(c['text']) for c in s['chords']],"nlyr=",len(s['lyrics']))
