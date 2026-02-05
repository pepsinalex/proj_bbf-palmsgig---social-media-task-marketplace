'use client';

import React from 'react';
import { Card, CardContent } from '../ui/card';
import type { Task } from '@/lib/types/api';

export interface TaskCardProps {
  task: Task;
  onClick?: (taskId: string) => void;
  className?: string;
  viewMode?: 'grid' | 'list';
}

export function TaskCard({ task, onClick, className = '', viewMode = 'grid' }: TaskCardProps) {
  const handleClick = () => {
    if (onClick) {
      console.log(`Task card clicked: ${task.id}`);
      onClick(task.id);
    }
  };

  const platformIcons: Record<string, string> = {
    instagram: '📷',
    twitter: '🐦',
    facebook: '👤',
    tiktok: '🎵',
    youtube: '▶️',
  };

  const taskTypeLabels: Record<string, string> = {
    post: 'Post',
    story: 'Story',
    reels: 'Reels',
    like: 'Like',
    comment: 'Comment',
    follow: 'Follow',
    share: 'Share',
    video: 'Video',
  };

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-blue-100 text-blue-700',
    cancelled: 'bg-red-100 text-red-700',
  };

  const availableSlots = task.totalSlots - task.filledSlots;
  const completionPercentage = (task.filledSlots / task.totalSlots) * 100;

  const isClickable = onClick !== undefined;

  if (viewMode === 'list') {
    return (
      <Card
        className={`transition-shadow hover:shadow-md ${isClickable ? 'cursor-pointer' : ''} ${className}`}
        onClick={isClickable ? handleClick : undefined}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        onKeyDown={
          isClickable
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleClick();
                }
              }
            : undefined
        }
      >
        <CardContent className="py-4">
          <div className="flex items-start space-x-4">
            {/* Platform Icon */}
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100 text-2xl">
                {platformIcons[task.platform] || '📱'}
              </div>
            </div>

            {/* Task Details */}
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">
                    {task.title}
                  </h3>
                  <p className="mt-1 text-sm text-gray-600 line-clamp-2">{task.description}</p>
                </div>

                {/* Status Badge */}
                <span
                  className={`ml-4 inline-flex flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${statusColors[task.status]}`}
                >
                  {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                </span>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center space-x-1 text-gray-600">
                  <span className="font-medium">Platform:</span>
                  <span className="capitalize">{task.platform}</span>
                </div>

                <div className="flex items-center space-x-1 text-gray-600">
                  <span className="font-medium">Type:</span>
                  <span>{taskTypeLabels[task.taskType]}</span>
                </div>

                <div className="flex items-center space-x-1 text-green-600">
                  <span className="font-medium">Reward:</span>
                  <span>${task.rewardPerAction.toFixed(2)}</span>
                </div>

                <div className="flex items-center space-x-1 text-sky-600">
                  <span className="font-medium">Available:</span>
                  <span>
                    {availableSlots} / {task.totalSlots}
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-3">
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full bg-sky-500 transition-all duration-300"
                    style={{ width: `${completionPercentage}%` }}
                    role="progressbar"
                    aria-valuenow={completionPercentage}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className={`transition-shadow hover:shadow-md ${isClickable ? 'cursor-pointer' : ''} ${className}`}
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleClick();
              }
            }
          : undefined
      }
    >
      <CardContent>
        {/* Header with Platform Icon and Status */}
        <div className="flex items-start justify-between">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100 text-2xl">
            {platformIcons[task.platform] || '📱'}
          </div>

          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusColors[task.status]}`}
          >
            {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
          </span>
        </div>

        {/* Task Title and Description */}
        <div className="mt-4">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">{task.title}</h3>
          <p className="mt-2 text-sm text-gray-600 line-clamp-3">{task.description}</p>
        </div>

        {/* Task Meta Information */}
        <div className="mt-4 space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Platform:</span>
            <span className="font-medium capitalize text-gray-900">{task.platform}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-600">Type:</span>
            <span className="font-medium text-gray-900">{taskTypeLabels[task.taskType]}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-600">Reward:</span>
            <span className="font-medium text-green-600">${task.rewardPerAction.toFixed(2)}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-600">Available Slots:</span>
            <span className="font-medium text-sky-600">
              {availableSlots} / {task.totalSlots}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between text-xs text-gray-600">
            <span>Progress</span>
            <span>{completionPercentage.toFixed(0)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-sky-500 transition-all duration-300"
              style={{ width: `${completionPercentage}%` }}
              role="progressbar"
              aria-valuenow={completionPercentage}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>

        {/* Footer with Budget Info */}
        <div className="mt-4 border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Budget</span>
            <span className="text-lg font-semibold text-gray-900">${task.budget.toFixed(2)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
