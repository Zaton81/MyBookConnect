import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BetaFeedbackModal } from '../BetaFeedbackModal';
import { useAuthStore } from '../../../store/auth';

describe('BetaFeedbackModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      token: 'fake-jwt-token',
      user: { id: 1, username: 'testuser', email: 'test@example.com', privacy_level: 'public' },
      isAuthenticated: true,
    });
  });

  it('no renderiza nada cuando isOpen es false', () => {
    const { container } = render(<BetaFeedbackModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renderiza título, 7 categorías y campos del formulario cuando isOpen es true', () => {
    render(<BetaFeedbackModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Feedback de Beta Cerrada')).toBeInTheDocument();
    expect(screen.getByLabelText(/Tipo de observación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Resumen breve/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Detalles \/ Pasos para reproducir/i)).toBeInTheDocument();

    // Comprobar presencia de opciones
    expect(screen.getByText(/Error o fallo técnico \(Bug\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Experiencia confusa o poco clara \(UX\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Funcionalidad ausente o sugerencia/i)).toBeInTheDocument();
    expect(screen.getByText(/Lentitud o problema de rendimiento/i)).toBeInTheDocument();
    expect(screen.getByText(/Inquietud sobre privacidad o datos/i)).toBeInTheDocument();
    expect(screen.getByText(/Calidad de las recomendaciones/i)).toBeInTheDocument();
    expect(screen.getByText(/Impresión u opinión general/i)).toBeInTheDocument();
  });

  it('invoca onClose al hacer clic en el botón Cancelar o cerrar', async () => {
    const handleClose = vi.fn();
    render(<BetaFeedbackModal isOpen={true} onClose={handleClose} />);

    const cancelBtn = screen.getByRole('button', { name: /Cancelar/i });
    fireEvent.click(cancelBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);

    const closeBtn = screen.getByRole('button', { name: /Cerrar modal/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(2);
  });

  it('envía el feedback correctamente y muestra confirmación de éxito', async () => {
    const user = userEvent.setup();
    const handleSubmitted = vi.fn();

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ id: 42, title: 'Prueba de feedback' }),
      })
    );

    render(<BetaFeedbackModal isOpen={true} onClose={vi.fn()} onSubmitted={handleSubmitted} />);

    const titleInput = screen.getByLabelText(/Resumen breve/i);
    const descInput = screen.getByLabelText(/Detalles \/ Pasos para reproducir/i);
    const submitBtn = screen.getByRole('button', { name: /Enviar Feedback/i });

    await user.type(titleInput, 'Error en filtrado');
    await user.type(descInput, 'Al pulsar el botón no se actualiza la lista.');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Tu feedback ha sido registrado para el equipo/i)
      ).toBeInTheDocument();
    });

    expect(handleSubmitted).toHaveBeenCalledTimes(1);
    expect(window.fetch).toHaveBeenCalledTimes(1);
  });
});
