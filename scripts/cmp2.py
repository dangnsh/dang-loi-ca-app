import sys, os, json
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for num in [int(x) for x in sys.argv[1:]]:
    s=[x for x in d if x['num']==num][0]
    pdf=f"/tmp/dlc/public/sheets/DLC_{num:03d}_{s['pdf_file'].split('_',2)[2] if s.get('pdf_file') else ''}"
    # find actual file
    pdf=None
    for f in os.listdir('/tmp/dlc/public/sheets'):
        if f.startswith(f'DLC_{num:03d}_'):
            pdf='/tmp/dlc/public/sheets/'+f; break
    print(f"\n############### DLC {num} {s['title']} ###############")
    print(v5.build_content(pdf, s['title']))
