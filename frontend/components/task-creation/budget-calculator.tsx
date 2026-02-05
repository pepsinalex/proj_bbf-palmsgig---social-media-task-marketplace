'use client';

import React, { useEffect } from 'react';
import { calculateServiceFee, calculateTotalCost } from '@/lib/validations/task';

export interface BudgetCalculatorProps {
  taskBudget: number;
  numberOfTasks: number;
  serviceFee: number;
  totalCost: number;
  onTaskBudgetChange: (budget: number) => void;
  onNumberOfTasksChange: (count: number) => void;
  onServiceFeeChange: (fee: number) => void;
  onTotalCostChange: (cost: number) => void;
  errors?: {
    taskBudget?: string;
    numberOfTasks?: string;
  };
  disabled?: boolean;
}

const SERVICE_FEE_PERCENTAGE = 15;

export function BudgetCalculator({
  taskBudget,
  numberOfTasks,
  serviceFee,
  totalCost,
  onTaskBudgetChange,
  onNumberOfTasksChange,
  onServiceFeeChange,
  onTotalCostChange,
  errors,
  disabled = false,
}: BudgetCalculatorProps) {
  // Calculate and update fees whenever budget or task count changes
  useEffect(() => {
    const newServiceFee = calculateServiceFee(taskBudget, numberOfTasks);
    const newTotalCost = calculateTotalCost(taskBudget, numberOfTasks);

    if (newServiceFee !== serviceFee) {
      onServiceFeeChange(newServiceFee);
    }
    if (newTotalCost !== totalCost) {
      onTotalCostChange(newTotalCost);
    }
  }, [taskBudget, numberOfTasks]); // eslint-disable-line react-hooks/exhaustive-deps

  const subtotal = taskBudget * numberOfTasks;

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="w-full space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Budget & Pricing
        </h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Set your budget and number of tasks
        </p>
      </div>

      {/* Task Budget Input */}
      <div>
        <label
          htmlFor="taskBudget"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100"
        >
          Budget per Task <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          Amount you will pay for each completed task ($0.50 - $1,000)
        </p>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400">
            $
          </span>
          <input
            id="taskBudget"
            type="number"
            value={taskBudget || ''}
            onChange={(e) => {
              const value = parseFloat(e.target.value) || 0;
              onTaskBudgetChange(value);
            }}
            disabled={disabled}
            min={0.5}
            max={1000}
            step={0.01}
            placeholder="0.00"
            className={`w-full rounded-lg border px-4 py-2 pl-8 text-gray-900 transition-colors dark:bg-gray-800 dark:text-gray-100 ${
              errors?.taskBudget
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600'
            } ${disabled ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-700' : ''}`}
          />
        </div>
        {errors?.taskBudget && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.taskBudget}</p>
        )}
      </div>

      {/* Number of Tasks Input */}
      <div>
        <label
          htmlFor="numberOfTasks"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100"
        >
          Number of Tasks <span className="text-red-500">*</span>
        </label>
        <p className="mb-2 text-xs text-gray-600 dark:text-gray-400">
          How many people should complete this task (1 - 10,000)
        </p>
        <input
          id="numberOfTasks"
          type="number"
          value={numberOfTasks || ''}
          onChange={(e) => {
            const value = parseInt(e.target.value, 10) || 0;
            onNumberOfTasksChange(value);
          }}
          disabled={disabled}
          min={1}
          max={10000}
          step={1}
          placeholder="0"
          className={`w-full rounded-lg border px-4 py-2 text-gray-900 transition-colors dark:bg-gray-800 dark:text-gray-100 ${
            errors?.numberOfTasks
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600'
          } ${disabled ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-700' : ''}`}
        />
        {errors?.numberOfTasks && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.numberOfTasks}</p>
        )}
      </div>

      {/* Cost Breakdown */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 dark:border-gray-700 dark:bg-gray-800">
        <h4 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">
          Cost Breakdown
        </h4>

        <div className="space-y-3">
          {/* Subtotal */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Subtotal ({numberOfTasks} × {formatCurrency(taskBudget)})
            </span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatCurrency(subtotal)}
            </span>
          </div>

          {/* Service Fee */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Service Fee ({SERVICE_FEE_PERCENTAGE}%)
            </span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {formatCurrency(serviceFee)}
            </span>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-600" />

          {/* Total */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Total Cost
            </span>
            <span className="text-xl font-bold text-primary-600 dark:text-primary-400">
              {formatCurrency(totalCost)}
            </span>
          </div>
        </div>
      </div>

      {/* Information Box */}
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
              About Service Fees
            </h4>
            <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
              <ul className="list-inside list-disc space-y-1">
                <li>Service fee is {SERVICE_FEE_PERCENTAGE}% of the total task budget</li>
                <li>This fee covers platform maintenance, payment processing, and support</li>
                <li>Task creators are only charged when tasks are successfully completed</li>
                <li>Funds are held in escrow until task completion and verification</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      {taskBudget > 0 && numberOfTasks > 0 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-green-400"
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
            <div className="ml-3">
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                You will pay {formatCurrency(totalCost)} for {numberOfTasks} completed{' '}
                {numberOfTasks === 1 ? 'task' : 'tasks'}
              </p>
              <p className="mt-1 text-xs text-green-700 dark:text-green-300">
                Each task completion will cost you {formatCurrency(taskBudget + serviceFee / numberOfTasks)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
