import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthorPublicationsSection, AuthorPublicationItem } from '../components/AuthorPublicationsSection';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('AuthorPublicationsSection Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester', role: 'USER' },
    });
    globalThis.fetch = vi.fn();
  });

  const samplePublications: AuthorPublicationItem[] = [
    {
      id: 1,
      author_profile: 1,
      author: 10,
      author_name: 'Gabriel García Márquez',
      title: 'Adelanto del nuevo prólogo',
      content: 'Texto completo de prueba con revelaciones de la trama.',
      excerpt: 'Texto completo de prueba...',
      publication_type: 'CHAPTER_PREVIEW',
      publication_type_display: 'Adelanto de capítulo',
      has_spoilers: true,
      spoiler_warning: 'Revela el destino del coronel.',
      estimated_reading_time: 3,
      is_pinned: true,
      is_draft: false,
      created_at: '2026-10-01T12:00:00Z',
      updated_at: '2026-10-01T12:00:00Z',
    },
  ];

  it('renders section header and empty state when no publications exist', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={false}
        books={[]}
      />
    );

    expect(screen.getByText(/Publicaciones y Adelantos/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Aún no hay publicaciones en esta categoría/i)).toBeInTheDocument();
    });
  });

  it('renders publication card with badges, reading time and spoiler warning', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => samplePublications,
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={false}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Adelanto del nuevo prólogo')).toBeInTheDocument();
      expect(screen.getByText(/Adelanto de capítulo/i)).toBeInTheDocument();
      expect(screen.getByText(/3 min de lectura/i)).toBeInTheDocument();
      expect(screen.getByText(/Revela el destino del coronel/i)).toBeInTheDocument();
      expect(screen.getByText(/Contenido oculto para evitar spoilers/i)).toBeInTheDocument();
    });
  });

  it('reveals spoiler content when user clicks Revelar button', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => samplePublications,
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={false}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Revelar')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Revelar'));

    expect(screen.getByText(/Texto completo de prueba/i)).toBeInTheDocument();
    expect(screen.getByText('Ocultar')).toBeInTheDocument();
  });

  it('displays Nueva Publicación button when isAuthorOwner is true', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => samplePublications,
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={true}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Nueva Publicación/i)).toBeInTheDocument();
      expect(screen.getByText(/Borradores/i)).toBeInTheDocument();
    });
  });

  it('displays Censurar and edit button for admin, but NOT Nueva Publicación if not author owner', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => samplePublications,
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={false}
        isAdmin={true}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByTitle(/Censurar publicación/i)).toBeInTheDocument();
      expect(screen.getByTitle(/Modificar publicación \(Admin\)/i)).toBeInTheDocument();
      expect(screen.queryByText(/Nueva Publicación/i)).not.toBeInTheDocument();
    });
  });

  it('renders paid badge and moderated alert when present', async () => {
    const moderatedPaidPublications: AuthorPublicationItem[] = [
      {
        ...samplePublications[0],
        is_paid: true,
        price: '2.50',
        is_moderated: true,
        moderation_reason: 'Contenido bajo revisión por spoiler explícito.',
      },
    ];

    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => moderatedPaidPublications,
    });

    render(
      <AuthorPublicationsSection
        authorId={10}
        authorName="Gabriel García Márquez"
        isAuthorOwner={false}
        isAdmin={true}
        books={[]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/🔒 De pago \(2.50 €\)/i)).toBeInTheDocument();
      expect(screen.getByText(/🚫 Censurada/i)).toBeInTheDocument();
      expect(screen.getByText(/Publicación censurada por moderación/i)).toBeInTheDocument();
    });
  });
});
