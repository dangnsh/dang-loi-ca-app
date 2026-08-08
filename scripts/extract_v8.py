#!/usr/bin/env python3
"""Extraction v8 — Smart Staff-Unweaving Engine for Dâng Lời Ca.
Handles:
1. Interleaved 2-verse staves (223 songs): separates top lines into Verse 1 and bottom lines into Verse 2, matching the actual musical flow.
2. Single-line staves (77 songs): preserves linear sequence with section detection (Verse 1/2/3, Chorus).
3. Title & Header filtering: removes repeated title headers from lyric staves.
4. Maps 100% of public sheet PDFs and metadata for complete component compatibility.
"""
import pdfplumber, json, re, os

INDEX_PATH = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs/dlc_songs_database.json'
PDF_DIR = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs'
SHEETS_DIR = '/home/dangnsh/projects/dang-loi-ca-app/public/sheets'
OUT_PATH = '/home/dangnsh/projects/dang-loi-ca-app/src/data/songs.json'

CHORD_RE = re.compile(
    r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$'
)
JUNK_RE = re.compile(r'^[b&\s\d™œÓ˙w‰jJ%„ŠŒ#=,;\.\'\-\|\[\]\(\)<>]*$')
VIET_RE = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)

def decode_chord(token):
    t = token.replace('“4', 'sus4').replace('“', 'sus')
    t = t.replace('‹', 'm').replace('„Š7', 'maj7').replace('„Š', 'maj')
    t = t.replace('&', '+').replace('Œ', '').replace('„', '')
    return re.sub(r'[^\w/#+\(\)b]', '', t)

def is_chord_word(w):
    if len(w) > 14: return False
    d = decode_chord(w)
    return bool(CHORD_RE.match(d)) if d else False

def clean_lyric(text):
    t = re.sub(r'[™œÓ˙w‰j„ŠŒ]', '', text)
    t = re.sub(r'\s+', ' ', t).strip()
    up = 'A-ZĂÂĐÊÔƠƯÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ'
    return re.sub(r'([a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ])([' + up + '])', r'\1 \2', t)

def join_words(words):
    parts, prev = [], None
    for w in words:
        t = w['text']
        if JUNK_RE.match(t): continue
        if prev is not None and (w['x0'] - prev) > 0.4:
            parts.append(' ')
        parts.append(t)
        prev = w['x1']
    return ''.join(parts)

def merge_chords(chords, lyric_words, lyric_str):
    if not chords: return lyric_str
    anchors = []
    pos = 0
    for w in lyric_words:
        t = w['text']
        if JUNK_RE.match(t): continue
        found = lyric_str.find(t, pos)
        if found == -1: found = pos
        anchors.append((found, w['x0']))
        pos = found + len(t)
    inserts = []
    for cw in chords:
        idx = len(lyric_str)
        for char_idx, ax in anchors:
            if ax >= cw['x0'] - 3:
                idx = char_idx
                break
        inserts.append((idx, decode_chord(cw['text'])))
    out = lyric_str
    for idx, ch in sorted(inserts, key=lambda t: t[0], reverse=True):
        out = out[:idx] + f'[{ch}]' + out[idx:]
    return out

def is_title_line(txt, title):
    t_clean = re.sub(r'^\d+\.?\s*', '', txt).strip().lower()
    title_clean = title.strip().lower()
    if not t_clean or not title_clean: return False
    return t_clean == title_clean or t_clean in title_clean or title_clean in t_clean

def parse_song_smart(pdf_path, title):
    meta_lines = []
    raw_lines = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.0)
            yg = {}
            for w in words: yg.setdefault(round(w['top']), []).append(w)

            for y in sorted(yg):
                lw = sorted(yg[y], key=lambda x: x['x0'])
                raw = join_words(lw)
                txt = clean_lyric(raw)
                if not txt: continue
                if all(JUNK_RE.match(t) for t in raw.split()): continue
                if re.match(r'^\d+fr$', txt) or txt in ('J', '˙', 'w'): continue
                if is_title_line(txt, title): continue

                if (txt.startswith(('Nguyên tác', 'Nhạc', 'LỜi Việt', 'LỜI VIỆT', 'Thi Thiên', 'Chưa rõ tác giả'))
                    or 'LỜI VIỆT' in txt.upper() or 'NGUYÊN TÁC' in txt.upper()):
                    meta_lines.append(f"//{txt}")
                    continue

                nonjunk = [w for w in lw if not JUNK_RE.match(w['text'])]
                if nonjunk and not VIET_RE.search(txt):
                    chords = [w for w in nonjunk if is_chord_word(w['text'])]
                    if chords and len(chords) / len(nonjunk) >= 0.3:
                        raw_lines.append(('chord', chords, y, lw))
                        continue

                if VIET_RE.search(txt):
                    raw_lines.append(('lyric', txt, y, lw))

    # Group into staves
    staves = []
    current_staff = {'chords': [], 'lyrics': []}

    for item in raw_lines:
        if item[0] == 'chord':
            if current_staff['lyrics']:
                staves.append(current_staff)
                current_staff = {'chords': [], 'lyrics': []}
            current_staff['chords'].extend(item[1])
        elif item[0] == 'lyric':
            current_staff['lyrics'].append({'txt': item[1], 'y': item[2], 'lw': item[3]})

    if current_staff['lyrics']:
        staves.append(current_staff)

    v1_lines, v2_lines, chorus_lines = [], [], []

    for staff in staves:
        chords = staff['chords']
        lyrics = staff['lyrics']
        if not lyrics: continue

        if len(lyrics) == 1:
            line = lyrics[0]
            txt = line['txt']
            merged = merge_chords(chords, line['lw'], txt)

            if txt.startswith('1.') or txt.startswith('1 '):
                v1_lines.append(re.sub(r'^1\.\s*', '', merged))
            elif txt.startswith('2.') or txt.startswith('2 '):
                v2_lines.append(re.sub(r'^2\.\s*', '', merged))
            elif txt.lower().startswith('đk:') or txt.lower().startswith('chorus'):
                chorus_lines.append(re.sub(r'^(đk|chorus):\s*', '', merged, flags=re.I))
            else:
                if len(v1_lines) > 0 and len(v2_lines) > 0:
                    chorus_lines.append(merged)
                else:
                    v1_lines.append(merged)

        elif len(lyrics) >= 2:
            lyrics_sorted = sorted(lyrics, key=lambda l: l['y'])
            l1, l2 = lyrics_sorted[0], lyrics_sorted[1]

            m1 = merge_chords(chords, l1['lw'], l1['txt'])
            m2 = merge_chords(chords, l2['lw'], l2['txt'])

            m1 = re.sub(r'^1\.\s*', '', m1)
            m2 = re.sub(r'^2\.\s*', '', m2)

            v1_lines.append(m1)
            v2_lines.append(m2)

            for l3 in lyrics_sorted[2:]:
                m3 = merge_chords(chords, l3['lw'], l3['txt'])
                chorus_lines.append(m3)

    blocks = []
    if meta_lines:
        blocks.append("\n".join(meta_lines))
    if v1_lines:
        blocks.append("[Verse 1]\n" + "\n".join(v1_lines))
    if v2_lines:
        blocks.append("[Verse 2]\n" + "\n".join(v2_lines))
    if chorus_lines:
        blocks.append("[Chorus]\n" + "\n".join(chorus_lines))

    if not blocks:
        # Fallback raw line joiner
        fallback_lines = []
        for s in staves:
            for l in s['lyrics']:
                fallback_lines.append(merge_chords(s['chords'], l['lw'], l['txt']))
        blocks.append("\n".join(fallback_lines))

    return "\n\n".join(blocks)

def main():
    sheets = os.listdir(SHEETS_DIR)
    sheet_map = {}
    for filename in sheets:
        m = re.match(r'DLC_(\d{3})_.*\.pdf', filename)
        if m: sheet_map[int(m.group(1))] = filename

    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    songs = []
    for item in db:
        num = item['num']
        title = item['title']
        pdf_file_src = item['pdf_file']
        pdf_path = os.path.join(PDF_DIR, pdf_file_src)

        if not os.path.exists(pdf_path):
            print(f"Warning: PDF {pdf_file_src} missing for song #{num}")
            continue

        chordpro = parse_song_smart(pdf_path, title)
        public_sheet = sheet_map.get(num, f"DLC_{num:03d}.pdf")

        songs.append({
            "id": str(num),
            "num": num,
            "title": title,
            "composer": "Dâng Lời Ca",
            "key": "C",
            "content": chordpro,
            "chopro": chordpro,
            "raw_text": chordpro,
            "pdf_file": public_sheet,
            "sheetUrl": f"/sheets/{public_sheet}"
        })

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)

    print(f"Successfully processed {len(songs)} songs with smart staff-unweaving into {OUT_PATH}")

if __name__ == '__main__':
    main()
