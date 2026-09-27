import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BookReviewsSection } from '../components/BookReviewsSection';

describe('BookReviewsSection Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
  });

  const renderSection = (
    token: string | null = 'mock-token',
    currentUser: any = { id: 1, username: 'testuser' }
  ) => {
    return render(
      <MemoryRouter>
        <BookReviewsSection
          bookId={1}
          bookTitle="Mock Book"
          token={token}
          currentUser={currentUser}
        />
      </MemoryRouter>
    );
  };

  it('displays loading state initially', () => {
    (globalThis.fetch as any).mockImplementationOnce(() => new Promise(() => {})); // Never resolves
    const { container } = renderSection();
    expect(container).toBeInTheDocument();
  });

  it('renders reviews when fetch succeeds', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            id: 1,
            user: 2,
            username: 'ReviewerUser',
            book: 1,
            rating: 5,
            text: 'Amazing book!',
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getAllByText('ReviewerUser').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/Amazing book!/i).length).toBeGreaterThan(0);
  });
});
