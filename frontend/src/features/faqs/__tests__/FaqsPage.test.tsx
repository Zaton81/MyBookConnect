import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FaqsPage } from '../pages/FaqsPage';

describe('FaqsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
  });

  const mockFaqs = [
    {
      id: 1,
      question: '¿Cómo funciona el intercambio de libros?',
      answer: 'Puedes solicitar libros a otros usuarios acordando el punto de encuentro o envío.',
      category: 'books',
      order: 1,
      created_at: '2026-10-01T12:00:00Z',
    },
    {
      id: 2,
      question: '¿Cómo puedo verificar mi perfil de autor?',
      answer: 'Debes dirigirte a la sección de solicitud de autor y aportar un documento o enlace oficial.',
      category: 'authors',
      order: 2,
      created_at: '2026-10-02T12:00:00Z',
    },
    {
      id: 3,
      question: '¿Es gratuito registrarse en MyBookConnect?',
      answer: 'Sí, registrarse y formar parte de la comunidad es totalmente gratuito.',
      category: 'general',
      order: 3,
      created_at: '2026-10-03T12:00:00Z',
    },
  ];

  const renderFaqsPage = () => {
    return render(
      <MemoryRouter>
        <FaqsPage />
      </MemoryRouter>
    );
  };

  it('renders loading state initially', () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => new Promise(() => {})
    );
    renderFaqsPage();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders FAQ list with categories when fetch succeeds', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFaqs,
    });

    renderFaqsPage();

    await waitFor(() => {
      expect(screen.getByText('¿Cómo funciona el intercambio de libros?')).toBeInTheDocument();
      expect(screen.getByText('¿Cómo puedo verificar mi perfil de autor?')).toBeInTheDocument();
      expect(screen.getByText('¿Es gratuito registrarse en MyBookConnect?')).toBeInTheDocument();
    });

    // Check categories buttons exist
    expect(screen.getByRole('button', { name: /Todas las preguntas/i })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Autores y Perfiles/i }).length).toBeGreaterThanOrEqual(1);
  });

  it('toggles accordion items and controls aria-expanded attributes', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFaqs,
    });

    renderFaqsPage();

    await waitFor(() => {
      expect(screen.getByText('¿Cómo funciona el intercambio de libros?')).toBeInTheDocument();
    });

    const firstQuestionBtn = screen.getByRole('button', {
      name: /¿Cómo funciona el intercambio de libros\?/i,
    });
    // First question is open by default
    expect(firstQuestionBtn).toHaveAttribute('aria-expanded', 'true');

    // Click to collapse
    fireEvent.click(firstQuestionBtn);
    expect(firstQuestionBtn).toHaveAttribute('aria-expanded', 'false');

    // Click to expand again
    fireEvent.click(firstQuestionBtn);
    expect(firstQuestionBtn).toHaveAttribute('aria-expanded', 'true');
  });

  it('filters FAQs using search query', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFaqs,
    });

    renderFaqsPage();

    await waitFor(() => {
      expect(screen.getByText('¿Cómo funciona el intercambio de libros?')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Busca por palabra clave/i);
    fireEvent.change(searchInput, { target: { value: 'verificar' } });

    expect(screen.getByText('¿Cómo puedo verificar mi perfil de autor?')).toBeInTheDocument();
    expect(screen.queryByText('¿Cómo funciona el intercambio de libros?')).not.toBeInTheDocument();
  });

  it('filters FAQs by clicking category button', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFaqs,
    });

    renderFaqsPage();

    await waitFor(() => {
      expect(screen.getByText('¿Cómo funciona el intercambio de libros?')).toBeInTheDocument();
    });

    // The filter buttons are at the top, select the one matching General
    const buttons = screen.getAllByRole('button');
    const generalBtn = buttons.find((b) => b.textContent?.trim() === 'General');
    expect(generalBtn).toBeDefined();
    if (generalBtn) {
      fireEvent.click(generalBtn);
    }

    expect(screen.getByText('¿Es gratuito registrarse en MyBookConnect?')).toBeInTheDocument();
    expect(screen.queryByText('¿Cómo funciona el intercambio de libros?')).not.toBeInTheDocument();
  });

  it('renders error message when fetch fails', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    renderFaqsPage();

    await waitFor(() => {
      expect(screen.getByText(/Error al cargar las preguntas frecuentes/i)).toBeInTheDocument();
    });
  });
});
