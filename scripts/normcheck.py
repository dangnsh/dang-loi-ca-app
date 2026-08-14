import sys, json, re, os, glob
sys.path.insert(0,'/tmp/dlc/scripts')
import align_v5 as v5
d=json.load(open('/tmp/dlc/src/data/songs.json'))

def strip_section(label): 
    m=re.match(r'\[(.*?)\]',label); return m.group(1) if m else label

def words_of_content(s):
    # remove [Chord] tokens, //comments, {meta}, section labels; return normalized words
    txt=re.sub(r'\[[^\]]{1,15}\]','',s['content'])
    txt=re.sub(r'//.*','',txt)
    txt=re.sub(r'\{.*?\}','',txt)
    txt=re.sub(r'^\s*1\.\s*|^\s*2\.\s*|^\s*3\.\s*|^\s*4\.\s*','',txt)
    ws=re.findall(r'[\w\p{L}\u0300-​]+', lower['...'])
    return None

def norm_words(s):
    txt=re.sub(r'\[[^\]]{1,15}\]','',s)
    txt=re.sub(r'//.*','',txt)
    txt=re.sub(r'\{.*?\}','',txt)
    txt=re.sub(r'\d+\.','',txt)
    ws=re.findall(r"[\w\u00C0-\u1EF9']+", txt.lower())
    return ws

for num in [int(x) for x in sys.argv[1:]]:
    s=[x for x in d if x['num']==num][0]
    pdf=glob.glob(f'/tmp/dlc/public/sheets/DLC_{num:03d}_*.pdf')
    if not pdf: print(num,'NO PDF'); continue
    golden=v5.build_content(pdf[0], s['title'])
    gw=norm_words(golden); cw=norm_words(s['content'])
    common=len(set(gw)&set(cw)); 
    print(f"DLC {num}: golden_words={len(gw)} content_words={len(cw)} overlap={common} ratio={common/max(len(gw),1):.2f}")
