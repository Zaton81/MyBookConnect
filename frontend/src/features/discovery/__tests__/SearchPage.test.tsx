import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchPage } from '../pages/SearchPage';
import { apiClient } from '../../../api/client';

vi.mock('../../../api/client', () => ({
  apiClient: vi.fn(),
}));

describe('SearchPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockSearchResponse = {
    query: 'quijote',
    type: 'all',
    total_results: 3,
    books: [
      {
        id: 10,
        title: 'Don Quijote de la Mancha',
        author: { id: 1, name: 'Miguel de Cervantes' },
        cover: null,
        description: 'Obra cumbre de la literatura.',
        isbn: '9781234567890',
        additional_isbns: ['9780987654321'],
        average_rating: 4.8,
        reviews_count: 42,
      },
    ],
    authors: [
      {
        id: 1,
        name: 'Miguel de Cervantes',
        photo: null,
        biography: 'Escritor español célebre.',
        is_verified: true,
        published_books_count: 5,
        total_readers_count: 120,
        total_reviews_count: 45,
        average_rating: 4.9,
      },
    ],
    users: [
      {
        id: 99,
        username: 'quijotero_fan',
        first_name: 'Alonso',
        last_name: 'Quijano',
        avatar: null,
        bio: 'Amante de la caballería andante.',
      },
    ],
  };

  const renderSearchPage = (initialUrl = '/search') => {
    return render(
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders search form and popular suggestions initially', () => {
    renderSearchPage();

    expect(screen.getByRole('heading', { name: /Búsqueda Global Unificada/i })).toBeInTheDocument();
    expect(screen.getByRole('search')).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Término de búsqueda global/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Búsquedas populares:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dune' })).toBeInTheDocument();
  });

  it('executes search automatically if "q" query param is present in URL', async () => {
    (apiClient as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockSearchResponse);

    renderSearchPage('/search?q=quijote');

    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/search/?q=quijote'),
      expect.objectContaining({ method: 'GET' })
    );

    await waitFor(() => {
      expect(screen.getByText('Don Quijote de la Mancha')).toBeInTheDocument();
      expect(screen.getAllByText('Miguel de Cervantes').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('@quijotero_fan')).toBeInTheDocument();
    });
  });

  it('allows user to type and submit a search query', async () => {
    (apiClient as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockSearchResponse);

    renderSearchPage();

    const input = screen.getByLabelText(/Término de búsqueda global/i);
    fireEvent.change(input, { target: { value: 'quijote' } });
    expect(input).toHaveValue('quijote');

    const submitBtn = screen.getByRole('button', { name: 'Buscar' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalled();
      expect(screen.getByText('Don Quijote de la Mancha')).toBeInTheDocument();
    });
  });

  it('supports filtering results via tabs and verifies WCAG tab roles', async () => {
    (apiClient as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockSearchResponse);

    renderSearchPage('/search?q=quijote');

    await waitFor(() => {
      expect(screen.getByText('Don Quijote de la Mancha')).toBeInTheDocument();
    });

    const tablist = screen.getByRole('tablist');
    expect(tablist).toBeInTheDocument();

    const booksTab = screen.getByRole('tab', { name: /Libros/i });
    expect(booksTab).toHaveAttribute('aria-selected', 'false');

    fireEvent.click(booksTab);
    expect(booksTab).toHaveAttribute('aria-selected', 'true');
  });

  it('displays error message if search request fails', async () => {
    (apiClient as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('Network error')
    );

    renderSearchPage('/search?q=quijote');

    await waitFor(() => {
      expect(
        screen.getByText('Error al consultar el motor de búsqueda. Inténtalo de nuevo.')
      ).toBeInTheDocument();
    });
  });
});
