import { useState, useEffect, useCallback } from 'react';
import { Button, Spinner } from 'flowbite-react';
import {
  HiPlay,
  HiOutlineVolumeUp,
  HiOutlineClock,
  HiOutlineMicrophone,
  HiOutlineSparkles,
} from 'react-icons/hi';
import { useAudioPlayerStore } from '../../../store/audioPlayer';
import { useAuthStore } from '../../../store/auth';

interface TrackData {
  id: number;
  title: string;
  track_number: number;
  duration_seconds: number;
  formatted_duration: string;
  stream_url: string;
  narrator_name?: string;
  is_sample: boolean;
}

interface AudiobookDetailResponse {
  book_id: number;
  book_title: string;
  author_name: string;
  cover_url: string | null;
  has_audiobook: boolean;
  tracks_count: number;
  total_duration_seconds: number;
  formatted_total_duration: string;
  narrators: string[];
  sample_track: TrackData | null;
  tracks: TrackData[];
  progress: {
    current_track_id: number | null;
    position_seconds: number;
    formatted_position: string;
    playback_speed: number;
    completion_percentage: number;
    is_completed: boolean;
  } | null;
  tts: {
    is_available: boolean;
    word_count: number;
    estimated_duration_seconds: number;
    formatted_estimated_duration: string;
    text_content: string;
  };
}

interface Props {
  bookId: number;
  bookTitle: string;
  authorName?: string;
  coverUrl?: string | null;
  description?: string;
}

export function BookAudiobookSection({
  bookId,
  bookTitle,
  authorName,
  coverUrl,
  description,
}: Props) {
  const { token } = useAuthStore();
  const { playTrack, playTts, currentTrack, isPlaying } = useAudioPlayerStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AudiobookDetailResponse | null>(null);

  const fetchAudiobookData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/api/v1/books/${bookId}/audiobook/`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      // silencioso
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, bookId]);

  useEffect(() => {
    fetchAudiobookData();
  }, [fetchAudiobookData]);

  if (loading) {
    return (
      <div className="p-6 rounded-3xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 flex justify-center items-center">
        <Spinner size="md" color="info" />
      </div>
    );
  }

  const bookItem = {
    id: bookId,
    title: bookTitle,
    author_name: authorName,
    cover_url: coverUrl,
  };

  // CASO 1: El libro cuenta con pistas oficiales de audiolibro
  if (data?.has_audiobook && data.tracks.length > 0) {
    const activeTrackId = currentTrack?.id;
    const progress = data.progress;

    return (
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 text-white shadow-xl border border-teal-500/20 space-y-6">
        {/* Cabecera del Audiolibro */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-700/60">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-black uppercase tracking-wider border border-teal-500/30">
                🎧 Audiolibro Disponible
              </span>
              <span className="text-xs text-slate-400 font-medium">
                {data.tracks_count} {data.tracks_count === 1 ? 'capítulo' : 'capítulos'}
              </span>
            </div>
            <h3 className="text-xl sm:text-2xl font-black text-white mt-2">
              Edición Narrada en Audio
            </h3>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 mt-1">
              <span className="flex items-center gap-1.5">
                <HiOutlineClock className="w-4 h-4 text-teal-400" />
                {data.formatted_total_duration} total
              </span>
              {data.narrators.length > 0 && (
                <span className="flex items-center gap-1.5">
                  <HiOutlineMicrophone className="w-4 h-4 text-teal-400" />
                  Narración: {data.narrators.join(', ')}
                </span>
              )}
            </div>
          </div>

          {/* Botones Principales de Acción */}
          <div className="flex items-center gap-3 shrink-0">
            {progress && progress.position_seconds > 0 ? (
              <Button
                color="teal"
                size="sm"
                onClick={() => {
                  const targetTrack =
                    data.tracks.find((t) => t.id === progress.current_track_id) || data.tracks[0];
                  playTrack(
                    bookItem,
                    targetTrack,
                    progress.position_seconds,
                    progress.playback_speed || 1.0
                  );
                }}
                className="font-bold shadow-md shadow-teal-500/20"
              >
                <HiPlay className="w-4 h-4 mr-1.5" />
                Continuar ({progress.formatted_position})
              </Button>
            ) : data.sample_track ? (
              <Button
                color="teal"
                size="sm"
                onClick={() => playTrack(bookItem, data.sample_track!)}
                className="font-bold shadow-md shadow-teal-500/20"
              >
                <HiPlay className="w-4 h-4 mr-1.5" />
                Escuchar muestra gratuita
              </Button>
            ) : null}
          </div>
        </div>

        {/* Lista de Pistas / Capítulos */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Capítulos y Pistas
          </h4>
          <div className="divide-y divide-slate-800 rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden">
            {data.tracks.map((track) => {
              const isThisPlaying = activeTrackId === track.id && isPlaying;
              return (
                <div
                  key={track.id}
                  className={`flex items-center justify-between p-3.5 sm:px-4 hover:bg-slate-800/60 transition-colors ${
                    activeTrackId === track.id ? 'bg-teal-950/40' : ''
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <button
                      type="button"
                      onClick={() => playTrack(bookItem, track)}
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-95 ${
                        isThisPlaying
                          ? 'bg-teal-400 text-slate-950 animate-pulse'
                          : 'bg-slate-800 text-teal-300 hover:bg-teal-500 hover:text-slate-950'
                      }`}
                      title={`Reproducir ${track.title}`}
                      aria-label={`Reproducir ${track.title}`}
                    >
                      <HiPlay className="w-4 h-4 ml-0.5" />
                    </button>
                    <div className="min-w-0">
                      <div className="font-bold text-xs sm:text-sm text-white truncate flex items-center gap-2">
                        <span>{track.title}</span>
                        {track.is_sample && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            Muestra
                          </span>
                        )}
                      </div>
                      {track.narrator_name && (
                        <p className="text-[11px] text-slate-400 truncate">
                          Voz: {track.narrator_name}
                        </p>
                      )}
                    </div>
                  </div>

                  <span className="text-xs font-mono text-slate-400 ml-4 shrink-0">
                    {track.formatted_duration}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // CASO 2: El libro no tiene pistas grabadas pero sí sinopsis (Modo TTS Accesible)
  if (data?.tts?.is_available || (description && description.trim().length > 0)) {
    const textToRead = data?.tts?.text_content || description || '';
    const estDuration = data?.tts?.formatted_estimated_duration || '2 min';

    return (
      <div className="p-6 rounded-3xl bg-slate-50 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="p-2.5 rounded-2xl bg-teal-100 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 text-xl shrink-0">
              <HiOutlineVolumeUp className="w-6 h-6" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-bold text-sm sm:text-base text-slate-900 dark:text-white">
                  Lectura asistida por voz (TTS)
                </h4>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                  Accesibilidad
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
                Escucha la sinopsis y fragmentos clave de esta obra con el sintetizador de voz
                nativo de tu navegador. Duración estimada: ~{estDuration}.
              </p>
            </div>
          </div>

          <Button
            size="sm"
            color="teal"
            onClick={() => playTts(bookItem, textToRead)}
            className="font-bold shrink-0 shadow-sm"
          >
            <HiOutlineSparkles className="w-4 h-4 mr-1.5" />
            Escuchar con BookVoice
          </Button>
        </div>
      </div>
    );
  }

  return null;
}

export default BookAudiobookSection;
