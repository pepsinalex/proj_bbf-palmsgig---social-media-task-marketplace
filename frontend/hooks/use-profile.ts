'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCurrentProfile,
  updateProfile,
  uploadProfilePicture,
  getProfileSettings,
  updateProfileSettings,
  getSocialAccounts,
  connectSocialAccount,
  disconnectSocialAccount,
  verifySocialAccount,
  refreshSocialAccount,
  getProfileById,
  getSocialAccountsByUserId,
  type UpdateProfileRequest,
  type UpdateSettingsRequest,
  type ConnectSocialAccountRequest,
  type ProfileSettings,
} from '@/lib/api/profile';
import type { User, SocialAccount } from '@/lib/types/api';

// Query keys
export const profileKeys = {
  all: ['profile'] as const,
  current: () => [...profileKeys.all, 'current'] as const,
  byId: (id: string) => [...profileKeys.all, 'detail', id] as const,
  settings: () => [...profileKeys.all, 'settings'] as const,
  socialAccounts: () => [...profileKeys.all, 'social-accounts'] as const,
  socialAccountsByUser: (userId: string) =>
    [...profileKeys.all, 'social-accounts', userId] as const,
};

// Hook to get current user profile
export function useCurrentProfile() {
  return useQuery({
    queryKey: profileKeys.current(),
    queryFn: async () => {
      const response = await getCurrentProfile();
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook to get profile by user ID
export function useProfileById(userId: string, enabled = true) {
  return useQuery({
    queryKey: profileKeys.byId(userId),
    queryFn: async () => {
      const response = await getProfileById(userId);
      return response.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

// Hook to update profile
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateProfileRequest) => {
      const response = await updateProfile(data);
      return response.data;
    },
    onSuccess: (updatedUser) => {
      // Update the current profile cache
      queryClient.setQueryData<User>(profileKeys.current(), updatedUser);

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.current() });
    },
    onError: (error) => {
      console.error('Failed to update profile:', error);
    },
  });
}

// Hook to upload profile picture
export function useUploadProfilePicture() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const response = await uploadProfilePicture(file);
      return response.data;
    },
    onSuccess: (data) => {
      // Update the profile with the new picture URL
      queryClient.setQueryData<User>(profileKeys.current(), (oldData) => {
        if (!oldData) return oldData;
        return {
          ...oldData,
          profilePicture: data.url,
        };
      });

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.current() });
    },
    onError: (error) => {
      console.error('Failed to upload profile picture:', error);
    },
  });
}

// Hook to get profile settings
export function useProfileSettings() {
  return useQuery({
    queryKey: profileKeys.settings(),
    queryFn: async () => {
      const response = await getProfileSettings();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

// Hook to update profile settings
export function useUpdateProfileSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateSettingsRequest) => {
      const response = await updateProfileSettings(data);
      return response.data;
    },
    onSuccess: (updatedSettings) => {
      // Update the settings cache
      queryClient.setQueryData<ProfileSettings>(profileKeys.settings(), updatedSettings);

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.settings() });
    },
    onError: (error) => {
      console.error('Failed to update profile settings:', error);
    },
  });
}

// Hook to get social accounts
export function useSocialAccounts() {
  return useQuery({
    queryKey: profileKeys.socialAccounts(),
    queryFn: async () => {
      const response = await getSocialAccounts();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

// Hook to get social accounts by user ID
export function useSocialAccountsByUserId(userId: string, enabled = true) {
  return useQuery({
    queryKey: profileKeys.socialAccountsByUser(userId),
    queryFn: async () => {
      const response = await getSocialAccountsByUserId(userId);
      return response.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

// Hook to connect social account
export function useConnectSocialAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConnectSocialAccountRequest) => {
      const response = await connectSocialAccount(data);
      return response.data;
    },
    onSuccess: (newAccount) => {
      // Update the social accounts cache
      queryClient.setQueryData<SocialAccount[]>(
        profileKeys.socialAccounts(),
        (oldData) => {
          if (!oldData) return [newAccount];
          return [...oldData, newAccount];
        }
      );

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.socialAccounts() });
      queryClient.invalidateQueries({ queryKey: profileKeys.current() });
    },
    onError: (error) => {
      console.error('Failed to connect social account:', error);
    },
  });
}

// Hook to disconnect social account
export function useDisconnectSocialAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId: string) => {
      const response = await disconnectSocialAccount(accountId);
      return { accountId, success: response.data.success };
    },
    onSuccess: ({ accountId }) => {
      // Remove the account from cache
      queryClient.setQueryData<SocialAccount[]>(
        profileKeys.socialAccounts(),
        (oldData) => {
          if (!oldData) return [];
          return oldData.filter((account) => account.id !== accountId);
        }
      );

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.socialAccounts() });
      queryClient.invalidateQueries({ queryKey: profileKeys.current() });
    },
    onError: (error) => {
      console.error('Failed to disconnect social account:', error);
    },
  });
}

// Hook to verify social account
export function useVerifySocialAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId: string) => {
      const response = await verifySocialAccount(accountId);
      return response.data;
    },
    onSuccess: (verifiedAccount) => {
      // Update the account in cache
      queryClient.setQueryData<SocialAccount[]>(
        profileKeys.socialAccounts(),
        (oldData) => {
          if (!oldData) return [verifiedAccount];
          return oldData.map((account) =>
            account.id === verifiedAccount.id ? verifiedAccount : account
          );
        }
      );

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.socialAccounts() });
    },
    onError: (error) => {
      console.error('Failed to verify social account:', error);
    },
  });
}

// Hook to refresh social account data
export function useRefreshSocialAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId: string) => {
      const response = await refreshSocialAccount(accountId);
      return response.data;
    },
    onSuccess: (refreshedAccount) => {
      // Update the account in cache
      queryClient.setQueryData<SocialAccount[]>(
        profileKeys.socialAccounts(),
        (oldData) => {
          if (!oldData) return [refreshedAccount];
          return oldData.map((account) =>
            account.id === refreshedAccount.id ? refreshedAccount : account
          );
        }
      );

      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: profileKeys.socialAccounts() });
    },
    onError: (error) => {
      console.error('Failed to refresh social account:', error);
    },
  });
}

// Combined hook for profile page
export function useProfile() {
  const profile = useCurrentProfile();
  const settings = useProfileSettings();
  const socialAccounts = useSocialAccounts();
  const updateProfileMutation = useUpdateProfile();
  const uploadPictureMutation = useUploadProfilePicture();
  const updateSettingsMutation = useUpdateProfileSettings();
  const connectAccountMutation = useConnectSocialAccount();
  const disconnectAccountMutation = useDisconnectSocialAccount();

  return {
    // Data
    profile: profile.data,
    settings: settings.data,
    socialAccounts: socialAccounts.data || [],

    // Loading states
    isLoadingProfile: profile.isLoading,
    isLoadingSettings: settings.isLoading,
    isLoadingSocialAccounts: socialAccounts.isLoading,
    isLoading: profile.isLoading || settings.isLoading || socialAccounts.isLoading,

    // Error states
    profileError: profile.error,
    settingsError: settings.error,
    socialAccountsError: socialAccounts.error,

    // Mutations
    updateProfile: updateProfileMutation.mutateAsync,
    uploadProfilePicture: uploadPictureMutation.mutateAsync,
    updateSettings: updateSettingsMutation.mutateAsync,
    connectSocialAccount: connectAccountMutation.mutateAsync,
    disconnectSocialAccount: disconnectAccountMutation.mutateAsync,

    // Mutation states
    isUpdatingProfile: updateProfileMutation.isPending,
    isUploadingPicture: uploadPictureMutation.isPending,
    isUpdatingSettings: updateSettingsMutation.isPending,
    isConnectingAccount: connectAccountMutation.isPending,
    isDisconnectingAccount: disconnectAccountMutation.isPending,

    // Refetch functions
    refetchProfile: profile.refetch,
    refetchSettings: settings.refetch,
    refetchSocialAccounts: socialAccounts.refetch,
  };
}
