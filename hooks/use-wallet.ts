'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { walletApi, type TransactionListParams, type DepositRequest, type WithdrawalRequest } from '../lib/api/wallet';

export function useWallet() {
  const queryClient = useQueryClient();

  const {
    data: walletData,
    isLoading: isLoadingWallet,
    error: walletError,
    refetch: refetchWallet,
  } = useQuery({
    queryKey: ['wallet'],
    queryFn: async () => {
      const response = await walletApi.getWallet();
      return response.data;
    },
    staleTime: 30000,
  });

  const refreshBalance = useMutation({
    mutationFn: async () => {
      const response = await walletApi.refreshBalance();
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['wallet'], data);
    },
  });

  return {
    wallet: walletData,
    isLoadingWallet,
    walletError,
    refetchWallet,
    refreshBalance: refreshBalance.mutate,
    isRefreshing: refreshBalance.isPending,
  };
}

export function useTransactions(params?: TransactionListParams) {
  const {
    data: transactionsData,
    isLoading: isLoadingTransactions,
    error: transactionsError,
    refetch: refetchTransactions,
  } = useQuery({
    queryKey: ['transactions', params],
    queryFn: async () => {
      const response = await walletApi.getTransactions(params);
      return response.data;
    },
    staleTime: 10000,
  });

  return {
    transactions: transactionsData?.transactions || [],
    pagination: transactionsData?.pagination,
    isLoadingTransactions,
    transactionsError,
    refetchTransactions,
  };
}

export function useTransaction(transactionId?: string) {
  const {
    data: transactionData,
    isLoading: isLoadingTransaction,
    error: transactionError,
  } = useQuery({
    queryKey: ['transaction', transactionId],
    queryFn: async () => {
      if (!transactionId) throw new Error('Transaction ID is required');
      const response = await walletApi.getTransaction(transactionId);
      return response.data;
    },
    enabled: !!transactionId,
  });

  return {
    transaction: transactionData,
    isLoadingTransaction,
    transactionError,
  };
}

export function useDeposit() {
  const queryClient = useQueryClient();

  const deposit = useMutation({
    mutationFn: async (data: DepositRequest) => {
      const response = await walletApi.deposit(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });

  return {
    deposit: deposit.mutate,
    depositAsync: deposit.mutateAsync,
    isDepositing: deposit.isPending,
    depositError: deposit.error,
    depositData: deposit.data,
  };
}

export function useWithdraw() {
  const queryClient = useQueryClient();

  const withdraw = useMutation({
    mutationFn: async (data: WithdrawalRequest) => {
      const response = await walletApi.withdraw(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });

  return {
    withdraw: withdraw.mutate,
    withdrawAsync: withdraw.mutateAsync,
    isWithdrawing: withdraw.isPending,
    withdrawError: withdraw.error,
    withdrawData: withdraw.data,
  };
}
