import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AudioPlayerBar, formatTime } from '../../../components/audio/AudioPlayerBar';
import { BookAudiobookSection } from '../components/BookAudiobookSection';
import { useAudioPlayerStore } from '../../../store/audioPlayer';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('Audiobook & TTS Player Suite (Sprint 18)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-jwt-token',
      user: { id: 1, username: 'testuser' },
    });

    // Resetear store
    useAudioPlayerStore.setState({
      currentBook: null,
      currentTrack: null,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      playbackSpeed: 1.0,
      volume: 1.0,
      isMuted: false,
      isOpen: false,
      isTtsActive: false,
      ttsText: '',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('correctly formats seconds into mm:ss format', () => {
    expect(formatTime(0)).toBe('0:00');
    expect(formatTime(45)).toBe('0:45');
    expect(formatTime(125)).toBe('2:05');
    expect(formatTime(3600)).toBe('60:00');
  });

  it('renders AudioPlayerBar when open with book and track information', () => {
    useAudioPlayerStore.setState({
      isOpen: true,
      currentBook: {
        id: 10,
        title: 'Cien años de soledad',
        author_name: 'Gabriel García Márquez',
        cover_url: null,
      },
      currentTrack: {
        id: 1,
        title: 'Capítulo 1: Macondo',
        track_number: 1,
        duration_seconds: 1800,
        stream_url: 'https://cdn.example.com/audio.mp3',
        narrator_name: 'Víctor Manuel',
      },
      isPlaying: false,
      currentTime: 120,
      duration: 1800,
      playbackSpeed: 1.0,
    });

    render(<AudioPlayerBar />);

    expect(screen.getByRole('region', { name: /Reproductor de audiolibro/i })).toBeInTheDocument();
    expect(screen.getByText('Cien años de soledad')).toBeInTheDocument();
    expect(screen.getByText('Capítulo 1: Macondo')).toBeInTheDocument();
    expect(screen.getByText(/Voz: Víctor Manuel/i)).toBeInTheDocument();
    expect(screen.getByText('2:00')).toBeInTheDocument();
    expect(screen.getByText('30:00')).toBeInTheDocument();
  });

  it('toggles play/pause and modifies playback speed', () => {
    useAudioPlayerStore.setState({
      isOpen: true,
      currentBook: { id: 10, title: 'Cien años de soledad' },
      currentTrack: {
        id: 1,
        title: 'Capítulo 1',
        track_number: 1,
        duration_seconds: 1800,
        stream_url: '',
      },
      isPlaying: false,
      currentTime: 0,
      duration: 1800,
    });

    render(<AudioPlayerBar />);

    const playButton = screen.getByRole('button', { name: /Iniciar reproducción/i });
    fireEvent.click(playButton);
    expect(useAudioPlayerStore.getState().isPlaying).toBe(true);

    // Cambiar velocidad
    const speedButton = screen.getByRole('button', { name: /Velocidad actual: 1x/i });
    fireEvent.click(speedButton);

    const speed15Button = screen.getByText('1.5x');
    fireEvent.click(speed15Button);
    expect(useAudioPlayerStore.getState().playbackSpeed).toBe(1.5);
  });

  it('renders BookAudiobookSection with track list and starts playback on click', async () => {
    const mockAudiobookData = {
      book_id: 10,
      book_title: 'Cien años de soledad',
      author_name: 'Gabriel García Márquez',
      cover_url: null,
      has_audiobook: true,
      tracks_count: 2,
      total_duration_seconds: 4200,
      formatted_total_duration: '1 h 10 min',
      narrators: ['Víctor Manuel'],
      sample_track: {
        id: 1,
        title: 'Capítulo 1: Macondo',
        track_number: 1,
        duration_seconds: 1800,
        formatted_duration: '30:00',
        stream_url: 'https://cdn.example.com/audio1.mp3',
        is_sample: true,
      },
      tracks: [
        {
          id: 1,
          title: 'Capítulo 1: Macondo',
          track_number: 1,
          duration_seconds: 1800,
          formatted_duration: '30:00',
          stream_url: 'https://cdn.example.com/audio1.mp3',
          narrator_name: 'Víctor Manuel',
          is_sample: true,
        },
        {
          id: 2,
          title: 'Capítulo 2: Los gitanos',
          track_number: 2,
          duration_seconds: 2400,
          formatted_duration: '40:00',
          stream_url: 'https://cdn.example.com/audio2.mp3',
          narrator_name: 'Víctor Manuel',
          is_sample: false,
        },
      ],
      progress: null,
      tts: { is_available: false, word_count: 0, estimated_duration_seconds: 0, text_content: '' },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAudiobookData,
    } as any);

    render(
      <BookAudiobookSection
        bookId={10}
        bookTitle="Cien años de soledad"
        authorName="Gabriel García Márquez"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Edición Narrada en Audio')).toBeInTheDocument();
      expect(screen.getByText('1 h 10 min total')).toBeInTheDocument();
      expect(screen.getByText('Capítulo 1: Macondo')).toBeInTheDocument();
      expect(screen.getByText('Capítulo 2: Los gitanos')).toBeInTheDocument();
    });

    const playSampleBtn = screen.getByRole('button', { name: /Escuchar muestra gratuita/i });
    fireEvent.click(playSampleBtn);

    const storeState = useAudioPlayerStore.getState();
    expect(storeState.isOpen).toBe(true);
    expect(storeState.currentTrack?.title).toBe('Capítulo 1: Macondo');
    expect(storeState.isPlaying).toBe(true);
  });

  it('renders TTS accessibility assistant when book has no audio tracks and starts BookVoice', async () => {
    const mockTtsData = {
      book_id: 20,
      book_title: 'Crónica de una muerte anunciada',
      author_name: 'Gabriel García Márquez',
      has_audiobook: false,
      tracks_count: 0,
      total_duration_seconds: 0,
      tracks: [],
      tts: {
        is_available: true,
        word_count: 280,
        estimated_duration_seconds: 120,
        formatted_estimated_duration: '2 min',
        text_content: 'El día en que lo iban a matar, Santiago Nasar se levantó a las 5:30 de la mañana.',
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTtsData,
    } as any);

    render(
      <BookAudiobookSection
        bookId={20}
        bookTitle="Crónica de una muerte anunciada"
        authorName="Gabriel García Márquez"
        description="El día en que lo iban a matar, Santiago Nasar se levantó a las 5:30 de la mañana."
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Lectura asistida por voz (TTS)')).toBeInTheDocument();
      expect(screen.getByText(/Escucha la sinopsis y fragmentos clave/i)).toBeInTheDocument();
    });

    const bookVoiceBtn = screen.getByRole('button', { name: /Escuchar con BookVoice/i });
    fireEvent.click(bookVoiceBtn);

    const storeState = useAudioPlayerStore.getState();
    expect(storeState.isOpen).toBe(true);
    expect(storeState.isTtsActive).toBe(true);
    expect(storeState.ttsText).toContain('Santiago Nasar');
  });
});
