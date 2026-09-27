import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReadingLists } from '../pages/ReadingLists';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('ReadingLists Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester' },
    });
    globalThis.fetch = vi.fn();
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <ReadingLists />
      </MemoryRouter>
    );
  };

  it('renders heading and tabs correctly', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    renderComponent();

    expect(screen.getByText('Listas de Lectura')).toBeInTheDocument();
    expect(screen.getByText(/Mis Listas/i)).toBeInTheDocument();
    expect(screen.getByText(/Explorar/i)).toBeInTheDocument();
  });

  it('renders reading lists fetched from API', async () => {
    const mockLists = [
      {
        id: 101,
        name: 'Ciencia Ficción 2026',
        slug: 'ciencia-ficcion-2026',
        description: 'Mejores lecturas sci-fi',
        privacy: 'public',
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
        user: { id: 1, username: 'tester' },
        items: [],
        items_count: 5,
        followers_count: 2,
        is_following: false,
      },
    ];

    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockLists,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Ciencia Ficción 2026')).toBeInTheDocument();
    });
    expect(screen.getByText('Mejores lecturas sci-fi')).toBeInTheDocument();
  });
});
