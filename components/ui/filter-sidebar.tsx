'use client';

import React, { useState, useCallback } from 'react';
import { Button } from './button';

export interface FilterOption {
  label: string;
  value: string;
  count?: number;
}

export interface FilterGroup {
  id: string;
  label: string;
  options: FilterOption[];
  type: 'checkbox' | 'radio' | 'range';
  min?: number;
  max?: number;
  step?: number;
}

export interface FilterSidebarProps {
  filterGroups: FilterGroup[];
  selectedFilters: Record<string, string | string[] | number[]>;
  onFilterChange: (filterId: string, value: string | string[] | number[]) => void;
  onClearAll: () => void;
  onApply?: () => void;
  isLoading?: boolean;
  className?: string;
}

export function FilterSidebar({
  filterGroups,
  selectedFilters,
  onFilterChange,
  onClearAll,
  onApply,
  isLoading = false,
  className = '',
}: FilterSidebarProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(filterGroups.map((g) => g.id))
  );

  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
        console.log(`Filter group collapsed: ${groupId}`);
      } else {
        next.add(groupId);
        console.log(`Filter group expanded: ${groupId}`);
      }
      return next;
    });
  }, []);

  const handleCheckboxChange = useCallback(
    (groupId: string, optionValue: string) => {
      const currentValues = (selectedFilters[groupId] as string[]) || [];
      const newValues = currentValues.includes(optionValue)
        ? currentValues.filter((v) => v !== optionValue)
        : [...currentValues, optionValue];

      console.log(`Filter checkbox changed: ${groupId} = ${JSON.stringify(newValues)}`);
      onFilterChange(groupId, newValues);
    },
    [selectedFilters, onFilterChange]
  );

  const handleRadioChange = useCallback(
    (groupId: string, optionValue: string) => {
      console.log(`Filter radio changed: ${groupId} = ${optionValue}`);
      onFilterChange(groupId, optionValue);
    },
    [onFilterChange]
  );

  const handleRangeChange = useCallback(
    (groupId: string, rangeType: 'min' | 'max', value: number) => {
      const currentRange = (selectedFilters[groupId] as number[]) || [0, 0];
      const newRange: number[] = [...currentRange];

      if (rangeType === 'min') {
        newRange[0] = value;
      } else {
        newRange[1] = value;
      }

      console.log(`Filter range changed: ${groupId} = ${JSON.stringify(newRange)}`);
      onFilterChange(groupId, newRange);
    },
    [selectedFilters, onFilterChange]
  );

  const handleClearAll = useCallback(() => {
    console.log('All filters cleared');
    onClearAll();
  }, [onClearAll]);

  const handleApply = useCallback(() => {
    if (onApply) {
      console.log('Filters applied');
      onApply();
    }
  }, [onApply]);

  const hasActiveFilters = Object.values(selectedFilters).some((value) => {
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return value !== undefined && value !== null && value !== '';
  });

  return (
    <div className={`flex flex-col rounded-lg border border-gray-200 bg-white ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearAll}
              disabled={isLoading}
              className="text-sm font-medium text-sky-500 transition-colors hover:text-sky-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Filter Groups */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {filterGroups.map((group) => {
            const isExpanded = expandedGroups.has(group.id);

            return (
              <div key={group.id} className="border-b border-gray-100 pb-4 last:border-b-0">
                {/* Group Header */}
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className="flex w-full items-center justify-between py-2 text-left transition-colors hover:text-sky-600"
                  aria-expanded={isExpanded}
                  aria-controls={`filter-group-${group.id}`}
                >
                  <span className="font-medium text-gray-900">{group.label}</span>
                  <svg
                    className={`h-5 w-5 text-gray-400 transition-transform ${
                      isExpanded ? 'rotate-180' : ''
                    }`}
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
                </button>

                {/* Group Content */}
                {isExpanded && (
                  <div id={`filter-group-${group.id}`} className="mt-2 space-y-2">
                    {group.type === 'checkbox' &&
                      group.options.map((option) => {
                        const isChecked = (
                          (selectedFilters[group.id] as string[]) || []
                        ).includes(option.value);

                        return (
                          <label
                            key={option.value}
                            className="flex cursor-pointer items-center space-x-3 py-1 transition-colors hover:text-sky-600"
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleCheckboxChange(group.id, option.value)}
                              disabled={isLoading}
                              className="h-4 w-4 rounded border-gray-300 text-sky-500 transition-colors focus:ring-2 focus:ring-sky-500 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
                            />
                            <span className="flex-1 text-sm text-gray-700">{option.label}</span>
                            {option.count !== undefined && (
                              <span className="text-xs text-gray-400">({option.count})</span>
                            )}
                          </label>
                        );
                      })}

                    {group.type === 'radio' &&
                      group.options.map((option) => {
                        const isChecked = selectedFilters[group.id] === option.value;

                        return (
                          <label
                            key={option.value}
                            className="flex cursor-pointer items-center space-x-3 py-1 transition-colors hover:text-sky-600"
                          >
                            <input
                              type="radio"
                              name={group.id}
                              checked={isChecked}
                              onChange={() => handleRadioChange(group.id, option.value)}
                              disabled={isLoading}
                              className="h-4 w-4 border-gray-300 text-sky-500 transition-colors focus:ring-2 focus:ring-sky-500 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
                            />
                            <span className="flex-1 text-sm text-gray-700">{option.label}</span>
                            {option.count !== undefined && (
                              <span className="text-xs text-gray-400">({option.count})</span>
                            )}
                          </label>
                        );
                      })}

                    {group.type === 'range' && (
                      <div className="space-y-3 pt-2">
                        <div className="space-y-2">
                          <label htmlFor={`${group.id}-min`} className="text-xs text-gray-600">
                            Min: {((selectedFilters[group.id] as number[]) || [])[0] || group.min || 0}
                          </label>
                          <input
                            id={`${group.id}-min`}
                            type="range"
                            min={group.min || 0}
                            max={group.max || 100}
                            step={group.step || 1}
                            value={((selectedFilters[group.id] as number[]) || [])[0] || group.min || 0}
                            onChange={(e) =>
                              handleRangeChange(group.id, 'min', parseFloat(e.target.value))
                            }
                            disabled={isLoading}
                            className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                          />
                        </div>
                        <div className="space-y-2">
                          <label htmlFor={`${group.id}-max`} className="text-xs text-gray-600">
                            Max: {((selectedFilters[group.id] as number[]) || [])[1] || group.max || 100}
                          </label>
                          <input
                            id={`${group.id}-max`}
                            type="range"
                            min={group.min || 0}
                            max={group.max || 100}
                            step={group.step || 1}
                            value={((selectedFilters[group.id] as number[]) || [])[1] || group.max || 100}
                            onChange={(e) =>
                              handleRangeChange(group.id, 'max', parseFloat(e.target.value))
                            }
                            disabled={isLoading}
                            className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer with Apply Button */}
      {onApply && (
        <div className="border-t border-gray-200 p-4">
          <Button
            onClick={handleApply}
            disabled={isLoading || !hasActiveFilters}
            isLoading={isLoading}
            fullWidth
            variant="primary"
          >
            Apply Filters
          </Button>
        </div>
      )}
    </div>
  );
}
