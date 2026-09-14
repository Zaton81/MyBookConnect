import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Register } from '../pages/Register';
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

describe('Register Component', () => {
  const mockRegister = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector) => {
      // Mock the state selector
      return selector({ register: mockRegister });
    });
  });

  const renderRegister = () => {
    return render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    );
  };

  it('renders register form correctly', () => {
    renderRegister();
    expect(screen.getByRole('heading', { name: /crea tu cuenta/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/nombre de usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /registrarse/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    renderRegister();
    const submitButton = screen.getByRole('button', { name: /registrarse/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getAllByText(/requerido|obligatorio|min|caracteres/i).length).toBeGreaterThan(0);
    });
  });

  it('calls register on successful submission', async () => {
    renderRegister();
    const usernameInput = screen.getByLabelText(/nombre de usuario/i);
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/contraseña/i);
    const submitButton = screen.getByRole('button', { name: /registrarse/i });

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } });
    
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('testuser', 'test@example.com', 'Password123!');
      expect(mockNavigate).toHaveBeenCalledWith('/profile/edit');
    });
  });

  it('displays error message when registration fails', async () => {
    mockRegister.mockRejectedValueOnce(new Error('El usuario ya existe'));
    renderRegister();
    
    const usernameInput = screen.getByLabelText(/nombre de usuario/i);
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/contraseña/i);
    const submitButton = screen.getByRole('button', { name: /registrarse/i });

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } });
    
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('El usuario ya existe')).toBeInTheDocument();
    });
  });
});
