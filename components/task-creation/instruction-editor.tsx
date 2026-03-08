'use client';

import React, { useState } from 'react';
import { RichTextEditor } from '@/components/ui/rich-text-editor';

export interface InstructionEditorProps {
  title: string;
  description: string;
  instructions: string;
  onTitleChange: (title: string) => void;
  onDescriptionChange: (description: string) => void;
  onInstructionsChange: (instructions: string) => void;
  errors?: {
    title?: string;
    description?: string;
    instructions?: string;
  };
  disabled?: boolean;
}

export function InstructionEditor({
  title,
  description,
  instructions,
  onTitleChange,
  onDescriptionChange,
  onInstructionsChange,
  errors,
  disabled = false,
}: InstructionEditorProps) {
  const [showPreview, setShowPreview] = useState(false);

  return (
    <div className="w-full space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Task Instructions
        </h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Provide clear and detailed instructions for completing the task
        </p>
      </div>

      {/* Title Input */}
      <div>
        <label htmlFor="title" className="block text-sm font-medium text-gray-900 dark:text-gray-100">
          Task Title <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          A short, descriptive title for your task (5-100 characters)
        </p>
        <input
          id="title"
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          disabled={disabled}
          placeholder="Enter a clear title for your task..."
          maxLength={100}
          className={`w-full rounded-lg border px-4 py-2 text-gray-900 transition-colors dark:bg-gray-800 dark:text-gray-100 ${
            errors?.title
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600'
          } ${disabled ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-700' : ''}`}
        />
        <div className="mt-1 flex items-center justify-between">
          {errors?.title ? (
            <p className="text-sm text-red-600 dark:text-red-400">{errors.title}</p>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {title.length} / 100 characters
            </p>
          )}
        </div>
      </div>

      {/* Description Input */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100"
        >
          Task Description <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          Brief description of what the task involves (20-500 characters)
        </p>
        <textarea
          id="description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          disabled={disabled}
          placeholder="Provide a brief description of the task..."
          rows={3}
          maxLength={500}
          className={`w-full rounded-lg border px-4 py-2 text-gray-900 transition-colors dark:bg-gray-800 dark:text-gray-100 ${
            errors?.description
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600'
          } ${disabled ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-700' : ''}`}
        />
        <div className="mt-1 flex items-center justify-between">
          {errors?.description ? (
            <p className="text-sm text-red-600 dark:text-red-400">{errors.description}</p>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {description.length} / 500 characters
            </p>
          )}
        </div>
      </div>

      {/* Detailed Instructions with Rich Text Editor */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
              Detailed Instructions <span className="text-red-500">*</span>
            </label>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Step-by-step instructions for completing the task (50-2000 characters)
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowPreview(!showPreview)}
            disabled={disabled}
            className="rounded-lg bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            {showPreview ? 'Edit' : 'Preview'}
          </button>
        </div>

        {showPreview ? (
          /* Preview Mode */
          <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-600 dark:bg-gray-800">
            <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
              Preview
            </h4>
            {instructions ? (
              <div
                className="prose prose-sm dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{ __html: instructions }}
              />
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No instructions provided yet...
              </p>
            )}
          </div>
        ) : (
          /* Editor Mode */
          <RichTextEditor
            value={instructions}
            onChange={onInstructionsChange}
            placeholder="Enter detailed, step-by-step instructions for completing this task..."
            maxLength={2000}
            minLength={50}
            error={errors?.instructions}
            disabled={disabled}
            showCharacterCount
            showToolbar
          />
        )}
      </div>

      {/* Help Text */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Tips for writing good instructions
            </h4>
            <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
              <ul className="list-inside list-disc space-y-1">
                <li>Be specific and clear about what needs to be done</li>
                <li>Break down complex tasks into simple steps</li>
                <li>Include any necessary links or references</li>
                <li>Specify what constitutes a completed task</li>
                <li>Mention any requirements for proof of completion</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
