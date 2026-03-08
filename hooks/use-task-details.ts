'use client';

import { useState, useEffect, useCallback } from 'react';

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'completed' | 'cancelled';
  platform: 'instagram' | 'facebook' | 'twitter' | 'youtube' | 'tiktok';
  taskType: string;
  rewardPerAction: number;
  deadline: string;
  availableSlots: number;
  totalSlots: number;
  requirements: Array<{
    id: string;
    description: string;
    required: boolean;
  }>;
  creator: {
    id: string;
    name: string;
    avatar?: string;
    rating: number;
    totalReviews: number;
    tasksCompleted: number;
    successRate: number;
    verified: boolean;
    joinedDate: string;
  };
}

export interface ProofSubmission {
  images: Array<{ id: string; file: File; preview: string }>;
  description: string;
  link?: string;
}

export interface TaskDetailsState {
  task: Task | null;
  isLoading: boolean;
  error: string | null;
  isSubmitting: boolean;
}

export interface UseTaskDetailsReturn extends TaskDetailsState {
  submitProof: (data: ProofSubmission) => Promise<void>;
  claimTask: () => Promise<void>;
  refetch: () => Promise<void>;
}

export function useTaskDetails(taskId: string): UseTaskDetailsReturn {
  const [state, setState] = useState<TaskDetailsState>({
    task: null,
    isLoading: true,
    error: null,
    isSubmitting: false,
  });

  const fetchTaskDetails = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      console.log(`Fetching task details for task ID: ${taskId}`);

      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || `Failed to fetch task: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      setState({
        task: data,
        isLoading: false,
        error: null,
        isSubmitting: false,
      });
    } catch (error) {
      console.error('Failed to fetch task details:', error);
      setState({
        task: null,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load task details',
        isSubmitting: false,
      });
    }
  }, [taskId]);

  const submitProof = useCallback(
    async (data: ProofSubmission) => {
      setState((prev) => ({ ...prev, isSubmitting: true, error: null }));

      try {
        console.log(`Submitting proof for task ID: ${taskId}`);

        const formData = new FormData();
        data.images.forEach((image, index) => {
          formData.append(`images[${index}]`, image.file);
        });
        formData.append('description', data.description);
        if (data.link) {
          formData.append('link', data.link);
        }

        const response = await fetch(`/api/tasks/${taskId}/proof`, {
          method: 'POST',
          body: formData,
          credentials: 'include',
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.message || `Failed to submit proof: ${response.status} ${response.statusText}`
          );
        }

        await fetchTaskDetails();

        setState((prev) => ({ ...prev, isSubmitting: false, error: null }));
      } catch (error) {
        console.error('Failed to submit proof:', error);
        setState((prev) => ({
          ...prev,
          isSubmitting: false,
          error: error instanceof Error ? error.message : 'Failed to submit proof',
        }));
        throw error;
      }
    },
    [taskId, fetchTaskDetails]
  );

  const claimTask = useCallback(async () => {
    setState((prev) => ({ ...prev, isSubmitting: true, error: null }));

    try {
      console.log(`Claiming task ID: ${taskId}`);

      const response = await fetch(`/api/tasks/${taskId}/claim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || `Failed to claim task: ${response.status} ${response.statusText}`
        );
      }

      await fetchTaskDetails();

      setState((prev) => ({ ...prev, isSubmitting: false, error: null }));
    } catch (error) {
      console.error('Failed to claim task:', error);
      setState((prev) => ({
        ...prev,
        isSubmitting: false,
        error: error instanceof Error ? error.message : 'Failed to claim task',
      }));
      throw error;
    }
  }, [taskId, fetchTaskDetails]);

  const refetch = useCallback(async () => {
    await fetchTaskDetails();
  }, [fetchTaskDetails]);

  useEffect(() => {
    if (taskId) {
      fetchTaskDetails();
    }
  }, [taskId, fetchTaskDetails]);

  return {
    ...state,
    submitProof,
    claimTask,
    refetch,
  };
}
