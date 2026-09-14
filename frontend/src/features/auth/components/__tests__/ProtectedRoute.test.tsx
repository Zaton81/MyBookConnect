import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProtectedRoute } from '../ProtectedRoute';
import { useAuthStore } from '../../../../store/auth';

// Mock the auth store
vi.mock('../../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (ui: React.ReactNode, initialEntry = '/') => {
    return render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/" element={<div>Public Route</div>} />
          <Route path="/home" element={<div>Home Route</div>} />
          <Route path="/protected" element={ui} />
          <Route path="/guest-only" element={ui} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('redirects to "/" when user is NOT authenticated and accesses a protected route', () => {
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => selector({ isAuthenticated: false }));
    
    renderWithRouter(
      <ProtectedRoute requireAuth={true}>
        <div>Protected Content</div>
      </ProtectedRoute>,
      '/protected'
    );

    expect(screen.getByText('Public Route')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when user IS authenticated and accesses a protected route', () => {
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => selector({ isAuthenticated: true }));
    
    renderWithRouter(
      <ProtectedRoute requireAuth={true}>
        <div>Protected Content</div>
      </ProtectedRoute>,
      '/protected'
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to "/home" when user IS authenticated and accesses a guest-only route', () => {
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => selector({ isAuthenticated: true }));
    
    renderWithRouter(
      <ProtectedRoute requireAuth={false}>
        <div>Guest Content</div>
      </ProtectedRoute>,
      '/guest-only'
    );

    expect(screen.getByText('Home Route')).toBeInTheDocument();
    expect(screen.queryByText('Guest Content')).not.toBeInTheDocument();
  });

  it('renders children when user is NOT authenticated and accesses a guest-only route', () => {
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => selector({ isAuthenticated: false }));
    
    renderWithRouter(
      <ProtectedRoute requireAuth={false}>
        <div>Guest Content</div>
      </ProtectedRoute>,
      '/guest-only'
    );

    expect(screen.getByText('Guest Content')).toBeInTheDocument();
  });
});
