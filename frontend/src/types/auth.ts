export interface User {
  id: number;
  username: string;
  email: string;
  bio?: string;
  avatar?: string;
  is_private: boolean;
}

export interface AuthState {
  user: User | null;
  token: string | null;
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