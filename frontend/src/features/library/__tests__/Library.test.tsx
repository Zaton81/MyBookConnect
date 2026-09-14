import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Library } from '../pages/Library';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('Library Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => {
      const state = { token: 'mock-token', user: { id: 1, username: 'testuser' } };
      return selector ? selector(state) : state;
    });
    
    globalThis.fetch = vi.fn();
  });

  const renderLibrary = () => {
    return render(
      <MemoryRouter initialEntries={['/library']}>
        <Routes>
          <Route path="/library" element={<Library />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('displays a loading spinner initially', () => {
    (globalThis.fetch as any).mockImplementationOnce(() => new Promise(() => {})); // Never resolves
    renderLibrary();
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders user books when fetch succeeds', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            id: 1,
            book: {
              id: 101,
              title: 'My Favorite Book',
              author: { name: 'Awesome Author' },
            },
            status: 'reading',
            progress: 50,
          }
        ],
        count: 1
      })
    });

    renderLibrary();

    await waitFor(() => {
      expect(screen.getByText('My Favorite Book')).toBeInTheDocument();
    });
    expect(screen.getByText(/awesome author/i)).toBeInTheDocument();
  });
});
