import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BookMarketplaceModal, MarketplaceData } from '../components/BookMarketplaceModal';

const mockMarketplaceData: MarketplaceData = {
  book_id: 42,
  book_title: 'Memorias de Idhún: La Resistencia',
  author_name: 'Laura Gallego García',
  isbn: '9788467502695',
  publisher: {
    id: 1,
    name: 'Editorial Minotauro',
    slug: 'editorial-minotauro',
    website: 'https://minotauro.com',
    is_verified: true,
  },
  can_manage: true,
  disclosure: 'MyBookConnect apoya el comercio de proximidad y la transparencia comercial.',
  total_offers: 5,
  offers: [
    {
      id: 101,
      merchant_name: 'TodosTusLibros',
      merchant_type: 'indie_network',
      format: 'paperback',
      format_display: 'Libro Físico (Librerías de barrio)',
      url: 'https://www.todostuslibros.com/busqueda_libros?isbn=9788467502695',
      price: 19.95,
      currency: 'EUR',
      is_official: false,
      is_affiliate: false,
      badge: 'Librerías de Proximidad',
    },
    {
      id: 102,
      merchant_name: 'Casa del Libro',
      merchant_type: 'online_retailer',
      format: 'paperback',
      format_display: 'Libro Físico',
      url: 'https://www.casadellibro.com/libros-busqueda?q=9788467502695',
      price: 19.95,
      currency: 'EUR',
      is_official: false,
      is_affiliate: false,
    },
    {
      id: 103,
      merchant_name: 'Amazon Kindle',
      merchant_type: 'ebook_store',
      format: 'ebook',
      format_display: 'Ebook Digital (Kindle)',
      url: 'https://www.amazon.es/s?k=Memorias+de+Idhun&i=digital-text&tag=mybooksocial-21',
      price: 8.99,
      currency: 'EUR',
      is_official: false,
      is_affiliate: true,
    },
    {
      id: 104,
      merchant_name: 'Audible',
      merchant_type: 'audio_store',
      format: 'audiobook',
      format_display: 'Audiolibro (Audible)',
      url: 'https://www.amazon.es/s?k=Memorias+de+Idhun&i=audible&tag=mybooksocial-21',
      price: 14.95,
      currency: 'EUR',
      is_official: false,
      is_affiliate: true,
    },
    {
      id: 105,
      merchant_name: 'Web Oficial Laura Gallego',
      merchant_type: 'publisher_direct',
      format: 'paperback',
      format_display: 'Tienda Oficial del Autor',
      url: 'https://www.lauragallego.com/tienda',
      price: 21.0,
      currency: 'EUR',
      is_official: true,
      is_affiliate: false,
      is_custom: true,
    },
  ],
  by_format: {
    paperback: [],
    ebook: [],
    audiobook: [],
  },
  by_merchant_type: {
    indie: [],
    online: [],
    publisher: [],
  },
};

describe('BookMarketplaceModal Component (Sprint 19)', () => {
  const onCloseMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/marketplace/click/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'recorded' }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockMarketplaceData),
      } as Response);
    });
  });

  it('renders modal header, book title and initial multitienda offers', async () => {
    render(
      <BookMarketplaceModal
        isOpen={true}
        onClose={onCloseMock}
        bookId={42}
        bookTitle="Memorias de Idhún: La Resistencia"
        authorName="Laura Gallego García"
      />
    );

    // Esperar a que carguen las ofertas
    await waitFor(() => {
      expect(screen.getByText(/Dónde conseguir «Memorias de Idhún: La Resistencia»/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Laura Gallego García')).toBeInTheDocument();
    expect(screen.getByText('TodosTusLibros')).toBeInTheDocument();
    expect(screen.getByText('Casa del Libro')).toBeInTheDocument();
    expect(screen.getByText('Amazon Kindle')).toBeInTheDocument();
    expect(screen.getByText('Audible')).toBeInTheDocument();
    expect(screen.getByText('Web Oficial Laura Gallego')).toBeInTheDocument();
  });

  it('filters offers by format tabs correctly', async () => {
    render(
      <BookMarketplaceModal
        isOpen={true}
        onClose={onCloseMock}
        bookId={42}
        bookTitle="Memorias de Idhún: La Resistencia"
        authorName="Laura Gallego García"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('TodosTusLibros')).toBeInTheDocument();
    });

    // Cambiar a la pestaña "Librerías de Barrio"
    const indieTab = screen.getByRole('button', { name: /Librerías de Barrio/i });
    fireEvent.click(indieTab);

    // TodosTusLibros debe permanecer visible
    expect(screen.getByText('TodosTusLibros')).toBeInTheDocument();
    // Casa del Libro y Amazon Kindle no deben mostrarse en esta pestaña
    expect(screen.queryByText('Casa del Libro')).not.toBeInTheDocument();
    expect(screen.queryByText('Amazon Kindle')).not.toBeInTheDocument();

    // Cambiar a la pestaña "Ebook"
    const ebookTab = screen.getByRole('button', { name: /Ebook/i });
    fireEvent.click(ebookTab);

    expect(screen.getByText('Amazon Kindle')).toBeInTheDocument();
    expect(screen.queryByText('TodosTusLibros')).not.toBeInTheDocument();
  });

  it('verifies secure store link attributes and triggers telemetry on click', async () => {
    render(
      <BookMarketplaceModal
        isOpen={true}
        onClose={onCloseMock}
        bookId={42}
        bookTitle="Memorias de Idhún: La Resistencia"
        authorName="Laura Gallego García"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('TodosTusLibros')).toBeInTheDocument();
    });

    const storeLinks = screen.getAllByRole('link', { name: /Ver en tienda/i });
    expect(storeLinks.length).toBeGreaterThan(0);

    const firstLink = storeLinks[0];
    expect(firstLink).toHaveAttribute('target', '_blank');
    expect(firstLink).toHaveAttribute('rel', 'noopener noreferrer sponsored');

    // Pulsar en el enlace para registrar telemetría
    fireEvent.click(firstLink);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/marketplace/click/'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('allows author owner to open form to add official buy link', async () => {
    render(
      <BookMarketplaceModal
        isOpen={true}
        onClose={onCloseMock}
        bookId={42}
        bookTitle="Memorias de Idhún: La Resistencia"
        authorName="Laura Gallego García"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Añadir enlace oficial de compra o editorial como autor/i)).toBeInTheDocument();
    });

    const addBtn = screen.getByText(/Añadir enlace oficial de compra o editorial como autor/i);
    fireEvent.click(addBtn);

    expect(screen.getByText(/Publicar enlace comercial oficial/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Tienda Oficial, Editorial Planeta/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Guardar enlace oficial/i })).toBeInTheDocument();
  });

  it('closes modal when close button is clicked', async () => {
    render(
      <BookMarketplaceModal
        isOpen={true}
        onClose={onCloseMock}
        bookId={42}
        bookTitle="Memorias de Idhún: La Resistencia"
        authorName="Laura Gallego García"
      />
    );

    const closeBtn = screen.getByLabelText(/Cerrar modal/i);
    fireEvent.click(closeBtn);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});
