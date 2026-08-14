import sys, os, json, time
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
d=json.load(open('/tmp/dlc/src/data/songs.json'))
nums=[int(x) for x in sys.argv[1:]]
t0=time.time(); total_lines=0; max_chord=0; nch=0
for num in nums:
    s=[x for x in d if x['num']==num][0]
    pdf=next((f'/tmp/dlc/public/sheets/{x}' for x in os.listdir('/tmp/dlc/public/sheets') if x.startswith(f'DLC_{num:03d}_')),None)
    try:
        c=v5.build_content(pdf,s['title'])
    except Exception as e:
        print(f"{num}: ERR {e}"); continue
    labs=[l for l in c.split('\n') if l.startswith('[') and l.endswith(']')]
    nchord=c.count('[')
    max_chord=max(max_chord,nchord)
    nl=len(c.split('\n'))
    total_lines+=nl; nch+=1
    print(f"DLC {num}: {len(labs)} labels {labs} | lines={nl} | chords={nchord}")
print("---"); print("songs:",nch,"avg lines",total_lines/max(1,nch),"time",round(time.time()-t0,1),"s")
