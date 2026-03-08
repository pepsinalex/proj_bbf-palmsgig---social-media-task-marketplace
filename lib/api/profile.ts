import { apiClient } from './client';
import type { ApiResponse, User, SocialAccount } from '../types/api';

// Profile API types
export interface UpdateProfileRequest {
  fullName?: string;
  bio?: string;
  profilePicture?: string;
}

export interface UpdateSettingsRequest {
  emailNotifications?: boolean;
  taskNotifications?: boolean;
  marketingEmails?: boolean;
  twoFactorEnabled?: boolean;
}

export interface ConnectSocialAccountRequest {
  platform: 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube';
  username: string;
}

export interface ProfileSettings {
  emailNotifications: boolean;
  taskNotifications: boolean;
  marketingEmails: boolean;
  twoFactorEnabled: boolean;
}

// Get current user profile
export async function getCurrentProfile(): Promise<ApiResponse<User>> {
  return apiClient.get<User>('/users/me');
}

// Update user profile
export async function updateProfile(
  data: UpdateProfileRequest
): Promise<ApiResponse<User>> {
  return apiClient.patch<User>('/users/me', data);
}

// Upload profile picture
export async function uploadProfilePicture(file: File): Promise<ApiResponse<{ url: string }>> {
  const formData = new FormData();
  formData.append('file', file);

  // For file uploads, we need to override the Content-Type header
  const response = await fetch(
    `${typeof window !== 'undefined' && window.location
      ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
      : 'http://localhost:8000/api/v1'
    }/users/me/profile-picture`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('palmsgig_access_token')}`,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Failed to upload profile picture');
  }

  return response.json();
}

// Get profile settings
export async function getProfileSettings(): Promise<ApiResponse<ProfileSettings>> {
  return apiClient.get<ProfileSettings>('/users/me/settings');
}

// Update profile settings
export async function updateProfileSettings(
  data: UpdateSettingsRequest
): Promise<ApiResponse<ProfileSettings>> {
  return apiClient.patch<ProfileSettings>('/users/me/settings', data);
}

// Get user's social accounts
export async function getSocialAccounts(): Promise<ApiResponse<SocialAccount[]>> {
  return apiClient.get<SocialAccount[]>('/users/me/social-accounts');
}

// Connect a new social account
export async function connectSocialAccount(
  data: ConnectSocialAccountRequest
): Promise<ApiResponse<SocialAccount>> {
  return apiClient.post<SocialAccount>('/users/me/social-accounts', data);
}

// Disconnect a social account
export async function disconnectSocialAccount(
  accountId: string
): Promise<ApiResponse<{ success: boolean }>> {
  return apiClient.delete<{ success: boolean }>(`/users/me/social-accounts/${accountId}`);
}

// Verify a social account
export async function verifySocialAccount(
  accountId: string
): Promise<ApiResponse<SocialAccount>> {
  return apiClient.post<SocialAccount>(`/users/me/social-accounts/${accountId}/verify`);
}

// Refresh social account data (followers count, etc.)
export async function refreshSocialAccount(
  accountId: string
): Promise<ApiResponse<SocialAccount>> {
  return apiClient.post<SocialAccount>(`/users/me/social-accounts/${accountId}/refresh`);
}

// Get profile by user ID (public profile view)
export async function getProfileById(userId: string): Promise<ApiResponse<User>> {
  return apiClient.get<User>(`/users/${userId}`);
}

// Get user's social accounts by user ID (public view)
export async function getSocialAccountsByUserId(
  userId: string
): Promise<ApiResponse<SocialAccount[]>> {
  return apiClient.get<SocialAccount[]>(`/users/${userId}/social-accounts`);
}
