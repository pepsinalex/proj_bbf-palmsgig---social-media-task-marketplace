import { apiClient } from './client';
import type { ApiResponse } from '../types/api';

export interface Wallet {
  id: string;
  userId: string;
  balance: number;
  availableBalance: number;
  pendingBalance: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

export interface Transaction {
  id: string;
  walletId: string;
  type: 'deposit' | 'withdrawal' | 'earning' | 'payment' | 'refund';
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  description: string;
  reference?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface TransactionListParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  types?: string[];
  statuses?: string[];
  startDate?: string;
  endDate?: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

export interface DepositRequest {
  amount: number;
  paymentMethod: 'stripe' | 'paypal';
  returnUrl?: string;
}

export interface DepositResponse {
  transaction: Transaction;
  paymentUrl?: string;
  paymentIntentId?: string;
}

export interface WithdrawalRequest {
  amount: number;
  payoutMethod: 'bank_account' | 'paypal';
}

export interface WithdrawalResponse {
  transaction: Transaction;
  estimatedArrival?: string;
}

export const walletApi = {
  getWallet: async (): Promise<ApiResponse<Wallet>> => {
    return apiClient.get<Wallet>('/wallet');
  },

  getTransactions: async (
    params?: TransactionListParams
  ): Promise<ApiResponse<TransactionListResponse>> => {
    const queryParams = new URLSearchParams();

    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params?.sortOrder) queryParams.append('sortOrder', params.sortOrder);
    if (params?.types?.length) queryParams.append('types', params.types.join(','));
    if (params?.statuses?.length) queryParams.append('statuses', params.statuses.join(','));
    if (params?.startDate) queryParams.append('startDate', params.startDate);
    if (params?.endDate) queryParams.append('endDate', params.endDate);

    const queryString = queryParams.toString();
    const endpoint = queryString ? `/wallet/transactions?${queryString}` : '/wallet/transactions';

    return apiClient.get<TransactionListResponse>(endpoint);
  },

  getTransaction: async (transactionId: string): Promise<ApiResponse<Transaction>> => {
    return apiClient.get<Transaction>(`/wallet/transactions/${transactionId}`);
  },

  deposit: async (data: DepositRequest): Promise<ApiResponse<DepositResponse>> => {
    return apiClient.post<DepositResponse>('/wallet/deposit', data);
  },

  withdraw: async (data: WithdrawalRequest): Promise<ApiResponse<WithdrawalResponse>> => {
    return apiClient.post<WithdrawalResponse>('/wallet/withdraw', data);
  },

  refreshBalance: async (): Promise<ApiResponse<Wallet>> => {
    return apiClient.post<Wallet>('/wallet/refresh');
  },
};
