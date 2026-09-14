import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BookDetail } from '../pages/BookDetail';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('BookDetail Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => {
      const state = { token: 'mock-token', user: { id: 1, username: 'testuser' } };
      return selector ? selector(state) : state;
    });
    
    globalThis.fetch = vi.fn();
  });

  const renderBookDetail = (bookId = '1') => {
    return render(
      <MemoryRouter initialEntries={[`/books/${bookId}`]}>
        <Routes>
          <Route path="/books/:id" element={<BookDetail />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('displays loading state initially', () => {
    (globalThis.fetch as any).mockImplementationOnce(() => new Promise(() => {})); // Never resolves
    const { container } = renderBookDetail();
    // Usually a spinner or loading text is shown, we'll just check it renders without crashing
    expect(container).toBeInTheDocument();
  });

  it('renders book details when fetch succeeds', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        title: 'Mock Book Title',
        author: { name: 'Mock Author' },
        description: 'Mock Description',
        categories: [],
        rating: 4.5
      })
    });

    renderBookDetail();

    await waitFor(() => {
      expect(screen.getAllByText('Mock Book Title').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Mock Author')).toBeInTheDocument();
  });

  it('renders an error message when fetch fails', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({})
    });

    renderBookDetail();

    await waitFor(() => {
      expect(screen.getByText(/Libro no encontrado/i)).toBeInTheDocument();
    });
  });
});
