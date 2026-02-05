'use client';

import React, { use } from 'react';
import { useTaskDetails } from '@/hooks/use-task-details';
import { TaskHeader } from '@/components/task-details/task-header';
import { CreatorProfile } from '@/components/task-details/creator-profile';
import { RequirementsChecklist } from '@/components/task-details/requirements-checklist';
import { ProofSubmission } from '@/components/task-details/proof-submission';
import { StatusTracker } from '@/components/task-details/status-tracker';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function TaskDetailsPage({ params }: PageProps) {
  const { id } = use(params);
  const { task, isLoading, error, submitProof, claimTask, isSubmitting, refetch } =
    useTaskDetails(id);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-sky-500" />
          <p className="text-sm text-gray-600 dark:text-gray-400">Loading task details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent>
            <div className="py-8 text-center">
              <svg
                className="mx-auto h-12 w-12 text-red-500"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h2 className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                Error Loading Task
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{error}</p>
              <Button onClick={refetch} className="mt-4">
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardContent>
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
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h2 className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                Task Not Found
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                The task you're looking for doesn't exist or has been removed.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const canClaim = task.status === 'open' && task.availableSlots > 0;
  const canSubmitProof = task.status === 'in_progress';

  const handleClaimTask = async () => {
    try {
      await claimTask();
    } catch (error) {
      console.error('Failed to claim task:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Tasks
          </button>
        </div>

        <div className="space-y-6">
          <TaskHeader
            title={task.title}
            status={task.status}
            platform={task.platform}
            rewardPerAction={task.rewardPerAction}
            deadline={task.deadline}
            availableSlots={task.availableSlots}
            totalSlots={task.totalSlots}
            taskType={task.taskType}
          />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              <Card>
                <CardContent>
                  <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Description
                  </h3>
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <p className="text-gray-700 dark:text-gray-300">{task.description}</p>
                  </div>
                </CardContent>
              </Card>

              <RequirementsChecklist
                requirements={task.requirements.map((req) => ({
                  id: req.id,
                  description: req.description,
                  required: req.required,
                  completed: false,
                }))}
                readOnly={!canSubmitProof}
              />

              {canSubmitProof && (
                <ProofSubmission onSubmit={submitProof} isSubmitting={isSubmitting} />
              )}

              {canClaim && (
                <Card>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          Ready to Start?
                        </h3>
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                          Claim this task to begin working on it
                        </p>
                      </div>
                      <Button
                        onClick={handleClaimTask}
                        isLoading={isSubmitting}
                        disabled={isSubmitting}
                      >
                        Claim Task
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="space-y-6">
              <CreatorProfile
                name={task.creator.name}
                avatar={task.creator.avatar}
                rating={task.creator.rating}
                totalReviews={task.creator.totalReviews}
                tasksCompleted={task.creator.tasksCompleted}
                successRate={task.creator.successRate}
                verified={task.creator.verified}
                joinedDate={task.creator.joinedDate}
              />

              <StatusTracker
                currentStatus={
                  task.status === 'open'
                    ? 'open'
                    : task.status === 'in_progress'
                      ? 'claimed'
                      : task.status === 'completed'
                        ? 'completed'
                        : 'open'
                }
                events={[
                  {
                    id: '1',
                    status: 'open',
                    description: 'Task created and opened for claims',
                    timestamp: new Date(task.deadline).toISOString(),
                  },
                ]}
              />

              <Card>
                <CardContent>
                  <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Important Notes
                  </h4>
                  <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                    <li className="flex items-start gap-2">
                      <svg
                        className="h-5 w-5 flex-shrink-0 text-sky-500"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Complete all requirements before submitting proof
                    </li>
                    <li className="flex items-start gap-2">
                      <svg
                        className="h-5 w-5 flex-shrink-0 text-sky-500"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Upload clear screenshots as proof
                    </li>
                    <li className="flex items-start gap-2">
                      <svg
                        className="h-5 w-5 flex-shrink-0 text-sky-500"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Reward paid after approval
                    </li>
                    <li className="flex items-start gap-2">
                      <svg
                        className="h-5 w-5 flex-shrink-0 text-sky-500"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Submit before the deadline
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
