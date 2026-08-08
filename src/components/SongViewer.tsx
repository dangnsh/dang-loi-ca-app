'use client';

import React from 'react';
import { parseChordProLine, transposeChord } from '@/lib/chordEngine';

interface SongViewerProps {
  content: string;
  semitones?: number;
  showChords?: boolean;
  displayMode?: 'stacked' | 'inline';
  fontSize?: number;
  useFlats?: boolean;
}

export const SongViewer: React.FC<SongViewerProps> = ({
  content,
  semitones = 0,
  showChords = true,
  displayMode = 'inline',
  fontSize = 18,
  useFlats = false,
}) => {
  if (!content) return <div className="text-slate-400 italic">Không có nội dung bài hát</div>;

  const rawLines = content.split('\n');

  return (
    <div 
      className="p-4 sm:p-6 bg-slate-900/90 rounded-2xl border border-slate-800 text-slate-100 font-sans leading-relaxed transition-all shadow-xl selection:bg-amber-500 selection:text-slate-900 overflow-x-hidden max-w-full break-words space-y-3"
      style={{ fontSize: `${fontSize}px` }}
    >
      {rawLines.map((line, lineIdx) => {
        const trimmed = line.trim();

        // Section Markers: [Verse 1], [Verse 2], [Chorus], [Bridge], [Outro]...
        if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
          const inner = trimmed.slice(1, -1);
          // Ensure it's a section marker, not a line starting and ending with chords e.g. [G]...[C]
          if (!inner.includes('[') && !inner.includes(']')) {
            const tag = inner;
            let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
            let displayName = tag;

            if (tag.toLowerCase().includes('verse 1') || tag.toLowerCase().includes('câu 1')) {
              badgeColor = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
              displayName = 'Verse 1 • Câu 1';
            } else if (tag.toLowerCase().includes('verse 2') || tag.toLowerCase().includes('câu 2')) {
              badgeColor = 'bg-teal-500/20 text-teal-400 border-teal-500/40';
              displayName = 'Verse 2 • Câu 2';
            } else if (tag.toLowerCase().includes('chorus') || tag.toLowerCase().includes('điệp khúc')) {
              badgeColor = 'bg-amber-500/20 text-amber-400 border-amber-500/40';
              displayName = 'Chorus • Điệp Khúc';
            } else if (tag.toLowerCase().includes('bridge')) {
              badgeColor = 'bg-purple-500/20 text-purple-400 border-purple-500/40';
              displayName = 'Bridge • Đoạn Nối';
            }

            return (
              <div key={lineIdx} className="pt-3 pb-1">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.75em] font-bold border tracking-wide uppercase ${badgeColor}`}>
                  {displayName}
                </span>
              </div>
            );
          }
        }

        // Directives like {title:...} or author/meta notes
        if (trimmed.startsWith('{') || trimmed.startsWith('//')) {
          return (
            <div key={lineIdx} className="text-emerald-400/90 italic font-medium my-1.5 opacity-90 text-[0.85em] flex items-center gap-1.5">
              <span>{trimmed.replace(/[\{\}]/g, '')}</span>
            </div>
          );
        }

        const tokens = parseChordProLine(line);

        return (
          <div key={lineIdx} className="min-h-[1.8em] my-1 flex flex-wrap items-end group hover:bg-slate-800/20 p-1 rounded transition">
            {tokens.map((token, tokenIdx) => {
              const transposed = token.chord 
                ? transposeChord(token.chord, semitones, useFlats)
                : undefined;

              if (displayMode === 'stacked') {
                return (
                  <span key={tokenIdx} className="inline-flex flex-col items-start mr-1.5 group">
                    {showChords && (
                      <span className="text-amber-400 font-bold text-[0.85em] leading-none mb-1 h-[1.1em] select-none tracking-wide">
                        {transposed || '\u00A0'}
                      </span>
                    )}
                    <span className="whitespace-pre-wrap break-words">{token.text || '\u00A0'}</span>
                  </span>
                );
              }

              return (
                <span key={tokenIdx} className="whitespace-pre-wrap break-words">
                  {showChords && transposed && (
                    <span className="text-amber-400 font-bold mx-0.5 select-none bg-amber-500/10 px-1 py-0.5 rounded inline-block">
                      [{transposed}]
                    </span>
                  )}
                  {token.text}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
