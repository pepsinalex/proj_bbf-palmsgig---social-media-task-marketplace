'use client';

import React from 'react';
import { Card, CardHeader, CardContent } from '../ui/card';
import { Progress, ProgressStep } from '../ui/progress';

export interface StatusEvent {
  id: string;
  status: string;
  description: string;
  timestamp: string;
}

export interface StatusTrackerProps {
  currentStatus: 'open' | 'claimed' | 'submitted' | 'approved' | 'rejected' | 'completed';
  events?: StatusEvent[];
  showTimeline?: boolean;
  className?: string;
}

const statusSteps: ProgressStep[] = [
  { id: 'open', label: 'Open', description: 'Task is available' },
  { id: 'claimed', label: 'Claimed', description: 'Task accepted' },
  { id: 'submitted', label: 'Submitted', description: 'Proof submitted' },
  { id: 'approved', label: 'Approved', description: 'Proof approved' },
  { id: 'completed', label: 'Completed', description: 'Reward paid' },
];

const statusIndex: Record<string, number> = {
  open: 0,
  claimed: 1,
  submitted: 2,
  approved: 3,
  rejected: 2,
  completed: 4,
};

export function StatusTracker({
  currentStatus,
  events = [],
  showTimeline = true,
  className = '',
}: StatusTrackerProps) {
  const currentStepIndex = statusIndex[currentStatus] ?? 0;
  const isRejected = currentStatus === 'rejected';

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-blue-600 dark:text-blue-400';
      case 'claimed':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'submitted':
        return 'text-purple-600 dark:text-purple-400';
      case 'approved':
        return 'text-green-600 dark:text-green-400';
      case 'rejected':
        return 'text-red-600 dark:text-red-400';
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        );
      case 'claimed':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'submitted':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        );
      case 'approved':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'rejected':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'completed':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M5 13l4 4L19 7" />
          </svg>
        );
      default:
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Task Status</h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Track your progress through the task lifecycle
        </p>
      </CardHeader>

      <CardContent>
        {isRejected && (
          <div className="mb-6 rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
            <div className="flex items-start gap-2">
              <svg
                className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-red-800 dark:text-red-300">
                  Proof Rejected
                </p>
                <p className="mt-1 text-sm text-red-700 dark:text-red-400">
                  Your submission was not approved. Please review the feedback and resubmit with
                  corrections.
                </p>
              </div>
            </div>
          </div>
        )}

        <Progress
          steps={statusSteps}
          currentStep={currentStepIndex}
          completedSteps={Array.from({ length: currentStepIndex }, (_, i) => i)}
        />

        {showTimeline && events.length > 0 && (
          <div className="mt-8">
            <h4 className="mb-4 text-sm font-medium text-gray-900 dark:text-gray-100">
              Activity Timeline
            </h4>
            <div className="space-y-4">
              {events.map((event, index) => {
                const isLast = index === events.length - 1;
                return (
                  <div key={event.id} className="relative flex gap-4">
                    {!isLast && (
                      <div className="absolute left-2.5 top-8 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
                    )}

                    <div
                      className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ${getStatusColor(event.status)}`}
                    >
                      {getStatusIcon(event.status)}
                    </div>

                    <div className="flex-1 pb-4">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {event.status.charAt(0).toUpperCase() +
                            event.status.slice(1).replace('_', ' ')}
                        </p>
                        <time className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(event.timestamp).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </time>
                      </div>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        {event.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
