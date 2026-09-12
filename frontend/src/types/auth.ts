export interface User {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  email: string;
  bio?: string;
  avatar?: string;
  birth_date?: string;
  location?: string;
  privacy_level: 'public' | 'friends' | 'private';
  show_email?: boolean;
  show_birth_date?: boolean;
  show_location?: boolean;
  show_bio?: boolean;
  following?: number[];
  followers?: number[];
  is_editor?: boolean;
  role?: 'USER' | 'EDITOR' | 'MODERATOR' | 'ADMIN';
  is_staff?: boolean;
  is_superuser?: boolean;
  is_following?: boolean;
  is_blocked?: boolean;
  am_i_blocked?: boolean;
  reviews_count?: number;
  books_read_count?: number;
  following_count?: number;
  followers_count?: number;
}

export interface Report {
  id: number;
  reporter: number;
  reporter_username: string;
  target_type: 'user' | 'review' | 'comment' | 'message';
  object_id: number;
  reason: string;
  reason_display: string;
  description?: string;
  status: 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED' | 'REJECTED';
  status_display: string;
  action_taken?: string;
  resolution_notes?: string;
  resolved_by?: number | null;
  resolved_by_username?: string | null;
  target_preview?: Record<string, any>;
  created_at: string;
  resolved_at?: string | null;
}

export interface AuditLog {
  id: number;
  actor: number | null;
  actor_username: string;
  action: string;
  action_display: string;
  target_type: string;
  object_id: number | null;
  target_repr: string;
  ip_address: string | null;
  user_agent?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken?: string | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  bio?: string;
}