'use client';

import { useCallback, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  useCurrentProfile,
  profileKeys,
} from '@/hooks/use-profile';
import { completeOnboarding } from '@/lib/api/profile';
import type { User, UserRole } from '@/lib/types/api';

// Window (ms) within which a fresh account is treated as a "first login"
const FIRST_LOGIN_WINDOW_MS = 24 * 60 * 60 * 1000;

export interface UseOnboardingReturn {
  user: User | undefined;
  role: User['role'] | undefined;
  isOnboarded: boolean;
  isFirstLogin: boolean;
  shouldShowWelcome: boolean;
  isLoading: boolean;
  isCompleting: boolean;
  error: unknown;
  markOnboardingComplete: () => Promise<User | undefined>;
}

export function useOnboarding(): UseOnboardingReturn {
  const queryClient = useQueryClient();
  const { data: user, isLoading, error } = useCurrentProfile();

  const completeMutation = useMutation({
    mutationFn: async () => {
      const response = await completeOnboarding();
      return response.data;
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData<User>(profileKeys.current(), (oldData) => {
        if (!oldData) return updatedUser;
        return { ...oldData, ...updatedUser, is_onboarded: true };
      });
      queryClient.invalidateQueries({ queryKey: profileKeys.current() });
    },
    onError: (mutationError) => {
      console.error('Failed to mark onboarding complete:', mutationError);
    },
  });

  const isFirstLogin = useMemo(() => {
    if (!user?.created_at) return false;
    const createdAt = new Date(user.created_at).getTime();
    if (Number.isNaN(createdAt)) return false;
    return Date.now() - createdAt <= FIRST_LOGIN_WINDOW_MS;
  }, [user?.created_at]);

  const isOnboarded = Boolean(user?.is_onboarded);
  const shouldShowWelcome = Boolean(user) && !isOnboarded && isFirstLogin;

  const markOnboardingComplete = useCallback(async () => {
    if (!user || user.is_onboarded) {
      return user;
    }
    return completeMutation.mutateAsync();
  }, [completeMutation, user]);

  return {
    user,
    role: user?.role,
    isOnboarded,
    isFirstLogin,
    shouldShowWelcome,
    isLoading,
    isCompleting: completeMutation.isPending,
    error,
    markOnboardingComplete,
  };
}

export type OnboardingUserRole = UserRole;
