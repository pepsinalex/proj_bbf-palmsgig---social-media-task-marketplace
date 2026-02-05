'use client';

import React from 'react';
import { Card, CardHeader, CardContent } from '../ui/card';

export interface Requirement {
  id: string;
  description: string;
  completed?: boolean;
  required?: boolean;
}

export interface RequirementsChecklistProps {
  requirements: Requirement[];
  onRequirementToggle?: (requirementId: string, completed: boolean) => void;
  readOnly?: boolean;
  showProgress?: boolean;
  className?: string;
}

export function RequirementsChecklist({
  requirements,
  onRequirementToggle,
  readOnly = false,
  showProgress = true,
  className = '',
}: RequirementsChecklistProps) {
  const completedCount = requirements.filter((req) => req.completed).length;
  const totalCount = requirements.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  const handleToggle = (requirementId: string, currentState: boolean) => {
    if (!readOnly && onRequirementToggle) {
      onRequirementToggle(requirementId, !currentState);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Task Requirements
          </h3>
          {showProgress && (
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
              {completedCount} / {totalCount} completed
            </span>
          )}
        </div>
        {showProgress && (
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="h-full bg-sky-500 transition-all duration-300 ease-in-out"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {requirements.length === 0 ? (
            <div className="py-8 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                No requirements specified
              </p>
            </div>
          ) : (
            requirements.map((requirement) => (
              <div
                key={requirement.id}
                className={`
                  flex items-start gap-3 rounded-lg border p-4 transition-all
                  ${
                    requirement.completed
                      ? 'border-green-200 bg-green-50 dark:border-green-900/30 dark:bg-green-900/10'
                      : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800/50'
                  }
                  ${!readOnly ? 'hover:border-gray-300 dark:hover:border-gray-600' : ''}
                `}
              >
                <div className="flex-shrink-0 pt-0.5">
                  {readOnly ? (
                    <div
                      className={`
                        flex h-5 w-5 items-center justify-center rounded border-2
                        ${
                          requirement.completed
                            ? 'border-green-500 bg-green-500'
                            : 'border-gray-300 dark:border-gray-600'
                        }
                      `}
                    >
                      {requirement.completed && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="none"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="3"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleToggle(requirement.id, requirement.completed || false)}
                      className={`
                        flex h-5 w-5 items-center justify-center rounded border-2 transition-all
                        focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2
                        ${
                          requirement.completed
                            ? 'border-green-500 bg-green-500 hover:bg-green-600'
                            : 'border-gray-300 hover:border-sky-500 dark:border-gray-600'
                        }
                      `}
                      aria-label={`Mark "${requirement.description}" as ${requirement.completed ? 'incomplete' : 'complete'}`}
                    >
                      {requirement.completed && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="none"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="3"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className={`
                        text-sm
                        ${
                          requirement.completed
                            ? 'text-gray-600 line-through dark:text-gray-400'
                            : 'text-gray-900 dark:text-gray-100'
                        }
                      `}
                    >
                      {requirement.description}
                    </p>
                    {requirement.required && (
                      <span className="flex-shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
                        Required
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {!readOnly && requirements.length > 0 && (
          <div className="mt-4 rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
            <div className="flex items-start gap-2">
              <svg
                className="h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-blue-900 dark:text-blue-300">
                Make sure to complete all required items before submitting your proof.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
