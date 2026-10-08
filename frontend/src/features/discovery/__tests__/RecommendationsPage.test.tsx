import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RecommendationsPage } from '../pages/RecommendationsPage';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('RecommendationsPage Component (Sprint 17)', () => {
  const mockToken = 'mock-jwt-token';
  const mockUser = { id: 1, username: 'testuser' };

  const mockRecommendations = {
    results: [
      {
        id: 101,
        title: 'Cien años de soledad',
        author_name: 'Gabriel García Márquez',
        cover: null,
        average_rating: 4.8,
        score: 0.95,
        affinity_percentage: 95,
        reason: 'Coincidencia con tus novelas de realismo mágico favoritas.',
        categories: [{ id: 1, name: 'Realismo Mágico' }],
        pages: 417,
        breakdown: { collaborative: 0.6, semantic: 0.35 },
      },
      {
        id: 102,
        title: 'Ficciones',
        author_name: 'Jorge Luis Borges',
        cover: null,
        average_rating: 4.7,
        score: 0.91,
        affinity_percentage: 91,
        reason: 'Lectores con gustos parecidos a los tuyos calificaron esta obra con 5 estrellas.',
        categories: [{ id: 2, name: 'Ficción' }],
        pages: 220,
        breakdown: { collaborative: 0.8 },
      },
    ],
    strategy: 'hybrid',
    count: 2,
  };

  const mockSimilarReaders = {
    results: [
      {
        user_id: 42,
        username: 'lector_gemelo_42',
        similarity_score: 0.88,
        shared_books_count: 14,
        avatar_url: null,
      },
    ],
  };

  const mockCategories = {
    results: [
      { id: 1, name: 'Realismo Mágico' },
      { id: 2, name: 'Ficción' },
      { id: 3, name: 'Ciencia Ficción' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: mockToken,
      user: mockUser,
    });

    globalThis.fetch = vi.fn(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes('/api/v1/books/recommendations/similar-readers/')) {
        return {
          ok: true,
          json: async () => mockSimilarReaders,
        } as any;
      }
      if (urlStr.includes('/api/v1/books/categories/')) {
        return {
          ok: true,
          json: async () => mockCategories,
        } as any;
      }
      if (urlStr.includes('/api/v1/books/recommendations/dismiss/')) {
        return {
          ok: true,
          json: async () => ({ status: 'ok', message: 'Descartado' }),
        } as any;
      }
      if (urlStr.includes('/api/v1/books/user-books/')) {
        return {
          ok: true,
          json: async () => ({ id: 1, status: 'want_to_read' }),
        } as any;
      }
      if (urlStr.includes('/api/v1/books/recommendations/')) {
        return {
          ok: true,
          json: async () => mockRecommendations,
        } as any;
      }
      return {
        ok: true,
        json: async () => ({}),
      } as any;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderComponent = () =>
    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    );

  it('renders page header, mode selectors and filter controls', async () => {
    renderComponent();

    expect(
      screen.getByRole('heading', { name: /Recomendaciones Inteligentes/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Descubre lecturas seleccionadas a tu medida/i)
    ).toBeInTheDocument();

    // Modos de recomendación
    expect(screen.getByText('Híbrido IA')).toBeInTheDocument();
    expect(screen.getAllByText('Gemelos Lectores').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Estilo y Temática')).toBeInTheDocument();
    expect(screen.getByText('Descubrimiento')).toBeInTheDocument();

    // Filtros
    expect(screen.getByLabelText(/Género:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Longitud:/i)).toBeInTheDocument();
  });

  it('fetches and displays recommended books with match percentage and similar readers', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText('Cien años de soledad').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Ficciones').length).toBeGreaterThanOrEqual(1);
    });

    // Validar % Afinidad
    expect(screen.getByText('95% Afinidad')).toBeInTheDocument();
    expect(screen.getByText('91% Afinidad')).toBeInTheDocument();

    // Validar razones explicables
    expect(
      screen.getByText(/Coincidencia con tus novelas de realismo mágico favoritas/i)
    ).toBeInTheDocument();

    // Validar widget de lectores similares
    expect(screen.getByText('@lector_gemelo_42')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
  });

  it('allows user to switch recommendation strategy and refetches data', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText('Cien años de soledad').length).toBeGreaterThanOrEqual(1);
    });

    const collabTab = screen.getByRole('tab', { name: /Gemelos Lectores/i });
    fireEvent.click(collabTab);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('strategy=collab'),
        expect.anything()
      );
    });
  });

  it('adds book to "Quiero leer" library shelf with 1-click feedback', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText('Cien años de soledad').length).toBeGreaterThanOrEqual(1);
    });

    const wantToReadButtons = screen.getAllByRole('button', { name: /Quiero leer/i });
    expect(wantToReadButtons.length).toBeGreaterThanOrEqual(1);

    fireEvent.click(wantToReadButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('En tu biblioteca')).toBeInTheDocument();
    });
  });

  it('allows dismissing a recommended book with 1-click and removes it from view', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText('Cien años de soledad').length).toBeGreaterThanOrEqual(1);
    });

    const dismissButton = screen.getByRole('button', {
      name: 'Descartar Cien años de soledad',
    });
    fireEvent.click(dismissButton);

    await waitFor(() => {
      expect(screen.queryAllByText('Cien años de soledad').length).toBe(0);
      expect(screen.getAllByText('Ficciones').length).toBeGreaterThanOrEqual(1);
    });
  });
});
