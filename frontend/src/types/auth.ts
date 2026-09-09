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
  is_following?: boolean;
  is_blocked?: boolean;
  am_i_blocked?: boolean;
  reviews_count?: number;
  books_read_count?: number;
  following_count?: number;
  followers_count?: number;
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