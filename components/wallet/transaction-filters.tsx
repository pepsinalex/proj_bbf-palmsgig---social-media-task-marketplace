'use client';

import React from 'react';
import { Button } from '../ui/button';
import { TransactionType, TransactionStatus } from './transaction-table';

export interface TransactionFiltersProps {
  selectedTypes: TransactionType[];
  selectedStatuses: TransactionStatus[];
  startDate?: string;
  endDate?: string;
  onTypeChange: (types: TransactionType[]) => void;
  onStatusChange: (statuses: TransactionStatus[]) => void;
  onDateRangeChange: (startDate: string, endDate: string) => void;
  onClearFilters: () => void;
  className?: string;
}

export function TransactionFilters({
  selectedTypes,
  selectedStatuses,
  startDate = '',
  endDate = '',
  onTypeChange,
  onStatusChange,
  onDateRangeChange,
  onClearFilters,
  className = '',
}: TransactionFiltersProps) {
  const types: { value: TransactionType; label: string }[] = [
    { value: 'deposit', label: 'Deposit' },
    { value: 'withdrawal', label: 'Withdrawal' },
    { value: 'earning', label: 'Earning' },
    { value: 'payment', label: 'Payment' },
    { value: 'refund', label: 'Refund' },
  ];

  const statuses: { value: TransactionStatus; label: string }[] = [
    { value: 'pending', label: 'Pending' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'cancelled', label: 'Cancelled' },
  ];

  const handleTypeToggle = (type: TransactionType) => {
    if (selectedTypes.includes(type)) {
      onTypeChange(selectedTypes.filter((t) => t !== type));
    } else {
      onTypeChange([...selectedTypes, type]);
    }
  };

  const handleStatusToggle = (status: TransactionStatus) => {
    if (selectedStatuses.includes(status)) {
      onStatusChange(selectedStatuses.filter((s) => s !== status));
    } else {
      onStatusChange([...selectedStatuses, status]);
    }
  };

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onDateRangeChange(e.target.value, endDate);
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onDateRangeChange(startDate, e.target.value);
  };

  const hasActiveFilters =
    selectedTypes.length > 0 || selectedStatuses.length > 0 || startDate || endDate;

  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800 ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filters</h3>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={onClearFilters}>
            Clear All
          </Button>
        )}
      </div>

      <div className="space-y-6">
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Transaction Type
          </label>
          <div className="flex flex-wrap gap-2">
            {types.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => handleTypeToggle(type.value)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
                  selectedTypes.includes(type.value)
                    ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Status
          </label>
          <div className="flex flex-wrap gap-2">
            {statuses.map((status) => (
              <button
                key={status.value}
                type="button"
                onClick={() => handleStatusToggle(status.value)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
                  selectedStatuses.includes(status.value)
                    ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {status.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Date Range
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="start-date" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
                From
              </label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={handleStartDateChange}
                max={endDate || undefined}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
                To
              </label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={handleEndDateChange}
                min={startDate || undefined}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
