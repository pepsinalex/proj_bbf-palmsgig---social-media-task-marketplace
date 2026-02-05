'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

export interface UseInfiniteScrollOptions {
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  threshold?: number;
  rootMargin?: string;
  enabled?: boolean;
}

export interface UseInfiniteScrollReturn {
  sentinelRef: React.RefObject<HTMLDivElement>;
  isIntersecting: boolean;
}

export function useInfiniteScroll({
  onLoadMore,
  hasMore,
  isLoading,
  threshold = 0.1,
  rootMargin = '100px',
  enabled = true,
}: UseInfiniteScrollOptions): UseInfiniteScrollReturn {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);

  // Callback ref to handle intersection
  const handleIntersection = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;

      if (!entry) {
        return;
      }

      const intersecting = entry.isIntersecting;
      setIsIntersecting(intersecting);

      // Only trigger load more if:
      // 1. The sentinel is intersecting
      // 2. We're not currently loading
      // 3. There are more items to load
      // 4. The feature is enabled
      if (intersecting && !isLoading && hasMore && enabled) {
        console.log('Infinite scroll triggered: loading more items');
        onLoadMore();
      }
    },
    [onLoadMore, isLoading, hasMore, enabled]
  );

  // Set up IntersectionObserver
  useEffect(() => {
    const sentinel = sentinelRef.current;

    if (!sentinel || !enabled) {
      return;
    }

    // Create observer with specified options
    const observer = new IntersectionObserver(handleIntersection, {
      root: null, // viewport
      rootMargin,
      threshold,
    });

    console.log('IntersectionObserver initialized for infinite scroll');
    observer.observe(sentinel);

    // Cleanup
    return () => {
      if (sentinel) {
        observer.unobserve(sentinel);
        console.log('IntersectionObserver disconnected');
      }
    };
  }, [handleIntersection, threshold, rootMargin, enabled]);

  // Log state changes for debugging
  useEffect(() => {
    if (isIntersecting) {
      console.log(
        `Infinite scroll state: intersecting=${isIntersecting}, loading=${isLoading}, hasMore=${hasMore}, enabled=${enabled}`
      );
    }
  }, [isIntersecting, isLoading, hasMore, enabled]);

  return {
    sentinelRef,
    isIntersecting,
  };
}
