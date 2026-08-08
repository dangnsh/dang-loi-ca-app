export interface Song {
  id: string;
  num: number;
  title: string;
  composer?: string;
  lyricist?: string;
  raw_text?: string;
  content?: string;
  sheetUrl?: string;
  pdf_file?: string;
  start_page?: number;
  end_page?: number;
  chopro?: string;
  key?: string;
  category?: string;
}

const SHARP_SCALE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const FLAT_SCALE  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'];

const NOTE_TO_INDEX: Record<string, number> = {
  'C': 0, 'C#': 1, 'Db': 1,
  'D': 2, 'D#': 3, 'Eb': 3,
  'E': 4, 'E#': 5, 'Fb': 4,
  'F': 5, 'F#': 6, 'Gb': 6,
  'G': 7, 'G#': 8, 'Ab': 8,
  'A': 9, 'A#': 10, 'Bb': 10,
  'B': 11, 'B#': 0, 'Cb': 11
};

export function transposeNote(note: string, semitones: number, useFlats = false): string {
  const cleanNote = note.charAt(0).toUpperCase() + note.slice(1);
  const baseIndex = NOTE_TO_INDEX[cleanNote];
  if (baseIndex === undefined) return note;

  let newIndex = (baseIndex + semitones) % 12;
  if (newIndex < 0) newIndex += 12;

  const scale = useFlats ? FLAT_SCALE : SHARP_SCALE;
  return scale[newIndex];
}

export function transposeChord(chord: string, semitones: number, useFlats = false): string {
  if (semitones === 0) return chord;

  if (chord.includes('/')) {
    const [mainChord, bassNote] = chord.split('/');
    const newMain = transposeChord(mainChord, semitones, useFlats);
    const newBass = transposeNote(bassNote, semitones, useFlats);
    return `${newMain}/${newBass}`;
  }

  const match = chord.match(/^([A-G][#b]?)(.*)$/);
  if (!match) return chord;

  const [, rootNote, suffix] = match;
  const newRoot = transposeNote(rootNote, semitones, useFlats);
  return `${newRoot}${suffix}`;
}

export interface ChordToken {
  chord?: string;
  text: string;
}

export function parseChordProLine(line: string): ChordToken[] {
  const tokens: ChordToken[] = [];
  const regex = /\[(.*?)\]([^\[]*)/g;
  let match;

  const firstBracket = line.indexOf('[');
  if (firstBracket > 0) {
    tokens.push({ text: line.substring(0, firstBracket) });
  } else if (firstBracket === -1) {
    return [{ text: line }];
  }

  while ((match = regex.exec(line)) !== null) {
    tokens.push({
      chord: match[1].trim(),
      text: match[2]
    });
  }

  return tokens;
}
