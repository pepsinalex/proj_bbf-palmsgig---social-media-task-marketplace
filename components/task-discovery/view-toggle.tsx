'use client';

import React from 'react';

export type ViewMode = 'grid' | 'list';

export interface ViewToggleProps {
  currentView: ViewMode;
  onViewChange: (view: ViewMode) => void;
  className?: string;
  disabled?: boolean;
}

export function ViewToggle({
  currentView,
  onViewChange,
  className = '',
  disabled = false,
}: ViewToggleProps) {
  const handleViewChange = (view: ViewMode) => {
    if (!disabled && view !== currentView) {
      console.log(`View mode changed to: ${view}`);
      onViewChange(view);
    }
  };

  const baseButtonClass =
    'flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50';

  const activeClass = 'bg-sky-500 text-white shadow-sm';
  const inactiveClass = 'bg-white text-gray-600 hover:bg-gray-50 hover:text-gray-900';

  return (
    <div
      className={`inline-flex space-x-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm ${className}`}
      role="group"
      aria-label="View mode toggle"
    >
      {/* Grid View Button */}
      <button
        type="button"
        onClick={() => handleViewChange('grid')}
        disabled={disabled}
        className={`${baseButtonClass} ${currentView === 'grid' ? activeClass : inactiveClass}`}
        aria-label="Grid view"
        aria-pressed={currentView === 'grid'}
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
          />
        </svg>
        <span className="ml-2">Grid</span>
      </button>

      {/* List View Button */}
      <button
        type="button"
        onClick={() => handleViewChange('list')}
        disabled={disabled}
        className={`${baseButtonClass} ${currentView === 'list' ? activeClass : inactiveClass}`}
        aria-label="List view"
        aria-pressed={currentView === 'list'}
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
        <span className="ml-2">List</span>
      </button>
    </div>
  );
}
