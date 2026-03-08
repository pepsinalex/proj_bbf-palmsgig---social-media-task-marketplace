'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';

export interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
  minLength?: number;
  error?: string;
  disabled?: boolean;
  className?: string;
  showCharacterCount?: boolean;
  showToolbar?: boolean;
}

type FormatType = 'bold' | 'italic' | 'underline' | 'orderedList' | 'unorderedList';

export function RichTextEditor({
  value,
  onChange,
  placeholder = 'Enter text...',
  maxLength,
  minLength,
  error,
  disabled = false,
  className = '',
  showCharacterCount = true,
  showToolbar = true,
}: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [characterCount, setCharacterCount] = useState(0);
  const [activeFormats, setActiveFormats] = useState<Set<FormatType>>(new Set());

  // Initialize editor content
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      const selection = window.getSelection();
      const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
      const startOffset = range?.startOffset ?? 0;

      editorRef.current.innerHTML = value || '';

      // Restore cursor position if possible
      if (range && editorRef.current.firstChild) {
        try {
          const newRange = document.createRange();
          const textNode = editorRef.current.firstChild;
          newRange.setStart(textNode, Math.min(startOffset, textNode.textContent?.length ?? 0));
          newRange.collapse(true);
          selection?.removeAllRanges();
          selection?.addRange(newRange);
        } catch {
          // Silently fail if cursor position cannot be restored
        }
      }
    }
  }, [value]);

  // Update character count
  useEffect(() => {
    if (editorRef.current) {
      const text = editorRef.current.textContent || '';
      setCharacterCount(text.length);
    }
  }, [value]);

  const handleInput = useCallback(() => {
    if (!editorRef.current) return;

    const html = editorRef.current.innerHTML;
    const text = editorRef.current.textContent || '';

    // Check max length
    if (maxLength && text.length > maxLength) {
      // Restore previous value
      editorRef.current.innerHTML = value;
      return;
    }

    setCharacterCount(text.length);
    onChange(html);
  }, [onChange, value, maxLength]);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
  }, []);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    updateActiveFormats();
  }, []);

  const updateActiveFormats = useCallback(() => {
    const formats = new Set<FormatType>();

    if (document.queryCommandState('bold')) formats.add('bold');
    if (document.queryCommandState('italic')) formats.add('italic');
    if (document.queryCommandState('underline')) formats.add('underline');
    if (document.queryCommandState('insertOrderedList')) formats.add('orderedList');
    if (document.queryCommandState('insertUnorderedList')) formats.add('unorderedList');

    setActiveFormats(formats);
  }, []);

  const handleKeyUp = useCallback(() => {
    updateActiveFormats();
  }, [updateActiveFormats]);

  const handleMouseUp = useCallback(() => {
    updateActiveFormats();
  }, [updateActiveFormats]);

  const applyFormat = useCallback(
    (format: FormatType) => {
      if (disabled) return;

      const commandMap: Record<FormatType, string> = {
        bold: 'bold',
        italic: 'italic',
        underline: 'underline',
        orderedList: 'insertOrderedList',
        unorderedList: 'insertUnorderedList',
      };

      document.execCommand(commandMap[format], false);
      editorRef.current?.focus();
      updateActiveFormats();
      handleInput();
    },
    [disabled, handleInput, updateActiveFormats]
  );

  const isValid = useCallback(() => {
    const text = editorRef.current?.textContent || '';
    if (minLength && text.length < minLength) return false;
    if (maxLength && text.length > maxLength) return false;
    return true;
  }, [minLength, maxLength]);

  const getCharacterCountColor = useCallback(() => {
    if (!maxLength) return 'text-gray-500 dark:text-gray-400';
    const percentage = (characterCount / maxLength) * 100;
    if (percentage >= 100) return 'text-red-600 dark:text-red-400';
    if (percentage >= 90) return 'text-orange-600 dark:text-orange-400';
    return 'text-gray-500 dark:text-gray-400';
  }, [characterCount, maxLength]);

  return (
    <div className={`w-full ${className}`}>
      {/* Toolbar */}
      {showToolbar && (
        <div className="mb-2 flex flex-wrap gap-1 rounded-t-lg border border-b-0 border-gray-300 bg-gray-50 p-2 dark:border-gray-600 dark:bg-gray-700">
          <button
            type="button"
            onClick={() => applyFormat('bold')}
            disabled={disabled}
            className={`rounded px-3 py-1 text-sm font-semibold transition-colors ${
              activeFormats.has('bold')
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500'
            } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            title="Bold"
          >
            <span className="font-bold">B</span>
          </button>

          <button
            type="button"
            onClick={() => applyFormat('italic')}
            disabled={disabled}
            className={`rounded px-3 py-1 text-sm transition-colors ${
              activeFormats.has('italic')
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500'
            } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            title="Italic"
          >
            <span className="italic">I</span>
          </button>

          <button
            type="button"
            onClick={() => applyFormat('underline')}
            disabled={disabled}
            className={`rounded px-3 py-1 text-sm transition-colors ${
              activeFormats.has('underline')
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500'
            } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            title="Underline"
          >
            <span className="underline">U</span>
          </button>

          <div className="mx-2 h-6 w-px bg-gray-300 dark:bg-gray-500" />

          <button
            type="button"
            onClick={() => applyFormat('unorderedList')}
            disabled={disabled}
            className={`rounded px-3 py-1 text-sm transition-colors ${
              activeFormats.has('unorderedList')
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500'
            } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            title="Bullet List"
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
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <button
            type="button"
            onClick={() => applyFormat('orderedList')}
            disabled={disabled}
            className={`rounded px-3 py-1 text-sm transition-colors ${
              activeFormats.has('orderedList')
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500'
            } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            title="Numbered List"
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
              <path d="M3 4h18M3 12h18M3 20h18M3 4v16" />
            </svg>
          </button>
        </div>
      )}

      {/* Editor */}
      <div
        className={`relative min-h-[150px] rounded-b-lg border ${
          error
            ? 'border-red-500 focus-within:ring-2 focus-within:ring-red-500'
            : isFocused
              ? 'border-primary-500 ring-2 ring-primary-500'
              : 'border-gray-300 dark:border-gray-600'
        } bg-white p-4 dark:bg-gray-800`}
      >
        <div
          ref={editorRef}
          contentEditable={!disabled}
          onInput={handleInput}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyUp={handleKeyUp}
          onMouseUp={handleMouseUp}
          className={`min-h-[100px] w-full outline-none ${
            disabled ? 'cursor-not-allowed opacity-50' : ''
          } prose prose-sm dark:prose-invert max-w-none`}
          style={{
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
          }}
          data-placeholder={placeholder}
          suppressContentEditableWarning
        />
        {!value && !isFocused && (
          <div className="pointer-events-none absolute left-4 top-4 text-gray-400 dark:text-gray-500">
            {placeholder}
          </div>
        )}
      </div>

      {/* Footer with character count and error */}
      <div className="mt-2 flex items-center justify-between">
        <div>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          {!error && minLength && characterCount < minLength && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Minimum {minLength} characters required
            </p>
          )}
        </div>
        {showCharacterCount && (
          <p className={`text-sm ${getCharacterCountColor()}`}>
            {characterCount}
            {maxLength ? ` / ${maxLength}` : ''} characters
          </p>
        )}
      </div>

      <style jsx>{`
        [contenteditable='true']:empty:before {
          content: attr(data-placeholder);
          color: #9ca3af;
          cursor: text;
        }
        [contenteditable='true']:focus:before {
          content: '';
        }
      `}</style>
    </div>
  );
}
