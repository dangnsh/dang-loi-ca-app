'use client';

import React, { useState, useMemo, useEffect, useRef } from 'react';
import songsData from '@/data/songs.json';
import { SongViewer } from '@/components/SongViewer';
import { Song } from '@/lib/chordEngine';
import { 
  Search, 
  Music, 
  Play, 
  Pause, 
  Plus, 
  Minus, 
  Layers, 
  ListMusic, 
  FileText, 
  Bookmark, 
  Sparkles,
  Download,
  ExternalLink,
  Eye
} from 'lucide-react';

export default function Home() {
  const songs = songsData as Song[];
  
  const [selectedSong, setSelectedSong] = useState<Song>(songs[0]);
  const [searchQuery, setSearchQuery] = useState('');
  const [semitones, setSemitones] = useState(0);
  const [showChords, setShowChords] = useState(true);
  const [displayMode, setDisplayMode] = useState<'stacked' | 'inline'>('inline');
  const [fontSize, setFontSize] = useState(18);
  const [activeTab, setActiveTab] = useState<'chords' | 'sheet' | 'setlist'>('chords');
  
  // Auto scroll state
  const [isAutoScrolling, setIsAutoScrolling] = useState(false);
  const [scrollSpeed, setScrollSpeed] = useState(2);
  const scrollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Setlist state
  const [setlist, setSetlist] = useState<Song[]>([]);

  // Filter songs
  const filteredSongs = useMemo(() => {
    if (!searchQuery.trim()) return songs;
    const q = searchQuery.toLowerCase().trim();
    return songs.filter(
      s => s.title.toLowerCase().includes(q) || 
           s.num.toString().includes(q) || 
           s.raw_text.toLowerCase().includes(q)
    );
  }, [searchQuery, songs]);

  // Handle auto-scroll
  useEffect(() => {
    if (isAutoScrolling) {
      scrollIntervalRef.current = setInterval(() => {
        window.scrollBy({ top: scrollSpeed, behavior: 'smooth' });
      }, 50);
    } else {
      if (scrollIntervalRef.current) clearInterval(scrollIntervalRef.current);
    }
    return () => {
      if (scrollIntervalRef.current) clearInterval(scrollIntervalRef.current);
    };
  }, [isAutoScrolling, scrollSpeed]);

  const toggleSetlist = (song: Song) => {
    if (setlist.some(s => s.id === song.id)) {
      setSetlist(setlist.filter(s => s.id !== song.id));
    } else {
      setSetlist([...setlist, song]);
    }
  };

  const pdfUrl = selectedSong.pdf_file ? `/sheets/${selectedSong.pdf_file}` : null;
  // Google Docs PDF Viewer embed URL for 100% reliable mobile viewing without iOS Safari / Zalo blocks
  const googlePdfViewerUrl = pdfUrl 
    ? `https://docs.google.com/viewer?url=${encodeURIComponent(`https://dang-loi-ca-app--worship-translator.asia-southeast1.hosted.app${pdfUrl}`)}&embedded=true` 
    : null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-amber-500 selection:text-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-tr from-amber-500 to-amber-300 p-2 rounded-xl text-slate-950 font-bold shadow-lg shadow-amber-500/20">
              <Music className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-extrabold text-lg sm:text-xl tracking-tight bg-gradient-to-r from-amber-400 via-amber-200 to-slate-100 bg-clip-text text-transparent">
                Dâng Lời Ca
              </h1>
              <p className="text-xs text-slate-400 hidden sm:block">
                Kho 300 Bài Thánh Ca & Biệt Thánh Ca Hợp Âm
              </p>
            </div>
          </div>

          {/* Global Actions */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setActiveTab('setlist')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'setlist' 
                  ? 'bg-amber-500 text-slate-950 font-bold' 
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <ListMusic className="w-4 h-4" />
              <span>Setlist ({setlist.length})</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Sidebar: Song List & Search */}
        <div className="lg:col-span-4 flex flex-col gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800/80">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3.5 text-slate-400" />
            <input 
              type="text"
              placeholder="Tìm theo tên, số bài (1-300) hoặc lời..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
            />
          </div>

          {/* List stats */}
          <div className="flex justify-between items-center px-1 text-xs text-slate-400">
            <span>Hiển thị {filteredSongs.length} / 300 bài</span>
            <span className="text-amber-400/80">300 Dâng Lời Ca</span>
          </div>

          {/* Scrollable Song Items */}
          <div className="overflow-y-auto space-y-1.5 pr-1 max-h-[350px] lg:max-h-[calc(100vh-16rem)] custom-scrollbar">
            {filteredSongs.map(s => {
              const isSelected = selectedSong.id === s.id;
              const inSetlist = setlist.some(item => item.id === s.id);

              return (
                <div 
                  key={s.id}
                  onClick={() => {
                    setSelectedSong(s);
                    setSemitones(0);
                    if (activeTab === 'setlist') setActiveTab('chords');
                  }}
                  className={`p-3 rounded-xl cursor-pointer border transition flex items-center justify-between group ${
                    isSelected 
                      ? 'bg-amber-500/15 border-amber-500/50 text-amber-300' 
                      : 'bg-slate-950/40 border-slate-800/50 hover:bg-slate-800/60 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                      isSelected ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400'
                    }`}>
                      #{s.num}
                    </span>
                    <span className="font-medium text-sm truncate">{s.title}</span>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSetlist(s);
                    }}
                    className={`p-1.5 rounded-lg transition ${
                      inSetlist 
                        ? 'text-amber-400 bg-amber-500/20' 
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                    }`}
                    title={inSetlist ? "Bỏ khỏi Setlist" : "Thêm vào Setlist"}
                  >
                    <Bookmark className="w-4 h-4 fill-current" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Main View Area */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          
          {/* Active Song Control Bar */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 sticky top-20 z-20 backdrop-blur shadow-lg flex flex-wrap items-center justify-between gap-4">
            {/* Song Info */}
            <div>
              <div className="flex items-center gap-2">
                <span className="bg-amber-500/20 text-amber-400 font-mono text-xs px-2 py-0.5 rounded font-bold">
                  DLC #{selectedSong.num}
                </span>
                <h2 className="text-lg sm:text-xl font-bold text-slate-100">
                  {selectedSong.title}
                </h2>
              </div>
            </div>

            {/* Mode Switcher Tabs */}
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setActiveTab('chords')}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === 'chords' ? 'bg-amber-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Hợp Âm</span>
              </button>
              <button
                onClick={() => setActiveTab('sheet')}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  activeTab === 'sheet' ? 'bg-amber-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Sheet PDF</span>
              </button>
            </div>
          </div>

          {/* Interactive Toolbar for Chords */}
          {activeTab === 'chords' && (
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
              
              {/* Transpose Control */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button 
                  onClick={() => setSemitones(s => s - 1)}
                  className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition"
                  title="Giảm 1 bán cung"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="px-2 font-mono font-bold text-amber-400">
                  Tông: {semitones > 0 ? `+${semitones}` : semitones}
                </span>
                <button 
                  onClick={() => setSemitones(s => s + 1)}
                  className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition"
                  title="Tăng 1 bán cung"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Display Mode (Stacked / Inline) */}
              <button
                onClick={() => setDisplayMode(m => m === 'stacked' ? 'inline' : 'stacked')}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-300 transition"
              >
                <Layers className="w-3.5 h-3.5 text-amber-400" />
                <span>{displayMode === 'stacked' ? 'Trên đầu chữ' : 'Nội tuyến (Inline)'}</span>
              </button>

              {/* Font Size */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button 
                  onClick={() => setFontSize(f => Math.max(12, f - 2))}
                  className="px-2 py-1 hover:bg-slate-800 rounded text-slate-300 font-bold"
                >
                  A-
                </button>

                <span className="px-1 text-slate-400 font-mono">{fontSize}px</span>
                <button 
                  onClick={() => setFontSize(f => Math.min(32, f + 2))}
                  className="px-2 py-1 hover:bg-slate-800 rounded text-slate-300 font-bold"
                >
                  A+
                </button>
              </div>

              {/* Toggle Chords */}
              <button
                onClick={() => setShowChords(!showChords)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition ${
                  showChords 
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 font-semibold' 
                    : 'bg-slate-950 border-slate-800 text-slate-500'
                }`}
              >
                <Music className="w-3.5 h-3.5" />
                <span>Hợp âm</span>
              </button>

              {/* Auto Scroll Controls */}
              <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setIsAutoScrolling(!isAutoScrolling)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded transition text-xs font-semibold ${
                    isAutoScrolling ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {isAutoScrolling ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  <span>Cuộn</span>
                </button>
                {isAutoScrolling && (
                  <input 
                    type="range"
                    min="1"
                    max="5"
                    value={scrollSpeed}
                    onChange={e => setScrollSpeed(Number(e.target.value))}
                    className="w-16 accent-amber-500 cursor-pointer"
                  />
                )}
              </div>

            </div>
          )}

          {/* Main Viewer Render */}
          {activeTab === 'chords' && (
            <SongViewer 
              content={selectedSong.chopro || selectedSong.raw_text}
              semitones={semitones}
              showChords={showChords}
              displayMode={displayMode}
              fontSize={fontSize}
            />
          )}

          {activeTab === 'sheet' && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-amber-400" />
                  <span className="font-semibold text-slate-200">Sheet nhạc DLC #{selectedSong.num}</span>
                  <span className="text-slate-400 font-mono">({selectedSong.pdf_file})</span>
                </div>

                {pdfUrl && (
                  <div className="flex items-center gap-2">
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 bg-amber-500 text-slate-950 font-bold rounded-lg hover:bg-amber-400 transition flex items-center gap-1"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Xem trực tiếp PDF</span>
                    </a>
                    <a
                      href={pdfUrl}
                      download={selectedSong.pdf_file}
                      className="px-3 py-1.5 bg-slate-800 text-slate-200 font-medium rounded-lg hover:bg-slate-700 transition flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Tải file</span>
                    </a>
                  </div>
                )}
              </div>

              {pdfUrl ? (
                <div className="w-full h-[650px] sm:h-[750px] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-inner flex flex-col">
                  {/* Google Docs Embedded Viewer for seamless rendering on iOS/Zalo mobile */}
                  <iframe 
                    src={googlePdfViewerUrl || pdfUrl}
                    className="w-full h-full border-0"
                    title={`Sheet PDF ${selectedSong.title}`}
                  />
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500">Chưa có file PDF sheet nhạc cho bài này</div>
              )}
            </div>
          )}

          {activeTab === 'setlist' && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-100">Danh Sách Buổi Nhóm (Setlist)</h3>
                  <p className="text-xs text-slate-400">Các bài hát đã chọn cho buổi thờ phượng</p>
                </div>
                {setlist.length > 0 && (
                  <button 
                    onClick={() => setSetlist([])}
                    className="text-xs text-rose-400 hover:underline"
                  >
                    Xóa tất cả
                  </button>
                )}
              </div>

              {setlist.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-sm">
                  Chưa có bài hát nào trong Setlist. Bấm biểu tượng 🔖 ở danh sách bên trái để thêm bài!
                </div>
              ) : (
                <div className="space-y-2">
                  {setlist.map((s, idx) => (
                    <div 
                      key={s.id}
                      onClick={() => {
                        setSelectedSong(s);
                        setActiveTab('chords');
                      }}
                      className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between cursor-pointer hover:border-amber-500/50 transition"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <div>
                          <div className="font-semibold text-sm text-slate-200">{s.title}</div>
                          <div className="text-xs text-slate-500 font-mono">DLC #{s.num}</div>
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSetlist(s);
                        }}
                        className="text-slate-500 hover:text-rose-400 p-1"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
