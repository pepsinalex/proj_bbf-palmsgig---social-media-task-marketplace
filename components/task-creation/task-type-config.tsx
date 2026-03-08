'use client';

import React, { useState } from 'react';
import type { Platform, TaskType } from '@/lib/validations/task';

export interface TaskTypeConfigProps {
  platform: Platform | null;
  selectedTaskType: TaskType | null;
  targetUrl: string;
  requirements: string[];
  onTaskTypeChange: (taskType: TaskType) => void;
  onTargetUrlChange: (url: string) => void;
  onRequirementsChange: (requirements: string[]) => void;
  errors?: {
    taskType?: string;
    targetUrl?: string;
    requirements?: string;
  };
  disabled?: boolean;
}

interface TaskTypeOption {
  id: TaskType;
  label: string;
  description: string;
}

const taskTypesByPlatform: Record<Platform, TaskTypeOption[]> = {
  instagram: [
    { id: 'like', label: 'Like Post', description: 'Like an Instagram post' },
    { id: 'comment', label: 'Comment', description: 'Comment on a post' },
    { id: 'follow', label: 'Follow Account', description: 'Follow an Instagram account' },
    { id: 'story_view', label: 'View Story', description: 'View an Instagram story' },
    { id: 'reel_view', label: 'View Reel', description: 'Watch an Instagram reel' },
    { id: 'save', label: 'Save Post', description: 'Save a post to collection' },
    { id: 'share', label: 'Share Post', description: 'Share a post with others' },
  ],
  twitter: [
    { id: 'like', label: 'Like Tweet', description: 'Like a tweet' },
    { id: 'retweet', label: 'Retweet', description: 'Retweet a tweet' },
    { id: 'comment', label: 'Reply', description: 'Reply to a tweet' },
    { id: 'follow', label: 'Follow Account', description: 'Follow a Twitter account' },
    { id: 'quote_tweet', label: 'Quote Tweet', description: 'Quote tweet with comment' },
    { id: 'bookmark', label: 'Bookmark', description: 'Bookmark a tweet' },
  ],
  facebook: [
    { id: 'like', label: 'Like Post', description: 'Like a Facebook post' },
    { id: 'comment', label: 'Comment', description: 'Comment on a post' },
    { id: 'share', label: 'Share Post', description: 'Share a post' },
    { id: 'follow', label: 'Follow', description: 'Follow a profile' },
    { id: 'reaction', label: 'React to Post', description: 'Add reaction to post' },
    { id: 'page_like', label: 'Like Page', description: 'Like a Facebook page' },
  ],
  tiktok: [
    { id: 'like', label: 'Like Video', description: 'Like a TikTok video' },
    { id: 'comment', label: 'Comment', description: 'Comment on a video' },
    { id: 'follow', label: 'Follow Account', description: 'Follow a TikTok account' },
    { id: 'share', label: 'Share Video', description: 'Share a video' },
    { id: 'duet', label: 'Create Duet', description: 'Create a duet video' },
    { id: 'stitch', label: 'Create Stitch', description: 'Create a stitch video' },
    { id: 'favorite', label: 'Add to Favorites', description: 'Add video to favorites' },
  ],
  youtube: [
    { id: 'like', label: 'Like Video', description: 'Like a YouTube video' },
    { id: 'comment', label: 'Comment', description: 'Comment on a video' },
    { id: 'subscribe', label: 'Subscribe', description: 'Subscribe to a channel' },
    { id: 'watch', label: 'Watch Video', description: 'Watch a video completely' },
    { id: 'share', label: 'Share Video', description: 'Share a video' },
    { id: 'playlist_add', label: 'Add to Playlist', description: 'Add video to playlist' },
  ],
};

export function TaskTypeConfig({
  platform,
  selectedTaskType,
  targetUrl,
  requirements,
  onTaskTypeChange,
  onTargetUrlChange,
  onRequirementsChange,
  errors,
  disabled = false,
}: TaskTypeConfigProps) {
  const [newRequirement, setNewRequirement] = useState('');

  if (!platform) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center dark:border-gray-700 dark:bg-gray-800">
        <p className="text-gray-600 dark:text-gray-400">
          Please select a platform first to configure task type
        </p>
      </div>
    );
  }

  const taskTypes = taskTypesByPlatform[platform];

  const handleAddRequirement = () => {
    if (newRequirement.trim() && requirements.length < 10) {
      onRequirementsChange([...requirements, newRequirement.trim()]);
      setNewRequirement('');
    }
  };

  const handleRemoveRequirement = (index: number) => {
    onRequirementsChange(requirements.filter((_, i) => i !== index));
  };

  return (
    <div className="w-full space-y-6">
      {/* Task Type Selection */}
      <div>
        <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Task Type <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {taskTypes.map((taskType) => {
            const isSelected = selectedTaskType === taskType.id;

            return (
              <button
                key={taskType.id}
                type="button"
                onClick={() => !disabled && onTaskTypeChange(taskType.id)}
                disabled={disabled}
                className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                  isSelected
                    ? 'border-primary-500 bg-primary-50 shadow-sm dark:bg-primary-900/20'
                    : 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600'
                } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
              >
                {isSelected && (
                  <div className="absolute right-3 top-3">
                    <svg
                      className="h-5 w-5 text-primary-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                )}
                <h4
                  className={`text-sm font-semibold ${
                    isSelected
                      ? 'text-primary-700 dark:text-primary-300'
                      : 'text-gray-900 dark:text-gray-100'
                  }`}
                >
                  {taskType.label}
                </h4>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                  {taskType.description}
                </p>
              </button>
            );
          })}
        </div>
        {errors?.taskType && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.taskType}</p>
        )}
      </div>

      {/* Target URL Input */}
      <div>
        <label
          htmlFor="targetUrl"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100"
        >
          Target URL <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          Enter the {platform} link where the task should be completed
        </p>
        <input
          id="targetUrl"
          type="url"
          value={targetUrl}
          onChange={(e) => onTargetUrlChange(e.target.value)}
          disabled={disabled}
          placeholder={`https://${platform}.com/...`}
          className={`w-full rounded-lg border px-4 py-2 text-gray-900 transition-colors dark:bg-gray-800 dark:text-gray-100 ${
            errors?.targetUrl
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600'
          } ${disabled ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-700' : ''}`}
        />
        {errors?.targetUrl && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.targetUrl}</p>
        )}
      </div>

      {/* Requirements List */}
      <div>
        <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
          Task Requirements <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          Add specific requirements for completing this task (max 10)
        </p>

        {/* Add Requirement Input */}
        <div className="mb-3 flex gap-2">
          <input
            type="text"
            value={newRequirement}
            onChange={(e) => setNewRequirement(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddRequirement()}
            disabled={disabled || requirements.length >= 10}
            placeholder="Enter a requirement..."
            maxLength={200}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
          />
          <button
            type="button"
            onClick={handleAddRequirement}
            disabled={disabled || !newRequirement.trim() || requirements.length >= 10}
            className="rounded-lg bg-primary-500 px-4 py-2 font-medium text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </div>

        {/* Requirements List */}
        {requirements.length > 0 && (
          <ul className="space-y-2">
            {requirements.map((req, index) => (
              <li
                key={index}
                className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <span className="flex-shrink-0 text-sm font-medium text-gray-500 dark:text-gray-400">
                  {index + 1}.
                </span>
                <span className="flex-1 text-sm text-gray-900 dark:text-gray-100">{req}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveRequirement(index)}
                  disabled={disabled}
                  className="flex-shrink-0 text-red-600 transition-colors hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-red-400"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}

        {requirements.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 p-4 text-center dark:border-gray-600">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No requirements added yet. Add at least one requirement.
            </p>
          </div>
        )}

        {errors?.requirements && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.requirements}</p>
        )}

        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {requirements.length} / 10 requirements
        </p>
      </div>
    </div>
  );
}
