import { apiClient } from './client';
import type { ApiResponse, DashboardStats, Transaction } from '../types/api';

export interface DashboardOverview {
  stats: DashboardStats;
}

export interface ActivityItem {
  id: string;
  type: 'task_completed' | 'payment_received' | 'withdrawal' | 'task_created' | 'submission_approved';
  title: string;
  description: string;
  timestamp: string;
  amount?: number;
  relatedId?: string;
}

export interface DashboardActivities {
  activities: ActivityItem[];
  total: number;
}

/**
 * Fetch dashboard overview statistics
 *
 * Retrieves comprehensive dashboard statistics including:
 * - Total, active, and completed tasks
 * - Total earnings and wallet balance
 * - Pending submissions count
 * - Recent transactions and tasks
 *
 * @returns Promise with dashboard statistics
 * @throws ApiClientError on request failure
 */
export async function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  try {
    console.log('Fetching dashboard stats');
    const response = await apiClient.get<DashboardStats>('/dashboard/stats');
    console.log('Dashboard stats fetched successfully');
    return response;
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    throw error;
  }
}

/**
 * Fetch recent dashboard activities
 *
 * Retrieves paginated list of recent user activities including:
 * - Task completions
 * - Payments received
 * - Withdrawals
 * - Task creations
 * - Submission approvals
 *
 * @param limit - Number of activities to fetch (default: 10)
 * @param offset - Offset for pagination (default: 0)
 * @returns Promise with dashboard activities
 * @throws ApiClientError on request failure
 */
export async function getDashboardActivities(
  limit = 10,
  offset = 0
): Promise<ApiResponse<DashboardActivities>> {
  try {
    console.log(`Fetching dashboard activities: limit=${limit}, offset=${offset}`);
    const endpoint = `/dashboard/activities?limit=${limit}&offset=${offset}`;
    const response = await apiClient.get<DashboardActivities>(endpoint);
    console.log(`Fetched ${response.data.activities.length} activities`);
    return response;
  } catch (error) {
    console.error('Error fetching dashboard activities:', error);
    throw error;
  }
}

/**
 * Fetch recent transactions for the dashboard
 *
 * Retrieves the most recent wallet transactions for quick overview.
 * For detailed transaction history, use the wallet API endpoints.
 *
 * @param limit - Number of transactions to fetch (default: 5)
 * @returns Promise with recent transactions
 * @throws ApiClientError on request failure
 */
export async function getRecentTransactions(limit = 5): Promise<ApiResponse<Transaction[]>> {
  try {
    console.log(`Fetching recent transactions: limit=${limit}`);
    const endpoint = `/dashboard/transactions/recent?limit=${limit}`;
    const response = await apiClient.get<Transaction[]>(endpoint);
    console.log(`Fetched ${response.data.length} recent transactions`);
    return response;
  } catch (error) {
    console.error('Error fetching recent transactions:', error);
    throw error;
  }
}

/**
 * Refresh all dashboard data
 *
 * Triggers a server-side refresh of cached dashboard data.
 * Useful after performing actions that should immediately reflect on the dashboard.
 *
 * @returns Promise with success status
 * @throws ApiClientError on request failure
 */
export async function refreshDashboardData(): Promise<ApiResponse<{ success: boolean }>> {
  try {
    console.log('Refreshing dashboard data');
    const response = await apiClient.post<{ success: boolean }>('/dashboard/refresh');
    console.log('Dashboard data refreshed successfully');
    return response;
  } catch (error) {
    console.error('Error refreshing dashboard data:', error);
    throw error;
  }
}
