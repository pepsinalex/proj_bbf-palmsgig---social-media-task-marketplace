'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { SearchInput } from '@/components/ui/search-input';
import { FilterSidebar, FilterGroup } from '@/components/ui/filter-sidebar';
import { TaskCard } from '@/components/task-discovery/task-card';
import { ViewToggle, ViewMode } from '@/components/task-discovery/view-toggle';
import { SortOptions, SortOption } from '@/components/task-discovery/sort-options';
import { useTaskDiscovery } from '@/hooks/use-task-discovery';
import { useInfiniteScroll } from '@/hooks/use-infinite-scroll';
import { Skeleton } from '@/components/ui/skeleton';

export default function DiscoverPage() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOption, setSortOption] = useState<SortOption>({
    field: 'createdAt',
    order: 'desc',
    label: 'Newest First',
  });

  // Initialize task discovery with filters
  const { tasks, totalCount, filters, isLoading, isFetchingNextPage, hasNextPage, isError, error, updateFilters, clearFilters, loadMore } = useTaskDiscovery({
    initialFilters: {
      search: searchQuery,
      sortBy: sortOption.field,
      sortOrder: sortOption.order,
    },
    limit: 20,
  });

  // Infinite scroll setup
  const { sentinelRef } = useInfiniteScroll({
    onLoadMore: loadMore,
    hasMore: hasNextPage,
    isLoading: isFetchingNextPage,
    threshold: 0.5,
  });

  // Filter groups for sidebar
  const filterGroups: FilterGroup[] = [
    {
      id: 'status',
      label: 'Status',
      type: 'checkbox',
      options: [
        { label: 'Active', value: 'active', count: undefined },
        { label: 'Paused', value: 'paused', count: undefined },
        { label: 'Completed', value: 'completed', count: undefined },
      ],
    },
    {
      id: 'platform',
      label: 'Platform',
      type: 'checkbox',
      options: [
        { label: 'Instagram', value: 'instagram', count: undefined },
        { label: 'Twitter', value: 'twitter', count: undefined },
        { label: 'Facebook', value: 'facebook', count: undefined },
        { label: 'TikTok', value: 'tiktok', count: undefined },
        { label: 'YouTube', value: 'youtube', count: undefined },
      ],
    },
    {
      id: 'taskType',
      label: 'Task Type',
      type: 'checkbox',
      options: [
        { label: 'Post', value: 'post', count: undefined },
        { label: 'Story', value: 'story', count: undefined },
        { label: 'Reels', value: 'reels', count: undefined },
        { label: 'Like', value: 'like', count: undefined },
        { label: 'Comment', value: 'comment', count: undefined },
        { label: 'Follow', value: 'follow', count: undefined },
        { label: 'Share', value: 'share', count: undefined },
        { label: 'Video', value: 'video', count: undefined },
      ],
    },
    {
      id: 'budget',
      label: 'Budget Range',
      type: 'range',
      min: 0,
      max: 1000,
      step: 10,
    },
  ];

  // Selected filters state
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string | string[] | number[]>>({});

  // Handle search change
  const handleSearchChange = useCallback(
    (value: string) => {
      console.log('Search query changed:', value);
      setSearchQuery(value);
      updateFilters({ search: value });
    },
    [updateFilters]
  );

  // Handle sort change
  const handleSortChange = useCallback(
    (newSort: SortOption) => {
      console.log('Sort option changed:', newSort);
      setSortOption(newSort);
      updateFilters({
        sortBy: newSort.field,
        sortOrder: newSort.order,
      });
    },
    [updateFilters]
  );

  // Handle filter change
  const handleFilterChange = useCallback(
    (filterId: string, value: string | string[] | number[]) => {
      console.log('Filter changed:', filterId, value);
      setSelectedFilters((prev) => ({
        ...prev,
        [filterId]: value,
      }));

      // Apply filters to task discovery
      if (filterId === 'status' && Array.isArray(value)) {
        updateFilters({ status: value.length > 0 ? (value[0] as 'active' | 'paused' | 'completed') : undefined });
      } else if (filterId === 'platform' && Array.isArray(value)) {
        updateFilters({ platform: value.length > 0 ? (value[0] as 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube') : undefined });
      } else if (filterId === 'taskType' && Array.isArray(value)) {
        updateFilters({ taskType: value.length > 0 ? (value[0] as 'post' | 'story' | 'reels' | 'like' | 'comment' | 'follow' | 'share' | 'video') : undefined });
      } else if (filterId === 'budget' && Array.isArray(value) && value.length === 2) {
        updateFilters({
          minBudget: typeof value[0] === 'number' ? value[0] : undefined,
          maxBudget: typeof value[1] === 'number' ? value[1] : undefined,
        });
      }
    },
    [updateFilters]
  );

  // Handle clear all filters
  const handleClearAllFilters = useCallback(() => {
    console.log('Clearing all filters');
    setSelectedFilters({});
    clearFilters();
  }, [clearFilters]);

  // Handle task card click
  const handleTaskClick = useCallback(
    (taskId: string) => {
      console.log('Navigating to task:', taskId);
      router.push(`/dashboard/tasks/${taskId}`);
    },
    [router]
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Discover Tasks</h1>
          <p className="mt-2 text-gray-600">
            Browse and discover tasks that match your skills and interests
          </p>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Filter Sidebar - Desktop */}
          <aside className="hidden w-full lg:block lg:w-80">
            <div className="sticky top-6">
              <FilterSidebar
                filterGroups={filterGroups}
                selectedFilters={selectedFilters}
                onFilterChange={handleFilterChange}
                onClearAll={handleClearAllFilters}
                isLoading={isLoading}
              />
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {/* Search and Controls */}
            <div className="mb-6 space-y-4">
              <SearchInput
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search tasks..."
                isLoading={isLoading}
              />

              <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
                <div className="flex items-center gap-4">
                  <ViewToggle currentView={viewMode} onViewChange={setViewMode} />
                  <div className="text-sm text-gray-600">
                    {totalCount > 0 ? `${totalCount} tasks found` : 'No tasks found'}
                  </div>
                </div>

                <SortOptions currentSort={sortOption} onSortChange={handleSortChange} />
              </div>
            </div>

            {/* Error State */}
            {isError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
                <p className="font-medium">Error loading tasks</p>
                <p className="mt-1 text-sm">{error || 'An unexpected error occurred'}</p>
              </div>
            )}

            {/* Loading State */}
            {isLoading && tasks.length === 0 && (
              <div className={viewMode === 'grid' ? 'grid gap-6 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3' : 'space-y-4'}>
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="rounded-lg border border-gray-200 bg-white p-6">
                    <Skeleton height="200px" />
                  </div>
                ))}
              </div>
            )}

            {/* Task Grid/List */}
            {!isError && tasks.length > 0 && (
              <>
                <div className={viewMode === 'grid' ? 'grid gap-6 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3' : 'space-y-4'}>
                  {tasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={handleTaskClick}
                      viewMode={viewMode}
                    />
                  ))}
                </div>

                {/* Infinite Scroll Sentinel */}
                {hasNextPage && (
                  <div ref={sentinelRef} className="mt-8 flex justify-center py-4">
                    {isFetchingNextPage && (
                      <div className="text-center">
                        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-sky-500 border-r-transparent"></div>
                        <p className="mt-2 text-sm text-gray-600">Loading more tasks...</p>
                      </div>
                    )}
                  </div>
                )}

                {/* No More Tasks Message */}
                {!hasNextPage && tasks.length > 0 && (
                  <div className="mt-8 text-center text-sm text-gray-600">
                    <p>No more tasks to load</p>
                  </div>
                )}
              </>
            )}

            {/* Empty State */}
            {!isLoading && !isError && tasks.length === 0 && (
              <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white py-12 text-center">
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No tasks found</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Try adjusting your filters or search query to find more tasks.
                </p>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
