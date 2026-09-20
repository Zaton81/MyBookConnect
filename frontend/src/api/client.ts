import { useAuthStore } from '../store/auth';

export const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const { refreshToken, logout } = useAuthStore.getState();
      if (!refreshToken) {
        logout();
        return null;
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) {
        logout();
        return null;
      }

      const data = await response.json();
      const newAccessToken = data.access;
      const newRefreshToken = data.refresh || refreshToken;

      useAuthStore.setState({
        token: newAccessToken,
        refreshToken: newRefreshToken,
        isAuthenticated: true,
      });

      return newAccessToken;
    } catch {
      useAuthStore.getState().logout();
      return null;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export interface ApiErrorData {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface ApiErrorResponse {
  error?: ApiErrorData;
  detail?: string;
  [key: string]: any;
}

export class ApiError extends Error {
  public code: string;
  public status: number;
  public details?: Record<string, any>;

  constructor(
    message: string,
    code: string = 'ERROR',
    status: number = 400,
    details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export interface RequestOptions extends RequestInit {
  requireAuth?: boolean;
  idempotencyKey?: string;
}

export async function apiClient<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { requireAuth = true, idempotencyKey, headers: customHeaders, ...restOptions } = options;

  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers: Record<string, string> = {
    ...(customHeaders as Record<string, string>),
  };

  // No sobrescribir Content-Type si el body es FormData
  if (!(restOptions.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  if (requireAuth) {
    const token = useAuthStore.getState().token;
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  let response = await fetch(url, {
    ...restOptions,
    headers,
  });

  // Si recibimos 401 Unauthorized y la petición requería auth, intentamos refrescar el token
  if (response.status === 401 && requireAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(url, {
        ...restOptions,
        headers,
      });
    }
  }

  if (!response.ok) {
    let errorDetail = `Error ${response.status}: ${response.statusText}`;
    let errorCode = 'ERROR';
    let errorDetails: Record<string, any> | undefined = undefined;

    try {
      const errorJson = await response.json();
      if (errorJson && typeof errorJson === 'object') {
        if (errorJson.error && typeof errorJson.error === 'object') {
          errorCode = errorJson.error.code || errorCode;
          errorDetail = errorJson.error.message || errorDetail;
          errorDetails = errorJson.error.details;
        } else if (errorJson.detail) {
          errorDetail = errorJson.detail;
        } else {
          const parts: string[] = [];
          for (const key of Object.keys(errorJson)) {
            const val = errorJson[key];
            if (Array.isArray(val)) parts.push(`${key}: ${val.join(', ')}`);
            else parts.push(`${key}: ${String(val)}`);
          }
          if (parts.length > 0) errorDetail = parts.join(' | ');
        }
      }
    } catch {
      // Ignorar error al parsear cuerpo no-JSON
    }
    throw new ApiError(errorDetail, errorCode, response.status, errorDetails);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  get: <T = any>(url: string, options?: RequestOptions) =>
    apiClient<T>(url, { ...options, method: 'GET' }),

  post: <T = any>(url: string, body?: any, options?: RequestOptions) =>
    apiClient<T>(url, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  patch: <T = any>(url: string, body?: any, options?: RequestOptions) =>
    apiClient<T>(url, {
      ...options,
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  delete: <T = any>(url: string, options?: RequestOptions) =>
    apiClient<T>(url, { ...options, method: 'DELETE' }),
};
