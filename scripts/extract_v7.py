#!/usr/bin/env python3
"""Extraction v7 — linear ChordPro extraction & full metadata mapping.
Fixes:
1. No complex verse/chorus unweaving (keeps natural linear PDF flow).
2. Maps `pdf_file` and `sheetUrl` to exact ASCII PDF files in public/sheets/.
3. Populates content, chopro, raw_text, pdf_file, sheetUrl for 100% component compatibility.
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

def extract_linear_song(pdf_path, title):
    title_lower = title.lower()
    lines = []
    pending_chords = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.0)
            yg = {}
            for w in words:
                yg.setdefault(round(w['top']), []).append(w)

            for y in sorted(yg):
                lw = sorted(yg[y], key=lambda x: x['x0'])
                raw = join_words(lw)
                txt = clean_lyric(raw)
                if not txt: continue
                if all(JUNK_RE.match(t) for t in raw.split()): continue
                if re.match(r'^\d+fr$', txt) or txt in ('J', '˙', 'w'): continue
                if re.sub(r'^\d+\.?\s*', '', txt).strip().lower() == title_lower: continue
                if txt == txt.upper() and VIET_RE.search(txt) and len(txt) > 4: continue
                if (txt.startswith(('Nguyên tác', 'Nhạc', 'LỜi Việt', 'LỜI VIỆT', 'Thi Thiên', 'Chưa rõ tác giả'))
                    or 'LỜI VIỆT' in txt.upper() or 'NGUYÊN TÁC' in txt.upper()):
                    lines.append(f"//{txt}")
                    continue

                nonjunk = [w for w in lw if not JUNK_RE.match(w['text'])]
                if nonjunk and not VIET_RE.search(txt):
                    chords = [w for w in nonjunk if is_chord_word(w['text'])]
                    if chords and len(chords) / len(nonjunk) >= 0.3:
                        pending_chords.extend(chords)
                        continue

                if VIET_RE.search(txt):
                    merged = merge_chords(pending_chords, lw, txt)
                    lines.append(merged)
                    pending_chords = []

            if pending_chords:
                c_str = ' '.join(f'[{decode_chord(w["text"])}]' for w in pending_chords)
                lines.append(c_str)
                pending_chords = []

    return "\n".join(lines)

def main():
    # Build sheet map for public/sheets
    sheets = os.listdir(SHEETS_DIR)
    sheet_map = {}
    for filename in sheets:
        m = re.match(r'DLC_(\d{3})_.*\.pdf', filename)
        if m:
            sheet_map[int(m.group(1))] = filename

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

        chordpro = extract_linear_song(pdf_path, title)

        # Get exact public sheet filename
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

    print(f"Successfully processed {len(songs)} songs into {OUT_PATH}")

if __name__ == '__main__':
    main()
