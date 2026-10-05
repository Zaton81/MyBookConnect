export type ClubRole = 'ADMIN' | 'MODERATOR' | 'MEMBER';
export type MemberStatus = 'ACTIVE' | 'PENDING' | 'BANNED';
export type ReadingPlanStatus = 'CURRENT' | 'UPCOMING' | 'FINISHED';

export interface ClubMember {
  id: number;
  club: number;
  user: {
    id: number;
    username: string;
    avatar_url?: string | null;
  };
  role: ClubRole;
  status: MemberStatus;
  joined_at: string;
}

export interface ClubBook {
  id: number;
  club: number;
  book: {
    id: number;
    title: string;
    author_name?: string;
    cover_image_url?: string | null;
    average_rating?: number | null;
  };
  status: ReadingPlanStatus;
  start_date?: string | null;
  end_date?: string | null;
  target_milestones?: string;
  created_at: string;
}

export interface ClubDiscussionComment {
  id: number;
  discussion: number;
  author: {
    id: number;
    username: string;
    avatar_url?: string | null;
  };
  content: string;
  has_spoilers: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClubDiscussion {
  id: number;
  club: number;
  book?: {
    id: number;
    title: string;
    cover_image_url?: string | null;
  } | null;
  title: string;
  content: string;
  author: {
    id: number;
    username: string;
    avatar_url?: string | null;
  };
  is_pinned: boolean;
  has_spoilers: boolean;
  comments_count: number;
  recent_comments?: ClubDiscussionComment[];
  created_at: string;
  updated_at: string;
}

export interface ReadingClub {
  id: number;
  name: string;
  slug: string;
  description: string;
  cover_image?: string | null;
  creator: {
    id: number;
    username: string;
  };
  is_private: boolean;
  rules?: string;
  current_book?: {
    id: number;
    title: string;
    author_name?: string;
    cover_image_url?: string | null;
    average_rating?: number | null;
  } | null;
  members_count: number;
  is_member?: boolean;
  membership?: {
    role: ClubRole;
    status: MemberStatus;
    joined_at: string;
  } | null;
  reading_plan?: ClubBook[];
  created_at: string;
  updated_at?: string;
}
