import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Login } from '../pages/Login';
import { useAuthStore } from '../../../store/auth';

// Mock the auth store
vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Component', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => {
      // Mock the state selector
      return selector({ login: mockLogin });
    });
  });

  const renderLogin = () => {
    return render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
  };

  it('renders login form correctly', () => {
    renderLogin();
    expect(screen.getByRole('heading', { name: /inicia sesión/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    renderLogin();
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      // It depends on the zod schema validation messages, assume general ones
      expect(screen.getAllByText(/requerido|obligatorio|min/i).length).toBeGreaterThan(0);
    });
  });

  it('calls login on successful submission', async () => {
    renderLogin();
    const emailInput = screen.getByLabelText(/correo electrónico/i);
    const passwordInput = screen.getByLabelText(/contraseña/i);
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } });

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'Password123!');
      expect(mockNavigate).toHaveBeenCalledWith('/home');
    });
  });

  it('displays error message when login fails', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Credenciales inválidas'));
    renderLogin();

    const emailInput = screen.getByLabelText(/correo electrónico/i);
    const passwordInput = screen.getByLabelText(/contraseña/i);
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i });

    fireEvent.change(emailInput, { target: { value: 'wrong@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpass' } });

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Credenciales inválidas')).toBeInTheDocument();
    });
  });
});
