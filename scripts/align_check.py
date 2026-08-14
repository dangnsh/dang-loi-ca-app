#!/usr/bin/env python3
"""Inspect the PDF text layer for a DLC song, showing chord symbols, noteheads,
rests and lyric words WITH their x/y coordinates, per staff — for manual/agent
ground-truth chord alignment."""
import pdfplumber, sys, re

# Glyph sets
NOTE = re.compile(r'^[œ˙™Ó‰]+$')   # noteheads/dots/rests
JUNK = re.compile(r'^[b&wjJ‰œÓ˙™\d\s\.,;:\'"\-|\[\]()<>%$@#=]+$')

def decode_chord(token):
    t = token.replace('“4', 'sus4').replace('“', 'sus')
    t = t.replace('‹', 'm').replace('„Š7', 'maj7').replace('„Š', 'maj')
    t = t.replace('&', '+').replace('Œ', '').replace('„', '')
    return re.sub(r'[^\w/#+\(\)b]', '', t)

CHORD_RE = re.compile(
    r'^[A-G][#b]?(m|maj7|maj|sus4|sus|dim|aug|\+|add9|6|7|9|11|13|m7|m6|m9|7sus4|7b5|m7b5|\(b5\)|2|5)*'
    r'(\([b#]?5\))?(/[A-G][#b]?)?$'
)
def is_chord(w):
    d = decode_chord(w)
    return bool(d) and bool(CHORD_RE.match(d))

def main(pdf):
    with pdfplumber.open(pdf) as p:
        for pi, page in enumerate(p.pages, 1):
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False, x_tolerance=1.0)
            # cluster lines by y-band
            lines = {}
            for w in words:
                y = round(w['top'])
                lines.setdefault(y, []).append(w)
            print(f"\n================ PAGE {pi} ================")
            for y in sorted(lines):
                ws = sorted(lines[y], key=lambda w: w['x0'])
                # classify
                ch = [w for w in ws if is_chord(w['text'])]
                nts = [w for w in ws if NOTE.match(w['text'])]
                ly = [w for w in ws if not is_chord(w['text']) and not NOTE.match(w['text'])]
                ly_txt = ' '.join(w['text'] for w in ly)
                if not ly_txt and not ch and not nts:
                    continue
                def fmt(ws_, maxn=28):
                    return '\n      '.join(f"{w['text']!r} x0={w['x0']:.1f} c={w['text'][0] if False else ''}{w['x0']+(0 if len(w['text'])<=1 else (2.2*len(w['text']))):.1f}" for w in ws_[:maxn])
                print(f"--- y={y:.0f} ---")
                if ch:  print(f"  CHORDS:\n      {fmt(ch)}")
                if nts: print(f"  NOTES :\n      {fmt(nts)}")
                print(f"  LYRIC(center): {ly_txt!r}")
                print(f"      {fmt(ly)}")

if __name__ == '__main__':
    main(sys.argv[1])
