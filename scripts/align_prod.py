#!/usr/bin/env python3
"""Final production re-aligner module.

Reuses align_v5's validated machinery (extract_staffs + align_line → correct text-layer
chord->notehead->syllable alignment) but with an improved build_content that implements
anh Đăng's ĐK-detection rule:

  - A staff with 2+ interleaved lyric rows (Lời 1 / Lời 2 printed above/below the same
    chord line) => those rows are the VERSES (v1, v2, ...).
  - Once we've seen such a multi-verse staff, a later STAFF with only ONE lyric row and no
    verse-number prefix is the ĐK (Chorus) — because the chorus repeats identically for all
    verses, so it's typeset only once.
"""
import sys, os, json, glob, re, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pull validated machinery from align_v5
import align_v5 as _v5
extract_staffs = _v5.extract_staffs
align_line    = _v5.align_line

def _strip_num(line):
    # remove leading "1. " / "2. " / "3." verse-number prefix
    return re.sub(r'^[0-9]+[\.\s]+\s*', '', line)

def build_content(pdf_path, title):
    staffs = extract_staffs(pdf_path)
    streams = {}; order = []
    def emit(key, line):
        if key not in streams:
            streams[key] = []; order.append(key)
        streams[key].append(line)

    multi_seen = False   # saw a staff with 2+ interleaved lyric rows?
    for s in staffs:
        chords = s['chords']; notes = s['notes']
        rows = s['lyrics']
        if len(rows) == 1:
            ly = rows[0]; txt = ly[1].strip()
            line, _ = align_line(chords, notes, ly)
            line = _strip_num(line)
            expl = re.match(r'(?i)^(đk|chorus|điệp)[\.\s:]', txt) or re.match(r'(?i)^coda', txt)
            if expl:
                grp = 'coda' if re.match(r'(?i)^coda', txt) else 'chorus'
                emit(grp, re.sub(r'^(?i)(đk|chorus|điệp|coda)[\.\s:]+', '', line))
            else:
                is_verse_num = re.match(r'^[0-9]+[\.\s]', txt)
                if multi_seen and not is_verse_num:
                    emit('chorus', line)                 # ĐK rule
                else:
                    key = 'v1' if 'v2' not in streams else ('v2' if 'v3' not in streams else 'v1')
                    emit(key, line)
        else:
            multi_seen = True
            for k, ly in enumerate(rows):
                txt = ly[1].strip()
                line, _ = align_line(chords, notes, ly)
                line = _strip_num(line)
                expl = re.match(r'(?i)^(đk|chorus|điệp)[\.\s:]', txt) or re.match(r'(?i)^coda', txt)
                if expl:
                    grp = 'coda' if re.match(r'(?i)^coda', txt) else 'chorus'
                    emit(grp, re.sub(r'^(?i)(đk|chorus|điệp|coda)[\.\s:]+', '', line))
                else:
                    emit(f'v{k+1}', line)

    label = {'v1':'[Verse 1]','v2':'[Verse 2]','v3':'[Verse 3]','v4':'[Verse 4]',
             'v5':'[Verse 5]','v6':'[Verse 6]','v7':'[Verse 7]','v8':'[Verse 8]',
             'v9':'[Verse 9]','v10':'[Verse 10]','v11':'[Verse 11]','v12':'[Verse 12]',
             'v13':'[Verse 13]','v14':'[Verse 14]','v15':'[Verse 15]','v16':'[Verse 16]',
             'chorus':'[Chorus]','coda':'[Coda]'}
    parts = [label.get(key, f'[{key}]') + '\n' + '\n'.join(streams[key]) for key in order]
    return '\n\n'.join(parts)

if __name__ == '__main__':
    pdf = sys.argv[1]
    print(build_content(pdf, sys.argv[2] if len(sys.argv) > 2 else ''))
