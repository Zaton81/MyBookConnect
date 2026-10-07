import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ReadingStats } from '../pages/ReadingStats';
import { useAuthStore } from '../../../store/auth';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

describe('ReadingStats Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'mock-token',
      user: { id: 1, username: 'tester', role: 'USER' },
    });
    globalThis.fetch = vi.fn();
  });

  const sampleStats = {
    total_books: 15,
    total_read: 12,
    currently_reading: 2,
    want_to_read: 1,
    abandoned: 0,
    total_pages_read: 4200,
    average_rating: 4.5,
    ratings_distribution: { '5': 6, '4': 4, '3': 2, '2': 0, '1': 0 },
    top_genres: [
      { name: 'Ciencia Ficción', count: 6, percentage: 50.0 },
      { name: 'Fantasía', count: 4, percentage: 33.3 },
    ],
    top_authors: [
      { id: 1, name: 'Isaac Asimov', count: 4 },
      { id: 2, name: 'Ursula K. Le Guin', count: 3 },
    ],
    books_this_year: 8,
    books_per_month: [
      { key: '2026-01', label: 'Ene 2026', count: 2, pages: 700 },
      { key: '2026-02', label: 'Feb 2026', count: 3, pages: 1100 },
      { key: '2026-03', label: 'Mar 2026', count: 3, pages: 950 },
    ],
    selected_year: null,
    available_years: [2026, 2025],
    reading_pace: {
      avg_days_per_book: 5.5,
      fastest_book: {
        book_id: 10,
        title: 'Fundación e Imperio',
        author: 'Isaac Asimov',
        cover: null,
        days: 2,
        pages: 250,
      },
      slowest_book: {
        book_id: 20,
        title: 'Los Desposeídos',
        author: 'Ursula K. Le Guin',
        cover: null,
        days: 12,
        pages: 400,
      },
      avg_pages_per_day: 18.5,
      avg_pages_per_month: 350.0,
      highest_reading_month: {
        label: 'Feb 2026',
        count: 3,
      },
    },
    length_distribution: {
      short: { label: 'Cortos (< 200 pág)', count: 2, percentage: 16.7 },
      medium: { label: 'Medios (200 - 399 pág)', count: 6, percentage: 50.0 },
      long: { label: 'Largos (400 - 599 pág)', count: 3, percentage: 25.0 },
      epic: { label: 'Épicos (600+ pág)', count: 1, percentage: 8.3 },
      longest_book: {
        book_id: 99,
        title: 'Criptonomicón',
        author: 'Neal Stephenson',
        pages: 950,
        cover: null,
      },
      shortest_book: {
        book_id: 10,
        title: 'Fundación e Imperio',
        author: 'Isaac Asimov',
        pages: 250,
        cover: null,
      },
    },
    format_distribution: {
      physical_count: 8,
      physical_percentage: 66.7,
      digital_count: 4,
      digital_percentage: 33.3,
      owned_count: 10,
      owned_percentage: 83.3,
      borrowed_count: 2,
      borrowed_percentage: 16.7,
    },
    year_in_review: {
      year: 2026,
      total_books: 8,
      total_pages: 2750,
      highest_rated_book: {
        book_id: 10,
        title: 'Fundación e Imperio',
        author: 'Isaac Asimov',
        rating: 5,
        cover: null,
      },
      favorite_genre: 'Ciencia Ficción',
      favorite_author: 'Isaac Asimov',
      comparison_previous_year: {
        previous_year: 2025,
        previous_year_books: 4,
        previous_year_pages: 1450,
        books_difference: 4,
        books_percentage_change: 100.0,
      },
    },
  };

  it('renders header, year selector pills, and overview tab metrics correctly', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleStats,
    });

    render(
      <MemoryRouter>
        <ReadingStats />
      </MemoryRouter>
    );

    // Esperar a que se carguen las estadísticas
    await waitFor(() => {
      expect(screen.getByText('Mis Estadísticas de Lectura')).toBeInTheDocument();
    });

    // Píldoras de selector de año
    expect(screen.getByRole('button', { name: 'Histórico' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2026' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2025' })).toBeInTheDocument();

    // KPIs principales
    expect(screen.getByText('12')).toBeInTheDocument(); // Leídos
    expect(screen.getByText('4.5')).toBeInTheDocument(); // Nota Media
    expect(screen.getByText(/4[.,]?200|4200/)).toBeInTheDocument(); // Páginas
    expect(screen.getByText('5.5d')).toBeInTheDocument(); // Ritmo Media/Libro

    // Pestañas WAI-ARIA
    expect(screen.getByRole('tab', { name: /Resumen General/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Ritmo & Velocidad/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Longitud & Formatos/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Memoria Anual/i })).toBeInTheDocument();
  });

  it('switches to pace tab and displays speed metrics and extreme books', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleStats,
    });

    render(
      <MemoryRouter>
        <ReadingStats />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Mis Estadísticas de Lectura')).toBeInTheDocument();
    });

    // Cambiar a la pestaña "Ritmo & Velocidad"
    const paceTab = screen.getByRole('tab', { name: /Ritmo & Velocidad/i });
    fireEvent.click(paceTab);

    await waitFor(() => {
      expect(screen.getByText('Duración Media por Libro')).toBeInTheDocument();
      expect(screen.getByText('5.5 días')).toBeInTheDocument();
      expect(screen.getByText('Velocidad de Páginas')).toBeInTheDocument();
      expect(screen.getByText('Lectura más veloz')).toBeInTheDocument();
      expect(screen.getAllByText('Fundación e Imperio').length).toBeGreaterThan(0);
      expect(screen.getByText('Terminado en 2 días')).toBeInTheDocument();
      expect(screen.getByText('Lectura más pausada y reposada')).toBeInTheDocument();
      expect(screen.getByText('Los Desposeídos')).toBeInTheDocument();
    });
  });

  it('switches to length tab and displays length tiers and reading formats', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleStats,
    });

    render(
      <MemoryRouter>
        <ReadingStats />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Mis Estadísticas de Lectura')).toBeInTheDocument();
    });

    // Cambiar a "Longitud & Formatos"
    const lengthTab = screen.getByRole('tab', { name: /Longitud & Formatos/i });
    fireEvent.click(lengthTab);

    await waitFor(() => {
      expect(screen.getByText('Distribución por Longitud')).toBeInTheDocument();
      expect(screen.getByText('Cortos (< 200 pág)')).toBeInTheDocument();
      expect(screen.getByText('Medios (200 - 399 pág)')).toBeInTheDocument();
      expect(screen.getByText('Largos (400 - 599 pág)')).toBeInTheDocument();
      expect(screen.getByText('Épicos (600+ pág)')).toBeInTheDocument();
      expect(screen.getByText('Libro más extenso')).toBeInTheDocument();
      expect(screen.getByText('Criptonomicón')).toBeInTheDocument();
      expect(screen.getByText('Formato de Lectura')).toBeInTheDocument();
      expect(screen.getByText('Estado de Posesión')).toBeInTheDocument();
    });
  });

  it('switches to review tab and displays year in review insights and year-over-year comparison', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleStats,
    });

    render(
      <MemoryRouter>
        <ReadingStats />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Mis Estadísticas de Lectura')).toBeInTheDocument();
    });

    // Cambiar a "Memoria Anual"
    const reviewTab = screen.getByRole('tab', { name: /Memoria Anual/i });
    fireEvent.click(reviewTab);

    await waitFor(() => {
      expect(screen.getByText('Año 2026 en Resumen')).toBeInTheDocument();
      expect(screen.getByText('Tu libro mejor puntuado del año')).toBeInTheDocument();
      expect(screen.getByText('Comparativa frente a 2025')).toBeInTheDocument();
      expect(screen.getByText('+4 libros')).toBeInTheDocument();
    });
  });
});
