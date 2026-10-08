import { create } from 'zustand';

export interface AudioBookItem {
  id: number;
  title: string;
  author_name?: string;
  cover_url?: string | null;
}

export interface AudioTrackItem {
  id: number;
  title: string;
  track_number: number;
  duration_seconds: number;
  formatted_duration?: string;
  stream_url: string;
  narrator_name?: string;
  is_sample?: boolean;
}

export interface AudioPlayerState {
  currentBook: AudioBookItem | null;
  currentTrack: AudioTrackItem | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  playbackSpeed: number;
  volume: number;
  isMuted: boolean;
  isOpen: boolean;
  isTtsActive: boolean;
  ttsText: string;

  // Actions
  playTrack: (
    book: AudioBookItem,
    track: AudioTrackItem,
    startAtSeconds?: number,
    speed?: number
  ) => void;
  pauseTrack: () => void;
  resumeTrack: () => void;
  togglePlay: () => void;
  seekTo: (seconds: number) => void;
  skipSeconds: (delta: number) => void;
  setPlaybackSpeed: (speed: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  playTts: (book: AudioBookItem, text: string, speed?: number) => void;
  stopTts: () => void;
  closePlayer: () => void;
}

export const useAudioPlayerStore = create<AudioPlayerState>((set, get) => ({
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

  playTrack: (book, track, startAtSeconds = 0, speed = 1.0) => {
    // Si había TTS activo, lo detenemos
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    set({
      currentBook: book,
      currentTrack: track,
      currentTime: startAtSeconds,
      duration: track.duration_seconds || 0,
      playbackSpeed: speed,
      isPlaying: true,
      isOpen: true,
      isTtsActive: false,
      ttsText: '',
    });
  },

  pauseTrack: () => {
    if (get().isTtsActive && typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.pause();
    }
    set({ isPlaying: false });
  },

  resumeTrack: () => {
    if (get().isTtsActive && typeof window !== 'undefined' && window.speechSynthesis) {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    }
    set({ isPlaying: true });
  },

  togglePlay: () => {
    const { isPlaying } = get();
    if (isPlaying) {
      get().pauseTrack();
    } else {
      get().resumeTrack();
    }
  },

  seekTo: (seconds: number) => {
    const maxDur = get().duration || 1;
    const clamped = Math.max(0, Math.min(seconds, maxDur));
    set({ currentTime: clamped });
  },

  skipSeconds: (delta: number) => {
    const { currentTime, duration } = get();
    const nextTime = Math.max(0, Math.min(currentTime + delta, duration || 99999));
    set({ currentTime: nextTime });
  },

  setPlaybackSpeed: (speed: number) => {
    const clamped = Math.max(0.5, Math.min(3.0, speed));
    set({ playbackSpeed: clamped });
  },

  setVolume: (vol: number) => {
    const clamped = Math.max(0, Math.min(1, vol));
    set({ volume: clamped, isMuted: clamped === 0 });
  },

  toggleMute: () => {
    set((state) => ({ isMuted: !state.isMuted }));
  },

  setCurrentTime: (time: number) => {
    set({ currentTime: time });
  },

  setDuration: (duration: number) => {
    set({ duration });
  },

  playTts: (book, text, speed = 1.0) => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    set({
      currentBook: book,
      currentTrack: {
        id: -1,
        title: 'Lectura asistida por voz (TTS)',
        track_number: 1,
        duration_seconds: Math.max(30, Math.round((text.split(' ').length / 140) * 60)),
        stream_url: '',
      },
      currentTime: 0,
      duration: Math.max(30, Math.round((text.split(' ').length / 140) * 60)),
      playbackSpeed: speed,
      isPlaying: true,
      isOpen: true,
      isTtsActive: true,
      ttsText: text,
    });
  },

  stopTts: () => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    set({
      isPlaying: false,
      isTtsActive: false,
      ttsText: '',
    });
  },

  closePlayer: () => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    set({
      isPlaying: false,
      isOpen: false,
      isTtsActive: false,
      currentBook: null,
      currentTrack: null,
      currentTime: 0,
    });
  },
}));
