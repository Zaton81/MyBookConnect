import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChallengesPage } from '../pages/ChallengesPage';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('ChallengesPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester', role: 'USER' },
    });
    globalThis.fetch = vi.fn();
  });

  const sampleOverview = {
    gamification_enabled: true,
    streak: {
      current_streak: 5,
      longest_streak: 12,
      last_reading_date: '2026-10-07',
      read_today: true,
    },
    goal: {
      year: 2026,
      target_books: 20,
      target_pages: 5000,
      current_books: 8,
      remaining_books: 12,
      percentage: 40.0,
      pacing_status: 'on_track',
      pacing_text: 'Vas al ritmo previsto',
      has_goal: true,
    },
    badges: {
      total_badges: 10,
      unlocked_count: 4,
      total_points: 95,
      list: [
        {
          id: 1,
          slug: 'raton-de-biblioteca',
          name: 'Ratón de biblioteca',
          description: 'Has terminado tu primer libro.',
          icon: '📚',
          category: 'reading',
          category_display: 'Lectura',
          points: 10,
          unlocked: true,
          awarded_at: '2026-05-01T10:00:00Z',
        },
      ],
    },
    challenges: [
      {
        id: 101,
        slug: 'reto-anual-2026',
        title: 'Reto Anual de Lectura 2026',
        description: 'Lee 12 libros durante 2026',
        challenge_type: 'books_count',
        target_count: 12,
        current_progress: 8,
        percentage: 66.7,
        is_completed: false,
        completed_at: null,
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        is_active: true,
        badge_reward: { name: 'Devoto', icon: '🦁' },
      },
    ],
  };

  const sampleChallenges = [
    {
      id: 101,
      slug: 'reto-anual-2026',
      title: 'Reto Anual de Lectura 2026',
      description: 'Lee 12 libros durante 2026',
      challenge_type: 'books_count',
      target_count: 12,
      start_date: '2026-01-01',
      end_date: '2026-12-31',
      badge_reward: { name: 'Devoto', icon: '🦁' },
    },
  ];

  const sampleBadges = [
    {
      id: 1,
      slug: 'raton-de-biblioteca',
      name: 'Ratón de biblioteca',
      description: 'Has terminado tu primer libro.',
      icon: '📚',
      category: 'reading',
      category_display: 'Lectura',
      points: 10,
      unlocked: true,
      awarded_at: '2026-05-01T10:00:00Z',
    },
    {
      id: 2,
      slug: 'lector-voraz',
      name: 'Lector voraz',
      description: '25 libros leídos.',
      icon: '🦁',
      category: 'reading',
      category_display: 'Lectura',
      points: 50,
      unlocked: false,
      awarded_at: null,
    },
  ];

  it('renders header and initial challenges tab correctly with metrics', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({ ok: true, json: async () => sampleOverview })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleChallenges })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleBadges });

    render(<ChallengesPage />);

    expect(screen.getByText(/Retos de Lectura & Gamificación/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/5 días/i)).toBeInTheDocument();
      expect(screen.getByText('Reto Anual de Lectura 2026')).toBeInTheDocument();
      expect(screen.getByText(/Participando/i)).toBeInTheDocument();
    });
  });

  it('switches to annual goal tab and displays progress and pacing', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({ ok: true, json: async () => sampleOverview })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleChallenges })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleBadges });

    render(<ChallengesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mi Meta Anual/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Mi Meta Anual/i));

    await waitFor(() => {
      expect(screen.getByText(/Objetivo de Lectura/i)).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument(); // current books
      expect(screen.getByText('20')).toBeInTheDocument(); // target books
      expect(screen.getByText('40%')).toBeInTheDocument(); // percentage
      expect(screen.getByText(/Vas al ritmo previsto/i)).toBeInTheDocument();
    });
  });

  it('switches to streak tab and displays streak cards', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({ ok: true, json: async () => sampleOverview })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleChallenges })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleBadges });

    render(<ChallengesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Racha & Registro/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Racha & Registro/i));

    await waitFor(() => {
      expect(screen.getByText(/Racha de Lectura Consecutiva/i)).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // current streak
      expect(screen.getByText('12')).toBeInTheDocument(); // longest streak
      expect(screen.getByText(/He leído hoy/i)).toBeInTheDocument();
    });
  });

  it('switches to badges tab and filters catalog', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({ ok: true, json: async () => sampleOverview })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleChallenges })
      .mockResolvedValueOnce({ ok: true, json: async () => sampleBadges });

    render(<ChallengesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Medallero/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Medallero/i));

    await waitFor(() => {
      expect(screen.getByText(/Catálogo de Insignias y Logros/i)).toBeInTheDocument();
      expect(screen.getByText('Ratón de biblioteca')).toBeInTheDocument();
      expect(screen.getByText('Lector voraz')).toBeInTheDocument();
      expect(screen.getByText(/✓ Desbloqueada/i)).toBeInTheDocument();
      expect(screen.getByText(/🔒 Bloqueada/i)).toBeInTheDocument();
    });
  });
});
