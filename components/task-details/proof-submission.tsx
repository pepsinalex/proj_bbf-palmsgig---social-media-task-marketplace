'use client';

import React, { useState, useCallback } from 'react';
import { Card, CardHeader, CardContent } from '../ui/card';
import { ImageUpload, UploadedFile } from '../ui/image-upload';
import { Button } from '../ui/button';

export interface ProofSubmissionProps {
  onSubmit?: (data: { images: UploadedFile[]; description: string; link?: string }) => Promise<void>;
  isSubmitting?: boolean;
  disabled?: boolean;
  className?: string;
}

export function ProofSubmission({
  onSubmit,
  isSubmitting = false,
  disabled = false,
  className = '',
}: ProofSubmissionProps) {
  const [images, setImages] = useState<UploadedFile[]>([]);
  const [description, setDescription] = useState('');
  const [link, setLink] = useState('');
  const [errors, setErrors] = useState<{ images?: string; description?: string; link?: string }>({});
  const [submitError, setSubmitError] = useState<string>('');
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const validateForm = useCallback((): boolean => {
    const newErrors: typeof errors = {};

    if (images.length === 0) {
      newErrors.images = 'At least one image is required';
    }

    if (!description.trim()) {
      newErrors.description = 'Description is required';
    } else if (description.trim().length < 20) {
      newErrors.description = 'Description must be at least 20 characters';
    }

    if (link && !isValidUrl(link)) {
      newErrors.link = 'Please enter a valid URL';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [images, description, link]);

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError('');
      setSubmitSuccess(false);

      if (!validateForm()) {
        return;
      }

      if (!onSubmit) {
        return;
      }

      try {
        await onSubmit({
          images,
          description: description.trim(),
          link: link.trim() || undefined,
        });
        setSubmitSuccess(true);
        setImages([]);
        setDescription('');
        setLink('');
      } catch (error) {
        console.error('Proof submission error:', error);
        setSubmitError(error instanceof Error ? error.message : 'Failed to submit proof');
      }
    },
    [images, description, link, validateForm, onSubmit]
  );

  const handleImagesChange = useCallback((newImages: UploadedFile[]) => {
    setImages(newImages);
    setErrors((prev) => ({ ...prev, images: undefined }));
  }, []);

  const handleDescriptionChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDescription(e.target.value);
    setErrors((prev) => ({ ...prev, description: undefined }));
  }, []);

  const handleLinkChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setLink(e.target.value);
    setErrors((prev) => ({ ...prev, link: undefined }));
  }, []);

  const handleImageError = useCallback((error: string) => {
    setErrors((prev) => ({ ...prev, images: error }));
  }, []);

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Submit Your Proof
        </h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Upload screenshots or images showing you completed the task
        </p>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Upload Images <span className="text-red-500">*</span>
            </label>
            <ImageUpload
              maxFiles={5}
              maxSize={5 * 1024 * 1024}
              onFilesChange={handleImagesChange}
              onError={handleImageError}
              disabled={disabled || isSubmitting}
            />
            {errors.images && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.images}</p>
            )}
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Upload clear screenshots showing you completed the task. Maximum 5 images, 5MB each.
            </p>
          </div>

          <div>
            <label
              htmlFor="proof-description"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="proof-description"
              rows={4}
              value={description}
              onChange={handleDescriptionChange}
              disabled={disabled || isSubmitting}
              className={`
                w-full rounded-lg border px-4 py-2 text-sm transition-colors
                focus:outline-none focus:ring-2 focus:ring-sky-500
                disabled:cursor-not-allowed disabled:opacity-50
                ${
                  errors.description
                    ? 'border-red-300 dark:border-red-700'
                    : 'border-gray-300 dark:border-gray-600'
                }
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
              `}
              placeholder="Describe what you did to complete this task..."
              aria-invalid={!!errors.description}
              aria-describedby={errors.description ? 'description-error' : undefined}
            />
            {errors.description && (
              <p id="description-error" className="mt-2 text-sm text-red-600 dark:text-red-400">
                {errors.description}
              </p>
            )}
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Minimum 20 characters. Be specific about what you did.
            </p>
          </div>

          <div>
            <label
              htmlFor="proof-link"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Link (Optional)
            </label>
            <input
              id="proof-link"
              type="url"
              value={link}
              onChange={handleLinkChange}
              disabled={disabled || isSubmitting}
              className={`
                w-full rounded-lg border px-4 py-2 text-sm transition-colors
                focus:outline-none focus:ring-2 focus:ring-sky-500
                disabled:cursor-not-allowed disabled:opacity-50
                ${
                  errors.link
                    ? 'border-red-300 dark:border-red-700'
                    : 'border-gray-300 dark:border-gray-600'
                }
                bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
              `}
              placeholder="https://example.com/your-post"
              aria-invalid={!!errors.link}
              aria-describedby={errors.link ? 'link-error' : undefined}
            />
            {errors.link && (
              <p id="link-error" className="mt-2 text-sm text-red-600 dark:text-red-400">
                {errors.link}
              </p>
            )}
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Add a link to your post, video, or other relevant content
            </p>
          </div>

          {submitError && (
            <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
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
                <p className="text-sm text-red-800 dark:text-red-300">{submitError}</p>
              </div>
            </div>
          )}

          {submitSuccess && (
            <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
              <div className="flex items-start gap-2">
                <svg
                  className="h-5 w-5 flex-shrink-0 text-green-600 dark:text-green-400"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-green-800 dark:text-green-300">
                  Proof submitted successfully! It will be reviewed shortly.
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button
              type="submit"
              disabled={disabled || isSubmitting}
              isLoading={isSubmitting}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Proof'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
