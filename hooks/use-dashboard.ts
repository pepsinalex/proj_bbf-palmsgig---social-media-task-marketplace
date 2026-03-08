'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDashboardStats, getDashboardActivities, getRecentTransactions } from '../lib/api/dashboard';
import { queryKeys, handleQueryError } from '../lib/react-query/client';
import type { DashboardStats } from '../lib/types/api';
import type { DashboardActivities } from '../lib/api/dashboard';

/**
 * Custom hook for fetching dashboard statistics
 *
 * Fetches comprehensive dashboard statistics with automatic caching and refetching.
 * Data is refreshed every 5 minutes or when explicitly invalidated.
 *
 * @param refetchInterval - Optional custom refetch interval in ms (default: 5 minutes)
 * @returns Query result with dashboard stats, loading state, and error
 */
export function useDashboardStats(refetchInterval?: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.stats(),
    queryFn: async () => {
      const response = await getDashboardStats();
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: refetchInterval || 5 * 60 * 1000, // Auto-refetch every 5 minutes
    refetchOnWindowFocus: true,
    retry: 2,
    onError: (error: unknown) => {
      const errorMessage = handleQueryError(error);
      console.error('Dashboard stats query error:', errorMessage);
    },
  });
}

/**
 * Custom hook for fetching dashboard activities
 *
 * Fetches paginated list of recent user activities with automatic caching.
 * Activities include task completions, payments, withdrawals, etc.
 *
 * @param limit - Number of activities to fetch (default: 10)
 * @param offset - Offset for pagination (default: 0)
 * @returns Query result with activities, loading state, and error
 */
export function useDashboardActivities(limit = 10, offset = 0) {
  return useQuery({
    queryKey: [...queryKeys.dashboard.activities(), { limit, offset }],
    queryFn: async () => {
      const response = await getDashboardActivities(limit, offset);
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchOnWindowFocus: true,
    retry: 2,
    onError: (error: unknown) => {
      const errorMessage = handleQueryError(error);
      console.error('Dashboard activities query error:', errorMessage);
    },
  });
}

/**
 * Custom hook for fetching recent transactions
 *
 * Fetches the most recent wallet transactions for quick dashboard overview.
 * For detailed transaction management, use the wallet hooks.
 *
 * @param limit - Number of transactions to fetch (default: 5)
 * @returns Query result with transactions, loading state, and error
 */
export function useRecentTransactions(limit = 5) {
  return useQuery({
    queryKey: [...queryKeys.wallet.transactions(), { recent: true, limit }],
    queryFn: async () => {
      const response = await getRecentTransactions(limit);
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchOnWindowFocus: true,
    retry: 2,
    onError: (error: unknown) => {
      const errorMessage = handleQueryError(error);
      console.error('Recent transactions query error:', errorMessage);
    },
  });
}

/**
 * Custom hook for invalidating dashboard queries
 *
 * Provides utility functions to manually trigger refetch of dashboard data.
 * Useful after performing actions that should immediately update the dashboard.
 *
 * @returns Object with invalidation functions
 */
export function useDashboardRefresh() {
  const queryClient = useQueryClient();

  return {
    /**
     * Invalidate and refetch all dashboard queries
     */
    refreshAll: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
      console.log('All dashboard queries invalidated');
    },

    /**
     * Invalidate and refetch dashboard statistics only
     */
    refreshStats: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
      console.log('Dashboard stats invalidated');
    },

    /**
     * Invalidate and refetch dashboard activities only
     */
    refreshActivities: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.activities() });
      console.log('Dashboard activities invalidated');
    },

    /**
     * Invalidate and refetch recent transactions only
     */
    refreshTransactions: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.wallet.transactions() });
      console.log('Recent transactions invalidated');
    },
  };
}

/**
 * Combined hook for all dashboard data
 *
 * Convenience hook that fetches all dashboard data at once.
 * Useful for the main dashboard page.
 *
 * @returns Object with all dashboard queries and loading states
 */
export function useDashboard() {
  const statsQuery = useDashboardStats();
  const activitiesQuery = useDashboardActivities(10);
  const transactionsQuery = useRecentTransactions(5);
  const refresh = useDashboardRefresh();

  return {
    stats: statsQuery.data,
    activities: activitiesQuery.data?.activities || [],
    transactions: transactionsQuery.data || [],
    isLoading: statsQuery.isLoading || activitiesQuery.isLoading || transactionsQuery.isLoading,
    isError: statsQuery.isError || activitiesQuery.isError || transactionsQuery.isError,
    error: statsQuery.error || activitiesQuery.error || transactionsQuery.error,
    refresh,
  };
}
