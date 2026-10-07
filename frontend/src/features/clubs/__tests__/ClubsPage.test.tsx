import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ClubsPage } from '../pages/ClubsPage';
import { clubService } from '../services/clubService';

vi.mock('../services/clubService', () => ({
  clubService: {
    getClubs: vi.fn(),
    createClub: vi.fn(),
  },
}));

const mockClubs = [
  {
    id: 1,
    name: 'Club de Ciencia Ficción',
    slug: 'club-de-ciencia-ficcion',
    description: 'Debatimos sobre viajes en el tiempo e IA.',
    creator: { id: 1, username: 'isaac_a' },
    is_private: false,
    members_count: 14,
    current_book: {
      id: 101,
      title: 'Fundación',
      author_name: 'Isaac Asimov',
      cover_image_url: null,
      average_rating: 4.8,
    },
    created_at: '2026-01-10T12:00:00Z',
  },
  {
    id: 2,
    name: 'Círculo de Poesía Oscura',
    slug: 'circulo-de-poesia-oscura',
    description: 'Poetas malditos y versos de medianoche.',
    creator: { id: 2, username: 'edgar_poe' },
    is_private: true,
    members_count: 5,
    current_book: null,
    created_at: '2026-02-15T12:00:00Z',
  },
];

describe('ClubsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(clubService.getClubs).mockReturnValue(new Promise(() => {}));

    render(
      <MemoryRouter>
        <ClubsPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('clubs-loading')).toBeInTheDocument();
  });

  it('renders club list with public and private badges', async () => {
    vi.mocked(clubService.getClubs).mockResolvedValue(mockClubs as any);

    render(
      <MemoryRouter>
        <ClubsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Club de Ciencia Ficción')).toBeInTheDocument();
      expect(screen.getByText('Círculo de Poesía Oscura')).toBeInTheDocument();
    });

    expect(screen.getByText('Público')).toBeInTheDocument();
    expect(screen.getByText('Privado')).toBeInTheDocument();
    expect(screen.getByText('Fundación')).toBeInTheDocument();
    expect(screen.getByText('Isaac Asimov')).toBeInTheDocument();
  });

  it('allows switching between tabs and calls getClubs with my_clubs=true', async () => {
    vi.mocked(clubService.getClubs).mockResolvedValue(mockClubs as any);

    render(
      <MemoryRouter>
        <ClubsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Club de Ciencia Ficción')).toBeInTheDocument();
    });

    const myClubsTab = screen.getByRole('tab', { name: /mis clubs/i });
    fireEvent.click(myClubsTab);

    expect(clubService.getClubs).toHaveBeenCalledWith({
      q: undefined,
      my_clubs: true,
    });
  });

  it('opens and closes create club modal properly', async () => {
    vi.mocked(clubService.getClubs).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ClubsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no se encontraron clubs de lectura/i)).toBeInTheDocument();
    });

    const openBtn = screen.getByRole('button', { name: /crear club/i });
    fireEvent.click(openBtn);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText(/nombre del club/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /cancelar/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
