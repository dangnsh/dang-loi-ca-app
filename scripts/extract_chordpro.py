import pdfplumber
import json
import re
import unicodedata

PDF_PATH = '/home/dangnsh/.hermes/cache/documents/doc_cf7520ff30a6_Dang-Loi-Ca.pdf'
INDEX_PATH = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs/songs_index.json'
OUT_PATH = '/home/dangnsh/projects/dang-loi-ca-app/src/data/songs.json'

# --- Music font symbol decoding ---
def decode_chord(token):
    """Decode sheet-music font chord symbols into standard text chords."""
    t = token
    t = t.replace('“4', 'sus4').replace('“', 'sus')
    t = t.replace('‹', 'm')                 # minor
    t = t.replace('„Š7', 'maj7').replace('„Š', 'maj')  # maj7
    t = t.replace('&', '+')                 # augmented (best guess)
    t = t.replace('Œ', '').replace('„', '')
    # strip remaining weird glyphs
    t = re.sub(r'[^\w/#+\(\)b]', '', t)
    return t

# Chord pattern: root A-G, optional #/b, optional suffix (m, 7, sus4, maj7, dim, +, 9...), optional /bass
CHORD_RE = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')

# Junk tokens from music notation layer
JUNK_RE = re.compile(r'^[b&\s\d™œÓ˙w‰jJ%„ŠŒ„#=,;\.\'\-\|\[\]\(\)<>]*$')

def is_chord_word(w):
    if len(w) > 14:
        return False
    d = decode_chord(w)
    return bool(CHORD_RE.match(d)) if d else False

def has_vietnamese(text):
    return bool(re.search(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', text, re.I))

def clean_lyric(text):
    t = text.replace('', '').replace('', '')
    t = re.sub(r'[™œÓ˙w‰j„ŠŒ]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Heuristic: split glued words — lowercase followed by uppercase (e.g. áiđức, ChúaChúa)
    # Vietnamese uppercase set included
    upper = 'A-ZĂÂĐÊÔƠƯÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ'
    t = re.sub(r'([a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ])([' + upper + '])', r'\1 \2', t)
    return t

def group_lines(words, y_tol=4):
    """Group words into lines by 'top' coordinate."""
    words = sorted(words, key=lambda w: (round(w['top'] / y_tol), w['x0']))
    lines = []
    cur = []
    cur_top = None
    for w in words:
        if cur_top is None or abs(w['top'] - cur_top) <= y_tol:
            cur.append(w)
            if cur_top is None:
                cur_top = w['top']
        else:
            lines.append(sorted(cur, key=lambda w: w['x0']))
            cur = [w]
            cur_top = w['top']
    if cur:
        lines.append(sorted(cur, key=lambda w: w['x0']))
    return lines

def classify_line(words):
    """Return ('chord'|'lyric'|'junk'|'meta'|'title', words/text)."""
    texts = [w['text'] for w in words]
    joined = ' '.join(texts).strip()
    if not joined:
        return ('junk', None)
    if re.match(r'^\d+fr$', joined) or joined in ('J', '˙', 'w'):
        return ('junk', None)
    if all(JUNK_RE.match(t) for t in texts):
        return ('junk', None)
    if joined.startswith(('Nguyên tác', 'LỜI VIỆT', 'LỜi Việt', 'LỜi Việt:', 'LỜi Việt', 'Thi Thiên', 'Chưa rõ tác giả', 'LỜi:')) or 'LỜi Việt' in joined.upper() or 'NGUYÊN TÁC' in joined.upper():
        return ('meta', joined)
    # Song title line: ALL CAPS Vietnamese (e.g. BÀI CA NGỢI KHEN)
    if joined == joined.upper() and has_vietnamese(joined) and len(joined) > 4:
        return ('title', joined)
    chord_words = [w for w in words if is_chord_word(w['text'])]
    # line is chord line if >=60% of non-junk tokens are chords and no vietnamese
    nonjunk = [w for w in words if not JUNK_RE.match(w['text'])]
    if nonjunk and not has_vietnamese(joined):
        ratio = len([w for w in nonjunk if is_chord_word(w['text'])]) / len(nonjunk)
        if ratio >= 0.6:
            return ('chord', [w for w in nonjunk if is_chord_word(w['text'])])
    if has_vietnamese(joined):
        return ('lyric', words)
    return ('junk', None)

def merge_chord_lyric(chord_words, lyric_words):
    """Insert chords into lyric text by x-coordinate alignment -> ChordPro line."""
    # build lyric string with char->x mapping
    chars = []  # (char, x0)
    for w in lyric_words:
        t = w['text']
        if JUNK_RE.match(t):
            continue
        for c in t:
            chars.append((c, w['x0']))
        chars.append((' ', w['x0'] + (w['x1'] - w['x0'])))  # space at word end
    lyric_str = ''.join(c for c, _ in chars)
    lyric_str = clean_lyric(lyric_str)
    if not lyric_str:
        return ''
    # find insertion points: for each chord, nearest char index whose x >= chord.x0
    inserts = []
    for cw in chord_words:
        cx = cw['x0']
        idx = len(lyric_str)
        for i, (c, x) in enumerate(chars):
            if x >= cx - 2:
                idx = i
                break
        inserts.append((idx, decode_chord(cw['text'])))
    inserts.sort(key=lambda t: t[0], reverse=True)
    out = lyric_str
    for idx, ch in inserts:
        out = out[:idx] + f'[{ch}]' + out[idx:]
    return out

def extract_song(page_lines, start_p, end_p):
    elements = []
    for p in range(start_p - 1, end_p):
        for lw in page_lines.get(p, []):
            kind, data = classify_line(lw)
            if kind == 'junk':
                continue
            elements.append((kind, data))
    # merge: a chord line applies to the NEXT lyric line(s)
    out_lines = []
    pending_chords = None
    seen_title = False
    for kind, data in elements:
        if kind == 'title':
            if seen_title:
                continue  # skip repeated running headers
            seen_title = True
            continue  # title already shown by UI; skip in body
        if kind == 'meta':
            out_lines.append('{' + data + '}')
        elif kind == 'chord':
            pending_chords = data
        elif kind == 'lyric':
            if pending_chords:
                merged = merge_chord_lyric(pending_chords, data)
                if merged:
                    out_lines.append(merged)
                pending_chords = None
            else:
                t = clean_lyric(join_lyric_words(data))
                if t:
                    out_lines.append(t)
    return '\n'.join(out_lines)

def join_lyric_words(words):
    """Join lyric words, inserting a space only when the x-gap indicates a real word break."""
    parts = []
    prev_x1 = None
    for w in words:
        t = w['text']
        if JUNK_RE.match(t):
            continue
        if prev_x1 is not None and (w['x0'] - prev_x1) > 0.8:
            parts.append(' ')
        parts.append(t)
        prev_x1 = w['x1']
    return ''.join(parts)

def slug(title, num):
    nfkd = unicodedata.normalize('NFKD', title)
    clean = ''.join(c for c in nfkd if not unicodedata.combining(c)).replace('đ', 'd').replace('Đ', 'D')
    clean = re.sub(r'[^\w\s\-]', '', clean)
    clean = re.sub(r'\s+', '_', clean.strip())
    return f'DLC_{num:03d}_{clean}.pdf'

import sys

with open(INDEX_PATH, encoding='utf-8') as f:
    index = json.load(f)

SAMPLE_N = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = full run

print("Extracting word coordinates from PDF pages (one pass)...")
page_lines = {}
with pdfplumber.open(PDF_PATH) as pdf:
    total = len(pdf.pages)
    for p_idx, page in enumerate(pdf.pages):
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.2)
        page_lines[p_idx] = group_lines(words)
        if p_idx % 50 == 0:
            print(f"  page {p_idx+1}/{total}", flush=True)

work = index[:SAMPLE_N] if SAMPLE_N else index
results = []
for s in work:
    num, title = s['num'], s['title']
    chopro = extract_song(page_lines, s['start_page'], s['end_page'])
    results.append({
        'id': f'dlc-{num:03d}',
        'num': num,
        'title': title,
        'pdf_file': slug(title, num),
        'raw_text': chopro,
        'chopro': chopro,
    })

if SAMPLE_N:
    for r in results:
        print(f"\n===== #{r['num']} {r['title']} =====")
        print(r['chopro'][:1200])
else:
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'Extracted {len(results)} songs with coordinate-aligned ChordPro -> {OUT_PATH}')
