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

  const lines = content.split('\n');

  return (
    <div 
      className="p-4 sm:p-6 bg-slate-900/90 rounded-2xl border border-slate-800 text-slate-100 font-sans leading-relaxed transition-all shadow-xl selection:bg-amber-500 selection:text-slate-900 overflow-x-hidden max-w-full break-words"
      style={{ fontSize: `${fontSize}px` }}
    >
      {lines.map((line, lineIdx) => {
        // Directives like {title:...} or comments
        if (line.trim().startsWith('{') || line.trim().startsWith('//')) {
          return (
            <div key={lineIdx} className="text-emerald-400 italic font-medium my-2 opacity-85 text-[0.9em]">
              {line.replace(/[\{\}]/g, '')}
            </div>
          );
        }

        const tokens = parseChordProLine(line);

        return (
          <div key={lineIdx} className="min-h-[1.8em] my-1 flex flex-wrap items-end">
            {tokens.map((token, tokenIdx) => {
              const transposed = token.chord 
                ? transposeChord(token.chord, semitones, useFlats)
                : undefined;

              if (displayMode === 'stacked') {
                return (
                  <span key={tokenIdx} className="inline-flex flex-col items-start mr-1 group">
                    {showChords && (
                      <span className="text-amber-400 font-bold text-[0.85em] leading-none mb-1 h-[1.1em] select-none tracking-wide">
                        {transposed || '\u00A0'}
                      </span>
                    )}
                    <span className="whitespace-pre">{token.text || '\u00A0'}</span>
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
