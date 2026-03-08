'use client';

import React, { createContext, useCallback, useEffect, useState } from 'react';
import { apiClient, tokenManager } from '../lib/api/client';
import type {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  ApiResponse,
} from '../lib/types/api';

// Authentication context state interface
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Authentication context methods interface
interface AuthContextValue extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

// Create the context with undefined as initial value
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// AuthProvider props
interface AuthProviderProps {
  children: React.ReactNode;
}

// Storage key for persisted user data
const USER_STORAGE_KEY = 'palmsgig_user';

// Helper function to safely store user data
const storeUser = (user: User | null): void => {
  if (typeof window === 'undefined') return;
  try {
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  } catch (error) {
    console.error('Error storing user data:', error);
  }
};

// Helper function to safely retrieve user data
const retrieveUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(USER_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as User;
    }
  } catch (error) {
    console.error('Error retrieving user data:', error);
  }
  return null;
};

// AuthProvider component
export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  // Initialize auth state from storage
  useEffect(() => {
    const initializeAuth = async () => {
      const token = tokenManager.getAccessToken();
      const storedUser = retrieveUser();

      if (token && storedUser) {
        // Validate token by fetching current user
        try {
          const response = await apiClient.get<User>('/auth/me');
          setState({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          storeUser(response.data);
        } catch (error) {
          console.error('Failed to validate token:', error);
          // Token is invalid, clear everything
          tokenManager.clearTokens();
          storeUser(null);
          setState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      } else {
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      }
    };

    initializeAuth();
  }, []);

  // Login function
  const login = useCallback(async (credentials: LoginRequest): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response: ApiResponse<AuthResponse> = await apiClient.post<AuthResponse>(
        '/auth/login',
        credentials,
        false
      );

      const { user, accessToken, refreshToken } = response.data;

      // Store tokens
      tokenManager.setAccessToken(accessToken);
      tokenManager.setRefreshToken(refreshToken);

      // Store user data
      storeUser(user);

      // Update state
      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Login failed. Please try again.';

      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });

      throw error;
    }
  }, []);

  // Register function
  const register = useCallback(async (data: RegisterRequest): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response: ApiResponse<AuthResponse> = await apiClient.post<AuthResponse>(
        '/auth/register',
        data,
        false
      );

      const { user, accessToken, refreshToken } = response.data;

      // Store tokens
      tokenManager.setAccessToken(accessToken);
      tokenManager.setRefreshToken(refreshToken);

      // Store user data
      storeUser(user);

      // Update state
      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Registration failed. Please try again.';

      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });

      throw error;
    }
  }, []);

  // Logout function
  const logout = useCallback(async (): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Call logout endpoint to invalidate tokens on server
      await apiClient.post('/auth/logout', {});
    } catch (error) {
      console.error('Logout request failed:', error);
      // Continue with local logout even if server request fails
    } finally {
      // Clear tokens and user data
      tokenManager.clearTokens();
      storeUser(null);

      // Update state
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  }, []);

  // Refresh user data
  const refreshUser = useCallback(async (): Promise<void> => {
    if (!state.isAuthenticated) {
      return;
    }

    try {
      const response = await apiClient.get<User>('/auth/me');
      setState((prev) => ({
        ...prev,
        user: response.data,
      }));
      storeUser(response.data);
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      // If refresh fails due to invalid token, logout
      await logout();
    }
  }, [state.isAuthenticated, logout]);

  // Clear error
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  // Context value
  const value: AuthContextValue = {
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    login,
    register,
    logout,
    refreshUser,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Export the context for use in custom hook
export { AuthContext };
