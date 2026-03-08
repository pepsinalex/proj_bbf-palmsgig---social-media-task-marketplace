import { apiClient } from './client';
import type {
  Task,
  CreateTaskRequest,
  UpdateTaskRequest,
  TaskSubmission,
  SubmitTaskProofRequest,
  ReviewSubmissionRequest,
  ApiResponse,
  PaginatedResponse,
  TaskFilters,
} from '../types/api';

export async function getTasks(filters?: TaskFilters): Promise<PaginatedResponse<Task>> {
  console.log('Fetching tasks with filters:', filters);

  const queryParams = new URLSearchParams();

  if (filters?.page !== undefined) {
    queryParams.append('page', filters.page.toString());
  }

  if (filters?.limit !== undefined) {
    queryParams.append('limit', filters.limit.toString());
  }

  if (filters?.sortBy) {
    queryParams.append('sortBy', filters.sortBy);
  }

  if (filters?.sortOrder) {
    queryParams.append('sortOrder', filters.sortOrder);
  }

  if (filters?.status) {
    queryParams.append('status', filters.status);
  }

  if (filters?.platform) {
    queryParams.append('platform', filters.platform);
  }

  if (filters?.taskType) {
    queryParams.append('taskType', filters.taskType);
  }

  if (filters?.minBudget !== undefined) {
    queryParams.append('minBudget', filters.minBudget.toString());
  }

  if (filters?.maxBudget !== undefined) {
    queryParams.append('maxBudget', filters.maxBudget.toString());
  }

  if (filters?.clientId) {
    queryParams.append('clientId', filters.clientId);
  }

  const queryString = queryParams.toString();
  const endpoint = `/tasks${queryString ? `?${queryString}` : ''}`;

  try {
    const response = await apiClient.get<PaginatedResponse<Task>>(endpoint);
    console.log(`Successfully fetched ${response.data.pagination?.total || 0} tasks`);
    return response.data as PaginatedResponse<Task>;
  } catch (error) {
    console.error('Failed to fetch tasks:', error);
    throw error;
  }
}

export async function getTaskById(taskId: string): Promise<ApiResponse<Task>> {
  console.log(`Fetching task by ID: ${taskId}`);

  if (!taskId) {
    throw new Error('Task ID is required');
  }

  try {
    const response = await apiClient.get<Task>(`/tasks/${taskId}`);
    console.log(`Successfully fetched task: ${taskId}`);
    return response;
  } catch (error) {
    console.error(`Failed to fetch task ${taskId}:`, error);
    throw error;
  }
}

export async function createTask(data: CreateTaskRequest): Promise<ApiResponse<Task>> {
  console.log('Creating new task:', data.title);

  if (!data.title || !data.platform || !data.taskType) {
    throw new Error('Title, platform, and task type are required');
  }

  if (data.budget <= 0 || data.rewardPerAction <= 0 || data.totalSlots <= 0) {
    throw new Error('Budget, reward, and total slots must be positive numbers');
  }

  try {
    const response = await apiClient.post<Task>('/tasks', data);
    console.log(`Successfully created task: ${response.data.id}`);
    return response;
  } catch (error) {
    console.error('Failed to create task:', error);
    throw error;
  }
}

export async function updateTask(
  taskId: string,
  data: UpdateTaskRequest
): Promise<ApiResponse<Task>> {
  console.log(`Updating task: ${taskId}`);

  if (!taskId) {
    throw new Error('Task ID is required');
  }

  if (data.budget !== undefined && data.budget <= 0) {
    throw new Error('Budget must be a positive number');
  }

  if (data.rewardPerAction !== undefined && data.rewardPerAction <= 0) {
    throw new Error('Reward per action must be a positive number');
  }

  if (data.totalSlots !== undefined && data.totalSlots <= 0) {
    throw new Error('Total slots must be a positive number');
  }

  try {
    const response = await apiClient.put<Task>(`/tasks/${taskId}`, data);
    console.log(`Successfully updated task: ${taskId}`);
    return response;
  } catch (error) {
    console.error(`Failed to update task ${taskId}:`, error);
    throw error;
  }
}

export async function deleteTask(taskId: string): Promise<ApiResponse<{ success: boolean }>> {
  console.log(`Deleting task: ${taskId}`);

  if (!taskId) {
    throw new Error('Task ID is required');
  }

  try {
    const response = await apiClient.delete<{ success: boolean }>(`/tasks/${taskId}`);
    console.log(`Successfully deleted task: ${taskId}`);
    return response;
  } catch (error) {
    console.error(`Failed to delete task ${taskId}:`, error);
    throw error;
  }
}

export async function getTaskSubmissions(
  taskId: string
): Promise<ApiResponse<TaskSubmission[]>> {
  console.log(`Fetching submissions for task: ${taskId}`);

  if (!taskId) {
    throw new Error('Task ID is required');
  }

  try {
    const response = await apiClient.get<TaskSubmission[]>(`/tasks/${taskId}/submissions`);
    console.log(`Successfully fetched ${response.data.length} submissions for task: ${taskId}`);
    return response;
  } catch (error) {
    console.error(`Failed to fetch submissions for task ${taskId}:`, error);
    throw error;
  }
}

export async function submitTaskProof(
  data: SubmitTaskProofRequest
): Promise<ApiResponse<TaskSubmission>> {
  console.log(`Submitting proof for task: ${data.taskId}`);

  if (!data.taskId) {
    throw new Error('Task ID is required');
  }

  if (!data.proofUrl && !data.proofDescription) {
    throw new Error('Either proof URL or proof description is required');
  }

  try {
    const response = await apiClient.post<TaskSubmission>('/tasks/submissions', data);
    console.log(`Successfully submitted proof for task: ${data.taskId}`);
    return response;
  } catch (error) {
    console.error(`Failed to submit proof for task ${data.taskId}:`, error);
    throw error;
  }
}

export async function reviewSubmission(
  data: ReviewSubmissionRequest
): Promise<ApiResponse<TaskSubmission>> {
  console.log(`Reviewing submission: ${data.submissionId} with status: ${data.status}`);

  if (!data.submissionId) {
    throw new Error('Submission ID is required');
  }

  if (!data.status || !['approved', 'rejected'].includes(data.status)) {
    throw new Error('Valid status (approved or rejected) is required');
  }

  if (data.status === 'rejected' && !data.rejectionReason) {
    throw new Error('Rejection reason is required when rejecting a submission');
  }

  try {
    const response = await apiClient.post<TaskSubmission>(
      `/tasks/submissions/${data.submissionId}/review`,
      {
        status: data.status,
        rejectionReason: data.rejectionReason,
      }
    );
    console.log(`Successfully reviewed submission: ${data.submissionId}`);
    return response;
  } catch (error) {
    console.error(`Failed to review submission ${data.submissionId}:`, error);
    throw error;
  }
}

export async function searchTasks(query: string, filters?: TaskFilters): Promise<PaginatedResponse<Task>> {
  console.log(`Searching tasks with query: "${query}"`);

  if (!query || query.trim().length === 0) {
    return getTasks(filters);
  }

  const queryParams = new URLSearchParams();
  queryParams.append('q', query.trim());

  if (filters?.page !== undefined) {
    queryParams.append('page', filters.page.toString());
  }

  if (filters?.limit !== undefined) {
    queryParams.append('limit', filters.limit.toString());
  }

  if (filters?.sortBy) {
    queryParams.append('sortBy', filters.sortBy);
  }

  if (filters?.sortOrder) {
    queryParams.append('sortOrder', filters.sortOrder);
  }

  if (filters?.status) {
    queryParams.append('status', filters.status);
  }

  if (filters?.platform) {
    queryParams.append('platform', filters.platform);
  }

  if (filters?.taskType) {
    queryParams.append('taskType', filters.taskType);
  }

  if (filters?.minBudget !== undefined) {
    queryParams.append('minBudget', filters.minBudget.toString());
  }

  if (filters?.maxBudget !== undefined) {
    queryParams.append('maxBudget', filters.maxBudget.toString());
  }

  const queryString = queryParams.toString();
  const endpoint = `/tasks/search?${queryString}`;

  try {
    const response = await apiClient.get<PaginatedResponse<Task>>(endpoint);
    console.log(`Search returned ${response.data.pagination?.total || 0} tasks`);
    return response.data as PaginatedResponse<Task>;
  } catch (error) {
    console.error('Failed to search tasks:', error);
    throw error;
  }
}
