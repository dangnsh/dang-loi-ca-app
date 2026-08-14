import json
from collections import Counter
d = json.load(open('/tmp/dlc/src/data/songs.json'))
s = d[0]
print('keys:', list(s.keys()))
c = Counter()
for x in d:
    c.update(x.keys())
print(dict(c))
print('has content:', sum(1 for x in d if x.get('content')))
print('has chopro:', sum(1 for x in d if x.get('chopro')))
print('has raw_text:', sum(1 for x in d if x.get('raw_text')))
print('has pdf_file:', sum(1 for x in d if x.get('pdf_file')))
# content field format check - sample a few
for x in d[:3]:
    print('---', x['num'], x['title'], '| content starts:', repr(x['content'][:80]))
