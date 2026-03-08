'use client';

import React, { useState } from 'react';
import { Table, TableColumn } from '../ui/table';

export type TransactionType = 'deposit' | 'withdrawal' | 'earning' | 'payment' | 'refund';
export type TransactionStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

export interface Transaction {
  id: string;
  date: string;
  type: TransactionType;
  amount: number;
  status: TransactionStatus;
  description: string;
  reference?: string;
  currency?: string;
}

export interface TransactionTableProps {
  transactions: Transaction[];
  loading?: boolean;
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  onViewDetails?: (transaction: Transaction) => void;
  currency?: string;
  className?: string;
}

export function TransactionTable({
  transactions,
  loading = false,
  currentPage = 1,
  totalPages = 1,
  onPageChange,
  sortBy,
  sortOrder = 'asc',
  onSort,
  onViewDetails,
  currency = 'USD',
  className = '',
}: TransactionTableProps) {
  const [, setSelectedTransaction] = useState<Transaction | null>(null);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getTypeIcon = (type: TransactionType) => {
    switch (type) {
      case 'deposit':
        return (
          <svg className="h-5 w-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        );
      case 'withdrawal':
        return (
          <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        );
      case 'earning':
        return (
          <svg className="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      case 'payment':
        return (
          <svg
            className="h-5 w-5 text-purple-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
        );
      case 'refund':
        return (
          <svg
            className="h-5 w-5 text-orange-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
            />
          </svg>
        );
    }
  };

  const getTypeBadge = (type: TransactionType) => {
    const badges = {
      deposit: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
      withdrawal: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
      earning: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
      payment: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
      refund: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
    };

    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${badges[type]}`}
      >
        {getTypeIcon(type)}
        {type.charAt(0).toUpperCase() + type.slice(1)}
      </span>
    );
  };

  const getStatusBadge = (status: TransactionStatus) => {
    const badges = {
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
      completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    };

    return (
      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badges[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const handleViewDetails = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    if (onViewDetails) {
      onViewDetails(transaction);
    }
  };

  const columns: TableColumn<Transaction>[] = [
    {
      key: 'date',
      header: 'Date',
      sortable: true,
      render: (transaction) => (
        <div className="flex flex-col">
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {formatDate(transaction.date).split(',')[0]}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatDate(transaction.date).split(',')[1]}
          </span>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      render: (transaction) => getTypeBadge(transaction.type),
    },
    {
      key: 'description',
      header: 'Description',
      sortable: false,
      render: (transaction) => (
        <div className="flex flex-col">
          <span className="text-sm text-gray-900 dark:text-white">{transaction.description}</span>
          {transaction.reference && (
            <span className="text-xs text-gray-500 dark:text-gray-400">Ref: {transaction.reference}</span>
          )}
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      sortable: true,
      align: 'right',
      render: (transaction) => {
        const isPositive = transaction.type === 'deposit' || transaction.type === 'earning' || transaction.type === 'refund';
        return (
          <span
            className={`text-sm font-semibold ${
              isPositive
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {isPositive ? '+' : '-'}
            {formatCurrency(Math.abs(transaction.amount))}
          </span>
        );
      },
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      align: 'center',
      render: (transaction) => getStatusBadge(transaction.status),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      align: 'center',
      render: (transaction) => (
        <button
          onClick={() => handleViewDetails(transaction)}
          className="text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
        </button>
      ),
    },
  ];

  return (
    <div className={className}>
      <Table
        columns={columns}
        data={transactions}
        loading={loading}
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={onPageChange}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={onSort}
        emptyMessage="No transactions found"
        striped={true}
        hoverable={true}
      />
    </div>
  );
}
