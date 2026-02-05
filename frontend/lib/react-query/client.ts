// React Query client configuration

// Note: This file exports a factory function instead of a singleton
// to ensure compatibility with Next.js App Router and server-side rendering

interface QueryClientConfig {
  defaultOptions: {
    queries: {
      staleTime: number;
      cacheTime: number;
      refetchOnWindowFocus: boolean;
      refetchOnReconnect: boolean;
      retry: number | ((failureCount: number, error: unknown) => boolean);
      retryDelay: (attemptIndex: number) => number;
    };
    mutations: {
      retry: number;
      retryDelay: (attemptIndex: number) => number;
    };
  };
}

// Query client default configuration
export const queryClientConfig: QueryClientConfig = {
  defaultOptions: {
    queries: {
      // Data is considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,

      // Cache is kept for 10 minutes
      cacheTime: 10 * 60 * 1000,

      // Don't refetch on window focus by default (can be overridden per query)
      refetchOnWindowFocus: false,

      // Refetch on reconnect
      refetchOnReconnect: true,

      // Retry failed requests with exponential backoff
      retry: (failureCount: number, error: unknown) => {
        // Don't retry on 4xx errors (client errors)
        if (
          error &&
          typeof error === 'object' &&
          'statusCode' in error &&
          typeof error.statusCode === 'number' &&
          error.statusCode >= 400 &&
          error.statusCode < 500
        ) {
          return false;
        }

        // Retry up to 3 times for other errors
        return failureCount < 3;
      },

      // Exponential backoff: 1s, 2s, 4s
      retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },

    mutations: {
      // Don't retry mutations by default
      retry: 0,

      // If retry is enabled for specific mutations, use exponential backoff
      retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
};

// Query keys factory for consistent key management
export const queryKeys = {
  // Authentication
  auth: {
    all: ['auth'] as const,
    me: () => [...queryKeys.auth.all, 'me'] as const,
  },

  // Users
  users: {
    all: ['users'] as const,
    lists: () => [...queryKeys.users.all, 'list'] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.users.lists(), filters] as const,
    details: () => [...queryKeys.users.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.users.details(), id] as const,
  },

  // Tasks
  tasks: {
    all: ['tasks'] as const,
    lists: () => [...queryKeys.tasks.all, 'list'] as const,
    list: (filters: Record<string, unknown>) => [...queryKeys.tasks.lists(), filters] as const,
    details: () => [...queryKeys.tasks.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.tasks.details(), id] as const,
    submissions: (taskId: string) => [...queryKeys.tasks.detail(taskId), 'submissions'] as const,
  },

  // Wallet
  wallet: {
    all: ['wallet'] as const,
    balance: () => [...queryKeys.wallet.all, 'balance'] as const,
    transactions: () => [...queryKeys.wallet.all, 'transactions'] as const,
    transactionsList: (filters: Record<string, unknown>) =>
      [...queryKeys.wallet.transactions(), filters] as const,
  },

  // Dashboard
  dashboard: {
    all: ['dashboard'] as const,
    stats: () => [...queryKeys.dashboard.all, 'stats'] as const,
    activities: () => [...queryKeys.dashboard.all, 'activities'] as const,
  },
};

// Error handling helper for queries
export const handleQueryError = (error: unknown): string => {
  if (error && typeof error === 'object') {
    if ('message' in error && typeof error.message === 'string') {
      return error.message;
    }
    if ('error' in error && typeof error.error === 'object' && error.error) {
      const errorObj = error.error as Record<string, unknown>;
      if ('message' in errorObj && typeof errorObj.message === 'string') {
        return errorObj.message;
      }
    }
  }

  return 'An unexpected error occurred';
};

// Mutation error handler
export const handleMutationError = (error: unknown): void => {
  const errorMessage = handleQueryError(error);
  console.error('Mutation error:', errorMessage);

  // You can add toast notifications here if needed
  // toast.error(errorMessage);
};

// Success handler for mutations
export const handleMutationSuccess = (message?: string): void => {
  if (message) {
    console.log('Mutation success:', message);
    // You can add toast notifications here if needed
    // toast.success(message);
  }
};

// Optimistic update helpers
export interface OptimisticUpdateConfig<TData, TVariables> {
  queryKey: readonly unknown[];
  updateFn: (oldData: TData | undefined, variables: TVariables) => TData;
}

export const createOptimisticUpdate = <TData, TVariables>({
  queryKey,
  updateFn,
}: OptimisticUpdateConfig<TData, TVariables>) => {
  return {
    queryKey,
    updateFn,
  };
};
