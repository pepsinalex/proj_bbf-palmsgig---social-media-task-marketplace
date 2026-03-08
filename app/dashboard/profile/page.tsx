'use client';

import React, { useState } from 'react';
import { ProfileHeader } from '@/components/profile/profile-header';
import { EditProfileForm } from '@/components/profile/edit-profile-form';
import { SocialAccounts } from '@/components/profile/social-accounts';
import { AccountStatistics } from '@/components/profile/account-statistics';
import { SettingsForm } from '@/components/profile/settings-form';
import { useProfile } from '@/hooks/use-profile';
import type { ProfileFormData } from '@/lib/validations/profile';
import type { SettingsFormData } from '@/lib/validations/profile';

type ActiveTab = 'overview' | 'edit' | 'social' | 'settings';

export default function ProfilePage() {
  const {
    profile,
    settings,
    socialAccounts,
    walletBalance,
    isLoading,
    profileError,
    settingsError,
    socialAccountsError,
    updateProfile,
    uploadProfilePicture,
    updateSettings,
    connectSocialAccount,
    disconnectSocialAccount,
  } = useProfile();

  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [isEditingProfile, setIsEditingProfile] = useState(false);

  // Handle profile update
  const handleProfileUpdate = async (
    data: ProfileFormData & { profilePictureFile?: File }
  ) => {
    try {
      // Upload profile picture if provided
      if (data.profilePictureFile) {
        const uploadResult = await uploadProfilePicture(data.profilePictureFile);
        data.profilePicture = uploadResult.url;
      }

      // Update profile data
      await updateProfile({
        fullName: data.fullName,
        bio: data.bio,
        profilePicture: data.profilePicture,
      });

      setIsEditingProfile(false);
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    }
  };

  // Handle settings update
  const handleSettingsUpdate = async (data: SettingsFormData) => {
    try {
      await updateSettings(data);
    } catch (error) {
      console.error('Settings update failed:', error);
      throw error;
    }
  };

  // Handle social account connection
  const handleConnectAccount = async (platform: string, username: string) => {
    try {
      await connectSocialAccount({
        platform: platform as
          | 'instagram'
          | 'twitter'
          | 'facebook'
          | 'tiktok'
          | 'youtube',
        username,
      });
    } catch (error) {
      console.error('Connect account failed:', error);
      throw error;
    }
  };

  // Handle social account disconnection
  const handleDisconnectAccount = async (accountId: string) => {
    try {
      await disconnectSocialAccount(accountId);
    } catch (error) {
      console.error('Disconnect account failed:', error);
      throw error;
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-sky-500 border-t-transparent" />
          <p className="mt-4 text-sm text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (profileError || settingsError || socialAccountsError) {
    return (
      <div className="rounded-lg bg-red-50 p-6">
        <div className="flex items-center gap-2">
          <svg className="h-5 w-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <p className="text-sm font-medium text-red-800">
            Failed to load profile. Please try again.
          </p>
        </div>
      </div>
    );
  }

  // No profile data
  if (!profile) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <p className="text-sm text-gray-600">No profile data available.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overview' as ActiveTab, label: 'Overview' },
    { id: 'edit' as ActiveTab, label: 'Edit Profile' },
    { id: 'social' as ActiveTab, label: 'Social Accounts' },
    { id: 'settings' as ActiveTab, label: 'Settings' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="mt-1 text-sm text-gray-600">
          Manage your profile information and connected social accounts
        </p>
      </div>

      {/* Profile Header */}
      <ProfileHeader
        user={profile}
        walletBalance={walletBalance}
        isOwnProfile={true}
        onEditClick={() => {
          setActiveTab('edit');
          setIsEditingProfile(true);
        }}
      />

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id !== 'edit') {
                  setIsEditingProfile(false);
                }
              }}
              className={`
                whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium transition-colors
                ${
                  activeTab === tab.id
                    ? 'border-sky-500 text-sky-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }
              `}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Profile Overview</h2>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Full Name</p>
                  <p className="mt-1 text-base text-gray-900">{profile.full_name}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Email</p>
                  <p className="mt-1 text-base text-gray-900">{profile.email}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Role</p>
                  <p className="mt-1 text-base capitalize text-gray-900">{profile.role}</p>
                </div>
                {profile.bio && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Bio</p>
                    <p className="mt-1 text-base text-gray-900">{profile.bio}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Account Statistics */}
            {socialAccounts.length > 0 && (
              <div className="border-t border-gray-200 pt-6">
                <AccountStatistics socialAccounts={socialAccounts} />
              </div>
            )}
          </div>
        )}

        {/* Edit Profile Tab */}
        {activeTab === 'edit' && (
          <div>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Edit Profile</h2>
            <EditProfileForm
              user={profile}
              onSubmit={handleProfileUpdate}
              onCancel={() => {
                setActiveTab('overview');
                setIsEditingProfile(false);
              }}
            />
          </div>
        )}

        {/* Social Accounts Tab */}
        {activeTab === 'social' && (
          <div>
            <SocialAccounts
              socialAccounts={socialAccounts}
              onConnect={handleConnectAccount}
              onDisconnect={handleDisconnectAccount}
            />
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && settings && (
          <div>
            <SettingsForm initialSettings={settings} onSubmit={handleSettingsUpdate} />
          </div>
        )}
      </div>
    </div>
  );
}
