import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthorNewsletterSection, AuthorNewsletterItem, AuthorNewsletterIssueItem } from '../components/AuthorNewsletterSection';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('AuthorNewsletterSection Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester', role: 'USER' },
    });
    globalThis.fetch = vi.fn();
  });

  const sampleNewsletter: AuthorNewsletterItem = {
    id: 1,
    author: 10,
    author_name: 'Isabel Allende',
    title: 'Cartas desde mi escritorio',
    description: 'Reflexiones y primicias exclusivas para lectores.',
    frequency: 'MONTHLY',
    frequency_display: 'Mensual',
    is_active: true,
    active_subscribers_count: 42,
    sent_issues_count: 3,
    is_subscribed: false,
    latest_issues: [],
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
  };

  const sampleIssues: AuthorNewsletterIssueItem[] = [
    {
      id: 101,
      newsletter: 1,
      newsletter_title: 'Cartas desde mi escritorio',
      author_name: 'Isabel Allende',
      title: 'Entrega #1: Mis libros favoritos del año',
      subject: 'Recomendaciones y secretos de biblioteca',
      content: 'Queridos lectores, en esta primera carta os desvelo las obras que marcaron mi año.',
      status: 'SENT',
      status_display: 'Enviado',
      sent_at: '2026-10-05T10:00:00Z',
      recipients_count: 42,
      views_count: 35,
      created_at: '2026-10-05T09:00:00Z',
    },
  ];

  it('renders section header and empty state when no newsletter exists', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(
      <AuthorNewsletterSection
        authorId={10}
        authorName="Isabel Allende"
        isAuthorOwner={false}
      />
    );

    expect(screen.getByText(/Boletín Literario & Novedades/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Sin boletín activo actualmente/i)).toBeInTheDocument();
    });
  });

  it('renders newsletter details and allows reader to subscribe and unsubscribe', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [sampleNewsletter],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleIssues,
      });

    render(
      <AuthorNewsletterSection
        authorId={10}
        authorName="Isabel Allende"
        isAuthorOwner={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Cartas desde mi escritorio')).toBeInTheDocument();
      expect(screen.getByText(/42 suscriptores/i)).toBeInTheDocument();
      expect(screen.getByText(/Suscribirme con 1 clic/i)).toBeInTheDocument();
    });

    // Mock para suscripción
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        is_subscribed: true,
        active_subscribers_count: 43,
      }),
    });

    const subButton = screen.getByText(/Suscribirme con 1 clic/i);
    fireEvent.click(subButton);

    await waitFor(() => {
      expect(screen.getByText(/Suscrito \(Cancelar\)/i)).toBeInTheDocument();
    });
  });

  it('renders published issues and expands content on click', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [sampleNewsletter],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleIssues,
      });

    render(
      <AuthorNewsletterSection
        authorId={10}
        authorName="Isabel Allende"
        isAuthorOwner={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Entrega #1: Mis libros favoritos del año')).toBeInTheDocument();
      expect(screen.getByText(/Asunto: Recomendaciones y secretos de biblioteca/i)).toBeInTheDocument();
    });

    const expandButton = screen.getByText(/Leer entrega/i);
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText(/Queridos lectores, en esta primera carta/i)).toBeInTheDocument();
      expect(screen.getByText(/Ocultar/i)).toBeInTheDocument();
    });
  });

  it('shows author management controls when user is owner', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [sampleNewsletter],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleIssues,
      });

    render(
      <AuthorNewsletterSection
        authorId={10}
        authorName="Isabel Allende"
        isAuthorOwner={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Editar boletín/i)).toBeInTheDocument();
      expect(screen.getByText(/Nueva entrega/i)).toBeInTheDocument();
    });
  });
});
