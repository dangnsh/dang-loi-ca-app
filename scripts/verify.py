import json, re
d=json.load(open('/tmp/dlc/src/data/songs.json'))
# verify 1-5 unchanged vs backup
bak=json.load(open('/tmp/dlc/scripts/songs_backup_before_prod.json'))
for n in range(1,6):
    a=[x for x in d if x['num']==n][0]['content']
    b=[x for x in bak if x['num']==n][0]['content']
    print(f"DLC {n}: {'UNCHANGED' if a==b else 'CHANGED!!'}")
print("---- DLC 280 sections + snippet ----")
s=[x for x in d if x['num']==280][0]
print(s['content'][:400])
