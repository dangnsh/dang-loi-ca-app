import pdfplumber
import json
import re
import unicodedata

PDF_PATH = '/home/dangnsh/.hermes/cache/documents/doc_cf7520ff30a6_Dang-Loi-Ca.pdf'
INDEX_PATH = '/home/dangnsh/Dang_Loi_Ca_Split_PDFs/songs_index.json'
OUT_PATH = '/home/dangnsh/projects/dang-loi-ca-app/src/data/songs.json'

CHORD_RE = re.compile(r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*(\([b#]?5\))?(/[A-G][#b]?)?$')
JUNK_RE = re.compile(r'^[b&\s\d™œÓ˙w‰jJ%„ŠŒ„#=,;\.\'\-\|\[\]\(\)<>]*$')

def decode_chord(token):
    t = token.replace('“4', 'sus4').replace('“', 'sus')
    t = t.replace('‹', 'm').replace('„Š7', 'maj7').replace('„Š', 'maj')
    t = t.replace('&', '+').replace('Œ', '').replace('„', '')
    t = re.sub(r'[^\w/#+\(\)b]', '', t)
    return t

def is_chord_word(w):
    if len(w) > 14: return False
    d = decode_chord(w)
    return bool(CHORD_RE.match(d)) if d else False

def has_vietnamese(text):
    return bool(re.search(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]', text, re.I))

def clean_lyric(text):
    t = text.replace('', '').replace('', '')
    t = re.sub(r'[™œÓ˙w‰j„ŠŒ]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    upper = 'A-ZĂÂĐÊÔƠƯÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ'
    t = re.sub(r'([a-zăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ])([' + upper + '])', r'\1 \2', t)
    return t

def join_words(words):
    parts = []
    prev_x1 = None
    for w in words:
        t = w['text']
        if JUNK_RE.match(t): continue
        if prev_x1 is not None and (w['x0'] - prev_x1) > 0.8:
            parts.append(' ')
        parts.append(t)
        prev_x1 = w['x1']
    return ''.join(parts)

def parse_song_pages(pdf, start_p, end_p):
    """Accurately group lines by strict Y coordinate (y_tolerance=1.5) to keep parallel verses separated."""
    all_lines = []
    
    for p_idx in range(start_p - 1, end_p):
        page = pdf.pages[p_idx]
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.2)
        
        # Strict grouping by Y coordinate (1.5pt threshold)
        y_groups = {}
        for w in words:
            top = round(w['top'] / 1.5) * 1.5
            y_groups.setdefault(top, []).append(w)
            
        for top in sorted(y_groups.keys()):
            lw = sorted(y_groups[top], key=lambda x: x['x0'])
            txt = join_words(lw)
            clean_t = clean_lyric(txt)
            if not clean_t or all(JUNK_RE.match(t) for t in txt.split()):
                continue
            if re.match(r'^\d+fr$', clean_t) or clean_t in ('J', '˙', 'w'):
                continue
                
            # Classify
            if clean_t.startswith(('Nguyên tác', 'LỜI VIỆT', 'LỜi Việt', 'LỜi Việt:', 'Thi Thiên', 'Chưa rõ tác giả', 'LỜi:')) or 'NGUYÊN TÁC' in clean_t.upper():
                all_lines.append(('meta', clean_t, lw))
            elif clean_t == clean_t.upper() and has_vietnamese(clean_t) and len(clean_t) > 4:
                all_lines.append(('title', clean_t, lw))
            elif not has_vietnamese(clean_t) and len([w for w in lw if is_chord_word(w['text'])]) >= 1:
                all_lines.append(('chord', [w for w in lw if is_chord_word(w['text'])], lw))
            elif has_vietnamese(clean_t):
                all_lines.append(('lyric', clean_t, lw))

    # Reconstruct into structured ChordPro
    output_lines = []
    pending_chords = None
    v1_parts = []
    v2_parts = []
    current_section = None

    for item in all_lines:
        kind = item[0]
        if kind == 'meta':
            output_lines.append(f"{{{item[1]}}}")
        elif kind == 'chord':
            pending_chords = item[1]
        elif kind == 'lyric':
            lyric_str = item[1]
            words = item[2]
            
            # Formatting chord inline
            formatted = lyric_str
            if pending_chords:
                inserts = []
                for cw in pending_chords:
                    inserts.append((cw['x0'], decode_chord(cw['text'])))
                for x, ch in sorted(inserts, key=lambda t: t[0], reverse=True):
                    formatted = f"[{ch}]" + formatted
                pending_chords = None

            # Detect verse start
            if lyric_str.startswith(('1.', '1 ')):
                if current_section != 'Verse 1':
                    output_lines.append('\n[Verse 1]')
                    current_section = 'Verse 1'
                formatted = re.sub(r'^1\.?\s*', '', formatted)
            elif lyric_str.startswith(('2.', '2 ')):
                if current_section != 'Verse 2':
                    output_lines.append('\n[Verse 2]')
                    current_section = 'Verse 2'
                formatted = re.sub(r'^2\.?\s*', '', formatted)
            elif 'điệp khúc' in lyric_str.lower() or lyric_str.startswith(('ĐK', 'ĐK:')):
                if current_section != 'Chorus':
                    output_lines.append('\n[Chorus]')
                    current_section = 'Chorus'
                formatted = re.sub(r'^(ĐK:?|Điệp khúc)\s*', '', formatted, flags=re.I)

            output_lines.append(formatted)

    return '\n'.join(output_lines)

with open(INDEX_PATH, encoding='utf-8') as f: index = json.load(f)

results = []
with pdfplumber.open(PDF_PATH) as pdf:
    for s in index:
        num, title = s['num'], s['title']
        chopro = parse_song_pages(pdf, s['start_page'], s['end_page'])
        clean_title = re.sub(r'[^\w]', '_', title)
        results.append({
            'id': f'dlc-{num:03d}',
            'num': num,
            'title': title,
            'pdf_file': f"DLC_{num:03d}_{clean_title}.pdf",
            'raw_text': chopro,
            'chopro': chopro,
        })

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('=== STRICT Y-GROUPING SAMPLE SONG #1 ===')
print(results[0]['chopro'])
