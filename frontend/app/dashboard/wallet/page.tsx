'use client';

import React, { useState, useEffect } from 'react';
import { BalanceCard } from '@/components/wallet/balance-card';
import { TransactionTable, type Transaction, type TransactionType, type TransactionStatus } from '@/components/wallet/transaction-table';
import { TransactionFilters } from '@/components/wallet/transaction-filters';
import { DepositModal } from '@/components/wallet/deposit-modal';
import { WithdrawalModal } from '@/components/wallet/withdrawal-modal';
import { useWallet, useTransactions, useDeposit, useWithdraw } from '@/hooks/use-wallet';
import type { PaymentMethod } from '@/components/wallet/deposit-modal';
import type { PayoutMethod } from '@/components/wallet/withdrawal-modal';

export default function WalletPage() {
  const [isDepositModalOpen, setIsDepositModalOpen] = useState(false);
  const [isWithdrawalModalOpen, setIsWithdrawalModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedTypes, setSelectedTypes] = useState<TransactionType[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<TransactionStatus[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { wallet, isLoadingWallet, refreshBalance, isRefreshing } = useWallet();

  const {
    transactions,
    pagination,
    isLoadingTransactions,
    refetchTransactions,
  } = useTransactions({
    page: currentPage,
    limit: 10,
    sortBy,
    sortOrder,
    types: selectedTypes.length > 0 ? selectedTypes : undefined,
    statuses: selectedStatuses.length > 0 ? selectedStatuses : undefined,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
  });

  const { depositAsync, isDepositing } = useDeposit();
  const { withdrawAsync, isWithdrawing } = useWithdraw();

  useEffect(() => {
    const interval = setInterval(() => {
      if (!isRefreshing && wallet) {
        refreshBalance();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isRefreshing, wallet, refreshBalance]);

  const handleDeposit = async (amount: number, paymentMethod: PaymentMethod) => {
    try {
      const result = await depositAsync({
        amount,
        paymentMethod,
        returnUrl: window.location.href,
      });

      if (result.paymentUrl) {
        window.location.href = result.paymentUrl;
      }
    } catch (error) {
      console.error('Deposit failed:', error);
      throw error;
    }
  };

  const handleWithdraw = async (amount: number, payoutMethod: PayoutMethod) => {
    try {
      await withdrawAsync({
        amount,
        payoutMethod,
      });
    } catch (error) {
      console.error('Withdrawal failed:', error);
      throw error;
    }
  };

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleDateRangeChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setSelectedTypes([]);
    setSelectedStatuses([]);
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
  };

  const handleViewDetails = (transaction: Transaction) => {
    console.log('View transaction details:', transaction);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Wallet</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Manage your funds and view transaction history
          </p>
        </div>

        <div className="space-y-6">
          <BalanceCard
            totalBalance={wallet?.balance || 0}
            availableBalance={wallet?.availableBalance || 0}
            pendingBalance={wallet?.pendingBalance || 0}
            currency={wallet?.currency || 'USD'}
            onDeposit={() => setIsDepositModalOpen(true)}
            onWithdraw={() => setIsWithdrawalModalOpen(true)}
            loading={isLoadingWallet}
          />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            <div className="lg:col-span-1">
              <TransactionFilters
                selectedTypes={selectedTypes}
                selectedStatuses={selectedStatuses}
                startDate={startDate}
                endDate={endDate}
                onTypeChange={setSelectedTypes}
                onStatusChange={setSelectedStatuses}
                onDateRangeChange={handleDateRangeChange}
                onClearFilters={handleClearFilters}
              />
            </div>

            <div className="lg:col-span-3">
              <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
                <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Transaction History
                    </h2>
                    <button
                      onClick={() => refetchTransactions()}
                      disabled={isLoadingTransactions}
                      className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-700"
                      aria-label="Refresh transactions"
                    >
                      <svg
                        className={`h-5 w-5 ${isLoadingTransactions ? 'animate-spin' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                    </button>
                  </div>
                </div>

                <TransactionTable
                  transactions={transactions}
                  loading={isLoadingTransactions}
                  currentPage={currentPage}
                  totalPages={pagination?.totalPages || 1}
                  onPageChange={handlePageChange}
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={handleSort}
                  onViewDetails={handleViewDetails}
                  currency={wallet?.currency || 'USD'}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <DepositModal
        isOpen={isDepositModalOpen}
        onClose={() => setIsDepositModalOpen(false)}
        onDeposit={handleDeposit}
        currency={wallet?.currency || 'USD'}
      />

      <WithdrawalModal
        isOpen={isWithdrawalModalOpen}
        onClose={() => setIsWithdrawalModalOpen(false)}
        onWithdraw={handleWithdraw}
        availableBalance={wallet?.availableBalance || 0}
        currency={wallet?.currency || 'USD'}
      />
    </div>
  );
}
