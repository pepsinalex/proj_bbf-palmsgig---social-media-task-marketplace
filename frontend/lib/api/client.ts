import axios from 'axios';
import type { ApiError, ApiResponse } from '../types/api';

// API configuration
const API_BASE_URL =
  typeof window !== 'undefined' && window.location
    ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
    : 'http://localhost:8000/api/v1';

const TOKEN_KEY = 'palmsgig_access_token';
const REFRESH_TOKEN_KEY = 'palmsgig_refresh_token';

// Token management utilities
export const tokenManager = {
  getAccessToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch (error) {
      console.error('Error getting access token:', error);
      return null;
    }
  },

  setAccessToken: (token: string): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch (error) {
      console.error('Error setting access token:', error);
    }
  },

  getRefreshToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return localStorage.getItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error getting refresh token:', error);
      return null;
    }
  },

  setRefreshToken: (token: string): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } catch (error) {
      console.error('Error setting refresh token:', error);
    }
  },

  clearTokens: (): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing tokens:', error);
    }
  },
};

// Custom error class for API errors
export class ApiClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

// Request configuration interface
interface RequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: unknown;
  requiresAuth?: boolean;
}

// Flag to prevent multiple concurrent refresh attempts
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

// Subscribe to token refresh
const subscribeTokenRefresh = (callback: (token: string) => void): void => {
  refreshSubscribers.push(callback);
};

// Notify subscribers when token is refreshed
const onTokenRefreshed = (token: string): void => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

// Refresh access token
const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = tokenManager.getRefreshToken();
  if (!refreshToken) {
    throw new ApiClientError('No refresh token available', 401, 'NO_REFRESH_TOKEN');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    });

    if (!response.ok) {
      throw new ApiClientError('Failed to refresh token', response.status, 'REFRESH_FAILED');
    }

    const data = (await response.json()) as ApiResponse<{
      accessToken: string;
      refreshToken: string;
    }>;
    const { accessToken, refreshToken: newRefreshToken } = data.data;

    tokenManager.setAccessToken(accessToken);
    tokenManager.setRefreshToken(newRefreshToken);

    return accessToken;
  } catch (error) {
    tokenManager.clearTokens();
    throw error;
  }
};

// Main API client function
async function makeRequest<T>(
  endpoint: string,
  config: RequestConfig
): Promise<ApiResponse<T>> {
  const { method, headers = {}, body, requiresAuth = true } = config;

  // Build headers
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Add authorization header if required
  if (requiresAuth) {
    const token = tokenManager.getAccessToken();
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  // Build request options
  const requestOptions: RequestInit = {
    method,
    headers: requestHeaders,
    credentials: 'include',
  };

  if (body && method !== 'GET') {
    requestOptions.body = JSON.stringify(body);
  }

  try {
    // Make the request
    const response = await fetch(`${API_BASE_URL}${endpoint}`, requestOptions);

    // Handle unauthorized - attempt token refresh
    if (response.status === 401 && requiresAuth) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const newToken = await refreshAccessToken();
          isRefreshing = false;
          onTokenRefreshed(newToken);

          // Retry original request with new token
          requestHeaders['Authorization'] = `Bearer ${newToken}`;
          const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...requestOptions,
            headers: requestHeaders,
          });

          if (!retryResponse.ok) {
            const errorData = (await retryResponse.json()) as ApiError;
            // Extract FastAPI error message from detail field
            if (axios.isAxiosError(errorData) && errorData.response?.data?.detail) {
              throw new ApiClientError(
                errorData.response.data.detail,
                retryResponse.status,
                'API_ERROR'
              );
            }
            throw new ApiClientError(
              errorData.error.message,
              retryResponse.status,
              errorData.error.code,
              errorData.error.details
            );
          }

          return (await retryResponse.json()) as ApiResponse<T>;
        } catch (error) {
          isRefreshing = false;
          refreshSubscribers = [];
          throw error;
        }
      } else {
        // Wait for the ongoing refresh to complete
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(async (token: string) => {
            try {
              requestHeaders['Authorization'] = `Bearer ${token}`;
              const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...requestOptions,
                headers: requestHeaders,
              });

              if (!retryResponse.ok) {
                const errorData = (await retryResponse.json()) as ApiError;
                // Extract FastAPI error message from detail field
                if (axios.isAxiosError(errorData) && errorData.response?.data?.detail) {
                  throw new ApiClientError(
                    errorData.response.data.detail,
                    retryResponse.status,
                    'API_ERROR'
                  );
                }
                throw new ApiClientError(
                  errorData.error.message,
                  retryResponse.status,
                  errorData.error.code,
                  errorData.error.details
                );
              }

              resolve((await retryResponse.json()) as ApiResponse<T>);
            } catch (error) {
              reject(error);
            }
          });
        });
      }
    }

    // Handle other error responses
    if (!response.ok) {
      let errorData: ApiError | { detail?: string };
      try {
        errorData = (await response.json()) as ApiError | { detail?: string };
      } catch {
        throw new ApiClientError(
          'An unexpected error occurred',
          response.status,
          'UNKNOWN_ERROR'
        );
      }

      // Extract FastAPI error message from detail field
      if ('detail' in errorData && typeof errorData.detail === 'string') {
        throw new ApiClientError(errorData.detail, response.status, 'API_ERROR');
      }

      if ('error' in errorData) {
        throw new ApiClientError(
          errorData.error.message,
          response.status,
          errorData.error.code,
          errorData.error.details
        );
      }

      throw new ApiClientError(
        'An unexpected error occurred',
        response.status,
        'UNKNOWN_ERROR'
      );
    }

    // Parse and return successful response
    return (await response.json()) as ApiResponse<T>;
  } catch (error) {
    // Handle network errors and Axios errors
    if (error instanceof ApiClientError) {
      throw error;
    }

    // Extract FastAPI error message from detail field for Axios errors
    if (axios.isAxiosError(error) && error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }

    console.error('API request failed:', error);
    throw new ApiClientError(
      'Network error: Failed to connect to the server',
      0,
      'NETWORK_ERROR'
    );
  }
}

// Exported API client methods
export const apiClient = {
  get: <T>(endpoint: string, requiresAuth = true): Promise<ApiResponse<T>> =>
    makeRequest<T>(endpoint, { method: 'GET', requiresAuth }),

  post: <T>(endpoint: string, data?: unknown, requiresAuth = true): Promise<ApiResponse<T>> =>
    makeRequest<T>(endpoint, { method: 'POST', body: data, requiresAuth }),

  put: <T>(endpoint: string, data?: unknown, requiresAuth = true): Promise<ApiResponse<T>> =>
    makeRequest<T>(endpoint, { method: 'PUT', body: data, requiresAuth }),

  patch: <T>(endpoint: string, data?: unknown, requiresAuth = true): Promise<ApiResponse<T>> =>
    makeRequest<T>(endpoint, { method: 'PATCH', body: data, requiresAuth }),

  delete: <T>(endpoint: string, requiresAuth = true): Promise<ApiResponse<T>> =>
    makeRequest<T>(endpoint, { method: 'DELETE', requiresAuth }),
};

// Export API base URL for use in other modules
export { API_BASE_URL };
