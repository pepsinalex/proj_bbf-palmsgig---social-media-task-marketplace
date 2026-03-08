'use client';

import React, { useState, useCallback, useRef } from 'react';

export interface UploadedFile {
  id: string;
  file: File;
  preview: string;
  progress: number;
  error?: string;
}

export interface ImageUploadProps {
  maxFiles?: number;
  maxSize?: number;
  accept?: string;
  onFilesChange?: (files: UploadedFile[]) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
  className?: string;
}

export function ImageUpload({
  maxFiles = 5,
  maxSize = 5 * 1024 * 1024,
  accept = 'image/*',
  onFilesChange,
  onError,
  disabled = false,
  className = '',
}: ImageUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      if (!file.type.startsWith('image/')) {
        return 'File must be an image';
      }

      if (file.size > maxSize) {
        const sizeMB = (maxSize / (1024 * 1024)).toFixed(1);
        return `File size must be less than ${sizeMB}MB`;
      }

      return null;
    },
    [maxSize]
  );

  const processFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;

      const newFiles: UploadedFile[] = [];
      const errors: string[] = [];

      Array.from(fileList).forEach((file) => {
        if (files.length + newFiles.length >= maxFiles) {
          errors.push(`Maximum ${maxFiles} files allowed`);
          return;
        }

        const error = validateFile(file);
        if (error) {
          errors.push(`${file.name}: ${error}`);
          return;
        }

        const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const preview = URL.createObjectURL(file);

        newFiles.push({
          id,
          file,
          preview,
          progress: 100,
        });
      });

      if (errors.length > 0 && onError) {
        onError(errors.join(', '));
      }

      if (newFiles.length > 0) {
        const updatedFiles = [...files, ...newFiles];
        setFiles(updatedFiles);
        if (onFilesChange) {
          onFilesChange(updatedFiles);
        }
      }
    },
    [files, maxFiles, validateFile, onError, onFilesChange]
  );

  const handleDragEnter = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragging(true);
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled) return;

      const droppedFiles = e.dataTransfer.files;
      processFiles(droppedFiles);
    },
    [disabled, processFiles]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      processFiles(e.target.files);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [processFiles]
  );

  const handleRemoveFile = useCallback(
    (fileId: string) => {
      const updatedFiles = files.filter((f) => {
        if (f.id === fileId) {
          URL.revokeObjectURL(f.preview);
          return false;
        }
        return true;
      });
      setFiles(updatedFiles);
      if (onFilesChange) {
        onFilesChange(updatedFiles);
      }
    },
    [files, onFilesChange]
  );

  const handleClick = useCallback(() => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [disabled]);

  return (
    <div className={`w-full ${className}`}>
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors
          ${
            isDragging
              ? 'border-sky-500 bg-sky-50 dark:border-sky-400 dark:bg-sky-900/20'
              : 'border-gray-300 hover:border-gray-400 dark:border-gray-600 dark:hover:border-gray-500'
          }
          ${disabled ? 'cursor-not-allowed opacity-50' : ''}
        `}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={maxFiles > 1}
          onChange={handleFileInputChange}
          disabled={disabled}
          className="hidden"
          aria-label="Upload images"
        />

        <div className="flex flex-col items-center space-y-2">
          <svg
            className="h-12 w-12 text-gray-400"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>

          <div className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-semibold text-sky-500">Click to upload</span> or drag and drop
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            PNG, JPG, GIF up to {(maxSize / (1024 * 1024)).toFixed(0)}MB
          </p>

          {maxFiles > 1 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {files.length} / {maxFiles} files
            </p>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {files.map((file) => (
            <div key={file.id} className="relative aspect-square overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
              <img
                src={file.preview}
                alt={file.file.name}
                className="h-full w-full object-cover"
              />

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveFile(file.id);
                }}
                className="absolute right-1 top-1 rounded-full bg-red-500 p-1 text-white shadow-lg transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                aria-label={`Remove ${file.file.name}`}
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              {file.error && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-500/90 p-2">
                  <p className="text-xs text-white">{file.error}</p>
                </div>
              )}

              {file.progress < 100 && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200">
                  <div
                    className="h-full bg-sky-500 transition-all duration-300"
                    style={{ width: `${file.progress}%` }}
                  />
                </div>
              )}

              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                <p className="truncate text-xs text-white">{file.file.name}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
