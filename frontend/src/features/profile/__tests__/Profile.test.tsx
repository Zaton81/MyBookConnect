import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Profile } from '../pages/Profile';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('Profile Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'testuser' },
      followUser: vi.fn(),
      unfollowUser: vi.fn(),
      getFollowStatus: vi.fn().mockResolvedValue({ is_following: false, is_mutual: false }),
    });
    globalThis.fetch = vi.fn();
  });

  const renderProfile = (path = '/profile') => {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/:userId" element={<Profile />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders own profile details and action buttons', async () => {
    (globalThis.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/profile/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 1,
            username: 'testuser',
            first_name: 'Test',
            last_name: 'User',
            email: 'test@example.com',
            privacy_level: 'public',
            bio: 'Lover of books',
            location: 'Madrid',
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });

    renderProfile('/profile');

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
    expect(screen.getByText('@testuser')).toBeInTheDocument();
    expect(screen.getByText('Editar perfil')).toBeInTheDocument();
    expect(screen.getByText('📊 Estadísticas')).toBeInTheDocument();
  });

  it('renders restricted access error when profile fetch fails with 403', async () => {
    (globalThis.fetch as any).mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Este perfil es privado.' }),
      })
    );

    renderProfile('/profile/999');

    await waitFor(() => {
      expect(screen.getByText('Acceso restringido')).toBeInTheDocument();
    });
    expect(screen.getByText('Este perfil es privado.')).toBeInTheDocument();
  });
});
