import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthorEventsSection, AuthorEventItem } from '../components/AuthorEventsSection';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('AuthorEventsSection Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester', role: 'USER' },
    });
    globalThis.fetch = vi.fn();
  });

  const sampleEvents: AuthorEventItem[] = [
    {
      id: 1,
      author: 42,
      author_name: 'Miguel de Cervantes',
      created_by: 10,
      created_by_username: 'cervantes_official',
      title: 'Presentación Don Quijote IV Centenario',
      description: 'Lectura comentada y preguntas del público lector.',
      event_type: 'BOOK_LAUNCH',
      event_type_display: 'Lanzamiento / Presentación',
      event_format: 'HYBRID',
      event_format_display: 'Híbrido',
      start_time: '2026-11-15T18:00:00Z',
      event_timezone: 'Europe/Madrid',
      location_name: 'Ateneo de Madrid',
      online_url: 'https://meet.jit.si/cervantes',
      max_attendees: 50,
      is_cancelled: false,
      registered_count: 12,
      waitlist_count: 0,
      is_full: false,
      user_registration_status: null,
      is_user_registered: false,
      created_at: '2026-10-01T10:00:00Z',
    },
  ];

  it('renders section title and empty state when no events exist', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(
      <AuthorEventsSection
        authorId={42}
        authorName="Miguel de Cervantes"
        isAuthorOwner={false}
        books={[]}
      />
    );

    expect(screen.getByText(/Encuentros y Eventos Literarios/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/No hay eventos programados próximamente/i)).toBeInTheDocument();
    });
  });

  it('renders event card and register button when events are fetched', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => sampleEvents,
    });

    render(
      <AuthorEventsSection
        authorId={42}
        authorName="Miguel de Cervantes"
        isAuthorOwner={false}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Presentación Don Quijote IV Centenario')).toBeInTheDocument();
      expect(screen.getByText(/Lectura comentada y preguntas/i)).toBeInTheDocument();
      expect(screen.getByText(/Inscribirme al evento/i)).toBeInTheDocument();
    });
  });

  it('displays Crear Evento button when isAuthorOwner is true', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => sampleEvents,
    });

    render(
      <AuthorEventsSection
        authorId={42}
        authorName="Miguel de Cervantes"
        isAuthorOwner={true}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Crear Evento/i)).toBeInTheDocument();
      expect(screen.getByText(/Ver Asistentes/i)).toBeInTheDocument();
    });
  });

  it('displays Inscrito and Cancelar plaza when user is registered', async () => {
    const registeredEvents: AuthorEventItem[] = [
      {
        ...sampleEvents[0],
        user_registration_status: 'REGISTERED',
        is_user_registered: true,
      },
    ];

    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => registeredEvents,
    });

    render(
      <AuthorEventsSection
        authorId={42}
        authorName="Miguel de Cervantes"
        isAuthorOwner={false}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Inscrito')).toBeInTheDocument();
      expect(screen.getByText('Cancelar plaza')).toBeInTheDocument();
    });
  });
});
