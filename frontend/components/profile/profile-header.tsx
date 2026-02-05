import React from 'react';
import type { User } from '@/lib/types/api';
import { Button } from '@/components/ui/button';

export interface ProfileHeaderProps {
  user: User;
  isOwnProfile?: boolean;
  onEditClick?: () => void;
}

export function ProfileHeader({
  user,
  isOwnProfile = false,
  onEditClick,
}: ProfileHeaderProps) {
  return (
    <div className="rounded-lg bg-white p-6 shadow-sm">
      <div className="flex items-start gap-6">
        {/* Profile Picture */}
        <div className="flex-shrink-0">
          {user.profilePicture ? (
            <img
              src={user.profilePicture}
              alt={user.fullName}
              className="h-24 w-24 rounded-full object-cover ring-4 ring-gray-100"
            />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full bg-sky-100 text-2xl font-semibold text-sky-600 ring-4 ring-gray-100">
              {user.fullName.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        {/* User Info */}
        <div className="flex-grow">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-gray-900">{user.fullName}</h1>
                {/* Verification Badges */}
                <div className="flex gap-1">
                  {user.emailVerified && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700"
                      title="Email verified"
                    >
                      <svg
                        className="h-3 w-3"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Email
                    </span>
                  )}
                  {user.phoneVerified && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700"
                      title="Phone verified"
                    >
                      <svg
                        className="h-3 w-3"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      Phone
                    </span>
                  )}
                </div>
              </div>
              <p className="mt-1 text-sm text-gray-500">{user.email}</p>
              <p className="mt-1 text-sm font-medium capitalize text-gray-700">
                {user.role}
              </p>
            </div>

            {/* Edit Button */}
            {isOwnProfile && onEditClick && (
              <Button variant="outline" size="sm" onClick={onEditClick}>
                <svg
                  className="-ml-1 mr-2 h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
                Edit Profile
              </Button>
            )}
          </div>

          {/* Bio */}
          {user.bio && (
            <div className="mt-4">
              <p className="text-sm text-gray-700">{user.bio}</p>
            </div>
          )}

          {/* Stats */}
          <div className="mt-4 flex gap-6">
            <div>
              <p className="text-sm font-medium text-gray-500">Wallet Balance</p>
              <p className="text-lg font-semibold text-gray-900">
                ${user.walletBalance.toFixed(2)}
              </p>
            </div>
            {user.socialAccounts && user.socialAccounts.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-500">Connected Accounts</p>
                <p className="text-lg font-semibold text-gray-900">
                  {user.socialAccounts.length}
                </p>
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-gray-500">Member Since</p>
              <p className="text-lg font-semibold text-gray-900">
                {new Date(user.createdAt).toLocaleDateString('en-US', {
                  month: 'short',
                  year: 'numeric',
                })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
