#!/usr/bin/env python3
"""Extraction v6 — staff-block parsing using split PDFs in /home/dangnsh/Dang_Loi_Ca_Split_PDFs/.
Each staff = 1 chord line + 1-2 lyric lines. Lyric lines unweave into
[Verse 1] / [Verse 2] via global line-count parity; explicit '1.'/'2.' or 'Chorus:' override.
"""
import pdfplumber, json, re, os, unicodedata

INDEX_PATH = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs/dlc_songs_database.json'
PDF_DIR = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs'
OUT_PATH = '/home/dangnsh/projects/dang-loi-ca-app/src/data/songs.json'

CHORD_RE = re.compile(
    r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$'
)
JUNK_RE = re.compile(r'^[b&\s\d™œÓ˙w‰jJ%„ŠŒ#=,;\.\'\-\|\[\]\(\)<>]*$')

def decode_chord(token):
    t = token.replace('“4', 'sus4').replace('“', 'sus')
    t = t.replace('‹', 'm').replace('„Š7', 'maj7').replace('„Š', 'maj')
    t = t.replace('&', '+').replace('Œ', '').replace('„', '')
    return re.sub(r'[^\w/#+\(\)b]', '', t)

def is_chord_word(w):
    if len(w) > 14: return False
    d = decode_chord(w)
    return bool(CHORD_RE.match(d)) if d else False

VIET_RE = re.compile(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', re.I)
def has_vietnamese(t): return bool(VIET_RE.search(t))

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

def parse_song_pdf(pdf_path, title):
    title_lower = title.lower()
    staves = []  # list of dicts: {'chords': [...], 'lyrics': [{'text': str, 'words': [...], 'x0': float}]}
    current_staff = {'chords': [], 'lyrics': []}

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
                if txt == txt.upper() and has_vietnamese(txt) and len(txt) > 4: continue
                if (txt.startswith(('Nguyên tác', 'Nhạc', 'LỜi Việt', 'LỜI VIỆT', 'Thi Thiên', 'Chưa rõ tác giả'))
                    or 'LỜI VIỆT' in txt.upper() or 'NGUYÊN TÁC' in txt.upper()):
                    continue

                nonjunk = [w for w in lw if not JUNK_RE.match(w['text'])]
                if nonjunk and not has_vietnamese(txt):
                    chords = [w for w in nonjunk if is_chord_word(w['text'])]
                    if chords and len(chords) / len(nonjunk) >= 0.4:
                        if current_staff['lyrics']:
                            staves.append(current_staff)
                            current_staff = {'chords': [], 'lyrics': []}
                        current_staff['chords'].extend(chords)
                        continue

                if has_vietnamese(txt):
                    current_staff['lyrics'].append({'text': txt, 'words': lw, 'x0': lw[0]['x0'] if lw else 0})

    if current_staff['lyrics']:
        staves.append(current_staff)

    # Unweave staves into sections
    v1_lines, v2_lines, chorus_lines = [], [], []
    v1_count, v2_count = 0, 0

    for staff in staves:
        chords = staff['chords']
        lyrics = staff['lyrics']
        if not lyrics: continue

        if len(lyrics) == 1:
            line = lyrics[0]
            txt = line['text']
            merged = merge_chords(chords, line['words'], txt)

            # Check explicit markers
            if txt.startswith('1.') or txt.startswith('1 '):
                v1_lines.append(re.sub(r'^1\.\s*', '', merged))
                v1_count += 1
            elif txt.startswith('2.') or txt.startswith('2 '):
                v2_lines.append(re.sub(r'^2\.\s*', '', merged))
                v2_count += 1
            elif txt.lower().startswith('đk:') or txt.lower().startswith('chorus'):
                chorus_lines.append(merged)
            else:
                # If indented (>120px) or chorus section active, assign to chorus else v1
                if line['x0'] > 120 or (v1_count > 0 and v2_count > 0 and len(v1_lines) == len(v2_lines)):
                    chorus_lines.append(merged)
                else:
                    v1_lines.append(merged)
                    v1_count += 1

        elif len(lyrics) >= 2:
            # 2 lyric lines under same chord line -> Verse 1 and Verse 2 side-by-side
            l1, l2 = lyrics[0], lyrics[1]
            m1 = merge_chords(chords, l1['words'], l1['text'])
            m2 = merge_chords(chords, l2['words'], l2['text'])

            # Clean explicit '1.' and '2.' prefixes if present
            m1 = re.sub(r'^1\.\s*', '', m1)
            m2 = re.sub(r'^2\.\s*', '', m2)

            v1_lines.append(m1)
            v2_lines.append(m2)
            v1_count += 1
            v2_count += 1

    blocks = []
    if v1_lines:
        blocks.append("[Verse 1]\n" + "\n".join(v1_lines))
    if v2_lines:
        blocks.append("[Verse 2]\n" + "\n".join(v2_lines))
    if chorus_lines:
        blocks.append("[Chorus]\n" + "\n".join(chorus_lines))

    # Fallback if unweaving resulted in empty blocks
    if not blocks:
        raw_lines = []
        for s in staves:
            for l in s['lyrics']:
                raw_lines.append(merge_chords(s['chords'], l['words'], l['text']))
        if raw_lines:
            blocks.append("[Verse 1]\n" + "\n".join(raw_lines))

    return "\n\n".join(blocks)

def main():
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    songs = []
    for item in db:
        num = item['num']
        title = item['title']
        pdf_file = item['pdf_file']
        pdf_path = os.path.join(PDF_DIR, pdf_file)

        if not os.path.exists(pdf_path):
            print(f"Warning: PDF {pdf_file} missing for song #{num}")
            continue

        chordpro = parse_song_pdf(pdf_path, title)
        
        # ASCII sheet slug
        sheet_slug = f"DLC_{num:03d}.pdf"

        songs.append({
            "id": str(num),
            "num": num,
            "title": title,
            "composer": "Dâng Lời Ca",
            "key": "C",
            "content": chordpro,
            "sheetUrl": f"/sheets/{sheet_slug}"
        })

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)

    print(f"Successfully processed {len(songs)} songs into {OUT_PATH}")

if __name__ == '__main__':
    main()
