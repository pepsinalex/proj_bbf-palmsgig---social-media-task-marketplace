'use client';

import React from 'react';

export type SortField = 'createdAt' | 'rewardPerAction' | 'budget' | 'totalSlots' | 'title';
export type SortOrder = 'asc' | 'desc';

export interface SortOption {
  field: SortField;
  order: SortOrder;
  label: string;
}

export interface SortOptionsProps {
  currentSort: SortOption;
  onSortChange: (sort: SortOption) => void;
  className?: string;
  disabled?: boolean;
}

const SORT_OPTIONS: SortOption[] = [
  { field: 'createdAt', order: 'desc', label: 'Newest First' },
  { field: 'createdAt', order: 'asc', label: 'Oldest First' },
  { field: 'rewardPerAction', order: 'desc', label: 'Highest Reward' },
  { field: 'rewardPerAction', order: 'asc', label: 'Lowest Reward' },
  { field: 'budget', order: 'desc', label: 'Highest Budget' },
  { field: 'budget', order: 'asc', label: 'Lowest Budget' },
  { field: 'totalSlots', order: 'desc', label: 'Most Slots' },
  { field: 'totalSlots', order: 'asc', label: 'Fewest Slots' },
  { field: 'title', order: 'asc', label: 'Title (A-Z)' },
  { field: 'title', order: 'desc', label: 'Title (Z-A)' },
];

export function SortOptions({
  currentSort,
  onSortChange,
  className = '',
  disabled = false,
}: SortOptionsProps) {
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedOption = SORT_OPTIONS.find((option) => {
      const value = `${option.field}-${option.order}`;
      return value === e.target.value;
    });

    if (selectedOption) {
      console.log(`Sort changed to: ${selectedOption.label}`);
      onSortChange(selectedOption);
    }
  };

  const currentValue = `${currentSort.field}-${currentSort.order}`;

  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      <label htmlFor="sort-select" className="text-sm font-medium text-gray-700">
        Sort by:
      </label>
      <div className="relative">
        <select
          id="sort-select"
          value={currentValue}
          onChange={handleSortChange}
          disabled={disabled}
          className="appearance-none rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm font-medium text-gray-900 transition-colors duration-200 hover:border-gray-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500"
          aria-label="Sort options"
        >
          {SORT_OPTIONS.map((option) => {
            const value = `${option.field}-${option.order}`;
            return (
              <option key={value} value={value}>
                {option.label}
              </option>
            );
          })}
        </select>

        {/* Custom dropdown arrow */}
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
          <svg
            className="h-5 w-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
