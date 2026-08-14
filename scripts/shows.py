import sys, json, re
d=json.load(open('/tmp/dlc/src/data/songs.json'))
for n in [int(x) for x in sys.argv[1:]]:
    s=[x for x in d if x['num']==n][0]
    print('==== DLC',n,s['title'],'====')
    print(s['content'])
    print()
