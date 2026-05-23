'use client';

import { OverviewCard } from '@/components/dashboard/overview-card';
import { ActivityFeed } from '@/components/dashboard/activity-feed';
import { Button } from '@/components/ui/button';
import { useDashboard } from '@/hooks/use-dashboard';
import { useAuth } from '@/hooks/use-auth';

export default function DashboardPage() {
  const { user } = useAuth();
  const { stats, activities, isLoading, refresh } = useDashboard();

  return (
    <div className="space-y-8 font-sans">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-secondary-900 dark:text-gray-50">
            Welcome back, {user?.fullName || 'User'}!
          </h1>
          <p className="mt-1 text-base text-gray-600 dark:text-gray-400">
            Here&apos;s what&apos;s happening with your account today.
          </p>
        </div>
        <Button
          variant="outline"
          size="md"
          onClick={() => refresh.refreshAll()}
          aria-label="Refresh dashboard"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span>Refresh</span>
        </Button>
      </header>

      <section
        aria-label="Account overview"
        className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
      >
        <OverviewCard
          title="Wallet Balance"
          value={stats?.walletBalance ? `$${stats.walletBalance.toFixed(2)}` : '$0.00'}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
              />
            </svg>
          }
          loading={isLoading}
        />

        <OverviewCard
          title="Active Tasks"
          value={stats?.activeTasks || 0}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
          }
          loading={isLoading}
        />

        <OverviewCard
          title="Completed Tasks"
          value={stats?.completedTasks || 0}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
          loading={isLoading}
        />

        <OverviewCard
          title="Total Earnings"
          value={stats?.totalEarnings ? `$${stats.totalEarnings.toFixed(2)}` : '$0.00'}
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
          loading={isLoading}
        />
      </section>

      <section aria-label="Recent activity">
        <ActivityFeed activities={activities} loading={isLoading} />
      </section>
    </div>
  );
}
