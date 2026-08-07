'use client';

import React, { useEffect, useRef } from 'react';
import abcjs from 'abcjs';

interface AbcSheetViewerProps {
  abcNotation: string;
  visualTranspose?: number; // semitones (-6 to +6)
  scale?: number;
}

export const AbcSheetViewer: React.FC<AbcSheetViewerProps> = ({
  abcNotation,
  visualTranspose = 0,
  scale = 1.0,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !abcNotation) return;

    containerRef.current.innerHTML = '';
    try {
      abcjs.renderAbc(containerRef.current, abcNotation, {
        responsive: 'resize',
        scale: scale,
        visualTranspose: visualTranspose,
        paddingtop: 10,
        paddingbottom: 10,
        paddingleft: 10,
        paddingright: 10,
        add_classes: true,
      });
    } catch (err) {
      console.error('Failed to render ABC notation:', err);
    }
  }, [abcNotation, visualTranspose, scale]);

  return (
    <div className="w-full bg-white text-slate-900 p-4 rounded-xl shadow-inner border border-slate-300 overflow-x-auto">
      <div ref={containerRef} className="w-full min-w-[320px]" />
    </div>
  );
};
