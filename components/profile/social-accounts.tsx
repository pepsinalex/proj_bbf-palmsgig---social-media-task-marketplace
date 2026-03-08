'use client';

import React, { useState } from 'react';
import type { SocialAccount } from '@/lib/types/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  validateSocialUsername,
  validateSocialPlatform,
} from '@/lib/validations/profile';

export interface SocialAccountsProps {
  socialAccounts: SocialAccount[];
  onConnect: (platform: string, username: string) => Promise<void>;
  onDisconnect: (accountId: string) => Promise<void>;
}

type Platform = 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube';

const platformConfig: Record<
  Platform,
  { name: string; icon: React.ReactNode; color: string; bgColor: string }
> = {
  instagram: {
    name: 'Instagram',
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    ),
  },
  twitter: {
    name: 'Twitter/X',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  facebook: {
    name: 'Facebook',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 3.667h-3.533v7.98H9.101z" />
      </svg>
    ),
  },
  tiktok: {
    name: 'TikTok',
    color: 'text-gray-800',
    bgColor: 'bg-gray-50',
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
      </svg>
    ),
  },
  youtube: {
    name: 'YouTube',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
  },
};

export function SocialAccounts({
  socialAccounts,
  onConnect,
  onDisconnect,
}: SocialAccountsProps) {
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [username, setUsername] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);

  const connectedPlatforms = new Set(socialAccounts.map((acc) => acc.platform));
  const availablePlatforms = Object.keys(platformConfig).filter(
    (platform) => !connectedPlatforms.has(platform as Platform)
  ) as Platform[];

  const handleConnectClick = () => {
    setShowConnectForm(true);
    setSelectedPlatform(availablePlatforms[0] || null);
    setUsername('');
    setErrors({});
  };

  const handleCancelConnect = () => {
    setShowConnectForm(false);
    setSelectedPlatform(null);
    setUsername('');
    setErrors({});
  };

  const handleSubmitConnect = async (e: React.FormEvent) => {
    e.preventDefault();

    const validationErrors: Record<string, string> = {};

    const platformError = validateSocialPlatform(selectedPlatform);
    if (platformError) {
      validationErrors.platform = platformError;
    }

    const usernameError = validateSocialUsername(username);
    if (usernameError) {
      validationErrors.username = usernameError;
    }

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      if (selectedPlatform) {
        await onConnect(selectedPlatform, username);
        handleCancelConnect();
      }
    } catch (error) {
      console.error('Connect account error:', error);
      setErrors({
        submit: error instanceof Error ? error.message : 'Failed to connect account',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    if (!window.confirm('Are you sure you want to disconnect this account?')) {
      return;
    }

    setDisconnectingId(accountId);
    try {
      await onDisconnect(accountId);
    } catch (error) {
      console.error('Disconnect account error:', error);
      alert(error instanceof Error ? error.message : 'Failed to disconnect account');
    } finally {
      setDisconnectingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Connected Accounts */}
      <div>
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Connected Accounts</h3>
        {socialAccounts.length > 0 ? (
          <div className="space-y-3">
            {socialAccounts.map((account) => {
              const config = platformConfig[account.platform as Platform];
              return (
                <div
                  key={account.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className={`rounded-lg ${config.bgColor} p-2 ${config.color}`}>
                      {config.icon}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900">{config.name}</h4>
                        {account.verified && (
                          <span
                            className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                            title="Verified account"
                          >
                            <svg
                              className="h-3 w-3"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                clipRule="evenodd"
                              />
                            </svg>
                            Verified
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">@{account.username}</p>
                      <p className="text-xs text-gray-400">
                        {account.followers.toLocaleString()} followers
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDisconnect(account.id)}
                    disabled={disconnectingId === account.id}
                    isLoading={disconnectingId === account.id}
                  >
                    {disconnectingId === account.id ? 'Disconnecting...' : 'Disconnect'}
                  </Button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
            <p className="text-sm text-gray-500">No social accounts connected yet</p>
          </div>
        )}
      </div>

      {/* Connect New Account */}
      {!showConnectForm && availablePlatforms.length > 0 && (
        <Button variant="primary" size="md" onClick={handleConnectClick}>
          <svg
            className="-ml-1 mr-2 h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Connect Account
        </Button>
      )}

      {/* Connect Form */}
      {showConnectForm && availablePlatforms.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Connect New Account</h3>
          <form onSubmit={handleSubmitConnect} className="space-y-4">
            {/* Platform Selection */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Platform <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedPlatform || ''}
                onChange={(e) => {
                  setSelectedPlatform(e.target.value as Platform);
                  if (errors.platform) {
                    setErrors((prev) => {
                      const newErrors = { ...prev };
                      delete newErrors.platform;
                      return newErrors;
                    });
                  }
                }}
                disabled={isSubmitting}
                className={`
                  w-full rounded-lg border px-4 py-2.5 text-sm
                  transition-colors duration-200
                  focus:outline-none focus:ring-2
                  disabled:cursor-not-allowed disabled:bg-gray-100
                  ${
                    errors.platform
                      ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
                      : 'border-gray-300 focus:border-sky-500 focus:ring-sky-200'
                  }
                `}
              >
                {availablePlatforms.map((platform) => (
                  <option key={platform} value={platform}>
                    {platformConfig[platform].name}
                  </option>
                ))}
              </select>
              {errors.platform && (
                <p className="mt-1.5 text-sm text-red-600">{errors.platform}</p>
              )}
            </div>

            {/* Username Input */}
            <Input
              label="Username"
              name="username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (errors.username) {
                  setErrors((prev) => {
                    const newErrors = { ...prev };
                    delete newErrors.username;
                    return newErrors;
                  });
                }
              }}
              error={errors.username}
              required
              disabled={isSubmitting}
              placeholder="Enter your username"
            />

            {/* Submit Error */}
            {errors.submit && (
              <div className="rounded-lg bg-red-50 p-4">
                <p className="text-sm text-red-600">{errors.submit}</p>
              </div>
            )}

            {/* Form Actions */}
            <div className="flex gap-3">
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                disabled={isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? 'Connecting...' : 'Connect Account'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="md"
                onClick={handleCancelConnect}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {availablePlatforms.length === 0 && !showConnectForm && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-600">
            All available platforms have been connected.
          </p>
        </div>
      )}
    </div>
  );
}
