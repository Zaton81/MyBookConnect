import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SocialShareModal, SocialShareResponse } from '../components/SocialShareModal';

describe('SocialShareModal Component (Sprint 16)', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  const mockBookData: SocialShareResponse = {
    share_type: 'book',
    title: 'Cien Años de Soledad',
    description: '¡Acabo de descubrir Cien Años de Soledad por Gabriel García Márquez en @MyBookConnect! 📖✨',
    canonical_url: 'http://localhost:3000/books/1',
    hashtags: ['#MyBookConnect', '#CienAñosDeSoledad', '#LibrosRecomendados'],
    share_text: '¡Acabo de descubrir Cien Años de Soledad por Gabriel García Márquez en @MyBookConnect! 📖✨ http://localhost:3000/books/1',
    share_urls: {
      twitter: 'https://twitter.com/intent/tweet?text=test',
      whatsapp: 'https://api.whatsapp.com/send?text=test',
      telegram: 'https://t.me/share/url?url=test',
      linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=test',
      facebook: 'https://www.facebook.com/sharer/sharer.php?u=test',
      email: 'mailto:?subject=test',
    },
    card_data: {
      title: 'Cien Años de Soledad',
      subtitle: 'por Gabriel García Márquez',
      stat_highlight: '4.8 ★',
      stat_label: 'Valoración media',
      badge_or_icon: '📖',
      image_url: null,
      theme_color: 'amber',
      site_name: 'MyBookConnect',
    },
  };

  const mockStatsData: SocialShareResponse = {
    share_type: 'reading_stats',
    title: 'Mi Memoria Lectora 2026',
    description: 'En 2026 he completado 32 libros y 11.200 páginas en @MyBookConnect. 📊✨',
    canonical_url: 'http://localhost:3000/statistics?user_id=1&year=2026',
    hashtags: ['#MyBookConnect', '#MemoriaLectora', '#ReadingGoals'],
    share_text: 'En 2026 he completado 32 libros y 11.200 páginas en @MyBookConnect. 📊✨ http://localhost:3000/statistics',
    share_urls: {
      twitter: 'https://twitter.com/intent/tweet?text=test',
      whatsapp: 'https://api.whatsapp.com/send?text=test',
      telegram: 'https://t.me/share/url?url=test',
      linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=test',
      facebook: 'https://www.facebook.com/sharer/sharer.php?u=test',
      email: 'mailto:?subject=test',
    },
    card_data: {
      title: 'Mi Memoria Lectora 2026',
      subtitle: '32 libros leídos • 11.200 páginas',
      stat_highlight: '32 libros',
      stat_label: 'Completados este año',
      badge_or_icon: '📊',
      image_url: null,
      theme_color: 'teal',
      site_name: 'MyBookConnect',
    },
  };

  it('renders modal with book details and social buttons when open', () => {
    render(
      <SocialShareModal
        isOpen={true}
        onClose={mockOnClose}
        shareType="book"
        objectId={1}
        initialData={mockBookData}
      />
    );

    // Header y título
    expect(screen.getByText('Compartir en Redes Sociales')).toBeInTheDocument();
    expect(screen.getByText('Cien Años de Soledad')).toBeInTheDocument();
    expect(screen.getByText('por Gabriel García Márquez')).toBeInTheDocument();
    expect(screen.getByText('4.8 ★')).toBeInTheDocument();

    // Botones de 1 clic en redes sociales
    expect(screen.getByRole('button', { name: /X \(Twitter\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /WhatsApp/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Telegram/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /LinkedIn/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Facebook/i })).toBeInTheDocument();
  });

  it('renders annual reading stats review card preview properly', () => {
    render(
      <SocialShareModal
        isOpen={true}
        onClose={mockOnClose}
        shareType="reading_stats"
        year={2026}
        initialData={mockStatsData}
      />
    );

    expect(screen.getByText('Mi Memoria Lectora 2026')).toBeInTheDocument();
    expect(screen.getByText('32 libros leídos • 11.200 páginas')).toBeInTheDocument();
    expect(screen.getByText('32 libros')).toBeInTheDocument();
    expect(screen.getByText('Completados este año')).toBeInTheDocument();
  });

  it('copies link to clipboard when "Copiar enlace" button is clicked', async () => {
    render(
      <SocialShareModal
        isOpen={true}
        onClose={mockOnClose}
        shareType="book"
        objectId={1}
        initialData={mockBookData}
      />
    );

    const copyBtn = screen.getByRole('button', { name: /Copiar Enlace/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockBookData.canonical_url);
  });

  it('copies text with emojis when "Copiar Texto" button is clicked', async () => {
    render(
      <SocialShareModal
        isOpen={true}
        onClose={mockOnClose}
        shareType="reading_stats"
        year={2026}
        initialData={mockStatsData}
      />
    );

    const copyTextBtn = screen.getByRole('button', { name: /Copiar Texto/i });
    fireEvent.click(copyTextBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining(mockStatsData.share_text)
    );
  });
});
