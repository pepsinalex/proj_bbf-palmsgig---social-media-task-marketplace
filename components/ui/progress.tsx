import React from 'react';

export interface ProgressStep {
  id: string;
  label: string;
  description?: string;
}

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  steps: ProgressStep[];
  currentStep: number;
  completedSteps?: number[];
}

export function Progress({ steps, currentStep, completedSteps = [], className = '', ...props }: ProgressProps) {
  const isStepCompleted = (stepIndex: number): boolean => {
    return completedSteps.includes(stepIndex) || stepIndex < currentStep;
  };

  const isStepCurrent = (stepIndex: number): boolean => {
    return stepIndex === currentStep;
  };

  const getStepStatus = (stepIndex: number): 'completed' | 'current' | 'upcoming' => {
    if (isStepCompleted(stepIndex)) {
      return 'completed';
    }
    if (isStepCurrent(stepIndex)) {
      return 'current';
    }
    return 'upcoming';
  };

  const progressPercentage = (currentStep / (steps.length - 1)) * 100;

  return (
    <div className={`w-full ${className}`} {...props}>
      {/* Progress bar */}
      <div className="relative mb-8">
        {/* Background bar */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 -translate-y-1/2 bg-gray-200 dark:bg-gray-700" />

        {/* Progress fill */}
        <div
          className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 bg-primary-500 transition-all duration-300 ease-in-out"
          style={{ width: `${progressPercentage}%` }}
        />

        {/* Step indicators */}
        <div className="relative flex justify-between">
          {steps.map((step, index) => {
            const status = getStepStatus(index);

            return (
              <div key={step.id} className="flex flex-col items-center">
                {/* Step circle */}
                <div
                  className={`z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                    status === 'completed'
                      ? 'border-primary-500 bg-primary-500'
                      : status === 'current'
                        ? 'border-primary-500 bg-white dark:bg-gray-800'
                        : 'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800'
                  }`}
                >
                  {status === 'completed' ? (
                    <svg
                      className="h-5 w-5 text-white"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <span
                      className={`text-sm font-medium ${
                        status === 'current'
                          ? 'text-primary-500'
                          : 'text-gray-400 dark:text-gray-500'
                      }`}
                    >
                      {index + 1}
                    </span>
                  )}
                </div>

                {/* Step label */}
                <div className="mt-2 text-center">
                  <p
                    className={`text-sm font-medium ${
                      status === 'current'
                        ? 'text-primary-600 dark:text-primary-400'
                        : status === 'completed'
                          ? 'text-gray-900 dark:text-gray-100'
                          : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {step.description}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Simple progress bar variant without steps
export interface SimpleProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SimpleProgress({
  value,
  max = 100,
  showLabel = false,
  size = 'md',
  className = '',
  ...props
}: SimpleProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className={`w-full ${className}`} {...props}>
      <div className={`overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700 ${sizeClasses[size]}`}>
        <div
          className="h-full bg-primary-500 transition-all duration-300 ease-in-out"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
      {showLabel && (
        <div className="mt-1 text-right">
          <span className="text-xs text-gray-600 dark:text-gray-400">
            {Math.round(percentage)}%
          </span>
        </div>
      )}
    </div>
  );
}
