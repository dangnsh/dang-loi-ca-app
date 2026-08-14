import json, sys
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for num in [int(x) for x in sys.argv[1:]]:
    s=[x for x in d if x['num']==num][0]
    print('== DLC',num,s['title'],'==')
    print(s['content'])
    print()
