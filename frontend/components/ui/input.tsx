import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', ...props }, ref) => {
    const inputId = props.id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = Boolean(error);

    return (
      <div className="w-full font-sans">
        {label && (
          <label
            htmlFor={inputId}
            className="mb-2 block text-sm font-medium text-secondary-900 dark:text-gray-100"
          >
            {label}
            {props.required && (
              <span className="ml-1 text-primary-500" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`
            w-full rounded-lg border bg-white px-4 py-2.5 text-sm text-secondary-900
            font-sans placeholder:text-gray-400
            transition-colors duration-200
            focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1
            disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500 disabled:opacity-70
            dark:bg-gray-900 dark:text-gray-50 dark:placeholder:text-gray-500 dark:disabled:bg-gray-800
            ${
              hasError
                ? 'border-red-500 focus:border-red-500 focus-visible:ring-red-300'
                : 'border-gray-300 focus:border-primary-500 focus-visible:ring-primary-300 dark:border-gray-700 dark:focus:border-primary-400'
            }
            ${className}
          `}
          aria-invalid={hasError}
          aria-describedby={
            error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined
          }
          {...props}
        />
        {error && (
          <p
            id={`${inputId}-error`}
            className="mt-1.5 text-sm font-medium text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${inputId}-helper`}
            className="mt-1.5 text-sm text-gray-500 dark:text-gray-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
