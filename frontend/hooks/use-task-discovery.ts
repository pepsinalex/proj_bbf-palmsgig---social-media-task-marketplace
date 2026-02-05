'use client';

import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useMemo } from 'react';
import { getTasks, searchTasks } from '../lib/api/tasks';
import { queryKeys, handleQueryError } from '../lib/react-query/client';
import type { Task, TaskFilters } from '../lib/types/api';

export interface TaskDiscoveryFilters {
  search?: string;
  status?: Task['status'];
  platform?: Task['platform'];
  taskType?: Task['taskType'];
  minBudget?: number;
  maxBudget?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface UseTaskDiscoveryOptions {
  initialFilters?: TaskDiscoveryFilters;
  limit?: number;
  enabled?: boolean;
}

export function useTaskDiscovery(options: UseTaskDiscoveryOptions = {}) {
  const { initialFilters = {}, limit = 20, enabled = true } = options;

  const [filters, setFilters] = useState<TaskDiscoveryFilters>(initialFilters);
  const queryClient = useQueryClient();

  // Build query filters for API
  const apiFilters = useMemo((): TaskFilters => {
    return {
      limit,
      status: filters.status,
      platform: filters.platform,
      taskType: filters.taskType,
      minBudget: filters.minBudget,
      maxBudget: filters.maxBudget,
      sortBy: filters.sortBy,
      sortOrder: filters.sortOrder,
    };
  }, [filters, limit]);

  // Infinite query for task discovery
  const query = useInfiniteQuery({
    queryKey: [...queryKeys.tasks.lists(), { filters, limit }],
    queryFn: async ({ pageParam = 1 }) => {
      console.log(`Fetching tasks page ${pageParam} with filters:`, filters);

      const queryFilters: TaskFilters = {
        ...apiFilters,
        page: pageParam,
      };

      try {
        // Use search endpoint if search query is provided
        if (filters.search && filters.search.trim().length > 0) {
          const result = await searchTasks(filters.search, queryFilters);
          console.log(`Search returned ${result.data?.length || 0} tasks on page ${pageParam}`);
          return result;
        }

        // Otherwise use regular task list endpoint
        const result = await getTasks(queryFilters);
        console.log(`Fetched ${result.data?.length || 0} tasks on page ${pageParam}`);
        return result;
      } catch (error) {
        console.error(`Failed to fetch tasks page ${pageParam}:`, error);
        throw error;
      }
    },
    getNextPageParam: (lastPage) => {
      const pagination = lastPage.pagination;
      if (!pagination) {
        return undefined;
      }

      if (pagination.hasNext) {
        const nextPage = pagination.page + 1;
        console.log(`Next page available: ${nextPage}`);
        return nextPage;
      }

      console.log('No more pages available');
      return undefined;
    },
    initialPageParam: 1,
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
    refetchOnWindowFocus: false,
  });

  // Flatten all pages into a single array of tasks
  const tasks = useMemo(() => {
    if (!query.data?.pages) {
      return [];
    }

    const allTasks = query.data.pages.flatMap((page) => page.data || []);
    console.log(`Total tasks loaded: ${allTasks.length}`);
    return allTasks;
  }, [query.data]);

  // Get total count from first page
  const totalCount = useMemo(() => {
    return query.data?.pages[0]?.pagination?.total || 0;
  }, [query.data]);

  // Update filters with type safety
  const updateFilters = useCallback((newFilters: Partial<TaskDiscoveryFilters>) => {
    console.log('Updating task discovery filters:', newFilters);
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
    }));
  }, []);

  // Clear all filters
  const clearFilters = useCallback(() => {
    console.log('Clearing all task discovery filters');
    setFilters({});
  }, []);

  // Refresh the query
  const refresh = useCallback(async () => {
    console.log('Refreshing task discovery');
    await queryClient.invalidateQueries({
      queryKey: [...queryKeys.tasks.lists(), { filters, limit }],
    });
  }, [queryClient, filters, limit]);

  // Load more tasks (fetch next page)
  const loadMore = useCallback(() => {
    if (query.hasNextPage && !query.isFetchingNextPage) {
      console.log('Loading more tasks');
      query.fetchNextPage();
    }
  }, [query]);

  // Error handling
  const error = useMemo(() => {
    if (query.error) {
      return handleQueryError(query.error);
    }
    return null;
  }, [query.error]);

  return {
    // Data
    tasks,
    totalCount,
    filters,

    // Loading states
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage || false,

    // Error states
    isError: query.isError,
    error,

    // Actions
    updateFilters,
    clearFilters,
    loadMore,
    refresh,

    // Raw query for advanced usage
    query,
  };
}
