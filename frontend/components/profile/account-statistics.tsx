import React from 'react';
import type { SocialAccount } from '@/lib/types/api';

export interface AccountStatisticsProps {
  socialAccounts: SocialAccount[];
}

export function AccountStatistics({ socialAccounts }: AccountStatisticsProps) {
  // Calculate total followers across all platforms
  const totalFollowers = socialAccounts.reduce((sum, account) => sum + account.followers, 0);

  // Calculate average followers
  const averageFollowers =
    socialAccounts.length > 0 ? Math.round(totalFollowers / socialAccounts.length) : 0;

  // Count verified accounts
  const verifiedAccounts = socialAccounts.filter((account) => account.verified).length;

  // Get account with most followers
  const topAccount = socialAccounts.reduce(
    (max, account) => (account.followers > (max?.followers || 0) ? account : max),
    null as SocialAccount | null
  );

  const stats = [
    {
      label: 'Total Followers',
      value: totalFollowers.toLocaleString(),
      icon: (
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      ),
      color: 'text-sky-600',
      bgColor: 'bg-sky-50',
    },
    {
      label: 'Connected Accounts',
      value: socialAccounts.length.toString(),
      icon: (
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
          />
        </svg>
      ),
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      label: 'Verified Accounts',
      value: verifiedAccounts.toString(),
      icon: (
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Average Followers',
      value: averageFollowers.toLocaleString(),
      icon: (
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
      ),
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ];

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Account Statistics</h3>

      {socialAccounts.length > 0 ? (
        <>
          {/* Statistics Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <div className={`rounded-lg ${stat.bgColor} p-2 ${stat.color}`}>
                    {stat.icon}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">{stat.label}</p>
                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Top Account */}
          {topAccount && (
            <div className="rounded-lg border border-gray-200 bg-gradient-to-br from-sky-50 to-purple-50 p-6">
              <div className="mb-3 flex items-center gap-2">
                <svg
                  className="h-5 w-5 text-yellow-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <h4 className="text-sm font-semibold text-gray-900">Top Performing Account</h4>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex-grow">
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-semibold capitalize text-gray-900">
                      {topAccount.platform}
                    </p>
                    {topAccount.verified && (
                      <span
                        className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                        title="Verified account"
                      >
                        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
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
                  <p className="text-sm text-gray-600">@{topAccount.username}</p>
                  <p className="mt-1 text-xl font-bold text-sky-600">
                    {topAccount.followers.toLocaleString()} followers
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Platform Breakdown */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h4 className="mb-4 text-sm font-semibold text-gray-900">
              Followers by Platform
            </h4>
            <div className="space-y-3">
              {socialAccounts
                .sort((a, b) => b.followers - a.followers)
                .map((account) => {
                  const percentage = totalFollowers > 0
                    ? (account.followers / totalFollowers) * 100
                    : 0;

                  return (
                    <div key={account.id}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="font-medium capitalize text-gray-700">
                          {account.platform}
                        </span>
                        <span className="text-gray-600">
                          {account.followers.toLocaleString()} ({percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                        <div
                          className="h-full rounded-full bg-sky-500 transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <h4 className="mt-2 text-sm font-semibold text-gray-900">No statistics available</h4>
          <p className="mt-1 text-sm text-gray-500">
            Connect your social accounts to see statistics
          </p>
        </div>
      )}
    </div>
  );
}
