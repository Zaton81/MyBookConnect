import { useEffect, useRef, useState, useCallback } from 'react';
import {
  HiPlay,
  HiPause,
  HiX,
  HiVolumeUp,
  HiVolumeOff,
  HiChevronUp,
  HiChevronDown,
} from 'react-icons/hi';
import { useAudioPlayerStore } from '../../store/audioPlayer';
import { useAuthStore } from '../../store/auth';
import { resolveMediaUrl } from '../../utils/media';

export function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

const SPEED_OPTIONS = [0.75, 1.0, 1.25, 1.5, 2.0];

export function AudioPlayerBar() {
  const {
    currentBook,
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    playbackSpeed,
    volume,
    isMuted,
    isOpen,
    isTtsActive,
    ttsText,
    pauseTrack,
    togglePlay,
    seekTo,
    skipSeconds,
    setPlaybackSpeed,
    setVolume,
    toggleMute,
    setCurrentTime,
    setDuration,
    closePlayer,
  } = useAudioPlayerStore();

  const { token } = useAuthStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isSpeedMenuOpen, setIsSpeedMenuOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const lastSyncTimeRef = useRef<number>(0);

  // Sincronizar progreso con el backend
  const syncProgress = useCallback(
    async (time: number, isFinished = false) => {
      if (!token || !currentBook) return;
      try {
        await fetch(`${apiUrl}/api/v1/books/${currentBook.id}/audiobook/progress/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            track_id: currentTrack && currentTrack.id > 0 ? currentTrack.id : null,
            position_seconds: Math.round(time),
            playback_speed: playbackSpeed,
            is_completed: isFinished,
          }),
        });
      } catch (err) {
        // silencioso
      }
    },
    [apiUrl, token, currentBook, currentTrack, playbackSpeed]
  );

  // Gestión de audio real <audio>
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || isTtsActive) return;

    if (currentTrack?.stream_url && audio.src !== currentTrack.stream_url) {
      audio.src = currentTrack.stream_url;
      audio.currentTime = currentTime;
    }

    if (isPlaying) {
      const playPromise = audio.play();
      if (playPromise !== undefined && typeof playPromise?.catch === 'function') {
        playPromise.catch(() => {
          pauseTrack();
        });
      }
    } else {
      if (typeof audio.pause === 'function') {
        audio.pause();
      }
    }
  }, [currentTrack, isPlaying, isTtsActive, pauseTrack]);

  // Actualizar velocidad y volumen del elemento de audio
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = playbackSpeed;
    audio.volume = isMuted ? 0 : volume;
  }, [playbackSpeed, volume, isMuted]);

  // Gestión de TTS (Web Speech API)
  useEffect(() => {
    if (!isTtsActive || typeof window === 'undefined' || !window.speechSynthesis) return;

    if (!isPlaying) {
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
      }
      return;
    }

    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(ttsText);
    utterance.rate = playbackSpeed;
    utterance.lang = 'es-ES';

    // Intentar seleccionar una voz en español si está disponible
    const voices = window.speechSynthesis.getVoices();
    const esVoice = voices.find((v) => v.lang.startsWith('es'));
    if (esVoice) {
      utterance.voice = esVoice;
    }

    utterance.onboundary = (e) => {
      if (e.charIndex && ttsText.length > 0) {
        const estSeconds = Math.round((e.charIndex / ttsText.length) * duration);
        setCurrentTime(estSeconds);
      }
    };

    utterance.onend = () => {
      pauseTrack();
      syncProgress(duration, true);
    };

    utterance.onerror = () => {
      pauseTrack();
    };

    window.speechSynthesis.speak(utterance);

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isTtsActive, isPlaying, ttsText, playbackSpeed, duration, pauseTrack, setCurrentTime, syncProgress]);

  // Manejadores de eventos de la etiqueta <audio>
  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio || isTtsActive) return;
    const cur = audio.currentTime;
    setCurrentTime(cur);

    // Sincronizar periódicamente cada 15 segundos
    if (Math.abs(cur - lastSyncTimeRef.current) >= 15) {
      lastSyncTimeRef.current = cur;
      syncProgress(cur);
    }
  };

  const handleLoadedMetadata = () => {
    const audio = audioRef.current;
    if (!audio || isTtsActive) return;
    if (audio.duration && !isNaN(audio.duration)) {
      setDuration(audio.duration);
    }
  };

  const handleEnded = () => {
    pauseTrack();
    syncProgress(duration, true);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    seekTo(val);
    if (audioRef.current && !isTtsActive) {
      audioRef.current.currentTime = val;
    }
  };

  if (!isOpen || !currentBook) return null;

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-50 transition-all duration-300 ${
        isMinimized ? 'translate-y-[calc(100%-2.5rem)]' : 'translate-y-0'
      }`}
      role="region"
      aria-label="Reproductor de audiolibro"
    >
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
      />

      <div className="bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-md border-t border-teal-500/30 text-white shadow-2xl">
        {/* Cabecera / Pestaña para minimizar */}
        <div className="flex items-center justify-between px-4 py-1 bg-slate-800/80 border-b border-slate-700/50 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
            <span className="font-semibold text-slate-200">
              {isTtsActive ? 'Asistente de lectura por voz (TTS)' : 'Reproductor de audiolibro'}
            </span>
            {currentTrack?.narrator_name && (
              <span className="hidden sm:inline text-slate-400">
                · Voz: {currentTrack.narrator_name}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 hover:text-white transition-colors"
              title={isMinimized ? 'Expandir reproductor' : 'Minimizar reproductor'}
            >
              {isMinimized ? <HiChevronUp className="w-4 h-4" /> : <HiChevronDown className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={() => {
                syncProgress(currentTime);
                closePlayer();
              }}
              className="p-1 hover:text-rose-400 transition-colors"
              title="Cerrar reproductor"
            >
              <HiX className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Barra de Controles Principales */}
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row items-center gap-3 md:gap-6">
          {/* Info del Libro y Pista */}
          <div className="flex items-center gap-3 w-full md:w-1/4 min-w-0">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl overflow-hidden bg-slate-800 shrink-0 border border-slate-700 shadow-sm">
              {currentBook.cover_url ? (
                <img
                  src={resolveMediaUrl(currentBook.cover_url)}
                  alt={currentBook.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-base">🎧</div>
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="font-bold text-xs sm:text-sm text-white truncate" title={currentBook.title}>
                {currentBook.title}
              </h4>
              <p className="text-[11px] text-teal-400 truncate">
                {currentTrack?.title || (isTtsActive ? 'Lectura por voz' : 'Pista')}
              </p>
            </div>
          </div>

          {/* Controles de Reproducción y Slider */}
          <div className="flex-1 w-full flex flex-col items-center gap-1.5">
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => skipSeconds(-15)}
                className="text-slate-300 hover:text-teal-400 font-bold text-xs p-1.5 transition-colors"
                title="Retroceder 15 segundos"
                aria-label="Retroceder 15 segundos"
              >
                -15s
              </button>

              <button
                type="button"
                onClick={togglePlay}
                className="w-10 h-10 rounded-full bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-slate-950 flex items-center justify-center font-bold shadow-lg shadow-teal-500/30 transition-transform active:scale-95"
                title={isPlaying ? 'Pausar' : 'Reproducir'}
                aria-label={isPlaying ? 'Pausar reproducción' : 'Iniciar reproducción'}
              >
                {isPlaying ? <HiPause className="w-5 h-5" /> : <HiPlay className="w-5 h-5 ml-0.5" />}
              </button>

              <button
                type="button"
                onClick={() => skipSeconds(15)}
                className="text-slate-300 hover:text-teal-400 font-bold text-xs p-1.5 transition-colors"
                title="Avanzar 15 segundos"
                aria-label="Avanzar 15 segundos"
              >
                +15s
              </button>
            </div>

            {/* Slider de Progreso y Tiempo */}
            <div className="w-full flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span className="w-10 text-right">{formatTime(currentTime)}</span>
              <input
                type="range"
                min={0}
                max={duration || 100}
                step={1}
                value={currentTime}
                onChange={handleSliderChange}
                className="flex-1 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-teal-400"
                aria-label="Progreso del audiolibro"
              />
              <span className="w-10">{formatTime(duration)}</span>
            </div>
          </div>

          {/* Velocidad y Volumen */}
          <div className="flex items-center justify-end gap-3 w-full md:w-1/4">
            {/* Selector de Velocidad */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsSpeedMenuOpen(!isSpeedMenuOpen)}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-teal-300 border border-slate-700 transition-colors"
                title="Velocidad de reproducción"
                aria-label={`Velocidad actual: ${playbackSpeed}x`}
              >
                {playbackSpeed}x
              </button>

              {isSpeedMenuOpen && (
                <div className="absolute bottom-full mb-2 right-0 bg-slate-800 border border-slate-700 rounded-xl p-1 shadow-xl flex flex-col gap-0.5 z-50">
                  {SPEED_OPTIONS.map((spd) => (
                    <button
                      key={spd}
                      type="button"
                      onClick={() => {
                        setPlaybackSpeed(spd);
                        setIsSpeedMenuOpen(false);
                      }}
                      className={`px-3 py-1 text-xs rounded-lg font-bold text-left transition-colors ${
                        playbackSpeed === spd
                          ? 'bg-teal-500 text-slate-950'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      {spd}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Volumen */}
            <div className="hidden sm:flex items-center gap-1.5 text-slate-400">
              <button
                type="button"
                onClick={toggleMute}
                className="hover:text-white transition-colors"
                title={isMuted ? 'Activar sonido' : 'Silenciar'}
                aria-label={isMuted ? 'Activar sonido' : 'Silenciar'}
              >
                {isMuted || volume === 0 ? (
                  <HiVolumeOff className="w-4 h-4 text-rose-400" />
                ) : (
                  <HiVolumeUp className="w-4 h-4" />
                )}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="w-16 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-teal-400"
                aria-label="Volumen"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AudioPlayerBar;
