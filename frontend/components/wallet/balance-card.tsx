'use client';

import React from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

export interface BalanceCardProps {
  totalBalance: number;
  availableBalance: number;
  pendingBalance: number;
  currency?: string;
  onDeposit?: () => void;
  onWithdraw?: () => void;
  loading?: boolean;
  className?: string;
}

export function BalanceCard({
  totalBalance,
  availableBalance,
  pendingBalance,
  currency = 'USD',
  onDeposit,
  onWithdraw,
  loading = false,
  className = '',
}: BalanceCardProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardContent>
          <div className="animate-pulse space-y-4 py-4">
            <div className="h-8 w-32 rounded bg-gray-200 dark:bg-gray-700"></div>
            <div className="h-12 w-48 rounded bg-gray-200 dark:bg-gray-700"></div>
            <div className="flex gap-4">
              <div className="h-20 flex-1 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-20 flex-1 rounded bg-gray-200 dark:bg-gray-700"></div>
            </div>
            <div className="flex gap-3">
              <div className="h-10 flex-1 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-10 flex-1 rounded bg-gray-200 dark:bg-gray-700"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardContent>
        <div className="space-y-6 py-4">
          <div>
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Balance</h3>
            <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(totalBalance)}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-850">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Available</p>
                  <p className="mt-1 text-xl font-semibold text-green-600 dark:text-green-400">
                    {formatCurrency(availableBalance)}
                  </p>
                </div>
                <div className="rounded-full bg-green-100 p-3 dark:bg-green-900">
                  <svg
                    className="h-6 w-6 text-green-600 dark:text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">Ready to withdraw</p>
            </div>

            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-850">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Pending</p>
                  <p className="mt-1 text-xl font-semibold text-yellow-600 dark:text-yellow-400">
                    {formatCurrency(pendingBalance)}
                  </p>
                </div>
                <div className="rounded-full bg-yellow-100 p-3 dark:bg-yellow-900">
                  <svg
                    className="h-6 w-6 text-yellow-600 dark:text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">Processing</p>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="primary"
              size="md"
              onClick={onDeposit}
              disabled={!onDeposit}
              className="flex-1"
            >
              <svg
                className="-ml-1 mr-2 h-5 w-5"
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
              Deposit
            </Button>
            <Button
              variant="outline"
              size="md"
              onClick={onWithdraw}
              disabled={!onWithdraw || availableBalance <= 0}
              className="flex-1"
            >
              <svg
                className="-ml-1 mr-2 h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20 12H4"
                />
              </svg>
              Withdraw
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
