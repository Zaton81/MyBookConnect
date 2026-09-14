import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Friends } from '../pages/Friends';
import { useAuthStore } from '../../../store/auth';
import * as socialHooks from '../hooks/useSocialQuery';

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('../hooks/useSocialQuery', () => ({
  useFollowing: vi.fn(),
  useFollowers: vi.fn(),
}));

describe('Friends Component (Social Interactions)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => {
      return { token: 'mock-token', user: { id: 1, username: 'testuser' } };
    });
  });

  const renderFriends = () => {
    return render(
      <MemoryRouter>
        <Friends />
      </MemoryRouter>
    );
  };

  it('displays loading state initially', () => {
    vi.spyOn(socialHooks, 'useFollowing').mockReturnValue({ data: [], isLoading: true } as any);
    vi.spyOn(socialHooks, 'useFollowers').mockReturnValue({ data: [], isLoading: false } as any);
    
    const { container } = renderFriends();
    expect(container).toBeInTheDocument();
  });

  it('renders following and followers lists when data is loaded', () => {
    vi.spyOn(socialHooks, 'useFollowing').mockReturnValue({
      data: [{ id: 2, username: 'FollowedUser' }],
      isLoading: false
    } as any);

    vi.spyOn(socialHooks, 'useFollowers').mockReturnValue({
      data: [{ id: 3, username: 'FollowerUser' }],
      isLoading: false
    } as any);

    renderFriends();

    expect(screen.getByText('FollowedUser')).toBeInTheDocument();
    expect(screen.getByText('FollowerUser')).toBeInTheDocument();
  });
});
