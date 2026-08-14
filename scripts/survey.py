import pdfplumber, re, glob, os, json
from collections import Counter

NOTE = re.compile(r'^[œ˙™Ó‰]+$')
JUNK = re.compile(r'^[b&wjJ‰œÓ˙™\d\s\.,;:\'"\-|\[\]()<>%$@#=]+$')
CH = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')

def decode_chord(t):
    t = t.replace('“4','sus4').replace('“','sus').replace('‹','m')
    t = t.replace('„Š7','maj7').replace('„Š','maj').replace('&','+').replace('Œ','').replace('„','')
    return re.sub(r'[^\w/#+\(\)b]','',t)

def is_chord(w):
    d = decode_chord(w)
    return bool(d) and bool(CH.match(d))

pdfs = sorted(glob.glob('/tmp/dlc/public/sheets/DLC_*.pdf'))
print('total pdfs:', len(pdfs))
stats = Counter()
examples = {}
no_lyric = 0
chord_lines = 0
note_lines = 0
for p in pdfs[:40]:  # survey first 40
    num = int(os.path.basename(p).split('_')[1])
    try:
        with pdfplumber.open(p) as pdf:
            nch=nnt=nly=0
            for page in pdf.pages:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.0)
                for w in words:
                    t = w['text']
                    if NOTE.match(t): nnt+=1
                    elif is_chord(t): nch+=1
                # lyric detection: has vietnamese accents
            stats['chords']+=nch; stats['notes']+=nnt
    except Exception as e:
        print('ERR', num, e)
print('survey 40 songs: total chord tokens', stats['chords'], 'note tokens', stats['notes'])
